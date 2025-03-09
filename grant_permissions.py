#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Grant permissions to the PostgreSQL user
"""

import asyncio
import logging
import asyncpg

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import database connection settings
from src.app.config.settings import settings

async def grant_permissions():
    """Grant permissions to the PostgreSQL user"""
    try:
        # Extract connection parameters from the DATABASE_URL
        # Format: postgresql+asyncpg://postgres:dqy@localhost:5432/movie_crawler
        db_url = settings.DATABASE_URL.replace('postgresql+asyncpg://', '')
        user_pass, host_db = db_url.split('@')
        user, password = user_pass.split(':')
        host_port, db_name = host_db.split('/')
        if ':' in host_port:
            host, port = host_port.split(':')
        else:
            host = host_port
            port = 5432
            
        logger.info(f"Connecting to database: {db_name} on {host}:{port} as {user}")
        
        # Connect to the database
        conn = await asyncpg.connect(
            user=user,
            password=password,
            database=db_name,
            host=host,
            port=port
        )
        
        # Set search_path to public explicitly
        await conn.execute("SET search_path TO public")
        
        # Grant permissions
        logger.info("Granting permissions...")
        
        # Grant permissions on crawler_progress table
        await conn.execute(f"GRANT ALL PRIVILEGES ON TABLE crawler_progress TO {user}")
        logger.info(f"Granted permissions on crawler_progress table to {user}")
        
        # Grant permissions on pages_progress table
        await conn.execute(f"GRANT ALL PRIVILEGES ON TABLE pages_progress TO {user}")
        logger.info(f"Granted permissions on pages_progress table to {user}")
        
        # Grant permissions on video_progress table
        await conn.execute(f"GRANT ALL PRIVILEGES ON TABLE video_progress TO {user}")
        logger.info(f"Granted permissions on video_progress table to {user}")
        
        # Grant permissions on sequences
        await conn.execute(f"GRANT ALL PRIVILEGES ON SEQUENCE crawler_progress_id_seq TO {user}")
        logger.info(f"Granted permissions on crawler_progress_id_seq to {user}")
        
        await conn.execute(f"GRANT ALL PRIVILEGES ON SEQUENCE pages_progress_id_seq TO {user}")
        logger.info(f"Granted permissions on pages_progress_id_seq to {user}")
        
        await conn.execute(f"GRANT ALL PRIVILEGES ON SEQUENCE video_progress_id_seq TO {user}")
        logger.info(f"Granted permissions on video_progress_id_seq to {user}")
        
        # Close the connection
        await conn.close()
        logger.info("All permissions granted successfully")
        
    except Exception as e:
        logger.error(f"Error granting permissions: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(grant_permissions())
