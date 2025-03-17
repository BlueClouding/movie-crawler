
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db_session
from app.repositories.base_repository import BaseRepositoryAsync
from common.db.entity.crawler import CrawlerProgress
from sqlalchemy import update

class CrawlerProgressRepository(BaseRepositoryAsync[CrawlerProgress, int]):
    def __init__(self, db: AsyncSession = Depends(get_db_session)):
        super().__init__(db)

    async def create(self, crawler_progress: CrawlerProgress):
        # add() 方法是同步的，不需要 await
        self.db.add(crawler_progress)
        # commit() 和 refresh() 是异步的，需要 await
        await self.db.commit()
        await self.db.refresh(crawler_progress)
        return crawler_progress

    async def update_status(self, crawler_progress: CrawlerProgress):
        """更新爬虫任务状态。
        
        Args:
            crawler_progress: 包含ID和状态的爬虫进度对象
        """
        try:
            # 检查会话状态
            if self.db.is_active:
                await self.db.execute(
                    update(CrawlerProgress)
                    .where(CrawlerProgress.id == crawler_progress.id)
                    .values(status=crawler_progress.status)
                )
                await self.db.commit()
                return crawler_progress
            else:
                # 如果会话不活跃，记录错误并返回
                print(f"会话不活跃，无法更新状态: {crawler_progress.id}")
                return None
        except Exception as e:
            # 只在事务活跃时尝试回滚
            if self.db.is_active:
                await self.db.rollback()
            print(f"更新状态时发生错误: {str(e)}")
            # 重新抛出异常，让调用者处理
            raise e