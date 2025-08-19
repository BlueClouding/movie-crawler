#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Feed Service - Python版本
用于处理用户feed页面的电影信息爬取和处理
"""

import re
import time
import logging
from typing import List, Set, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import json
import asyncio

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Movie:
    """电影数据模型"""
    code: Optional[str] = None
    title: Optional[str] = None
    thumbnail: Optional[str] = None
    original_id: Optional[int] = None
    likes: Optional[int] = None
    duration: Optional[str] = None
    link: Optional[str] = None
    status: str = "NEW"
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'code': self.code,
            'title': self.title,
            'thumbnail': self.thumbnail,
            'original_id': self.original_id,
            'likes': self.likes,
            'duration': self.duration,
            'link': self.link,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class PlaywrightLoginService:
    """Playwright登录服务"""
    
    def __init__(self):
        self.base_url = "https://123av.com"
        self.login_username = "12345"
        self.login_password = "kongqy"
        self.cached_cookies = None
        self.cookie_expiry_time = None
        self.cookie_cache_duration_seconds = 3600  # 1小时
    
    def get_auth_cookies(self, force_refresh: bool = False) -> str:
        """获取认证cookies"""
        if not force_refresh and self.cached_cookies and self.cookie_expiry_time:
            if datetime.now().timestamp() < self.cookie_expiry_time:
                logger.info("使用缓存的cookies")
                return self.cached_cookies
        
        logger.info("执行Playwright登录获取新cookies")
        try:
            # 检查是否已经在事件循环中
            try:
                loop = asyncio.get_running_loop()
                # 如果已经在事件循环中，使用线程池执行
                import concurrent.futures
                import threading
                
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(self.perform_playwright_login())
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    return future.result(timeout=60)  # 60秒超时
                    
            except RuntimeError:
                # 没有运行的事件循环，可以直接创建新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(self.perform_playwright_login())
                finally:
                    loop.close()
        except Exception as e:
            logger.error(f"异步调用Playwright登录失败: {e}")
            return ""
    
    def invalidate_cookie_cache(self):
        """使cookie缓存失效"""
        self.cached_cookies = None
        self.cookie_expiry_time = None
        logger.info("Cookie缓存已失效")
    
    async def perform_playwright_login(self) -> str:
        """执行Playwright登录"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, timeout=30000)
                try:
                    context = await browser.new_context(
                        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
                    )
                    
                    page = await context.new_page()
                    
                    # 先访问主页获取基础cookies
                    await page.goto(f"{self.base_url}/ja")
                    await page.wait_for_load_state("networkidle")
                    
                    # 使用API端点进行登录
                    login_data = {
                        "username": self.login_username,
                        "password": self.login_password,
                        "remember_me": 1
                    }
                    
                    logger.info(f"使用API端点登录: {self.base_url}/ja/ajax/user/signin")
                    
                    # 发送登录请求
                    response = await page.evaluate("""
                        async (data) => {
                            const response = await fetch('/ja/ajax/user/signin', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'Accept': 'application/json, text/plain, */*',
                                    'X-Requested-With': 'XMLHttpRequest',
                                    'Cache-Control': 'no-cache',
                                    'Pragma': 'no-cache'
                                },
                                body: JSON.stringify(data)
                            });
                            return {
                                status: response.status,
                                text: await response.text()
                            };
                        }
                    """, login_data)
                    
                    logger.info(f"登录API响应状态: {response['status']}")
                    logger.info(f"登录API响应内容: {response['text']}")
                    
                    if response['status'] == 200:
                        # 检查响应内容是否包含错误信息
                        try:
                            import json
                            response_data = json.loads(response['text'])
                            if 'errors' in response_data and response_data['errors']:
                                logger.error(f"API登录失败: {response_data['errors']}")
                                return ""
                            else:
                                logger.info("API登录成功")
                        except json.JSONDecodeError:
                            logger.info("API登录成功 (无法解析JSON响应)")
                        
                        # 等待cookies更新
                        await page.wait_for_timeout(2000)
                    else:
                        logger.warning(f"API登录失败，状态码: {response['status']}")
                        return ""
                    
                    # 从浏览器上下文提取cookies
                    cookies = await context.cookies()
                    cookie_string = self.format_cookies_for_http_header(cookies)
                    
                    logger.info(f"提取的cookies: {cookie_string}")
                    
                    # 缓存cookies
                    if cookie_string:
                        self.cached_cookies = cookie_string
                        self.cookie_expiry_time = datetime.now().timestamp() + self.cookie_cache_duration_seconds
                        logger.info(f"缓存的cookies将在 {datetime.fromtimestamp(self.cookie_expiry_time)} 过期")
                    
                    return cookie_string
                    
                finally:
                    await browser.close()
                    
        except Exception as e:
            logger.error(f"Playwright登录请求期间出错: {e}")
            return ""
    
    def format_cookies_for_http_header(self, cookies) -> str:
        """格式化cookies为HTTP头格式"""
        if not cookies:
            return ""
        
        cookie_pairs = []
        for cookie in cookies:
            cookie_pairs.append(f"{cookie['name']}={cookie['value']}")
        
        return "; ".join(cookie_pairs)

