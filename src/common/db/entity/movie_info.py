from sqlalchemy import Column, Integer, Text, String, Date, ARRAY, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from common.db.entity.base import DBBaseModel
from common.enums.enums import SupportedLanguage, SupportedLanguageEnum


class MovieInfo(DBBaseModel):
    """
    电影详情实体类
    
    对应PostgreSQL中的movie_info表，存储电影的详细信息。
    """
    __tablename__ = "movie_info"
    __table_args__ = {'extend_existing': True}
    
    code = Column(String(255), nullable=False)
    movie_uuid = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    language = Column(String(10), nullable=False)
    title = Column(Text)
    description = Column(Text)
    tags = Column(ARRAY(String(255)))
    genres = Column(ARRAY(String(255)))
    director = Column(String(255))
    maker = Column(String(255))
    actresses = Column(ARRAY(Text))
    release_date = Column(Date)
    website_date = Column(Date)
    duration = Column(Integer)
    cover_url = Column(String(512))
    series = Column(Text)
    label = Column(String(255))
    m3u8_info = Column(ARRAY(Text))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = Column(String(255))
    
    def __repr__(self):
        return f"<MovieInfo {self.code}: {self.title}>"


class MovieTitle(DBBaseModel):
    """
    电影标题实体类
    
    存储不同语言版本的电影标题。
    """
    __tablename__ = "movie_titles"
    __table_args__ = {'extend_existing': True}
    
    movie_uuid = Column(UUID(as_uuid=True), ForeignKey("movie_info.movie_uuid"), nullable=False)
    language = Column(SupportedLanguageEnum, nullable=False)
    title = Column(Text, nullable=False)
    
    def __repr__(self):
        return f"<MovieTitle {self.language}: {self.title}>"
