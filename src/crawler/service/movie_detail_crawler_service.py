"""Detail crawler module for fetching movie details."""

import logging
import random
import time
import asyncio
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse, urlunparse

from fastapi import Depends

from app.utils.drission_utils import CloudflareBypassBrowser
from crawler.parser.movie_parser import MovieParser
from crawler.parser.actress_parser import ActressParser
from crawler.service.crawler_progress_service import CrawlerProgressService
from crawler.repository.movie_repository import MovieRepository
from common.db.entity.movie import Movie, MovieStatus

class MovieDetailCrawlerService:
    """Crawler for fetching movie details."""
    
    def __init__(self,
        crawler_progress_service: CrawlerProgressService = Depends(CrawlerProgressService),
        movie_repository: MovieRepository = Depends(MovieRepository)
        ):
        """Initialize DetailCrawler.

        Args:
            crawler_progress_service: CrawlerProgressService instance for progress tracking
            movie_repository: MovieRepository instance for database operations
        """
        self._logger = logging.getLogger(__name__)
        
        # 创建一个保存结果的目录
        self._data_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))) / "data"
        self._data_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize parsers
        self._movie_parser = MovieParser()
        self._actress_parser = ActressParser()
        
        # Initialize retry counts
        self._retry_counts = {}
        
        # Service dependencies
        self._crawler_progress_service = crawler_progress_service
        self._movie_repository = movie_repository

    # 单次执行的方法
    async def process_movies_details_once(self, limit: int = 100) -> List[Movie]:
        """使用原有HTTP方法处理电影详情
        
        Args:
            limit: 单次处理的最大电影数量
            
        Returns:
            List[Movie]: 处理后的电影列表
        """
        # 这里保留原有实现，若无实现则可以抛出异常
        # 获取待处理的电影
        new_movies: List[Movie] = list(await self._movie_repository.get_new_movies(limit))
        if not new_movies:
            self._logger.info(f"No pending movies to process.")
            return []

        self._logger.info(f"Found {len(new_movies)} pending movies to process")
        

        # 处理每个电影
        processed_count = 0
        movies_details: List[Movie] = []
        
        # 每个电影单独处理，并且每个电影使用单独的数据库事务
        for movie in new_movies:
            try:
                movie_detail = await self._process_movie(movie)
                if movie_detail:
                    movies_details.append(movie_detail)
                    processed_count += 1
            except Exception as e:
                self._logger.error(f"Error processing movie {movie.code}: {str(e)}")

        self._logger.info(f"Successfully processed {processed_count} out of {len(new_movies)} pending movies in this cycle.")
        return movies_details

    async def _crawl_single_movie(self, movie_id: str, language: str, browser: CloudflareBypassBrowser, max_retries: int = 3) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        爬取单部电影的详情
        
        Args:
            movie_id: 电影ID
            language: 语言代码 (ja, en, zh)
            browser: 浏览器实例
            max_retries: 最大重试次数
            
        Returns:
            Tuple[str, Optional[Dict[str, Any]]]: 元组 (movie_id, movie_info)
        """
        
        # 定义一个安全的JavaScript执行函数，以兼容不同版本的CloudflareBypassBrowser
        def safe_run_js(script):
            """安全地执行JavaScript，支持不同版本的浏览器API"""
            try:
                # 尝试直接使用browser.run_js
                if hasattr(browser, 'run_js'):
                    return browser.run_js(script)
                # 如果不存在，尝试通过browser.page.run_js
                elif hasattr(browser, 'page') and hasattr(browser.page, 'run_js'):
                    return browser.page.run_js(script)
                else:
                    raise AttributeError("浏览器实例没有可用的run_js方法")
            except Exception as e:
                self._logger.error(f"执行JavaScript出错: {e}")
                return None
        from src.test.test_drission_movie import MovieDetailCrawler
        
        # 构建URL
        url = f"https://missav.ai/{language}/{movie_id}"
        self._logger.info(f"正在爬取电影: {movie_id}")
        
        # 实现重试逻辑
        for attempt in range(max_retries + 1):
            try:
                # 访问电影页面
                browser.get(url, timeout=15, wait_for_full_load=False)
                await asyncio.sleep(2.0)  # 给页面加载一些时间
                
                # 改进的页面检测逻辑 - 更宽松的检查条件
                check_script = """
                () => {
                    // 检查页面基本结构是否加载完成
                    const body = document.body;
                    if (!body) {
                        return {'status': 'loading', 'reason': 'body not found'};
                    }

                    // 检查页面内容长度
                    const bodyText = body.innerText || body.textContent || '';
                    if (bodyText.length < 100) {
                        return {'status': 'loading', 'reason': 'content too short'};
                    }

                    // 检查是否有Cloudflare挑战页面
                    if (bodyText.includes('Checking your browser') ||
                        bodyText.includes('Please wait') ||
                        bodyText.includes('DDoS protection')) {
                        return {'status': 'loading', 'reason': 'cloudflare challenge'};
                    }

                    // 检查多种可能的页面元素
                    const indicators = [
                        document.querySelector('meta[property="og:title"]'),
                        document.querySelector('.movie-info-panel'),
                        document.querySelector('h1'),
                        document.querySelector('.video-player'),
                        document.querySelector('.movie-detail'),
                        document.querySelector('title')
                    ];

                    const foundIndicators = indicators.filter(el => el !== null);

                    if (foundIndicators.length > 0) {
                        const title = document.querySelector('meta[property="og:title"]')?.getAttribute('content') ||
                                    document.querySelector('h1')?.textContent ||
                                    document.title ||
                                    'Found content';
                        return {'status': 'ready', 'title': title.trim(), 'indicators': foundIndicators.length};
                    }

                    // 如果没有找到特定元素，但页面内容足够长，也认为加载完成
                    if (bodyText.length > 1000) {
                        return {'status': 'ready', 'title': 'Content loaded', 'contentLength': bodyText.length};
                    }

                    return {'status': 'loading', 'reason': 'no indicators found'};
                }
                """

                # 执行检查脚本并验证页面状态
                page_status = safe_run_js(check_script)
                page_ready = False

                if isinstance(page_status, dict) and page_status.get('status') == 'ready':
                    page_ready = True
                    title = page_status.get('title', '')
                    indicators = page_status.get('indicators', 0)
                    content_length = page_status.get('contentLength', 0)

                    if title:
                        self._logger.info(f"页面已加载，标题: {title[:30]}...")
                    if indicators:
                        self._logger.info(f"找到 {indicators} 个页面指示器")
                    if content_length:
                        self._logger.info(f"页面内容长度: {content_length} 字符")
                else:
                    # 多次检查页面状态，但减少检查次数和等待时间
                    for check in range(2):  # 减少到2次检查
                        await asyncio.sleep(0.3)  # 减少等待时间
                        page_status = safe_run_js(check_script)
                        if isinstance(page_status, dict) and page_status.get('status') == 'ready':
                            page_ready = True
                            self._logger.info(f"第 {check+1} 次检查后页面加载完成")
                            break
                        else:
                            reason = page_status.get('reason', 'unknown') if isinstance(page_status, dict) else 'script error'
                            self._logger.debug(f"第 {check+1} 次检查未通过，原因: {reason}")

                # 如果页面检查失败，但CloudflareBypassBrowser已经确认页面加载，则信任浏览器的判断
                if not page_ready:
                    self._logger.warning(f"页面元素检查未通过，但浏览器已确认内容加载，继续处理...")
                    page_ready = True  # 信任CloudflareBypassBrowser的判断
                
                # 获取HTML内容并验证
                html_content = browser.html
                if not html_content:
                    self._logger.error(f"无法获取HTML内容")
                    if attempt < max_retries:
                        self._logger.info(f"将重试获取HTML内容 ({attempt+1}/{max_retries})")
                        await asyncio.sleep(1.0)
                        continue
                    return movie_id, None

                # 降低HTML内容长度要求，因为有些页面可能比较简洁
                if len(html_content) < 1000:
                    self._logger.warning(f"HTML内容较短: {len(html_content)} bytes，但仍尝试解析")

                # 解析电影详情
                parser = MovieDetailCrawler(movie_id)
                movie_info = parser.parse_movie_page(html_content)

                # 检查解析结果
                if not movie_info or not isinstance(movie_info, dict):
                    self._logger.error(f"电影 {movie_id} 解析失败，未获得有效数据")
                    if attempt < max_retries:
                        self._logger.info(f"将重试解析 ({attempt+1}/{max_retries})")
                        await asyncio.sleep(1.0)
                        continue
                    return movie_id, None

                # 提取流媒体URL - 修复正则表达式转义问题
                stream_script = """
                function() {
                    const streamUrls = [];
                    const scripts = document.querySelectorAll('script');
                    for (const script of scripts) {
                        const content = script.textContent || '';
                        if (content.includes('m3u8')) {
                            const m3u8Matches = content.match(/https?:\/\/[^"']+\.m3u8[^"']*/g);
                            if (m3u8Matches) {
                                streamUrls.push(...m3u8Matches);
                            }
                        }
                    }
                    return streamUrls;
                }
                """

                stream_urls = safe_run_js(stream_script)
                if stream_urls and isinstance(stream_urls, list):
                    movie_info['stream_urls'] = stream_urls
                    self._logger.info(f"找到 {len(stream_urls)} 个流媒体URL")

                # 保存电影信息到数据库 movie_info表
                await self._save_to_json(movie_info, movie_id, language)
                await self._save_to_db(movie_info, movie_id, language)
                self._logger.info(f"电影 {movie_id} 爬取成功")
                return movie_id, movie_info
                
            except Exception as e:
                self._logger.error(f"爬取电影 {movie_id} 出错: {str(e)}")
                if attempt < max_retries:
                    self._logger.info(f"将在 2 秒后重试 ({attempt+1}/{max_retries})")
                    await asyncio.sleep(2.0)
                else:
                    self._logger.error(f"电影 {movie_id} 爬取失败，已达到最大重试次数")
                    return movie_id, None
        
        return movie_id, None
    
    async def _save_to_db(self, movie_info: Dict[str, Any], movie_id: str, language: str = 'ja') -> None:
        """保存电影信息到数据库

        Args:
            movie_info: 电影详情
            movie_id: 电影ID
            language: 语言版本
        """
        if not movie_info or not isinstance(movie_info, dict):
            self._logger.error(f"电影 {movie_id} 信息无效，无法保存到数据库")
            return

        try:
            # 先检查电影是否已存在
            movie = self._movie_repository.get_movie_by_code(movie_id)
            if not movie:
                self._logger.warning(f"电影 {movie_id} 在数据库中不存在，无法更新")
                return

            # 提取并转换电影信息
            updates = {
                'status': 'completed',  # 更新爬取状态
                'updated_at': datetime.now()
            }

            # 常规字段映射
            field_mapping = {
                'title': 'title',
                'cover_url': 'cover',
                'thumbnail': 'thumbnail',
                'description': 'description',
                'duration_seconds': 'duration',
                'release_date': 'release_date',
                'producer': 'producer',
                'director': 'director',
                'studio': 'studio',
                'label': 'label',
                'series': 'series',
                'rating': 'rating'
            }

            for db_field, info_field in field_mapping.items():
                if info_field in movie_info and movie_info[info_field]:
                    updates[db_field] = movie_info[info_field]

            # 特殊字段处理
            # 女演员列表
            if 'actresses' in movie_info and isinstance(movie_info['actresses'], list):
                updates['actresses'] = movie_info['actresses']

            # 类别列表
            if 'genres' in movie_info and isinstance(movie_info['genres'], list):
                updates['genres'] = movie_info['genres']

            # 标签列表
            if 'tags' in movie_info and isinstance(movie_info['tags'], list):
                updates['tags'] = movie_info['tags']

            # 流媒体URL
            if 'stream_url' in movie_info and movie_info['stream_url']:
                updates['stream_url'] = movie_info['stream_url']
            elif 'stream_urls' in movie_info and isinstance(movie_info['stream_urls'], list) and movie_info['stream_urls']:
                updates['stream_url'] = movie_info['stream_urls'][0]  # 使用第一个URL

            # 语言特定字段
            if language:
                # 例如，保存不同语言版本的标题
                language_title_field = f'title_{language}'
                if 'title' in movie_info and movie_info['title']:
                    updates[language_title_field] = movie_info['title']

                # 例如，保存不同语言版本的描述
                language_desc_field = f'description_{language}'
                if 'description' in movie_info and movie_info['description']:
                    updates[language_desc_field] = movie_info['description']

            # 将数据保存到数据库
            # 使用数据实体的ID更新记录
            updated = await self._movie_repository.update_movie(movie.id, updates)

            if updated:
                self._logger.info(f"电影 {movie_id} 信息已成功保存到数据库")

                # 可选：更新关联记录，如女演员、类别等
                if 'actresses' in movie_info and isinstance(movie_info['actresses'], list):
                    await self._update_movie_actresses(movie.id, movie_info['actresses'])
            else:
                self._logger.warning(f"电影 {movie_id} 信息更新失败")

        except Exception as e:
            self._logger.error(f"保存电影 {movie_id} 信息到数据库时出错: {str(e)}")
            import traceback
            self._logger.error(traceback.format_exc())

    async def _update_movie_actresses(self, movie_id: int, actresses: List[str]) -> None:
        """更新电影的女演员关联

        Args:
            movie_id: 数据库中电影的ID
            actresses: 女演员名称列表
        """
        try:
            # 先检查所有女演员是否存在，不存在则创建
            for actress_name in actresses:
                # 调用仓库方法检查并创建女演员
                await self._movie_repository.find_or_create_actress(actress_name)

            # 更新电影与女演员的关联
            await self._movie_repository.update_movie_actresses(movie_id, actresses)

            self._logger.info(f"电影ID {movie_id} 的女演员关联已更新: {', '.join(actresses)}")
        except Exception as e:
            self._logger.error(f"更新电影ID {movie_id} 的女演员关联时出错: {str(e)}")


    async def _create_browser_pool(self, count: int, headless: bool = True) -> List[CloudflareBypassBrowser]:
        """
        创建多个浏览器实例

        注意：由于Chrome浏览器的限制，多个浏览器实例可能会共享同一个窗口。
        如果需要真正的多窗口支持，建议使用单浏览器顺序处理。

        Args:
            count: 要创建的浏览器数量
            headless: 是否使用无头浏览器

        Returns:
            List[CloudflareBypassBrowser]: 浏览器实例列表
        """
        browsers = []
        import uuid
        import tempfile

        for i in range(count):
            try:
                # 为每个浏览器实例创建完全独立的用户数据目录
                # 使用UUID确保目录名称的唯一性
                unique_id = str(uuid.uuid4())[:8]
                timestamp = int(time.time() * 1000)

                # 使用临时目录确保完全隔离
                temp_dir = Path(tempfile.gettempdir()) / f"cf_browser_{i}_{unique_id}_{timestamp}"
                temp_dir.mkdir(parents=True, exist_ok=True)

                self._logger.info(f"为浏览器 #{i+1} 创建独立数据目录: {temp_dir}")

                # 创建浏览器实例并优化它
                browser = CloudflareBypassBrowser(
                    headless=headless,
                    user_data_dir=str(temp_dir),
                    load_images=False,  # 禁用图片加载以提高速度
                    timeout=30,  # 增加超时时间
                    wait_after_cf=3  # 增加Cloudflare后的等待时间
                )

                # 先访问一次基础页面，通过Cloudflare挑战
                self._logger.info(f"浏览器 #{i+1} 正在初始化并通过Cloudflare挑战...")
                browser.get("https://missav.ai/", timeout=30, wait_for_full_load=True)
                await asyncio.sleep(5 if i == 0 else 3)  # 增加等待时间，第一个浏览器等待稍长
                browsers.append(browser)
                self._logger.info(f"浏览器 #{i+1} 创建并初始化成功")

                # 每创建一个浏览器后等待一段时间，避免同时创建多个浏览器导致资源竞争
                if i < count - 1:
                    await asyncio.sleep(3)  # 增加等待时间

            except Exception as e:
                self._logger.error(f"浏览器 #{i+1} 创建失败: {str(e)}")

        if len(browsers) < count:
            self._logger.warning(f"只成功创建了 {len(browsers)}/{count} 个浏览器实例")
            if len(browsers) == 0:
                self._logger.error("没有成功创建任何浏览器实例，这可能是由于Chrome的多实例限制")
                self._logger.info("建议使用单浏览器模式或检查系统资源")
        else:
            self._logger.info(f"成功创建 {len(browsers)}/{count} 个浏览器实例")

        return browsers
        
    async def batch_crawl_movie_details(self, movie_codes: List[str], language: str = 'ja', headless: bool = True, max_retries: int = 2, use_single_browser: bool = True) -> Dict[str, Dict[str, Any]]:
        """爬取电影详情

        Args:
            movie_codes: 电影代码列表
            language: 语言版本，'ja'表示日语，'zh'表示中文
            headless: 是否使用无头浏览器
            max_retries: 最大重试次数
            use_single_browser: 是否使用单浏览器模式（推荐，避免多浏览器窗口问题）

        Returns:
            Dict[str, Dict[str, Any]]: 电影代码到电影详情的映射
        """
        if use_single_browser:
            return await self._batch_crawl_single_browser(movie_codes, language, headless, max_retries)
        else:
            return await self._batch_crawl_multi_browser(movie_codes, language, headless, max_retries)

    async def _batch_crawl_single_browser(self, movie_codes: List[str], language: str = 'ja', headless: bool = True, max_retries: int = 2) -> Dict[str, Dict[str, Any]]:
        """使用单个浏览器实例顺序爬取电影详情（推荐方式）

        Args:
            movie_codes: 电影代码列表
            language: 语言版本，'ja'表示日语，'zh'表示中文
            headless: 是否使用无头浏览器
            max_retries: 最大重试次数

        Returns:
            Dict[str, Dict[str, Any]]: 电影代码到电影详情的映射
        """
        start_time = time.time()
        self._logger.info(f"开始使用单浏览器顺序爬取{len(movie_codes)}部电影详情，语言：{language}")

        results = {}
        browser = None

        try:
            # 创建单个浏览器实例
            import uuid
            import tempfile

            unique_id = str(uuid.uuid4())[:8]
            timestamp = int(time.time() * 1000)
            temp_dir = Path(tempfile.gettempdir()) / f"cf_browser_single_{unique_id}_{timestamp}"
            temp_dir.mkdir(parents=True, exist_ok=True)

            self._logger.info(f"创建单浏览器实例，数据目录: {temp_dir}")

            browser = CloudflareBypassBrowser(
                headless=headless,
                user_data_dir=str(temp_dir),
                load_images=False,  # 禁用图片加载以提高速度
                timeout=30,
                wait_after_cf=3
            )

            # 初始化浏览器并通过Cloudflare挑战
            self._logger.info("浏览器正在初始化并通过Cloudflare挑战...")
            browser.get("https://missav.ai/", timeout=30, wait_for_full_load=True)
            time.sleep(3)
            self._logger.info("浏览器初始化完成")

            # 顺序处理每部电影
            for i, movie_id in enumerate(movie_codes):
                self._logger.info(f"正在处理电影 {i+1}/{len(movie_codes)}: {movie_id}")

                movie_id_result, movie_info = await self._crawl_single_movie(
                    movie_id=movie_id,
                    language=language,
                    browser=browser,
                    max_retries=max_retries
                )

                if movie_info:
                    results[movie_id_result] = movie_info
                    self._logger.info(f"电影 {movie_id} 爬取成功")
                else:
                    self._logger.warning(f"电影 {movie_id} 爬取失败")

                # 在电影之间添加短暂延迟
                if i < len(movie_codes) - 1:
                    await asyncio.sleep(1)

            # 记录完成时间
            elapsed = time.time() - start_time
            self._logger.info(f"单浏览器爬取 {len(movie_codes)} 部电影完成，结果: {len(results)}/{len(movie_codes)} 成功, 耗时 {elapsed:.2f} 秒")

        except Exception as e:
            self._logger.error(f"单浏览器爬取过程中出错: {str(e)}")
        finally:
            # 关闭浏览器实例
            if browser:
                try:
                    browser.quit()
                    self._logger.info("浏览器已关闭")
                except Exception as e:
                    self._logger.warning(f"关闭浏览器时出错: {str(e)}")

        # 输出爬取结果统计
        self._logger.info(f"爬取完成，共成功爬取 {len(results)}/{len(movie_codes)} 部电影")
        for movie_id, info in results.items():
            if info:
                self._logger.info(f"电影 {movie_id} {language}版本爬取完成")
                self._logger.info(f"  标题: {info.get('title', '未知标题')[:100]}")
                self._logger.info(f"  女优: {', '.join(info.get('actresses', []))}")
                self._logger.info(f"  时长: {info.get('duration_seconds', 0)} 秒")
                self._logger.info(f"  数据已保存到: {self._data_dir}/{movie_id}_{language}.json")

        return results

    async def _batch_crawl_multi_browser(self, movie_codes: List[str], language: str = 'ja', headless: bool = True, max_retries: int = 2) -> Dict[str, Dict[str, Any]]:
        """使用多个浏览器实例并行爬取电影详情（可能存在窗口显示问题）

        注意：由于Chrome浏览器的限制，多个浏览器实例可能只显示一个窗口。
        建议使用单浏览器模式 (use_single_browser=True)。

        Args:
            movie_codes: 电影代码列表
            language: 语言版本，'ja'表示日语，'zh'表示中文
            headless: 是否使用无头浏览器
            max_retries: 最大重试次数

        Returns:
            Dict[str, Dict[str, Any]]: 电影代码到电影详情的映射
        """
        start_time = time.time()
        self._logger.info(f"开始并行爬取{len(movie_codes)}部电影详情，语言：{language}")
        self._logger.warning("注意：多浏览器模式可能只显示一个浏览器窗口，这是Chrome的正常行为")

        results = {}
        browsers = []

        try:
            # 确定要创建的浏览器实例数量
            worker_count = min(3, len(movie_codes))  # 减少到最多3个浏览器实例

            # 创建浏览器池
            browsers = self._create_browser_pool(worker_count, headless)

            if not browsers:
                self._logger.error("没有成功创建任何浏览器实例，回退到单浏览器模式")
                return await self._batch_crawl_single_browser(movie_codes, language, headless, max_retries)

            # 分配电影代码到不同浏览器实例
            movie_batches = [[] for _ in range(len(browsers))]
            for i, movie_id in enumerate(movie_codes):
                batch_index = i % len(browsers)
                movie_batches[batch_index].append(movie_id)

            self._logger.info(f"已将{len(movie_codes)}部电影分配给{len(browsers)}个浏览器实例")

            # 准备并发爬取任务
            async def crawl_batch(batch_movies, browser_index):
                browser = browsers[browser_index]
                batch_results = {}

                for movie_id in batch_movies:
                    movie_id_result, movie_info = await self._crawl_single_movie(
                        movie_id=movie_id,
                        language=language,
                        browser=browser,
                        max_retries=max_retries
                    )
                    if movie_info:
                        batch_results[movie_id_result] = movie_info

                return batch_results

            # 并发执行所有爬取任务
            tasks = []
            for i, batch in enumerate(movie_batches):
                if batch:  # 只处理非空批次
                    tasks.append(crawl_batch(batch, i))

            # 等待所有任务完成
            batch_results = await asyncio.gather(*tasks)

            # 合并所有结果
            for batch_result in batch_results:
                results.update(batch_result)

            # 记录完成时间
            elapsed = time.time() - start_time
            self._logger.info(f"并行爬取 {len(movie_codes)} 部电影完成，结果: {len(results)}/{len(movie_codes)} 成功, 耗时 {elapsed:.2f} 秒")

        except Exception as e:
            self._logger.error(f"批量爬取过程中出错: {str(e)}")
        finally:
            # 关闭所有浏览器实例
            for i, browser in enumerate(browsers):
                try:
                    browser.quit()
                    self._logger.info(f"浏览器 #{i+1} 已关闭")
                except Exception as e:
                    self._logger.warning(f"关闭浏览器 #{i+1} 时出错: {str(e)}")

        # 输出爬取结果统计
        self._logger.info(f"爬取完成，共成功爬取 {len(results)}/{len(movie_codes)} 部电影")
        for movie_id, info in results.items():
            if info:
                self._logger.info(f"电影 {movie_id} {language}版本爬取完成")
                self._logger.info(f"  标题: {info.get('title', '未知标题')[:100]}")
                self._logger.info(f"  女优: {', '.join(info.get('actresses', []))}")
                self._logger.info(f"  时长: {info.get('duration_seconds', 0)} 秒")
                self._logger.info(f"  数据已保存到: {self._data_dir}/{movie_id}_{language}.json")

        return results

    async def _save_to_json(self, movie_info: Dict[str, Any], movie_id: str, language: str = 'ja') -> None:
        """保存电影信息到JSON文件
        
        Args:
            movie_info: 电影详情
            movie_id: 电影ID
            language: 语言版本
        """
        try:
            # 确保数据目录存在
            data_dir = Path(self._data_dir)
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # 构建保存路径
            file_name = f"{movie_id}_{language}.json"
            file_path = data_dir / file_name
            
            # 将电影信息保存为JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(movie_info, f, ensure_ascii=False, indent=4)
                
            self._logger.info(f"电影 {movie_id} 的详情已保存到 {file_path}")
            
        except Exception as e:
            self._logger.error(f"保存电影信息时出错: {str(e)}")
            
    async def _process_movie(self, movie: Movie) -> Optional[Movie]:
        """Process a single movie using browser to handle Cloudflare

        Args:
            movie: Movie object to process

        Returns:
            Movie: Updated movie object or None if extraction fails
        """
        # Get movie code and build URL
        movie_code = getattr(movie, 'code', None)
        if not movie_code:
            self._logger.error(f"Movie has no code")
            return None

        # 使用CloudflareBypassBrowser爬取电影详情
        browser = None
        try:
            # 创建浏览器实例
            browser = CloudflareBypassBrowser(headless=True)
            
            # 爬取电影详情
            movie_id, movie_info = await self._crawl_single_movie(movie_code, 'ja', browser, max_retries=2)
            
            if not movie_info:
                self._logger.error(f"Failed to crawl movie details for {movie_code}")
                return None
                
            # 更新电影对象
            await self._save_to_db(movie_info, movie_id, 'ja')
            
            # 标记为已处理
            return movie
            
        except Exception as e:
            self._logger.error(f"Error processing movie {movie_code}: {str(e)}")
            return None
        finally:
            if browser:
                try:
                    browser.quit()
                except Exception as e:
                    self._logger.error(f"Error closing browser: {str(e)}")
                    try:
                        browser.close()
                    except:
                        pass

    def modify_url(self, url: str) -> str:
        parsed = urlparse(url)
        path_parts = parsed.path.split('/')  # 拆解路径
        
        # 查找最后一个 "v" 的位置
        try:
            v_index = path_parts.index("v", 2)  # 从第3个元素开始查找（跳过空字符串和 "ja"）
        except ValueError:
            return url  # 若未找到 "v"，返回原链接
    
        # 重组路径：保留 "ja" 和 "v" 之后的部分
        new_path = f"/{path_parts[1]}/v/{path_parts[v_index+1]}"
        new_parsed = parsed._replace(path=new_path)
        return urlunparse(new_parsed)
            

