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
        
    def test_get_movie_detail(self):
        """Test getting movie details from detail page URL."""
        # 1. 构造测试数据，使用电影详情页 URL
        movie_url = "http://123av.com/jp/v/dass-587-uncensored-leaked"  # 使用电影详情页 URL
        movie = {
            'url': movie_url,
        }

        # 2. 获取视频详情
        logging.info("movie:", movie)
        video_info = self.crawler._get_movie_detail(movie)
        self.assertIsNotNone(video_info, "Video info should not be None")

        # 3. 验证 ID 是否已提取，并且不是从 URL 简单分割出来的
        self.assertIsNotNone(video_info.get('id'), "Video ID should not be None")
        # 假设从 HTML 中提取的 ID  通常不是 'dass-587-uncensored-leaked' 这种 URL slug
        self.assertNotEqual(video_info['id'], 'dass-587-uncensored-leaked',
                            "Video ID should not be directly from URL slug")
        self.assertTrue(video_info['id'].isdigit(), "Video ID should be digits (extracted from HTML)")


        # 4. 验证其他基本信息 (可以根据实际情况调整验证的字段)
        self.assertIsNotNone(video_info.get('title'), "Title should not be None")
        self.assertIsNotNone(video_info.get('duration'), "Duration should not be None")

        # 5. 验证URL (M3U8 and VTT URLs)
        self.assertIsNotNone(video_info.get('m3u8_url'), "M3U8 URL should not be None")
        self.assertIsNotNone(video_info.get('vtt_url'), "VTT URL should not be None")

        if video_info.get('m3u8_url'):
            self.assertTrue(video_info['m3u8_url'].endswith('m3u8'),
                          "M3U8 URL should end with m3u8")
        if video_info.get('vtt_url'):
            self.assertTrue(video_info['vtt_url'].endswith('vtt'),
                          "VTT URL should end with vtt")

        # 6. 保存测试结果
        video_id_for_filename = video_info.get('id', 'unknown_id') # 使用解析出的 ID 或 'unknown_id'
        result_file = os.path.join(self.test_dir, f'detail_test_html_id_{video_id_for_filename}.json')
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(video_info, f, indent=2, ensure_ascii=False)
        self.crawler._logger.info(f"Saved test result to {result_file}")

if __name__ == '__main__':
    unittest.main()
