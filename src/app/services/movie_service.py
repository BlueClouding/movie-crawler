from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import date, timedelta
from models import Movie, MovieTitle, SupportedLanguage
from .base_service import BaseService

class MovieService(BaseService[Movie]):
    def __init__(self, db: Session):
        super().__init__(db, Movie)
    
    def get_by_code(self, code: str) -> Optional[Movie]:
        return self.db.query(Movie).filter(Movie.code == code).first()
    
    def search_by_title(self, title: str, language: SupportedLanguage = None, skip: int = 0, limit: int = 20) -> List[Movie]:
        query = self.db.query(Movie).join(MovieTitle)
        
        if language:
            query = query.filter(MovieTitle.language == language)
        
        query = query.filter(MovieTitle.title.ilike(f"%{title}%"))
        return query.offset(skip).limit(limit).all()
    
    def get_recent_releases(self, days: int = 30, skip: int = 0, limit: int = 20) -> List[Movie]:
        cutoff_date = date.today() - timedelta(days=days)
        return self.db.query(Movie)\
            .filter(Movie.release_date >= cutoff_date)\
            .order_by(Movie.release_date.desc())\
            .offset(skip).limit(limit).all()
    
    def get_popular_movies(self, skip: int = 0, limit: int = 20) -> List[Movie]:
        return self.db.query(Movie)\
            .order_by(Movie.likes.desc())\
            .offset(skip).limit(limit).all()
    
    def increment_likes(self, movie_id: int) -> Optional[Movie]:
        movie = self.get_by_id(movie_id)
        if not movie:
            return None
        
        movie.likes += 1
        self.db.commit()
        self.db.refresh(movie)
        return movie
    
    def add_title(self, movie_id: int, title: str, language: SupportedLanguage) -> Optional[MovieTitle]:
        movie = self.get_by_id(movie_id)
        if not movie:
            return None
        
        movie_title = MovieTitle(movie_id=movie_id, title=title, language=language)
        self.db.add(movie_title)
        self.db.commit()
        self.db.refresh(movie_title)
        return movie_title