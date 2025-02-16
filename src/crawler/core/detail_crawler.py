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
from ..utils.db import DatabaseManager
from concurrent.futures import as_completed
from ..utils.progress_manager import ProgressManager

class DetailCrawler:
    """Crawler for fetching movie details."""
    
    def __init__(self, base_url, language, threads=1):
        """Initialize DetailCrawler.

        Args:
            base_url (str): Base URL for the website
            language (str): Language code
            threads (int): Number of threads to use
        """
        self._base_url = base_url
        self._language = language
        self._threads = threads
        self._logger = logging.getLogger(__name__)
        self._db = DatabaseManager()
        self._progress_manager = ProgressManager(language)
        
        # Create session with retry mechanism
        self._session = create_session(use_proxy=True)

        # Initialize retry counts
        self._retry_counts = {}

    def start(self):
        """Start crawling movie details."""
        try:
            genres = self._get_genres_from_db()
            if not genres:
                self._logger.error("No genres available to process")
                return False

            with ThreadPoolExecutor(max_workers=self._threads) as executor:
                futures = []
                for genre in genres:
                    if not self._progress_manager.is_genre_completed(genre['name']):
                        next_page = self._progress_manager.get_genre_progress(genre['name']) + 1
                        future = executor.submit(
                            self._process_genre_page,
                            genre['name'],
                            genre['url'],
                            next_page
                        )
                        futures.append(future)

                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        self._logger.error(f"Error processing genre page: {str(e)}")
                        continue  # Continue with other genres even if one fails

            return True
        except Exception as e:
            self._logger.error(f"Error in detail crawler: {str(e)}")
            import traceback
            self._logger.error(f"Traceback: {traceback.format_exc()}")
            return False

    def _get_genres_from_db(self):
        """Get genres from database."""
        try:
            with self._db._conn.cursor() as cursor:
                cursor.execute("""
                    SELECT g.id, gn.name 
                    FROM genres g 
                    JOIN genre_names gn ON g.id = gn.genre_id 
                    WHERE gn.language = %s
                """, (self._language,))
                genres = cursor.fetchall()
                if not genres:
                    self._logger.error("No genres found in database")
                    return []
                self._logger.info(f"Found {len(genres)} genres in database")
                
                # 构造genre URLs
                return [{
                    'id': g[0], 
                    'name': g[1],
                    'url': f"http://123av.com/{self._language}/dm3/genres/{g[1].lower().replace(' ', '-').replace('/', '-')}"
                } for g in genres]
        except Exception as e:
            self._logger.error(f"Failed to get genres from database: {str(e)}")
            return []

    def _process_genre_page(self, genre_name, genre_url, page):
        """Process a single genre page."""
        try:
            url = f"{genre_url}?page={page}"
            self._logger.info(f"Processing {genre_name} page {page}")
            
            response = self._session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Save the HTML for debugging
            debug_dir = os.path.join('debug', 'html', 'genre_pages')
            os.makedirs(debug_dir, exist_ok=True)
            safe_name = genre_name.replace('/', '_').replace(' ', '_')
            with open(os.path.join(debug_dir, f'{safe_name}_page_{page}.html'), 'w', encoding='utf-8') as f:
                f.write(soup.prettify())
            
            # Try different selectors for movie items
            selectors = [
                '.movie-box',
                '.movie-item',
                '.video-item',
                '.box-item',
                '.video-box',
                '.video-list-item',
                '.video-grid-item'
            ]
            
            movie_elements = []
            for selector in selectors:
                movie_elements = soup.select(selector)
                if movie_elements:
                    self._logger.info(f"Found {len(movie_elements)} movies with selector: {selector}")
                    break
            
            if not movie_elements:
                # Try finding any links that look like movie links
                movie_links = soup.find_all('a', href=re.compile(r'/v/[a-zA-Z0-9-]+'))
                if movie_links:
                    self._logger.info(f"Found {len(movie_links)} movie links")
                    movie_elements = movie_links
                else:
                    self._logger.info(f"No more movies found for {genre_name} at page {page}")
                    self._progress_manager.update_genre_progress(genre_name, -1)  # Mark as completed
                    return
            
            movies = []
            for element in movie_elements:
                # Get movie URL
                if isinstance(element, str):
                    movie_url = element
                else:
                    movie_url = element.get('href')
                
                if not movie_url:
                    continue
                
                # Ensure URL is absolute
                if not movie_url.startswith('http'):
                    if not movie_url.startswith('/'):
                        movie_url = f'/{movie_url}'
                    movie_url = f"http://123av.com{movie_url}"
                
                movie_info = self._process_movie_detail(movie_url)
                if movie_info:
                    movies.append(movie_info)
            
            if movies:
                self._save_movies_to_db(movies)
                self._progress_manager.update_genre_progress(genre_name, page)
                self._progress_manager.update_detail_progress(genre_name, len(movies))
            
            # Add delay before next request
            time.sleep(random.uniform(1, 3))
            
            # Continue to next page if we found movies on this page
            if len(movies) > 0:
                self._process_genre_page(genre_name, genre_url, page + 1)
            
        except Exception as e:
            self._logger.error(f"Error processing {genre_name} page {page}: {str(e)}")
            import traceback
            self._logger.error(f"Traceback: {traceback.format_exc()}")
            raise

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

    def _get_genres(self):
        """Get list of genres from the website.
        
        Returns:
            list: List of genre names
        """
        try:
            url = f"{self._base_url}/genres"
            response = self._session.get(url, timeout=10)
            if response.status_code != 200:
                self._logger.error(f"Failed to fetch genres: HTTP {response.status_code}")
                return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            genre_links = soup.select('.genre-item a')
            
            genres = []
            for link in genre_links:
                genre_name = link.get_text(strip=True)
                if genre_name:
                    genres.append(genre_name)
                    
            self._logger.info(f"Found {len(genres)} genres")
            return genres
            
        except Exception as e:
            self._logger.error(f"Error getting genres: {str(e)}")
            return []
            
    def _get_genre_movies(self, genre_name):
        """Get list of movies for a genre.
        
        Args:
            genre_name (str): Name of the genre
            
        Returns:
            list: List of movie dictionaries
        """
        try:
            url = f"{self._base_url}/genres/{genre_name}"
            response = self._session.get(url, timeout=10)
            if response.status_code != 200:
                self._logger.error(f"Failed to fetch movies for genre {genre_name}: HTTP {response.status_code}")
                return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            movie_items = soup.select('.movie-item')
            
            movies = []
            for item in movie_items:
                link = item.select_one('a')
                if not link:
                    continue
                    
                movie = {
                    'url': link.get('href'),
                    'title': link.get('title', '').strip()
                }
                movies.append(movie)
                
            self._logger.info(f"Found {len(movies)} movies for genre {genre_name}")
            return movies
            
        except Exception as e:
            self._logger.error(f"Error getting movies for genre {genre_name}: {str(e)}")
            return []

    def _save_movies_to_db(self, movies):
        """Save movies to database.
        
        Args:
            movies (list): List of movie dictionaries
        """
        try:
            for movie in movies:
                try:
                    movie_id = self._db.save_movie(movie)
                    if movie_id:
                        self._logger.info(f"Successfully saved movie {movie.get('code', 'Unknown')} to database")
                    else:
                        self._logger.error(f"Failed to save movie {movie.get('code', 'Unknown')}")
                except Exception as e:
                    self._logger.error(f"Error saving movie {movie.get('code', 'Unknown')}: {str(e)}")
                    continue
        except Exception as e:
            self._logger.error(f"Error in _save_movies_to_db: {str(e)}")
            raise

    def _process_movie_detail(self, movie_url):
        """Process movie detail page.
        
        Args:
            movie_url (str): URL of the movie detail page
            
        Returns:
            dict: Movie information dictionary
        """
        try:
            self._logger.info(f"Processing movie detail: {movie_url}")
            
            # 获取页面内容
            response = requests.get(movie_url)
            response.raise_for_status()
            
            # 解析页面
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取电影信息
            movie_info = {
                'url': movie_url,
                'title': '',
                'code': '',
                'duration': '00:00:00',
                'release_date': '1970-01-01',
                'actresses': [],
                'genres': [],
                'maker': 'Das!',
                'series': '',
                'likes': 0,
                'magnets': [],
                'watch_urls_info': [],
                'download_urls_info': []
            }
            
            # 提取标题
            title_elem = soup.select_one('h1')
            if title_elem:
                movie_info['title'] = title_elem.text.strip()
            
            # 提取代码
            code_elem = soup.select_one('.movie-info-code')
            if code_elem:
                code_text = code_elem.text.strip()
                code_match = re.search(r'([A-Z]+-\d+)', code_text)
                if code_match:
                    movie_info['code'] = code_match.group(1)
            
            # 提取时长
            duration_elem = soup.select_one('.movie-info-duration')
            if duration_elem:
                movie_info['duration'] = duration_elem.text.strip()
            
            # 提取发布日期
            date_elem = soup.select_one('.movie-info-date')
            if date_elem:
                movie_info['release_date'] = date_elem.text.strip()
            
            # 提取演员
            actress_elems = soup.select('.movie-info-actresses a')
            movie_info['actresses'] = [elem.text.strip() for elem in actress_elems]
            
            # 提取类型
            genre_elems = soup.select('.movie-info-genres a')
            movie_info['genres'] = [elem.text.strip() for elem in genre_elems]
            
            # 提取磁力链接
            magnet_elems = soup.select('.movie-info-magnets a')
            for elem in magnet_elems:
                magnet_info = {
                    'url': elem.get('href', ''),
                    'name': elem.text.strip(),
                    'size': elem.get('data-size', ''),
                    'date': elem.get('data-date', '')
                }
                movie_info['magnets'].append(magnet_info)
            
            # 提取观看链接
            watch_elems = soup.select('.movie-info-watch a')
            for idx, elem in enumerate(watch_elems):
                watch_info = {
                    'index': idx,
                    'name': elem.text.strip(),
                    'url': elem.get('href', '')
                }
                movie_info['watch_urls_info'].append(watch_info)
            
            # 提取下载链接
            download_elems = soup.select('.movie-info-download a')
            for idx, elem in enumerate(download_elems):
                download_info = {
                    'index': idx,
                    'name': elem.text.strip(),
                    'url': elem.get('href', ''),
                    'host': elem.get('data-host', '')
                }
                movie_info['download_urls_info'].append(download_info)
            
            return movie_info
            
        except Exception as e:
            self._logger.error(f"Error processing movie detail {movie_url}: {str(e)}")
            return None
