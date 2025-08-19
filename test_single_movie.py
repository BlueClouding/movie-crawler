#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
from pathlib import Path
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from test.test_drission_movie import MovieDetailCrawler
from loguru import logger

async def test_movie_code(movie_code):
    """测试单个电影代码"""
    logger.info(f"开始测试电影代码: {movie_code}")
    
    # 创建爬虫实例
    crawler = MovieDetailCrawler(language="ja")
    
    try:
        # 爬取电影信息
        movie_info = await crawler.crawl_movie_detail(movie_code)
        
        if movie_info:
            logger.info(f"✅ 成功爬取电影 {movie_code}")
            logger.info(f"  标题: {movie_info.get('title', 'N/A')}")
            logger.info(f"  时长: {movie_info.get('duration_seconds', 0)} 秒")
            logger.info(f"  发布日期: {movie_info.get('release_date', 'N/A')}")
            logger.info(f"  女优: {', '.join(movie_info.get('actresses', [])[:3])}")
            
            # 保存结果
            output_dir = Path("test_536VOLA_data")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{movie_code}_parsed.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(movie_info, f, ensure_ascii=False, indent=2)
            
            logger.info(f"  💾 结果已保存到: {output_file}")
            return True
        else:
            logger.error(f"❌ 未能获取电影 {movie_code} 的信息")
            return False
            
    except Exception as e:
        logger.error(f"❌ 爬取电影 {movie_code} 时发生错误: {str(e)}")
        return False
    finally:
        await crawler.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python test_single_movie.py <电影代码>")
        sys.exit(1)
    
    movie_code = sys.argv[1]
    success = asyncio.run(test_movie_code(movie_code))
    sys.exit(0 if success else 1)