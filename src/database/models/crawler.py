from sqlalchemy import Column, String, Integer, Text, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.models.base import BaseModel

class CrawlerProgress(BaseModel):
    __tablename__ = "crawler_progress"
    
    task_type = Column(String(50), nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    last_update = Column(DateTime(timezone=True), server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 关系
    pages = relationship("PagesProgress", back_populates="crawler_progress", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<CrawlerProgress {self.task_type}: {self.status}>"

class PagesProgress(BaseModel):
    __tablename__ = "pages_progress"
    
    crawler_progress_id = Column(Integer, ForeignKey("crawler_progress.id"), nullable=False)
    relation_id = Column(Integer, nullable=False)
    page_type = Column(String(50), nullable=False)
    page_number = Column(Integer, nullable=False)
    total_pages = Column(Integer, nullable=False)
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    status = Column(String(20), default="pending", nullable=False)
    last_update = Column(DateTime(timezone=True), server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # 关系
    crawler_progress = relationship("CrawlerProgress", back_populates="pages")
    
    def __repr__(self):
        return f"<PagesProgress {self.page_type} {self.page_number}/{self.total_pages}>"

class VideoProgress(BaseModel):
    __tablename__ = "video_progress"
    
    code = Column(String(50), nullable=False)
    url = Column(Text, nullable=False)
    genre_id = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=False)
    title = Column(Text)
    status = Column(String(20), default="pending", nullable=False)
    retry_count = Column(Integer, default=0)
    last_error = Column(Text)
    detail_fetched = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    def __repr__(self):
        return f"<VideoProgress {self.code}: {self.status}>"