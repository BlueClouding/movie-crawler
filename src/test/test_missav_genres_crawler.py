"""
使用 DrissionPage 绕过 Cloudflare 检测的测试脚本。
演示如何将 CloudflareBypassBrowser 集成到现有的爬虫系统中。
支持多语言版本的网站爬取。
"""
import sys
import time
import random
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
import re
from urllib.parse import urljoin

from loguru import logger
from bs4 import BeautifulSoup

# 将项目根目录添加到 Python 路径
sys.path.append(str(Path(__file__).parent.parent))

# 导入我们的 CloudflareBypassBrowser 类
from app.utils.drission_utils import CloudflareBypassBrowser
from common.enums.enums import SupportedLanguage


class CloudflareCrawler:
    """
    使用 DrissionPage 绕过 Cloudflare 检测的爬虫类
    
    这个类演示了如何将 CloudflareBypassBrowser 集成到现有爬虫架构中
    支持多语言版本的网站爬取
    """
    
    # 支持的语言和对应的URL前缀
    LANGUAGE_URL_PREFIXES = {
        SupportedLanguage.ENGLISH: "/en",
        SupportedLanguage.JAPANESE: "/ja",
        SupportedLanguage.CHINESE: "/zh",
    }
    
    def __init__(self, base_url: str, max_pages: int = 23, language: SupportedLanguage = SupportedLanguage.JAPANESE):
        """
        初始化 CloudflareCrawler
        
        Args:
            base_url: 要爬取的网站基础URL
            max_pages: 要爬取的最大页数
            language: 爬取的语言版本
        """
        self.base_url = base_url
        self.max_pages = max_pages
        self.language = language
        self.browser = None
        
        # 创建浏览器数据持久化目录
        self.user_data_dir = Path.home() / ".cache" / "cloudflare_bypass_browser"
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
    
    def setup_browser(self, headless: bool = False):
        """
        设置 CloudflareBypassBrowser
        
        Args:
            headless: 是否以无头模式运行
        """
        self.browser = CloudflareBypassBrowser(
            headless=headless,
            user_data_dir=str(self.user_data_dir),
            load_images=False  # 禁用图片加载以提高速度
        )
        logger.info("浏览器初始化完成")
    
    def get_language_url(self, base_url: str) -> str:
        """
        根据选择的语言生成对应的URL
        
        Args:
            base_url: 基础URL
            
        Returns:
            带有语言前缀的URL
        """
        # 如果基础URL已经包含语言前缀，则直接返回
        for prefix in self.LANGUAGE_URL_PREFIXES.values():
            if prefix in base_url:
                return base_url
        
        # 添加语言前缀
        language_prefix = self.LANGUAGE_URL_PREFIXES.get(self.language, "")
        if language_prefix:
            # 确保 URL 格式正确
            if base_url.endswith("/"):
                base_url = base_url[:-1]
            return f"{base_url}{language_prefix}"
        
        return base_url

    def crawl_genre_list(self, start_page: int = 1, headless: bool = False) -> List[Dict]:
        """
        爬取女优列表页，绕过 Cloudflare 保护
        
        Args:
            start_page: 起始页码
            headless: 是否使用无头模式
            
        Returns:
            包含女优信息的字典列表
        """
        if not self.browser:
            self.setup_browser(headless=headless)
        
        # 生成带有语言前缀的URL
        language_base_url = self.get_language_url(self.base_url)
        logger.info(f"使用语言版本: {self.language.value}, URL: {language_base_url}")
        
        all_genres = []
        max_retries = 1  # 最多重试1次，即最多刷新2次
        
        for page_num in range(start_page, start_page + self.max_pages):
            # 构造页面 URL
            if page_num == 1:
                url = language_base_url
            else:
                url = f"{language_base_url}?page={page_num}"
            
            logger.info(f"正在爬取第 {page_num} 页: {url}")
            
            # 尝试加载页面，最多尝试两次
            success = False
            retries = 0
            
            while not success and retries <= max_retries:
                # 访问页面，使用更激进的优化设置
                success = self.browser.get(
                    url, 
                    wait_for_full_load=False,
                    dom_ready_timeout=2  # 只等待2秒就开始处理页面
                )
                
                if not success and retries < max_retries:
                    logger.warning(f"加载第 {page_num} 页失败，正在重试 ({retries+1}/{max_retries+1})")
                    retries += 1
                    time.sleep(0.5)  # 重试前等待半秒
            
            if not success:
                logger.error(f"加载第 {page_num} 页失败，已达到最大重试次数")
                break
            
            # 获取页面 HTML 内容
            html = self.browser.get_html()
            
            # 解析 HTML 提取类型信息
            genres = self.parse_genre_page(html)
            
            if not genres:
                logger.warning(f"第 {page_num} 页未找到类型信息，停止爬取")
                break
            
            all_genres.extend(genres)
            logger.info(f"第 {page_num} 页爬取完成。找到 {len(genres)} 个类型。")
            
            # 页面间添加固定延迟
            if page_num < start_page + self.max_pages - 1:  # 不是最后一页
                logger.info(f"等待 0.5 秒后爬取下一页...")
                time.sleep(0.5)  # 固定等待半秒
        
        logger.info(f"爬取完成。共找到 {len(all_genres)} 个类型。")
        return all_genres
    
    def parse_genre_page(self, html: str) -> list:
        """
        解析 HTML 内容并提取类型信息
        
        Args:
            html: 页面 HTML 内容
            
        Returns:
            包含类型名称的字符串列表
        """
        genres = []
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # 查找包含类型信息的容器
            container = soup.find('div', class_='grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4')
            if not container:
                return []
            
            # 查找所有类型项目
            genre_items = container.find_all('div')
            
            for item in genre_items:
                # 提取类型名称
                name_elem = item.find('a', class_='text-nord13')
                if name_elem:
                    genre_name = name_elem.text.strip()
                    genres.append(genre_name)

            return genres
                    
        except Exception as e:
            print(f"解析 HTML 时出错: {e}")
    
    def close(self):
        """关闭浏览器并释放资源"""
        if self.browser:
            self.browser.close()
            self.browser = None


