"""
使用 DrissionPage 爬取电影详情页面并支持多语言版本。
"""
import os
import sys
import re
import json
import time
import traceback
import concurrent.futures
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
        self.language = "ja"  # 默认使用日语
        
        # 创建浏览器数据持久化目录
        self.user_data_dir = Path.home() / ".cache" / "cloudflare_bypass_browser"
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化浏览器
        self.browser = None
        
        # 支持的所有语言列表
        self.languages = [
            "en",      # English
            "ja",      # Japanese
            "",   # Traditional Chinese
            "zh",   # Simplified Chinese
            "ko",      # Korean
            "ms",      # Malay
            "th",      # Thai
            "de",      # German
            "fr",      # French
            "vi",      # Vietnamese
            "id",      # Indonesian
            "fil",     # Filipino
            "pt",      # Portuguese
            "hi"       # Hindi
        ]
        
        # 初始化字段模式
        self.field_patterns = self.initialize_field_patterns()
    
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
    
    def get_new_browser_instance(self, headless: bool = True):
        """
        创建新的浏览器实例，用于并行爬取
        
        Args:
            headless: 是否在无头模式下运行，默认为真以提高性能
            
        Returns:
            CloudflareBypassBrowser: 新的浏览器实例，用于绕过Cloudflare验证
        """
        try:
            from app.utils.drission_utils import CloudflareBypassBrowser
            
            # 每个并行实例使用单独的数据目录
            instance_id = int(time.time())
            user_data_dir = Path.home() / ".cache" / f"cloudflare_bypass_browser_parallel_{instance_id}"
            user_data_dir.mkdir(exist_ok=True, parents=True)
            
            # 创建并返回新的浏览器实例
            browser = CloudflareBypassBrowser(
                headless=headless,
                user_data_dir=str(user_data_dir),
                load_images=False,  # 不加载图片提高效率
                timeout=30  # 给Cloudflare挑战足够时间
            )
            
            return browser
        except ImportError as e:
            logger.error(f"导入CloudflareBypassBrowser出错: {e}")
            raise e
        except Exception as e:
            logger.error(f"创建并行浏览器实例出错: {e}")
            raise e
    
    def get_base_page(self) -> bool:
        """
        访问基础URL并通过Cloudflare挑战，为后续多语言爬取铺垫
        
        Returns:
            bool: 返回是否成功访问页面
        """
        # 构建基本 URL
        base_url = f"https://missav.ai/{self.language}/{self.movie_id}"
        
        try:
            # 访问页面并等待通过Cloudflare检测
            logger.info("访问页面并等待自动通过Cloudflare检测...")
            self.browser.get(base_url, timeout=10)
            
            # 等待页面加载
            time.sleep(1)
            
            # 在页面上等待一段时间，让Cloudflare检测完成
            # CloudflareBypassBrowser会自动处理人类行为模拟
            try:
                self.browser.execute_script("window.scrollTo(0, document.body.scrollHeight/2)")
            except Exception as scroll_error:
                logger.warning(f"等待过程中出错: {scroll_error}")
            
            # 检查页面是否加载成功
            html = self.browser.get_html()
            if not html or len(html) < 500 or "missav" not in html.lower():
                logger.warning("页面可能未正确加载")
                return False
            logger.info("页面加载成功")
            return True
            
        except Exception as e:
            logger.error(f"访问基础页面时出错: {str(e)}")
            logger.debug(traceback.format_exc())
            return False
    
    def crawl(self, headless: bool = False) -> Dict[str, Dict]:
        """
        爬取所有语言版本的电影详情，使用并行处理加速
        
        Args:
            headless: 是否以无头模式运行浏览器
            
        Returns:
            包含多语言电影详情的字典，格式为 {语言: 详情字典}
        """
        if not self.browser:
            self.setup_browser(headless=headless)
        
        results = {}
        
        try:
            # 直接访问无语言参数的基础URL
            base_url = f"https://missav.ai/{self.language}/{self.movie_id}"
            logger.info(f"正在访问基础URL: {base_url}")
            
            # 访问页面并获取基础语言版本的数据
            if not self.get_base_page():
                return results
            
            logger.info(f"继续解析当前页面")
            
            # 获取当前页面的HTML内容
            html = self.browser.get_html()
            
            # 获取当前页面URL并判断语言
            # 注意：CloudflareBypassBrowser不支持url属性
            base_language = "ja"  # 默认使用英语
            try:
                
                # 如果是DrissionPage类，尝试直接获取URL
                if hasattr(self.browser, 'url'):
                    base_language = self.browser.url
                # 如果是CloudflareBypassBrowser，尝试从页面内容推断
                else:
                    html = self.browser.get_html()
                    
                # 从URL中尝试提取语言代码
                soup = BeautifulSoup(html, 'html.parser')
            except Exception as e:
                base_language = "en"  # 错误时默认使用英语
                logger.warning(f"判断页面语言出错，使用默认值英语: {e}")
                
            # 无论是否出现异常，都记录检测到的语言
            logger.info(f"检测到当前页面语言: {base_language}")
                
            # 解析基础语言版本的数据
            base_data = self.parse_movie_page(html, base_language)
            if not html or len(html) < 500 or "missav" not in html.lower():
                logger.warning("页面可能未正确加载，继续尝试...")
            else:
                logger.info("页面已成功加载！")
            
            
            # 展示收集结果概要
            title = base_data.get('title', '无标题')
            actresses = ', '.join(base_data.get('actresses', [])[:3])
            if len(base_data.get('actresses', [])) > 3:
                actresses += '...' 
            logger.info(f"- {base_language}: {title[:30]}{' ...' if len(title) > 30 else ''} | {actresses}")
            
        except Exception as e:
            logger.error(f"爬虫出错: \n{e}")
        finally:
            # 清理资源，关闭浏览器
            try:
                if self.browser:
                    self.browser.close()
            except Exception as e:
                logger.error(f"关闭浏览器出错: {e}")
        
        return base_data
    
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
        return False
            
    def crawl_movie_in_language(self, language: str) -> Optional[Dict]:
        """
        爬取特定语言版本的电影详情
        为了支持并行处理，此方法创建独立的浏览器实例
        
        Args:
            language: 语言代码，例如 "en", "ja", "zh-tw"
            
        Returns:
            电影详情字典或 None（爬取失败时）
        """
        # 创建新的浏览器实例用于并行爬取
        lang_browser = None
        try:
            # 使用新的浏览器实例来支持并行处理
            lang_browser = self.get_new_browser_instance(headless=True)
            
            # 构造对应语言的URL
            url = f"https://missav.ai/{language}/{self.movie_id}"
            logger.info(f"并行爬取: 开始访问{language}语言版本: {url}")
            
            # 实现重试逻辑
            max_retries = 2
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # 访问页面
                    lang_browser.get(url, timeout=15)
                    time.sleep(3)  # 等待页面加载
                    
                    # 等待Cloudflare检测完成
                    # CloudflareBypassBrowser已内置了人类行为模拟
                    time.sleep(3)
                    
                    # 获取页面HTML内容
                    html = lang_browser.get_html()
                    
                    # 验证页面内容
                    if not html or len(html) < 1000 or "missav" not in html.lower():
                        retry_count += 1
                        logger.warning(f"[{language}]页面可能未正确加载，重试({retry_count}/{max_retries})")
                        time.sleep(2)
                        continue
                    
                    # 页面加载成功，解析内容
                    logger.info(f"[{language}]页面加载成功，开始解析内容")
                    result = self.parse_movie_page(html, language)
                    
                    if result:
                        # 保存结果到JSON
                        self.save_to_json(result, language)
                        return result
                    else:
                        retry_count += 1
                        logger.warning(f"[{language}]页面解析失败，重试({retry_count}/{max_retries})")
                        time.sleep(2)
                        
                except Exception as e:
                    retry_count += 1
                    logger.error(f"[{language}]访问错误: {str(e)}")
                    time.sleep(2)
            
            logger.error(f"[{language}]在{max_retries}次尝试后仍未成功获取数据")
            return None
                
        except Exception as e:
            logger.error(f"[{language}]并行爬取错误: {str(e)}")
            return None
            
        finally:
            # 确保浏览器实例被正确关闭以释放资源
            if lang_browser is not None:
                try:
                    lang_browser.quit()
                    logger.debug(f"[{language}]已关闭并行爬取浏览器实例")
                except:
                    pass
        
    def parse_movie_page(self, browser, language="en") -> Dict:
        """
        分析电影页面
        
        Args:
            browser: 浏览器实例或HTML字符串
            language: 当前语言
            
        Returns:
            Dict: 电影详情字典
        """
        # 构造页面URL
        if language == "en":
            url = f"https://missav.ai/{self.movie_id}"
        else:
            url = f"https://missav.ai/{language}/{self.movie_id}"
            
        # 初始化结果字典
        result = {
            "id": self.movie_id,
            "language": language,
            "url": url,  # 使用预构建的URL而不是从浏览器获取
            "crawled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
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
            # 获取HTML内容并初始BeautifulSoup
            if isinstance(browser, str):
                html = browser
            else:
                try:
                    html = browser.get_html()
                except Exception as e:
                    logger.error(f"获取HTML时出错: {e}")
                    return result
                    
            soup = BeautifulSoup(html, "html.parser")
            
            # 首先从meta标签中提取信息
            try:
                # 提取标题 - 从meta标签
                meta_title = soup.select_one('meta[property="og:title"]')
                if meta_title and meta_title.get('content'):
                    result["title"] = meta_title.get('content').strip()
                
                # 提取封面图片URL - 从meta标签
                meta_image = soup.select_one('meta[property="og:image"]')
                if meta_image and meta_image.get('content'):
                    result["cover_url"] = meta_image.get('content')
                
                # 提取描述 - 从meta标签
                meta_desc = soup.select_one('meta[property="og:description"]')
                if meta_desc and meta_desc.get('content'):
                    result["description"] = meta_desc.get('content')
                    # 限制描述长度
                    if len(result["description"]) > 500:
                        result["description"] = result["description"][:497] + "..."
                
                # 尝试从meta标签提取发布日期
                meta_date = soup.select_one('meta[property="og:article:published_time"]')
                if meta_date and meta_date.get('content'):
                    result["website_date"] = meta_date.get('content')
                    # 如果没有其他发布日期，使用网站日期
                    if not result["release_date"]:
                        result["release_date"] = meta_date.get('content')
            except Exception as e:
                logger.warning(f"从meta标签提取信息失败: {e}")
            
            # 如果meta标签中没有标题，尝试从其他元素中提取
            if not result["title"]:
                # 从页面标题中提取DVD ID
                title_tag = soup.select_one('title')
                if title_tag and title_tag.text:
                    title_parts = title_tag.text.split()
                    if title_parts:
                        # 使用标题的第一部分作为标题
                        result["title"] = title_parts[0]
                
                # 如果还是没有标题，使用其他选择器尝试
                if not result["title"]:
                    title_selectors = ['h1', '.videoTitle', '.film-title', '.title', '[class*="title"]', 'article h2']
                    for selector in title_selectors:
                        try:
                            title_elem = soup.select_one(selector)
                            if title_elem and title_elem.text.strip():
                                result["title"] = title_elem.text.strip()
                                break
                        except Exception:
                            continue
                
                # 如果依然没有找到标题，使用电影ID
                if not result["title"]:
                    result["title"] = self.movie_id
            
            # 如果meta标签中没有封面URL，尝试从其他元素中提取
            if not result["cover_url"]:
                cover_selectors = [
                    '.poster img', '.cover img', '.thumbnail img', 
                    '[class*="poster"] img', '[class*="cover"] img',
                    '.movie-cover img', 'video-player img', '.preview img'
                ]
                for selector in cover_selectors:
                    try:
                        cover_elem = soup.select_one(selector)
                        if cover_elem and cover_elem.has_attr('src'):
                            result["cover_url"] = cover_elem['src']
                            break
                    except Exception:
                        continue
                        
            # 如果meta标签中没有发行日期，尝试从HTML中提取
            if not result["release_date"]:
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
                    except Exception:
                        continue
            
            # 先尝试提取所有的元数据
            metadata = self._extract_meta_data(soup)
            
            # 使用提取的元数据填充结果
            if metadata.get("duration"):
                result["duration"] = metadata.get("duration")
            if metadata.get("maker"):
                result["studio"] = metadata.get("maker")
            if metadata.get("actor") and not result["actresses"]:
                # 如果元数据有演员信息但result中还没有，就使用它
                actors = metadata.get("actor").split(',') if ',' in metadata.get("actor") else [metadata.get("actor")]  
                result["actresses"] = [a.strip() for a in actors if a.strip()]
            
            # 如果元数据中没有时长信息，尝试从页面中提取
            if not result["duration"]:
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
                    except Exception:
                        continue
            
            # 如果元数据中没有制作商信息，尝试从页面中提取
            if not result["studio"]:
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
                    except Exception:
                        continue
            
            # 提取标签 - 先使用元数据中的类型
            if metadata.get("genres") and isinstance(metadata.get("genres"), list):
                result["tags"] = metadata.get("genres")
            else:
                # 如果元数据中没有类型，尝试从页面中提取
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
                    except Exception:
                        continue
            
            # 如果元数据中没有演员信息，尝试从页面中提取
            if not result["actresses"]:
                # 特别尝试提取女演员
                extracted_actress = self._extract_actress(soup)
                if extracted_actress:
                    # 如果使用特殊方法提取到了女演员，优先使用
                    actresses = extracted_actress.split(',') if ',' in extracted_actress else [extracted_actress]  
                    result["actresses"] = [a.strip() for a in actresses if a.strip()]
                else:
                    # 使用字段模式中的女优关键词构建选择器
                    actress_terms = self.field_patterns.get("actress", [])
                    actress_selectors = []
                    
                    # 基础选择器
                    base_selectors = [
                        '[class*="actress"] a', '[class*="star"] a', 
                        '.cast a', '.performer a', '.actor a',
                        '[class*="cast-item"] a', '.video-performer a'
                    ]
                    
                    # 添加基础选择器
                    actress_selectors.extend(base_selectors)
                    
                    # 为每个女优关键词添加特定选择器
                    for term in actress_terms:
                        actress_selectors.append(f'[class*="{term.lower()}"] a')
                        actress_selectors.append(f'[data-label="{term}"] a')
                        actress_selectors.append(f'[data-label*="{term}"] a')
                        actress_selectors.append(f'.{term.lower()} a')
                        
                    # 日语特定选择器
                    if language == "ja":
                        actress_selectors.extend([
                            '.av-actress a', '.av-performer a', '.jav-actress a',
                            '[class*="女優"] a', '[class*="出演者"] a', '[class*="出演"] a',
                            '[data-label="女優"] a', '[data-label="出演者"] a'
                        ])
                    
                    found_actresses = []
                    for selector in actress_selectors:
                        try:
                            actress_elems = soup.select(selector)
                            for actress in actress_elems:
                                if actress.text.strip() and not any(x in actress.text.lower() for x in ['tag', 'genre', 'studio', 'category']):
                                    if actress.text.strip() not in found_actresses:
                                        result["actresses"].append(actress.text.strip())
                                        found_actresses.append(actress.text.strip())
                        except Exception:
                            continue
            
            # 如果元数据中没有描述信息，尝试从页面中提取
            if not result["description"]:
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
                    except Exception:
                        continue
            
            logger.info(f"成功解析电影信息: {result['title']}")
            
        except Exception as e:
            logger.error(f"解析页面时出错: {e}")
            logger.debug(traceback.format_exc())
        
        return result
    
    def _extract_meta_data(self, soup) -> Dict[str, str]:
        """
        从页面提取结构化元数据
        
        Args:
            soup: BeautifulSoup解析后的页面
            
        Returns:
            Dict: 包含各类元数据的字典
        """
        meta_data = {}
        
        try:
            # 寻找包含属性信息的容器
            info_containers = soup.select('.info-item, [class*="meta"], [class*="info"]')
            
            for container in info_containers:
                text = container.text.strip()
                # 尝试查找格式为"属性: 值"的项目
                if ':' in text or '：' in text:
                    parts = text.split(':', 1) if ':' in text else text.split('：', 1)
                    if len(parts) == 2:
                        key = parts[0].strip().lower()
                        value = parts[1].strip()
                        
                        # 使用字段模式进行匹配
                        # 发行日期
                        if self._match_field_pattern(key, self.field_patterns.get("releaseDate", [])):
                            meta_data['release_date'] = value
                        # 制作商/发行商
                        elif self._match_field_pattern(key, self.field_patterns.get("maker", [])):
                            meta_data['maker'] = value
                        # 系列
                        elif self._match_field_pattern(key, self.field_patterns.get("series", [])):
                            meta_data['series'] = value
                        # 演员/女优
                        elif self._match_field_pattern(key, self.field_patterns.get("actress", [])) or \
                             self._match_field_pattern(key, self.field_patterns.get("maleActor", [])):
                            meta_data['actor'] = value
                        # 导演
                        elif self._match_field_pattern(key, self.field_patterns.get("director", [])):
                            meta_data['director'] = value
                        # 标签/类型
                        elif self._match_field_pattern(key, self.field_patterns.get("genre", [])) or \
                             self._match_field_pattern(key, self.field_patterns.get("label", [])):
                            tags = [tag.strip() for tag in value.split(',')] if ',' in value else [value.strip()]
                            meta_data['genres'] = tags
                        # 时长 - 使用特定关键词匹配
                        elif any(x in key for x in ['时长', 'duration', '長さ', '长度', 'length', '時間']):
                            meta_data['duration'] = value
        
            # 尝试提取单独的元数据标签
            for meta_tag in soup.select('meta'):
                if meta_tag.has_attr('name') and meta_tag.has_attr('content'):
                    name = meta_tag['name'].lower()
                    content = meta_tag['content']
                    
                    if 'keywords' in name and not meta_data.get('genres'):
                        keywords = [kw.strip() for kw in content.split(',')] if ',' in content else [content.strip()]
                        meta_data['genres'] = keywords
                    elif 'description' in name and not meta_data.get('description'):
                        meta_data['description'] = content
                        
            # 尝试使用特定选择器查找元数据
            # 制作商
            if not meta_data.get('maker'):
                for pattern in self.field_patterns.get("maker", []):
                    maker_selector = f'[class*="maker"]:contains("{pattern}"), [class*="studio"]:contains("{pattern}")'                    
                    maker_elem = soup.select_one(maker_selector)
                    if maker_elem and ':' in maker_elem.text:
                        meta_data['maker'] = maker_elem.text.split(':', 1)[1].strip()
                        break
            
            # 女优
            if not meta_data.get('actor'):
                for pattern in self.field_patterns.get("actress", []):
                    actress_selector = f'[class*="actress"]:contains("{pattern}"), [class*="cast"]:contains("{pattern}")'                    
                    actress_elem = soup.select_one(actress_selector)
                    if actress_elem and ':' in actress_elem.text:
                        meta_data['actor'] = actress_elem.text.split(':', 1)[1].strip()
                        break
        except Exception as e:
            logger.warning(f"提取元数据时出错: {e}")
        
        return meta_data
    
    def _match_field_pattern(self, key: str, patterns: List[str]) -> bool:
        """
        检查关键字是否匹配任何字段模式
        
        Args:
            key: 要检查的关键字
            patterns: 要匹配的模式列表
            
        Returns:
            bool: 如果关键字匹配任何模式，则返回 True
        """
        key = key.lower()
        for pattern in patterns:
            pattern_lower = pattern.lower()
            # 检查关键字是否包含模式
            if pattern_lower in key:
                return True
            # 检查模式是否包含关键字
            if len(key) > 2 and key in pattern_lower:
                return True
        return False
        
    def _extract_actress(self, soup) -> str:
        """
        特别提取女优信息
        
        Args:
            soup: BeautifulSoup解析后的页面
            
        Returns:
            str: 女优名字，如果有多个则用逗号分隔
        """
        try:
            # 首先尝试找特定的女优区域
            actress_area = None
            # 使用字段模式中的女优相关关键词
            actress_terms = self.field_patterns.get("actress", [])
            for area in soup.select('div, section, aside'):
                if area.text and any(term.lower() in area.text.lower() for term in actress_terms):
                    actress_area = area
                    break
            
            if actress_area:
                # 在女优区域中寻找链接或标签
                actress_links = actress_area.select('a')
                if actress_links:
                    actresses = [link.text.strip() for link in actress_links 
                               if link.text.strip() and not any(x in link.text.lower() for x in ['tag', 'genre', 'category'])]                    
                    if actresses:
                        return ', '.join(actresses)
            
            # 如果没找到专门的区域，查找可能包含女优信息的标题
            for heading in soup.select('h1, h2, h3, h4, h5, h6'):
                text = heading.text.strip()
                if any(term in text.lower() for term in ['starring', 'featuring', 'stars', 'actress']):
                    # 假设标题后面的文本包含女优名字
                    next_elem = heading.find_next_sibling()
                    if next_elem and next_elem.text.strip():
                        return next_elem.text.strip()
        except Exception as e:
            logger.warning(f"提取女优信息时出错: {e}")
        
        return ""
        
    def initialize_field_patterns(self):
        """
        初始化不同语言的字段模式，用于提取页面中的信息
        基于多语言支持的字段名称
        
        Returns:
            Dict: 包含各字段的多语言模式的字典
        """
        field_patterns = {}
        
        # 系列字段模式 - 所有支持的语言
        field_patterns["series"] = [
            "系列",  # Traditional Chinese
            "系列",  # Simplified Chinese
            "Series",  # English
            "シリーズ",  # Japanese
            "시리즈",  # Korean
            "Siri", "Series",  # Malay
            "ชุด",  # Thai
            "Serie",  # German
            "Série",  # French
            "Loạt",  # Vietnamese
            "Seri",  # Indonesian
            "Serye",  # Filipino
            "Série"  # Portuguese
        ]
        
        # 制作商字段模式 - 所有支持的语言
        field_patterns["maker"] = [
            "製作商",  # Traditional Chinese
            "发行商",  # Simplified Chinese
            "Maker",  # English
            "メーカー",  # Japanese
            "메이커",  # Korean
            "Pembuat",  # Malay
            "ผู้ผลิต",  # Thai
            "Hersteller",  # German
            "Fabricant",  # French
            "nhà sản xuất",  # Vietnamese
            "Pembuat",  # Indonesian
            "Gumawa",  # Filipino
            "Fabricante"  # Portuguese
        ]
        
        # 标签字段模式 - 所有支持的语言
        field_patterns["label"] = [
            "標籤",  # Traditional Chinese
            "标籤",  # Simplified Chinese
            "Label",  # English
            "レーベル",  # Japanese
            "상표",  # Korean
            "Label",  # Malay
            "ฉลาก",  # Thai
            "Etikett",  # German
            "Étiqueter",  # French
            "Nhãn",  # Vietnamese
            "Label",  # Indonesian
            "Label",  # Filipino
            "Rótulo"  # Portuguese
        ]
        
        # 类型字段模式 - 所有支持的语言
        field_patterns["genre"] = [
            "類型",  # Traditional Chinese
            "类型",  # Simplified Chinese
            "Genre",  # English
            "ジャンル",  # Japanese
            "장르",  # Korean
            "Genre",  # Malay
            "ประเภท",  # Thai
            "Genre",  # German
            "Le genre",  # French
            "thể loại",  # Vietnamese
            "Genre",  # Indonesian
            "Genre",  # Filipino
            "Gênero"  # Portuguese
        ]
        
        # 女优字段模式 - 所有支持的语言
        field_patterns["actress"] = [
            "女優",  # Traditional Chinese
            "女优",  # Simplified Chinese
            "Actress",  # English
            "女優",  # Japanese
            "여배우",  # Korean
            "Pelakon wanita",  # Malay
            "นักแสดงหญิง",  # Thai
            "Schauspielerin",  # German
            "Actrice",  # French
            "Diễn viên",  # Vietnamese
            "Aktris",  # Indonesian
            "Artista",  # Filipino
            "Actriz"  # Portuguese
        ]
        
        # 发行日期字段模式 - 所有支持的语言
        field_patterns["releaseDate"] = [
            "發行日期", "发行日期",  # Traditional & Simplified Chinese
            "Release date",  # English
            "配信開始日",  # Japanese
            "출시일",  # Korean
            "Tarikh keluaran",  # Malay
            "วันที่วางจำหน่าย",  # Thai
            "Veröffentlichungsdatum",  # German
            "Date de sortie",  # French
            "Ngày phát hành",  # Vietnamese
            "Tanggal rilis",  # Indonesian
            "Petsa ng Paglabas",  # Filipino
            "Data de lançamento"  # Portuguese
        ]
        
        # 男优字段模式 - 所有支持的语言
        field_patterns["maleActor"] = [
            "男優",  # Traditional Chinese
            "男优",  # Simplified Chinese
            "Actor", "Male actor",  # English
            "男優",  # Japanese
            "남자 배우", "남배우",  # Korean
            "Pelakon lelaki",  # Malay
            "นักแสดงชาย",  # Thai
            "Schauspieler", "Darsteller",  # German
            "Acteur",  # French
            "Diễn viên nam",  # Vietnamese
            "Aktor",  # Indonesian
            "Aktor",  # Filipino
            "Ator"  # Portuguese
        ]
        
        # 导演字段模式 - 所有支持的语言
        field_patterns["director"] = [
            "導演", "监督",  # Traditional Chinese
            "导演", "监督",  # Simplified Chinese
            "Director",  # English
            "監督", "ディレクター",  # Japanese
            "관리자",  # Korean
            "Pengarah",  # Malay
            "ผู้อำนวยการ",  # Thai
            "Direktor", "Regisseur",  # German
            "Réalisateur",  # French
            "Giám đốc",  # Vietnamese
            "Direktur",  # Indonesian
            "Direktor",  # Filipino
            "Diretor"  # Portuguese
        ]
        
        return field_patterns
        
    def close(self):
        """关闭浏览器并释放资源"""
        if self.browser:
            self.browser.close()
            self.browser = None
            
    def save_to_json(self, movie_info: dict):
        """将电影信息保存到JSON文件
        
        Args:
            movie_info: 电影信息字典
        """
        if not movie_info:
            logger.warning(f"没有电影信息可保存")
            return
            
        # 创建数据目录
        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)
        
        # 构建文件名
        filename = f"{self.movie_id}_{self.language}.json"
        output_file = data_dir / filename
        
        # 保存到文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(movie_info, f, ensure_ascii=False, indent=2)
            
        logger.info(f"已保存 {self.language} 版本电影信息到 {output_file}")


