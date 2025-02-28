from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.db.entity.enums import SupportedLanguage
from app.db.entity.genre import Genre, GenreName
from app.db.entity.movie_genres import MovieGenre
from app.repositories.base_repository import BaseRepository

class GenreRepository(BaseRepository[Genre]):
    def __init__(self):
        super().__init__(Genre)
    
    async def get_by_name(
        self, db: AsyncSession, *, name: str, language: SupportedLanguage = None
    ) -> Optional[Genre]:
        """根据名称获取类型"""
        query = select(Genre).join(GenreName)
        
        if language:
            query = query.filter(GenreName.language == language)
        
        query = query.filter(GenreName.name == name)
        result = await db.execute(query)
        return result.scalars().first()
    
    async def search_by_name(
        self, db: AsyncSession, *, name: str, language: SupportedLanguage = None, skip: int = 0, limit: int = 100
    ) -> List[Genre]:
        """根据名称搜索类型"""
        query = select(Genre).join(GenreName)
        
        if language:
            query = query.filter(GenreName.language == language)
        
        query = query.filter(GenreName.name.ilike(f"%{name}%"))
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def create_with_names(
        self, db: AsyncSession, *, names: List[Dict[str, Any]], urls: List[str] = None
    ) -> Genre:
        """创建类型及其多语言名称"""
        # 创建类型
        db_genre = Genre(urls=urls or [])
        db.add(db_genre)
        await db.flush()  # 获取ID但不提交
        
        # 添加名称
        for name_data in names:
            db_name = GenreName(**name_data, genre_id=db_genre.id)
            db.add(db_name)
        
        await db.commit()
        await db.refresh(db_genre)
        return db_genre
    
    async def get_popular(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[Genre]:
        """获取最受欢迎的类型（根据影片数量）"""
        # 在方法内部导入以避免循环引用
        
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
        
        result = await db.execute(query)
        return result.scalars().all()
