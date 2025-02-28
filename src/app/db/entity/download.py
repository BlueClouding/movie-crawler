from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Date
from sqlalchemy.orm import relationship

from app.db.entity.base import DBBaseModel


class Magnet(DBBaseModel):
    __tablename__ = "magnets"
    __table_args__ = {'extend_existing': True}
    
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    url = Column(Text, nullable=False)
    name = Column(Text)
    size = Column(Text)
    created_date = Column(String(50), nullable=False)
    
    # 关系
    movie = relationship("app.db.entity.movie.Movie", back_populates="magnets")
    
    def __repr__(self):
        return f"<Magnet {self.id}>"

class DownloadUrl(DBBaseModel):
    __tablename__ = "download_urls"
    __table_args__ = {'extend_existing': True}
    
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    url = Column(Text, nullable=False)
    name = Column(Text)
    host = Column(Text)
    index = Column(Integer, nullable=False)
    
    # 关系
    movie = relationship("app.db.entity.movie.Movie", back_populates="download_urls")
    
    def __repr__(self):
        return f"<DownloadUrl {self.id}>"

class WatchUrl(DBBaseModel):
    __tablename__ = "watch_urls"
    __table_args__ = {'extend_existing': True}
    
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    url = Column(Text, nullable=False)
    name = Column(Text)
    index = Column(Integer, nullable=False)
    
    # 关系
    movie = relationship("app.db.entity.movie.Movie", back_populates="watch_urls")
    
    def __repr__(self):
        return f"<WatchUrl {self.id}>"
