
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db_session
from app.repositories.base_repository import BaseRepositoryAsync
from common.db.entity.crawler import CrawlerProgress

class CrawlerProgressRepository(BaseRepositoryAsync[CrawlerProgress, int]):
    def __init__(self, db: AsyncSession = Depends(get_db_session)):
        super().__init__(db)


    async def create(self, CrawlerProgress):
        await self.db.add(CrawlerProgress)
        await self.db.commit()
        await self.db.refresh(CrawlerProgress)
        return CrawlerProgress