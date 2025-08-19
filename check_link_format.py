import asyncio
import sys
import os
sys.path.append('src')
from common.utils.database_manager import DatabaseManager
from sqlalchemy import text

async def check_link_format():
    """检查数据库中link字段的实际格式"""
    dm = DatabaseManager()
    try:
        async with dm.get_session() as session:
            # 查询前10条记录的link字段
            result = await session.execute(text('SELECT link FROM movies LIMIT 10'))
            rows = result.fetchall()
            
            print('数据库中的link字段格式:')
            for i, row in enumerate(rows, 1):
                print(f'  {i}. {row[0]}')
                
    except Exception as e:
        print(f'查询失败: {e}')
    finally:
        await dm.close()

if __name__ == "__main__":
    asyncio.run(check_link_format())