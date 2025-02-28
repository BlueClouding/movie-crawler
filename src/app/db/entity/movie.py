from datetime import timedelta, date
from typing import List, Optional
from sqlalchemy import Column, DateTime, String, Integer, Date, Text, Interval, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declared_attr
from pydantic import BaseModel, ConfigDict
from app.config.database import Base
from db.entity import movie_actress, movie_genres
from db.entity.base import DBBaseModel
from db.entity.enums import SupportedLanguageEnum


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
    titles = relationship("MovieTitle", back_populates="movie", cascade="all, delete-orphan")
    actress_associations = relationship("MovieActress", back_populates="movie", cascade="all, delete-orphan")
    genre_associations = relationship("MovieGenre", back_populates="movie", cascade="all, delete-orphan")
    magnets = relationship("Magnet", back_populates="movie", cascade="all, delete-orphan")
    download_urls = relationship("DownloadUrl", back_populates="movie", cascade="all, delete-orphan")
    watch_urls = relationship("WatchUrl", back_populates="movie", cascade="all, delete-orphan")
    
    # 方便访问的属性
    @property
    def actresses(self):
        return [association.actress for association in self.actress_associations]
        
    @property
    def genres(self):
        return [association.genre for association in self.genre_associations]
    
    def __repr__(self):
        return f"<Movie {self.code}>"

class MovieTitle(DBBaseModel):
    __tablename__ = "movie_titles"
    __table_args__ = {'extend_existing': True}
    
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    language = Column(SupportedLanguageEnum, nullable=False)
    title = Column(Text, nullable=False)
    
    # 关系
    movie = relationship("Movie", back_populates="titles")
    
    def __repr__(self):
        return f"<MovieTitle {self.language}: {self.title}>"