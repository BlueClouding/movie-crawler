from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
import re
from ..utils.http import create_session
import urllib
import logging
from httpx import Response
import json
from sqlalchemy.ext.asyncio import AsyncSession

class MovieDetailInfoService:
    def __init__(self, db: AsyncSession):
        self._db = db

def _extract_movie_id(soup: BeautifulSoup, fallback_url: str) -> Optional[str]:
        """Extract movie ID from HTML content using multiple strategies.
        
        Args:
            soup: Parsed HTML content
            fallback_url: URL to extract ID from if page parsing fails
            
        Returns:
            Extracted movie ID or None if no valid ID found
        """
        try:
            # Strategy 1: Extract from v-scope attribute
            video_scope = soup.select_one('#page-video')
            if video_scope and (scope_attr := video_scope.get('v-scope')):
                # Match Movie({id: xxx, code: xxx}) pattern
                if (id_match := re.search(r'Movie\(\{id:\s*(\d+),\s*code:', scope_attr)):
                    movie_id = id_match.group(1)
                    return movie_id

            # Strategy 2: Extract from meta tag
            if (meta_movie := soup.find('meta', {'name': 'movie-id'})) and \
               (movie_id := meta_movie.get('content')):
                return movie_id

            # Strategy 3: Extract from script tags
            for script in soup.find_all('script'):
                if script.string and 'MOVIE_ID' in script.string:
                    if (match := re.search(r'MOVIE_ID\s*=\s*[\'"]?(\d+)[\'"]?', script.string)):
                        movie_id = match.group(1)
                        return movie_id

            # Strategy 4: Extract from URL as fallback
            if (code_match := re.search(r'/v/([a-zA-Z]+-\d+)', fallback_url)):
                movie_code = code_match.group(1)
                return movie_code
                
            return {}

        except Exception as e:
            return {}
        
