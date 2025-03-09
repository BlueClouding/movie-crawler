#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
初始化数据库，创建所有必要的表
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入所有实体类，确保它们被注册到SQLAlchemy的元数据中
from app.config.settings import settings
from app.config.database import Base
from app.db.entity.base import DBBaseModel
from app.db.entity.crawler import CrawlerProgress, PagesProgress, VideoProgress
from app.db.entity.movie import Movie
from app.db.entity.actress import Actress
from app.db.entity.genre import Genre
from app.db.entity.movie_actress import MovieActress
from app.db.entity.movie_genres import MovieGenre
from app.db.entity.movie_info import MovieTitle

async def init_db():
    """初始化数据库，创建所有表"""
    try:
        # 创建异步引擎
        engine = create_async_engine(settings.DATABASE_URL)
        
        # 创建所有表
        async with engine.begin() as conn:
            # 删除所有表（如果存在）- 谨慎使用！
            # await conn.run_sync(Base.metadata.drop_all)
            
            # 创建所有表
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("数据库表创建成功")
        
        # 关闭引擎
        await engine.dispose()
        
    except Exception as e:
        logger.error(f"初始化数据库时出错: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(init_db())
