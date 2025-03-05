#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试脚本，用于测试GenreProcessor的功能
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
from src.crawler.core.genre_processor import GenreProcessor
from src.crawler.utils.progress_manager import DBProgressManager
from src.crawler.db.connection import get_db_connection
from src.app.config.settings import settings

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockProgressManager:
    """模拟进度管理器，用于测试"""
    
    def __init__(self):
        self.progress = {}
        self.movies = []
        
    async def get_genre_progress(self, genre_id, code=None):
        """获取类型进度
        
        Args:
            genre_id: 类型ID
            code: 类型代码（可选）
        
        Returns:
            int: 当前进度页码
        """
        # 在测试中，我们只使用 genre_id 来获取进度
        return self.progress.get(genre_id, 0)
        
    async def update_genre_progress(self, genre_id, page, total_pages, code=None):
        """更新类型进度
        
        Args:
            genre_id: 类型ID
            page: 当前页码
            total_pages: 总页数
            code: 类型代码（可选）
        
        Returns:
            bool: 是否成功
        """
        # 在测试中，我们只使用 genre_id 来更新进度
        self.progress[genre_id] = page
        logger.info(f"Updated genre {genre_id} progress: {page}/{total_pages}")
        return True
        
    async def save_movie(self, movie):
        """保存电影数据"""
        self.movies.append(movie)
        return True

async def test_genre_processor(base_url='http://123av.com', language='ja', max_genres=2, max_pages=3):
    """
    测试GenreProcessor的功能
    
    Args:
        base_url: 基础URL
        language: 语言代码
        max_genres: 最大类型数
        max_pages: 每个类型最大页数
    """
    try:
        logger.info(f"Testing genre processor with base_url={base_url}, language={language}")
        
        # 创建GenreProcessor
        processor = GenreProcessor(base_url, language)
        
        # 设置限制
        processor._max_genres = max_genres
        processor._max_pages = max_pages
        
        # 创建模拟进度管理器
        progress_manager = MockProgressManager()
        
        # 处理类型
        logger.info("Processing genres...")
        result = await processor.process_genres(progress_manager)
        
        logger.info(f"Genre processing result: {result}")
        logger.info(f"Progress: {progress_manager.progress}")
        
        # 输出收集到的电影数据
        logger.info(f"Collected {len(progress_manager.movies)} movies")
        for i, movie in enumerate(progress_manager.movies[:5]):
            logger.info(f"Movie {i+1}: {movie}")
        
    except Exception as e:
        logger.error(f"Error testing genre processor: {str(e)}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Test genre processor')
    
    parser.add_argument('--base-url',
                       type=str,
                       default='http://123av.com',
                       help='Base URL for the website')
                       
    parser.add_argument('--language',
                       type=str,
                       default='ja',
                       choices=['en', 'ja', 'zh'],
                       help='Language code')
                       
    parser.add_argument('--max-genres',
                       type=int,
                       default=2,
                       help='Maximum number of genres to process')
                       
    parser.add_argument('--max-pages',
                       type=int,
                       default=3,
                       help='Maximum number of pages per genre')
    
    args = parser.parse_args()
    
    # 运行测试
    asyncio.run(test_genre_processor(
        args.base_url, 
        args.language,
        args.max_genres,
        args.max_pages
    ))

if __name__ == '__main__':
    main()
