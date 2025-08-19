#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from src.common.utils.database_manager import DatabaseManager

async def test_get_pending_codes():
    """测试获取待爬取电影代码"""
    db = DatabaseManager()
    try:
        print("正在获取待爬取的电影代码...")
        codes = await db.get_pending_movie_codes(5)
        print(f"获取到的电影代码: {codes}")
        print(f"代码数量: {len(codes) if codes else 0}")
        return codes
    except Exception as e:
        print(f"获取电影代码时出错: {e}")
        return None
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(test_get_pending_codes())