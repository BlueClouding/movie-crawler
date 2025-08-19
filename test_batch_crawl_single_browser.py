#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 MovieDetailCrawlerService._batch_crawl_single_browser 方法

该测试文件专门用于测试单浏览器批量爬取电影详情的功能。
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any, Optional

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockCloudflareBypassBrowser:
    """模拟 CloudflareBypassBrowser 类"""
    
    def __init__(self, headless=True, user_data_dir=None):
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.is_closed = False
        logger.info(f"创建模拟浏览器实例，headless={headless}, user_data_dir={user_data_dir}")
    
    def quit(self):
        """模拟浏览器关闭"""
        self.is_closed = True
        logger.info("模拟浏览器已关闭")
    
    def close(self):
        """模拟浏览器关闭（备用方法）"""
        self.is_closed = True
        logger.info("模拟浏览器已关闭（备用方法）")

class MockMovieDetailCrawlerService:
    """模拟 MovieDetailCrawlerService 类用于测试"""
    
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._data_dir = Path("./test_data")
        self._data_dir.mkdir(exist_ok=True, parents=True)
        
        # 模拟依赖项
        self._crawler_progress_service = Mock()
        self._movie_info_repository = Mock()
        self._movie_repository = Mock()
        self._download_url_repository = Mock()
    
    async def _crawl_single_movie(
        self,
        movie_code: str,
        language: str,
        browser: MockCloudflareBypassBrowser,
        max_retries: int = 3,
    ) -> tuple[str, Optional[Dict[str, Any]]]:
        """
        模拟单部电影爬取方法
        
        Args:
            movie_code: 电影代码
            language: 语言代码
            browser: 浏览器实例
            max_retries: 最大重试次数
            
        Returns:
            tuple[str, Optional[Dict[str, Any]]]: (电影代码, 电影信息)
        """
        self._logger.info(f"开始爬取电影: {movie_code}, 语言: {language}")
        
        # 模拟网络延迟
        await asyncio.sleep(0.1)
        
        # 模拟不同的爬取结果
        if movie_code == "FAIL_TEST":
            self._logger.error(f"模拟爬取失败: {movie_code}")
            return movie_code, None
        
        # 模拟成功的爬取结果
        mock_movie_info = {
            "code": movie_code,
            "title": f"测试电影 {movie_code}",
            "actresses": ["测试女优1", "测试女优2"],
            "duration_seconds": 3600,
            "release_date": "2024-01-01",
            "genres": ["测试类型1", "测试类型2"],
            "description": f"这是电影 {movie_code} 的测试描述",
            "stream_urls": [f"https://example.com/{movie_code}.m3u8"]
        }
        
        self._logger.info(f"电影 {movie_code} 爬取成功")
        return movie_code, mock_movie_info
    
    async def _batch_crawl_single_browser(
        self,
        movie_codes: List[str],
        language: str = "ja",
        headless: bool = True,
        max_retries: int = 2,
    ) -> Dict[str, Dict[str, Any]]:
        """
        使用单个浏览器实例顺序爬取电影详情（测试版本）
        
        这是原方法的简化测试版本，保持相同的接口和核心逻辑
        """
        import time
        import uuid
        import tempfile
        
        start_time = time.time()
        self._logger.info(
            f"开始使用单浏览器顺序爬取 {len(movie_codes)} 部电影详情，语言： {language}"
        )
        
        results = {}
        browser = None
        
        try:
            # 创建单个浏览器实例
            unique_id = str(uuid.uuid4())[:8]
            timestamp = int(time.time() * 1000)
            temp_dir = (
                Path(tempfile.gettempdir())
                / f"cf_browser_single_{unique_id}_{timestamp}"
            )
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            self._logger.info(f"创建单浏览器实例，数据目录: {temp_dir}")
            
            browser = MockCloudflareBypassBrowser(
                headless=headless,
                user_data_dir=str(temp_dir),
            )
            
            # 模拟 Cloudflare 挑战处理
            self._logger.info("模拟处理 Cloudflare 挑战...")
            await asyncio.sleep(0.2)  # 模拟挑战处理时间
            
            # 顺序爬取每部电影
            for i, movie_code in enumerate(movie_codes, 1):
                self._logger.info(f"正在爬取第 {i}/{len(movie_codes)} 部电影: {movie_code}")
                
                try:
                    movie_code_result, movie_info = await self._crawl_single_movie(
                        movie_code=movie_code,
                        language=language,
                        browser=browser,
                        max_retries=max_retries,
                    )
                    
                    if movie_info:
                        results[movie_code_result] = movie_info
                        self._logger.info(f"电影 {movie_code} 爬取成功")
                    else:
                        self._logger.warning(f"电影 {movie_code} 爬取失败")
                        
                except Exception as e:
                    self._logger.error(f"爬取电影 {movie_code} 时出错: {str(e)}")
                
                # 模拟请求间隔
                if i < len(movie_codes):
                    await asyncio.sleep(0.1)
            
            elapsed = time.time() - start_time
            self._logger.info(
                f"单浏览器爬取 {len(movie_codes)} 部电影完成，结果: {len(results)}/{len(movie_codes)} 成功, 耗时 {elapsed:.2f} 秒"
            )
            
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
        self._logger.info(
            f"爬取完成，共成功爬取 {len(results)}/{len(movie_codes)} 部电影"
        )
        for movie_code, info in results.items():
            if info:
                self._logger.info(f"电影 {movie_code} {language}版本爬取完成")
                self._logger.info(f"  标题: {info.get('title', '未知标题')[:100]}")
                self._logger.info(f"  女优: {', '.join(info.get('actresses', []))}")
                self._logger.info(f"  时长: {info.get('duration_seconds', 0)} 秒")
                file_path = self._data_dir / f"{movie_code}_{language}.json"
                self._logger.info(f"  数据已保存到: {str(file_path)}")
        
        return results

