"""M3U8 crawler module for fetching video streams."""

import logging
import os
import json
import time
import random
import urllib.parse
from bs4 import BeautifulSoup
from datetime import datetime
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
    
    def get_video_urls(self, video_id):
        """Get video URLs from ajax API.
        
        Args:
            video_id (str): Video ID
            
        Returns:
            tuple: (watch_url, download_url) or (None, None) if failed
        """
        try:
            ajax_url = f'https://123av.com/ja/ajax/v/{video_id}/videos'
            self.logger.info(f"Requesting ajax URL: {ajax_url}")
            
            time.sleep(random.uniform(1, 3))  # Rate limiting
            
            response = self.session.get(ajax_url, timeout=10)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch video URLs: {response.status_code}")
                return None, None
            
            data = response.json()
            if not data.get('result') or not data['result'].get('watch'):
                self.logger.error("Invalid ajax response format")
                return None, None
            
            watch_urls = data['result']['watch']
            download_urls = data['result'].get('download', [])
            
            return (watch_urls[0]['url'] if watch_urls else None,
                    download_urls[0]['url'] if download_urls else None)
                    
        except Exception as e:
            self.logger.error(f"Error getting video URLs: {str(e)}")
            return None, None
    
    def extract_video_info(self, video_id, cover_url):
        """Extract video information from javplayer.
        
        Args:
            video_id (str): Video ID
            cover_url (str): URL of the movie poster
            
        Returns:
            tuple: (m3u8_url, vtt_url) or (None, None) if extraction fails
        """
        try:
            # 1. 获取视频URL
            watch_url, _ = self.get_video_urls(video_id)
            if not watch_url:
                return None, None
                
            # 2. 构造播放器URL
            encoded_cover = urllib.parse.quote(cover_url)
            player_url = f"{watch_url}?poster={encoded_cover}"
            
            self.logger.info(f"Requesting player URL: {player_url}")
            time.sleep(random.uniform(1, 3))  # Rate limiting
            
            # 3. 获取播放器页面
            response = self.session.get(player_url, timeout=10)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch player page: {response.status_code}")
                return None, None
            
            # 4. 解析m3u8 URL
            soup = BeautifulSoup(response.text, 'html.parser')
            player_div = soup.find('div', id='player')
            if not player_div:
                self.logger.error("Player div not found")
                return None, None
            
            v_scope = player_div.get('v-scope', '')
            if not v_scope or 'stream' not in v_scope:
                self.logger.error("Stream URL not found in v-scope")
                return None, None
            
            # 解析v-scope属性中的JSON
            try:
                # 找到第二个参数的JSON开始位置
                video_start = v_scope.find('Video(')
                if video_start == -1:
                    self.logger.error("Video() function not found in v-scope")
                    return None, None
                
                # 找到第二个参数的开始位置
                first_comma = v_scope.find(',', video_start)
                if first_comma == -1:
                    self.logger.error("Comma not found after first parameter")
                    return None, None
                
                json_start = v_scope.find('{', first_comma)
                if json_start == -1:
                    self.logger.error("Opening brace not found for second parameter")
                    return None, None
                
                # 找到JSON的结束位置
                brace_count = 1
                json_end = json_start + 1
                while brace_count > 0 and json_end < len(v_scope):
                    if v_scope[json_end] == '{':
                        brace_count += 1
                    elif v_scope[json_end] == '}':
                        brace_count -= 1
                    json_end += 1
                
                if brace_count > 0:
                    self.logger.error("Closing brace not found for JSON")
                    return None, None
                
                # 提取JSON字符串
                json_str = v_scope[json_start:json_end]
                json_str = json_str.replace('&quot;', '"')
                
                # 解析JSON
                stream_data = json.loads(json_str)
                
                m3u8_url = stream_data.get('stream')
                vtt_url = stream_data.get('vtt')
                
                if not m3u8_url or not vtt_url:
                    self.logger.error("Stream or VTT URL not found in JSON data")
                    return None, None
                
                return m3u8_url, vtt_url
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON from v-scope: {e}")
                return None, None
                
        except Exception as e:
            self.logger.error(f"Error extracting video info: {str(e)}")
            return None, None
    
    def update_movie_details(self, detail_file, movie_data, m3u8_url, vtt_url):
        """Update movie details with M3U8 and VTT URLs.
        
        Args:
            detail_file (str): Path to detail file
            movie_data (dict): Movie data dictionary
            m3u8_url (str): M3U8 stream URL
            vtt_url (str): VTT subtitle URL
        """
        details = safe_read_json(detail_file)
        if not details:
            return
            
        movie_id = str(movie_data.get('id'))
        if movie_id in details:
            details[movie_id].update({
                'm3u8_url': m3u8_url,
                'vtt_url': vtt_url,
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
                m3u8_url, vtt_url = self.extract_video_info(movie_id, movie_data['cover_image'])
                if m3u8_url:
                    self.update_movie_details(detail_file, movie_data, m3u8_url, vtt_url)
                    self.logger.info(f"Successfully updated M3U8 info for movie {movie_id}")
                else:
                    self.logger.error(f"Failed to get M3U8 info for movie {movie_id}")
                    
            if self.progress_manager:
                self.progress_manager.update_m3u8_progress(genre_name, i + 1)
                
            time.sleep(random.uniform(1, 3))  # Rate limiting
