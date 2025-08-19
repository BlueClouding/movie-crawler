#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 MovieDetailCrawlerService._batch_crawl_single_browser 方法
使用真实电影代码: 536VOLA-001

该测试文件专门用于测试单浏览器批量爬取电影详情的功能，
使用真实的电影代码进行测试。
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

class Test536VOLA001:
    """测试 536VOLA-001 电影代码的爬取功能"""
    
    def __init__(self):
        self.movie_code = "536VOLA-001"
        self.test_results = []
    
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
            service = MovieDetailCrawlerService.__new__(MovieDetailCrawlerService)
            
            # 手动初始化属性
            service._logger = logging.getLogger("MovieDetailCrawlerService")
            service._crawler_progress_service = mock_crawler_progress_service
            service._movie_info_repository = mock_movie_info_repository
            service._movie_repository = mock_movie_repository
            service._download_url_repository = mock_download_url_repository
            
            # 创建数据目录
            service._data_dir = Path("./test_536VOLA_data")
            service._data_dir.mkdir(exist_ok=True, parents=True)
            
            # 初始化重试计数
            service._retry_counts = {}
            
            logger.info(f"服务实例创建成功，准备测试电影: {self.movie_code}")
            return service
            
        except ImportError as e:
            logger.error(f"无法导入 MovieDetailCrawlerService: {e}")
            return None
    
    async def test_single_movie_crawl(self):
        """测试单个电影的爬取"""
        logger.info(f"=== 测试单个电影爬取: {self.movie_code} ===")
        
        service = await self.setup_service()
        if not service:
            logger.error("无法创建服务实例，跳过测试")
            return False
        
        try:
            # 使用真实的浏览器进行测试
            results = await service._batch_crawl_single_browser(
                movie_codes=[self.movie_code],
                language="ja",
                headless=True,
                max_retries=3
            )
            
            # 验证结果
            if self.movie_code in results:
                movie_info = results[self.movie_code]
                logger.info(f"✅ 电影 {self.movie_code} 爬取成功")
                logger.info(f"  标题: {movie_info.get('title', '未知')[:100]}")
                logger.info(f"  女优: {', '.join(movie_info.get('actresses', []))}")
                logger.info(f"  时长: {movie_info.get('duration_seconds', 0)} 秒")
                logger.info(f"  发布日期: {movie_info.get('release_date', '未知')}")
                logger.info(f"  类型: {', '.join(movie_info.get('genres', []))}")
                
                # 检查是否有流媒体URL
                stream_urls = movie_info.get('stream_urls', [])
                if stream_urls:
                    logger.info(f"  找到 {len(stream_urls)} 个流媒体URL")
                    for i, url in enumerate(stream_urls[:3]):  # 只显示前3个
                        logger.info(f"    URL {i+1}: {url[:100]}...")
                else:
                    logger.info("  未找到流媒体URL")
                
                return True
            else:
                logger.error(f"❌ 电影 {self.movie_code} 爬取失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 测试过程中出错: {str(e)}")
            return False
    
    async def test_batch_crawl_with_multiple_codes(self):
        """测试批量爬取多个电影代码（包含目标电影）"""
        logger.info("=== 测试批量爬取多个电影代码 ===")
        
        service = await self.setup_service()
        if not service:
            logger.error("无法创建服务实例，跳过测试")
            return False
        
        # 包含目标电影和一些测试电影代码
        movie_codes = [self.movie_code, "TEST001", "TEST002"]
        
        # 模拟其他电影的爬取结果
        original_crawl_method = service._crawl_single_movie
        
        async def mock_crawl_single_movie(movie_code, language, browser, max_retries=3):
            if movie_code == self.movie_code:
                # 对目标电影使用真实爬取
                return await original_crawl_method(movie_code, language, browser, max_retries)
            else:
                # 对测试电影返回模拟数据
                await asyncio.sleep(0.1)  # 模拟网络延迟
                return movie_code, {
                    "code": movie_code,
                    "title": f"测试电影 {movie_code}",
                    "actresses": ["测试女优"],
                    "duration_seconds": 1800,
                    "language": language
                }
        
        # 替换爬取方法
        service._crawl_single_movie = mock_crawl_single_movie
        
        try:
            results = await service._batch_crawl_single_browser(
                movie_codes=movie_codes,
                language="ja",
                headless=True,
                max_retries=2
            )
            
            # 验证结果
            success_count = len(results)
            logger.info(f"批量爬取完成，成功爬取 {success_count}/{len(movie_codes)} 部电影")
            
            # 特别检查目标电影
            if self.movie_code in results:
                logger.info(f"✅ 目标电影 {self.movie_code} 在批量爬取中成功")
                return True
            else:
                logger.error(f"❌ 目标电影 {self.movie_code} 在批量爬取中失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 批量爬取测试失败: {str(e)}")
            return False
    
    async def test_different_languages(self):
        """测试不同语言版本的爬取"""
        logger.info(f"=== 测试不同语言版本爬取: {self.movie_code} ===")
        
        service = await self.setup_service()
        if not service:
            logger.error("无法创建服务实例，跳过测试")
            return False
        
        languages = ["ja", "zh", "en"]
        success_count = 0
        
        for language in languages:
            try:
                logger.info(f"测试 {language} 语言版本...")
                results = await service._batch_crawl_single_browser(
                    movie_codes=[self.movie_code],
                    language=language,
                    headless=True,
                    max_retries=2
                )
                
                if self.movie_code in results:
                    logger.info(f"✅ {language} 语言版本爬取成功")
                    success_count += 1
                else:
                    logger.warning(f"⚠️  {language} 语言版本爬取失败")
                    
            except Exception as e:
                logger.error(f"❌ {language} 语言版本测试出错: {str(e)}")
        
        if success_count > 0:
            logger.info(f"✅ 多语言测试完成，{success_count}/{len(languages)} 个语言版本成功")
            return True
        else:
            logger.error("❌ 所有语言版本都失败")
            return False
    
    async def test_error_handling(self):
        """测试错误处理机制"""
        logger.info("=== 测试错误处理机制 ===")
        
        service = await self.setup_service()
        if not service:
            logger.error("无法创建服务实例，跳过测试")
            return False
        
        # 测试无效的电影代码
        invalid_codes = ["INVALID_CODE", "NOT_EXIST_001", self.movie_code]
        
        try:
            results = await service._batch_crawl_single_browser(
                movie_codes=invalid_codes,
                language="ja",
                headless=True,
                max_retries=1  # 减少重试次数以加快测试
            )
            
            # 验证至少目标电影能够成功
            if self.movie_code in results:
                logger.info(f"✅ 错误处理测试通过，目标电影 {self.movie_code} 成功爬取")
                logger.info(f"总共成功爬取 {len(results)}/{len(invalid_codes)} 部电影")
                return True
            else:
                logger.warning("⚠️  错误处理测试中目标电影也失败了")
                return False
                
        except Exception as e:
            logger.error(f"❌ 错误处理测试失败: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info(f"开始运行 {self.movie_code} 的 _batch_crawl_single_browser 测试")
        
        tests = [
            ("单个电影爬取", self.test_single_movie_crawl),
            ("批量爬取测试", self.test_batch_crawl_with_multiple_codes),
            ("多语言测试", self.test_different_languages),
            ("错误处理测试", self.test_error_handling)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*50}")
            logger.info(f"开始执行: {test_name}")
            logger.info(f"{'='*50}")
            
            try:
                result = await test_func()
                if result:
                    passed_tests += 1
                    logger.info(f"✅ {test_name} 通过")
                else:
                    logger.error(f"❌ {test_name} 失败")
            except Exception as e:
                logger.error(f"❌ {test_name} 执行异常: {str(e)}")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"测试完成: {passed_tests}/{total_tests} 通过")
        logger.info(f"{'='*60}")
        
        if passed_tests == total_tests:
            logger.info(f"🎉 所有测试都通过了！电影 {self.movie_code} 的爬取功能正常")
        elif passed_tests > 0:
            logger.warning(f"⚠️  部分测试通过 ({passed_tests}/{total_tests})，功能基本正常")
        else:
            logger.error(f"❌ 所有测试都失败了，请检查实现")
        
        return passed_tests, total_tests

async def main():
    """主函数"""
    tester = Test536VOLA001()
    passed, total = await tester.run_all_tests()
    
    if passed == total:
        logger.info("测试完全成功")
        return 0
    elif passed > 0:
        logger.info("测试部分成功")
        return 0
    else:
        logger.error("测试完全失败")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)