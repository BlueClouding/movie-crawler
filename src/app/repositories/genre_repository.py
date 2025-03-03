from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.db.entity.enums import SupportedLanguage
from app.db.entity.genre import Genre, GenreName
from app.db.entity.movie_genres import MovieGenre
from app.db.entity.movie import Movie
from app.repositories.base_repository import BaseRepository

class GenreRepository(BaseRepository[Genre]):
    def __init__(self):
        super().__init__(Genre)
    
    async def get_by_name(
        self, db: AsyncSession, *, name: str, language: SupportedLanguage = None
    ) -> Optional[Genre]:
        """根据名称获取类型"""
        query = select(Genre).join(GenreName, Genre.id == GenreName.genre_id)
        
        if language:
            query = query.filter(GenreName.language == language)
        
        query = query.filter(GenreName.name == name)
        result = await db.execute(query)
        return result.scalars().first()
    
    async def search_by_name(
        self, db: AsyncSession, *, name: str, language: SupportedLanguage = None, skip: int = 0, limit: int = 100
    ) -> List[Genre]:
        """根据名称搜索类型"""
        query = select(Genre).join(GenreName, Genre.id == GenreName.genre_id)
        
        if language:
            query = query.filter(GenreName.language == language)
        
        query = query.filter(GenreName.name.ilike(f"%{name}%"))
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_with_names(
        self, db: AsyncSession, *, genre_id: int, language: SupportedLanguage = None
    ) -> Tuple[Genre, List[GenreName]]:
        """获取类型及其名称"""
        # 获取类型
        genre_query = select(Genre).filter(Genre.id == genre_id)
        genre_result = await db.execute(genre_query)
        genre = genre_result.scalars().first()
        
        if not genre:
            return None, []
        
        # 获取名称
        name_query = select(GenreName).filter(GenreName.genre_id == genre_id)
        if language:
            name_query = name_query.filter(GenreName.language == language)
        name_result = await db.execute(name_query)
        names = name_result.scalars().all()
        
        return genre, names
    
    async def get_genre_with_movies(
        self, db: AsyncSession, *, genre_id: int, skip: int = 0, limit: int = 100
    ) -> Dict[str, Any]:
        """获取类型及其相关电影"""
        # 获取类型
        genre, names = await self.get_with_names(db, genre_id=genre_id)
        
        if not genre:
            return None
        
        # 获取相关电影
        movie_query = (
            select(Movie)
            .join(MovieGenre, Movie.id == MovieGenre.movie_id)
            .filter(MovieGenre.genre_id == genre_id)
            .order_by(Movie.release_date.desc())
            .offset(skip)
            .limit(limit)
        )
        movie_result = await db.execute(movie_query)
        movies = movie_result.scalars().all()
        
        return {
            "genre": genre,
            "names": names,
            "movies": movies
        }
    
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
