from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, or_

from common.db.entity.movie import Movie
from common.db.entity.download import Magnet, DownloadUrl, WatchUrl
from app.repositories.base_repository import BaseRepositoryAsync
from app.config.database import get_db_session
from fastapi import Depends
from common.db.entity.movie import MovieStatus
from sqlalchemy import update

class MovieRepository(BaseRepositoryAsync[Movie, int]):
    # if insert session use it
    def __init__(self, db: AsyncSession = Depends(get_db_session)):
        super().__init__(db)
        # 添加logger属性
        import logging
        self._logger = logging.getLogger(__name__)


    # get status new movie with limit
    async def get_new_movies(self, limit: int = 100):
        """
        Get new movies with limit.
        
        Args:
            limit: Number of movies to retrieve
        
        Returns:
            List[Movie]: List of new movies
        """
        query = select(Movie).where(Movie.status == MovieStatus.NEW.value).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def saveOrUpdate(self, movie_details: Dict[str, Any]) -> bool:
        """Save or update movie details to the database.
        
        Args:   
            movie_details: Movie details dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """ 
        try:    
            # 确保db是一个有效的会话对象
            if not hasattr(self.db, 'execute') or not callable(self.db.execute):
                self._logger.error("Invalid database session object")
                return False
                
            # 直接执行数据库操作，不创建新事务
            # 首先检查电影是否已经存在（通过code或original_id）
            original_id = int(movie_details.get('id')) if movie_details.get('id') else None
            
            # 构建查询条件，检查code或original_id
            query_conditions = []
            if movie_details.get('code'):
                query_conditions.append(Movie.code == movie_details['code'])
            if original_id:
                query_conditions.append(Movie.original_id == original_id)
                
            # 如果没有有效的查询条件，返回失败
            if not query_conditions:
                self._logger.error("No valid identifier (code or original_id) provided for movie")
                return False
                
            # 使用OR连接多个条件
            result = await self.db.execute(
                select(Movie).where(or_(*query_conditions)))
            existing_movie = result.scalar_one_or_none()

            if existing_movie:
                # Update existing movie
                # 根据查询到的电影的ID来更新，而不是仅仅通过code
                await self.db.execute(
                    update(Movie)
                    .where(Movie.id == existing_movie.id)
                    .values(
                        title=movie_details.get('title'),
                        link=movie_details.get('url'),
                        cover_image_url=movie_details.get('cover_image_url'),
                        preview_video_url=movie_details.get('preview_video_url'),
                        thumbnail=movie_details.get('thumbnail'),
                        likes=movie_details.get('likes'),
                        original_id=int(movie_details.get('id')),
                        status=movie_details.get('status', MovieStatus.ONLINE.value),
                        code=movie_details.get('code'),
                        release_date=movie_details.get('release_date'),
                        duration=movie_details.get('duration'),
                        description=movie_details.get('description'),
                        updated_at=func.current_timestamp(),
                        tags=movie_details.get('tags'),
                        genres=movie_details.get('genres'),
                        director=movie_details.get('director'),
                        maker=movie_details.get('maker'),
                        actresses=movie_details.get('actresses'),
                    )
                )
            else:
                # Create new movie
                movie = Movie(
                    code=movie_details['code'],
                    title=movie_details.get('title'),
                    link=movie_details.get('url'),
                    cover_image_url=movie_details.get('cover_image_url'),
                    preview_video_url=movie_details.get('preview_video_url'),
                    thumbnail=movie_details.get('thumbnail'),
                    likes=movie_details.get('likes'),
                    original_id=int(movie_details.get('id')),
                    status=movie_details.get('status', MovieStatus.ONLINE.value),
                    release_date=movie_details.get('release_date'),
                    duration=movie_details.get('duration'),
                    description=movie_details.get('description'),
                    updated_at=func.current_timestamp(),
                    tags=movie_details.get('tags'),
                    genres=movie_details.get('genres'),
                    director=movie_details.get('director'),
                    maker=movie_details.get('maker'),
                    actresses=movie_details.get('actresses'),
                )
                # SQLAlchemy 2.0中，add方法不是异步的
                self.db.add(movie)
                
            # 不进行显式的提交，让外部事务管理器处理
            return True
        except Exception as e:
            self._logger.error(f"Error saving or updating movie: {str(e)}")
            # 不进行显式的回滚，让外部事务管理器处理
            return False