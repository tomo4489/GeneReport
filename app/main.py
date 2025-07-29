from fastapi import FastAPI, Depends, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import io
import csv
import pandas as pd
from pdfminer.high_level import extract_text

from .database import Base, engine, SessionLocal
from . import models, crud
from .openai_util import parse_text_to_fields
from .report_dal import get_report_table

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Report Generator")
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Web UI
@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    rts = crud.get_report_types(db)
    return templates.TemplateResponse("index.html", {"request": request, "report_types": rts, "title":"Reports", "active":"list"})


@app.get("/report-types/new", response_class=HTMLResponse)
async def new_report_form(request: Request):
    return templates.TemplateResponse("new_report.html", {"request": request, "title":"Create Report", "active":"create"})


@app.post("/report-types/new")
async def create_report(request: Request, name: str = Form(...), mode: str = Form(...), db: Session = Depends(get_db), file: UploadFile = File(None), fields: list[str] = Form(None)):
    if mode == 'manual':
        if not fields:
            field_list = []
        elif isinstance(fields, list):
            field_list = [f for f in fields if f]
        else:
            field_list = [fields] if fields else []
    else:
        contents = await file.read()
        if file.filename.lower().endswith('.xlsx'):
            df = pd.read_excel(io.BytesIO(contents))
            field_list = list(df.columns)
        elif file.filename.lower().endswith('.pdf'):
            text = extract_text(io.BytesIO(contents))
            field_list = [line.strip() for line in text.splitlines() if line.strip()][:10]
        else:
            field_list = []
    crud.create_report_type(db, name, field_list)
    return RedirectResponse(url="/", status_code=302)


@app.get("/report-types/{rt_id}", response_class=HTMLResponse)
async def show_records(request: Request, rt_id: int, db: Session = Depends(get_db)):
    rt = crud.get_report_type(db, rt_id)
    records = crud.fetch_report_records(db, rt)
    return templates.TemplateResponse("records.html", {"request": request, "rt": rt, "records": records, "title":rt.name, "active":"list"})


@app.post("/report-types/{rt_id}/upload")
async def upload_excel(rt_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    rt = crud.get_report_type(db, rt_id)
    df = pd.read_excel(io.BytesIO(await file.read()))
    # assume first row has column names matching fields
    for _, row in df.iterrows():
        data = {f: str(row.get(f, "")) for f in rt.fields}
        crud.insert_report_record(db, rt, data)
    return RedirectResponse(url=f"/report-types/{rt_id}", status_code=302)


@app.post("/report-types/{rt_id}/records/{rec_id}/delete")
async def delete_record(rt_id: int, rec_id: int, db: Session = Depends(get_db)):
    crud.delete_report_records(db, crud.get_report_type(db, rt_id), [rec_id])
    return RedirectResponse(url=f"/report-types/{rt_id}", status_code=302)

@app.get("/report-types/{rt_id}/records/{rec_id}/delete")
async def delete_record_get(rt_id: int, rec_id: int, db: Session = Depends(get_db)):
    crud.delete_report_records(db, crud.get_report_type(db, rt_id), [rec_id])
    return RedirectResponse(url=f"/report-types/{rt_id}", status_code=302)


@app.post("/report-types/{rt_id}/delete-records")
async def delete_records(rt_id: int, record_ids: list[int] = Form(...), db: Session = Depends(get_db)):
    crud.delete_report_records(db, crud.get_report_type(db, rt_id), record_ids)
    return RedirectResponse(url=f"/report-types/{rt_id}", status_code=302)


@app.get("/report-types/{rt_id}/delete")
async def delete_report_type(rt_id: int, db: Session = Depends(get_db)):
    rt = crud.get_report_type(db, rt_id)
    crud.delete_report_type(db, rt)
    return RedirectResponse(url="/", status_code=302)


@app.get("/report-types/{rt_id}/edit", response_class=HTMLResponse)
async def edit_columns(request: Request, rt_id: int, db: Session = Depends(get_db)):
    rt = crud.get_report_type(db, rt_id)
    return templates.TemplateResponse("edit_columns.html", {"request": request, "rt": rt, "title":"Edit Columns", "active":"list"})


@app.post("/report-types/{rt_id}/edit")
async def update_columns(rt_id: int, fields: list[str] = Form(...), db: Session = Depends(get_db)):
    rt = crud.get_report_type(db, rt_id)
    crud.update_report_type_fields(db, rt, fields)
    return RedirectResponse(url=f"/report-types/{rt_id}", status_code=302)


@app.get("/report-types/{rt_id}/records/{rec_id}/excel")
async def download_record_excel(rt_id: int, rec_id: int, db: Session = Depends(get_db)):
    rt = crud.get_report_type(db, rt_id)
    table = get_report_table(rt.id, rt.fields)
    sel = table.select().where(table.c.id == rec_id)
    res = db.execute(sel).fetchone()
    output = io.BytesIO()
    df = pd.DataFrame([{f: res[f] for f in rt.fields}])
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    headers = {"Content-Disposition": f"attachment; filename=record_{rec_id}.xlsx"}
    return StreamingResponse(output, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers=headers)


@app.get("/settings/users", response_class=HTMLResponse)
async def users(request: Request):
    return templates.TemplateResponse("users.html", {"request": request, "title":"ユーザー管理"})


@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request, "title":"Settings"})


@app.get("/settings/apis", response_class=HTMLResponse)
async def api_list(request: Request):
    return templates.TemplateResponse("api_list.html", {"request": request, "title":"API一覧"})


from .config import save_openai_config, load_openai_config

@app.get("/settings/openai", response_class=HTMLResponse)
async def openai_form(request: Request):
    cfg = load_openai_config()
    return templates.TemplateResponse("openai_settings.html", {"request": request, "title":"Azure OpenAI設定", "config": cfg})


@app.post("/settings/openai")
async def save_openai(request: Request, endpoint: str = Form(None), key: str = Form(None)):
    save_openai_config({"endpoint": endpoint, "key": key})
    return RedirectResponse(url="/settings", status_code=302)


# API endpoint
@app.post("/api/report/{rt_id}/parse")
async def api_parse(rt_id: int, text: str = Form(...), db: Session = Depends(get_db)):
    rt = crud.get_report_type(db, rt_id)
    data = parse_text_to_fields(text, rt.fields)
    crud.insert_report_record(db, rt, data)
    return {"status": "ok", "data": data}


@app.get("/api/report-types")
async def api_report_types(db: Session = Depends(get_db)):
    rts = crud.get_report_types(db)
    return {"reports": [rt.name for rt in rts]}


@app.post("/api/report/{name}/record")
async def api_create_record(name: str, payload: dict, db: Session = Depends(get_db)):
    rt = crud.get_report_type_by_name(db, name)
    if not rt:
        return {"error": "report type not found"}
    crud.insert_report_record(db, rt, payload)
    return {"status": "ok"}
