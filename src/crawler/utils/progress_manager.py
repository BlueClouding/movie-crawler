import os
import json
import logging
from .file_ops import safe_read_json, safe_save_json

class ProgressManager:
    """Manages progress of the crawler."""

    def __init__(self, language):
        """Initialize ProgressManager.

        Args:
            language (str): Language code
        """
        self._language = language
        self._logger = logging.getLogger(__name__)
        self._progress_dir = os.path.join('progress')
        os.makedirs(self._progress_dir, exist_ok=True)
        self._progress_file = os.path.join(self._progress_dir, f'progress_{language}.json')
        self._progress = self._load_progress()

    def _load_progress(self):
        """Load progress from file."""
        try:
            if os.path.exists(self._progress_file):
                progress = safe_read_json(self._progress_file)
                if progress and isinstance(progress, dict):
                    # Ensure required keys exist
                    if 'genres' not in progress:
                        progress['genres'] = {}
                    if 'details' not in progress:
                        progress['details'] = {}
                    return progress
            
            # Create default progress structure
            return {
                'genres': {},  # genre_name -> last_processed_page
                'details': {}  # genre_name -> processed_movies_count
            }
        except Exception as e:
            self._logger.error(f"Failed to load progress: {str(e)}")
            return {
                'genres': {},
                'details': {}
            }

    def _save_progress(self):
        """Save progress to file."""
        try:
            # Ensure required keys exist before saving
            if not isinstance(self._progress, dict):
                self._progress = {}
            if 'genres' not in self._progress:
                self._progress['genres'] = {}
            if 'details' not in self._progress:
                self._progress['details'] = {}
            
            safe_save_json(self._progress_file, self._progress)
        except Exception as e:
            self._logger.error(f"Failed to save progress: {str(e)}")

    def get_genre_progress(self, genre_name):
        """Get the last processed page for a genre.

        Args:
            genre_name (str): Name of the genre

        Returns:
            int: Last processed page number, 0 if not started
        """
        if not isinstance(self._progress, dict) or 'genres' not in self._progress:
            return 0
        return self._progress['genres'].get(genre_name, 0)

    def update_genre_progress(self, genre_name, page):
        """Update progress for a genre.

        Args:
            genre_name (str): Name of the genre
            page (int): Last processed page number
        """
        if not isinstance(self._progress, dict):
            self._progress = {}
        if 'genres' not in self._progress:
            self._progress['genres'] = {}
        self._progress['genres'][genre_name] = page
        self._save_progress()

    def get_detail_progress(self, genre_name):
        """Get the number of processed movies for a genre.

        Args:
            genre_name (str): Name of the genre

        Returns:
            int: Number of processed movies
        """
        if not isinstance(self._progress, dict) or 'details' not in self._progress:
            return 0
        return self._progress['details'].get(genre_name, 0)

    def update_detail_progress(self, genre_name, count):
        """Update the number of processed movies for a genre.

        Args:
            genre_name (str): Name of the genre
            count (int): Number of processed movies
        """
        if not isinstance(self._progress, dict):
            self._progress = {}
        if 'details' not in self._progress:
            self._progress['details'] = {}
        current = self.get_detail_progress(genre_name)
        self._progress['details'][genre_name] = current + count
        self._save_progress()

    def is_genre_completed(self, genre_name):
        """Check if a genre is completed.

        Args:
            genre_name (str): Name of the genre

        Returns:
            bool: True if genre is completed
        """
        if not isinstance(self._progress, dict) or 'genres' not in self._progress:
            return False
        return self._progress['genres'].get(genre_name, 0) == -1  # -1 indicates completion 