from datetime import timedelta, date
from typing import List, Optional
from enum import Enum
from sqlalchemy import Column, DateTime, String, Integer, Date, Text, Interval, Table, Enum as SQLAlchemyEnum
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declared_attr
from pydantic import BaseModel, ConfigDict
from common.db.entity.base import DBBaseModel
from common.enums.enums import SupportedLanguage
from sqlalchemy.dialects.postgresql import ARRAY


class MovieStatus(str, Enum):
    NEW = "new"
    ONLINE = "online"
    OFFLINE = "offline"


class Movie(DBBaseModel):
    __tablename__ = "movies"
    __table_args__ = {'extend_existing': True}
    
    code = Column(String(50), nullable=False, index=True)
    duration = Column(String(50), nullable=False)
    release_date = Column(String(50), nullable=True)
    cover_image_url = Column(Text)
    preview_video_url = Column(Text)
    thumbnail = Column(Text)  # 新增缩略图字段
    likes = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    link = Column(String(255))
    original_id = Column(Integer)
    title = Column(Text)
    status = Column(String(20), default=MovieStatus.NEW.value, nullable=False)
    description = Column(Text)
    tags = Column(ARRAY(Text), nullable=True)
    genres = Column(ARRAY(Text), nullable=True)
    director = Column(String(55), nullable=True)
    maker = Column(String(55), nullable=True)
    actresses = Column(ARRAY(String(55)), nullable=True)
    watch_urls_info = Column(Text, nullable=True)
    download_urls_info = Column(Text, nullable=True)
    magnets = Column(Text, nullable=True)
    series = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Movie {self.code}>"
