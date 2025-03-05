#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
检查数据库中的电影数据
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from src.crawler.db.connection import get_db_connection
from src.app.config.settings import settings

def main():
    """主函数"""
    try:
        # 获取数据库连接
        conn = get_db_connection(settings.DATABASE_URL)
        
        # 创建会话
        with conn.connect() as session:
            # 查询电影数量
            result = session.execute(text('SELECT COUNT(*) FROM video_progress'))
            count = result.scalar()
            print(f'Total movies in database: {count}')
            
            # 查询最近添加的5条电影数据
            result = session.execute(text('SELECT id, code, title, url, genre_id, page_number, status FROM video_progress ORDER BY id DESC LIMIT 5'))
            rows = result.fetchall()
            
            print("\nRecent movies:")
            for row in rows:
                print(f"ID: {row.id}, Code: {row.code}, Title: {row.title}, URL: {row.url}, Genre: {row.genre_id}, Page: {row.page_number}, Status: {row.status}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        
if __name__ == '__main__':
    main()
