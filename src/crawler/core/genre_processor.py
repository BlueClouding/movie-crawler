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
from ..utils.file_ops import safe_save_json, safe_read_json
from ..utils.db import DatabaseManager
import re

class GenreProcessor:
    """Processor for genre data."""
    
    def __init__(self, base_url, language):
        """Initialize GenreProcessor.

        Args:
            base_url (str): Base URL for the website
            language (str): Language code
        """
        self._base_url = base_url
        self._language = language
        self._logger = logging.getLogger(__name__)
        self._session = create_session(use_proxy=True)
        self._db = DatabaseManager()
        
    def process_genres(self):
        """Process and save genres."""
        try:
            # 获取类型列表
            genres = self._fetch_genres()
            if not genres:
                self._logger.error("Failed to fetch genres")
                return None
                
            # 保存到数据库
            saved_genres = []
            for genre in genres:
                try:
                    genre_id = self._save_genre(genre)
                    if genre_id:
                        saved_genres.append({
                            'id': genre_id,
                            'name': genre['name'],
                            'url': genre['url'],
                            'count': genre.get('count', 0)
                        })
                except Exception as e:
                    self._logger.error(f"Error saving genre {genre['name']}: {str(e)}")
                    continue
                    
            self._logger.info(f"Saved {len(saved_genres)} genres to database")
            return saved_genres
            
        except Exception as e:
            self._logger.error(f"Error processing genres: {str(e)}")
            return None
        finally:
            self._db.close()
            
    def _fetch_genres(self):
        """Fetch genres from website.
        
        Returns:
            list: List of genre dictionaries
        """
        try:
            url = f"{self._base_url}/genres"
            response = self._session.get(url, timeout=10)
            if response.status_code != 200:
                self._logger.error(f"Failed to fetch genres: HTTP {response.status_code}")
                return None
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 尝试多个选择器
            selectors = [
                '.genre-item',
                '.genre-list a',
                '.categories a',
                '.nav-item a[href*="/genres/"]',
                'a[href*="/genres/"]',
                '.category a'
            ]
            
            genres = []
            for selector in selectors:
                genre_items = soup.select(selector)
                if genre_items:
                    self._logger.info(f"Found {len(genre_items)} genres using selector: {selector}")
                    for item in genre_items:
                        link = item.select_one('a') if selector == '.genre-item' else item
                        if not link:
                            continue
                            
                        name = link.get_text(strip=True)
                        url = link.get('href', '')
                        
                        # 处理 URL
                        if url:
                            # 如果是相对路径，添加基础 URL
                            if not url.startswith('http'):
                                if not url.startswith('/'):
                                    url = f'/{url}'
                                if not url.startswith(f'/{self._language}/'):
                                    url = f'/{self._language}/{url.lstrip("/")}'
                                url = f'http://123av.com{url}'
                                
                        count_span = item.select_one('.count') if selector == '.genre-item' else None
                        count = int(count_span.get_text(strip=True).strip('()')) if count_span else 0
                        
                        if name and url:
                            genres.append({
                                'name': name,
                                'url': url,
                                'count': count
                            })
                    break
                else:
                    self._logger.debug(f"No genres found using selector: {selector}")
                    
            if not genres:
                self._logger.error("No genres found with any selector")
                self._logger.debug(f"Available classes: {[cls for tag in soup.find_all(class_=True) for cls in tag.get('class', [])][:20]}")
                self._logger.debug(f"Page structure:\n{soup.prettify()[:1000]}")
                
            return genres
            
        except Exception as e:
            self._logger.error(f"Error fetching genres: {str(e)}")
            return None
            
    def _save_genre(self, genre):
        """Save genre to database.
        
        Args:
            genre (dict): Genre information
            
        Returns:
            int: Genre ID
        """
        try:
            with self._db._conn.cursor() as cur:
                # 检查类型是否已存在
                cur.execute("""
                    WITH genre_check AS (
                        SELECT g.id 
                        FROM genres g
                        JOIN genre_names gn ON g.id = gn.genre_id
                        WHERE gn.name = %s AND gn.language = %s
                    ), new_genre AS (
                        INSERT INTO genres DEFAULT VALUES
                        RETURNING id
                    )
                    SELECT COALESCE(
                        (SELECT id FROM genre_check),
                        (SELECT id FROM new_genre)
                    ) as genre_id
                """, (genre['name'], self._language))
                genre_id = cur.fetchone()[0]
                
                # 插入或更新类型名称
                cur.execute("""
                    INSERT INTO genre_names (genre_id, language, name)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (genre_id, language) DO UPDATE 
                    SET name = EXCLUDED.name
                """, (genre_id, self._language, genre['name']))
                
                self._db._conn.commit()
                return genre_id
                
        except Exception as e:
            self._db._conn.rollback()
            self._logger.error(f"Error saving genre {genre['name']}: {str(e)}")
            raise

    def process_genre(self, genre):
        """Process a single genre's movies.
        
        Args:
            genre (dict): Genre information containing name and URL
        """
        genre_name = genre['name']
        start_page = self.progress_manager.get_genre_progress(genre_name) if self.progress_manager else 1
        
        self._logger.info(f"Processing genre: {genre_name}, starting from page {start_page}")
        
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
                url = f"{self._base_url}/{genre['url'].lstrip('/')}"
            else:
                url = genre['url']
            
            # 添加页码
            if '?' in url:
                url = f"{url}&page={page_num}"
            else:
                url = f"{url}?page={page_num}"
                
            self._logger.info(f"Fetching URL: {url}")
            response = self._session.get(url, timeout=10)
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
                    self._logger.error(f"No movies found on page {page_num}. HTML: {soup.prettify()[:500]}...")
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
                            if not url.startswith(f'/{self._language}/'):
                                url = f'/{self._language}/{url.lstrip("/")}'
                            final_url = f'http://123av.com{url}'
                        
                        movies[movie_id] = {
                            'id': movie_id,
                            'title': title,
                            'url': final_url,
                            'duration': duration_text
                        }
                return movies
                
        except Exception as e:
            self._logger.error(f"Error processing page {page_num} of {genre_name}: {str(e)}")
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

    def process(self):
        """Process genres."""
        try:
            self._logger.info("Starting to process genres")
            response = requests.get(f"{self._base_url}/genres")
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Save last response HTML for debugging
            debug_dir = os.path.join('debug', 'html')
            os.makedirs(debug_dir, exist_ok=True)
            with open(os.path.join(debug_dir, 'last_response.html'), 'w', encoding='utf-8') as f:
                f.write(soup.prettify())

            # Find all genre items
            genres = []
            # 获取所有文本内容并按行分割
            lines = soup.get_text().split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 匹配格式：Genre Name xxx videos
                match = re.match(r'(.+?)\s+(\d+(?:,\d+)?)\s+videos?\s*$', line)
                if match:
                    name = match.group(1).strip()
                    count_str = match.group(2).replace(',', '')
                    try:
                        count = int(count_str)
                    except (ValueError, TypeError):
                        continue

                    # 构造URL
                    url_name = f"dm3/genres/{name.lower().replace(' ', '-').replace('/', '-')}"
                    
                    genres.append({
                        'name': name,
                        'url': url_name,
                        'count': count
                    })

            if not genres:
                raise Exception("No valid genres found")

            self._logger.info(f"Found {len(genres)} genres")
            self._save_genres_to_db(genres)
            return True

        except Exception as e:
            self._logger.error(f"Failed to process genres: {str(e)}")
            return False

    def _save_genres_to_db(self, genres):
        """Save genres to database."""
        try:
            with self._db._conn.cursor() as cursor:
                for genre in genres:
                    # Check if genre exists
                    cursor.execute("""
                        WITH genre_check AS (
                            SELECT g.id 
                            FROM genres g
                            JOIN genre_names gn ON g.id = gn.genre_id
                            WHERE gn.name = %s AND gn.language = %s
                        ), new_genre AS (
                            INSERT INTO genres DEFAULT VALUES
                            RETURNING id
                        )
                        SELECT COALESCE(
                            (SELECT id FROM genre_check),
                            (SELECT id FROM new_genre)
                        ) as genre_id
                    """, (genre['name'], self._language))
                    genre_id = cursor.fetchone()[0]

                    # Insert or update genre name
                    cursor.execute("""
                        INSERT INTO genre_names (genre_id, language, name)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (genre_id, language) DO UPDATE 
                        SET name = EXCLUDED.name
                    """, (genre_id, self._language, genre['name']))
                    
                self._db._conn.commit()
                self._logger.info(f"Successfully saved {len(genres)} genres to database")
        except Exception as e:
            self._db._conn.rollback()
            self._logger.error(f"Failed to save genres to database: {str(e)}")
            raise