def main():
    """主函数，运行爬虫"""
    import argparse
    
    # 配置日志
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)
    
    logger.remove()
    logger.add(
        logs_dir / "cloudflare_bypass_test.log",
        rotation="10 MB",
        retention="10 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{line} - {message}",
    )
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="使用 DrissionPage 绕过 Cloudflare 检测的测试脚本")
    parser.add_argument(
        "--language", 
        type=str, 
        default="ja", 
        choices=["en", "ja", "zh", "ko"],
        help="爬取的语言版本 (en: 英文, ja: 日文, zh: 中文, ko: 韩文)"
    )
    parser.add_argument(
        "--pages", 
        type=int, 
        default=2, 
        help="爬取的页面数"
    )
    parser.add_argument(
        "--headless", 
        action="store_true", 
        help="使用无头模式"
    )
    
    args = parser.parse_args()
    
    # 根据命令行参数选择语言
    language_map = {
        "en": SupportedLanguage.ENGLISH,
        "ja": SupportedLanguage.JAPANESE,
        "zh": SupportedLanguage.CHINESE,
    }
    language = language_map.get(args.language, SupportedLanguage.JAPANESE)
    
    # 目标网站
    base_url = "https://missav.ai/ja/genres"  # 基础 URL
    
    logger.info(f"使用语言: {args.language}, 页数: {args.pages}, 无头模式: {args.headless}")
    
    # 创建并运行爬虫
    crawler = CloudflareCrawler(
        base_url=base_url, 
        max_pages=args.pages,
        language=language
    )
    
    try:
        # 爬取女优信息
        genres = crawler.crawl_genre_list(headless=args.headless)
        logger.info(f"共爬取了 {len(genres)} 个类型信息")
        
        # 将结果保存到文件
        if genres:
            output_file = Path('data') / 'genres.json'
            output_file.parent.mkdir(exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(genres, f, ensure_ascii=False, indent=2)
            
            logger.info(f"结果已保存到 {output_file}")
            
            # 打印部分示例数据
            logger.info("示例数据:")
            for i, genre in enumerate(genres[:3]):
                logger.info(f"  {i+1}. {genre}")
        
    except Exception as e:
        logger.error(f"爬虫出错: {e}", exc_info=True)
    finally:
        # 确保关闭浏览器
        crawler.close()


if __name__ == "__main__":
    main()
