import unittest
from unittest.mock import patch, MagicMock
import os
import json
from bs4 import BeautifulSoup
from datetime import datetime
from crawler.core.genre_processor import GenreProcessor

class TestGenreProcessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
     
        # 创建测试目录
        cls.test_dir = os.path.join('tests', 'data')
        os.makedirs(cls.test_dir, exist_ok=True)
        
        # 初始化处理器
        cls.processor = GenreProcessor(base_url='http://123av.com', language='ja')
        
    def test_fetch_genres(self):
        """Test fetching genres from website."""
        # 获取类型列表
        genres = self.processor._fetch_genres()
        
        # 验证返回结果
        self.assertIsNotNone(genres, "Genres should not be None")
        self.assertIsInstance(genres, list, "Genres should be a list")
        
        if genres:
            # 验证第一个类型的结构
            first_genre = genres[0]
            self.assertIn('name', first_genre, "Genre should have name")
            self.assertIn('url', first_genre, "Genre should have URL")
            self.assertIn('count', first_genre, "Genre should have count")
            
            # 打印调试信息
            print(f"\nFound {len(genres)} genres")
            print("Sample genre:")
            print(json.dumps(first_genre, indent=2, ensure_ascii=False))
            
    # def test_process_genre_page(self):
    #     """Test processing a single genre page."""
    #     # 创建测试类型数据
    #     test_genre = {
    #         'name': 'test_genre',
    #         'url': 'http://123av.com/ja/dm1/genres/av-idol'
    #     }
        
    #     # 处理第一页
    #     movies = self.processor._process_genre_page(test_genre, 1)
        
    #     # 验证返回结果
    #     self.assertIsNotNone(movies, "Movies should not be None")
    #     self.assertIsInstance(movies, dict, "Movies should be a dictionary")
        
    #     if movies:
    #         # 验证第一个电影的结构
    #         first_movie = next(iter(movies.values()))
    #         self.assertIn('id', first_movie, "Movie should have ID")
    #         self.assertIn('title', first_movie, "Movie should have title")
    #         self.assertIn('url', first_movie, "Movie should have URL")
    #         self.assertIn('duration', first_movie, "Movie should have duration")
            
    #         # 打印调试信息
    #         print(f"\nFound {len(movies)} movies on page 1")
    #         print("Sample movie:")
    #         print(json.dumps(first_movie, indent=2, ensure_ascii=False))
            
    # def test_save_genre(self):
    #     """Test saving genre to database."""
    #     # 创建测试类型数据
    #     test_genre = {
    #         'name': 'テスト',
    #         'url': 'http://123av.com/ja/dm1/genres/test',
    #         'count': 100
    #     }
        
    #     try:
    #         # 保存到数据库
    #         genre_id = self.processor._save_genre(test_genre)
            
    #         # 验证返回结果
    #         self.assertIsNotNone(genre_id, "Genre ID should not be None")
    #         self.assertIsInstance(genre_id, int, "Genre ID should be an integer")
            
    #         print(f"\nSuccessfully saved genre with ID: {genre_id}")
            
    #     except Exception as e:
    #         self.fail(f"Failed to save genre: {str(e)}")
            
    # @classmethod
    # def tearDownClass(cls):
    #     """Clean up test environment."""
    #     if hasattr(cls, 'processor') and hasattr(cls.processor, '_db'):
    #         cls.processor._db.close()
    
if __name__ == '__main__':
    unittest.main()