"""Test module for movie detail processing."""

import asyncio
import logging
import os
from typing import Optional

from app.config import settings
from crawler.core.crawler_manager import CrawlerManager
from crawler.utils.progress_manager import DBProgressManager
from crawler.db.connection import get_db_session

logger = logging.getLogger(__name__)

async def test_movie_detail_processing(base_url: str = 'http://123av.com', 
                                     language: str = 'ja',
                                     threads: int = 1,
                                     output_dir: Optional[str] = None,
                                     test_movies_count: int = 5):
    """测试电影详情处理功能。
    
    Args:
        base_url: 基础URL
        language: 语言代码
        threads: 线程数
        output_dir: 输出目录
        test_movies_count: 测试电影数量
    """
    try:
        logger.info(f"Testing movie detail processing with {test_movies_count} movies")
        
        # 获取数据库会话
        session = await get_db_session()
        if not session:
            logger.error("Failed to get database session")
            return False
            
        # 创建爬虫管理器
        crawler = CrawlerManager(
            base_url=base_url,
            task_id=0,
            language=language,
            threads=threads,
            output_dir=output_dir
        )
        
        # 初始化爬虫
        if not await crawler.initialize():
            logger.error("Failed to initialize crawler")
            return False
        
        # 执行电影详情处理
        logger.info("Starting movie detail processing...")
        success = await crawler._detail_crawler.process_pending_movies()
        
        if success:
            logger.info("Successfully processed movie details")
        else:
            logger.error("Failed to process movie details")
        
        return success
        
    except Exception as e:
        logger.error(f"Error in movie detail processing test: {str(e)}")
        return False
    finally:
        if 'session' in locals():
            await session.close()

if __name__ == '__main__':
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)
    
    # 运行测试
    asyncio.run(test_movie_detail_processing(
        output_dir='./test_images',
        test_movies_count=3
    ))