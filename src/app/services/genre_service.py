from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from models import Genre, GenreName, SupportedLanguage, Movie
from .base_service import BaseService

class GenreService(BaseService[Genre]):
    def __init__(self, db: Session):
        super().__init__(db, Genre)
    
    def search_by_name(self, name: str, language: SupportedLanguage = None, skip: int = 0, limit: int = 20) -> List[Genre]:
        query = self.db.query(Genre).join(GenreName)
        
        if language:
            query = query.filter(GenreName.language == language)
        
        query = query.filter(GenreName.name.ilike(f"%{name}%"))
        return query.offset(skip).limit(limit).all()
    
    def add_name(self, genre_id: int, name: str, language: SupportedLanguage) -> Optional[GenreName]:
        genre = self.get_by_id(genre_id)
        if not genre:
            return None
        
        genre_name = GenreName(genre_id=genre_id, name=name, language=language)
        self.db.add(genre_name)
        self.db.commit()
        self.db.refresh(genre_name)
        return genre_name
    
    def get_movies_by_genre(self, genre_id: int, skip: int = 0, limit: int = 20) -> List[Movie]:
        genre = self.get_by_id(genre_id)
        if not genre:
            return []
        
        return self.db.query(Movie)\
            .join(Movie.genres)\
            .filter(Genre.id == genre_id)\
            .offset(skip).limit(limit).all()