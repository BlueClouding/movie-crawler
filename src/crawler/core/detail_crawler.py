"""Detail crawler module for fetching movie details."""

import logging
import os
import json
import time
import random
import ssl
import urllib.parse
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
    
    def _extract_m3u8_info(self, image_url):
        """Extract M3U8 and VTT information from javplayer.
        
        Args:
            image_url (str): URL of the movie poster
            
        Returns:
            tuple: (m3u8_url, vtt_url) or (None, None) if extraction fails
        """
        try:
            encoded_poster = urllib.parse.quote(image_url)
            player_url = f"https://javplayer.me/e/8WZOMOV8?poster={encoded_poster}"
            
            self._logger.info(f"Requesting player URL: {player_url}")
            
            time.sleep(random.uniform(1, 3))  # Rate limiting
            
            response = self._session.get(player_url, timeout=10)
            if response.status_code != 200:
                self._logger.error(f"Failed to fetch player page: {response.status_code}")
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
            self._logger.error(f"Error extracting video info: {str(e)}")
            return None, None

    def _parse_video_info(self, soup):
        """Parse video information from the detail page.
        
        Args:
            soup (BeautifulSoup): Parsed HTML
            
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
            'vtt_url': None
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
                m3u8_url, vtt_url = self._extract_m3u8_info(info['cover_image'])
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
            response = self._session.get(movie['url'])
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                video_info = self._parse_video_info(soup)
                
                # 获取 M3U8 和 VTT URL
                if video_info['cover_image']:
                    m3u8_url, vtt_url = self._extract_m3u8_info(video_info['cover_image'])
                    video_info['m3u8_url'] = m3u8_url
                    video_info['vtt_url'] = vtt_url
                
                # 添加原始信息
                movie_id = movie['url'].split('/')[-1]
                video_info['id'] = movie_id
                video_info['url'] = movie['url']
                video_info['duration'] = movie.get('duration')
                
                return video_info
                
        except Exception as e:
            self._logger.error(f"Error getting movie details for {movie['url']}: {str(e)}")
            return None

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
            if self._progress_manager:
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
                        if self._progress_manager:
                            self._progress_manager.update_detail_progress(genre_name, page)
                    else:
                        self._logger.warning(f"No movies found on page {page} for genre: {genre_name}")
                    
                    # Update genre progress
                    if self._progress_manager:
                        self._progress_manager.update_genre_progress(genre_name, page)
                        
                except Exception as e:
                    self._logger.error(f"Error processing page {page} for genre {genre_name}: {str(e)}")
                    import traceback
                    self._logger.error(f"Traceback: {traceback.format_exc()}")
                    # Continue with next page
                    continue
            
            # Mark genre as completed
            if self._progress_manager:
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
        start_index = self.progress_manager.get_detail_progress(genre_name) if self.progress_manager else 0
        
        self.logger.info(f"Processing {len(movie_list[start_index:])} movies for genre: {genre_name}")
        
        for i, movie in enumerate(movie_list[start_index:], start=start_index):
            details = self._get_movie_detail(movie)
            if details:
                self._save_movie_data(details, genre_name)
                
            if self.progress_manager:
                self.progress_manager.update_detail_progress(genre_name, i + 1)
                
            time.sleep(random.uniform(1, 3))  # Rate limiting
            
    def _get_total_pages(self, genre_url):
        """Get total number of pages for a genre.
        
        Args:
            genre_url (str): URL of the genre
            
        Returns:
            int: Total number of pages, or None if failed
        """
        try:
            if not genre_url.startswith('http'):
                genre_url = f"{self._base_url}/{genre_url}"
            
            self._logger.debug(f"Fetching total pages from URL: {genre_url}")
            response = self._session.get(genre_url)
            
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 尝试多个分页选择器
                selectors = [
                    '.pagination .page-item:last-child a',  # Bootstrap 风格
                    '.pager .last a',                       # 通用分页
                    '.pages .last',                         # 简单分页
                    '.page-numbers:last-child'              # WordPress 风格
                ]
                
                for selector in selectors:
                    last_page = soup.select_one(selector)
                    if last_page:
                        # 尝试从 href 获取页数
                        href = last_page.get('href', '')
                        if 'page=' in href:
                            try:
                                return int(href.split('page=')[-1])
                            except ValueError:
                                continue
                        
                        # 尝试从文本获取页数
                        text = last_page.text.strip()
                        try:
                            return int(''.join(filter(str.isdigit, text)))
                        except ValueError:
                            continue
                
                # 如果找不到分页组件，记录页面结构
                self._logger.debug(f"Available classes: {[cls for tag in soup.find_all(class_=True) for cls in tag.get('class', [])][:20]}")
                # 默认返回 1 页
                return 1
                
        except Exception as e:
            self._logger.error(f"Error getting total pages: {str(e)}")
            if hasattr(e, 'response'):
                self._logger.error(f"Response content: {e.response.content[:500]}")
        return None
        
    def _fetch_genre_movies(self, genre_url, page):
        """Fetch movies for a genre page.
        
        Args:
            genre_url (str): URL of the genre
            page (int): Page number to fetch
            
        Returns:
            dict: Dictionary of movies with movie ID as key
        """
        try:
            if not genre_url.startswith('http'):
                genre_url = f"{self._base_url}/{genre_url}"
            url = f"{genre_url}?page={page}"
            self._logger.debug(f"Fetching URL: {url}")
            
            response = self._session.get(url, timeout=30)
            if response.status_code == 200:
                from bs4 import BeautifulSoup
                from urllib.parse import urljoin
                soup = BeautifulSoup(response.text, 'html.parser')
                movies = {}
                
                # 获取所有电影项
                items = soup.select('.box-item')
                self._logger.debug(f"Found {len(items)} movie items")
                
                for item in items:
                    # 获取缩略图链接
                    thumb_link = item.select_one('.thumb a')
                    if not thumb_link:
                        continue
                    
                    url = thumb_link.get('href', '')
                    if not url:
                        continue
                    
                    # 获取标题
                    title = thumb_link.get('title', '')
                    if not title:
                        img = thumb_link.find('img')
                        if img:
                            title = img.get('alt', '')
                    
                    # 获取详细信息
                    detail = item.select_one('.detail a')
                    if detail:
                        detail_text = detail.get_text(strip=True)
                        if detail_text:
                            title = detail_text
                    
                    # 获取时长
                    duration = item.select_one('.duration')
                    duration_text = duration.get_text(strip=True) if duration else ''
                    
                    # 生成电影ID
                    movie_id = url.split('/')[-1]
                    
                    if movie_id and title:
                        # 确保 URL 包含语言路径
                        if url.startswith('http'):
                            final_url = url
                        else:
                            # 如果 URL 不以语言路径开头，添加语言路径
                            if not url.startswith(f'/{self._language}/'):
                                url = f'/{self._language}/{url.lstrip("/")}'
                            final_url = f'http://123av.com{url}'
                        
                        movies[movie_id] = {
                            'id': movie_id,
                            'title': title,
                            'url': final_url,
                            'duration': duration_text
                        }
                
                if movies:
                    self._logger.debug(f"Successfully extracted {len(movies)} movies")
                    return movies
                else:
                    self._logger.warning("No movies found in the page")
                    return None
                
        except Exception as e:
            self._logger.error(f"Error fetching movies for page {page}: {str(e)}")
            if hasattr(e, 'response'):
                self._logger.error(f"Response content: {e.response.content[:500]}")
            import traceback
            self._logger.error(f"Traceback: {traceback.format_exc()}")
        return None
    
    def start(self):
        """Start crawling details for all movies in genre_movie directory."""
        self._logger.info("Starting detail crawler")
        
        # 遍历 genre_movie 目录
        if not os.path.exists(self._source_dir):
            self._logger.error(f"Source directory not found: {self._source_dir}")
            return
        
        # 获取所有类型目录
        genre_dirs = [d for d in os.listdir(self._source_dir) if os.path.isdir(os.path.join(self._source_dir, d))]
        self._logger.info(f"Found {len(genre_dirs)} genre directories")
        
        # 按字母顺序排序
        genre_dirs.sort()
        
        # 使用线程池处理每个类型
        with ThreadPoolExecutor(max_workers=self._threads) as executor:
            # 提交所有任务
            future_to_genre = {executor.submit(self._process_genre_dir, genre_dir): genre_dir 
                              for genre_dir in genre_dirs}
            
            # 等待任务完成并处理结果
            for future in future_to_genre:
                genre_dir = future_to_genre[future]
                try:
                    future.result()  # 等待任务完成
                    self._logger.info(f"Completed genre directory: {genre_dir}")
                except Exception as e:
                    self._logger.error(f"Error processing genre directory {genre_dir}: {str(e)}")
                    import traceback
                    self._logger.error(f"Traceback: {traceback.format_exc()}")
        
        self._logger.info("Detail crawler finished")
    
    def _process_genre_dir(self, genre_dir):
        """Process all JSON files in a genre directory.
        
        Args:
            genre_dir (str): Name of the genre directory
        """
        source_path = os.path.join(self._source_dir, genre_dir)
        target_path = os.path.join(self._base_dir, genre_dir)
        self._logger.info(f"Processing genre directory: {source_path}")
        
        # 创建目标目录
        os.makedirs(target_path, exist_ok=True)
        
        # 获取所有 JSON 文件
        json_files = sorted([f for f in os.listdir(source_path) if f.endswith('.json')],
                           key=lambda x: int(x.split('_page_')[1].split('.')[0]))
        
        # 获取当前进度
        current_file = 0
        if self._progress_manager:
            current_file = self._progress_manager.get_detail_progress(genre_dir)
        
        # 从上次进度继续
        for i, json_file in enumerate(json_files[current_file:], start=current_file):
            try:
                source_file = os.path.join(source_path, json_file)
                target_file = os.path.join(target_path, json_file)
                self._logger.info(f"Processing file {i+1}/{len(json_files)}: {source_file}")
                
                # 如果目标文件已存在且不需要清除，则跳过
                if os.path.exists(target_file) and not self._clear_existing:
                    self._logger.info(f"Target file exists, skipping: {target_file}")
                    continue
                
                # 读取源 JSON 文件
                with open(source_file, 'r', encoding='utf-8') as f:
                    movies = json.load(f)
                
                # 处理每个电影
                for movie_id, movie_data in movies.items():
                    try:
                        # 检查是否已经处理过
                        movie_file = os.path.join(target_path, f"{movie_id}.json")
                        if os.path.exists(movie_file) and not self._clear_existing:
                            self._logger.info(f"Movie file exists, skipping: {movie_file}")
                            continue
                        
                        # 检查重试次数
                        retry_key = f"{genre_dir}/{movie_id}"
                        if retry_key in self._retry_counts and self._retry_counts[retry_key] >= 3:
                            self._logger.warning(f"Movie {movie_id} has failed 3 times, skipping")
                            failed_file = os.path.join(self._failed_dir, genre_dir, f"{movie_id}.json")
                            os.makedirs(os.path.dirname(failed_file), exist_ok=True)
                            with open(failed_file, 'w', encoding='utf-8') as f:
                                json.dump({
                                    'id': movie_id,
                                    'url': movie_data['url'],
                                    'error': f"Failed after {self._retry_counts[retry_key]} retries"
                                }, f, ensure_ascii=False, indent=2)
                            continue
                        
                        # 获取详细信息
                        success = False
                        try:
                            response = self._session.get(movie_data['url'], timeout=30)
                            if response.status_code == 200:
                                soup = BeautifulSoup(response.text, 'html.parser')
                                video_info = self._parse_video_info(soup)
                                
                                # 获取M3U8和VTT URL
                                if video_info['cover_image']:
                                    try:
                                        m3u8_url, vtt_url = self._extract_m3u8_info(video_info['cover_image'])
                                        video_info['m3u8_url'] = m3u8_url
                                        video_info['vtt_url'] = vtt_url
                                    except Exception as e:
                                        self._logger.error(f"Error getting M3U8 info for movie {movie_id}: {str(e)}")
                                        video_info['m3u8_url'] = None
                                        video_info['vtt_url'] = None
                                
                                # 添加原始信息
                                video_info['id'] = movie_id
                                video_info['url'] = movie_data['url']
                                video_info['duration'] = movie_data.get('duration')
                                
                                # 保存到单独文件
                                with open(movie_file, 'w', encoding='utf-8') as f:
                                    json.dump(video_info, f, ensure_ascii=False, indent=2)
                                self._logger.info(f"Saved video details to: {movie_file}")
                                success = True
                            else:
                                self._logger.error(f"Failed to get movie details for {movie_id}: HTTP {response.status_code}")
                        except Exception as e:
                            self._logger.error(f"Error getting movie details for {movie_id}: {str(e)}")
                        
                        # 更新重试计数
                        if not success:
                            self._retry_counts[retry_key] = self._retry_counts.get(retry_key, 0) + 1
                            self._logger.warning(f"Movie {movie_id} failed {self._retry_counts[retry_key]} times")
                        
                        # 添加随机延迟
                        time.sleep(random.uniform(1, 3))
                        
                    except Exception as e:
                        self._logger.error(f"Error processing movie {movie_id}: {str(e)}")
                        continue  # 继续处理下一个电影
                
                # 更新进度
                if self._progress_manager:
                    self._progress_manager.update_detail_progress(genre_dir, i + 1)
                    
            except Exception as e:
                self._logger.error(f"Error processing file {json_file}: {str(e)}")
                continue  # 继续处理下一个文件
