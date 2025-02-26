from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import Column, Integer, Text, ForeignKey, Date
from sqlalchemy.orm import relationship

from app.models.base import DBBaseModel

class Magnet(DBBaseModel):
    __tablename__ = "magnets"
    
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    url = Column(Text, nullable=False)
    name = Column(Text)
    size = Column(Text)
    created_date = Column(Date)
    
    # 关系
    movie = relationship("Movie", back_populates="magnets")
    
    def __repr__(self):
        return f"<Magnet {self.id}>"

class DownloadUrl(DBBaseModel):
    __tablename__ = "download_urls"
    
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    url = Column(Text, nullable=False)
    name = Column(Text)
    host = Column(Text)
    index = Column(Integer, nullable=False)
    
    # 关系
    movie = relationship("Movie", back_populates="download_urls")
    
    def __repr__(self):
        return f"<DownloadUrl {self.id}>"

class WatchUrl(DBBaseModel):
    __tablename__ = "watch_urls"
    
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    url = Column(Text, nullable=False)
    name = Column(Text)
    index = Column(Integer, nullable=False)
    
    # 关系
    movie = relationship("Movie", back_populates="watch_urls")
    
    def __repr__(self):
        return f"<WatchUrl {self.id}>"
    
class DownloadUrlResponse(BaseModel):
    id: int
    movie_id: int
    url: str
    source: Optional[str] = None
    created_at: datetime
    
    class Config:
        orm_mode = True

class WatchUrlResponse(BaseModel):
    id: int
    movie_id: int
    url: str
    source: Optional[str] = None
    created_at: datetime
    
    class Config:
        orm_mode = True

class MagnetResponse(BaseModel):
    id: int
    movie_id: int
    link: str
    name: Optional[str] = None
    size: Optional[str] = None
    share_date: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        orm_mode = True