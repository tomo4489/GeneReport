from fastapi import FastAPI, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import io
import csv
import pandas as pd

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
async def index(db: Session = Depends(get_db)):
    rts = crud.get_report_types(db)
    return templates.TemplateResponse("index.html", {"request": {}, "report_types": rts})


@app.get("/report-types/new", response_class=HTMLResponse)
async def new_report_form():
    return templates.TemplateResponse("new_report.html", {"request": {}})


@app.post("/report-types/new")
async def create_report(name: str = Form(...), fields: str = Form(...), db: Session = Depends(get_db)):
    field_list = [f.strip() for f in fields.split(',') if f.strip()]
    crud.create_report_type(db, name, field_list)
    return RedirectResponse(url="/", status_code=302)


@app.get("/report-types/{rt_id}", response_class=HTMLResponse)
async def show_records(rt_id: int, db: Session = Depends(get_db)):
    rt = crud.get_report_type(db, rt_id)
    records = crud.fetch_report_records(db, rt)
    return templates.TemplateResponse("records.html", {"request": {}, "rt": rt, "records": records})


@app.post("/report-types/{rt_id}/upload")
async def upload_excel(rt_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    rt = crud.get_report_type(db, rt_id)
    df = pd.read_excel(io.BytesIO(await file.read()))
    # assume first row has column names matching fields
    for _, row in df.iterrows():
        data = {f: str(row.get(f, "")) for f in rt.fields}
        crud.insert_report_record(db, rt, data)
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


# API endpoint
@app.post("/api/report/{rt_id}/parse")
async def api_parse(rt_id: int, text: str = Form(...), db: Session = Depends(get_db)):
    rt = crud.get_report_type(db, rt_id)
    data = parse_text_to_fields(text, rt.fields)
    crud.insert_report_record(db, rt, data)
    return {"status": "ok", "data": data}
