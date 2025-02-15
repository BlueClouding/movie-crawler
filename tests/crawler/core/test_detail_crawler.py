"""Test detail crawler functionality."""

import unittest
import os
import json
import logging
from datetime import datetime
import pytest
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
        
    @pytest.mark.timeout(30)  # 设置30秒超时
    def test_get_movie_detail(self):
        """Test getting movie details from detail page URL."""
        # 1. 构造测试数据
        # movie_url = "https://123av.com/en/dm1/v/dass-587-uncensored-leaked"
        movie_url='https://123av.com/en/v/urvrsp-421'
        movie = {
            'url': movie_url,
        }

        # 2. 获取视频详情
        video_info = self.crawler._get_movie_detail(movie)
        
        # 打印完整的视频信息用于调试
        print("\n=== Video Info Debug Output ===")
        if video_info:
            for key, value in video_info.items():
                print(f"\n{key}:")
                if isinstance(value, list):
                    if value:
                        print(f"  List with {len(value)} items:")
                        for item in value[:2]:  # 只显示前两个项目
                            print(f"    {item}")
                        if len(value) > 2:
                            print(f"    ... ({len(value)-2} more items)")
                    else:
                        print("  Empty list")
                else:
                    print(f"  {value}")
        else:
            print("Video info is None!")
        print("\n=== End Debug Output ===\n")

        # 3. 验证结果
        self.assertIsNotNone(video_info, "Video info should not be None")
        
        # 更新必需字段列表，确保与实际返回数据结构匹配
        required_fields = {
            'id': str,
            'title': str,
            'duration': str,
            'code': str,
            'cover_image': str,
            'actresses': list,
            'genres': list,
            'magnets': list,
            'likes': int,
            'watch_urls_info': list,
            'download_urls_info': list
        }
        
        for field, expected_type in required_fields.items():
            self.assertIn(field, video_info, f"Missing field: {field}")
            if isinstance(expected_type, tuple):
                self.assertIsInstance(video_info[field], expected_type, 
                                    f"Field {field} has wrong type. Expected {expected_type}, got {type(video_info[field])}")
            else:
                self.assertIsInstance(video_info[field], expected_type, 
                                    f"Field {field} has wrong type. Expected {expected_type}, got {type(video_info[field])}")
            
            # 对非None的字符串字段进行非空检查
            if expected_type == str and video_info[field] is not None:
                self.assertNotEqual(video_info[field], "", f"Field {field} is empty string")
            
            # 检查列表字段是否有内容
            if expected_type == list:
                self.assertGreater(len(video_info[field]), 0, f"List field {field} is empty")

        # 4. 验证 ID 是否已提取，并且不是从 URL 简单分割出来的
        self.assertIsNotNone(video_info.get('id'), "Video ID should not be None")
        # 假设从 HTML 中提取的 ID  通常不是 'dass-587-uncensored-leaked' 这种 URL slug
        self.assertNotEqual(video_info['id'], 'dass-587-uncensored-leaked',
                            "Video ID should not be directly from URL slug")
        self.assertTrue(video_info['id'].isdigit(), "Video ID should be digits (extracted from HTML)")

        # 5. 验证其他基本信息
        self.assertIsNotNone(video_info.get('title'), "Title should not be None")
        self.assertIsNotNone(video_info.get('duration'), "Duration should not be None")

        # 6. 验证 watch_urls_info 和 download_urls_info 的格式
        for watch_info in video_info['watch_urls_info']:
            self.assertIn('index', watch_info, "Watch URL info missing 'index'")
            self.assertIn('name', watch_info, "Watch URL info missing 'name'")
            self.assertIn('url', watch_info, "Watch URL info missing 'url'")
            self.assertTrue(watch_info['url'].startswith('https://'), "Invalid watch URL format")

        for download_info in video_info['download_urls_info']:
            self.assertIn('host', download_info, "Download URL info missing 'host'")
            self.assertIn('index', download_info, "Download URL info missing 'index'")
            self.assertIn('name', download_info, "Download URL info missing 'name'")
            self.assertIn('url', download_info, "Download URL info missing 'url'")
            self.assertTrue(download_info['url'].startswith('https://'), "Invalid download URL format")

        # 7. 保存测试结果
        video_id = video_info.get('id', 'unknown_id')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        result_file = os.path.join(self.test_dir, f'detail_test_{video_id}_{timestamp}.json')
        
        # 保存完整的响应数据，包括中间数据，方便调试
        test_result = {
            'video_info': video_info,
            'test_timestamp': timestamp,
            'test_url': movie_url
        }
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(test_result, f, indent=2, ensure_ascii=False)
        self.crawler._logger.info(f"Saved test result to {result_file}")

if __name__ == '__main__':
    unittest.main()
