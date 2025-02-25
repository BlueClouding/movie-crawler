from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from database.models.base import BaseModel
from database.models.enums import SupportedLanguageEnum
from database.models.movie import movie_actresses

class Actress(BaseModel):
    __tablename__ = "actresses"
    
    # 关系
    names = relationship("ActressName", back_populates="actress", cascade="all, delete-orphan")
    movies = relationship("Movie", secondary=movie_actresses, back_populates="actresses")
    
    def __repr__(self):
        return f"<Actress {self.id}>"

class ActressName(BaseModel):
    __tablename__ = "actress_names"
    
    actress_id = Column(Integer, ForeignKey("actresses.id"), nullable=False)
    language = Column(SupportedLanguageEnum, nullable=False)
    name = Column(Text, nullable=False)
    
    # 关系
    actress = relationship("Actress", back_populates="names")
    
    def __repr__(self):
        return f"<ActressName {self.language}: {self.name}>"