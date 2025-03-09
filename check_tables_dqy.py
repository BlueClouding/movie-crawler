#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Check all schemas and tables in the database
"""

import asyncio
import logging
import asyncpg

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import database connection settings
from src.app.config.settings import settings

async def check_all_schemas():
    """Check all schemas and tables in the database"""
    try:
        # Extract connection parameters from the DATABASE_URL
        # Format: postgresql+asyncpg://dqy:dqy@localhost:5432/movie_crawler
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
        
        # Check all schemas
        logger.info("Checking all schemas in the database")
        schemas = await conn.fetch("""
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
        """)
        
        if schemas:
            logger.info(f"Found {len(schemas)} schemas:")
            for schema in schemas:
                schema_name = schema['schema_name']
                logger.info(f"Schema: {schema_name}")
                
                # Check tables in this schema
                tables = await conn.fetch(f"""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = '{schema_name}' 
                AND table_type = 'BASE TABLE'
                """)
                
                if tables:
                    logger.info(f"  Found {len(tables)} tables in schema {schema_name}:")
                    for table in tables:
                        table_name = table['table_name']
                        logger.info(f"  - {table_name}")
                        
                        # Check if this is the crawler_progress table
                        if table_name == 'crawler_progress':
                            logger.info(f"    Found crawler_progress table in schema {schema_name}!")
                            
                            # Check columns in the crawler_progress table
                            columns = await conn.fetch(f"""
                            SELECT column_name, data_type 
                            FROM information_schema.columns 
                            WHERE table_schema = '{schema_name}' 
                            AND table_name = 'crawler_progress'
                            """)
                            
                            logger.info(f"    Columns in crawler_progress table:")
                            for column in columns:
                                logger.info(f"      {column['column_name']}: {column['data_type']}")
                else:
                    logger.info(f"  No tables found in schema {schema_name}")
        else:
            logger.info("No schemas found in the database")
                
        # Close the connection
        await conn.close()
        
    except Exception as e:
        logger.error(f"Error checking schemas: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(check_all_schemas())
