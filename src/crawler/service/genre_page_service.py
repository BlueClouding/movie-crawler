from sqlalchemy.ext.asyncio import AsyncSession
class GenrePageService:
    def __init__(self, db: AsyncSession):
        self._db = db
        