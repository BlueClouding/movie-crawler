from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def clear_all_tables(session: AsyncSession):
    """Clear crawler progress data."""
    try:
        async with session.begin():
            # Delete data in dependency order
            await session.execute(text("DELETE FROM video_progress"))
            await session.execute(text("DELETE FROM pages_progress"))
            await session.execute(text("DELETE FROM crawler_progress"))
            
            # Reset sequences
            await session.execute(text("ALTER SEQUENCE video_progress_id_seq RESTART WITH 1"))
            await session.execute(text("ALTER SEQUENCE pages_progress_id_seq RESTART WITH 1"))
            await session.execute(text("ALTER SEQUENCE crawler_progress_id_seq RESTART WITH 1"))
    except Exception as e:
        raise e
