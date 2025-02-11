"""Detail crawler module for fetching movie details."""

import logging
import os
import json
import time
import random
import ssl
import urllib.parse
import re
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from ..utils.http import create_session
from ..utils.file_ops import safe_read_json, safe_save_json

class DetailCrawler:
    """Crawler for fetching movie details."""
    
    def __init__(self, clear_existing=False, threads=3, progress_manager=None, language='en'):
        """Initialize the detail crawler.
        
        Args:
            clear_existing (bool): Whether to clear existing data
            threads (int): Number of threads to use
            progress_manager: Optional progress manager instance
            language (str): Language code for the website
        """
        self._clear_existing = clear_existing
        self._threads = threads
        self._logger = logging.getLogger(__name__)
        self._progress_manager = progress_manager
        self._language = language
        self._base_url = f'http://123av.com/{language}'
        
        # 创建语言特定的目录
        self._source_dir = os.path.join('genre_movie', language)
        self._base_dir = os.path.join('movie_details', language)
        self._failed_dir = os.path.join('failed_movies', language)
        os.makedirs(self._base_dir, exist_ok=True)
        os.makedirs(self._failed_dir, exist_ok=True)
        
        # Create session with retry mechanism and SSL handling
        self._session = create_session(use_proxy=True)

        # 初始化重试记录
        self._retry_counts = {}

    def start(self):
        """Start the detail crawling process."""
        self._logger.info("Starting detail crawler...")
        
        language_dir = os.path.join('genre_movie', self._language)
        if not os.path.exists(language_dir):
            self._logger.warning(f"Language directory not found: {language_dir}")
            return

        genre_dirs = [d for d in os.listdir(language_dir)
                      if os.path.isdir(os.path.join(language_dir, d))]
        if not genre_dirs:
            self._logger.info("No genre directories found to process.")
            return

        self._logger.info(f"Found {len(genre_dirs)} genre directories: {genre_dirs}")

        with ThreadPoolExecutor(max_workers=self._threads) as executor:
            for genre_name in genre_dirs:
                executor.submit(self.process_genre_movies, genre_name)

        self._logger.info("Detail crawling process started for all genres.")


    def process_genre_movies(self, genre_name):
        """Process movies for a specific genre."""
        genre_dir = os.path.join('genre_movie', self._language, genre_name)
        if not os.path.isdir(genre_dir):
            self._logger.error(f"Genre directory not found: {genre_dir}")
            return

        movie_files = [f for f in os.listdir(genre_dir)
                       if f.endswith('.json') and f.startswith(f'{genre_name}_page_')]
        if not movie_files:
            self._logger.info(f"No movie files found in genre directory: {genre_dir}")
            return

        self._logger.info(f"Found {len(movie_files)} movie files for genre: {genre_name}")

        for movie_file in movie_files:
            file_path = os.path.join(genre_dir, movie_file)
            movies = safe_read_json(file_path)
            if not movies:
                self._logger.warning(f"No movies loaded from file: {file_path}")
                continue

            self._logger.info(f"Processing {len(movies)} movies from {movie_file} for genre: {genre_name}")
            for movie in movies.values():
                if not movie or not movie.get('url'):
                    self._logger.warning(f"Invalid movie data in {movie_file}: {movie}")
                    continue
                detail = self._get_movie_detail(movie)
                if detail:
                    self._save_movie_data(detail, genre_name)
                time.sleep(random.uniform(1, 3))  # Rate limiting
            self._logger.info(f"Finished processing movies from {movie_file} for genre: {genre_name}")


    def _get_video_urls(self, video_id):
        """Get video URLs from ajax API.
        
        Args:
            video_id (str): Video ID
            
        Returns:
            tuple: (watch_url, download_url) or (None, None) if failed
        """
        try:
            ajax_url = f'https://123av.com/ja/ajax/v/{video_id}/videos'
            self._logger.info(f"Requesting ajax URL: {ajax_url}")
            
            time.sleep(random.uniform(1, 3))  # Rate limiting
            
            response = self._session.get(ajax_url, timeout=10)
            if response.status_code != 200:
                self._logger.error(f"Failed to fetch video URLs: {response.status_code}")
                return None, None
            
            data = response.json()
            if not data.get('result') or not data['result'].get('watch'):
                self._logger.error("Invalid ajax response format")
                return None, None
            
            watch_urls = data['result']['watch']
            download_urls = data['result'].get('download', [])
            
            return (watch_urls[0]['url'] if watch_urls else None,
                    download_urls[0]['url'] if download_urls else None)
                    
        except Exception as e:
            self._logger.error(f"Error getting video URLs: {str(e)}")
            return None, None
    
    def _extract_m3u8_info(self, video_id, cover_url):
        """Extract M3U8 and VTT information from javplayer.
        
        Args:
            video_id (str): Video ID
            cover_url (str): URL of the movie poster
            
        Returns:
            tuple: (m3u8_url, vtt_url) or (None, None) if extraction fails
        """
        try:
            # 1. 获取视频URL
            watch_url, _ = self._get_video_urls(video_id)
            if not watch_url:
                return None, None
                
            # 2. 构造播放器URL
            encoded_cover = urllib.parse.quote(cover_url)
            player_url = f"{watch_url}?poster={encoded_cover}"
            
            self._logger.info(f"Requesting player URL: {player_url}")
            time.sleep(random.uniform(1, 3))  # Rate limiting
            
            # 3. 获取播放器页面
            response = self._session.get(player_url, timeout=10)
            if response.status_code != 200:
                self._logger.error(f"Failed to fetch player page: {response.status_code}")
                return None, None
            
            # 4. 解析m3u8 URL
            soup = BeautifulSoup(response.text, 'html.parser')
            player_div = soup.find('div', id='player')
            if not player_div:
                self._logger.error("Player div not found")
                return None, None
            
            v_scope = player_div.get('v-scope', '')
            if not v_scope or 'stream' not in v_scope:
                self._logger.error("Stream URL not found in v-scope")
                return None, None
            
            # 解析v-scope属性中的JSON
            try:
                # 找到第二个参数的JSON开始位置
                video_start = v_scope.find('Video(')
                if video_start == -1:
                    self._logger.error("Video() function not found in v-scope")
                    return None, None
                
                # 找到第二个参数的开始位置
                first_comma = v_scope.find(',', video_start)
                if first_comma == -1:
                    self._logger.error("Comma not found after first parameter")
                    return None, None
                
                json_start = v_scope.find('{', first_comma)
                if json_start == -1:
                    self._logger.error("Opening brace not found for second parameter")
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
                    self._logger.error("Closing brace not found for JSON")
                    return None, None
                
                # 提取JSON字符串
                json_str = v_scope[json_start:json_end]
                json_str = json_str.replace('"', '"')
                
                # 解析JSON
                stream_data = json.loads(json_str)
                
                m3u8_url = stream_data.get('stream')
                vtt_url = stream_data.get('vtt')
                
                if not m3u8_url or not vtt_url:
                    self._logger.error("Stream or VTT URL not found in JSON data")
                    return None, None
                
                return m3u8_url, vtt_url
                
            except json.JSONDecodeError as e:
                self._logger.error(f"Failed to parse JSON from v-scope: {e}")
                return None, None
                
        except Exception as e:
            self._logger.error(f"Error extracting video info: {str(e)}")
            return None, None

    def _parse_video_info(self, soup, id):
        """Parse video information from the detail page.
        
        Args:
            soup (BeautifulSoup): Parsed HTML
            movie (dict): Movie information

        Returns:
            dict: Video information
        """
        info = {
            'title': None,
            'cover_image': None,
            'preview_video': None,
            'duration': None,
            'release_date': None,
            'code': None,
            'actresses': [],
            'genres': [],
            'series': None,
            'maker': None,
            'm3u8_url': None,
            'vtt_url': None,
            'id': id  # Ensure 'id' is initialized
        }
        
        try:
            # 提取标题
            title_elem = soup.select_one('h1')
            if title_elem:
                info['title'] = title_elem.get_text(strip=True)
            
            # 提取封面图和预览视频
            video_elem = soup.select_one('#player video')
            if video_elem:
                info['cover_image'] = video_elem.get('poster')
                info['preview_video'] = video_elem.get('src')
            
            # 提取详细信息
            detail_items = soup.select('#details .detail-item > div')
            for item in detail_items:
                spans = item.find_all('span')
                if len(spans) >= 2:
                    # 使用第一个 span 的内容来确定字段类型
                    field_type = None
                    label_text = spans[0].get_text(strip=True).rstrip(':')
                    
                    # 根据关键字确定字段类型
                    if any(code in label_text.lower() for code in ['code', 'コード']):
                        field_type = 'code'
                    elif any(date in label_text.lower() for date in ['release', 'リリース']):
                        field_type = 'release_date'
                    elif any(duration in label_text.lower() for duration in ['duration', '再生時間', '时长']):
                        field_type = 'duration'
                    elif any(actress in label_text.lower() for actress in ['actress', '女優', '演员']):
                        field_type = 'actresses'
                    elif any(genre in label_text.lower() for genre in ['genre', 'ジャンル', '类型']):
                        field_type = 'genres'
                    elif any(maker in label_text.lower() for maker in ['maker', 'メーカー', '制作商']):
                        field_type = 'maker'
                    elif any(series in label_text.lower() for series in ['series', 'シリーズ', '系列']):
                        field_type = 'series'
                    
                    # 根据字段类型提取数据
                    if field_type:
                        if field_type in ['actresses', 'genres']:
                            # 列表类型的字段
                            elements = spans[1].find_all('a')
                            info[field_type] = [a.get_text(strip=True) for a in elements]
                        elif field_type in ['maker', 'series']:
                            # 单个链接类型的字段
                            element = spans[1].find('a')
                            if element:
                                info[field_type] = element.get_text(strip=True)
                        else:
                            # 普通文本字段
                            info[field_type] = spans[1].get_text(strip=True)
                            
            # 提取 M3U8 和 VTT URL
            if info['cover_image']:
                m3u8_url, vtt_url = self._extract_m3u8_info(info['id'], info['cover_image'])
                info['m3u8_url'] = m3u8_url
                info['vtt_url'] = vtt_url
            
        except Exception as e:
            self._logger.error(f"Error parsing video info: {str(e)}")
            self._logger.error("Error details:", exc_info=True)
        
        return info
        
    def _get_movie_detail(self, movie):
        """Get details for a single movie.

        Args:
            movie (dict): Movie information

        Returns:
            dict: Movie details
        """
        try:
            self._logger.info(f"Fetching movie details from: {movie['url']}")
            response = self._session.get(movie['url'])

            if response.status_code != 200:
                self._logger.error(f"Failed to fetch movie page: HTTP {response.status_code}")
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Initialize video_info with basic data
            video_info = {'url': movie['url']}

            # 提取 movie ID - 优先从 v-scope 中提取
            video_info['id'] = None  # 初始化 id 为 None
            container_div = soup.select_one('#page-video')
            if container_div:
                v_scope_attr = container_div.get('v-scope')
                if v_scope_attr:
                    movie_id_match = re.search(r"Movie\(\{id: (\d+),", v_scope_attr)
                    if movie_id_match:
                        video_info['id'] = movie_id_match.group(1)
                        self._logger.info(f"Extracted movie ID from v-scope: {video_info['id']}")
                    else:
                        self._logger.warning("Could not extract movie ID from v-scope regex.")
                else:
                    self._logger.warning("No v-scope attribute found.")
            else:
                self._logger.warning("No #page-video container found.")

            # 如果 v-scope 中没有提取到 movie ID，则从 URL 中获取作为 fallback
            if not video_info['id']:
                video_info['id'] = movie['url'].split('/')[-1]
                self._logger.info(f"Fallback to URL-based ID: {video_info['id']}")


            # Parse video info from page (在提取 ID 之后)
            parsed_info = self._parse_video_info(soup, video_info['id'])
            self._logger.info(f"Parsed info: {parsed_info}")
            if not parsed_info:
                self._logger.error("Failed to parse video info from page")
                return None

            video_info.update(parsed_info)

            # Get M3U8 and VTT URLs if cover image exists
            if video_info.get('cover_image'):
                m3u8_url, vtt_url = self._extract_m3u8_info(video_info['id'], video_info['cover_image'])
                self._logger.info(f"M3U8 URL: {m3u8_url}, VTT URL: {vtt_url}")
                if not m3u8_url or not vtt_url:
                    self._logger.warning("Failed to extract M3U8/VTT URLs")
                video_info['m3u8_url'] = m3u8_url
                video_info['vtt_url'] = vtt_url

            # Add duration if provided
            if 'duration' in movie:
                video_info['duration'] = movie['duration']


            self._logger.info(f"Successfully fetched movie details: {video_info.get('id')}")
            return video_info

        except Exception as e:
            self._logger.error(f"Error getting movie details for {movie['url']}: {str(e)}")
            self._logger.error("Error details:", exc_info=True)
            return None
    
    def _save_movie_data(self, movie_data, genre_name):
        """Save movie details to file.
        
        Args:
            movie_data (dict): Movie details to save
            genre_name (str): Name of the genre
        """
        filename = f'movie_details/{genre_name}_details.json'
        existing_data = safe_read_json(filename) or {}
        
        if movie_data:
            movie_id = movie_data['url'].split('/')[-1]
            existing_data[movie_id] = movie_data
            safe_save_json(filename, existing_data)
    
    def process_genre(self, genre):
        """Process all movies in a genre.
        
        Args:
            genre (dict): Genre information
        """
        try:
            genre_name = genre['name']
            genre_url = genre['url']
            
            self._logger.info(f"Starting to process genre: {genre_name}")
            
            # Create genre directory if not exists
            genre_dir = os.path.join(self._base_dir, genre_name)
            os.makedirs(genre_dir, exist_ok=True)
            
            # Get total pages
            total_pages = self._get_total_pages(genre_url)
            if not total_pages:
                self._logger.error(f"Failed to get total pages for genre: {genre_name}")
                return
                
                self._logger.info(f"Found {total_pages} pages for genre: {genre_name}")
            
                # Get last processed page from progress
                start_page = self._progress_manager.get_genre_progress(genre_name)
                self._logger.info(f"Resuming from page {start_page} for genre: {genre_name}")
            else:
                start_page = 1
        
            # Process each page
            movies_count = 0
            for page in range(start_page, total_pages + 1):
                try:
                    # Add random delay to avoid being blocked
                    delay = random.uniform(1, 3)
                    self._logger.debug(f"Waiting {delay:.2f}s before fetching page {page}")
                    time.sleep(delay)
                    
                    self._logger.info(f"Fetching page {page}/{total_pages} for genre: {genre_name}")
                    movies = self._fetch_genre_movies(genre_url, page)
                    
                    if movies:
                        # Save to file
                        output_file = os.path.join(genre_dir, f"{genre_name}_page_{page}.json")
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(movies, f, ensure_ascii=False, indent=2)
                        
                        movies_count += len(movies)
                        self._logger.info(f"Saved {len(movies)} movies from page {page} to {output_file} (Total: {movies_count})")
                        
                        # Update progress
                        self._progress_manager.update_detail_progress(genre_name, page)
                    else:
                        self._logger.warning(f"No movies found on page {page} for genre: {genre_name}")
                    
                    # Update genre progress
                    self._progress_manager.update_genre_progress(genre_name, page)
                        
                except Exception as e:
                    self._logger.error(f"Error processing page {page} for genre {genre_name}: {str(e)}")
                    import traceback
                    self._logger.error(f"Traceback: {traceback.format_exc()}")
                    # Continue with next page
                    continue
            
            # Mark genre as completed
            self._progress_manager.update_genre_progress(genre_name, total_pages, completed=True)
            
            self._logger.info(f"Completed processing genre: {genre_name} (Total movies: {movies_count})")
            
        except Exception as e:
            self._logger.error(f"Error processing genre {genre_name}: {str(e)}")
            import traceback
            self._logger.error(f"Traceback: {traceback.format_exc()}")
            raise  # Re-raise to let the executor handle it
            
            # 创建空的 JSON 文件
            safe_save_json(movies_file, {})
            
            # 逐页爬取并追加保存
            for page in range(1, total_pages + 1):
                page_movies = self._fetch_genre_movies(genre['url'], page)
                if not page_movies:
                    self.logger.warning(f"No movies found on page {page} for genre: {genre_name}")
                    continue
                
                # 读取现有数据并追加
                movies = safe_read_json(movies_file) or {}
                movies.update(page_movies)
                safe_save_json(movies_file, movies)
                
                if self.progress_manager:
                    self.progress_manager.update_genre_progress(genre_name, page)
                
                self.logger.info(f"Fetched page {page}/{total_pages} for genre {genre_name}, found {len(page_movies)} movies, total: {len(movies)}")
                time.sleep(random.uniform(1, 3))  # Rate limiting
            
            # 最终检查
            movies = safe_read_json(movies_file)
            if not movies:
                self.logger.warning(f"No movies found for genre: {genre_name}")
                return
            else:
                self.logger.info(f"Successfully crawled {len(movies)} movies for genre: {genre_name}")
        
        # 读取电影列表
        movies = safe_read_json(movies_file)
        if not movies:
            self.logger.warning(f"Empty movies file for genre: {genre_name}")
            return
            
        movie_list = list(movies.values())
        start_index = self._progress_manager.get_detail_progress(genre_name) if self._progress_manager else 0
        
        self.logger.info(f"Processing {len(movie_list[start_index:])} movies for genre: {genre_name}")
        
        for i, movie in enumerate(movie_list[start_index:], start=start_index):
            details = self._get_movie_detail(movie)
            if details:
                self._save_movie_data(details, genre_name)
                
            if self._progress_manager:
                self._progress_manager.update_detail_progress(genre_name, i + 1)
                
            time.sleep(random.uniform(1, 3))  # Rate limiting