class FeedService:
    """Feed服务 - 处理用户feed页面的电影信息"""
    
    def __init__(self, manual_cookie: Optional[str] = None):
        self.feed_base_url = "https://123av.com/ja/user/feed"
        self.default_cookie = "_ga=GA1.1.1641394730.1737617680; locale=ja; session=OS8d8va7hjbID4sjBzXhGojmCqsFh4ZIKORmR8mv; x-token=a9526be6a94f1201cc45e89a7b41806b;"
        self.manual_cookie = manual_cookie  # 手动传入的cookie
        self.playwright_login_service = PlaywrightLoginService()
        # 添加Cloudflare登录服务作为备选
        try:
            from cloudflare_login_service import CloudflareLoginService
            self.cloudflare_login_service = CloudflareLoginService()
        except ImportError:
            logger.warning("CloudflareLoginService不可用，将仅使用Playwright登录服务")
            self.cloudflare_login_service = None
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
        })
        
        # 模拟数据库存储
        self.movies_db: List[Movie] = []
        
        # 记录使用的cookie类型
        if self.manual_cookie:
            logger.info("FeedService初始化：使用手动传入的cookie")
        else:
            logger.info("FeedService初始化：将使用自动登录获取cookie（Playwright优先，Cloudflare备选）")
    
    def get_auth_cookies_with_fallback(self, force_refresh: bool = False) -> Optional[str]:
        """获取认证cookies，支持备选登录方案
        
        Args:
            force_refresh: 是否强制刷新cookies
            
        Returns:
            cookie字符串，如果所有登录方案都失败则返回None
        """
        # 首先尝试使用Playwright登录服务
        try:
            logger.info("尝试使用Playwright登录服务获取cookies")
            cookies = self.playwright_login_service.get_auth_cookies(force_refresh=force_refresh)
            if cookies:
                logger.info("Playwright登录服务成功获取cookies")
                return cookies
            else:
                logger.warning("Playwright登录服务未能获取有效cookies")
        except Exception as e:
            logger.error(f"Playwright登录服务出错: {e}")
        
        # 如果Playwright失败，尝试使用Cloudflare登录服务
        if self.cloudflare_login_service:
            try:
                logger.info("尝试使用Cloudflare登录服务作为备选方案")
                cookies = self.cloudflare_login_service.get_cookies(force_refresh=force_refresh)
                if cookies:
                    logger.info("Cloudflare登录服务成功获取cookies")
                    return cookies
                else:
                    logger.warning("Cloudflare登录服务未能获取有效cookies")
            except Exception as e:
                logger.error(f"Cloudflare登录服务出错: {e}")
        else:
            logger.warning("Cloudflare登录服务不可用")
        
        logger.error("所有登录服务都失败，无法获取有效cookies")
        return None
    
    def get_total_feed_pages(self, retry_count: int = 0) -> int:
        """获取feed页面总数"""
        # 防止无限递归，最多重试2次
        if retry_count > 2:
            logger.error("已达到最大重试次数，停止重试")
            return 0
            
        try:
            # 获取cookie：优先使用手动传入的cookie，否则使用自动登录获取的cookie
            if self.manual_cookie:
                cookie_string = self.manual_cookie
                logger.info("使用手动传入的cookie访问feed页面")
            else:
                cookie_string = self.get_auth_cookies_with_fallback()
                logger.info("使用自动登录获取的cookie访问feed页面")
            
            headers = {
                'Cookie': cookie_string or self.default_cookie,
                'Referer': 'https://123av.com/ja',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # 构建完整的feed URL，包含排序参数
            feed_url = f"{self.feed_base_url}?sort=recent_update"
            logger.info(f"访问feed页面: {feed_url}")
            
            response = self.session.get(feed_url, headers=headers, allow_redirects=True)
            
            # 检查是否发生了跳转
            if response.history:
                logger.info(f"检测到跳转: {len(response.history)} 次重定向")
                for i, resp in enumerate(response.history):
                    logger.info(f"重定向 {i+1}: {resp.status_code} -> {resp.url}")
                logger.info(f"最终URL: {response.url}")
                
                # 如果跳转到登录页面，说明需要重新登录
                if 'login' in response.url or 'signin' in response.url:
                    logger.warning("跳转到登录页面，需要重新登录")
                    if self.manual_cookie:
                        logger.error("使用手动cookie但跳转到登录页面，cookie可能已失效")
                        return 0
                    else:
                        # 使缓存失效并尝试重新登录
                        if hasattr(self.playwright_login_service, 'invalidate_cookie_cache'):
                            self.playwright_login_service.invalidate_cookie_cache()
                        if self.cloudflare_login_service and hasattr(self.cloudflare_login_service, 'clear_cache'):
                            self.cloudflare_login_service.clear_cache()
                        new_cookies = self.get_auth_cookies_with_fallback(force_refresh=True)
                        if new_cookies:
                            logger.info(f"重新登录后重试 (第{retry_count + 1}次重试)")
                            return self.get_total_feed_pages(retry_count + 1)
                        return 0
            
            if not response.ok:
                logger.error(f"获取feed页面失败: {response.status_code} - {response.url}")
                
                # 如果未授权，使缓存失效并强制刷新cookies，然后重试
                if response.status_code == 401:
                    logger.info("未授权响应(401)，使cookie缓存失效并刷新")
                    if self.manual_cookie:
                        logger.error("使用手动cookie但收到401未授权响应，cookie可能已失效")
                        return 0
                    else:
                        # 使缓存失效并尝试重新登录
                        if hasattr(self.playwright_login_service, 'invalidate_cookie_cache'):
                            self.playwright_login_service.invalidate_cookie_cache()
                        if self.cloudflare_login_service and hasattr(self.cloudflare_login_service, 'clear_cache'):
                            self.cloudflare_login_service.clear_cache()
                        new_cookies = self.get_auth_cookies_with_fallback(force_refresh=True)
                        if new_cookies:
                            logger.info(f"cookie刷新后重试 (第{retry_count + 1}次重试)")
                            return self.get_total_feed_pages(retry_count + 1)  # 递归调用重试
                elif response.status_code == 403:
                    logger.error("访问被禁止(403)，可能需要重新登录或账户被限制")
                elif response.status_code == 404:
                    logger.error("feed页面不存在(404)，URL可能已变更")
                return 0
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 检查页面内容是否为登录页面
            if soup.select('form[action*="signin"]') or soup.select('input[name="username"]'):
                logger.warning("页面内容显示为登录页面，需要重新登录")
                if self.manual_cookie:
                    logger.error("使用手动cookie但页面显示为登录页面，cookie可能已失效")
                    return 0
                else:
                    # 使缓存失效并尝试重新登录
                    if hasattr(self.playwright_login_service, 'invalidate_cookie_cache'):
                        self.playwright_login_service.invalidate_cookie_cache()
                    if self.cloudflare_login_service and hasattr(self.cloudflare_login_service, 'clear_cache'):
                        self.cloudflare_login_service.clear_cache()
                    new_cookies = self.get_auth_cookies_with_fallback(force_refresh=True)
                    if new_cookies:
                        logger.info(f"重新登录后重试 (第{retry_count + 1}次重试)")
                        return self.get_total_feed_pages(retry_count + 1)
                    return 0
            
            # 查找分页信息
            pagination_items = soup.select("nav.navigation li.page-item:not(.disabled)")
            if pagination_items:
                # 获取最后一页的页码
                try:
                    last_page_text = pagination_items[-3].get_text().strip()
                    total_pages = int(last_page_text)
                    logger.info(f"从分页信息解析到总页数: {total_pages}")
                    return total_pages
                except (ValueError, IndexError) as e:
                    logger.error(f"解析页码错误: {e}")
            
            # 如果找不到分页，检查是否有电影内容
            movie_elements = soup.select(".box-item")
            if movie_elements:
                logger.info(f"找到 {len(movie_elements)} 个电影元素，假设至少有1页")
                return 1
            else:
                logger.warning("未找到电影内容，可能页面结构已变更或需要登录")
                return 0
            
        except Exception as e:
            logger.error(f"getTotalFeedPages中的意外错误: {e}")
            return 0
    
    def get_movies_from_feed_page(self, page_number: int, retry_count: int = 0) -> Set[Movie]:
        """从feed页面获取电影信息"""
        # 防止无限递归，最多重试2次
        if retry_count > 2:
            logger.error(f"页面{page_number}已达到最大重试次数，停止重试")
            return set()
            
        movies = set()
        url = f"{self.feed_base_url}&page={page_number}"
        
        try:
            # 获取cookie：优先使用手动传入的cookie，否则使用自动登录获取的cookie
            if self.manual_cookie:
                cookie_string = self.manual_cookie
                logger.info(f"使用手动传入的cookie访问feed页面 {page_number}")
            else:
                cookie_string = self.get_auth_cookies_with_fallback()
                logger.info(f"使用自动登录获取的cookie访问feed页面 {page_number}")
            
            headers = {
                'Cookie': cookie_string or self.default_cookie
            }
            
            response = self.session.get(url, headers=headers)
            
            if not response.ok:
                logger.error(f"获取feed页面失败 url:{url}: HTTP {response.status_code}")
                
                # 如果未授权，使缓存失效并强制刷新cookies，然后重试
                if response.status_code == 401:
                    logger.info("未授权响应(401)，使cookie缓存失效并刷新")
                    if self.manual_cookie:
                        logger.error(f"使用手动cookie访问页面{page_number}但收到401未授权响应，cookie可能已失效")
                        return movies
                    else:
                        # 使缓存失效并尝试重新登录
                        if hasattr(self.playwright_login_service, 'invalidate_cookie_cache'):
                            self.playwright_login_service.invalidate_cookie_cache()
                        if self.cloudflare_login_service and hasattr(self.cloudflare_login_service, 'clear_cache'):
                            self.cloudflare_login_service.clear_cache()
                        new_cookies = self.get_auth_cookies_with_fallback(force_refresh=True)
                        if new_cookies:
                            logger.info(f"cookie刷新后重试页面{page_number} (第{retry_count + 1}次重试)")
                            return self.get_movies_from_feed_page(page_number, retry_count + 1)  # 递归调用重试
                return movies
            
            page_movies = self.extract_movie_from_element(response.text)
            movies.update(page_movies)
            
            return movies
            
        except Exception as e:
            logger.error(f"处理feed页面 {page_number} 时出错: {e}")
            return movies  # 失败时返回空集合
    
    def handle_feed_movies(self, pages_to_fetch: int) -> Set[Movie]:
        """处理feed电影 - 带分页的获取电影ID"""
        all_movies = set()
        
        try:
            # 获取总页数
            total_pages = self.get_total_feed_pages()
            logger.info(f"总feed页数: {total_pages}")
            
            # 限制为请求的页数
            pages_to_process = min(pages_to_fetch, total_pages)
            logger.info(f"处理 {pages_to_process} 个feed页面")
            
            # 处理每一页
            for page in range(1, pages_to_process + 1):
                logger.info(f"处理feed页面 {page} / {pages_to_process}")
                page_movies = self.get_movies_from_feed_page(page)
                page_movie_ids = {movie.original_id for movie in page_movies if movie.original_id}
                existing_count = self.count_existing_movies_by_ids(page_movie_ids)
                logger.info(f"在feed页面 {page} 找到 {existing_count} 个现有电影")
                
                if existing_count == len(page_movie_ids) and page_movie_ids:
                    logger.info(f"feed页面 {page} 上的所有电影都已存在")
                    break
                
                all_movies.update(page_movies)
                
                # 可选：在页面请求之间添加短暂暂停
                if page < pages_to_process:
                    time.sleep(1)  # 1秒暂停
            
            logger.info(f"找到的唯一电影ID总数: {len(all_movies)}")
            return all_movies
            
        except Exception as e:
            logger.error(f"处理feed电影时出错: {e}")
            return all_movies
    
    def process_feed_movies(self, pages_to_fetch: int) -> Dict[str, Any]:
        """处理feed电影 - 从feed获取和更新电影"""
        result = {
            'success': False,
            'message': '',
            'movies_found': 0,
            'movies_saved': 0,
            'errors': []
        }
        
        try:
            # 从feed获取电影ID
            movies = self.handle_feed_movies(pages_to_fetch)
            logger.info(f"在feed中找到 {len(movies)} 个电影ID")
            
            result['movies_found'] = len(movies)
            
            # 保存电影
            saved_count = self.save_movies_from_feed(movies)
            result['movies_saved'] = saved_count
            
            # 注释：123网站的m3u8不再可用
            # 处理新电影
            # for movie in movies:
            #     try:
            #         video_id_crawler_service.process_video_by_id(movie.code, movie.original_id)
            #     except Exception as e:
            #         logger.error(f"处理电影ID {movie.original_id} 时出错: {e}")
            #         result['errors'].append(f"处理电影 {movie.code} 时出错: {e}")
            
            result['success'] = True
            result['message'] = f"成功处理 {len(movies)} 个电影，保存了 {saved_count} 个"
            
        except Exception as e:
            logger.error(f"处理feed电影时出错: {e}")
            result['message'] = f"处理feed电影时出错: {e}"
            result['errors'].append(str(e))
        
        return result
    
    def save_movies_from_feed(self, movies: Set[Movie]) -> int:
        """从feed保存电影"""
        if not movies:
            return 0
        
        saved_count = 0
        for movie in movies:
            try:
                # 模拟事务保证persist()在一个事务中执行
                # 即使这个方法失败，也只会回滚这一个电影的事务
                if self.save_single_movie(movie):
                    saved_count += 1
            except Exception as e:
                # 在这里记录错误，而不是让它中断整个循环
                logger.warning(f"无法保存电影 '{movie.title}'，可能已经存在或数据格式错误。错误: {e}")
                # 继续处理下一个电影
        
        return saved_count
    
    def save_single_movie(self, movie: Movie) -> bool:
        """保存单个电影 - 模拟数据库操作"""
        try:
            # 检查是否已存在
            existing = next((m for m in self.movies_db if m.original_id == movie.original_id), None)
            if existing:
                logger.info(f"电影 {movie.code} 已存在，跳过")
                return False
            
            # 添加到模拟数据库
            self.movies_db.append(movie)
            logger.info(f"成功保存电影: {movie.code} - {movie.title}")
            return True
            
        except Exception as e:
            logger.error(f"保存电影 '{movie.title}' 时发生未知错误: {e}")
            raise
    
    def count_existing_movies_by_ids(self, movie_ids: Set[int]) -> int:
        """根据ID计算现有电影数量"""
        if not movie_ids:
            return 0
        
        existing_count = sum(1 for movie in self.movies_db if movie.original_id in movie_ids)
        return existing_count
    
    def extract_movie_from_element(self, html_content: str) -> List[Movie]:
        """从HTML元素提取电影信息"""
        movies = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            movie_elements = soup.select(".box-item")
            
            logger.info(f"在页面上找到 {len(movie_elements)} 个电影元素")
            
            for element in movie_elements:
                try:
                    movie = Movie()
                    
                    # 1. 从img标签提取缩略图和代码
                    img_element = element.select_one("img.lazyload")
                    if img_element:
                        # 缩略图
                        thumbnail = img_element.get('data-src', '')
                        if thumbnail:
                            # 处理可能的列表类型
                            if isinstance(thumbnail, list):
                                movie.thumbnail = thumbnail[0] if thumbnail else None
                            else:
                                movie.thumbnail = thumbnail
                        
                        # 从title属性获取代码
                        code = img_element.get('title', '')
                        if code:
                            # 处理可能的列表类型
                            if isinstance(code, list):
                                code_str = code[0] if code else ''
                            else:
                                code_str = code
                            movie.code = code_str.strip() if code_str else None
                            # 先用代码作为基础标题
                            movie.title = code_str.strip() if code_str else None
                    
                    # 2. 如果从img标签没找到代码，从favourite按钮获取
                    if not movie.code:
                        favourite_button = element.select_one(".favourite")
                        if favourite_button:
                            code = favourite_button.get('data-code', '')
                            if code:
                                # 处理可能的列表类型
                                if isinstance(code, list):
                                    code_str = code[0] if code else ''
                                else:
                                    code_str = code
                                movie.code = code_str.strip() if code_str else None
                                if not movie.title:
                                    movie.title = code_str.strip() if code_str else None
                    
                    # 3. 从detail链接获取完整标题
                    detail_link = element.select_one(".detail a")
                    if detail_link:
                        full_text = detail_link.get_text()
                        # 处理可能的列表类型
                        if isinstance(full_text, list):
                            full_text = full_text[0] if full_text else ''
                        full_text = full_text.strip() if full_text else ''
                        
                        if full_text:
                            first_dash_index = full_text.find(" - ")
                            if first_dash_index != -1:
                                second_dash_index = full_text.find(" - ", first_dash_index + 3)
                                
                                if second_dash_index != -1:
                                    # 提取第一个和第二个" - "之间的内容作为主标题
                                    main_title = full_text[first_dash_index + 3:second_dash_index].strip()
                                    if main_title:
                                        movie.title = main_title
                                else:
                                    # 如果只有一个" - "，提取其后的所有内容
                                    main_title = full_text[first_dash_index + 3:].strip()
                                    if main_title:
                                        movie.title = main_title
                            else:
                                # 如果没有" - "，使用整个文本作为标题
                                movie.title = full_text
                    
                    # 4. 提取原始ID和点赞数
                    favourite_button = element.select_one(".favourite")
                    if favourite_button:
                        v_scope = favourite_button.get('v-scope', '')
                        # 处理可能的列表类型
                        if isinstance(v_scope, list):
                            v_scope = v_scope[0] if v_scope else ''
                        
                        # 调试: 打印前5个电影的v-scope属性
                        if len(movies) < 5:
                            logger.info(f"电影代码: {movie.code}, v-scope属性: [{v_scope}]")
                        
                        # 匹配Favourite('movie', 数字, 数字)格式
                        # 第2个数字是originalId，第3个数字是点赞数
                        if v_scope:
                            pattern = re.compile(r"Favourite\('movie',\s*(\d+),\s*(\d+)\)")
                            match = pattern.search(str(v_scope))
                            if match:
                                # 获取第一个数字作为originalId
                                try:
                                    original_id = int(match.group(1))
                                    movie.original_id = original_id
                                    if len(movies) < 5:
                                        logger.info(f"成功解析originalId: {original_id} 对于电影: {movie.code}")
                                except ValueError:
                                    logger.warning(f"解析originalId失败: {match.group(1)}")
                                
                                # 获取第二个数字作为点赞数
                                try:
                                    movie.likes = int(match.group(2))
                                except ValueError:
                                    logger.warning(f"解析点赞数失败: {match.group(2)}")
                            else:
                                if len(movies) < 5:
                                    logger.warning(f"电影 {movie.code} 的v-scope模式匹配失败")
                    
                    # 5. 提取时长
                    duration_element = element.select_one(".duration")
                    if duration_element:
                        duration = duration_element.get_text()
                        # 处理可能的列表类型
                        if isinstance(duration, list):
                            duration = duration[0] if duration else ''
                        duration = duration.strip() if duration else ''
                        if duration:
                            movie.duration = duration
                    
                    # 6. 提取链接
                    link_element = element.select_one(".thumb a")
                    if link_element:
                        link = link_element.get('href', '')
                        # 处理可能的列表类型
                        if isinstance(link, list):
                            link = link[0] if link else ''
                        if link:
                            movie.link = link
                    
                    # 最后检查：确保至少有代码和标题
                    if movie.code and movie.title:
                        movie.status = "NEW"
                        movies.append(movie)
                    else:
                        logger.warning(f"跳过缺少代码或标题的电影. 代码: {movie.code}, 标题: {movie.title}")
                        
                except Exception as e:
                    logger.error(f"从元素提取电影详情时出错: {e}")
            
            return movies
            
        except Exception as e:
            logger.error(f"解析HTML内容时出错: {e}")
            return movies
    
    def get_all_movies(self) -> List[Dict[str, Any]]:
        """获取所有电影 - 用于API接口"""
        return [movie.to_dict() for movie in self.movies_db]
    
    def get_movie_by_id(self, original_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取电影"""
        movie = next((m for m in self.movies_db if m.original_id == original_id), None)
        return movie.to_dict() if movie else None

# 全局服务实例
feed_service = FeedService()

if __name__ == "__main__":
    # 测试代码
    service = FeedService()
    result = service.process_feed_movies(2)  # 处理前2页
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 显示所有电影
    all_movies = service.get_all_movies()
    print(f"\n总共找到 {len(all_movies)} 个电影:")
    for movie in all_movies[:5]:  # 只显示前5个
        print(f"- {movie['code']}: {movie['title']}")