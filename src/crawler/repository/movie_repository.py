from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from common.db.entity.movie import Movie
from app.repositories.base_repository import BaseRepositoryAsync
from app.config.database import get_db_session
from fastapi import Depends
from common.db.entity.movie import MovieStatus
from sqlalchemy import update
from typing import List, Dict, Any

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

    async def saveOrUpdate(self, movie_details: List[Movie], session: AsyncSession = None) -> bool:
        """Save or update movie details to the database.
        
        Args:       
            movie_details: List of Movie objects to save or update
            session: SQLAlchemy session to use
            
        Returns:
            bool: True if all operations were successful, False otherwise
        """ 
        if not movie_details:
            return True  # 如果没有电影需要处理，直接返回true
            
        success_count = 0
        total_count = len(movie_details)
        
        # 使用提供的会话或实例的默认会话
        use_session = session if session is not None else self.db
        
        # 处理每个电影
        for movie_detail in movie_details:
            try:
                # 首先检查电影是否已存在
                result = await use_session.execute(
                    select(Movie).where(Movie.code == movie_detail.code)
                )
                existing_movie = result.scalar_one_or_none()

                if existing_movie:
                    # 更新现有电影
                    try:
                        # 使用ID更新电影
                        await use_session.execute(
                            update(Movie)
                            .where(Movie.id == existing_movie.id)
                            .values(**{k: v for k, v in vars(movie_detail).items() if not k.startswith('_')})
                        )
                        success_count += 1
                    except Exception as update_error:
                        self._logger.error(f"Error updating movie {movie_detail.code}: {str(update_error)}")
                        # 继续处理下一个电影
                        continue
                else:
                    # 添加新电影前处理JSON字段
                    try:
                        # 添加电影
                        use_session.add(movie_detail)
                    except Exception as add_error:
                        self._logger.error(f"Error adding new movie {movie_detail.code}: {str(add_error)}")
                        # 继续处理下一个电影
                        continue
                
                # 记录成功处理的电影
                success_count += 1
                
            except Exception as e:
                self._logger.error(f"Error processing movie {getattr(movie_detail, 'code', 'unknown')}: {str(e)}")
                # 继续处理下一个电影
                continue
        
        # 返回成功标志（如果至少有一个电影成功处理）
        self._logger.info(f"Successfully processed {success_count} out of {total_count} movies")
        return success_count > 0