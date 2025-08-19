#!/usr/bin/env python3
"""重置处于 processing 状态的电影为 pending"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent / "src"))

from common.utils.database_manager import DatabaseManager
from sqlalchemy import text

async def reset_processing_movies():
    """重置处于 processing 状态的电影为 pending"""
    db = DatabaseManager()
    
    try:
        async with db.get_session() as session:
            # 更新处于 processing 状态的电影
            result = await session.execute(
                text("UPDATE movies SET miss_status = 'pending' WHERE miss_status = 'processing'")
            )
            await session.commit()
            
            print(f"已重置 {result.rowcount} 个处于 processing 状态的电影为 pending")
            
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(reset_processing_movies())