from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from models import Magnet, Movie
from .base_service import BaseService

class MagnetService(BaseService[Magnet]):
    def __init__(self, db: Session):
        super().__init__(db, Magnet)
    
    def get_by_movie_id(self, movie_id: int) -> List[Magnet]:
        return self.db.query(Magnet).filter(Magnet.movie_id == movie_id).all()
    
    def add_to_movie(self, movie_id: int, url: str, name: str = None, size: str = None, created_date = None) -> Optional[Magnet]:
        # 检查电影是否存在
        movie = self.db.query(Movie).filter(Movie.id == movie_id).first()
        if not movie:
            return None
        
        magnet = Magnet(
            movie_id=movie_id,
            url=url,
            name=name,
            size=size,
            created_date=created_date
        )
        
        self.db.add(magnet)
        self.db.commit()
        self.db.refresh(magnet)
        return magnet