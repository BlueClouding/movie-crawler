from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy import Column, Integer, Text, DateTime

from common.db.entity.base import DBBaseModel
from common.enums.enums import SupportedLanguageEnum

class Actress(DBBaseModel):
    __tablename__ = "actresses"
    __table_args__ = {'extend_existing': True}
    
    name = Column(Text, nullable=False)
    language = Column(SupportedLanguageEnum, nullable=False)
    avatar = Column(Text, nullable=True)
    debut_year = Column(Integer, nullable=True)
    link = Column(Text, nullable=True)
    create_time = Column("create_time", DateTime, default=datetime.utcnow)
    update_time = Column("update_time", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Actress {self.id}: {self.name}>"

class ActressName(DBBaseModel):
    __tablename__ = "actress_names"
    __table_args__ = {'extend_existing': True}
    
    actress_id = Column(Integer, nullable=False)
    language = Column(SupportedLanguageEnum, nullable=False)
    name = Column(Text, nullable=False)
    
    def __repr__(self):
        return f"<ActressName {self.language}: {self.name}>"



