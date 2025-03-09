#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Create database tables using asyncpg with explicit schema
"""

import asyncio
import logging
import asyncpg

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import database connection settings
from src.app.config.settings import settings

async def create_tables():
    """Create database tables using asyncpg with explicit schema"""
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
        
        # First, check if the schema exists
        schema_exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'public')"
        )
        
        if not schema_exists:
            logger.info("Creating public schema")
            await conn.execute("CREATE SCHEMA IF NOT EXISTS public")
        
        # Create tables
        logger.info("Creating tables...")
        
        # Create crawler_progress table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS crawler_progress (
            id SERIAL PRIMARY KEY,
            task_type VARCHAR(50) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending' NOT NULL,
            last_update TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """)
        logger.info("Created crawler_progress table")
        
        # Create pages_progress table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS pages_progress (
            id SERIAL PRIMARY KEY,
            crawler_progress_id INTEGER NOT NULL,
            relation_id INTEGER NOT NULL,
            page_type VARCHAR(50) NOT NULL,
            page_number INTEGER NOT NULL,
            total_pages INTEGER NOT NULL,
            status VARCHAR(20) DEFAULT 'pending' NOT NULL,
            total_items INTEGER NOT NULL,
            processed_items INTEGER DEFAULT 0,
            last_update TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """)
        logger.info("Created pages_progress table")
        
        # Create video_progress table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS video_progress (
            id SERIAL PRIMARY KEY,
            code VARCHAR(50) NOT NULL,
            crawler_progress_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            genre_id INTEGER NOT NULL,
            page_number INTEGER NOT NULL,
            title TEXT,
            status VARCHAR(20) DEFAULT 'pending' NOT NULL,
            retry_count INTEGER DEFAULT 0,
            last_error TEXT,
            detail_fetched BOOLEAN DEFAULT FALSE,
            movie_id INTEGER,
            page_progress_id INTEGER,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """)
        logger.info("Created video_progress table")
        
        # Close the connection
        await conn.close()
        logger.info("All tables created successfully")
        
    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(create_tables())
