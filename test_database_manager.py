#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import asyncio
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.common.utils.database_manager import DatabaseManager
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_database_manager():
    """测试DatabaseManager的get_pending_movie_codes方法"""
    db_manager = DatabaseManager()
    
    try:
        logger.info("开始测试DatabaseManager...")
        
        # 获取状态统计
        status_count = await db_manager.get_movie_status_count()
        logger.info(f"状态统计: {status_count}")
        
        # 获取待爬取的电影代码
        movie_codes = await db_manager.get_pending_movie_codes(limit=5)
        logger.info(f"获取到的电影代码: {movie_codes}")
        logger.info(f"电影代码数量: {len(movie_codes)}")
        
        if movie_codes:
            logger.info("成功获取到待爬取的电影代码")
            return movie_codes
        else:
            logger.warning("没有获取到待爬取的电影代码")
            return []
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}", exc_info=True)
        return None
    finally:
        await db_manager.close()

if __name__ == "__main__":
    results = asyncio.run(test_database_manager())
    if results:
        print(f"\n测试成功! 获取到 {len(results)} 个电影代码")
        for code in results:
            print(f"  - {code}")
    else:
        print("\n测试失败或没有获取到电影代码!")