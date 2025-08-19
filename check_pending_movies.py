#!/usr/bin/env python3
"""检查数据库中的待爬取电影"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent / "src"))

from common.utils.database_manager import DatabaseManager

async def check_pending_movies():
    """检查待爬取的电影代码"""
    db = DatabaseManager()
    
    try:
        # 获取5个待爬取的电影代码
        codes = await db.get_pending_movie_codes(5)
        print(f"待爬取电影代码: {codes}")
        print(f"数量: {len(codes) if codes else 0}")
        
        # 获取状态统计
        status_counts = await db.get_movie_status_count()
        print(f"状态统计: {status_counts}")
        
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(check_pending_movies())