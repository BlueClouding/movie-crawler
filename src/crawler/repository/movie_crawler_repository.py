class MovieCrawlerRepository(BaseRepository[Movie, int]):
    def __init__(self, db: AsyncSession = Depends(get_db_session)):
        super().__init__(db)