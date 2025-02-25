from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from models import Actress, ActressName, SupportedLanguage, Movie
from .base_service import BaseService

class ActressService(BaseService[Actress]):
    def __init__(self, db: Session):
        super().__init__(db, Actress)
    
    def search_by_name(self, name: str, language: SupportedLanguage = None, skip: int = 0, limit: int = 20) -> List[Actress]:
        query = self.db.query(Actress).join(ActressName)
        
        if language:
            query = query.filter(ActressName.language == language)
        
        query = query.filter(ActressName.name.ilike(f"%{name}%"))
        return query.offset(skip).limit(limit).all()
    
    def add_name(self, actress_id: int, name: str, language: SupportedLanguage) -> Optional[ActressName]:
        actress = self.get_by_id(actress_id)
        if not actress:
            return None
        
        actress_name = ActressName(actress_id=actress_id, name=name, language=language)
        self.db.add(actress_name)
        self.db.commit()
        self.db.refresh(actress_name)
        return actress_name
    
    def get_movies_by_actress(self, actress_id: int, skip: int = 0, limit: int = 20) -> List[Movie]:
        actress = self.get_by_id(actress_id)
        if not actress:
            return []
        
        return self.db.query(Movie)\
            .join(Movie.actresses)\
            .filter(Actress.id == actress_id)\
            .offset(skip).limit(limit).all()