from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from app.repositories.base_repository import BaseRepositoryAsync
from app.config.database import get_db_session
from fastapi import Depends
from db.entity.genre import Genre, GenreName
from src.enums.enums import SupportedLanguage
from sqlalchemy.engine.result import Result

class GenreRepository(BaseRepositoryAsync[Genre, int]):
    def __init__(self, db: AsyncSession = Depends(get_db_session)):
        super().__init__(db)
    
    async def get_by_name(
        self, name: str, language: SupportedLanguage = None
    ) -> Optional[Genre]:
        """根据名称获取类型"""
        query = select(Genre).join(GenreName).where(
            GenreName.name == name,
            GenreName.language == language if language else True
        )
        result = await self.db.execute(query)
        return result.scalars().first()
        
    async def get_by_code(
        self, code: str
    ) -> Genre:
        """根据code获取类型
        
        Args:
            code: 类型代码
            
        Returns:
            Optional[Genre]: 找到的类型，如果没有找到则返回None
        """
        query = select(Genre).filter(Genre.code == code)
        result : Result = await self.db.execute(query)
        return result.scalars().first()
    
    async def search_by_name(
        self, name: str, language: SupportedLanguage = None, skip: int = 0, limit: int = 100
    ) -> List[Genre]:
        """根据名称搜索类型"""
        query = select(Genre).join(GenreName, Genre.id == GenreName.genre_id)
        
        if language:
            query = query.filter(GenreName.language == language)
        
        query = query.filter(GenreName.name.ilike(f"%{name}%"))
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_with_names(
        self, genre_id: int, language: SupportedLanguage = None
    ) -> Tuple[Genre, List[GenreName]]:
        """获取类型及其名称"""
        # 获取类型
        genre_query = select(Genre).filter(Genre.id == genre_id)
        genre_result = await self.db.execute(genre_query)
        genre = genre_result.scalars().first()
        
        if not genre:
            return None, []
        
        # 获取名称
        name_query = select(GenreName).filter(GenreName.genre_id == genre_id)
        if language:
            name_query = name_query.filter(GenreName.language == language)
        name_result = await self.db.execute(name_query)
        names = name_result.scalars().all()
        
        return genre, names
    
    async def get_genre_with_movies(
        self, genre_id: int, skip: int = 0, limit: int = 100
    ) -> List[Movie]:
        """获取类型及其相关电影"""
        # 获取类型
        genre, names = await self.get_with_names(genre_id=genre_id)
        
        if not genre:
            return []
        
        # 获取相关电影
        movie_query = (
            select(Movie)
            .join(MovieGenre, Movie.id == MovieGenre.movie_id)
            .filter(MovieGenre.genre_id == genre_id)
            .order_by(Movie.release_date.desc())
            .offset(skip)
            .limit(limit)
        )
        movie_result = await self.db.execute(movie_query)
        return movie_result.scalars().all()
    
    async def create_with_names(
        self, name: Dict[str, str], urls: List[str] = None, code: str = None
    ) -> Genre:
        """创建类型及其多语言名称
        
        Args:
            name: 多语言名称列表，每个元素包含name和language
            urls: URL列表
            code: 类型代码
            
        Returns:
            Genre: 创建的类型对象
        """
        # 创建类型
        db_genre = Genre(urls=urls or [], code=code)
        self.db.add(db_genre)
        await self.db.flush()  # 获取ID但不提交
        
        # 添加名称
        db_name = GenreName(language=name['language'], name=name['name'], genre_id=db_genre.id)
        self.db.add(db_name)
        
        await self.db.commit()
        await self.db.refresh(db_genre)
        return db_genre
    
    async def get_popular(
        self, skip: int = 0, limit: int = 100
    ) -> List[Genre]:
        """获取最受欢迎的类型（根据影片数量）"""
        # 创建子查询获取类型ID和影片数量
        subquery = (
            select(
                MovieGenre.genre_id,
                func.count(MovieGenre.movie_id).label("movie_count")
            )
            .group_by(MovieGenre.genre_id)
            .subquery()
        )
        
        # 查询类型并按影片数量排序
        query = (
            select(Genre)
            .join(
                subquery,
                Genre.id == subquery.c.genre_id
            )
            .order_by(subquery.c.movie_count.desc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()

    # get all genres
    async def get_all(self) -> List[Genre]:
        query = select(Genre)
        result = await self.db.execute(query)
        return result.scalars().all()
