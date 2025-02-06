"""M3U8 crawler module for fetching video streams."""

import logging
import os
import json
import time
import random
import urllib.parse
from ..utils.http import create_session
from ..utils.file_ops import safe_read_json, safe_save_json

class M3U8Crawler:
    """Crawler for fetching M3U8 video streams."""
    
    def __init__(self, progress_manager=None, language='en'):
        """Initialize the M3U8 crawler.
        
        Args:
            progress_manager: Optional progress manager instance
            language (str): Language code (e.g., en, jp)
        """
        self.logger = logging.getLogger(__name__)
        self.progress_manager = progress_manager
        self.language = language
        # Create session
        self.session = create_session(use_proxy=True)
    
    def extract_video_info(self, image_url):
        """Extract video information from javplayer.
        
        Args:
            image_url (str): URL of the movie poster
            
        Returns:
            tuple: (m3u8_url, vtt_url) or (None, None) if extraction fails
        """
        try:
            encoded_poster = urllib.parse.quote(image_url)
            player_url = f"https://javplayer.me/e/8WZOMOV8?poster={encoded_poster}"
            
            self.logger.info(f"Requesting player URL: {player_url}")
            
            time.sleep(random.uniform(1, 3))  # Rate limiting
            
            response = self.session.get(player_url, timeout=10)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch player page: {response.status_code}")
                return None, None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract m3u8 URL
            video_elem = soup.select_one('video source[type="application/x-mpegURL"]')
            m3u8_url = video_elem['src'] if video_elem else None
            
            # Extract VTT URL
            track_elem = soup.select_one('track[kind="subtitles"]')
            vtt_url = track_elem['src'] if track_elem else None
            
            return m3u8_url, vtt_url
            
        except Exception as e:
            self.logger.error(f"Error extracting video info: {str(e)}")
            return None, None
    
    def update_movie_details(self, detail_file, movie_link, m3u8_url, vtt_url):
        """Update movie details with M3U8 and VTT URLs.
        
        Args:
            detail_file (str): Path to detail file
            movie_link (str): Movie link
            m3u8_url (str): M3U8 stream URL
            vtt_url (str): VTT subtitle URL
        """
        details = safe_read_json(detail_file)
        if not details:
            return
            
        movie_id = movie_link.split('/')[-1]
        if movie_id in details:
            details[movie_id].update({
                'm3u8_url': m3u8_url,
                'vtt_url': vtt_url,
                'last_update': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            safe_save_json(detail_file, details)
    
    def process_detail_file(self, detail_file):
        """Process a single detail file.
        
        Args:
            detail_file (str): Path to detail file
        """
        details = safe_read_json(detail_file)
        if not details:
            return
            
        genre_name = os.path.basename(detail_file).replace('_details.json', '')
        start_index = self.progress_manager.get_m3u8_progress(genre_name) if self.progress_manager else 0
        
        movie_items = list(details.items())[start_index:]
        self.logger.info(f"Processing {len(movie_items)} movies from {genre_name}")
        
        for i, (movie_id, movie_data) in enumerate(movie_items, start=start_index):
            if not movie_data.get('m3u8_url'):
                m3u8_url, vtt_url = self.extract_video_info(movie_data['image_url'])
                if m3u8_url:
                    self.update_movie_details(detail_file, movie_data['url'], m3u8_url, vtt_url)
                    
            if self.progress_manager:
                self.progress_manager.update_m3u8_progress(genre_name, i + 1)
                
            time.sleep(random.uniform(1, 3))  # Rate limiting
