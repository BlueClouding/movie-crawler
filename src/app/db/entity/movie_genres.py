from sqlalchemy import Column, Integer

from app.db.entity.base import DBBaseModel

class MovieGenre(DBBaseModel):
    __tablename__ = "movie_genres"
    __table_args__ = {'extend_existing': True}
    
    movie_id = Column(Integer, primary_key=True)
    genre_id = Column(Integer, primary_key=True)
    
    def __repr__(self):
        return f"<MovieGenre movie_id={self.movie_id} genre_id={self.genre_id}>"
