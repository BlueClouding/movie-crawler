#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Check if tables exist in the database
"""

import asyncio
import logging
from sqlalchemy import text

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import database connection
from src.app.config.settings import settings
from src.app.config.database import engine

async def check_tables():
    """Check if tables exist in the database"""
    try:
        # Check if tables exist
        check_tables_sql = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE';
        """
        
        async with engine.begin() as conn:
            logger.info("Checking tables in the database")
            result = await conn.execute(text(check_tables_sql))
            tables = result.fetchall()
            
            if tables:
                logger.info(f"Found {len(tables)} tables:")
                for table in tables:
                    logger.info(f"- {table[0]}")
            else:
                logger.info("No tables found in the database")
                
    except Exception as e:
        logger.error(f"Error checking tables: {str(e)}")
        raise
    finally:
        # Close the engine
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_tables())
