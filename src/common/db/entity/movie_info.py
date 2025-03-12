from sqlalchemy import Column, Integer, Text
from common.db.entity.base import DBBaseModel
from common.enums.enums import SupportedLanguage, SupportedLanguageEnum


class MovieTitle(DBBaseModel):
    __tablename__ = "movie_titles"
    __table_args__ = {'extend_existing': True}
    
    movie_id = Column(Integer, nullable=False)
    language = Column(SupportedLanguageEnum, nullable=False)
    title = Column(Text, nullable=False)
    
    def __repr__(self):
        return f"<MovieTitle {self.language}: {self.title}>"
