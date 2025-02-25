"""Test detail crawler functionality."""

import unittest
import os
import json
import logging
from datetime import datetime
import pytest
from src.crawler.core.detail_crawler import DetailCrawler
from src.crawler.utils.db import DatabaseManager

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
        movie_url = "https://123av.com/en/v/urvrsp-421"
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
            'cover_image': (str, type(None)),  # 允许为 None
            'actresses': list,
            'genres': list,
            'likes': int,
            'watch_urls_info': list,
            'download_urls_info': list
        }
        
        # 可选字段列表
        optional_fields = {
            'magnets': list,
            'preview_video': (str, type(None)),
            'series': str,
            'maker': str
        }
        
        for field, expected_type in required_fields.items():
            self.assertIn(field, video_info, f"Missing required field: {field}")
            if isinstance(expected_type, tuple):
                self.assertIsInstance(video_info[field], expected_type, 
                                    f"Field {field} has wrong type. Expected {expected_type}, got {type(video_info[field])}")
            else:
                self.assertIsInstance(video_info[field], expected_type, 
                                    f"Field {field} has wrong type. Expected {expected_type}, got {type(video_info[field])}")
            
            # 对非None的字符串字段进行非空检查
            if expected_type == str and video_info[field] is not None:
                self.assertNotEqual(video_info[field], "", f"Required field {field} is empty string")
            
            # 检查必需的列表字段是否有内容
            if field in ['actresses', 'genres']:  # 只检查必需的列表字段
                self.assertGreater(len(video_info[field]), 0, f"Required list field {field} is empty")
                
        # 检查可选字段的类型（如果存在）
        for field, expected_type in optional_fields.items():
            if field in video_info:
                if isinstance(expected_type, tuple):
                    self.assertIsInstance(video_info[field], expected_type,
                                        f"Optional field {field} has wrong type. Expected {expected_type}, got {type(video_info[field])}")
                else:
                    self.assertIsInstance(video_info[field], expected_type,
                                        f"Optional field {field} has wrong type. Expected {expected_type}, got {type(video_info[field])}")

        # 4. 验证 ID 格式
        self.assertTrue(video_info['id'].isdigit() or video_info['id'].startswith(('URVRSP-', 'DASS-')),
                       "Video ID should be digits or start with valid prefix")

        # 5. 验证 URL 格式
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

        # 6. 保存到数据库
        db = DatabaseManager()
        try:
            movie_id = db.save_movie(video_info)
            self.assertIsNotNone(movie_id, "Movie ID should not be None after saving to database")
            print(f"\nSuccessfully saved movie to database with ID: {movie_id}")
            
            # 验证数据已保存
            with db._conn.cursor() as cur:
                # 检查电影基本信息
                cur.execute("SELECT code, title FROM movies m JOIN movie_titles mt ON m.id = mt.movie_id WHERE m.id = %s", (movie_id,))
                result = cur.fetchone()
                self.assertIsNotNone(result, "Movie not found in database")
                self.assertEqual(result[0], video_info['code'], "Movie code mismatch")
                
                # 检查演员信息
                cur.execute("""
                    SELECT an.name 
                    FROM actresses a 
                    JOIN movie_actresses ma ON a.id = ma.actress_id 
                    JOIN actress_names an ON a.id = an.actress_id 
                    WHERE ma.movie_id = %s
                """, (movie_id,))
                actresses = [row[0] for row in cur.fetchall()]
                self.assertEqual(set(actresses), set(video_info['actresses']), "Actresses mismatch")
                
                # 检查类型信息
                cur.execute("""
                    SELECT gn.name 
                    FROM genres g 
                    JOIN movie_genres mg ON g.id = mg.genre_id 
                    JOIN genre_names gn ON g.id = gn.genre_id 
                    WHERE mg.movie_id = %s
                """, (movie_id,))
                genres = [row[0] for row in cur.fetchall()]
                self.assertEqual(set(genres), set(video_info['genres']), "Genres mismatch")
                
        finally:
            db.close()

        # 7. 保存测试结果到文件
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
