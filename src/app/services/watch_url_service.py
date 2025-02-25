from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from models import WatchUrl, Movie
from .base_service import BaseService

class WatchUrlService(BaseService[WatchUrl]):
    def __init__(self, db: Session):
        super().__init__(db, WatchUrl)
    
    def get_by_movie_id(self, movie_id: int) -> List[WatchUrl]:
        return self.db.query(WatchUrl)\
            .filter(WatchUrl.movie_id == movie_id)\
            .order_by(WatchUrl.index)\
            .all()
    
    def add_to_movie(self, movie_id: int, url: str, name: str = None, index: int = 0) -> Optional[WatchUrl]:
        # 检查电影是否存在
        movie = self.db.query(Movie).filter(Movie.id == movie_id).first()
        if not movie:
            return None
        
        watch_url = WatchUrl(
            movie_id=movie_id,
            url=url,
            name=name,
            index=index
        )
        
        self.db.add(watch_url)
        self.db.commit()
        self.db.refresh(watch_url)
        return watch_url