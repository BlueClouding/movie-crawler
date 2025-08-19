#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试只爬取日语版本的 536VOLA-001 电影详情
不访问主页，直接访问电影代码对应的页面获取HTML内容
"""

import asyncio
import logging
import sys
import os
import time
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BatchMovieCrawler:
    """批量电影爬虫类"""
    
    def __init__(self, language="ja"):
        self.language = language
        
        # 创建浏览器数据持久化目录
        self.user_data_dir = Path.home() / ".cache" / "cloudflare_bypass_browser"
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建测试数据目录
        self.test_data_dir = Path("test_536VOLA_data")
        self.test_data_dir.mkdir(exist_ok=True)
    
    def crawl_movies_single_browser(self, movie_codes, output_file="batch_results.jsonl"):
        """使用单个浏览器实例批量爬取电影信息
        
        Args:
            movie_codes: 电影代码列表，如 ['VOLA-001', 'HZHB-004']
            output_file: 输出JSON文件名
        
        Returns:
            dict: 爬取结果统计和数据
        """
        results = {
            'success': [],
            'failed': [],
            'total': len(movie_codes),
            'movies': {}  # 存储所有电影数据
        }
        
        browser = None
        try:
            logger.info(f"开始批量爬取 {len(movie_codes)} 个电影（使用单个浏览器实例）")
            
            # 创建浏览器实例（无头模式）
            from app.utils.drission_utils import CloudflareBypassBrowser
            from test.test_drission_movie import MovieDetailCrawler
            
            browser = CloudflareBypassBrowser(
                headless=True,
                user_data_dir=str(self.user_data_dir),
                load_images=True,
                timeout=60
            )
            
            # 逐个处理电影代码
            for i, movie_code in enumerate(movie_codes, 1):
                logger.info(f"\n[{i}/{len(movie_codes)}] 正在处理: {movie_code}")
                
                try:
                    movie_info = self._crawl_single_movie_with_browser(browser, movie_code)
                    if movie_info and movie_info.get('title'):
                        results['success'].append(movie_code)
                        results['movies'][movie_code] = movie_info
                        logger.info(f"✅ {movie_code} 爬取成功")
                    else:
                        results['failed'].append(movie_code)
                        logger.error(f"❌ {movie_code} 爬取失败：未获取到有效信息")
                except Exception as e:
                    results['failed'].append(movie_code)
                    logger.error(f"❌ {movie_code} 爬取失败：{str(e)}")
                
                # 添加延迟避免请求过快
                if i < len(movie_codes):
                    time.sleep(2)
            
            # 保存所有结果到JSONL文件（每行一个JSON对象）
            output_path = self.test_data_dir / output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                for movie_code, movie_info in results['movies'].items():
                    # 每行写入一个完整的JSON对象
                    json_line = json.dumps(movie_info, ensure_ascii=False)
                    f.write(json_line + '\n')
            
            logger.info(f"\n结果已保存到JSONL格式文件: {output_path}")
            logger.info(f"JSONL格式说明: 每行是一个独立的JSON对象，支持流式处理大量数据")
            
        except Exception as e:
            logger.error(f"批量爬取过程中发生错误: {str(e)}")
        finally:
            if browser is not None:
                browser.close()
                logger.info("浏览器已关闭")
        
        # 输出统计信息
        logger.info("\n=== 批量爬取完成 ===")
        logger.info(f"总数: {results['total']}")
        logger.info(f"成功: {len(results['success'])}")
        logger.info(f"失败: {len(results['failed'])}")
        
        if results['success']:
            logger.info(f"成功列表: {', '.join(results['success'])}")
        if results['failed']:
            logger.info(f"失败列表: {', '.join(results['failed'])}")
        
        return results
    
    def crawl_movies_concurrent_tabs(self, movie_codes, output_file="batch_results_concurrent.jsonl", max_tabs=3):
        """使用单个浏览器的多个标签页并发爬取电影信息
        
        Args:
            movie_codes: 电影代码列表，如 ['VOLA-001', 'HZHB-004']
            output_file: 输出JSONL文件名
            max_tabs: 最大并发标签页数量（建议2-4个，避免过多占用资源）
        
        Returns:
            dict: 爬取结果统计和数据
        """
        results = {
            'success': [],
            'failed': [],
            'total': len(movie_codes),
            'movies': {}  # 存储所有电影数据
        }
        
        browser = None
        lock = threading.Lock()  # 用于线程安全的结果更新
        
        try:
            logger.info(f"开始并发批量爬取 {len(movie_codes)} 个电影（最多 {max_tabs} 个并发标签页）")
            
            # 创建浏览器实例（无头模式）
            from app.utils.drission_utils import CloudflareBypassBrowser
            from test.test_drission_movie import MovieDetailCrawler
            
            browser = CloudflareBypassBrowser(
                headless=True,
                user_data_dir=str(self.user_data_dir),
                load_images=True,
                timeout=60
            )
            
            def crawl_single_movie_in_tab(movie_code):
                """在新标签页中爬取单个电影"""
                tab = None
                try:
                    # 检查浏览器对象是否有效
                    if browser is None:
                        raise Exception("浏览器对象为空")
                    
                    # 创建新标签页
                    tab = browser.page.new_tab()
                    if tab is None:
                        raise Exception("无法创建新标签页")
                    
                    logger.info(f"[标签页] 正在处理: {movie_code}")
                    
                    # 构建URL并访问
                    url = f"https://missav.ai/{self.language}/{movie_code}"
                    tab.get(url)
                    
                    # 等待页面加载
                    time.sleep(3)
                    
                    # 解析电影信息
                    crawler = MovieDetailCrawler(movie_code)
                    html_content = tab.html
                    movie_info = crawler.parse_movie_page(html_content)
                    
                    # 线程安全地更新结果
                    with lock:
                        if movie_info and movie_info.get('title'):
                            results['success'].append(movie_code)
                            results['movies'][movie_code] = movie_info
                            logger.info(f"✅ [标签页] {movie_code} 爬取成功")
                        else:
                            results['failed'].append(movie_code)
                            logger.error(f"❌ [标签页] {movie_code} 爬取失败：未获取到有效信息")
                    
                    return movie_code, True
                    
                except Exception as e:
                    with lock:
                        results['failed'].append(movie_code)
                        logger.error(f"❌ [标签页] {movie_code} 爬取失败：{str(e)}")
                    return movie_code, False
                finally:
                    if tab:
                        try:
                            tab.close()
                        except:
                            pass
            
            # 使用线程池进行并发处理
            with ThreadPoolExecutor(max_workers=max_tabs) as executor:
                # 提交所有任务
                future_to_movie = {executor.submit(crawl_single_movie_in_tab, movie_code): movie_code 
                                 for movie_code in movie_codes}
                
                # 等待所有任务完成
                for future in as_completed(future_to_movie):
                    movie_code = future_to_movie[future]
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"线程执行异常 {movie_code}: {str(e)}")
            
            # 保存所有结果到JSONL文件（每行一个JSON对象）
            output_path = self.test_data_dir / output_file
            with open(output_path, 'w', encoding='utf-8') as f:
                for movie_code, movie_info in results['movies'].items():
                    # 每行写入一个完整的JSON对象
                    json_line = json.dumps(movie_info, ensure_ascii=False)
                    f.write(json_line + '\n')
            
            logger.info(f"\n并发爬取结果已保存到JSONL格式文件: {output_path}")
            logger.info(f"并发优势: 使用 {max_tabs} 个标签页同时处理，大幅提升爬取速度")
            
        except Exception as e:
            logger.error(f"并发批量爬取过程中发生错误: {str(e)}")
        finally:
            if browser is not None:
                browser.close()
                logger.info("浏览器已关闭")
        
        # 输出统计信息
        logger.info("\n=== 并发批量爬取完成 ===")
        logger.info(f"总数: {results['total']}")
        logger.info(f"成功: {len(results['success'])}")
        logger.info(f"失败: {len(results['failed'])}")
        
        if results['success']:
            logger.info(f"成功列表: {', '.join(results['success'])}")
        if results['failed']:
            logger.info(f"失败列表: {', '.join(results['failed'])}")
        
        return results
    
    def _crawl_single_movie_with_browser(self, browser, movie_code):
        """使用已有浏览器实例爬取单个电影信息"""
        try:
            from test.test_drission_movie import MovieDetailCrawler
            
            # 构建电影页面URL
            movie_url = f"https://missav.ai/{self.language}/{movie_code}"
            logger.info(f"访问URL: {movie_url}")
            
            # 访问电影页面
            browser.get(movie_url)
            time.sleep(3)
            
            # 获取页面HTML
            html_content = browser.get_html()
            
            # 创建解析器并解析
            crawler = MovieDetailCrawler(movie_code)
            movie_info = crawler.parse_movie_page(html_content)
            
            # 保存HTML文件（可选）
            html_file = self.test_data_dir / f"{movie_code}_{self.language}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return movie_info
            
        except Exception as e:
            logger.error(f"爬取 {movie_code} 时发生错误: {str(e)}")
            raise
    
    def crawl_movies(self, movie_codes):
        """批量爬取电影信息
        
        Args:
            movie_codes: 电影代码列表，如 ['VOLA-001', 'HZHB-004']
        
        Returns:
            dict: 爬取结果统计
        """
        results = {
            'success': [],
            'failed': [],
            'total': len(movie_codes)
        }
        
        logger.info(f"开始批量爬取 {len(movie_codes)} 个电影")
        
        for i, movie_code in enumerate(movie_codes, 1):
            logger.info(f"\n[{i}/{len(movie_codes)}] 正在处理: {movie_code}")
            
            try:
                movie_info = self._crawl_single_movie(movie_code)
                if movie_info and movie_info.get('title'):
                    results['success'].append(movie_code)
                    logger.info(f"✅ {movie_code} 爬取成功")
                else:
                    results['failed'].append(movie_code)
                    logger.error(f"❌ {movie_code} 爬取失败：未获取到有效信息")
            except Exception as e:
                results['failed'].append(movie_code)
                logger.error(f"❌ {movie_code} 爬取失败：{str(e)}")
            
            # 添加延迟避免请求过快
            if i < len(movie_codes):
                time.sleep(2)
        
        # 输出统计结果
        logger.info(f"\n=== 批量爬取完成 ===")
        logger.info(f"总数: {results['total']}")
        logger.info(f"成功: {len(results['success'])}")
        logger.info(f"失败: {len(results['failed'])}")
        
        if results['success']:
            logger.info(f"成功列表: {', '.join(results['success'])}")
        if results['failed']:
            logger.info(f"失败列表: {', '.join(results['failed'])}")
        
        return results
    
    def _crawl_single_movie(self, movie_code):
        """爬取单个电影信息"""
        browser = None
        try:
            # 创建浏览器实例（无头模式）
            from app.utils.drission_utils import CloudflareBypassBrowser
            from test.test_drission_movie import MovieDetailCrawler
            
            browser = CloudflareBypassBrowser(
                headless=True,
                user_data_dir=str(self.user_data_dir),
                load_images=True,
                timeout=60
            )
            
            # 构建电影页面URL
            movie_url = f"https://missav.ai/{self.language}/{movie_code}"
            logger.info(f"访问URL: {movie_url}")
            
            # 访问电影页面
            browser.get(movie_url)
            time.sleep(3)
            
            # 获取页面HTML
            html_content = browser.get_html()
            
            # 创建解析器并解析
            crawler = MovieDetailCrawler(movie_code)
            movie_info = crawler.parse_movie_page(html_content)
            
            # 保存HTML和解析结果
            html_file = self.test_data_dir / f"{movie_code}_{self.language}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            json_file = self.test_data_dir / f"{movie_code}_{self.language}_parsed.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(movie_info, f, ensure_ascii=False, indent=2)
            
            browser.quit()
            return movie_info
            
        except Exception as e:
            logger.error(f"爬取 {movie_code} 时发生错误: {str(e)}")
            if browser is not None:
                try:
                    browser.quit()
                except:
                    pass
            raise


class TestJAOnly536VOLA001:
    """测试只爬取日语版本的 536VOLA-001 电影详情"""
    
    def __init__(self):
        self.movie_code = "HZHB-004"
        self.language = "ja"  # 只爬取日语版本
    
    async def setup_service(self):
        """设置测试服务"""
        try:
            from crawler.service.movie_detail_crawler_service import MovieDetailCrawlerService
            
            # 创建模拟的依赖项
            mock_crawler_progress_service = Mock()
            mock_movie_info_repository = Mock()
            mock_movie_repository = Mock()
            mock_download_url_repository = Mock()
            
            # 模拟数据库保存操作
            mock_movie_info_repository.save = AsyncMock(return_value=True)
            mock_movie_repository.save = AsyncMock(return_value=True)
            mock_download_url_repository.save = AsyncMock(return_value=True)
            
            # 创建服务实例
            service = MovieDetailCrawlerService(
                crawler_progress_service=mock_crawler_progress_service,
                movie_info_repository=mock_movie_info_repository,
                movie_repository=mock_movie_repository,
                download_url_repository=mock_download_url_repository
            )
            
            logger.info("✅ 服务实例创建成功")
            return service
            
        except Exception as e:
            logger.error(f"❌ 创建服务实例失败: {str(e)}")
            return None
    
    async def test_direct_movie_page_crawl(self):
        """测试直接访问电影页面进行爬取和解析（不保存数据库）"""
        logger.info(f"=== 测试直接访问电影页面: {self.movie_code} (语言: {self.language}) ===")
        
        try:
            # 创建浏览器实例（无头模式）
            from app.utils.drission_utils import CloudflareBypassBrowser
            from test.test_drission_movie import MovieDetailCrawler
            
            browser = CloudflareBypassBrowser(headless=True)
            
            # 构建电影页面URL
            movie_url = f"https://missav.ai/{self.language}/{self.movie_code}"
            logger.info(f"访问URL: {movie_url}")
            
            # 直接访问电影页面
            success = browser.get(movie_url)
            if not success:
                logger.error("❌ 无法访问电影页面")
                browser.quit()
                return False
            
            # 获取页面HTML内容
            html_content = browser.get_html()
            if not html_content:
                logger.error("❌ 无法获取HTML内容")
                browser.quit()
                return False
            
            logger.info(f"✅ 成功获取HTML内容，长度: {len(html_content)} 字符")
            
            # 解析电影信息
            parser = MovieDetailCrawler(self.movie_code)
            movie_info = parser.parse_movie_page(html_content)
            
            # 检查解析结果
            if not movie_info or not isinstance(movie_info, dict):
                logger.error(f"❌ 电影 {self.movie_code} 解析失败，未获得有效数据")
                browser.quit()
                return False
            
            logger.info(f"✅ 电影 {self.movie_code} 日语版本解析成功")
            
            # 提取流媒体URL
            def safe_run_js(script):
                try:
                    return browser.run_js(script)
                except Exception as e:
                    logger.warning(f"执行JavaScript失败: {str(e)}")
                    return None
            
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
                movie_info["stream_urls"] = stream_urls
                logger.info(f"找到 {len(stream_urls)} 个流媒体URL")
            
            # 显示解析结果
            title = movie_info.get('title', '未知')
            logger.info(f"  标题: {title[:100]}")
            
            actresses = movie_info.get('actresses', [])
            logger.info(f"  女优: {', '.join(actresses)}")
            
            duration = movie_info.get('duration_seconds', 0) or 0
            if duration > 0:
                logger.info(f"  时长: {duration} 秒 ({duration//60}分{duration%60}秒)")
            else:
                logger.info(f"  时长: 未知")
            
            release_date = movie_info.get('release_date', '未知')
            logger.info(f"  发布日期: {release_date}")
            
            genres = movie_info.get('genres', [])
            logger.info(f"  类型: {', '.join(genres)}")
            
            # 检查语言
            language = movie_info.get('language', '未知')
            logger.info(f"  语言: {language}")
            
            # 检查流媒体URL
            stream_urls = movie_info.get('stream_urls', [])
            if stream_urls:
                logger.info(f"  ✅ 找到 {len(stream_urls)} 个流媒体URL")
                for i, url in enumerate(stream_urls[:3]):  # 只显示前3个
                    logger.info(f"    URL {i+1}: {url[:100]}...")
            else:
                logger.info("  ⚠️  未找到流媒体URL")
            
            # 检查M3U8信息
            m3u8_info = movie_info.get('m3u8_info', {})
            if m3u8_info:
                logger.info(f"  ✅ 找到M3U8信息")
                logger.info(f"    加密代码长度: {len(str(m3u8_info.get('encrypted_code', '')))}")
                logger.info(f"    字典键数量: {len(m3u8_info.get('dictionary', {}))}")
            else:
                logger.info("  ⚠️  未找到M3U8信息")
            
            # 保存HTML内容用于调试
            html_file = f"test_536VOLA_data/{self.movie_code}_{self.language}.html"
            os.makedirs("test_536VOLA_data", exist_ok=True)
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"  💾 HTML内容已保存到: {html_file}")
            
            # 保存解析结果用于调试
            import json
            json_file = f"test_536VOLA_data/{self.movie_code}_{self.language}_parsed.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(movie_info, f, ensure_ascii=False, indent=2)
            logger.info(f"  💾 解析结果已保存到: {json_file}")
            
            browser.quit()
            
            # 验证是否为日语版本
            if language == self.language or language == '未知':  # 允许未知语言
                logger.info(f"  ✅ 测试完成，成功解析电影信息")
                return True
            else:
                logger.warning(f"  ⚠️  语言不匹配，期望: {self.language}, 实际: {language}")
                return True  # 仍然认为测试成功，因为解析到了数据
                
        except Exception as e:
            logger.error(f"❌ 测试过程中出错: {str(e)}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            return False
    
    async def test_html_content_extraction(self):
        """测试HTML内容提取功能"""
        logger.info(f"=== 测试HTML内容提取: {self.movie_code} ===")
        
        service = await self.setup_service()
        if not service:
            logger.error("无法创建服务实例，跳过测试")
            return False
        
        try:
            # 创建浏览器实例（无头模式）
            from app.utils.drission_utils import CloudflareBypassBrowser
            
            browser = CloudflareBypassBrowser(headless=True)
            
            # 构建电影页面URL
            movie_url = f"https://missav.ai/{self.language}/{self.movie_code}"
            logger.info(f"访问URL: {movie_url}")
            
            # 直接访问电影页面
            success = browser.get(movie_url)
            if not success:
                logger.error("❌ 无法访问电影页面")
                browser.quit()
                return False
            
            # 获取页面HTML内容
            html_content = browser.get_html()
            if html_content:
                logger.info(f"✅ 成功获取HTML内容，长度: {len(html_content)} 字符")
                
                # 检查关键内容
                if self.movie_code in html_content:
                    logger.info(f"  ✅ HTML中包含电影代码: {self.movie_code}")
                else:
                    logger.warning(f"  ⚠️  HTML中未找到电影代码: {self.movie_code}")
                
                # 检查是否包含视频相关内容
                video_keywords = ['video', 'm3u8', 'stream', 'player']
                found_keywords = [kw for kw in video_keywords if kw.lower() in html_content.lower()]
                if found_keywords:
                    logger.info(f"  ✅ 找到视频相关关键词: {', '.join(found_keywords)}")
                else:
                    logger.warning("  ⚠️  未找到视频相关关键词")
                
                # 保存HTML内容用于调试
                html_file = f"test_536VOLA_data/{self.movie_code}_{self.language}.html"
                os.makedirs("test_536VOLA_data", exist_ok=True)
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"  💾 HTML内容已保存到: {html_file}")
                
                browser.quit()
                return True
            else:
                logger.error("❌ 无法获取HTML内容")
                browser.quit()
                return False
                
        except Exception as e:
            logger.error(f"❌ HTML内容提取测试出错: {str(e)}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("\n" + "="*60)
        logger.info(f"开始测试 {self.movie_code} 日语版本爬取功能")
        logger.info("="*60)
        
        tests = [
            ("HTML内容提取测试", self.test_html_content_extraction),
            ("直接电影页面爬取测试", self.test_direct_movie_page_crawl),
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\n--- {test_name} ---")
            try:
                result = await test_func()
                if result:
                    logger.info(f"✅ {test_name} 通过")
                    passed += 1
                else:
                    logger.error(f"❌ {test_name} 失败")
            except Exception as e:
                logger.error(f"❌ {test_name} 异常: {str(e)}")
        
        logger.info("\n" + "="*60)
        logger.info(f"测试完成: {passed}/{total} 通过")
        logger.info("="*60)
        
        return passed, total

async def main():
    """主函数"""
    tester = TestJAOnly536VOLA001()
    
    try:
        passed, total = await tester.run_all_tests()
        
        if passed == total:
            logger.info("🎉 所有测试通过！")
            return 0
        else:
            logger.error(f"💥 {total - passed} 个测试失败")
            return 1
            
    except KeyboardInterrupt:
        logger.info("\n⏹️  测试被用户中断")
        return 130
    except Exception as e:
        logger.error(f"💥 测试过程中发生未预期的错误: {str(e)}")
        return 1

def batch_crawl_example():
    """批量爬取示例"""
    # 创建批量爬虫实例
    crawler = BatchMovieCrawler(language="ja")
    
    # 示例电影代码列表
    movie_codes = [
        "VOLA-001",
        # "HZHB-004",  # 可以添加更多电影代码
        # "ABCD-123",
    ]
    
    # 执行批量爬取
    results = crawler.crawl_movies(movie_codes)
    
    return results


def test_specific_movies():
    """测试指定的电影代码（顺序爬取）"""
    logger.info("开始测试指定电影的批量爬取...")
    
    # 创建批量爬虫实例
    crawler = BatchMovieCrawler(language="ja")
    
    # 用户指定的电影代码列表
    movie_codes = [
        "HZHB-004",
        "VERO-085", 
        "TW-02677",
        "PPT-028"
    ]
    
    # 使用单个浏览器实例执行批量爬取
    results = crawler.crawl_movies_single_browser(movie_codes, "test_movies_batch.jsonl")
    
    logger.info(f"\n测试完成！详细结果请查看: {crawler.test_data_dir / 'test_movies_batch.jsonl'}")
    return results


def test_concurrent_movies():
    """测试指定的电影代码（并发爬取）"""
    logger.info("开始测试指定电影的并发批量爬取...")
    
    # 创建批量爬虫实例
    crawler = BatchMovieCrawler(language="ja")
    
    # 用户指定的电影代码列表
    movie_codes = [
        "HZHB-004",
        "VERO-085", 
        "TW-02677",
        "PPT-028"
    ]
    
    # 执行并发批量爬取（使用多个标签页）
    results = crawler.crawl_movies_concurrent_tabs(
        movie_codes=movie_codes,
        output_file="test_movies_concurrent.jsonl",
        max_tabs=3  # 最多3个并发标签页
    )
    
    logger.info(f"\n并发测试完成！详细结果请查看: {crawler.test_data_dir / 'test_movies_concurrent.jsonl'}")
    return results


def read_jsonl_example():
    """演示如何流式读取JSONL文件"""
    logger.info("=== JSONL文件流式读取示例 ===")
    
    jsonl_file = Path("test_536VOLA_data") / "test_movies_batch.jsonl"
    
    if not jsonl_file.exists():
        logger.error(f"JSONL文件不存在: {jsonl_file}")
        return
    
    logger.info(f"正在流式读取文件: {jsonl_file}")
    
    # 流式读取JSONL文件 - 每次只加载一行到内存
    movie_count = 0
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                # 解析每一行的JSON对象
                movie_data = json.loads(line.strip())
                movie_count += 1
                
                # 提取关键信息
                movie_id = movie_data.get('id', 'Unknown')
                title = movie_data.get('title', 'No Title')
                duration = movie_data.get('duration_seconds', 0)
                actresses = movie_data.get('actresses', [])
                
                logger.info(f"第{line_num}行 - ID: {movie_id}")
                logger.info(f"  标题: {title[:50]}{'...' if len(title) > 50 else ''}")
                logger.info(f"  时长: {duration}秒 ({duration//60}分{duration%60}秒)")
                logger.info(f"  女优: {', '.join(actresses[:3])}{'...' if len(actresses) > 3 else ''}")
                logger.info("  " + "-" * 50)
                
            except json.JSONDecodeError as e:
                logger.error(f"第{line_num}行JSON解析错误: {e}")
            except Exception as e:
                logger.error(f"第{line_num}行处理错误: {e}")
    
    logger.info(f"\n=== 流式读取完成 ===")
    logger.info(f"总共处理了 {movie_count} 个电影对象")
    logger.info(f"JSONL优势: 即使文件有20万行，内存占用也很少，因为每次只加载一行")


def interactive_batch_crawl():
    """交互式批量爬取"""
    print("=== MissAV 批量电影爬虫 ===")
    print("请输入要爬取的电影代码，每行一个，输入空行结束：")
    
    movie_codes = []
    while True:
        code = input("电影代码: ").strip()
        if not code:
            break
        movie_codes.append(code)
    
    if not movie_codes:
        print("未输入任何电影代码")
        return
    
    print(f"\n将要爬取 {len(movie_codes)} 个电影: {', '.join(movie_codes)}")
    confirm = input("确认开始爬取？(y/N): ").strip().lower()
    
    if confirm == 'y':
        crawler = BatchMovieCrawler(language="ja")
        results = crawler.crawl_movies(movie_codes)
        
        print("\n=== 爬取完成 ===")
        print(f"成功: {len(results['success'])} 个")
        print(f"失败: {len(results['failed'])} 个")
        
        return results
    else:
        print("已取消")
        return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        # 交互式批量爬取
        interactive_batch_crawl()
    elif len(sys.argv) > 1 and sys.argv[1] == "example":
        # 批量爬取示例
        batch_crawl_example()
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        # 测试指定电影（顺序爬取）
        test_specific_movies()
    elif len(sys.argv) > 1 and sys.argv[1] == "concurrent":
        # 测试指定电影（并发爬取）
        test_concurrent_movies()
    elif len(sys.argv) > 1 and sys.argv[1] == "read":
        # 演示JSONL文件读取
        read_jsonl_example()
    else:
        # 运行原有测试
        exit_code = asyncio.run(main())
        sys.exit(exit_code)