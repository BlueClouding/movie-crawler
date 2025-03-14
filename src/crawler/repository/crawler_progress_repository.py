
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db_session
from app.repositories.base_repository import BaseRepositoryAsync
from common.db.entity.crawler import CrawlerProgress

class CrawlerProgressRepository(BaseRepositoryAsync[CrawlerProgress, int]):
    def __init__(self, db: AsyncSession = Depends(get_db_session)):
        super().__init__(db)

    async def create(self, CrawlerProgress):
        # add() 方法是同步的，不需要 await
        self.db.add(CrawlerProgress)
        # commit() 和 refresh() 是异步的，需要 await
        await self.db.commit()
        await self.db.refresh(CrawlerProgress)
        return CrawlerProgress

    async def update_status(self, CrawlerProgress):
        self.db.add(CrawlerProgress)
        await self.db.commit()
        await self.db.refresh(CrawlerProgress)