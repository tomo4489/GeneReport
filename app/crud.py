from sqlalchemy.orm import Session
from . import models
from .report_dal import (
    get_report_table,
    drop_report_table,
    rename_column,
    delete_records,
    get_question_table,
    drop_question_table,
    rename_question_column,
)

def create_report_type(db: Session, name: str, fields: list[str], questions: list[str], types: list[str]):
    """Create a new report type with associated tables."""
    rt = models.ReportType(name=name, fields=fields, field_types=types)
    db.add(rt)
    db.commit()
    db.refresh(rt)
    get_report_table(rt.id, fields)
    q_table = get_question_table(rt.id, fields)
    if questions:
        data = {f: q for f, q in zip(fields, questions)}
        db.execute(q_table.insert().values(**data))
        db.commit()
    return rt


def get_report_types(db: Session):
    return db.query(models.ReportType).all()


def get_report_type(db: Session, rt_id: int):
    return db.query(models.ReportType).filter(models.ReportType.id == rt_id).first()

def get_report_type_by_name(db: Session, name: str):
    return db.query(models.ReportType).filter(models.ReportType.name == name).first()

def insert_report_record(db: Session, report_type: models.ReportType, data: dict):
    table = get_report_table(report_type.id, report_type.fields)
    insert_stmt = table.insert().values(**data)
    db.execute(insert_stmt)
    db.commit()


def fetch_report_records(db: Session, report_type: models.ReportType):
    table = get_report_table(report_type.id, report_type.fields)
    sel = table.select()
    res = db.execute(sel)
    return [dict(r) for r in res]

def fetch_question_prompts(db: Session, report_type: models.ReportType):
    table = get_question_table(report_type.id, report_type.fields)
    sel = table.select()
    res = db.execute(sel).fetchone()
    if not res:
        return {}
    return {f: res[f] for f in report_type.fields}

def update_question_prompts(db: Session, report_type: models.ReportType, questions: list[str]):
    table = get_question_table(report_type.id, report_type.fields)
    existing = db.execute(table.select()).fetchone()
    data = {f: q for f, q in zip(report_type.fields, questions)}
    if existing:
        db.execute(table.update().where(table.c.id == existing["id"]).values(**data))
    else:
        db.execute(table.insert().values(**data))
    db.commit()

def delete_report_type(db: Session, rt: models.ReportType):
    drop_report_table(rt.id)
    drop_question_table(rt.id)
    db.delete(rt)
    db.commit()


def delete_report_records(db: Session, report_type: models.ReportType, ids: list[int]):
    delete_records(report_type.id, ids)
    db.commit()


def update_report_type_fields(db: Session, rt: models.ReportType, new_fields: list[str]):
    for old, new in zip(rt.fields, new_fields):
        if old != new:
            rename_column(rt.id, old, new)
            rename_question_column(rt.id, old, new)
    rt.fields = new_fields
    if rt.field_types:
        rt.field_types = rt.field_types[: len(new_fields)]

    db.commit()
    db.refresh(rt)
