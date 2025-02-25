from datetime import timedelta, date
from sqlalchemy import Column, DateTime, String, Integer, Date, Text, Interval, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declared_attr

from config.database import Base
from database.models.base import BaseModel
from database.models.enums import SupportedLanguageEnum


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

class Movie(BaseModel):
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

class MovieTitle(BaseModel):
    __tablename__ = "movie_titles"
    
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    language = Column(SupportedLanguageEnum, nullable=False)
    title = Column(Text, nullable=False)
    
    # 关系
    movie = relationship("Movie", back_populates="titles")
    
    def __repr__(self):
        return f"<MovieTitle {self.language}: {self.title}>"