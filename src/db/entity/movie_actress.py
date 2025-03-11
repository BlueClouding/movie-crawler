from sqlalchemy import Column, Integer

from src.db.entity.base import DBBaseModel

class MovieActress(DBBaseModel):
    __tablename__ = "movie_actresses"
    __table_args__ = {'extend_existing': True}
    
    movie_id = Column(Integer, primary_key=True)
    actress_id = Column(Integer, primary_key=True)
    
    def __repr__(self):
        return f"<MovieActress movie_id={self.movie_id} actress_id={self.actress_id}>"
