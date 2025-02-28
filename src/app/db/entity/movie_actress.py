from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.db.entity.base import DBBaseModel

class MovieActress(DBBaseModel):
    __tablename__ = "movie_actresses"
    __table_args__ = {'extend_existing': True}
    
    movie_id = Column(Integer, ForeignKey('movies.id'), primary_key=True)
    actress_id = Column(Integer, ForeignKey('actresses.id'), primary_key=True)
    
    # 关系
    movie = relationship("app.db.entity.movie.Movie", back_populates="actress_associations")
    actress = relationship("app.db.entity.actress.Actress", back_populates="movie_associations")
    
    def __repr__(self):
        return f"<MovieActress movie_id={self.movie_id} actress_id={self.actress_id}>"
