from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Integer, Text, ForeignKey, ARRAY
from sqlalchemy.orm import relationship

from db.entity import movie_genres
from db.entity.base import DBBaseModel
from db.entity.enums import SupportedLanguageEnum


class Genre(DBBaseModel):
    __tablename__ = "genres"
    __table_args__ = {'extend_existing': True}
    
    urls = Column(ARRAY(Text), default=list)
    
    # 关系
    names = relationship("GenreName", back_populates="genre", cascade="all, delete-orphan")
    movie_associations = relationship("MovieGenre", back_populates="genre", cascade="all, delete-orphan")
    
    # 方便访问的属性
    @property
    def movies(self):
        return [association.movie for association in self.movie_associations]
    
    def __repr__(self):
        return f"<Genre {self.id}>"

class GenreName(DBBaseModel):
    __tablename__ = "genre_names"
    __table_args__ = {'extend_existing': True}
    
    genre_id = Column(Integer, ForeignKey("genres.id"), nullable=False)
    language = Column(SupportedLanguageEnum, nullable=False)
    name = Column(Text, nullable=False)
    
    # 关系
    genre = relationship("Genre", back_populates="names")
    
    def __repr__(self):
        return f"<GenreName {self.language}: {self.name}>"
