from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.actress_repository import ActressRepository
from app.repositories.movie_repository import MovieRepository
from crawler.core.actress_processor import Actress
from db.entity.actress import ActressName
from db.entity.enums import SupportedLanguage
from db.entity.movie import Movie
from .base_service import BaseService

class ActressService(BaseService[Actress]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Actress)  # Note: I switched the order to match your BaseService
        self.actress_repository = ActressRepository()
        self.movie_repository = MovieRepository()
    
    async def search_by_name(self, name: str, language: SupportedLanguage = None, skip: int = 0, limit: int = 20) -> List[Actress]:
        """根据名字搜索演员"""
        return await self.actress_repository.search_by_name(
            db=self.db, 
            name=name, 
            language=language, 
            skip=skip, 
            limit=limit
        )
    
    async def add_name(self, actress_id: int, name: str, language: SupportedLanguage) -> Optional[ActressName]:
        """为演员添加新名称"""
        # 检查演员是否存在
        actress = await self.actress_repository.get(db=self.db, id=actress_id)
        if not actress:
            return None
        
        # 创建新名称
        actress_name = ActressName(actress_id=actress_id, name=name, language=language)
        self.db.add(actress_name)
        await self.db.commit()
        await self.db.refresh(actress_name)
        return actress_name
    
    async def get_movies_by_actress(self, actress_id: int, skip: int = 0, limit: int = 20) -> List[Movie]:
        """获取演员参演的电影"""
        # 检查演员是否存在
        actress = await self.actress_repository.get(db=self.db, id=actress_id)
        if not actress:
            return []
        
        return await self.movie_repository.get_by_actress(
            db=self.db,
            actress_id=actress_id,
            skip=skip,
            limit=limit
        )
    
    async def get_by_name(self, name: str, language: SupportedLanguage = None) -> Optional[Actress]:
        """根据名字获取演员"""
        return await self.actress_repository.get_by_name(
            db=self.db,
            name=name,
            language=language
        )
    
    async def create_with_names(self, names: List[Dict[str, Any]]) -> Actress:
        """创建演员及其多语言名称"""
        return await self.actress_repository.create_with_names(
            db=self.db,
            names=names
        )
    
    async def get_popular(self, skip: int = 0, limit: int = 20) -> List[Actress]:
        """获取最受欢迎的演员"""
        return await self.actress_repository.get_popular(
            db=self.db,
            skip=skip,
            limit=limit
        )