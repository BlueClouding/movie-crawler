from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.db.entity.base import DBBaseModel
from app.db.entity.enums import SupportedLanguageEnum
from db.entity import movie_actress

class Actress(DBBaseModel):
    __tablename__ = "actresses"
    __table_args__ = {'extend_existing': True}
    
    # 关系
    names = relationship("ActressName", back_populates="actress", cascade="all, delete-orphan")
    movie_associations = relationship("MovieActress", back_populates="actress", cascade="all, delete-orphan")
    
    # 方便访问的属性
    @property
    def movies(self):
        return [association.movie for association in self.movie_associations]
    
    def __repr__(self):
        return f"<Actress {self.id}>"

class ActressName(DBBaseModel):
    __tablename__ = "actress_names"
    __table_args__ = {'extend_existing': True}
    
    actress_id = Column(Integer, ForeignKey("actresses.id"), nullable=False)
    language = Column(SupportedLanguageEnum, nullable=False)
    name = Column(Text, nullable=False)
    
    # 关系
    actress = relationship("Actress", back_populates="names")
    
    def __repr__(self):
        return f"<ActressName {self.language}: {self.name}>"



