import unittest
import os
import sys
import requests
from bs4 import BeautifulSoup
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent.parent)
sys.path.append(project_root)

from src.crawler.utils.http import create_session
from src.crawler.core.detail_crawler import DetailCrawler

class TestPageParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.session = create_session(use_proxy=True)
        cls.test_url = "https://123av.com/en/dm1/genres/av-idol?page=14"
        cls.html_cache_dir = Path(project_root) / "tests" / "data" / "html_cache"
        cls.html_cache_dir.mkdir(parents=True, exist_ok=True)
        cls.html_cache_file = cls.html_cache_dir / "av_idol_page14.html"
        
        # 如果缓存文件不存在，则获取页面内容并缓存
        if not cls.html_cache_file.exists():
            response = cls.session.get(cls.test_url)
            if response.status_code == 200:
                cls.html_cache_file.write_text(response.text, encoding='utf-8')
                cls.html_content = response.text
            else:
                raise Exception(f"Failed to fetch page: {response.status_code}")
        else:
            cls.html_content = cls.html_cache_file.read_text(encoding='utf-8')
        
        cls.soup = BeautifulSoup(cls.html_content, 'html.parser')

    def test_get_total_pages(self):
        """Test extracting total pages from pagination."""
        # 测试不同的分页选择器
        selectors = [
            '.pagination .page-item:last-child a',  # Bootstrap 风格
            '.pager .last a',                       # 通用分页
            '.pages .last',                         # 简单分页
            '.page-numbers:last-child'              # WordPress 风格
        ]
        
        total_pages = None
        for selector in selectors:
            last_page = self.soup.select_one(selector)
            if last_page:
                href = last_page.get('href', '')
                if 'page=' in href:
                    try:
                        total_pages = int(href.split('page=')[-1])
                        break
                    except ValueError:
                        continue
                
                # 尝试从文本获取页数
                try:
                    text = last_page.get_text(strip=True)
                    if text.isdigit():
                        total_pages = int(text)
                        break
                except ValueError:
                    continue
        
        self.assertIsNotNone(total_pages, "Failed to extract total pages")
        self.assertGreater(total_pages, 0, "Total pages should be greater than 0")
        print(f"Total pages found: {total_pages}")

    def test_get_movies(self):
        """Test extracting movie information from the page."""
        movies = {}
        items = self.soup.select('.box-item')
        
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
            movie_id = url.split('/')[-1] if url else None
            
            if movie_id and title:
                movies[movie_id] = {
                    'id': movie_id,
                    'title': title,
                    'url': url,
                    'duration': duration_text
                }
        
        self.assertGreater(len(movies), 0, "Should find at least one movie")
        print(f"Found {len(movies)} movies")
        # 打印第一个电影的信息作为示例
        if movies:
            first_movie = next(iter(movies.values()))
            print("Sample movie:", first_movie)

    def test_debug_page_structure(self):
        """Debug the page structure to help identify correct selectors."""
        # 打印所有可用的类名
        classes = set()
        for tag in self.soup.find_all(class_=True):
            classes.update(tag['class'])
        print("Available classes:", sorted(list(classes)))
        
        # 打印所有链接
        links = self.soup.find_all('a', href=True)
        print(f"\nTotal links found: {len(links)}")
        # 打印前5个链接作为示例
        print("Sample links:")
        for link in links[:5]:
            print(link)
            
        # 分析页面结构
        print("\nAnalyzing page structure:")
        for selector in ['.box-item-list', '.movie-list', '.video-grid', '.content-list']:
            elements = self.soup.select(selector)
            print(f"\nFound {len(elements)} elements with selector '{selector}'")
            if elements:
                print("First element structure:")
                print(elements[0].prettify())
                
        # 查找所有可能的电影链接
        print("\nSearching for potential movie links:")
        for link in links:
            href = link.get('href', '')
            if '/movie/' in href or '/video/' in href or '/dm1/movies/' in href:
                print(f"\nPotential movie link found:")
                print(f"URL: {href}")
                print(f"HTML: {link.prettify()}")

if __name__ == '__main__':
    unittest.main()
