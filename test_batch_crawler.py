#!/usr/bin/env python3
"""测试BatchMovieCrawler的基本功能"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from src.crawler.batch_movie_crawler import BatchMovieCrawler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_batch_crawler():
    """测试BatchMovieCrawler的基本功能"""
    logger.info("开始测试BatchMovieCrawler...")
    
    try:
        # 初始化爬虫
        crawler = BatchMovieCrawler(language='ja')
        
        # 测试爬取几个电影代码
        test_codes = ['sone-625', 'ipzz-620']
        
        logger.info(f"测试爬取电影代码: {test_codes}")
        
        # 执行爬取
        results = await crawler.crawl_movies(test_codes)
        
        logger.info(f"爬取结果: 成功 {results['success_count']} 个, 失败 {results['failed_count']} 个")
        
        if results['success_count'] > 0:
            logger.info("BatchMovieCrawler测试成功！")
            return True
        else:
            logger.error("BatchMovieCrawler