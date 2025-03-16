
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
        await self.db.execute(
            update(CrawlerProgress)
            .where(CrawlerProgress.id == crawler_progress.id)
            .values(status=crawler_progress.status)
        )
        await self.db.commit()
        await self.db.refresh(crawler_progress)