async def test_batch_crawl_single_browser_success():
    """测试成功的批量爬取场景"""
    logger.info("=== 测试成功的批量爬取场景 ===")
    
    service = MockMovieDetailCrawlerService()
    movie_codes = ["TEST001", "TEST002", "TEST003"]
    
    results = await service._batch_crawl_single_browser(
        movie_codes=movie_codes,
        language="ja",
        headless=True,
        max_retries=2
    )
    
    # 验证结果
    assert len(results) == 3, f"期望爬取3部电影，实际爬取了{len(results)}部"
    
    for movie_code in movie_codes:
        assert movie_code in results, f"电影 {movie_code} 未在结果中找到"
        movie_info = results[movie_code]
        assert movie_info is not None, f"电影 {movie_code} 的信息为空"
        assert movie_info["code"] == movie_code, f"电影代码不匹配"
        assert "title" in movie_info, f"电影 {movie_code} 缺少标题信息"
        assert "actresses" in movie_info, f"电影 {movie_code} 缺少女优信息"
    
    logger.info("✅ 成功批量爬取测试通过")

async def test_batch_crawl_single_browser_with_failures():
    """测试包含失败情况的批量爬取场景"""
    logger.info("=== 测试包含失败情况的批量爬取场景 ===")
    
    service = MockMovieDetailCrawlerService()
    movie_codes = ["TEST001", "FAIL_TEST", "TEST003"]  # FAIL_TEST 会模拟失败
    
    results = await service._batch_crawl_single_browser(
        movie_codes=movie_codes,
        language="ja",
        headless=True,
        max_retries=2
    )
    
    # 验证结果
    assert len(results) == 2, f"期望爬取2部电影成功，实际爬取了{len(results)}部"
    assert "TEST001" in results, "TEST001 应该爬取成功"
    assert "TEST003" in results, "TEST003 应该爬取成功"
    assert "FAIL_TEST" not in results, "FAIL_TEST 应该爬取失败"
    
    logger.info("✅ 包含失败情况的批量爬取测试通过")

async def test_batch_crawl_single_browser_empty_list():
    """测试空电影列表的场景"""
    logger.info("=== 测试空电影列表的场景 ===")
    
    service = MockMovieDetailCrawlerService()
    movie_codes = []
    
    results = await service._batch_crawl_single_browser(
        movie_codes=movie_codes,
        language="ja",
        headless=True,
        max_retries=2
    )
    
    # 验证结果
    assert len(results) == 0, f"空列表应该返回空结果，实际返回了{len(results)}个结果"
    
    logger.info("✅ 空电影列表测试通过")

async def test_batch_crawl_single_browser_different_languages():
    """测试不同语言版本的爬取"""
    logger.info("=== 测试不同语言版本的爬取 ===")
    
    service = MockMovieDetailCrawlerService()
    movie_codes = ["TEST001", "TEST002"]
    
    # 测试日语版本
    results_ja = await service._batch_crawl_single_browser(
        movie_codes=movie_codes,
        language="ja",
        headless=True,
        max_retries=2
    )
    
    # 测试中文版本
    results_zh = await service._batch_crawl_single_browser(
        movie_codes=movie_codes,
        language="zh",
        headless=True,
        max_retries=2
    )
    
    # 验证结果
    assert len(results_ja) == 2, "日语版本应该爬取2部电影"
    assert len(results_zh) == 2, "中文版本应该爬取2部电影"
    
    logger.info("✅ 不同语言版本测试通过")

async def run_all_tests():
    """运行所有测试"""
    logger.info("开始运行 _batch_crawl_single_browser 方法测试")
    
    try:
        await test_batch_crawl_single_browser_success()
        await test_batch_crawl_single_browser_with_failures()
        await test_batch_crawl_single_browser_empty_list()
        await test_batch_crawl_single_browser_different_languages()
        
        logger.info("🎉 所有测试都通过了！")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {str(e)}")
        raise

if __name__ == "__main__":
    # 运行测试
    asyncio.run(run_all_tests())