#!/usr/bin/env python3
import asyncio
from sqlalchemy import text
from src.common.utils.database_manager import DatabaseManager

async def check_movie_links():
    dm = DatabaseManager()
    
    async with dm.get_session() as session:
        # 查询这两个电影代码对应的链接
        result = await session.execute(
            text("SELECT link FROM movies WHERE link LIKE '%jur-319%' OR link LIKE '%ipzz-546%' LIMIT 5")
        )
        rows = result.fetchall()
        
        print('找到的链接:')
        for r in rows:
            print(r[0])
            
        if not rows:
            print('没有找到匹配的链接')
            
        # 查看前几个待爬取的电影链接
        print('\n前5个待爬取的电影链接:')
        pending_result = await session.execute(
            text("SELECT link FROM movies WHERE miss_status IS NULL OR miss_status = 'pending' LIMIT 5")
        )
        pending_rows = pending_result.fetchall()
        
        for r in pending_rows:
            print(r[0])

if __name__ == '__main__':
    asyncio.run(check_movie_links())