def _get_movie_detail(session, movie: Dict[str, Any], response: Response) -> Dict[str, Any]:
    """Get complete details for a single movie.
    
    Args:
        movie (dict): Movie information containing at least a 'url' key
        
    Returns:
        dict: Complete movie details or empty dict if extraction fails
    """
    if not movie or not isinstance(movie, dict) or 'url' not in movie:
        logging.error("Invalid movie input: must be a dictionary with 'url' key")
        return {}       
    try:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Initialize video info with basic data
        video_info = {
            'url': movie['url'],
            'id': movie['id']
        }
        
        if not video_info['id']:
            logging.error("Failed to extract movie ID")
            return {}
        
        # 暂时跳过获取视频URL的步骤，用于调试
        logging.info(f"Skipping video URL extraction for movie ID: {video_info['id']}")
        video_info['watch_urls_info'] = []
        video_info['download_urls_info'] = []
        
        # 设置默认值
        video_info.setdefault('title', '')
        video_info.setdefault('duration', '00:00:00')
        video_info.setdefault('release_date', '1970-01-01')
        video_info.setdefault('code', '')
        video_info.setdefault('actresses', [])
        video_info.setdefault('genres', [])
        video_info.setdefault('maker', 'Das!')  # Default maker is Das!
        video_info.setdefault('series', '')
        video_info.setdefault('likes', 0)
        video_info.setdefault('magnets', [])
        video_info.setdefault('description', '')
        video_info.setdefault('tags', [])
        video_info.setdefault('director', '')

        # 提取导演
        director_tag = soup.find('span', text='監督:')
        if director_tag:
            director = director_tag.find_next('span')
            if director:
                video_info['director'] = director.get_text(strip=True)

        # 提取标题
        title_tag = soup.find('h1')
        if title_tag:
            video_info['title'] = title_tag.get_text(strip=True)

        # 提取封面图和预览视频
        player = soup.select_one('#player')
        if player:
            video_info['cover_image'] = player.get('data-poster')
            video = player.select_one('video')
            if video:
                video_info['preview_video'] = video.get('src')


        # Extract the code
        code_div = soup.find('span', text='コード:')
        if code_div:
            code_span = code_div.find_next('span')
            if code_span:
                video_info['code'] = code_span.get_text(strip=True)

        # 提取发布日期
        release_date_tag = soup.find('span', text='リリース日:')
        if release_date_tag:
            release_date = release_date_tag.find_next('span')
            if release_date:
                video_info['release_date'] = release_date.get_text(strip=True)

        # 提取时长
        duration_tag = soup.find('span', text='再生時間:')
        if duration_tag:
            duration = duration_tag.find_next('span')
            if duration:
                video_info['duration'] = duration.get_text(strip=True)

        # 提取演员
        actress_tag = soup.find('span', text='女優:')
        if actress_tag:
            actress = actress_tag.find_next('span')
            if actress:
                actress_name = actress.get_text(strip=True)
                if actress_name:
                    video_info['actresses'] = [actress_name]

        # 提取类型
        genres_tag = soup.find('span', text='ジャンル:')
        if genres_tag:
            genres = genres_tag.find_next('span')
            if genres:
                genre_links = genres.find_all('a')
                video_info['genres'] = [genre.get_text(strip=True) for genre in genre_links]

        # 提取制作商
        maker_tag = soup.find('span', text='メーカー:')
        if maker_tag:
            maker = maker_tag.find_next('span')
            if maker:
                maker_name = maker.get_text(strip=True)
                if maker_name:
                    video_info['maker'] = maker_name

        # 提取描述
        description_tag = soup.find('div', class_='description')
        if description_tag:
            video_info['description'] = description_tag.get_text(strip=True)

        # 提取tags
        tags_div = soup.find('div', text='タグ:')
        if tags_div:
            tags_span = tags_div.find_next('span')
            if tags_span:
                tags = [a_tag.get_text() for a_tag in tags_span.find_all('a')]
                video_info['tags'] = tags

        return video_info
        
    except Exception as e:
        logging.error(f"Error getting movie detail: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return {}


def _parse_player_page(html_content):
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
            logging.error("Player div not found")
            return {}
            
        v_scope = player_div.get('v-scope', '')
        if not v_scope:
            logging.error("v-scope attribute not found")
            return {}
            
        # Extract JSON data from v-scope
        json_data = _extract_json_from_vscope(v_scope)
        if not json_data:
            return {}
            
        if 'stream' not in json_data or 'vtt' not in json_data:
            logging.error("Stream or VTT URL not found in JSON data")
            return {}
            
        return json_data
        
    except Exception as e:
        logging.error(f"Error parsing player page: {str(e)}")
        return {}

def _extract_m3u8_from_player(player_url, cover_url):
        """Extract M3U8 URL from player page.
        
        Args:
            player_url (str): Player page URL
            cover_url (str): Cover image URL
            
        Returns:
            dict: Dictionary containing m3u8_url and vtt_url
        """
        try:
            # 验证player_url是否有效
            if not player_url:
                logging.warning("Player URL is empty or None")
                return {}
                
            # 构造完整的播放器URL
            # 确保 cover_url 是字符串类型
            try:
                if cover_url is None:
                    cover_url = ""
                elif isinstance(cover_url, bytes):
                    cover_url = cover_url.decode('utf-8', errors='replace')
                elif not isinstance(cover_url, str):
                    cover_url = str(cover_url)
                    
                # 安全地进行 URL 编码
                try:
                    encoded_cover = urllib.parse.quote(cover_url)
                except Exception as encode_error:
                    logging.warning(f"Error encoding cover URL: {str(encode_error)}. Using empty string instead.")
                    encoded_cover = ""
                    
                full_url = f"{player_url}?poster={encoded_cover}"
            except Exception as url_error:
                logging.warning(f"Error constructing player URL: {str(url_error)}. Using original player URL.")
                full_url = player_url
            
            # 获取播放器页面
            try:
                response = create_session().get(full_url, timeout=15)  # 增加超时时间
                if response.status_code != 200:
                    logging.warning(f"Failed to get player page, status code: {response.status_code}")
                    return {}
            except Exception as request_error:
                logging.error(f"Error requesting player page: {str(request_error)}")
                return {}
                
            # 解析页面获取m3u8 URL
            try:
                stream_data = _parse_player_page(response.text)
                if not stream_data:
                    logging.warning("No stream data found in player page")
                    return {}
                    
                return {
                    'm3u8_url': stream_data.get('stream'),
                    'vtt_url': stream_data.get('vtt')
                }
            except Exception as parse_error:
                logging.error(f"Error parsing player page: {str(parse_error)}")
                return {}
            
        except Exception as e:
            logging.error(f"Error extracting m3u8 URL: {str(e)}")
            return {}

def _extract_json_from_vscope(v_scope):
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
                return {}
                
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
                return {}
                
            # Parse JSON
            json_str = v_scope[json_start:json_end].replace('"', '"')
            return json.loads(json_str)
            
        except Exception as e:
            logging.error(f"Error extracting JSON from v-scope: {str(e)}")
            return {}