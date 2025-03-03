from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, Text, ARRAY

from app.db.entity.base import DBBaseModel
from app.db.entity.enums import SupportedLanguageEnum

class Genre(DBBaseModel):
    __tablename__ = "genres"
    __table_args__ = {'extend_existing': True}
    
    urls = Column(ARRAY(Text), default=list)
    
    def __repr__(self):
        return f"<Genre {self.id}>"

class GenreName(DBBaseModel):
    __tablename__ = "genre_names"
    __table_args__ = {'extend_existing': True}
    
    genre_id = Column(Integer, nullable=False)
    language = Column(SupportedLanguageEnum, nullable=False)
    name = Column(Text, nullable=False)
    
    def __repr__(self):
        return f"<GenreName {self.language}: {self.name}>"