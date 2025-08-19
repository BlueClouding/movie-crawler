#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试URL构建和访问"""

import asyncio
import logging
from src.common.utils.database_manager import DatabaseManager
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_url_construction():
    """测试URL构建逻辑"""
    dm = DatabaseManager()
    try:
        async with dm.get_session() as session:
            # 获取前2个待爬取的电影
            result = await session.execute(
                text("SELECT link FROM movies WHERE miss_status IS NULL OR miss_status = 'pending' LIMIT 2")
            )
            links = [row[0] for row in result.fetchall()]
            
            print("数据库中的link字段:")
            for link in links:
                print(f"  原始link: {link}")
                
                # 提取电影代码
                movie_code = link.split('/')[-1]
                print(f"  提取的电影代码: {movie_code}")
                
                # 构建MissAV URL
                missav_url = f"https://missav.ai/ja/{movie_code}"
                print(f"  构建的MissAV URL: {missav_url}")
                print("  ---")
                
    finally:
        await dm.close()

if __name__ == '__main__':
    asyncio.run(test_url_construction())