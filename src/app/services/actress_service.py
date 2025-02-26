from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.actress import Actress, ActressName
from app.models.movie import Movie
from app.models.enums import SupportedLanguage
from app.repositories.actress_repository import ActressRepository
from app.repositories.movie_repository import MovieRepository
from .base_service import BaseService

class ActressService(BaseService[Actress]):
    def __init__(self, db: Session):
        super().__init__(db, Actress)
        self.actress_repository = ActressRepository()
        self.movie_repository = MovieRepository()  # 假设你有一个MovieRepository
    
    def search_by_name(self, name: str, language: SupportedLanguage = None, skip: int = 0, limit: int = 20) -> List[Actress]:
        """根据名字搜索演员"""
        return self.actress_repository.search_by_name(
            db=self.db, 
            name=name, 
            language=language, 
            skip=skip, 
            limit=limit
        )
    
    def add_name(self, actress_id: int, name: str, language: SupportedLanguage) -> Optional[ActressName]:
        """为演员添加新名称"""
        # 检查演员是否存在
        actress = self.actress_repository.get_by_id(db=self.db, id=actress_id)
        if not actress:
            return None
        
        # 创建新名称
        actress_name = ActressName(actress_id=actress_id, name=name, language=language)
        self.db.add(actress_name)
        self.db.commit()
        self.db.refresh(actress_name)
        return actress_name
    
    def get_movies_by_actress(self, actress_id: int, skip: int = 0, limit: int = 20) -> List[Movie]:
        """获取演员参演的电影"""
        # 检查演员是否存在
        actress = self.actress_repository.get_by_id(db=self.db, id=actress_id)
        if not actress:
            return []
        
        # 假设MovieRepository有一个get_by_actress方法
        return self.movie_repository.get_by_actress(
            db=self.db,
            actress_id=actress_id,
            skip=skip,
            limit=limit
        )
    
    def get_by_name(self, name: str, language: SupportedLanguage = None) -> Optional[Actress]:
        """根据名字获取演员"""
        return self.actress_repository.get_by_name(
            db=self.db,
            name=name,
            language=language
        )
    
    def create_with_names(self, names: List[Dict[str, Any]]) -> Actress:
        """创建演员及其多语言名称"""
        return self.actress_repository.create_with_names(
            db=self.db,
            names=names
        )
    
    def get_popular(self, skip: int = 0, limit: int = 20) -> List[Actress]:
        """获取最受欢迎的演员"""
        return self.actress_repository.get_popular(
            db=self.db,
            skip=skip,
            limit=limit
        )