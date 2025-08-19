#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
from src.common.utils.database_manager import DatabaseManager

async def check_movie_codes():
    """检查数据库中的电影代码"""
    dm = DatabaseManager()
    try:
        # 获取前10个待爬取的电影代码
        codes = await dm.get_pending_movie_codes(10)
        print("前10个待爬取电影代码:")
        print("-" * 40)
        for i, code in enumerate(codes, 1):
            print(f"{i:2d}. {code}")
        print("-" * 40)
        print(f"总共获取到 {len(codes)} 个电影代码")
        
        # 检查这些代码的格式
        print("\n代码格式分析:")
        for code in codes[:5]:  # 只分析前5个
            if '-' in code:
                parts = code.split('-')
                print(f"  {code} -> 前缀: {parts[0]}, 后缀: {'-'.join(parts[1:])}")
            else:
                print(f"  {code} -> 无分隔符")
                
    except Exception as e:
        print(f"错误: {e}")
    finally:
        await dm.close()

if __name__ == "__main__":
    asyncio.run(check_movie_codes())