from sqlalchemy import Table, Column, Integer, MetaData, String
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

def drop_report_table(report_type_id: int):
    table_name = f"report_{report_type_id}"
    if engine.dialect.has_table(engine.connect(), table_name):
        tbl = Table(table_name, metadata, autoload_with=engine)
        tbl.drop(engine)
        metadata.remove(tbl)


def rename_column(report_type_id: int, old: str, new: str):
    table_name = f"report_{report_type_id}"
    engine.execute(f'ALTER TABLE "{table_name}" RENAME COLUMN "{old}" TO "{new}"')


def delete_records(report_type_id: int, ids: list[int]):
    table_name = f"report_{report_type_id}"
    table = Table(table_name, metadata, autoload_with=engine)
    stmt = table.delete().where(table.c.id.in_(ids))
    engine.execute(stmt)

# Question table handling
def get_question_table(report_type_id: int, fields: list[str]):
    """Return the question table for the report, creating it if needed."""
    table_name = f"report_{report_type_id}_q"
    try:
        table = Table(table_name, metadata, autoload_with=engine)
    except Exception:
        cols = [Column('id', Integer, primary_key=True)]
        for f in fields:
            cols.append(Column(f, String))
        table = Table(table_name, metadata, *cols)
        metadata.create_all(tables=[table])
    return table


def drop_question_table(report_type_id: int):
    table_name = f"report_{report_type_id}_q"
    if engine.dialect.has_table(engine.connect(), table_name):
        tbl = Table(table_name, metadata, autoload_with=engine)
        tbl.drop(engine)
        metadata.remove(tbl)


def rename_question_column(report_type_id: int, old: str, new: str):
    table_name = f"report_{report_type_id}_q"
    engine.execute(f'ALTER TABLE "{table_name}" RENAME COLUMN "{old}" TO "{new}"')
