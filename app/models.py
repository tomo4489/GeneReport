from sqlalchemy import Column, Integer, String, JSON
from .database import Base

class ReportType(Base):
    __tablename__ = "report_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    mode = Column(String, default="struct")  # 'struct' or 'smart'
    prompt = Column(String, nullable=True)  # used only in smart mode
    fields = Column(JSON)  # list of field names in order
    field_types = Column(JSON)  # list of input types aligned with fields
