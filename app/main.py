from fastapi import FastAPI, Depends, Form, Request, File
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import UploadFile
from sqlalchemy.orm import Session
import io
import csv
import os
import uuid
import pandas as pd
from pdfminer.high_level import extract_text
from pydantic import BaseModel

from .database import Base, engine, SessionLocal
from . import models, crud
from .openai_util import parse_text_to_fields, chat_reply
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
    return templates.TemplateResponse(
        "new_report.html", {"request": request, "title": "Create Report", "active": "create"}
    )


@app.post("/report-types/new")
async def create_report(
    request: Request,
    name: str = Form(...),
    source: str = Form(...),
    input_mode: str = Form("struct"),
    db: Session = Depends(get_db),
    file: UploadFile = File(None),
    fields: list[str] = Form(None),
    questions: list[str] = Form(None),
    types: list[str] = Form(None),
    prompt: str = Form(None),
):
    if source == "manual":
        if input_mode == "struct":
            if not fields:
                field_list = []
                question_list = []
                type_list = []
            elif isinstance(fields, list):
                field_list = [f for f in fields if f]
                question_list = [q for q in questions][: len(field_list)] if questions else ["" for _ in field_list]
                type_list = [t for t in types][: len(field_list)] if types else ["qa" for _ in field_list]
            else:
                field_list = [fields] if fields else []
                question_list = [questions] if questions else [""]
                type_list = [types] if types else ["qa"]
            crud.create_report_type(
                db, name, field_list, question_list, type_list, "struct"
            )
        else:  # smart mode
            if isinstance(fields, list):
                field_list = [f for f in fields if f]
            else:
                field_list = [fields] if fields else []
            type_list = ["qa" for _ in field_list]
            crud.create_report_type(
                db, name, field_list, [], type_list, "smart", prompt=prompt
            )
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
        question_list = [f + " を入力してください" for f in field_list]
        type_list = ["qa" for _ in field_list]
        crud.create_report_type(
            db, name, field_list, question_list, type_list, "struct"
        )
    return RedirectResponse(url="/", status_code=302)


@app.get("/report-types/{rt_id}", response_class=HTMLResponse)
async def show_records(request: Request, rt_id: int, db: Session = Depends(get_db)):
    rt = crud.get_report_type(db, rt_id)
    records = crud.fetch_report_records(db, rt)
    questions = crud.fetch_question_prompts(db, rt)
    type_map = {
        "qa": "テキスト",
        "image": "画像",
        "video": "動画",
    }
    field_info = []
    for i, f in enumerate(rt.fields):
        t = rt.field_types[i] if rt.field_types else "qa"
        field_info.append(
            {
                "name": f,
                "question": questions.get(f, ""),
                "type": t,
                "type_label": type_map.get(t, t),
            }
        )
    return templates.TemplateResponse(
        "records.html",
        {
            "request": request,
            "rt": rt,
            "records": records,
            "fields_info": field_info,
            "title": rt.name,
            "active": "list",
            "prompt": rt.prompt,
        },
    )


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


@app.post("/report-types/{rt_id}/records/{rec_id}/update")
async def update_record(rt_id: int, rec_id: int, request: Request, db: Session = Depends(get_db)):
    rt = crud.get_report_type(db, rt_id)
    form = await request.form()
    data = {}
    for f, t in zip(rt.fields, rt.field_types or []):
        if t == "qa" and f in form:
            data[f] = form[f]
    if data:
        crud.update_report_record(db, rt, rec_id, data)
    return RedirectResponse(url=f"/report-types/{rt_id}", status_code=302)


@app.post("/report-types/{rt_id}/questions")
async def update_questions(rt_id: int, request: Request, db: Session = Depends(get_db)):
    rt = crud.get_report_type(db, rt_id)
    form = await request.form()
    if rt.mode == "struct":
        qs = form.getlist("questions")
        crud.update_question_prompts(db, rt, qs)
    else:
        prompt = form.get("prompt", "")
        crud.update_report_prompt(db, rt, prompt)
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


@app.get("/users", response_class=HTMLResponse)
async def users(request: Request):
    return templates.TemplateResponse("users.html", {"request": request, "title":"ユーザー管理", "active":"users"})


@app.get("/settings/users", response_class=HTMLResponse)
async def settings_users_redirect():
    return RedirectResponse(url="/users")


