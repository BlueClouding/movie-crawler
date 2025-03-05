"""Database connection module."""

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker

class DBConnection:
    """Database connection manager."""
    
    def __init__(self, db_url: str):
        """Initialize database connection.
        
        Args:
            db_url: Database URL
        """
        self._db_url = db_url
        self._engine: Optional[AsyncEngine] = None
        self._session_factory = None
        self._logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize database engine and session factory."""
        try:
            self._engine = create_async_engine(
                self._db_url,
                echo=False,
                pool_pre_ping=True,
                pool_recycle=3600
            )
            
            self._session_factory = sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            self._logger.info("Database connection initialized")
            
        except Exception as e:
            self._logger.error(f"Failed to initialize database connection: {str(e)}")
            raise
    
    async def get_session(self) -> AsyncSession:
        """Get a database session.
        
        Returns:
            AsyncSession: SQLAlchemy async session
        """
        if not self._session_factory:
            await self.initialize()
            
        return self._session_factory()
    
    async def close(self):
        """Close database connection."""
        if self._engine:
            await self._engine.dispose()
            self._logger.info("Database connection closed")


# Singleton instance
_db_connection: Optional[DBConnection] = None

def get_db_connection(db_url: str) -> DBConnection:
    """Get database connection singleton.
    
    Args:
        db_url: Database URL
        
    Returns:
        DBConnection: Database connection instance
    """
    global _db_connection
    if _db_connection is None:
        _db_connection = DBConnection(db_url)
    return _db_connection

async def get_db_session() -> AsyncSession:
    """Get a database session using configuration settings.
    
    Returns:
        AsyncSession: SQLAlchemy async session
    """
    try:
        from app.config.settings import settings
        
        # Get database URL from settings
        db_url = settings.DATABASE_URL
        if not db_url:
            raise ValueError("Database URL not configured")
            
        db_conn = get_db_connection(db_url)
        return await db_conn.get_session()
    except Exception as e:
        logging.error(f"Failed to get database session: {str(e)}")
        return None
