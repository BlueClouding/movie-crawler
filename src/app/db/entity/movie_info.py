from sqlalchemy import Column, ForeignKey, Integer, Text
from app.db.entity.base import DBBaseModel
from app.db.entity.enums import SupportedLanguageEnum
from sqlalchemy.orm import relationship


class MovieTitle(DBBaseModel):
    __tablename__ = "movie_titles"
    __table_args__ = {'extend_existing': True}
    
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    language = Column(SupportedLanguageEnum, nullable=False)
    title = Column(Text, nullable=False)
    
    # 关系
    movie = relationship("app.db.entity.movie.Movie", back_populates="titles")
    
    def __repr__(self):
        return f"<MovieTitle {self.language}: {self.title}>"
