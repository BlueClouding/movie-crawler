from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db_session
from common.db.entity.crawler import PagesProgress
from sqlalchemy import select, update
from sqlalchemy.engine.result import Result
from app.repositories.base_repository import BaseRepositoryAsync
from pydantic import BaseModel
from crawler.models.update_progress import GenrePageProgressUpdate


class PageCrawlerRepository(BaseRepositoryAsync[PagesProgress, int]):
    def __init__(self, db: AsyncSession = Depends(get_db_session)):
        super().__init__(db)

    async def get_latest_page_by_genre_task(self, genre_id: int, task_id: int) -> int:
        result : Result = await self.db.execute(
            select(PagesProgress)
            .filter(
                PagesProgress.relation_id == genre_id,
                PagesProgress.page_type == 'genre',
                PagesProgress.crawler_progress_id == task_id
            )
            .order_by(PagesProgress.page_number.desc())
            .limit(1)
        )
        page_progress : PagesProgress = result.scalars().first()
        if page_progress:
            return page_progress.page_number
        else:
            return 0

    async def update_page_progress(self, page_progress_id: int, update_values: GenrePageProgressUpdate):
        await self.db.execute(
            update(PagesProgress)
            .where(PagesProgress.id == page_progress_id)
            .values(update_values.model_dump(exclude_none=True))
        )
        await self.db.commit()
        return page_progress_id

    async def create_genre_progress(self, page_progress: PagesProgress):
        self.db.add(page_progress)
        await self.db.commit()
        return page_progress.id

    #check if exist By relationIdAndPageNumber
    async def check_exist_by_relation_id_and_page_number(self, genre_id: int, page_number: int) -> bool:
        result : Result = await self.db.execute(
            select(PagesProgress)
            .filter(
                PagesProgress.relation_id == genre_id,
                PagesProgress.page_number == page_number
            )
            .limit(1)
        )
        return result.scalar() is not None