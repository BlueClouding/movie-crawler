"""Progress manager module for tracking crawler progress."""

import json
import os
import threading
import logging
from datetime import datetime
from ..utils.file_ops import safe_read_json, safe_save_json

class ProgressManager:
    """Manager for tracking progress of all crawler tasks."""
    
    def __init__(self, language='en', progress_dir='progress'):
        """Initialize the progress manager.
        
        Args:
            language (str): Language code (e.g., 'en', 'jp')
            progress_dir (str): Directory for progress files
        """
        self.language = language
        self.progress_dir = progress_dir
        os.makedirs(progress_dir, exist_ok=True)
        
        # 创建语言特定的进度文件
        self.progress_file = os.path.join(progress_dir, f'progress_{language}.json')
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        # 初始化进度数据
        self.progress_data = {
            'genre': {
                'genres': {},  # Progress for each genre's pages
                'last_update': None,
                'completed': False
            },
            'detail': {
                'genres': {},  # Progress for each genre's movies
                'last_update': None,
                'completed': False
            },
            'm3u8': {
                'files': {},  # Progress for each file
                'last_update': None,
                'completed': False
            }
        }
        
        # 加载或创建进度文件
        if os.path.exists(self.progress_file):
            loaded_data = safe_read_json(self.progress_file)
            if loaded_data:
                self.progress_data = loaded_data
        else:
            self._save_progress(self.progress_data)

    
    def _load_progress(self):
        """Load progress data from file.
        
        Returns:
            dict: Progress data
        """
        return safe_read_json(self.progress_file) or {}
    
    def _save_progress(self, progress):
        """Save progress data to file.
        
        Args:
            progress (dict): Progress data to save
        """
        safe_save_json(self.progress_file, progress)
    
    def update_genre_progress(self, genre_name, page_num, completed=False):
        """Update genre processing progress.
        
        Args:
            genre_name (str): Name of the genre
            page_num (int): Current page number
            completed (bool): Whether all genres are completed
        """
        with self.lock:
            progress = self._load_progress()
            
            if genre_name:
                if 'genres' not in progress['genre']:
                    progress['genre']['genres'] = {}
                
                progress['genre']['genres'][genre_name] = {
                    'last_page': page_num,
                    'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            if completed:
                progress['genre']['completed'] = True
                self.logger.info("All genres have been processed")
            else:
                progress['genre']['completed'] = False
            
            progress['genre']['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._save_progress(progress)
    
    def get_genre_progress(self, genre_name):
        """Get progress for a genre.
        
        Args:
            genre_name (str): Name of the genre
            
        Returns:
            int: Last processed page number
        """
        progress = self._load_progress()
        if 'genre' in progress and 'genres' in progress['genre']:
            genre_progress = progress['genre']['genres'].get(genre_name, {})
            return genre_progress.get('last_page', 1)
        return 1
    
    def update_detail_progress(self, genre_name, movie_index, completed=False):
        """Update detail crawler progress.
        
        Args:
            genre_name (str): Name of the genre
            movie_index (int): Current movie index
            completed (bool): Whether all details are completed
        """
        with self.lock:
            progress = self._load_progress()
            
            if genre_name:
                if 'genres' not in progress['detail']:
                    progress['detail']['genres'] = {}
                
                progress['detail']['genres'][genre_name] = {
                    'current_index': movie_index,
                    'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            if completed:
                progress['detail']['completed'] = True
                self.logger.info("All movie details have been processed")
            else:
                progress['detail']['completed'] = False
            
            progress['detail']['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._save_progress(progress)
    
    def get_detail_progress(self, genre_name):
        """Get progress for detail crawler.
        
        Args:
            genre_name (str): Name of the genre
            
        Returns:
            int: Last processed movie index
        """
        progress = self._load_progress()
        if 'detail' in progress and 'genres' in progress['detail']:
            genre_progress = progress['detail']['genres'].get(genre_name, {})
            return genre_progress.get('current_index', 0)
        return 0
    
    def update_m3u8_progress(self, genre_name, movie_index, completed=False):
        """Update M3U8 crawler progress.
        
        Args:
            genre_name (str): Name of the genre
            movie_index (int): Current movie index
            completed (bool): Whether all M3U8s are completed
        """
        with self.lock:
            progress = self._load_progress()
            
            if genre_name:
                if 'files' not in progress['m3u8']:
                    progress['m3u8']['files'] = {}
                
                progress['m3u8']['files'][genre_name] = {
                    'current_index': movie_index,
                    'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            
            if completed:
                progress['m3u8']['completed'] = True
                self.logger.info("All M3U8 streams have been processed")
            else:
                progress['m3u8']['completed'] = False
            
            progress['m3u8']['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._save_progress(progress)
    
    def get_m3u8_progress(self, genre_name):
        """Get progress for M3U8 crawler.
        
        Args:
            genre_name (str): Name of the genre
            
        Returns:
            int: Last processed movie index
        """
        progress = self._load_progress()
        if 'm3u8' in progress and 'files' in progress['m3u8']:
            file_progress = progress['m3u8']['files'].get(genre_name, {})
            return file_progress.get('current_index', 0)
        return 0
    
    def clear_progress(self):
        """Clear all progress data."""
        with self.lock:
            # 重新初始化进度数据
            self.progress_data = {
                'genre': {
                    'genres': {},
                    'last_update': None,
                    'completed': False
                },
                'detail': {
                    'genres': {},
                    'last_update': None,
                    'completed': False
                },
                'm3u8': {
                    'files': {},
                    'last_update': None,
                    'completed': False
                }
            }
            # 保存新的进度数据
            self._save_progress(self.progress_data)
