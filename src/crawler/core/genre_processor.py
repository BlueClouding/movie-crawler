"""Genre processor module for crawling movie genres."""

import argparse
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
from ..utils.progress_manager import DBProgressManager
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
        self._progress_manager = DBProgressManager(language, self._db)
        
    async def process_genres(self, progress_manager):
        """Process and save genres.
        
        Args:
            progress_manager: DBProgressManager instance for tracking progress
        """
        try:
            # Fetch genres
            self._logger.info("Processing genres...")
            genres = await self._fetch_genres()
            if not genres:
                self._logger.error("Failed to fetch genres")
                return False

            self._logger.info(f"Found {len(genres)} genres")
            self._logger.info("Processing genre pages...")
            
            # Process each genre
            for genre in genres:
                try:
                    genre_id = await self._save_genre(genre)
                    if not genre_id:
                        self._logger.error(f"Failed to save genre: {genre['name']}")
                        return False
                    
                    # Update progress
                    await progress_manager.update_genre_progress(genre['name'])
                    
                except Exception as e:
                    self._logger.error(f"Error processing genre {genre['name']}: {str(e)}")
                    return False

            self._logger.info("Successfully processed all genres")
            return True

        except Exception as e:
            self._logger.error(f"Error processing genres: {str(e)}")
            return False
        finally:
            self._db.close()
            
    async def _fetch_genres(self):
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
            
            # Try multiple selectors
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
                            
                        name_element = link.select_one('.name')
                        if name_element:
                            genre_name = name_element.get_text(strip=True)
                        else:
                            genre_name = "Name not found"

                        count_element = link.select_one('.text-muted')
                        if count_element:
                            count_text = count_element.get_text(strip=True)
                            count = count_text.split(" ")[0]
                        else:
                            count = 0

                        url = link.get('href', '')
                        
                        if url:
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
            
    async def _save_genre(self, genre):
        """Save genre to database.
        
        Args:
            genre (dict): Genre information
            
        Returns:
            int: Genre ID
        """
        try:
            with self._db._conn.cursor() as cur:
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
                
                if genre['url'] not in existing_urls:
                    cur.execute("""
                        UPDATE genres
                        SET urls = array_append(urls, %s)
                        WHERE id = %s
                    """, (genre['url'], genre_id))
                
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

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Movie crawler')
    
    parser.add_argument('--clear', 
                       action='store_true',
                       help='Clear existing data')
                       
    
    parser.add_argument('--language',
                       type=str,
                       default='en',
                       choices=['en', 'ja', 'zh'],
                       help='Language code')
    
    args = parser.parse_args()
    GenreProcessor.process_genres(args)

if __name__ == '__main__':
    main()
