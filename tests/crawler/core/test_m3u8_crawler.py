"""Test M3U8 crawler functionality."""

import unittest
import os
import json
import logging
from datetime import datetime
from src.crawler.core.m3u8_crawler import M3U8Crawler

class TestM3U8Crawler(unittest.TestCase):
    """Test cases for M3U8Crawler."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # 设置日志
        logging.basicConfig(level=logging.INFO,
                          format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # 创建测试目录
        cls.test_dir = os.path.join('tests', 'data')
        os.makedirs(cls.test_dir, exist_ok=True)
        
        # 创建测试数据
        cls.test_detail_file = os.path.join(cls.test_dir, 'test_details.json')
        cls.test_data = {
            '180813': {
                'id': '180813',
                'title': 'Test Movie',
                'cover_image': 'https://cdn.avfever.net/images/7/d7/savr-238/cover.jpg?t=1730570053',
                'url': 'https://123av.com/ja/movies/180813'
            }
        }
        
        # 保存测试数据
        with open(cls.test_detail_file, 'w', encoding='utf-8') as f:
            json.dump(cls.test_data, f, indent=2, ensure_ascii=False)
            
        # 创建M3U8爬虫实例
        cls.crawler = M3U8Crawler()
        
    def test_get_video_urls(self):
        """Test getting video URLs from ajax API."""
        video_id = '180813'
        watch_url, download_url = self.crawler.get_video_urls(video_id)
        
        self.assertIsNotNone(watch_url, "Watch URL should not be None")
        self.assertTrue(watch_url.startswith('https://javplayer.me/'),
                       "Watch URL should be a javplayer URL")
        
    def test_extract_video_info(self):
        """Test extracting video information."""
        video_id = '180813'
        cover_url = self.test_data[video_id]['cover_image']
        
        m3u8_url, vtt_url = self.crawler.extract_video_info(video_id, cover_url)
        
        self.assertIsNotNone(m3u8_url, "M3U8 URL should not be None")
        self.assertIsNotNone(vtt_url, "VTT URL should not be None")
        self.assertTrue(m3u8_url.endswith('m3u8'), "M3U8 URL should end with m3u8")
        self.assertTrue(vtt_url.endswith('vtt'), "VTT URL should end with vtt")
        
    def test_process_detail_file(self):
        """Test processing detail file."""
        self.crawler.process_detail_file(self.test_detail_file)
        
        # 验证结果
        with open(self.test_detail_file, 'r', encoding='utf-8') as f:
            updated_data = json.load(f)
            
        movie_data = updated_data.get('180813')
        self.assertIsNotNone(movie_data, "Movie data should exist")
        self.assertIn('m3u8_url', movie_data, "M3U8 URL should be added")
        self.assertIn('vtt_url', movie_data, "VTT URL should be added")
        self.assertIn('last_update', movie_data, "Last update should be added")
        
        m3u8_url = movie_data['m3u8_url']
        vtt_url = movie_data['vtt_url']
        
        self.assertTrue(m3u8_url.endswith('m3u8'), "M3U8 URL should end with m3u8")
        self.assertTrue(vtt_url.endswith('vtt'), "VTT URL should end with vtt")
        
if __name__ == '__main__':
    unittest.main()
