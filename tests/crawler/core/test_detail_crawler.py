"""Test detail crawler functionality."""

import unittest
import os
import json
import logging
from datetime import datetime
from src.crawler.core.detail_crawler import DetailCrawler

class TestDetailCrawler(unittest.TestCase):
    """Test cases for DetailCrawler."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # 设置日志
        logging.basicConfig(level=logging.INFO,
                          format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # 创建测试目录
        cls.test_dir = os.path.join('tests', 'data')
        os.makedirs(cls.test_dir, exist_ok=True)
        
        # 创建爬虫实例
        cls.crawler = DetailCrawler(clear_existing=True)
        
    def test_get_video_urls(self):
        """Test getting video URLs from ajax API."""
        video_id = '180813'
        watch_url, download_url = self.crawler._get_video_urls(video_id)
        
        self.assertIsNotNone(watch_url, "Watch URL should not be None")
        self.assertTrue(watch_url.startswith('https://javplayer.me/'),
                       "Watch URL should be a javplayer URL")
        
    def test_extract_m3u8_info(self):
        """Test extracting M3U8 and VTT information."""
        video_id = '180813'
        cover_url = "https://cdn.avfever.net/images/7/d7/savr-238/cover.jpg?t=1730570053"
        
        m3u8_url, vtt_url = self.crawler._extract_m3u8_info(video_id, cover_url)
        
        self.assertIsNotNone(m3u8_url, "M3U8 URL should not be None")
        self.assertIsNotNone(vtt_url, "VTT URL should not be None")
        self.assertTrue(m3u8_url.endswith('m3u8'), "M3U8 URL should end with m3u8")
        self.assertTrue(vtt_url.endswith('vtt'), "VTT URL should end with vtt")
        
    def test_get_movie_detail(self):
        """Test getting movie details."""
        # 1. 先获取视频URL
        video_id = '180813'
        watch_url, _ = self.crawler._get_video_urls(video_id)
        self.assertIsNotNone(watch_url, "Failed to get watch URL")
        
        # 2. 构造测试数据
        movie = {
            'url': f'https://123av.com/ja/movies/{video_id}',
            'title': 'Test Movie',
            'duration': '120',
            'cover_image': "https://cdn.avfever.net/images/7/d7/savr-238/cover.jpg?t=1730570053"
        }
        
        # 3. 获取视频详情
        video_info = self.crawler._get_movie_detail(movie)
        self.assertIsNotNone(video_info, "Video info should not be None")
        
        # 4. 验证基本信息
        self.assertEqual(video_info['id'], video_id, "Video ID should match")
        self.assertEqual(video_info['title'], movie['title'], "Title should match")
        self.assertEqual(video_info['duration'], movie['duration'], "Duration should match")
        
        # 5. 验证URL
        self.assertIsNotNone(video_info.get('m3u8_url'), "M3U8 URL should not be None")
        self.assertIsNotNone(video_info.get('vtt_url'), "VTT URL should not be None")
        
        if video_info.get('m3u8_url'):
            self.assertTrue(video_info['m3u8_url'].endswith('m3u8'),
                          "M3U8 URL should end with m3u8")
        if video_info.get('vtt_url'):
            self.assertTrue(video_info['vtt_url'].endswith('vtt'),
                          "VTT URL should end with vtt")
        
        # 6. 保存测试结果
        result_file = os.path.join(self.test_dir, f'detail_test_{video_id}.json')
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(video_info, f, indent=2, ensure_ascii=False)
        self.crawler._logger.info(f"Saved test result to {result_file}")
        
if __name__ == '__main__':
    unittest.main()
