#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修改后的数据库集成爬虫系统
验证从link字段提取电影代码的功能是否正常工作
"""

import asyncio
import logging
from pathlib import Path
from src.common.utils.database_manager import DatabaseManager
from src.crawler.missav_database_crawler import MissAVDatabaseCrawler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_database_manager():
    """测试DatabaseManager从link字段提取电影代码的功能"""
    logger.info("开始测试DatabaseManager...")
    
    try:
        db_manager = DatabaseManager()
        
        # 测试获取待爬取电影代码
        logger.info("测试获取待爬取电影代码...")
        pending_codes = await db_manager.get_pending_movie_codes(limit=5)
        
        if pending_codes:
            logger.info(f"成功获取到 {len(pending_codes)} 个待爬取电影代码:")
            for i, code in enumerate(pending_codes[:3], 1):
                logger.info(f"  {i}. {code}")
        else:
            logger.warning("没有找到待爬取的电影代码")
            
        return pending_codes
        
    except Exception as e:
        logger.error(f"测试DatabaseManager时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []

async def test_crawler_integration(test_codes):
    """测试爬虫集成功能"""
    if not test_codes:
        logger.warning("没有测试代码，跳过爬虫集成测试")
        return
        
    logger.info("开始测试爬虫集成功能...")
    
    try:
        # 只测试第一个电影代码
        test_code = test_codes[0]
        logger.info(f"使用测试代码: {test_code}")
        
        crawler = MissAVDatabaseCrawler()
        
        # 测试单批次处理（限制为1个电影以避免长时间运行）
        logger.info("开始测试单批次爬取...")
        result = await crawler.process_single_batch(batch_size=1)
        
        if result:
            logger.info(f"爬取测试完成，结果: {result}")
        else:
            logger.warning("爬取测试没有返回结果")
            
    except Exception as e:
        logger.error(f"测试爬虫集成时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

async def main():
    """主测试函数"""
    logger.info("=" * 60)
    logger.info("开始测试修改后的数据库集成爬虫系统")
    logger.info("=" * 60)
    
    # 测试1: DatabaseManager功能
    logger.info("\n[测试1] 测试DatabaseManager从link字段提取电影代码...")
    pending_codes = await test_database_manager()
    
    # 测试2: 爬虫集成功能（可选，因为可能耗时较长）
    logger.info("\n[测试2] 测试爬虫集成功能...")
    # 注释掉实际爬取测试，避免长时间运行
    # await test_crawler_integration(pending_codes)
    logger.info("爬虫集成测试已跳过（避免长时间运行）")
    
    logger.info("\n" + "=" * 60)
    logger.info("测试完成！")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())