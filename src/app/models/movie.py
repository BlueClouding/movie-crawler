from datetime import timedelta, date
from typing import List, Optional
from sqlalchemy import Column, DateTime, String, Integer, Date, Text, Interval, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declared_attr
from pydantic import BaseModel, ConfigDict
from config.database import Base
from app.models.base import DBBaseModel
from app.models.enums import SupportedLanguageEnum


class MovieCreate(BaseModel):
    __allow_unmapped__ = True

    code: str
    duration: timedelta
    release_date: date
    cover_image_url: Optional[str] = None
    preview_video_url: Optional[str] = None
    likes: int = 0
    link: Optional[str] = None
    original_id: Optional[int] = None
    
class MovieUpdate(BaseModel):
    __allow_unmapped__ = True
    
    code: Optional[str] = None
    duration: Optional[timedelta] = None
    release_date: Optional[date] = None
    cover_image_url: Optional[str] = None
    preview_video_url: Optional[str] = None
    likes: Optional[int] = None
    link: Optional[str] = None
    original_id: Optional[int] = None


class MovieResponse(BaseModel):
    __allow_unmapped__ = True
    
    id: int
    code: str
    duration: timedelta
    release_date: date
    cover_image_url: Optional[str] = None
    preview_video_url: Optional[str] = None
    likes: int
    link: Optional[str] = None
    original_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)


class MovieDetailResponse(BaseModel):
    __allow_unmapped__ = True
    
    id: int
    code: str
    duration: timedelta
    release_date: date
    cover_image_url: Optional[str] = None
    preview_video_url: Optional[str] = None
    likes: int
    link: Optional[str] = None
    original_id: Optional[int] = None
    # 详细信息可能包含关联数据
    titles: List[dict] = []  # 或者使用专门的 MovieTitleResponse 类
    actresses: List[dict] = []  # 或者使用专门的 ActressResponse 类
    genres: List[dict] = []  # 或者使用专门的 GenreResponse 类
    magnets: List[dict] = []  # 或者使用专门的 MagnetResponse 类
    
    model_config = ConfigDict(from_attributes=True)


class MovieTitleCreate(BaseModel):
    __allow_unmapped__ = True
    
    movie_id: int
    language_id: int
    title: str

# 电影-演员关联表
movie_actresses = Table(
    'movie_actresses',
    Base.metadata,
    Column('movie_id', Integer, ForeignKey('movies.id'), primary_key=True),
    Column('actress_id', Integer, ForeignKey('actresses.id'), primary_key=True)
)

# 电影-类型关联表
movie_genres = Table(
    'movie_genres',
    Base.metadata,
    Column('movie_id', Integer, ForeignKey('movies.id'), primary_key=True),
    Column('genre_id', Integer, ForeignKey('genres.id'), primary_key=True)
)

class Movie(DBBaseModel):
    __tablename__ = "movies"
    
    code = Column(String(50), nullable=False, index=True)
    duration = Column(Interval, nullable=False)
    release_date = Column(Date, nullable=False)
    cover_image_url = Column(Text)
    preview_video_url = Column(Text)
    likes = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    link = Column(String(255))
    original_id = Column(Integer)
    
    # 关系
    titles = relationship("MovieTitle", back_populates="movie", cascade="all, delete-orphan")
    actresses = relationship("Actress", secondary=movie_actresses, back_populates="movies")
    genres = relationship("Genre", secondary=movie_genres, back_populates="movies")
    magnets = relationship("Magnet", back_populates="movie", cascade="all, delete-orphan")
    download_urls = relationship("DownloadUrl", back_populates="movie", cascade="all, delete-orphan")
    watch_urls = relationship("WatchUrl", back_populates="movie", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Movie {self.code}>"

class MovieTitle(DBBaseModel):
    __tablename__ = "movie_titles"
    
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    language = Column(SupportedLanguageEnum, nullable=False)
    title = Column(Text, nullable=False)
    
    # 关系
    movie = relationship("Movie", back_populates="titles")
    
    def __repr__(self):
        return f"<MovieTitle {self.language}: {self.title}>"
