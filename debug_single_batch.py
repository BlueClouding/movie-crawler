#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import asyncio
import logging
from datetime import datetime
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.common.utils.database_manager import DatabaseManager
from src.crawler.main_database_crawler import DirectMovieCrawler

# 设置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def debug_single_batch():
    """调试单批次爬取问题"""
    logger.info("开始调试单批次爬取...")
    
    # 创建数据库管理器和直接爬虫
    db_manager = DatabaseManager()
    direct_crawler = DirectMovieCrawler(language="ja")
    
    try:
        # 1. 获取待爬取的电影代码
        logger.info("正在获取待爬取的电影代码...")
        movie_codes = await db_manager.get_pending_movie_codes(limit=2)
        
        if not movie_codes:
            logger.warning("没有找到待爬取的电影")
            return
        
        logger.info(f"获取到电影代码: {movie_codes}")
        
        # 2. 更新状态为 processing
        logger.info("更新电影状态为 processing...")
        await db_manager.update_movie_status(movie_codes, 'processing')
        
        # 3. 尝试调用爬取方法
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"debug_crawl_{timestamp}.jsonl"
            
            logger.info(f"开始调用 crawl_movies_concurrent_tabs...")
            logger.info(f"参数: movie_codes={movie_codes}, output_file={output_file}, max_tabs=3")
            
            # 检查方法是否存在
            if hasattr(direct_crawler, 'crawl_movies_concurrent_tabs'):
                logger.info("crawl_movies_concurrent_tabs 方法存在")
            else:
                logger.error("crawl_movies_concurrent_tabs 方法不存在!")
                return
            
            # 调用方法
            crawl_results = direct_crawler.crawl_movies_concurrent_tabs(
                movie_codes=movie_codes,
                output_file=output_file,
                max_tabs=3
            )
            
            logger.info(f"爬取完成，结果: {crawl_results}")
            
            # 4. 根据结果更新状态
            if crawl_results['success']:
                logger.info(f"成功的电影: {crawl_results['success']}")
                await db_manager.update_movie_status(crawl_results['success'], 'completed')
            
            if crawl_results['failed']:
                logger.info(f"失败的电影: {crawl_results['failed']}")
                await db_manager.update_movie_status(crawl_results['failed'], 'failed')
            
            print(f"\n调试结果:")
            print(f"处理: {len(movie_codes)}")
            print(f"成功: {len(crawl_results['success'])}")
            print(f"失败: {len(crawl_results['failed'])}")
            
        except Exception as e:
            logger.error(f"调用 crawl_movies_concurrent_tabs 时发生错误: {e}", exc_info=True)
            # 重置状态
            await db_manager.update_movie_status(movie_codes, 'pending')
            
    except Exception as e:
        logger.error(f"调试过程中发生错误: {e}", exc_info=True)
    finally:
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(debug_single_batch())