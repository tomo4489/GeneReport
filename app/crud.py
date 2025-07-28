from sqlalchemy.orm import Session
from . import models
from .report_dal import get_report_table


def create_report_type(db: Session, name: str, fields: list[str]):
    rt = models.ReportType(name=name, fields=fields)
    db.add(rt)
    db.commit()
    db.refresh(rt)
    # create table
    get_report_table(rt.id, fields)
    return rt


def get_report_types(db: Session):
    return db.query(models.ReportType).all()


def get_report_type(db: Session, rt_id: int):
    return db.query(models.ReportType).filter(models.ReportType.id == rt_id).first()

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
