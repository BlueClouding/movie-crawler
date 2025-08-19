#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试DirectMovieCrawler的crawl_movies_concurrent_tabs方法
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# 导入必要的模块
from src.crawler.main_database_crawler import DirectMovieCrawler
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_direct_crawler_debug():
    """测试DirectMovieCrawler的详细调试"""
    
    # 创建爬虫实例
    crawler = DirectMovieCrawler(language="ja")
    
    # 测试电影代码
    movie_codes = ['ebod-890-uncensored-leaked', 'huntc-294']
    
    print(f"开始测试DirectMovieCrawler...")
    print(f"电影代码: {movie_codes}")
    print(f"爬虫语言: {crawler.language}")
    print(f"输出目录: {crawler.output_dir}")
    print(f"用户数据目录: {crawler.user_data_dir}")
    
    try:
        # 测试导入
        print("\n=== 测试导入 ===")
        try:
            from src.app.utils.drission_utils import CloudflareBypassBrowser
            print("✅ CloudflareBypassBrowser 导入成功")
        except Exception as e:
            print(f"❌ CloudflareBypassBrowser 导入失败: {e}")
            return
        
        try:
            from src.test.test_drission_movie import MovieDetailCrawler
            print("✅ MovieDetailCrawler 导入成功")
        except Exception as e:
            print(f"❌ MovieDetailCrawler 导入失败: {e}")
            return
        
        # 测试浏览器创建
        print("\n=== 测试浏览器创建 ===")
        try:
            browser = CloudflareBypassBrowser(
                headless=True,
                user_data_dir=str(crawler.user_data_dir),
                load_images=True,
                timeout=60
            )
            print("✅ 浏览器创建成功")
            
            # 测试页面访问
            print("\n=== 测试页面访问 ===")
            test_url = f"https://missav.ai/{crawler.language}/{movie_codes[0]}"
            print(f"访问URL: {test_url}")
            
            browser.get(test_url)
            print("✅ 页面访问成功")
            
            # 获取页面HTML
            html_content = browser.get_html()
            print(f"HTML长度: {len(html_content)}")
            
            # 测试解析器
            print("\n=== 测试解析器 ===")
            movie_crawler = MovieDetailCrawler(movie_codes[0])
            movie_info = movie_crawler.parse_movie_page(html_content)
            
            print(f"解析结果: {movie_info}")
            
            if movie_info and movie_info.get('title'):
                print("✅ 解析成功")
            else:
                print("❌ 解析失败或未获取到有效信息")
            
            browser.close()
            print("✅ 浏览器已关闭")
            
        except Exception as e:
            print(f"❌ 浏览器测试失败: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # 测试完整的crawl_movies_concurrent_tabs方法
        print("\n=== 测试完整爬取方法 ===")
        result = crawler.crawl_movies_concurrent_tabs(
            movie_codes=movie_codes,
            output_file="debug_test_results.jsonl",
            max_tabs=2
        )
        
        print(f"\n最终结果: {result}")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_crawler_debug()