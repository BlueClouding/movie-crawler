"""Test module for parsing video detail pages."""

import unittest
import os
import json
import logging
from bs4 import BeautifulSoup
from src.crawler.utils.http import create_session

class TestVideoParser(unittest.TestCase):
    """Test case for video detail page parsing."""
    
    def setUp(self):
        """Set up test case."""
        self.logger = logging.getLogger(__name__)
        self.session = create_session(use_proxy=True)
        
        # 设置测试数据文件路径
        self.test_file = os.path.join(
            'tests', 'data', 'html_cache', 'mxgs-1329-uncensored-leaked.html'
        )
    
    def test_parse_video_detail(self):
        """Test parsing video detail page."""
        # 读取测试HTML文件
        with open(self.test_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        self.logger.info(f"Testing HTML file: {self.test_file}")
        
        # 解析页面
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 打印页面结构
        self.logger.info("\nPage structure:")
        main_content = soup.find('main') or soup.find('div', class_='main') or soup.find('div', id='main')
        if main_content:
            self.logger.info("Main content structure:")
            for elem in main_content.find_all(['div', 'section'], recursive=False):
                class_str = '.'.join(elem.get('class', [])) if elem.get('class') else ''
                id_str = f'#{elem.get("id")}' if elem.get('id') else ''
                self.logger.info(f"- {elem.name}{id_str}{f'.{class_str}' if class_str else ''}")
        
        # 打印所有类
        classes = set()
        for tag in soup.find_all(class_=True):
            classes.update(tag.get('class', []))
        self.logger.info(f"\nAll classes: {sorted(classes)}")
        
        # 打印标题相关元素
        self.logger.info("\nPossible title elements:")
        for elem in soup.find_all(['h1', 'h2', 'h3', 'title']):
            self.logger.info(f"Tag: {elem.name}, Text: {elem.get_text(strip=True)}")
        
        # 提取视频信息
        video_info = self._parse_video_info(soup)
        
        # 验证提取的信息
        self.assertIsNotNone(video_info['title'], "Title should not be None")
        
        # 创建输出目录
        output_dir = os.path.join('tests', 'data', 'parsed_videos')
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存解析结果
        movie_id = video_info.get('id', 'unknown')
        output_file = os.path.join(output_dir, f"video_{movie_id}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(video_info, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"\nParsed video info saved to: {output_file}")
        self.logger.info(f"Content:\n{json.dumps(video_info, indent=2, ensure_ascii=False)}")
    
    def _parse_video_info(self, soup):
        """Parse video information from the detail page.
        
        Args:
            soup (BeautifulSoup): Parsed HTML
            
        Returns:
            dict: Video information
        """
        info = {
            'id': None,
            'title': None,
            'cover_image': None,
            'preview_video': None,
            'duration': None,
            'release_date': None,
            'code': None,
            'actresses': [],
            'genres': [],
            'series': None,
            'maker': None  # 制作商
        }
        
        try:
            # 提取视频ID
            video_container = soup.find('div', id='page-video')
            if video_container and 'v-scope' in video_container.attrs:
                v_scope = video_container['v-scope']
                if 'Movie({id:' in v_scope:
                    # 使用字符串处理提取ID
                    start_idx = v_scope.find('id:') + 3
                    end_idx = v_scope.find(',', start_idx)
                    if end_idx == -1:
                        end_idx = v_scope.find('}', start_idx)
                    if end_idx != -1:
                        try:
                            info['id'] = int(v_scope[start_idx:end_idx].strip())
                        except ValueError:
                            self.logger.error(f"Failed to parse video ID from {v_scope}")
            
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
                    label = spans[0].get_text(strip=True).rstrip(':')
                    value = spans[1].get_text(strip=True)
                    
                    if label == 'コード':  # 代码
                        info['code'] = value
                    elif label == 'リリース日':  # 发布日期
                        info['release_date'] = value
                    elif label == '再生時間':  # 时长
                        info['duration'] = value
                    elif label == '女優':  # 演员
                        actresses = spans[1].find_all('a')
                        info['actresses'] = [a.get_text(strip=True) for a in actresses]
                    elif label == 'ジャンル':  # 类型
                        genres = spans[1].find_all('a')
                        info['genres'] = [a.get_text(strip=True) for a in genres]
                    elif label == 'メーカー':  # 制作商
                        maker_elem = spans[1].find('a')
                        if maker_elem:
                            info['maker'] = maker_elem.get_text(strip=True)
                    elif label == 'シリーズ':  # 系列
                        series_elem = spans[1].find('a')
                        if series_elem:
                            info['series'] = series_elem.get_text(strip=True)
            
        except Exception as e:
            self.logger.error(f"Error parsing video info: {str(e)}")
            self.logger.error(f"Error details:", exc_info=True)
        
        return info

if __name__ == '__main__':
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    unittest.main()
