from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Integer, Text, ForeignKey, ARRAY
from sqlalchemy.orm import relationship

from app.db.entity.base import DBBaseModel
from app.db.entity.enums import SupportedLanguageEnum



class Genre(DBBaseModel):
    __tablename__ = "genres"
    __table_args__ = {'extend_existing': True}
    
    urls = Column(ARRAY(Text), default=list)
    
    # 关系
    names = relationship("app.db.entity.genre.GenreName", backref="genre", cascade="all, delete-orphan")
    movie_associations = relationship("app.db.entity.movie_genres.MovieGenre", back_populates="genre", cascade="all, delete-orphan")
    
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
    genre = relationship("app.db.entity.genre.Genre", backref="names", foreign_keys=[genre_id])
    
    def __repr__(self):
        return f"<GenreName {self.language}: {self.name}>"
