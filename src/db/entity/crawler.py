from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime
from sqlalchemy.sql import func
from src.db.entity.base import DBBaseModel



class CrawlerProgress(DBBaseModel):
    __tablename__ = "crawler_progress"
    __table_args__ = {'extend_existing': True}
    
    task_type = Column(String(50), nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    last_update = Column(DateTime(timezone=True), server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    def __repr__(self):
        return f"<CrawlerProgress {self.task_type}: {self.status}>"

class PagesProgress(DBBaseModel):
    __tablename__ = "pages_progress"
    __table_args__ = {'extend_existing': True}
    
    crawler_progress_id = Column(Integer, nullable=False)
    relation_id = Column(Integer, nullable=False)
    page_type = Column(String(50), nullable=False)
    page_number = Column(Integer, nullable=False)
    total_pages = Column(Integer, nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    total_items = Column(Integer, nullable=True)
    last_update = Column(DateTime(timezone=True), server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    def __repr__(self):
        return f"<PagesProgress {self.page_type} {self.page_number}/{self.total_pages}>"

class VideoProgress(DBBaseModel):
    __tablename__ = "video_progress"
    __table_args__ = {'extend_existing': True}
    
    code = Column(String(50), nullable=False)
    crawler_progress_id = Column(Integer, nullable=False)
    url = Column(Text, nullable=False)
    genre_id = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=False)
    title = Column(Text)
    status = Column(String(20), default="pending", nullable=False)
    retry_count = Column(Integer, default=0)
    last_error = Column(Text)
    detail_fetched = Column(Boolean, default=False)
    movie_id = Column(Integer, nullable=True)  # 新增关联到Movie表的ID字段
    page_progress_id = Column(Integer, nullable=True)  # 新增关联到PagesProgress表的ID字段
    updated_at = Column(DateTime(timezone=True), server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    def __repr__(self):
        return f"<VideoProgress {self.code}: {self.status}>"

class PagesProgressCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    crawler_progress_id: Optional[int] = None
    relation_id: int
    page_type: str
    page_number: int
    total_pages: int
    total_items: int = 0
    processed_items: int = 0
    status: str = "pending"

class CrawlerProgressCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    task_type: str
    status: str = "pending"
    pages: List[PagesProgressCreate] = []

class VideoProgressCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    code: str
    url: str
    genre_id: int
    page_number: int
    title: Optional[str] = None
    status: str = "pending"
    retry_count: int = 0
    last_error: Optional[str] = None
    detail_fetched: bool = False

class PagesProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    crawler_progress_id: int
    relation_id: int
    page_type: str
    page_number: int
    total_pages: int
    total_items: int
    processed_items: int
    status: str
    last_update: datetime
    created_at: datetime

class CrawlerProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    task_type: str
    status: str
    last_update: datetime
    created_at: datetime
    pages: List[PagesProgressResponse] = []

class VideoProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    code: str
    url: str
    genre_id: int
    page_number: int
    title: Optional[str] = None
    status: str
    retry_count: int
    last_error: Optional[str] = None
    detail_fetched: bool
    updated_at: datetime
    created_at: datetime

class PagesProgressSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    page_type: str
    total_pages: int
    processed_pages: int
    total_items: int
    processed_items: int
    completion_percentage: float

class CrawlerProgressSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    task_id: str
    status: str
    progress: float
    total_urls: int
    processed_urls: int
    failed_urls: int
    created_at: datetime
    updated_at: datetime