@app.get("/settings", response_class=HTMLResponse)
async def settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request, "title":"Settings"})


@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request, "title":"AIチャット", "active":"chat"})


@app.post("/chat", response_class=HTMLResponse)
async def chat_submit(request: Request, message: str = Form(...)):
    reply = chat_reply(message)
    return templates.TemplateResponse("chat.html", {"request": request, "title":"AIチャット", "active":"chat", "message": message, "reply": reply})


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

# Request models for API endpoints


class ReportRequest(BaseModel):
    report_name: str


class ParseRequest(ReportRequest):
    text: str

# API endpoint


@app.post("/api/report/parse")
async def api_parse(req: ParseRequest, db: Session = Depends(get_db)):
    """Parse free text with GPT and store as a new record"""
    rt = crud.get_report_type_by_name(db, req.report_name)
    if not rt:
        return {"error": "report type not found"}
    if rt.mode != "smart":
        return {"error": "report type is not smart mode"}
    data = parse_text_to_fields(req.text, rt.fields)
    crud.insert_report_record(db, rt, data)
    return {"status": "ok", "data": data}


@app.post("/api/report/fields")
async def api_report_fields(req: ReportRequest, db: Session = Depends(get_db)):
    """Return the field list for the specified report"""
    rt = crud.get_report_type_by_name(db, req.report_name)
    if not rt:
        return {"error": "report type not found"}
    return {"fields": rt.fields}


@app.post("/api/report/questions")
async def api_report_questions(req: ReportRequest, db: Session = Depends(get_db)):
    """Return the question prompts for the specified report"""
    rt = crud.get_report_type_by_name(db, req.report_name)
    if not rt:
        return {"error": "report type not found"}
    if rt.mode == "struct":
        questions = crud.fetch_question_prompts(db, rt)
        data = [
            {
                "field": f,
                "question": questions.get(f, ""),
                "type": rt.field_types[i] if rt.field_types else "qa",
            }
            for i, f in enumerate(rt.fields)
        ]
        return {"mode": "struct", "questions": data}
    else:
        return {"mode": "smart", "prompt": rt.prompt, "fields": rt.fields}


@app.get("/api/report-types")
async def api_report_types(db: Session = Depends(get_db)):
    rts = crud.get_report_types(db)
    return {"reports": [rt.name for rt in rts]}


@app.post("/api/report/record")
async def api_create_record(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    logs: list[str] = []
    report_name = form.get("report_name")
    logs.append(f"report_name: {report_name}")
    if not report_name:
        return {"error": "report_name required", "logs": logs}
    rt = crud.get_report_type_by_name(db, report_name)
    if not rt:
        logs.append("report type not found")
        return {"error": "report type not found", "logs": logs}
    if rt.mode != "struct":
        logs.append("report not in struct mode")
        return {"error": "invalid mode", "logs": logs}

    data: dict[str, str] = {}
    os.makedirs("static/uploads", exist_ok=True)
    field_types = rt.field_types or []
    type_map = {f: field_types[i] if i < len(field_types) else "text" for i, f in enumerate(rt.fields)}
    logs.append(f"rt.fields: {rt.fields}")
    logs.append(f"form keys: {list(form.keys())}")
    for f in rt.fields:
        t = type_map.get(f, "text")
        logs.append(f"checking: {f}, {t}")
        value = form[f] if f in form else None
        logs.append(f"received: {value}, {type(value)}")
        if t in ("image", "video"):
            if isinstance(value, UploadFile) and value.filename:
                contents = await value.read()
                logs.append(f"read size: {len(contents)}")
                if len(contents) > 100 * 1024 * 1024:
                    logs.append("file too large")
                    return {"error": "file too large", "logs": logs}
                ext = os.path.splitext(value.filename)[1]
                filename = f"{uuid.uuid4().hex}{ext}"
                with open(os.path.join("static/uploads", filename), "wb") as out:
                    out.write(contents)
                data[f] = f"uploads/{filename}"
            else:
                logs.append("not a valid UploadFile")
        else:
            if not isinstance(value, UploadFile):
                logs.append(f"text value: {value}")
                if value is not None:
                    data[f] = value
            else:
                logs.append("unexpected UploadFile for text field")

    crud.insert_report_record(db, rt, data)
    logs.append("inserted record")
    return {"status": "ok", "logs": logs}
