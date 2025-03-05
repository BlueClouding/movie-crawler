#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试脚本，用于测试类型解析器的功能
"""

import os
import sys
import logging
import argparse
import requests
from pathlib import Path
from bs4 import BeautifulSoup

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 导入解析器
from src.crawler.parsers.genre_parser import GenreParser

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_genre_parser(base_url='http://123av.com', language='ja'):
    """
    测试类型解析器的功能
    
    Args:
        base_url: 基础URL
        language: 语言代码
    """
    try:
        logger.info(f"Testing genre parser with base_url={base_url}, language={language}")
        
        # 创建解析器
        parser = GenreParser(language)
        
        # 获取类型页面
        url = f"{base_url}/{language}/genres"
        logger.info(f"Fetching genres from: {url}")
        
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            logger.error(f"Failed to fetch genres: HTTP {response.status_code}")
            return
        
        # 解析类型页面
        genres = parser.parse_genres_page(response.text, base_url)
        
        logger.info(f"Found {len(genres)} genres")
        
        # 输出前10个类型
        for i, genre in enumerate(genres[:10]):
            logger.info(f"Genre {i+1}: {genre}")
        
        # 测试获取类型详情页面
        if genres:
            genre = genres[0]
            logger.info(f"Testing genre detail page: {genre['name']}, URL: {genre['url']}")
            
            # 确保URL包含语言代码
            if f"/{language}/" not in genre['url']:
                import re
                if re.search(r'dm\d+/genres/', genre['url']):
                    # 提取域名部分
                    domain_part = genre['url'].split('//')[-1].split('/')[0]
                    # 提取路径部分
                    path_part = '/'.join(genre['url'].split('//')[-1].split('/')[1:])
                    
                    # 构建新的URL，包含语言代码
                    url = f"http://{domain_part}/{language}/{path_part}"
                    logger.info(f"Adjusted URL with language code: {url}")
                    genre['url'] = url
            
            # 获取类型详情页面
            response = requests.get(genre['url'], timeout=10)
            if response.status_code != 200:
                logger.error(f"Failed to fetch genre detail: HTTP {response.status_code}")
                return
            
            # 获取分页信息
            total_pages = parser.get_pagination_info(response.text)
            logger.info(f"Found {total_pages} pages for genre: {genre['name']}")
            
            # 测试获取第一页内容
            url = f"{genre['url']}?page=1"
            logger.info(f"Testing first page: {url}")
            
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                logger.error(f"Failed to fetch first page: HTTP {response.status_code}")
                return
            
            # 使用BeautifulSoup分析页面结构
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 尝试找出电影项目的选择器
            selectors = [
                '.movie-list .movie-item', '.movie-grid .movie-item', 
                '.movie-box', '.movie-card', '.video-item', 
                '.video-box', '.video-card', '.thumbnail',
                '.movie', '.video', '.item', '.box-item'
            ]
            
            best_selector = None
            max_items = 0
            
            for selector in selectors:
                items = soup.select(selector)
                if items:
                    logger.info(f"Selector '{selector}' found {len(items)} items")
                    
                    if len(items) > max_items:
                        max_items = len(items)
                        best_selector = selector
            
            if best_selector:
                logger.info(f"Best selector for movie items: '{best_selector}' with {max_items} items")
            else:
                logger.warning("No suitable selector found for movie items")
        
    except Exception as e:
        logger.error(f"Error testing genre parser: {str(e)}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Test genre parser')
    
    parser.add_argument('--base-url',
                       type=str,
                       default='http://123av.com',
                       help='Base URL for the website')
                       
    parser.add_argument('--language',
                       type=str,
                       default='ja',
                       choices=['en', 'ja', 'zh'],
                       help='Language code')
    
    args = parser.parse_args()
    
    test_genre_parser(args.base_url, args.language)

if __name__ == '__main__':
    main()
