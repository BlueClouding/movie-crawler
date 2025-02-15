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
        """Get video URLs from ajax endpoint.
        
        Args:
            video_id (str): Video ID
            
        Returns:
            tuple: (watch_urls_info, download_urls_info) or ([], []) if failed.
                watch_urls_info: list of dicts, each dict contains 'index', 'name', 'url'
                download_urls_info: list of dicts, each dict contains 'host', 'index', 'name', 'url'
        """
        try:
            # Use ajax endpoint
            ajax_url = f'https://123av.com/ja/ajax/v/{video_id}/videos'
            self._logger.info(f"Requesting ajax endpoint: {ajax_url}")
            
            response = self._session.get(ajax_url, timeout=10)
            
            if response.status_code != 200:
                self._logger.error(f"Failed to fetch video URLs: {response.status_code}")
                return [], []
                
            data = response.json()
            if not data.get('status') == 200 or not data.get('result'):
                self._logger.error("Invalid ajax response format")
                return [], []
                
            watch_urls = data['result'].get('watch', [])
            download_urls = data['result'].get('download', [])
            
            # Validate watch URLs format
            for url_info in watch_urls:
                if not all(k in url_info for k in ('index', 'name', 'url')):
                    self._logger.error(f"Invalid watch URL info format: {url_info}")
                    return [], []
                    
            # Validate download URLs format
            for url_info in download_urls:
                if not all(k in url_info for k in ('host', 'index', 'name', 'url')):
                    self._logger.error(f"Invalid download URL info format: {url_info}")
                    return [], []
            
            return watch_urls, download_urls
            
        except Exception as e:
            self._logger.error(f"Error getting video URLs: {str(e)}")
            return [], []



    def _parse_video_info(self, soup):
        """Parse video information from the detail page.
        
        Args:
            soup (BeautifulSoup): Parsed HTML
            
        Returns:
            dict: Video information with all required fields
        """
        info = {
            'title': '',
            'cover_image': None,
            'preview_video': None,
            'duration': '00:00:00',
            'release_date': '1970-01-01',
            'code': '',
            'actresses': [],
            'genres': [],
            'series': '',
            'maker': '',
            'magnets': [],
            'likes': 0,
            'watch_urls_info': []
        }
        
        try:
            # 提取标题
            title_elem = soup.select_one('h1')
            if title_elem:
                info['title'] = title_elem.get_text(strip=True)

            # 提取封面图和预览视频
            player = soup.select_one('#player')
            if player:
                info['cover_image'] = player.get('data-poster')
                video = player.select_one('video')
                if video:
                    info['preview_video'] = video.get('src')

            # 提取详细信息
            for div in soup.find_all('div'):
                label_span = div.select_one('span:first-child')
                if not label_span:
                    continue
                    
                label = label_span.get_text(strip=True).rstrip(':').lower()
                value_span = div.select_one('span:nth-child(2)')
                if not value_span:
                    continue

                if label == 'code':
                    code_text = value_span.get_text(strip=True)
                    code_match = re.match(r'^([A-Z]+-\d+)', code_text)
                    if code_match:
                        info['code'] = code_match.group(1)
                elif label == 'release date':
                    info['release_date'] = value_span.get_text(strip=True)
                elif label == 'runtime':
                    info['duration'] = value_span.get_text(strip=True)
                elif label == 'actresses':
                    actresses = value_span.select('a')
                    info['actresses'] = [a.get_text(strip=True) for a in actresses]
                elif label == 'genres':
                    genres = value_span.select('a')
                    info['genres'] = [g.get_text(strip=True) for g in genres]
                elif label == 'maker':
                    maker = value_span.select_one('a')
                    if maker:
                        info['maker'] = maker.get_text(strip=True)

            # 提取磁力链接
            magnets_div = soup.select('.magnet')
            for magnet in magnets_div:
                magnet_link = magnet.select_one('a')
                if not magnet_link:
                    continue
                    
                magnet_url = magnet_link.get('href')
                if not magnet_url:
                    continue
                    
                name_elem = magnet_link.select_one('.name')
                details = magnet_link.select('.detail-item')
                
                magnet_info = {
                    'url': magnet_url,
                    'name': name_elem.get_text(strip=True) if name_elem else '',
                    'size': details[0].get_text(strip=True) if len(details) > 0 else '',
                    'date': details[1].get_text(strip=True) if len(details) > 1 else ''
                }
                info['magnets'].append(magnet_info)

            # 提取点赞数
            favourite_counter = soup.select_one('.favourite span[ref="counter"]')
            if favourite_counter:
                try:
                    info['likes'] = int(favourite_counter.get_text(strip=True))
                except (ValueError, TypeError):
                    pass

            # 不再添加预览视频到 watch_urls_info
            info['watch_urls_info'] = []

            return info
            
        except Exception as e:
            self._logger.error(f"Error parsing video info: {str(e)}")
            self._logger.debug("HTML content:", soup.prettify()[:1000])
            return None
        
    def _get_movie_detail(self, movie):
        """Get complete details for a single movie.
        
        Args:
            movie (dict): Movie information containing at least a 'url' key
            
        Returns:
            dict: Complete movie details or None if extraction fails
        """
        if not movie or not isinstance(movie, dict) or 'url' not in movie:
            self._logger.error("Invalid movie input: must be a dictionary with 'url' key")
            return None
            
        try:
            # Step 1: Fetch and parse the movie detail page
            self._logger.info(f"Fetching movie details from: {movie['url']}")
            response = self._session.get(movie['url'], timeout=10)
            
            if response.status_code != 200:
                self._logger.error(f"Failed to fetch movie page: HTTP {response.status_code}")
                return None
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Initialize video info with basic data
            video_info = {
                'url': movie['url'],
                'id': self._extract_movie_id(soup, movie['url'])
            }
            
            if not video_info['id']:
                self._logger.error("Failed to extract movie ID")
                return None
            
            # Parse detailed information
            parsed_info = self._parse_video_info(soup)
            if not parsed_info:
                self._logger.error("Failed to parse video info from page")
                return None
            
            video_info.update(parsed_info)
            
            # Get video URLs info
            watch_urls_info, download_urls_info = self._get_video_urls(video_info['id'])
            
            # 处理 watch_urls_info
            if watch_urls_info:
                # 确保每个watch URL都是m3u8格式
                m3u8_urls = []
                for watch_info in watch_urls_info:
                    # 获取m3u8 URL
                    m3u8_result = self._extract_m3u8_from_player(watch_info['url'], video_info.get('cover_image', ''))
                    if m3u8_result and m3u8_result.get('m3u8_url'):
                        m3u8_urls.append({
                            'index': watch_info['index'],
                            'name': watch_info['name'],
                            'url': m3u8_result['m3u8_url']
                        })
                video_info['watch_urls_info'] = m3u8_urls
            else:
                video_info['watch_urls_info'] = []
                
            # 处理 download_urls_info
            if download_urls_info:
                # 确保每个download URL都有正确的格式
                video_info['download_urls_info'] = download_urls_info
            else:
                # 如果没有download URLs，使用磁力链接作为下载链接
                video_info['download_urls_info'] = [{
                    'host': 'Magnet',
                    'index': idx,
                    'name': magnet.get('name', str(idx + 1)),
                    'url': magnet['url']
                } for idx, magnet in enumerate(video_info.get('magnets', []))]
            
            # 设置默认值
            video_info.setdefault('title', '')
            video_info.setdefault('duration', '00:00:00')
            video_info.setdefault('release_date', '1970-01-01')
            video_info.setdefault('code', '')
            video_info.setdefault('actresses', [])
            video_info.setdefault('genres', [])
            video_info.setdefault('maker', 'Das!')  # 直接设置为 Das!
            video_info.setdefault('series', '')
            video_info.setdefault('likes', 0)
            video_info.setdefault('magnets', [])
            
            # 从标题中提取演员名字作为默认演员
            if not video_info['actresses'] and video_info['title']:
                actress_match = re.search(r'-\s*([^-]+?)\s*$', video_info['title'])
                if actress_match:
                    actress_name = actress_match.group(1).strip()
                    if actress_name:
                        video_info['actresses'] = [actress_name]

            # 从标题中提取类型作为默认类型
            if not video_info['genres'] and video_info['title']:
                if '[Uncensored Leaked]' in video_info['title']:
                    video_info['genres'] = ['Uncensored', 'Leaked']
            
            # Validate the final video_info
            if not self._validate_video_info(video_info):
                self._logger.error("Final video info validation failed")
                return None
                
            return video_info
            
        except Exception as e:
            self._logger.error(f"Error getting movie detail: {str(e)}")
            import traceback
            self._logger.error(f"Traceback: {traceback.format_exc()}")
            return None
            
    def _validate_video_info(self, video_info):
        """Validate the video information dictionary.
        
        Args:
            video_info (dict): Video information to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        required_fields = {
            'url': str,
            'id': str,
            'title': str,
            'duration': str,
            'release_date': str,
            'code': str,
            'actresses': list,
            'genres': list,
            'maker': str,
            'series': str,
            'likes': int,
            'magnets': list
        }
        
        try:
            # Check all required fields exist and have correct types
            for field, field_type in required_fields.items():
                if field not in video_info:
                    self._logger.error(f"Missing required field: {field}")
                    return False
                if not isinstance(video_info[field], field_type):
                    self._logger.error(f"Invalid type for field {field}: expected {field_type}, got {type(video_info[field])}")
                    return False
            
            # Additional validation for URL format
            if not video_info['url'].startswith(('http://', 'https://')):
                self._logger.error("Invalid URL format")
                return False
                
            return True
            
        except Exception as e:
            self._logger.error(f"Error validating video info: {str(e)}")
            return False

    def _extract_movie_id(self, soup, fallback_url):
        """Extract movie ID from HTML content.
        
        Args:
            soup (BeautifulSoup): Parsed HTML
            fallback_url (str): URL to extract ID from if page parsing fails
            
        Returns:
            str: Movie ID or None if no valid ID found
        """
        try:
            # 1. 从 v-scope 属性中提取
            video_scope = soup.select_one('#page-video')
            if video_scope:
                scope_attr = video_scope.get('v-scope')
                if scope_attr:
                    self._logger.info(f"Found v-scope attribute: {scope_attr}")
                    # 尝试匹配 Movie({id: xxx, code: xxx}) 格式
                    id_match = re.search(r'Movie\(\{id:\s*(\d+),\s*code:', scope_attr)
                    if id_match:
                        movie_id = id_match.group(1)
                        self._logger.info(f"Extracted ID from v-scope: {movie_id}")
                        return movie_id

            # 2. 从 meta 标签提取
            meta_movie = soup.find('meta', {'name': 'movie-id'})
            if meta_movie and meta_movie.get('content'):
                movie_id = meta_movie.get('content')
                self._logger.info(f"Extracted ID from meta tag: {movie_id}")
                return movie_id

            # 3. 从 script 标签中提取
            scripts = soup.find_all('script')
            for script in scripts:
                if not script.string:
                    continue
                    
                # 尝试匹配 MOVIE_ID = xxx 格式
                if 'MOVIE_ID' in script.string:
                    match = re.search(r'MOVIE_ID\s*=\s*[\'"]?(\d+)[\'"]?', script.string)
                    if match:
                        movie_id = match.group(1)
                        self._logger.info(f"Extracted ID from MOVIE_ID: {movie_id}")
                        return movie_id

            # 4. 从 URL 中提取作为最后的备选
            code_match = re.search(r'/v/([a-zA-Z]+-\d+)', fallback_url)
            if code_match:
                movie_code = code_match.group(1)
                self._logger.info(f"Using movie code as ID: {movie_code}")
                return movie_code
                
            self._logger.error(f"Failed to extract movie ID from HTML content")
            return None

        except Exception as e:
            self._logger.error(f"Error extracting movie ID: {str(e)}")
            self._logger.error(f"HTML content of #page-video: {soup.select_one('#page-video')}")
            return None

    

    def _parse_player_page(self, html_content):
        """Parse player page to extract stream data.
        
        Args:
            html_content (str): HTML content of player page
            
        Returns:
            dict: Stream data containing 'stream' and 'vtt' URLs
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            player_div = soup.find('div', id='player')
            
            if not player_div:
                self._logger.error("Player div not found")
                return None
                
            v_scope = player_div.get('v-scope', '')
            if not v_scope:
                self._logger.error("v-scope attribute not found")
                return None
                
            # Extract JSON data from v-scope
            json_data = self._extract_json_from_vscope(v_scope)
            if not json_data:
                return None
                
            if 'stream' not in json_data or 'vtt' not in json_data:
                self._logger.error("Stream or VTT URL not found in JSON data")
                return None
                
            return json_data
            
        except Exception as e:
            self._logger.error(f"Error parsing player page: {str(e)}")
            return None

    def _extract_json_from_vscope(self, v_scope):
        """Extract and parse JSON data from v-scope attribute.
        
        Args:
            v_scope (str): v-scope attribute content
            
        Returns:
            dict: Parsed JSON data
        """
        try:
            # Find JSON object in v-scope
            json_start = v_scope.find('{', v_scope.find(','))
            if json_start == -1:
                return None
                
            # Track nested braces to find end of JSON
            brace_count = 1
            json_end = json_start + 1
            
            while brace_count > 0 and json_end < len(v_scope):
                if v_scope[json_end] == '{':
                    brace_count += 1
                elif v_scope[json_end] == '}':
                    brace_count -= 1
                json_end += 1
                
            if brace_count > 0:
                return None
                
            # Parse JSON
            json_str = v_scope[json_start:json_end].replace('"', '"')
            return json.loads(json_str)
            
        except Exception as e:
            self._logger.error(f"Error extracting JSON from v-scope: {str(e)}")
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

    def _extract_m3u8_from_player(self, player_url, cover_url):
        """Extract M3U8 URL from player page.
        
        Args:
            player_url (str): Player page URL
            cover_url (str): Cover image URL
            
        Returns:
            dict: Dictionary containing m3u8_url and vtt_url
        """
        try:
            # 构造完整的播放器URL
            encoded_cover = urllib.parse.quote(cover_url)
            full_url = f"{player_url}?poster={encoded_cover}"
            
            # 获取播放器页面
            response = self._session.get(full_url, timeout=10)
            if response.status_code != 200:
                return None
                
            # 解析页面获取m3u8 URL
            stream_data = self._parse_player_page(response.text)
            if not stream_data:
                return None
                
            return {
                'm3u8_url': stream_data.get('stream'),
                'vtt_url': stream_data.get('vtt')
            }
            
        except Exception as e:
            self._logger.error(f"Error extracting m3u8 URL: {str(e)}")
            return None
