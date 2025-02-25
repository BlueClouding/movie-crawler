from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from models import DownloadUrl, Movie
from .base_service import BaseService

class DownloadUrlService(BaseService[DownloadUrl]):
    def __init__(self, db: Session):
        super().__init__(db, DownloadUrl)
    
    def get_by_movie_id(self, movie_id: int) -> List[DownloadUrl]:
        return self.db.query(DownloadUrl)\
            .filter(DownloadUrl.movie_id == movie_id)\
            .order_by(DownloadUrl.index)\
            .all()
    
    def add_to_movie(self, movie_id: int, url: str, name: str = None, host: str = None, index: int = 0) -> Optional[DownloadUrl]:
        # 检查电影是否存在
        movie = self.db.query(Movie).filter(Movie.id == movie_id).first()
        if not movie:
            return None
        
        download_url = DownloadUrl(
            movie_id=movie_id,
            url=url,
            name=name,
            host=host,
            index=index
        )
        
        self.db.add(download_url)
        self.db.commit()
        self.db.refresh(download_url)
        return download_url