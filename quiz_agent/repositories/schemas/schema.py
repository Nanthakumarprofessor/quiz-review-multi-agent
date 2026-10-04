"""
Database Schema Models
"""
import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ErrorLog(Base):
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    uuid = Column(String(36), default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    request_id = Column(String(36), nullable=False, index=True)
    function_name = Column(String(100), nullable=False)
    file_name = Column(String(100), nullable=False)
    error_name = Column(String(100))
    error_message = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(String(50), default="client")
