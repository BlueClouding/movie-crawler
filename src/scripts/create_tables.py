#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
创建数据库表
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import logging
from sqlalchemy import text

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入数据库连接
from app.config.settings import settings
from app.config.database import engine

async def create_tables():
    """创建数据库表"""
    try:
        # 创建表的SQL语句 - 分开执行每个表的创建语句
        create_crawler_progress_sql = """
        CREATE TABLE IF NOT EXISTS public.crawler_progress (
            id SERIAL PRIMARY KEY,
            task_type VARCHAR(50) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending' NOT NULL,
            last_update TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        create_pages_progress_sql = """
        CREATE TABLE IF NOT EXISTS public.pages_progress (
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
        """
        
        create_video_progress_sql = """
        CREATE TABLE IF NOT EXISTS public.video_progress (
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
        """
        
        # 执行SQL创建表 - 分别执行每个表的创建语句
        async with engine.begin() as conn:
            logger.info("创建 crawler_progress 表")
            await conn.execute(text(create_crawler_progress_sql))
            
            logger.info("创建 pages_progress 表")
            await conn.execute(text(create_pages_progress_sql))
            
            logger.info("创建 video_progress 表")
            await conn.execute(text(create_video_progress_sql))
            
        logger.info("数据库表创建成功")
        
    except Exception as e:
        logger.error(f"创建数据库表时出错: {str(e)}")
        raise
    finally:
        # 关闭引擎
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_tables())
