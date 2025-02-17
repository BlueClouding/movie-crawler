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
        """Fetch all available genres from the website.
        
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
                            
                        name_element = link.select_one('.name') #  使用 CSS 选择器 .name 定位到 <div class="name">
                        if name_element:
                            genre_name = name_element.get_text(strip=True)
                        else:
                            genre_name = "Name not found"  #  处理找不到 name 的情况

                        # 提取 video count
                        count_element = link.select_one('.text-muted') # 使用 CSS 选择器 .text-muted 定位到 <div class="text-muted">
                        if count_element:
                            count_text = count_element.get_text(strip=True)
                            count = count_text.split(" ")[0]
                        else:
                            count = 0

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
                                
                        if genre_name and url:
                            genres.append({
                                'name': genre_name,
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
                        SELECT g.id, g.urls
                        FROM genres g
                        JOIN genre_names gn ON g.id = gn.genre_id
                        WHERE gn.name = %s AND gn.language = %s
                    ), new_genre AS (
                        INSERT INTO genres (urls)
                        VALUES (ARRAY[%s])
                        RETURNING id
                    )
                    SELECT id, urls
                    FROM (
                        SELECT id, urls FROM genre_check
                        UNION ALL
                        SELECT id, ARRAY[%s] as urls FROM new_genre
                        LIMIT 1
                    ) combined
                """, (genre['name'], self._language, genre['url'], genre['url']))
                
                result = cur.fetchone()
                genre_id = result[0]
                existing_urls = result[1] if result[1] else []
                
                # 如果是已存在的类型，更新URLs数组
                if genre['url'] not in existing_urls:
                    cur.execute("""
                        UPDATE genres
                        SET urls = array_append(urls, %s)
                        WHERE id = %s
                    """, (genre['url'], genre_id))
                
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
