from sqlalchemy import Column, Integer, Text, ForeignKey, Date
from sqlalchemy.orm import relationship

from database.models.base import BaseModel

class Magnet(BaseModel):
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

class DownloadUrl(BaseModel):
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

class WatchUrl(BaseModel):
    __tablename__ = "watch_urls"
    
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    url = Column(Text, nullable=False)
    name = Column(Text)
    index = Column(Integer, nullable=False)
    
    # 关系
    movie = relationship("Movie", back_populates="watch_urls")
    
    def __repr__(self):
        return f"<WatchUrl {self.id}>"