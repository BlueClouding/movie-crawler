"""Genre processor module for crawling movie genres."""

import logging
import os
import json
import time
import random
import csv
import ssl
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from ..utils.http import create_session
from ..utils.file_ops import safe_save_json

class GenreProcessor:
    """Processor for handling movie genres and their listings."""
    
    def __init__(self, progress_manager=None, language='en'):
        """Initialize the genre processor.
        
        Args:
            progress_manager: Optional progress manager instance
            language (str): Language code (e.g., 'en', 'jp')
        """
        self.progress_manager = progress_manager
        self.logger = logging.getLogger(__name__)
        self.language = language
        
        # Base URL with language
        self.base_url = f'http://123av.com/{language}'
        
        # 创建语言特定的数据目录
        self.genres_dir = os.path.join('genres', language)
        self.movies_dir = os.path.join('genre_movie', language)
        os.makedirs(self.genres_dir, exist_ok=True)
        os.makedirs(self.movies_dir, exist_ok=True)
        
        # Create session with retry mechanism and SSL handling
        # Create session
        self.session = create_session(use_proxy=True)
    
    def process_genres(self):
        """Process all genres and return the genre list.
        If existing genres file found, load from it instead of crawling.
        
        Returns:
            list: List of genre dictionaries with name, url, and video count
        """
        # 检查是否存在最新的 genres 文件
        latest_genres_file = self._get_latest_genres_file()
        if latest_genres_file:
            self.logger.info(f'Found existing genres file: {latest_genres_file}')
            genres = self._load_genres(latest_genres_file)
            self.logger.info(f'Loaded {len(genres)} genres from file')
            return genres
            
        self.logger.info('No existing genres file found, crawling genres...')
        genres = self._fetch_genres()
        if genres:
            # Save genres to file with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(self.genres_dir, f'genres_{timestamp}.csv')
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['name', 'url', 'count'])
                writer.writeheader()
                writer.writerows(genres)
            
            self.logger.info(f"Saved {len(genres)} genres to {filename}")
            return genres
        return []
        
    def _get_latest_genres_file(self):
        """Get the latest genres file from data directory."""
        import glob
        
        # 获取所有 genres 文件
        genre_files = glob.glob(os.path.join(self.genres_dir, 'genres_*.csv'))
        if not genre_files:
            return None
            
        # 按修改时间排序，返回最新的文件
        return max(genre_files, key=os.path.getmtime)
        
    def _load_genres(self, file_path):
        """Load genres from CSV file."""
        genres = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                genres.append({
                    'name': row['name'],
                    'url': row['url'],
                    'count': row['count']
                })
        return genres
    
    def process_genre(self, genre):
        """Process a single genre's movies.
        
        Args:
            genre (dict): Genre information containing name and URL
        """
        genre_name = genre['name']
        start_page = self.progress_manager.get_genre_progress(genre_name) if self.progress_manager else 1
        
        self.logger.info(f"Processing genre: {genre_name}, starting from page {start_page}")
        
        current_page = start_page
        
        while True:
            page_movies = self._process_genre_page(genre, current_page)
            if not page_movies:
                break
                
            # 创建类型目录
            genre_dir = os.path.join(self.movies_dir, genre_name)
            os.makedirs(genre_dir, exist_ok=True)
            
            # 保存到新文件
            filename = os.path.join(genre_dir, f'{genre_name}_page_{current_page}.json')
            safe_save_json(filename, page_movies)
            
            if self.progress_manager:
                self.progress_manager.update_genre_progress(genre_name, current_page)
            
            current_page += 1
            time.sleep(random.uniform(1, 3))  # Rate limiting
    
    def _fetch_genres(self):
        """Fetch all available genres from the website.
        
        Returns:
            list: List of genre dictionaries
        """
        try:
            response = self.session.get(f'{self.base_url}/genres', timeout=10)
            response.encoding = 'utf-8'  # 强制使用 UTF-8 编码
            
            if response.status_code == 200:
                self.logger.debug(f"URL: {self.base_url}/genres")
                self.logger.debug(f"Response encoding: {response.encoding}")
                self.logger.debug(f"Content-Type: {response.headers.get('content-type')}")
                self.logger.debug(f"Response content: {response.text[:500]}")
                
                soup = BeautifulSoup(response.text, 'html.parser')
                genres = []
                
                # 尝试多个选择器
                selectors = [
                    '.genre-list a',
                    '.categories a', 
                    '.nav-item a[href*="/genres/"]',
                    'a[href*="/genres/"]',
                    '.category a'
                ]
                
                for selector in selectors:
                    genre_elems = soup.select(selector)
                    if genre_elems:
                        self.logger.debug(f"Found {len(genre_elems)} genres using selector: {selector}")
                        for genre_elem in genre_elems:
                            text = genre_elem.text.strip()
                            # 分离名称和视频数量
                            parts = text.split('\n')
                            name = parts[0].strip()
                            count = parts[1].strip() if len(parts) > 1 else '0 videos'
                            # 先移除逗号，然后去掉 'videos' 字样
                            count = count.replace(',', '').replace(' videos', '')
                            
                            genres.append({
                                'name': name,
                                'url': genre_elem['href'],
                                'count': count
                            })
                        return genres
                    else:
                        self.logger.debug(f"No genres found using selector: {selector}")
                
                # 如果所有选择器都失败，记录更多信息
                self.logger.error("No genres found with any selector")
                self.logger.debug(f"Available classes: {[cls for tag in soup.find_all(class_=True) for cls in tag.get('class', [])][:20]}")
                self.logger.debug(f"Page structure:\n{soup.prettify()[:1000]}")
                return []
        except Exception as e:
            self.logger.error(f"Error fetching genres: {str(e)}")
            if hasattr(e, 'response') and hasattr(e.response, 'content'):
                self.logger.error(f"Response content: {e.response.content[:500]}")
        return []
    
    def _process_genre_page(self, genre, page_num):
        """Process a single page of a genre.
        
        Args:
            genre (dict): Genre information containing name and URL
            page_num (int): Page number to process
            
        Returns:
            dict: Dictionary of movies from the page
        """
        try:
            # 构建 URL
            if not genre['url'].startswith('http'):
                url = f"{self.base_url}/{genre['url'].lstrip('/')}"
            else:
                url = genre['url']
            
            # 添加页码
            if '?' in url:
                url = f"{url}&page={page_num}"
            else:
                url = f"{url}?page={page_num}"
                
            self.logger.info(f"Fetching URL: {url}")
            response = self.session.get(url, timeout=10)
            response.encoding = 'utf-8'  # 强制使用 UTF-8 编码
            
            if response.status_code == 404:
                return None
                
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                movies = {}
                
                # 尝试多个选择器
                selectors = [
                    '.box-item',
                    '.movie-item',
                    '.video-item',
                    '.post-item'
                ]
                
                for selector in selectors:
                    movie_elems = soup.select(selector)
                    if movie_elems:
                        break
                
                if not movie_elems:
                    # 如果找不到，记录HTML以便调试
                    self.logger.error(f"No movies found on page {page_num}. HTML: {soup.prettify()[:500]}...")
                    return None
                    
                for movie_elem in movie_elems:
                    # 获取缩略图链接
                    thumb_link = movie_elem.select_one('.thumb a')
                    if not thumb_link:
                        continue
                    
                    url = thumb_link.get('href', '')
                    if not url:
                        continue
                    
                    # 获取标题
                    title = thumb_link.get('title', '')
                    if not title:
                        img = thumb_link.find('img')
                        if img:
                            title = img.get('alt', '')
                    
                    # 获取详细信息
                    detail = movie_elem.select_one('.detail a')
                    if detail:
                        detail_text = detail.get_text(strip=True)
                        if detail_text:
                            title = detail_text
                    
                    # 获取时长
                    duration = movie_elem.select_one('.duration')
                    duration_text = duration.get_text(strip=True) if duration else ''
                    
                    # 生成电影ID
                    movie_id = url.split('/')[-1]
                    
                    if movie_id and title:
                        # 确保 URL 包含语言路径
                        if url.startswith('http'):
                            final_url = url
                        else:
                            # 如果 URL 不以语言路径开头，添加语言路径
                            if not url.startswith(f'/{self.language}/'):
                                url = f'/{self.language}/{url.lstrip("/")}'
                            final_url = f'http://123av.com{url}'
                        
                        movies[movie_id] = {
                            'id': movie_id,
                            'title': title,
                            'url': final_url,
                            'duration': duration_text
                        }
                return movies
                
        except Exception as e:
            self.logger.error(f"Error processing page {page_num} of {genre_name}: {str(e)}")
        return {}
    
    def _save_movies(self, genre_name, movies):
        """Save movies data to file.
        
        Args:
            genre_name (str): Name of the genre
            movies (dict): Dictionary of movies to save
        """
        # 创建类型目录
        genre_dir = os.path.join(self.movies_dir, genre_name)
        os.makedirs(genre_dir, exist_ok=True)
        
        # 保存电影数据
        if movies:
            # 获取现有的页面号
            import glob
            import re
            existing_files = glob.glob(os.path.join(genre_dir, f'{genre_name}_page_*.json'))
            page_nums = [int(re.search(r'page_([0-9]+)', f).group(1)) 
                        for f in existing_files if re.search(r'page_([0-9]+)', f)]
            next_page = max(page_nums) + 1 if page_nums else 1
            
            # 保存到新文件
            filename = os.path.join(genre_dir, f'{genre_name}_page_{next_page}.json')
            safe_save_json(filename, movies)
