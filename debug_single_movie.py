#!/usr/bin/env python3
"""调试单个电影爬取问题"""

import sys
import logging
from pathlib import Path

# 添加路径
sys.path.append('src')
sys.path.append('.')

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_single_movie_crawl():
    """测试单个电影爬取"""
    try:
        from test_ja_only_536VOLA_001 import BatchMovieCrawler
        
        # 创建爬虫实例
        crawler = BatchMovieCrawler(language="ja")
        
        # 测试单个电影代码
        test_movie_code = "sone-717"
        logger.info(f"开始测试爬取电影: {test_movie_code}")
        
        # 使用单浏览器模式爬取
        results = crawler.crawl_movies_single_browser(
            movie_codes=[test_movie_code],
            output_file=f"debug_single_{test_movie_code}.jsonl"
        )
        
        logger.info(f"爬取结果: {results}")
        
        # 检查输出文件
        output_file = Path("test_536VOLA_data/crawl_results") / f"debug_single_{test_movie_code}.jsonl"
        if output_file.exists():
            logger.info(f"输出文件存在: {output_file}")
            with open(output_file, 'r', encoding='utf-8') as f:
                content = f.read()
                logger.info(f"文件内容长度: {len(content)}")
                if content:
                    logger.info(f"文件内容: {content[:500]}...")  # 只显示前500字符
                else:
                    logger.warning("文件内容为空")
        else:
            logger.error(f"输出文件不存在: {output_file}")
            
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_single_movie_crawl()