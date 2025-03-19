from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db_session
from common.db.entity.crawler import VideoProgress
from app.repositories.base_repository import BaseRepositoryAsync
from common.db.entity.movie import Movie
from typing import List
from sqlalchemy.exc import IntegrityError

class MovieCrawlerRepository(BaseRepositoryAsync[VideoProgress, int]):
    def __init__(self, db: AsyncSession = Depends(get_db_session)):
        super().__init__(db)


    async def save_movies(self, movies: List[Movie]) -> int:
        saved_count = 0
        for movie in movies:
            try:
                self.db.add(movie)
                await self.db.flush()  # 使用 flush 可以在提交前捕获异常
                saved_count += 1
                # 每一条记录保存成功后立即提交，避免累积事务
                await self.db.commit()
            except IntegrityError as e:
                # 回滚当前事务，但不影响后续处理
                await self.db.rollback()
                if "unique constraint" in str(e).lower() or "唯一约束" in str(e).lower() or "duplicate key" in str(e).lower():
                    # 忽略唯一索引冲突错误，只记录日志
                    self._logger.info(f"忽略唯一索引冲突: {movie.code if hasattr(movie, 'code') else '未知'}")
                else:
                    # 其他完整性错误仍然记录
                    self._logger.error(f"数据完整性错误: {str(e)}")
            except Exception as e:
                self._logger.error(f"保存电影时出错: {str(e)}")
                # 回滚当前事务，但不影响后续处理
                await self.db.rollback()
        
        return saved_count