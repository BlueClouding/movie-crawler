from sqlalchemy import Column, Integer, Text, ForeignKey, ARRAY
from sqlalchemy.orm import relationship

from database.models.base import BaseModel
from database.models.enums import SupportedLanguageEnum
from database.models.movie import movie_genres

class Genre(BaseModel):
    __tablename__ = "genres"
    
    urls = Column(ARRAY(Text))
    
    # 关系
    names = relationship("GenreName", back_populates="genre", cascade="all, delete-orphan")
    movies = relationship("Movie", secondary=movie_genres, back_populates="genres")
    
    def __repr__(self):
        return f"<Genre {self.id}>"

class GenreName(BaseModel):
    __tablename__ = "genre_names"
    
    genre_id = Column(Integer, ForeignKey("genres.id"), nullable=False)
    language = Column(SupportedLanguageEnum, nullable=False)
    name = Column(Text, nullable=False)
    
    # 关系
    genre = relationship("Genre", back_populates="names")
    
    def __repr__(self):
        return f"<GenreName {self.language}: {self.name}>"