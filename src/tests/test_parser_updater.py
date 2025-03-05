#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试脚本，用于分析保存的HTML内容并更新解析器
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from bs4 import BeautifulSoup

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 导入解析器
from src.crawler.parsers.genre_parser import GenreParser
from src.crawler.parsers.movie_parser import MovieParser

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def analyze_genres_html(html_path, base_url='http://123av.com', language='ja'):
    """
    分析类型页面的HTML内容，测试并更新GenreParser
    
    Args:
        html_path: HTML文件路径
        base_url: 基础URL
        language: 语言代码
    """
    try:
        if not os.path.exists(html_path):
            logger.error(f"HTML file not found: {html_path}")
            return
        
        logger.info(f"Analyzing genres HTML: {html_path}")
        
        # 读取HTML内容
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 使用BeautifulSoup分析HTML结构
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 尝试不同的选择器，找出最适合的
        selectors = [
            '.genre-list a', '.category-list a', '.genres a', '.tags a', 
            '.genre-item a', '.genre-box a', '.genre-section a', '.category a',
            '.tag-cloud a', 'ul.genres li a', 'div.genres a', '.genre-tag a',
            '.genre-link', 'a[href*="/genre/"]', 'a[href*="/genres/"]', 
            'a[href*="/category/"]'
        ]
        
        best_selector = None
        max_items = 0
        
        for selector in selectors:
            items = soup.select(selector)
            if items:
                logger.info(f"Selector '{selector}' found {len(items)} items")
                
                # 输出前3个项目的信息
                for i, item in enumerate(items[:3]):
                    text = item.get_text(strip=True)
                    href = item.get('href', '')
                    logger.info(f"  - Item {i+1}: Text='{text}', Href='{href}'")
                
                if len(items) > max_items:
                    max_items = len(items)
                    best_selector = selector
        
        if best_selector:
            logger.info(f"Best selector: '{best_selector}' with {max_items} items")
            
            # 使用GenreParser测试解析
            parser = GenreParser(language)
            genres = parser.parse_genres_page(html_content, base_url)
            
            logger.info(f"GenreParser found {len(genres)} genres")
            
            # 输出前5个解析结果
            for i, genre in enumerate(genres[:5]):
                logger.info(f"  - Genre {i+1}: {genre}")
            
            # 如果解析结果为空，但我们找到了项目，则建议更新解析器
            if len(genres) == 0 and max_items > 0:
                logger.info("Suggesting updates to GenreParser...")
                
                # 输出建议的选择器代码
                logger.info("Suggested code for GenreParser.parse_genres_page:")
                logger.info(f"""
# Try different selectors for genre items
selectors = [
    '{best_selector}',  # This is the best selector found
    '.genre-list a',
    '.category-list a',
    '.genres a',
    '.tags a',
    '.genre-item a'
]
                """)
        else:
            logger.warning("No suitable selector found")
        
    except Exception as e:
        logger.error(f"Error analyzing genres HTML: {str(e)}")

def analyze_movie_html(html_path, base_url='http://123av.com', language='ja'):
    """
    分析电影详情页面的HTML内容，测试并更新MovieParser
    
    Args:
        html_path: HTML文件路径
        base_url: 基础URL
        language: 语言代码
    """
    try:
        if not os.path.exists(html_path):
            logger.error(f"HTML file not found: {html_path}")
            return
        
        logger.info(f"Analyzing movie HTML: {html_path}")
        
        # 读取HTML内容
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 使用BeautifulSoup分析HTML结构
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 尝试查找电影标题
        title_selectors = [
            'h1.title', '.movie-title', '.video-title', 
            'h1', 'h2.title', '.title h1', '.title h2'
        ]
        
        logger.info("Looking for movie title...")
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                logger.info(f"Found title with selector '{selector}': '{title_elem.get_text(strip=True)}'")
                break
        
        # 尝试查找封面图片
        cover_selectors = [
            '.cover img', '.poster img', '.movie-cover img', 
            '.video-cover img', '.thumbnail img'
        ]
        
        logger.info("Looking for cover image...")
        for selector in cover_selectors:
            cover_elem = soup.select_one(selector)
            if cover_elem:
                src = cover_elem.get('src', '')
                logger.info(f"Found cover image with selector '{selector}': '{src}'")
                break
        
        # 尝试查找电影信息
        info_selectors = [
            '.movie-info', '.video-info', '.info-box', 
            '.details', '.movie-details', '.video-details'
        ]
        
        logger.info("Looking for movie information...")
        for selector in info_selectors:
            info_elem = soup.select_one(selector)
            if info_elem:
                logger.info(f"Found info box with selector '{selector}'")
                
                # 查找信息项
                info_items = info_elem.find_all(['p', 'div', 'li'])
                for item in info_items[:5]:
                    logger.info(f"  - Info item: '{item.get_text(strip=True)}'")
                break
        
        # 使用MovieParser测试解析
        parser = MovieParser(language)
        movie_details = parser.parse_movie_page(html_content, html_path)
        
        logger.info("MovieParser results:")
        for key, value in movie_details.items():
            if isinstance(value, list) and len(value) > 3:
                logger.info(f"  - {key}: {value[:3]} ... (and {len(value)-3} more)")
            else:
                logger.info(f"  - {key}: {value}")
        
    except Exception as e:
        logger.error(f"Error analyzing movie HTML: {str(e)}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Analyze HTML content and update parsers')
    parser.add_argument('--html-dir', type=str, default='src/tests/html_data', help='HTML data directory')
    parser.add_argument('--base-url', type=str, default='http://123av.com', help='Base URL')
    parser.add_argument('--language', type=str, default='ja', help='Language code')
    args = parser.parse_args()
    
    # 检查HTML数据目录
    if not os.path.exists(args.html_dir):
        logger.error(f"HTML data directory not found: {args.html_dir}")
        return
    
    # 分析类型页面
    genres_html_path = os.path.join(args.html_dir, 'genres.html')
    if os.path.exists(genres_html_path):
        analyze_genres_html(genres_html_path, args.base_url, args.language)
    else:
        logger.warning(f"Genres HTML file not found: {genres_html_path}")
    
    # 分析电影详情页面
    for filename in os.listdir(args.html_dir):
        if filename.startswith('movie_') and filename.endswith('.html'):
            movie_html_path = os.path.join(args.html_dir, filename)
            analyze_movie_html(movie_html_path, args.base_url, args.language)

if __name__ == '__main__':
    main()
