#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试脚本，用于测试整个爬虫的功能
"""

import os
import sys
import time
import logging
import argparse
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 导入爬虫组件
from src.crawler.core.crawler_manager import CrawlerManager
from src.crawler.db.connection import get_db_connection, DBConnection
from src.crawler.utils.progress_manager import DBProgressManager
from src.app.config.settings import settings

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_crawler(base_url='http://123av.com', language='ja', threads=3, output_dir='./images', 
                     max_genres=5, max_pages=2):
    """
    测试爬虫的功能
    
    Args:
        base_url: 基础URL
        language: 语言代码
        threads: 线程数
        output_dir: 输出目录
        max_genres: 最大类型数
        max_pages: 每个类型最大页数
    """
    try:
        logger.info(f"Testing crawler with base_url={base_url}, language={language}, threads={threads}")
        
        # 获取数据库连接
        db_url = settings.DATABASE_URL
        db_connection = get_db_connection(db_url)
        await db_connection.initialize()
        
        # 创建任务ID
        task_id = int(time.time())
        logger.info(f"Created task ID: {task_id}")
        
        # 创建爬虫管理器
        crawler = CrawlerManager(
            base_url=base_url,
            task_id=task_id,
            language=language,
            threads=threads,
            output_dir=output_dir
        )
        
        # 初始化爬虫
        await crawler.initialize()
        
        # 限制爬取的类型数量和页数
        crawler._genre_processor._max_genres = max_genres
        crawler._genre_processor._max_pages = max_pages
        
        # 启动爬虫
        logger.info("Starting crawler...")
        await crawler.start()
        
        # 等待一段时间
        logger.info("Crawler started, waiting for 30 seconds...")
        for i in range(30):
            logger.info(f"Elapsed: {i+1} seconds")
            await asyncio.sleep(1)
        
        # 停止爬虫
        logger.info("Stopping crawler...")
        await crawler.stop()
        
        logger.info("Crawler test completed")
        
    except Exception as e:
        logger.error(f"Error testing crawler: {str(e)}")
    finally:
        # 关闭数据库连接
        if 'db_connection' in locals():
            await db_connection.close()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Test crawler')
    
    parser.add_argument('--base-url',
                       type=str,
                       default='http://123av.com',
                       help='Base URL for the website')
                       
    parser.add_argument('--language',
                       type=str,
                       default='ja',
                       choices=['en', 'ja', 'zh'],
                       help='Language code')
                       
    parser.add_argument('--threads',
                       type=int,
                       default=3,
                       help='Number of threads')
                       
    parser.add_argument('--output-dir',
                       type=str,
                       default='./images',
                       help='Output directory for images')
                       
    parser.add_argument('--max-genres',
                       type=int,
                       default=5,
                       help='Maximum number of genres to crawl')
                       
    parser.add_argument('--max-pages',
                       type=int,
                       default=2,
                       help='Maximum number of pages per genre')
    
    args = parser.parse_args()
    
    # 运行测试
    asyncio.run(test_crawler(
        args.base_url, 
        args.language, 
        args.threads, 
        args.output_dir,
        args.max_genres,
        args.max_pages
    ))

if __name__ == '__main__':
    main()
