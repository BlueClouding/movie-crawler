"""
使用 DrissionPage 爬取电影详情页面并支持多语言版本。
"""
import os
import sys
import re
import json
import time
import traceback
from typing import Dict, List, Optional, Union, Any
from pathlib import Path
from loguru import logger
from bs4 import BeautifulSoup

# 将项目根目录添加到 Python 路径
sys.path.append(str(Path(__file__).parent.parent))

from app.utils.drission_utils import CloudflareBypassBrowser


class MovieDetailCrawler:
    """
    电影详情爬虫类，使用 DrissionPage 绕过 Cloudflare 检测
    支持抓取不同语言版本的电影详情页面
    
    注意：这是一个测试版本。按照模块化设计，该类应分割成：
    1. 解析器部分（parsers/movie_parser.py）
    2. 爬虫核心部分（core/detail_crawler.py）
    3. 数据存储部分（db/operations.py）
    """
    
    def __init__(self, movie_id: str):
        """
        初始化电影详情爬虫
        
        Args:
            movie_id: 电影ID，如 'shmo-162'，FC2-PPV-1020621
        """
        self.movie_id = movie_id
        
        # 创建浏览器数据持久化目录
        self.user_data_dir = Path.home() / ".cache" / "cloudflare_bypass_browser"
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化浏览器
        self.browser = None
        
        # 支持的语言列表 (先使用主要语言以提高成功率)
        self.languages = ["en", "ja"]  # 可以之后扩展到["en", "ja", "zh-TW", "zh-CN", "ko"]
    
    def setup_browser(self, headless: bool = False):
        """
        设置 CloudflareBypassBrowser
        
        Args:
            headless: 是否以无头模式运行
        """
        # 创建浏览器实例 - 只使用支持的参数
        self.browser = CloudflareBypassBrowser(
            headless=headless,
            user_data_dir=str(self.user_data_dir),
            load_images=True,  # 加载图片更容易通过Cloudflare检测
            timeout=60  # 给Cloudflare挑战更充足的时间
        )
        
        # 模拟窗口调整，保持更好的用户体验
        try:
            # 使用JavaScript将窗口调整到正常大小
            self.browser.page.run_js("window.resizeTo(1280, 800);")
        except:
            pass
            
        logger.info("浏览器初始化完成")
    
    def get_base_page(self) -> bool:
        """
        访问基础URL并通过Cloudflare挑战，为后续多语言爬取铺垫
        
        Returns:
            bool: 是否成功访问基础页面
        """
        base_url = f"https://missav.ai/{self.movie_id}"
        
        logger.info(f"正在访问基础URL: {base_url}")
        
        try:
            # 多次重试访问基础页面
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    success = self.browser.get(base_url, wait_for_cf=True)
                    
                    if success:
                        logger.info(f"成功访问基础URL: {base_url}")
                        
                        # 成功访问后，等待页面完全加载
                        self.browser.wait(3)
                        
                        # 验证页面内容是否有效
                        html = self.browser.get_html()
                        if html and len(html) > 1000 and "missav" in html.lower():
                            return True
                        else:
                            logger.warning(f"页面内容可能不完整，尝试刷新 (尝试 {attempt}/{max_retries})")
                    else:
                        logger.warning(f"访问失败，重试中 (尝试 {attempt}/{max_retries})")
                    
                    # 如果不是最后一次尝试，则等待后重试
                    if attempt < max_retries:
                        time.sleep(3 * attempt)  # 增加等待时间
                        
                except Exception as e:
                    logger.error(f"尝试 {attempt}/{max_retries} 失败: {e}")
                    if attempt < max_retries:
                        time.sleep(3 * attempt)
            
            logger.error(f"经过 {max_retries} 次尝试后仍无法访问基础URL: {base_url}，爬虫终止")
            return False
            
        except Exception as e:
            logger.error(f"访问基础URL出错: {base_url}, 错误: {e}")
            return False
    
    def crawl(self, headless: bool = False) -> Dict[str, Dict]:
        """
        爬取所有语言版本的电影详情
        
        Args:
            headless: 是否以无头模式运行浏览器
            
        Returns:
            包含多语言电影详情的字典，格式为 {语言: 详情字典}
        """
        results = {}
        
        try:
            # 设置浏览器 - 始终使用有头模式，便于观察和手动操作
            self.setup_browser(headless=False)
            
            # 直接访问无语言参数的基础URL
            base_url = f"https://missav.ai/{self.movie_id}"
            logger.info(f"正在访问基础URL: {base_url}")
            
            # 载入URL，设置短的超时时间
            try:
                logger.info("访问页面并等待自动通过Cloudflare检测...")
                self.browser.page.get(base_url, timeout=5)
                # 小等片刻，给页面时间完成加载
                time.sleep(3)
            except Exception as e:
                logger.warning(f"访问 URL 时发生异常: {e}")
            
            # 在页面上简单滚动以模拟人类行为
            try:
                for _ in range(2):
                    # 滚动到页面不同位置
                    self.browser.page.scroll.to_half()
                    time.sleep(0.5)
                    self.browser.page.scroll.down()
                    time.sleep(0.5)
                    self.browser.page.scroll.up()
                    time.sleep(0.5)
            except Exception as e:
                logger.warning(f"滚动页面时出错: {e}")
                
            # 检查页面是否加载成功
            html = self.browser.get_html()
            if not html or len(html) < 500 or "missav" not in html.lower():
                logger.warning("页面可能未正确加载，继续尝试...")
            else:
                logger.info("页面已成功加载！")
            
            # 解析当前页面
            logger.info("继续解析当前页面")
            html = self.browser.get_html()
            
            # 确定当前页面语言
            current_url = self.browser.page.url
            default_lang = "unknown"
            lang_match = re.search(r"https?://[^/]+/([a-z-]+)/", current_url)
            
            if lang_match:
                default_lang = lang_match.group(1)
            else:
                default_lang = "en"  # 假设默认为英文
                
            logger.info(f"检测到当前页面语言: {default_lang}")
            
            # 解析页面内容
            if html and len(html) > 1000:
                result = self.parse_movie_page(html, default_lang)
                if result:
                    results[default_lang] = result
                    self.save_to_json(result, default_lang)
                    logger.info(f"{default_lang}语言版本数据获取成功")
            
            # 先尝试查找页面上的语言切换器
            logger.info("尝试查找页面内的语言切换器...")
            lang_switchers = self.browser.find_elements("a[hreflang]")
            if not lang_switchers:
                lang_switchers = self.browser.find_elements(".language-switcher a, .lang a, [class*='language'] a, .language a")
            
            # 如果找到语言切换器，使用它们在同一会话中切换语言
            if lang_switchers:
                logger.info(f"找到 {len(lang_switchers)} 个语言切换器")
                
                for switcher in lang_switchers:
                    try:
                        # 获取目标语言
                        href = switcher.attr("href") or ""
                        lang = switcher.attr("hreflang")
                        
                        # 从链接提取语言代码
                        if not lang and href:
                            lang_match = re.search(r"/([a-z-]+)/", href)
                            if lang_match:
                                lang = lang_match.group(1)
                        
                        # 没有找到语言代码，尝试从元素内容推断
                        if not lang:
                            text = switcher.text.strip().lower()
                            if text in ["en", "ja", "zh-tw", "zh-cn", "ko"]:
                                lang = text
                        
                        # 检查语言代码是否有效且未处理
                        if not lang or lang == default_lang or lang not in self.languages or lang in results:
                            continue
                            
                        logger.info(f"尝试切换到语言: {lang}")
                        
                        # 点击语言切换器
                        switcher.click()
                        time.sleep(3)  # 等待页面加载
                        
                        # 同样解析该语言版本
                        html = self.browser.get_html()
                        if html and len(html) > 1000:
                            result = self.parse_movie_page(html, lang)
                            if result:
                                results[lang] = result
                                self.save_to_json(result, lang)
                                logger.info(f"{lang}语言版本数据获取成功")
                    except Exception as e:
                        logger.error(f"切换到{lang}语言失败: {str(e)}")
            else:
                logger.info("未找到语言切换器，将使用直接访问方式")
            
            # 对于未能获取的语言，尝试直接访问对应URL
            for lang in self.languages:
                if lang != default_lang and lang not in results:
                    logger.info(f"直接访问 {lang} 语言版本页面")
                    lang_url = f"https://missav.ai/{lang}/{self.movie_id}"
                    
                    try:
                        # 访问该语言的URL
                        self.browser.get(lang_url)
                        time.sleep(3)
                        
                        # 解析内容
                        html = self.browser.get_html()
                        if html and len(html) > 1000 and "missav" in html.lower():
                            result = self.parse_movie_page(html, lang)
                            if result:
                                results[lang] = result
                                self.save_to_json(result, lang)
                                logger.info(f"{lang}语言版本数据获取成功")
                        else:
                            logger.warning(f"{lang}语言版本页面内容无效或被Cloudflare拦截")
                    except Exception as e:
                        logger.error(f"访问{lang}语言版本失败: {str(e)}")
            
            logger.info("===============================")
            logger.info(f"已获取 {len(results)} 种语言的电影详情")
            
            # 展示收集结果概要
            for lang, data in results.items():
                title = data.get('title', '无标题')
                actresses = ', '.join(data.get('actresses', [])[:3])
                if len(data.get('actresses', [])) > 3:
                    actresses += '...' 
                logger.info(f"- {lang}: {title[:30]}{' ...' if len(title) > 30 else ''} | {actresses}")
            
            # 截图保存主页面
            try:
                screenshot_dir = Path('screenshots')
                screenshot_dir.mkdir(exist_ok=True)
                screenshot_path = screenshot_dir / f"{self.movie_id}_main.png"
                self.browser.page.get_screenshot(str(screenshot_path), full_page=True)
                logger.info(f"页面截图已保存到: {screenshot_path}")
            except Exception as e:
                logger.error(f"截图失败: {e}")
            
        except Exception as e:
            logger.error(f"爬虫出错: \n{e}")
        finally:
            # 清理资源，关闭浏览器
            try:
                if self.browser:
                    self.browser.close()
            except Exception as e:
                logger.error(f"关闭浏览器出错: {e}")
        
        return results
    
    def is_cloudflare_page(self, html: str) -> bool:
        """
        检测页面是否为Cloudflare挑战页面
        
        Args:
            html: 页面HTML内容
            
        Returns:
            是否为Cloudflare挑战页面
        """
        if not html or len(html) < 200:
            return True
            
        # 快速检查常见的Cloudflare标记
        cf_indicators = [
            "checking your browser", 
            "cloudflare", 
            "security check",
            "正在检查您的浏览器",
            "just a moment",
            "attention required",
            "需要注意"
        ]
        
        # 先进行字符串匹配，效率更高
        html_lower = html.lower()
        for indicator in cf_indicators:
            if indicator.lower() in html_lower:
                return True
        
        # 再进行更精确的BeautifulSoup检测
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 检查特定文本模式
            for text_pattern in ["checking your browser", "cloudflare", "security check"]:
                if soup.find(text=re.compile(text_pattern, re.IGNORECASE)):
                    return True
                    
            # 检查特定元素
            if soup.select("#challenge-running") or soup.select(".cf-browser-verification"):
                return True
                
            # 检查页面内容 - 如果包含电影相关元素，则不是Cloudflare页面
            if soup.select(".movie-info") or soup.select(".video-info") or \
               soup.find('h1', class_=lambda c: c and 'title' in c.lower()):
                return False
                
        except Exception as e:
            logger.error(f"BeautifulSoup解析错误: {e}")
            
        # 默认返回安全的选项
        return True
            
    def crawl_movie_in_language(self, language: str) -> Optional[Dict]:
        """
        爬取特定语言版本的电影详情
        
        Args:
            language: 语言代码，例如 "en", "ja"
            
        Returns:
            电影详情字典或 None（爬取失败时）
        """
        # 尝试访问特定语言的URL
        # 根据测试，直接格式最可靠: https://missav.ai/{language}/{movie_id}
        url = f"https://missav.ai/{language}/{self.movie_id}"
        
        logger.info(f"尝试访问: {url}")
        
        # 实现重试逻辑
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 随机延迟，模拟人类行为
                import random
                delay = 1 + random.random() * 2  
                time.sleep(delay)
                
                # 访问页面
                success = self.browser.get(url)
                
                if not success:
                    retry_count += 1
                    logger.warning(f"访问失败: {url}，重试 ({retry_count}/{max_retries})")
                    time.sleep(2 * retry_count)  # 每次重试等待时间增加
                    continue
                    
                logger.info(f"成功访问: {url}")
                
                # 获取页面 HTML 内容
                html = self.browser.get_html()
                
                # 防止页面断开连接
                if not html or len(html) < 100:
                    retry_count += 1
                    logger.warning(f"HTML内容为空或过短，可能是浏览器连接断开，重试 ({retry_count}/{max_retries})")
                    time.sleep(2 * retry_count)
                    continue
                    
                # 检查是否为Cloudflare页面
                if self.is_cloudflare_page(html):
                    retry_count += 1
                    logger.warning(f"检测到Cloudflare挑战页面，重试 ({retry_count}/{max_retries})")
                    time.sleep(2 * retry_count)
                    continue
                
                # 解析电影信息
                movie_info = self.parse_movie_page(html, language)
                
                return movie_info
                
            except Exception as e:
                retry_count += 1
                logger.error(f"访问或解析出错: {url}, 错误: {e}")
                logger.info(f"重试 ({retry_count}/{max_retries})")
                time.sleep(2 * retry_count)
        
        logger.error(f"经过 {max_retries} 次重试后仍无法获取 {language} 语言版本")
        return None
        
    def parse_movie_page(self, html: str, language: str) -> Dict:
        """
        解析电影页面内容
        
        Args:
            html: HTML内容
            language: 语言代码
            
        Returns:
            解析后的电影详情字典
        """
        # 初始化结果字典
        result = {
            "id": self.movie_id,
            "language": language,
            "url": f"https://missav.ai/{language}/{self.movie_id}" 
                   if language != "en" else f"https://missav.ai/{self.movie_id}",
            "title": "",
            "cover_url": "",
            "release_date": "",
            "duration": "",
            "studio": "",
            "tags": [],
            "actresses": [],
            "description": ""
        }
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 更广泛的选择器，增加成功率
            # 提取标题 - 尝试多种可能的选择器
            title_selectors = ['h1', '.videoTitle', '.film-title', '.title', '[class*="title"]', 'article h2']
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem and title_elem.text.strip():
                    result["title"] = title_elem.text.strip()
                    break
            
            # 提取封面图片 - 寻找所有可能的图片元素
            cover_selectors = [
                '.poster img', '.cover img', '.thumbnail img', 
                '[class*="poster"] img', '[class*="cover"] img',
                '.movie-cover img', 'video-player img', '.preview img'
            ]
            for selector in cover_selectors:
                cover_elem = soup.select_one(selector)
                if cover_elem and cover_elem.has_attr('src'):
                    result["cover_url"] = cover_elem['src']
                    break
                
            # 提取发行日期
            date_selectors = [
                '[class*="date"]', 'time', '.release-date', 
                '.video-meta time', '.info-item:contains("发行")', 
                '.meta-item:contains("Date")', '.meta-item:contains("日期")'
            ]
            for selector in date_selectors:
                try:
                    date_elem = soup.select_one(selector)
                    if date_elem and date_elem.text.strip():
                        result["release_date"] = date_elem.text.strip()
                        break
                except:
                    continue
            
            # 提取时长
            duration_selectors = [
                '[class*="duration"]', '[class*="time"]', '.video-time',
                '.meta-item:contains("Duration")', '.meta-item:contains("時長")',
                '.meta-item:contains("长度")', '.length'
            ]
            for selector in duration_selectors:
                try:
                    duration_elem = soup.select_one(selector)
                    if duration_elem and duration_elem.text.strip():
                        result["duration"] = duration_elem.text.strip()
                        break
                except:
                    continue
            
            # 提取制作商
            studio_selectors = [
                '[class*="studio"]', '[class*="maker"]', '.producer', 
                '.meta-item:contains("Studio")', '.meta-item:contains("制作")'
            ]
            for selector in studio_selectors:
                try:
                    studio_elem = soup.select_one(selector)
                    if studio_elem and studio_elem.text.strip():
                        result["studio"] = studio_elem.text.strip()
                        break
                except:
                    continue
            
            # 提取标签 - 尝试多个可能的选择器
            tag_selectors = [
                '[class*="tag"]', '[class*="genre"] a', '.tags a', 
                '.categories a', '.genres a', '[class*="category"] a'
            ]
            found_tags = []
            for selector in tag_selectors:
                try:
                    tag_elems = soup.select(selector)
                    if tag_elems:
                        for tag in tag_elems:
                            if tag.text.strip() and tag.text.strip() not in found_tags:
                                result["tags"].append(tag.text.strip())
                                found_tags.append(tag.text.strip())
                except:
                    continue
            
            # 提取女优名字
            actress_selectors = [
                '[class*="actress"] a', '[class*="star"] a', 
                '.cast a', '.performer a', '.actor a',
                '[class*="cast-item"] a', '.video-performer a'
            ]
            found_actresses = []
            for selector in actress_selectors:
                try:
                    actress_elems = soup.select(selector)
                    for actress in actress_elems:
                        if actress.text.strip() and not any(x in actress.text.lower() for x in ['tag', 'genre', 'studio', 'category']):
                            if actress.text.strip() not in found_actresses:
                                result["actresses"].append(actress.text.strip())
                                found_actresses.append(actress.text.strip())
                except:
                    continue
            
            # 提取描述文本
            desc_selectors = [
                '[class*="desc"]', '[class*="summary"]', 
                '[class*="description"]', '.video-info', 
                '.movie-description', '.synopsis', '.plot'
            ]
            for selector in desc_selectors:
                try:
                    desc_elem = soup.select_one(selector)
                    if desc_elem and desc_elem.text.strip():
                        result["description"] = desc_elem.text.strip()
                        # 限制描述长度
                        if len(result["description"]) > 500:
                            result["description"] = result["description"][:497] + "..."
                        break
                except:
                    continue
            
            logger.info(f"成功解析电影信息: {result['title']}")
            
        except Exception as e:
            logger.error(f"解析页面时出错: {e}")
        
        return result
    
    def close(self):
        """关闭浏览器并释放资源"""
        if self.browser:
            self.browser.close()
            self.browser = None


