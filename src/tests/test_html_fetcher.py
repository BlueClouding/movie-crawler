#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试脚本，用于获取和保存网页HTML内容，以便于分析网页结构
"""

import os
import sys
import logging
import requests
import argparse
from pathlib import Path
from bs4 import BeautifulSoup

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def save_html(url, output_path):
    """
    获取并保存网页HTML内容
    
    Args:
        url: 网页URL
        output_path: 保存路径
    """
    try:
        logger.info(f"Fetching HTML from: {url}")
        
        # 创建session并设置headers
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        })
        
        # 获取网页内容
        response = session.get(url, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch HTML: HTTP {response.status_code}")
            return False
        
        # 保存HTML内容
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        logger.info(f"Saved HTML to: {output_path}")
        
        # 简单分析HTML结构
        analyze_html_structure(response.text)
        
        return True
    
    except Exception as e:
        logger.error(f"Error fetching HTML: {str(e)}")
        return False

def analyze_html_structure(html_content):
    """
    简单分析HTML结构，输出可能的类型/分类选择器
    
    Args:
        html_content: HTML内容
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 尝试查找可能的类型/分类元素
        potential_selectors = [
            '.genre-list a', '.category-list a', '.genres a', '.tags a', 
            '.genre-item a', '.genre-box a', '.genre-section a', '.category a',
            '.tag-cloud a', 'ul.genres li a', 'div.genres a', '.genre-tag a',
            '.genre-link', 'a[href*="/genre/"]', 'a[href*="/genres/"]', 
            'a[href*="/category/"]'
        ]
        
        logger.info("Analyzing HTML structure...")
        
        for selector in potential_selectors:
            elements = soup.select(selector)
            if elements:
                logger.info(f"Found {len(elements)} elements with selector: {selector}")
                # 输出前5个元素的文本和链接
                for i, elem in enumerate(elements[:5]):
                    text = elem.get_text(strip=True)
                    href = elem.get('href', '')
                    logger.info(f"  - Element {i+1}: Text='{text}', Href='{href}'")
        
        # 查找所有链接，看是否有包含genre或category的链接
        all_links = soup.find_all('a', href=True)
        genre_links = [a for a in all_links if 'genre' in a['href'] or 'category' in a['href']]
        
        if genre_links:
            logger.info(f"Found {len(genre_links)} links containing 'genre' or 'category'")
            # 输出前5个链接
            for i, link in enumerate(genre_links[:5]):
                text = link.get_text(strip=True)
                href = link['href']
                logger.info(f"  - Link {i+1}: Text='{text}', Href='{href}'")
                
                # 尝试找出这个链接的父元素的选择器
                parents = []
                parent = link.parent
                for _ in range(3):  # 只查找3层父元素
                    if parent is None or parent.name == 'html':
                        break
                    
                    classes = parent.get('class', [])
                    if classes:
                        class_selector = '.'.join(classes)
                        parents.append(f"{parent.name}.{class_selector}")
                    else:
                        parents.append(parent.name)
                    
                    parent = parent.parent
                
                if parents:
                    logger.info(f"    Parent selectors: {' > '.join(parents)}")
        
    except Exception as e:
        logger.error(f"Error analyzing HTML structure: {str(e)}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Fetch and save HTML content for analysis')
    parser.add_argument('--base-url', type=str, default='http://123av.com', help='Base URL')
    parser.add_argument('--language', type=str, default='ja', help='Language code')
    parser.add_argument('--output-dir', type=str, default='src/tests/html_data', help='Output directory')
    args = parser.parse_args()
    
    # 构建URL和输出路径
    genres_url = f"{args.base_url}/{args.language}/genres"
    genres_output_path = os.path.join(args.output_dir, 'genres.html')
    
    # 获取并保存类型页面
    save_html(genres_url, genres_output_path)
    
    # 如果成功获取了类型页面，尝试获取一个类型的详情页面
    if os.path.exists(genres_output_path):
        try:
            with open(genres_output_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 尝试找到一个类型链接
            genre_links = []
            for selector in [
                'a[href*="/genre/"]', 'a[href*="/genres/"]', 
                'a[href*="/category/"]', '.genre-list a', '.category-list a'
            ]:
                links = soup.select(selector)
                if links:
                    genre_links.extend(links)
                    break
            
            if genre_links:
                # 获取第一个类型的链接
                genre_link = genre_links[0]['href']
                if not genre_link.startswith('http'):
                    if not genre_link.startswith('/'):
                        genre_link = f'/{genre_link}'
                    genre_link = f"{args.base_url}{genre_link}"
                
                genre_name = genre_links[0].get_text(strip=True)
                logger.info(f"Found genre: {genre_name}, URL: {genre_link}")
                
                # 保存这个类型的详情页面
                genre_output_path = os.path.join(args.output_dir, f'genre_{genre_name}.html')
                save_html(genre_link, genre_output_path)
                
                # 尝试从这个类型页面获取一个电影详情页面
                if os.path.exists(genre_output_path):
                    with open(genre_output_path, 'r', encoding='utf-8') as f:
                        genre_html = f.read()
                    
                    genre_soup = BeautifulSoup(genre_html, 'html.parser')
                    
                    # 尝试找到一个电影链接
                    movie_links = []
                    for selector in [
                        '.movie-item a', '.video-item a', '.item a', 
                        'a[href*="/movie/"]', 'a[href*="/video/"]'
                    ]:
                        links = genre_soup.select(selector)
                        if links:
                            movie_links.extend(links)
                            break
                    
                    if movie_links:
                        # 获取第一个电影的链接
                        movie_link = movie_links[0]['href']
                        if not movie_link.startswith('http'):
                            if not movie_link.startswith('/'):
                                movie_link = f'/{movie_link}'
                            movie_link = f"{args.base_url}{movie_link}"
                        
                        movie_id = movie_link.split('/')[-1]
                        logger.info(f"Found movie: {movie_id}, URL: {movie_link}")
                        
                        # 保存这个电影的详情页面
                        movie_output_path = os.path.join(args.output_dir, f'movie_{movie_id}.html')
                        save_html(movie_link, movie_output_path)
        
        except Exception as e:
            logger.error(f"Error processing HTML: {str(e)}")

if __name__ == '__main__':
    main()
