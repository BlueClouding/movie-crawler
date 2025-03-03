from datetime import timedelta, date
from typing import List, Optional
from sqlalchemy import Column, DateTime, String, Integer, Date, Text, Interval, Table
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declared_attr
from pydantic import BaseModel, ConfigDict
from app.config.database import Base
from app.db.entity.base import DBBaseModel
from app.db.entity.enums import SupportedLanguageEnum


class Movie(DBBaseModel):
    __tablename__ = "movies"
    __table_args__ = {'extend_existing': True}
    
    code = Column(String(50), nullable=False, index=True)
    duration = Column(String(50), nullable=False)
    release_date = Column(String(50), nullable=False)
    cover_image_url = Column(Text)
    preview_video_url = Column(Text)
    likes = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    link = Column(String(255))
    original_id = Column(Integer)
    
    def __repr__(self):
        return f"<Movie {self.code}>"
