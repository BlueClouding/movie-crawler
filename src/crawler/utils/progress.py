"""Progress manager module."""

import os
import json
import logging
from .file_ops import safe_read_json, safe_save_json

class ProgressManager:
    """Manager for tracking crawling progress."""
    
    def __init__(self, language='en'):
        """Initialize progress manager.
        
        Args:
            language (str): Language code
        """
        self._logger = logging.getLogger(__name__)
        self._language = language
        self._progress_file = os.path.join('progress', f'progress_{language}.json')
        os.makedirs('progress', exist_ok=True)
        
        # Load existing progress
        self._progress = self._load_progress()
        
    def _load_progress(self):
        """Load progress from file.
        
        Returns:
            dict: Progress data
        """
        progress = safe_read_json(self._progress_file)
        if not progress:
            progress = {
                'genres': {},
                'details': {}
            }
        return progress
        
    def _save_progress(self):
        """Save progress to file."""
        safe_save_json(self._progress_file, self._progress)
        
    def get_genre_progress(self, genre_name):
        """Get progress for a genre.
        
        Args:
            genre_name (str): Name of the genre
            
        Returns:
            int: Last processed page number
        """
        return self._progress['genres'].get(genre_name, {}).get('page', 1)
        
    def update_genre_progress(self, genre_name, page, completed=False):
        """Update progress for a genre.
        
        Args:
            genre_name (str): Name of the genre
            page (int): Current page number
            completed (bool): Whether genre processing is completed
        """
        if genre_name not in self._progress['genres']:
            self._progress['genres'][genre_name] = {}
            
        self._progress['genres'][genre_name].update({
            'page': page,
            'completed': completed
        })
        self._save_progress()
        
    def get_detail_progress(self, genre_name):
        """Get detail processing progress for a genre.
        
        Args:
            genre_name (str): Name of the genre
            
        Returns:
            int: Number of processed movies
        """
        return self._progress['details'].get(genre_name, 0)
        
    def update_detail_progress(self, genre_name, count):
        """Update detail processing progress for a genre.
        
        Args:
            genre_name (str): Name of the genre
            count (int): Number of processed movies
        """
        self._progress['details'][genre_name] = count
        self._save_progress()
        
    def is_genre_completed(self, genre_name):
        """Check if a genre is completed.
        
        Args:
            genre_name (str): Name of the genre
            
        Returns:
            bool: True if genre is completed
        """
        return self._progress['genres'].get(genre_name, {}).get('completed', False) 