from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Integer, Text, ForeignKey, ARRAY
from sqlalchemy.orm import relationship

from app.models.base import DBBaseModel
from app.models.enums import SupportedLanguageEnum
from app.models.movie import movie_genres

class Genre(DBBaseModel):
    __tablename__ = "genres"
    
    urls = Column(ARRAY(Text))
    
    # 关系
    names = relationship("GenreName", back_populates="genre", cascade="all, delete-orphan")
    movies = relationship("Movie", secondary=movie_genres, back_populates="genres")
    
    def __repr__(self):
        return f"<Genre {self.id}>"

class GenreName(DBBaseModel):
    __tablename__ = "genre_names"
    
    genre_id = Column(Integer, ForeignKey("genres.id"), nullable=False)
    language = Column(SupportedLanguageEnum, nullable=False)
    name = Column(Text, nullable=False)
    
    # 关系
    genre = relationship("Genre", back_populates="names")
    
    def __repr__(self):
        return f"<GenreName {self.language}: {self.name}>"
    

class GenreNameCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    genre_id: Optional[int] = None
    language: str
    name: str

class GenreCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    urls: List[str] = []
    names: List[GenreNameCreate] = []

class GenreUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    urls: Optional[List[str]] = None
    names: Optional[List[GenreNameCreate]] = None

class GenreNameResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    genre_id: int
    language: str
    name: str
    created_at: datetime

class GenreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    urls: List[str]
    created_at: datetime
    names: List[GenreNameResponse] = []

class GenreDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    urls: List[str]
    created_at: datetime
    names: List[GenreNameResponse] = []
    movies: List[dict] = []  # 或使用 MovieResponse 类型