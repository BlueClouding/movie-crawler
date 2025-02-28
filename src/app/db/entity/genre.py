from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, Text, ForeignKey, ARRAY
from sqlalchemy.orm import relationship, backref

from app.db.entity.base import DBBaseModel
from app.db.entity.enums import SupportedLanguageEnum

class Genre(DBBaseModel):
    __tablename__ = "genres"
    __table_args__ = {'extend_existing': True}
    
    urls = Column(ARRAY(Text), default=list)
    
    # Define relationship only on this side with backref
    names = relationship(
        "app.db.entity.genre.GenreName",
        backref=backref("genre"), # This creates the reverse relationship
        cascade="all, delete-orphan"
    )
    movie_associations = relationship(
        "app.db.entity.movie_genres.MovieGenre", 
        back_populates="genre", 
        cascade="all, delete-orphan"
    )
    
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
    
    # Remove this relationship completely
    # genre = relationship("app.db.entity.genre.Genre", back_populates="names")
    
    def __repr__(self):
        return f"<GenreName {self.language}: {self.name}>"