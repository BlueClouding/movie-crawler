#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.crawler.main_database_crawler import DirectMovieCrawler
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_direct_crawler():
    """测试DirectMovieCrawler的crawl_movies_concurrent_tabs方法"""
    try:
        logger.info("开始测试DirectMovieCrawler...")
        
        # 创建爬虫实例
        crawler = DirectMovieCrawler(language="ja")
        logger.info("DirectMovieCrawler实例创建成功")
        
        # 测试电影代码
        test_codes = ["HZHB-004", "VERO-085"]
        output_file = "test_direct_crawler_results.jsonl"
        
        logger.info(f"开始爬取测试电影: {test_codes}")
        
        # 调用爬取方法
        results = crawler.crawl_movies_concurrent_tabs(
            movie_codes=test_codes,
            output_file=output_file,
            max_tabs=2
        )
        
        logger.info(f"爬取完成，结果: {results}")
        
        return results
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    results = test_direct_crawler()
    if results:
        print("\n测试成功!")
        print(f"成功: {len(results.get('success', []))}")
        print(f"失败: {len(results.get('failed', []))}")
    else:
        print("\n测试失败!")
        sys.exit(1)