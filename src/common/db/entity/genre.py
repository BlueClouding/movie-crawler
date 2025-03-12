from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, Text, ARRAY
from common.db.entity.base import DBBaseModel
from common.enums.enums import SupportedLanguageEnum

class Genre(DBBaseModel):
    __tablename__ = "genres"
    __table_args__ = {'extend_existing': True}
    
    urls = Column(ARRAY(Text), default=list)
    code = Column(Text, nullable=True)  # 添加code字段，对应URL的最后一个路径部分
    
    def __repr__(self):
        return f"<Genre {self.id}: {self.code}>"

class GenreName(DBBaseModel):
    __tablename__ = "genre_names"
    __table_args__ = {'extend_existing': True}
    
    genre_id = Column(Integer, nullable=False)
    language = Column(SupportedLanguageEnum, nullable=False)
    name = Column(Text, nullable=False)
    
    def __repr__(self):
        return f"<GenreName {self.language}: {self.name}>"