from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.db.entity.base import DBBaseModel

class MovieGenre(DBBaseModel):
    __tablename__ = "movie_genres"
    __table_args__ = {'extend_existing': True}
    
    movie_id = Column(Integer, ForeignKey('movies.id'), primary_key=True)
    genre_id = Column(Integer, ForeignKey('genres.id'), primary_key=True)
    
    # 关系
    movie = relationship("app.db.entity.movie.Movie", back_populates="genre_associations")
    genre = relationship("app.db.entity.genre.Genre", back_populates="movie_associations")
    
    def __repr__(self):
        return f"<MovieGenre movie_id={self.movie_id} genre_id={self.genre_id}>"
