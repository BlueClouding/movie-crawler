from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.repositories.base_repository import BaseRepository
from db.entity.enums import SupportedLanguage
from db.entity.movie import Movie, MovieTitle
from db.entity.movie_actress import MovieActress
from db.entity.movie_genres import MovieGenre

class MovieRepository(BaseRepository[Movie]):
    def __init__(self):
        super().__init__(Movie)
    
    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[Movie]:
        """根据影片代码获取影片"""
        result = await db.execute(select(Movie).filter(Movie.code == code))
        return result.scalars().first()
    
    async def get_with_titles(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100, language: SupportedLanguage = None
    ) -> List[Movie]:
        """获取影片列表，包含标题"""
        query = select(Movie).options(selectinload(Movie.titles))
        if language:
            query = query.join(MovieTitle).filter(MovieTitle.language == language)
        query = query.order_by(Movie.release_date.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def search_by_title(
        self, db: AsyncSession, *, title: str, language: SupportedLanguage = None, skip: int = 0, limit: int = 100
    ) -> List[Movie]:
        """根据标题搜索影片"""
        query = select(Movie).join(MovieTitle)
        
        if language:
            query = query.filter(MovieTitle.language == language)
        
        query = query.filter(MovieTitle.title.ilike(f"%{title}%"))
        query = query.order_by(Movie.release_date.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_by_actress(
        self, db: AsyncSession, *, actress_id: int, skip: int = 0, limit: int = 100
    ) -> List[Movie]:
        """获取演员的所有影片"""
        # 使用MovieActress类而不是关系属性
        from db.entity.movie_actress import MovieActress
        
        query = (
            select(Movie)
            .join(MovieActress, Movie.id == MovieActress.movie_id)
            .filter(MovieActress.actress_id == actress_id)
            .order_by(Movie.release_date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_by_genre(
        self, db: AsyncSession, *, genre_id: int, skip: int = 0, limit: int = 100
    ) -> List[Movie]:
        """获取特定类型的所有影片"""
        # 使用MovieGenre类而不是关系属性
        
        query = (
            select(Movie)
            .join(MovieGenre, Movie.id == MovieGenre.movie_id)
            .filter(MovieGenre.genre_id == genre_id)
            .order_by(Movie.release_date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()
    
    async def create_with_relations(
        self, 
        db: AsyncSession, 
        *, 
        movie_data: Dict[str, Any],
        titles: List[Dict[str, Any]] = None,
        actress_ids: List[int] = None,
        genre_ids: List[int] = None
    ) -> Movie:
        """创建影片及其关联数据"""
        # 创建影片
        db_movie = Movie(**movie_data)
        db.add(db_movie)
        await db.flush()  # 获取ID但不提交
        
        # 添加标题
        if titles:
            for title_data in titles:
                db_title = MovieTitle(**title_data, movie_id=db_movie.id)
                db.add(db_title)
        
        # 添加演员关联
        if actress_ids:
            for actress_id in actress_ids:
                db.add(MovieActress(movie_id=db_movie.id, actress_id=actress_id))
        
        # 添加类型关联
        if genre_ids:
            for genre_id in genre_ids:
                db.add(MovieGenre(movie_id=db_movie.id, genre_id=genre_id))
        
        await db.commit()
        await db.refresh(db_movie)
        return db_movie