from sqlalchemy import Column, Integer, String, JSON
from .database import Base

class ReportType(Base):
    __tablename__ = 'report_types'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    fields = Column(JSON)  # list of field names
