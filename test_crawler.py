#!/usr/bin/env python3
"""测试数据库集成爬虫的核心功能"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

# 直接导入需要的模块，避免复杂依赖
from src.common.utils.database_manager import DatabaseManager

async def test_database_operations():
    """测试数据库基本操作"""
    print("=== 测试数据库基本操作 ===")
    
    db = DatabaseManager()
    
    try:
        # 测试获取状态统计
        print("\n1. 获取电影状态统计...")
        status_counts = await db.get_movie_status_count()
        for status, count in status_counts.items():
            status_name = {
                'null': '未处理',
                'pending': '待爬取',
                'processing': '爬取中',
                'completed': '已完成',
                'failed': '失败'
            }.get(status, status)
            print(f"{status_name}: {count} 个")
        
        # 测试获取待爬取电影代码
        print("\n2. 获取待爬取电影代码...")
        movie_codes = await db.get_pending_movie_codes(limit=3)
        print(f"获取到 {len(movie_codes)} 个电影代码: {movie_codes}")
        
        if movie_codes:
            # 测试更新状态为processing
            print("\n3. 测试更新状态为processing...")
            success = await db.update_movie_status(movie_codes, 'processing')
            print(f"更新状态结果: {success}")
            
            # 再次查看状态统计
            print("\n4. 更新后的状态统计...")
            status_counts = await db.get_movie_status_count()
            for status, count in status_counts.items():
                status_name = {
                    'null': '未处理',
                    'pending': '待爬取',
                    'processing': '爬取中',
                    'completed': '已完成',
                    'failed': '失败'
                }.get(status, status)
                print(f"{status_name}: {count} 个")
            
            # 模拟爬取结果，部分成功部分失败
            if len(movie_codes) >= 2:
                success_codes = movie_codes[:1]  # 第一个成功
                failed_codes = movie_codes[1:]   # 其余失败
                
                print("\n5. 模拟爬取结果更新...")
                if success_codes:
                    await db.update_movie_status(success_codes, 'completed')
                    print(f"成功代码: {success_codes}")
                
                if failed_codes:
                    await db.update_movie_status(failed_codes, 'failed')
                    print(f"失败代码: {failed_codes}")
            else:
                # 只有一个代码，标记为完成
                await db.update_movie_status(movie_codes, 'completed')
                print(f"完成代码: {movie_codes}")
            
            # 最终状态统计
            print("\n6. 最终状态统计...")
            status_counts = await db.get_movie_status_count()
            for status, count in status_counts.items():
                status_name = {
                    'null': '未处理',
                    'pending': '待爬取',
                    'processing': '爬取中',
                    'completed': '已完成',
                    'failed': '失败'
                }.get(status, status)
                print(f"{status_name}: {count} 个")
        else:
            print("没有找到待爬取的电影")
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await db.close()
        print("\n测试完成")

if __name__ == "__main__":
    asyncio.run(test_database_operations())