from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import Column, Integer, Text

from src.db.entity.base import DBBaseModel
from app.db.entity.enums import SupportedLanguageEnum

class Actress(DBBaseModel):
    __tablename__ = "actresses"
    __table_args__ = {'extend_existing': True}
    
    def __repr__(self):
        return f"<Actress {self.id}>"

class ActressName(DBBaseModel):
    __tablename__ = "actress_names"
    __table_args__ = {'extend_existing': True}
    
    actress_id = Column(Integer, nullable=False)
    language = Column(SupportedLanguageEnum, nullable=False)
    name = Column(Text, nullable=False)
    
    def __repr__(self):
        return f"<ActressName {self.language}: {self.name}>"