def main():
    """主函数，运行爬虫 - 只处理日语版本"""
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
        movie_id = "sdjs-146"  # 默认电影ID
    
    # 创建数据和结果目录
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)
    
    # 打印开始信息
    logger.info(f"开始爬取电影: {movie_id} (日语版本)")
    logger.info("使用优化策略：只处理日语版本")
    
    # 创建并运行爬虫
    crawler = MovieDetailCrawler(movie_id=movie_id)
    
    try:
        # 不使用无头模式，便于观察页面加载情况
        movie_info = crawler.crawl(headless=False)
        
        # 将结果保存到文件
        crawler.save_to_json(movie_info)
            
        # 打印详细信息
        logger.info(f"电影 {movie_id} 日语版本爬取完成")
        logger.info(f"  标题: {movie_info.get('title', '未知')}")
        logger.info(f"  女优: {', '.join(movie_info.get('actresses', ['未知']))}")
        if movie_info.get('tags'):
            tag_preview = ', '.join(movie_info.get('tags', [])[:5])
            logger.info(f"  标签: {tag_preview}{' ...' if len(movie_info.get('tags', [])) > 5 else ''}")
        logger.info(f"  制作商: {movie_info.get('studio', '未知')}")
        logger.info(f"  发行日期: {movie_info.get('release_date', '未知')}")
        logger.info(f"  时长: {movie_info.get('duration', '未知')}")
        logger.info(f"  封面URL: {movie_info.get('cover_url', '未知')}")
        logger.info(f"  数据已保存到: data/{movie_id}_ja.json")
        
    except Exception as e:
        logger.error(f"爬虫出错: {e}", exc_info=True)
    finally:
        crawler.close()


if __name__ == "__main__":
    main()
