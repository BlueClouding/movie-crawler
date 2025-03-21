"""Movie parser module for extracting movie data from HTML."""

import logging
import re
import json
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
from httpx import Response
from crawler.service.movie_detail_info import _extract_m3u8_from_player
from common.db.entity.movie import Movie
from crawler.utils.http import create_session
from common.db.entity.movie import MovieStatus

class MovieParser:
    """Parser for movie detail pages."""
    
    def __init__(self):
        """Initialize MovieParser."""
        self._logger = logging.getLogger(__name__)
        self._session = create_session(use_proxy=True)

    
    def parse_movie_page(self, movie: Movie, html_content: str, url: str) -> Optional[Movie]:
        """Get complete details for a single movie.
            Args:
                movie (Movie): Movie object to process
                html_content (str): HTML content of the movie page
                url (str): URL of the movie page
                
            Returns:
                Optional[Movie]: Complete movie details or None if extraction fails
        """
        if not html_content or not isinstance(html_content, str) or not url:
            self._logger.error("Invalid input: must be a string with 'url' key")
            return None
            
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取标题
            title_tag = soup.find('h1')
            if title_tag:
                movie.title = title_tag.get_text(strip=True)

            # 提取代码
            code_tag = soup.find('span', text='コード:')
            if code_tag:
                code = code_tag.find_next('span')
                if code:
                    movie.code = code.get_text(strip=True)

            # 提取发布日期
            release_date_tag = soup.find('span', text='リリース日:')
            if release_date_tag:
                release_date = release_date_tag.find_next('span')
                if release_date:
                    movie.release_date = release_date.get_text(strip=True)

            # 提取时长
            duration_tag = soup.find('span', text='再生時間:')
            if duration_tag:
                duration = duration_tag.find_next('span')
                if duration:
                    movie.duration = duration.get_text(strip=True)

            # 提取演员
            actress_tag = soup.find('span', text='女優:')
            if actress_tag:
                actress_span = actress_tag.find_next('span')
                if actress_span:
                    actress_name = actress_span.get_text(strip=True)
                    if actress_name:
                        movie.actresses = [actress_name]

            # 提取类型
            genres_tag = soup.find('span', text='ジャンル:')
            if genres_tag:
                genres_span = genres_tag.find_next('span')
                if genres_span:
                    genre_links = genres_span.find_all('a')
                    movie.genres = [genre.get_text(strip=True) for genre in genre_links]

            # 提取制作商
            maker_tag = soup.find('span', text='メーカー:')
            if maker_tag:
                maker_span = maker_tag.find_next('span')
                if maker_span:
                    maker_name = maker_span.get_text(strip=True)
                    if maker_name:
                        movie.maker = maker_name

            # 提取系列（从“ラベル:”中提取）
            series_tag = soup.find('span', text='ラベル:')
            if series_tag:
                series_span = series_tag.find_next('span')
                if series_span:
                    series_name = series_span.get_text(strip=True)
                    if series_name:
                        movie.series = series_name

            # 提取“喜欢”数量
            likes_button = soup.find('button', class_='favourite')
            if likes_button:
                likes_span = likes_button.find('span', ref='counter')
                if likes_span:
                    likes_text = likes_span.get_text(strip=True)
                    if likes_text.isdigit():
                        movie.likes = int(likes_text)

            # 提取描述（从 meta 标签中获取）
            description_meta = soup.find('meta', attrs={'name': 'description'})
            if description_meta and description_meta.get('content'):
                movie.description = description_meta['content'].strip()

            # 提取标签
            tags_tag = soup.find('span', text='タグ:')
            if tags_tag:
                tags_span = tags_tag.find_next('span')
                if tags_span:
                    tags = [a.get_text(strip=True) for a in tags_span.find_all('a')]
                    movie.tags = tags

            # 提取导演（HTML 中无此信息，保持默认值）
            director_tag = soup.find('span', text='監督:')
            if director_tag:
                director = director_tag.find_next('span')
                if director:
                    movie.director = director.get_text(strip=True)

            # 提取封面图像 URL 和预览视频 URL
            video_tag = soup.find('video')
            if video_tag:
                movie.cover_image_url = video_tag.get('poster', '')
                movie.preview_video_url = video_tag.get('src', '')

            # 提取缩略图（HTML 中无明确缩略图，暂用封面图像）
            if movie.cover_image_url:
                movie.thumbnail = movie.cover_image_url

            movie.status = MovieStatus.ONLINE.value
            return movie
        except Exception as e:
            self._logger.error(f"Error getting movie detail: {str(e)}")
            import traceback
            self._logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    # todo
    def get_download_url_and_watch_url(self, movie_id: int) :
        # Get video URLs info (保持不变)
        watch_urls_info, download_urls_info = self._get_video_urls(movie_id)
            
        # 处理 watch_urls_info - 序列化为JSON字符串
        if watch_urls_info:
            m3u8_urls = []
            for watch_info in watch_urls_info:
                m3u8_result = _extract_m3u8_from_player(watch_info['url'], movie.cover_image_url)
                if m3u8_result and m3u8_result.get('m3u8_url'):
                    m3u8_urls.append({
                        'index': watch_info['index'],
                        'name': watch_info['name'],
                        'url': m3u8_result['m3u8_url']
                    })
                # 将列表序列化为JSON字符串
                movie.watch_urls_info = json.dumps(m3u8_urls)
        else:
            movie.watch_urls_info = json.dumps([])
                
        # 处理 download_urls_info - 序列化为JSON字符串
        if download_urls_info:
            movie.download_urls_info = json.dumps(download_urls_info)
        else:
            if movie.magnets is not None:
                movie.download_urls_info = json.dumps(movie.magnets)
            else:
                movie.download_urls_info = json.dumps([])
        
    def extract_movie_links(self, html_content: str, base_url: str) -> List[Movie]:
        """Extract movie links from a page.
        
        Args:
            html_content: HTML content
            base_url: Base URL for the website
            
        Returns:
            list: List of movie data dictionaries
        """
        try:
            self._logger.info(f"Extracting movie links from HTML content (length: {len(html_content)})")
            soup = BeautifulSoup(html_content, 'html.parser')
            movies = []
            
            # Try different selectors for movie items
            selectors = [
                '.movie-item',
                '.video-item',
                '.item',
                '.box-item',  # 根据测试脚本发现的选择器
                '.movie-box',
                '.video-box',
                '.thumbnail',
                '.movie',
                '.video',
                '.col-6 .box-item'  # 根据提供的HTML结构添加
            ]
            
            for selector in selectors:
                items = soup.select(selector)
                if items:
                    self._logger.info(f"Found {len(items)} items using selector: {selector}")
                    for item in items:
                        try:
                            movie = Movie()
                            
                            # 提取电影代码和ID
                            favourite_div = item.select_one('.favourite')
                            if favourite_div:
                                # 从data-code属性中提取电影代码
                                movie_code = favourite_div.get('data-code', '')
                                if movie_code:
                                    movie.code = movie_code
                                
                                # 从v-scope属性中提取电影ID
                                v_scope = favourite_div.get('v-scope', '')
                                if v_scope:
                                    # 使用正则表达式提取ID
                                    id_match = re.search(r"Favourite\('movie', (\d+)", v_scope)
                                    if id_match:
                                        movie.original_id = int(id_match.group(1))
                            
                            # 提取电影标题
                            # 首先尝试从detail区域获取标题
                            detail_div = item.select_one('.detail a')
                            if detail_div:
                                title = detail_div.get_text(strip=True)
                                if title:
                                    movie.title = title
                                
                                # 获取链接
                                url = detail_div.get('href', '')
                                movie.link = f'{base_url}/{url}'
                            
                            # Get thumbnail
                            img = item.select_one('img')
                            if img:
                                thumbnail = img.get('src', '')
                                if not thumbnail:
                                    # 如果没有src属性，尝试使用data-src属性
                                    thumbnail = img.get('data-src', '')
                                    
                                if thumbnail:
                                    # 处理缓存图片URL
                                    if not thumbnail.startswith('http'):
                                        if thumbnail.startswith('/'):
                                            thumbnail = f'{base_url}/{thumbnail}'
                                        else:
                                            thumbnail = f'{base_url}/{thumbnail}'
                                            
                                    movie.thumbnail = thumbnail     
                            
                            # Get duration
                            duration_elem = item.select_one('.duration')
                            if duration_elem:
                                movie.duration = duration_elem.get_text(strip=True)
                            
                            # 如果有URL就添加，不必要求有code
                            if movie.link:
                                self._logger.info(f"Found movie: {movie}")
                                movies.append(movie)
                            else:
                                self._logger.warning(f"Skipping movie without URL: {movie}")
                                
                        except Exception as e:
                            self._logger.error(f"Error processing movie item: {str(e)}")
                            continue
                            
                    # 如果找到了电影，就不再尝试其他选择器
                    if movies:
                        self._logger.info(f"Successfully extracted {len(movies)} movies using selector: {selector}")
                        break
            
            self._logger.info(f"Extracted {len(movies)} movies in total")
            return movies
            
        except Exception as e:
            self._logger.error(f"Error extracting movie links: {str(e)}")
            return []


    def _get_video_urls(self, video_id) -> tuple:
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
                logging.info(f"Requesting ajax endpoint: {ajax_url}")
                
                response: Response = self._session.get(ajax_url, timeout=10)
                
                if response.status_code != 200:
                    logging.error(f"Failed to fetch video URLs: {response.status_code}")
                    return [], []
                    
                data : Dict[str, Any] = response.json()
                if not data.get('status') == 200 or not data.get('result'):
                    logging.error("Invalid ajax response format")
                    return [], []
                    
                watch_urls = data['result'].get('watch', [])
                download_urls = data['result'].get('download', [])
                
                # Validate watch URLs format
                for url_info in watch_urls:
                    if not all(k in url_info for k in ('index', 'name', 'url')):
                        logging.error(f"Invalid watch URL info format: {url_info}")
                        return [], []
                        
                # Validate download URLs format
                for url_info in download_urls:
                    if not all(k in url_info for k in ('host', 'index', 'name', 'url')):
                        logging.error(f"Invalid download URL info format: {url_info}")
                        return [], []
                
                return watch_urls, download_urls
                
            except Exception as e:
                logging.error(f"Error getting video URLs: {str(e)}")
                return [], []
