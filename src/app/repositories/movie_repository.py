from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, join, outerjoin

from common.enums.enums import SupportedLanguage
from common.db.entity.movie import Movie
from common.db.entity.movie_actress import MovieActress
from common.db.entity.movie_genres import MovieGenre
from common.db.entity.movie_info import MovieTitle
from common.db.entity.actress import Actress, ActressName
from common.db.entity.genre import Genre, GenreName
from common.db.entity.download import Magnet, WatchUrl
from app.repositories.base_repository import BaseRepositoryAsync
from app.config.database import get_db_session
from fastapi import Depends

class MovieRepository(BaseRepositoryAsync[Movie, int]):
    def __init__(self, db: AsyncSession = Depends(get_db_session)):
        super().__init__(db)
    
    async def get_by_code(self, code: str) -> Optional[Movie]:
        """根据影片代码获取影片"""
        result = await self.db.execute(select(Movie).filter(Movie.code == code))
        return result.scalars().first()
    
    async def get_with_titles(
        self, skip: int = 0, limit: int = 100, language: SupportedLanguage = None
    ) -> List[Tuple[Movie, List[MovieTitle]]]:
        """获取影片列表，包含标题"""
        # 首先获取电影列表
        movie_query = select(Movie).order_by(Movie.release_date.desc()).offset(skip).limit(limit)
        movie_result = await self.db.execute(movie_query)
        movies = movie_result.scalars().all()
        
        # 为每个电影获取标题
        result = []
        for movie in movies:
            title_query = select(MovieTitle).filter(MovieTitle.movie_id == movie.id)
            if language:
                title_query = title_query.filter(MovieTitle.language == language)
            title_result = await self.db.execute(title_query)
            titles = title_result.scalars().all()
            result.append((movie, titles))
        
        return result
    
    async def search_by_title(
        self, title: str, language: SupportedLanguage = None, skip: int = 0, limit: int = 100
    ) -> List[Movie]:
        """根据标题搜索影片"""
        query = select(Movie).join(MovieTitle, Movie.id == MovieTitle.movie_id)
        
        if language:
            query = query.filter(MovieTitle.language == language)
        
        query = query.filter(MovieTitle.title.ilike(f"%{title}%"))
        query = query.order_by(Movie.release_date.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_by_actress(
        self, actress_id: int, skip: int = 0, limit: int = 100
    ) -> List[Movie]:
        query = (
            select(Movie)
            .join(MovieActress, Movie.id == MovieActress.movie_id)
            .filter(MovieActress.actress_id == actress_id)
            .order_by(Movie.release_date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_by_genre(
        self, genre_id: int, skip: int = 0, limit: int = 100
    ) -> List[Movie]:
        """获取特定类型的所有影片"""
        query = (
            select(Movie)
            .join(MovieGenre, Movie.id == MovieGenre.movie_id)
            .filter(MovieGenre.genre_id == genre_id)
            .order_by(Movie.release_date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_movie_with_details(
        self, movie_id: int, language: SupportedLanguage = None
    ) -> Dict[str, Any]:
        """获取电影详细信息，包括标题、演员、类型等"""
        # 获取电影基本信息
        movie_query = select(Movie).filter(Movie.id == movie_id)
        movie_result = await self.db.execute(movie_query)
        movie = movie_result.scalars().first()
        
        if not movie:
            return None
        
        # 获取电影标题
        title_query = select(MovieTitle).filter(MovieTitle.movie_id == movie_id)
        if language:
            title_query = title_query.filter(MovieTitle.language == language)
        title_result = await self.db.execute(title_query)
        titles = title_result.scalars().all()
        
        # 获取演员信息
        actress_query = (
            select(Actress, ActressName)
            .join(MovieActress, Actress.id == MovieActress.actress_id)
            .join(ActressName, Actress.id == ActressName.actress_id)
            .filter(MovieActress.movie_id == movie_id)
        )
        if language:
            actress_query = actress_query.filter(ActressName.language == language)
        actress_result = await self.db.execute(actress_query)
        actresses = actress_result.all()
        
        # 获取类型信息
        genre_query = (
            select(Genre, GenreName)
            .join(MovieGenre, Genre.id == MovieGenre.genre_id)
            .join(GenreName, Genre.id == GenreName.genre_id)
            .filter(MovieGenre.movie_id == movie_id)
        )
        if language:
            genre_query = genre_query.filter(GenreName.language == language)
        genre_result = await self.db.execute(genre_query)
        genres = genre_result.all()
        
        # 获取磁力链接
        magnet_query = select(Magnet).filter(Magnet.movie_id == movie_id)
        magnet_result = await self.db.execute(magnet_query)
        magnets = magnet_result.scalars().all()
        
        # 获取观看链接
        watch_query = select(WatchUrl).filter(WatchUrl.movie_id == movie_id).order_by(WatchUrl.index)
        watch_result = await self.db.execute(watch_query)
        watch_urls = watch_result.scalars().all()
        
        # 构建结果
        return {
            "movie": movie,
            "titles": titles,
            "actresses": actresses,
            "genres": genres,
            "magnets": magnets,
            "watch_urls": watch_urls
        }
    
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