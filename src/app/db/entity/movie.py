from datetime import timedelta, date
from typing import List, Optional
from sqlalchemy import Column, DateTime, String, Integer, Date, Text, Interval, ForeignKey, Table
from sqlalchemy.orm import relationship
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
    
    # 关系 - 修改为使用关联类
    titles = relationship("app.db.entity.movie_info.MovieTitle", back_populates="movie", cascade="all, delete-orphan")
    actress_associations = relationship("app.db.entity.movie_actress.MovieActress", back_populates="movie", cascade="all, delete-orphan")
    genre_associations = relationship("app.db.entity.movie_genres.MovieGenre", back_populates="movie", cascade="all, delete-orphan")
    magnets = relationship("app.db.entity.download.Magnet", back_populates="movie", cascade="all, delete-orphan")
    download_urls = relationship("app.db.entity.download.DownloadUrl", back_populates="movie", cascade="all, delete-orphan")
    watch_urls = relationship("app.db.entity.download.WatchUrl", back_populates="movie", cascade="all, delete-orphan")
    
    # 方便访问的属性
    @property
    def actresses(self):
        return [association.actress for association in self.actress_associations]
        
    @property
    def genres(self):
        return [association.genre for association in self.genre_associations]
    
    def __repr__(self):
        return f"<Movie {self.code}>"
