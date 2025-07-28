from sqlalchemy import Table, Column, Integer, MetaData, String
from sqlalchemy.exc import NoSuchTableError
from .database import engine

metadata = MetaData(bind=engine)

def get_report_table(report_type_id: int, fields: list[str]):
    table_name = f"report_{report_type_id}"
    try:
        table = Table(table_name, metadata, autoload_with=engine)
    except Exception:
        cols = [Column('id', Integer, primary_key=True)]
        for f in fields:
            cols.append(Column(f, String))
        table = Table(table_name, metadata, *cols)
        metadata.create_all(tables=[table])
    return table
