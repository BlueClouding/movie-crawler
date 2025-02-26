from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import DBBaseModel
from app.models.enums import SupportedLanguageEnum
from app.models.movie import movie_actresses

class Actress(DBBaseModel):
    __tablename__ = "actresses"
    
    # 关系
    names = relationship("ActressName", back_populates="actress", cascade="all, delete-orphan")
    movies = relationship("Movie", secondary=movie_actresses, back_populates="actresses")
    
    def __repr__(self):
        return f"<Actress {self.id}>"

class ActressName(DBBaseModel):
    __tablename__ = "actress_names"
    
    actress_id = Column(Integer, ForeignKey("actresses.id"), nullable=False)
    language = Column(SupportedLanguageEnum, nullable=False)
    name = Column(Text, nullable=False)
    
    # 关系
    actress = relationship("Actress", back_populates="names")
    
    def __repr__(self):
        return f"<ActressName {self.language}: {self.name}>"
    

class ActressNameCreate(BaseModel):
    actress_id: Optional[int] = None
    language: str
    name: str
    
    class Config:
        from_attributes = True

class ActressCreate(BaseModel):
    names: List[ActressNameCreate] = []
    
    class Config:
        from_attributes = True

class ActressUpdate(BaseModel):
    names: Optional[List[ActressNameCreate]] = None
    
    class Config:
        from_attributes = True

class ActressNameResponse(BaseModel):
    id: int
    actress_id: int
    language: str
    name: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ActressResponse(BaseModel):
    id: int
    created_at: datetime
    names: List[ActressNameResponse] = []
    
    class Config:
        from_attributes = True

class ActressDetailResponse(BaseModel):
    id: int
    created_at: datetime
    names: List[ActressNameResponse] = []
    movies: List[dict] = []  # 或者使用专门的 MovieResponse 类
    
    class Config:
        from_attributes = True