def main():
    """主函数，运行爬虫"""
    # 配置日志
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)
    
    logger.remove()
    logger.add(
        logs_dir / "drission_movie_test.log",
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
    
    # 从命令行参数获取电影ID，如果没有提供则使用默认值
    if len(sys.argv) > 1:
        movie_id = sys.argv[1]
    else:
        movie_id = "shmo-162"  # 默认电影ID
    
    # 创建数据和结果目录
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)
    
    # 打印开始信息
    logger.info(f"开始爬取电影: {movie_id}")
    logger.info("使用优化策略：先访问基础URL绕过Cloudflare，再处理多语言版本")
    
    # 创建并运行爬虫
    crawler = MovieDetailCrawler(movie_id=movie_id)
    
    try:
        # 不使用无头模式，便于观察页面加载情况
        movie_results = crawler.crawl(headless=False)
        
        # 将结果保存到文件
        for language, movie_info in movie_results.items():
            crawler.save_to_json(movie_info, language)
        
        logger.info(f"电影 {movie_id} 爬取完成，获取了 {len(movie_results)} 种语言版本的详情")
        
        # 打印部分信息
        for lang, details in movie_results.items():
            logger.info(f"语言: {lang}")
            logger.info(f"  标题: {details.get('title', '未知')}")
            logger.info(f"  女优: {', '.join(details.get('actresses', ['未知']))}")
            if details.get('tags'):
                tag_preview = ', '.join(details.get('tags', [])[:5])
                logger.info(f"  标签: {tag_preview}{' ...' if len(details.get('tags', [])) > 5 else ''}")
            logger.info("")
        
    except Exception as e:
        logger.error(f"爬虫出错: {e}", exc_info=True)
    finally:
        crawler.close()


if __name__ == "__main__":
    main()
