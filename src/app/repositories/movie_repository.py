from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, join, outerjoin

from app.db.entity.enums import SupportedLanguage
from app.db.entity.movie import Movie
from app.db.entity.movie_actress import MovieActress
from app.db.entity.movie_genres import MovieGenre
from app.db.entity.movie_info import MovieTitle
from app.db.entity.actress import Actress, ActressName
from app.db.entity.genre import Genre, GenreName
from app.db.entity.download import Magnet, DownloadUrl, WatchUrl
from app.repositories.base_repository import BaseRepository

class MovieRepository(BaseRepository[Movie]):
    def __init__(self):
        super().__init__(Movie)
    
    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[Movie]:
        """根据影片代码获取影片"""
        result = await db.execute(select(Movie).filter(Movie.code == code))
        return result.scalars().first()
    
    async def get_with_titles(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100, language: SupportedLanguage = None
    ) -> List[Tuple[Movie, List[MovieTitle]]]:
        """获取影片列表，包含标题"""
        # 首先获取电影列表
        movie_query = select(Movie).order_by(Movie.release_date.desc()).offset(skip).limit(limit)
        movie_result = await db.execute(movie_query)
        movies = movie_result.scalars().all()
        
        # 为每个电影获取标题
        result = []
        for movie in movies:
            title_query = select(MovieTitle).filter(MovieTitle.movie_id == movie.id)
            if language:
                title_query = title_query.filter(MovieTitle.language == language)
            title_result = await db.execute(title_query)
            titles = title_result.scalars().all()
            result.append((movie, titles))
        
        return result
    
    async def search_by_title(
        self, db: AsyncSession, *, title: str, language: SupportedLanguage = None, skip: int = 0, limit: int = 100
    ) -> List[Movie]:
        """根据标题搜索影片"""
        query = select(Movie).join(MovieTitle, Movie.id == MovieTitle.movie_id)
        
        if language:
            query = query.filter(MovieTitle.language == language)
        
        query = query.filter(MovieTitle.title.ilike(f"%{title}%"))
        query = query.order_by(Movie.release_date.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_by_actress(
        self, db: AsyncSession, *, actress_id: int, skip: int = 0, limit: int = 100
    ) -> List[Movie]:
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
    
    async def get_movie_with_details(
        self, db: AsyncSession, *, movie_id: int, language: SupportedLanguage = None
    ) -> Dict[str, Any]:
        """获取电影详细信息，包括标题、演员、类型等"""
        # 获取电影基本信息
        movie_query = select(Movie).filter(Movie.id == movie_id)
        movie_result = await db.execute(movie_query)
        movie = movie_result.scalars().first()
        
        if not movie:
            return None
        
        # 获取电影标题
        title_query = select(MovieTitle).filter(MovieTitle.movie_id == movie_id)
        if language:
            title_query = title_query.filter(MovieTitle.language == language)
        title_result = await db.execute(title_query)
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
        actress_result = await db.execute(actress_query)
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
        genre_result = await db.execute(genre_query)
        genres = genre_result.all()
        
        # 获取磁力链接
        magnet_query = select(Magnet).filter(Magnet.movie_id == movie_id)
        magnet_result = await db.execute(magnet_query)
        magnets = magnet_result.scalars().all()
        
        # 获取下载链接
        download_query = select(DownloadUrl).filter(DownloadUrl.movie_id == movie_id).order_by(DownloadUrl.index)
        download_result = await db.execute(download_query)
        download_urls = download_result.scalars().all()
        
        # 获取观看链接
        watch_query = select(WatchUrl).filter(WatchUrl.movie_id == movie_id).order_by(WatchUrl.index)
        watch_result = await db.execute(watch_query)
        watch_urls = watch_result.scalars().all()
        
        # 构建结果
        return {
            "movie": movie,
            "titles": titles,
            "actresses": actresses,
            "genres": genres,
            "magnets": magnets,
            "download_urls": download_urls,
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