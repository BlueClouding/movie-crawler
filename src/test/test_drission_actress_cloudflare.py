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
        SupportedLanguage.KOREAN: "/ko",
    }
    
    def __init__(self, base_url: str, max_pages: int = 3, language: SupportedLanguage = SupportedLanguage.JAPANESE):
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

    def crawl_actress_list(self, start_page: int = 1, headless: bool = False) -> List[Dict]:
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
        
        all_actresses = []
        
        for page_num in range(start_page, start_page + self.max_pages):
            # 构造页面 URL
            if page_num == 1:
                url = language_base_url
            else:
                url = f"{language_base_url}?page={page_num}"
            
            logger.info(f"正在爬取第 {page_num} 页: {url}")
            
            # 使用 CloudflareBypassBrowser 访问 URL
            success = self.browser.get(url)
            
            if not success:
                logger.error(f"加载第 {page_num} 页失败")
                break
            
            # 获取页面 HTML 内容
            html = self.browser.get_html()
            
            # 解析 HTML 提取女优信息
            actresses = self.parse_actress_page(html)
            
            if not actresses:
                logger.warning(f"第 {page_num} 页未找到女优信息，停止爬取")
                break
            
            all_actresses.extend(actresses)
            logger.info(f"第 {page_num} 页爬取完成。找到 {len(actresses)} 位女优。")
            
            # 模拟人类行为
            self.browser.scroll_to_bottom()
            
            # 页面间添加随机延迟
            delay = 2 + round(random.random() * 3, 1)  # 2-5 秒
            logger.info(f"等待 {delay} 秒后爬取下一页...")
            time.sleep(delay)
        
        logger.info(f"爬取完成。共找到 {len(all_actresses)} 位女优。")
        return all_actresses
    
    def parse_actress_page(self, html: str) -> List[Dict]:
        """
        解析 HTML 内容并提取女优信息
        
        Args:
            html: 页面 HTML 内容
            
        Returns:
            包含女优信息的字典列表
        """
        if not html or not html.strip():
            logger.warning("HTML 内容为空")
            return []
        
        actresses = []
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # 尝试不同的选择器来查找女优项目
            selectors = [
                'div.actress-item',  # 直接的项目类
                'div.grid > div',     # 网格布局
                'div.space-y-4 > div',  # 常见网格布局
                'div.relative',       # 常见容器
                'div[class*="actress"]',  # 类包含 'actress'
                'div[class*="item"]',  # 通用项目类
                'div.card',           # 卡片布局
                'div[data-testid*="actress"]',  # 测试 ID 基础
                'div[class*="grid"] > div',  # 通用网格
                'div[class*="list"] > div'   # 通用列表
            ]
            
            items = []
            for selector in selectors:
                found_items = soup.select(selector)
                if found_items:
                    logger.debug(f"使用选择器 '{selector}' 找到 {len(found_items)} 个项目")
                    items = found_items
                    break
            
            if not items:
                logger.warning("在 HTML 中未找到女优项目")
                return []
            
            for item in items:
                try:
                    # 提取女优姓名
                    name_elem = item.select_one('h3, h4, [class*="name"], [class*="title"]')
                    name = name_elem.text.strip() if name_elem else 'Unknown'
                    
                    # 提取影片数量
                    works_elem = item.select_one('p:contains("movies"), p:contains("条影片"), p:contains("作品")')
                    works = works_elem.text.strip() if works_elem else '0'
                    works = ''.join(filter(str.isdigit, works)) or '0'
                    
                    # 提取出道年份
                    debut_elem = item.select_one('p:contains("debut"), p:contains("出道")')
                    debut = debut_elem.text.strip() if debut_elem else ''
                    debut = ''.join(filter(str.isdigit, debut))
                    
                    # 提取头像 URL
                    avatar_elem = item.select_one('img')
                    avatar = avatar_elem.get('src', '') if avatar_elem else ''
                    
                    # 提取个人资料页面 URL
                    link_elem = item.select_one('a')
                    profile_url = link_elem.get('href', '') if link_elem else ''
                    
                    actresses.append({
                        'name': name,
                        'works_count': works,
                        'debut_year': debut,
                        'avatar_url': avatar,
                        'profile_url': profile_url
                    })
                    
                    logger.info(f"找到女优: {name} - {works} 部作品")
                    
                except Exception as e:
                    logger.error(f"解析女优项目时出错: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"解析 HTML 时出错: {e}")
        
        return actresses
    
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
        "ko": SupportedLanguage.KOREAN,
    }
    language = language_map.get(args.language, SupportedLanguage.JAPANESE)
    
    # 目标网站
    base_url = "https://missav.ai/actresses"  # 基础 URL
    
    logger.info(f"使用语言: {args.language}, 页数: {args.pages}, 无头模式: {args.headless}")
    
    # 创建并运行爬虫
    crawler = CloudflareCrawler(
        base_url=base_url, 
        max_pages=args.pages,
        language=language
    )
    
    try:
        # 爬取女优信息
        actresses = crawler.crawl_actress_list(headless=args.headless)
        logger.info(f"共爬取了 {len(actresses)} 位女优信息")
        
        # 将结果保存到文件
        if actresses:
            output_file = Path('data') / 'actresses.json'
            output_file.parent.mkdir(exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(actresses, f, ensure_ascii=False, indent=2)
            
            logger.info(f"结果已保存到 {output_file}")
            
            # 打印部分示例数据
            logger.info("示例数据:")
            for i, actress in enumerate(actresses[:3]):
                logger.info(f"  {i+1}. {actress['name']} - {actress['works_count']} 部作品")
        
    except Exception as e:
        logger.error(f"爬虫出错: {e}", exc_info=True)
    finally:
        # 确保关闭浏览器
        crawler.close()


if __name__ == "__main__":
    main()
