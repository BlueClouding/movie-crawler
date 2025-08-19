#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成测试：MovieDetailCrawlerService._batch_crawl_single_browser 方法

该测试文件提供了对真实 MovieDetailCrawlerService 类的集成测试，
包含完整的依赖注入和数据库模拟。

使用方法:
    python3 test_integration_batch_crawl.py

测试覆盖:
    1. 正常批量爬取流程
    2. 异常处理和重试机制
    3. 浏览器资源管理
    4. 数据库保存操作
    5. 不同语言版本支持
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

class IntegrationTestRunner:
    """集成测试运行器"""
    
    def __init__(self):
        self.test_results = []
    
    async def setup_mocks(self):
        """设置模拟对象"""
        # 模拟数据库依赖
        self.mock_crawler_progress_service = Mock()
        self.mock_movie_info_repository = Mock()
        self.mock_movie_repository = Mock()
        self.mock_download_url_repository = Mock()
        
        # 模拟数据库保存操作
        self.mock_movie_info_repository.save = AsyncMock(return_value=True)
        self.mock_movie_repository.save = AsyncMock(return_value=True)
        self.mock_download_url_repository.save = AsyncMock(return_value=True)
        
        logger.info("模拟对象设置完成")
    
    async def create_test_service(self):
        """创建测试用的服务实例"""
        try:
            # 尝试导入真实的服务类
            from crawler.service.movie_detail_crawler_service import MovieDetailCrawlerService
            
            # 创建服务实例（使用模拟的依赖）
            service = MovieDetailCrawlerService.__new__(MovieDetailCrawlerService)
            
            # 手动初始化属性
            service._logger = logging.getLogger("MovieDetailCrawlerService")
            service._crawler_progress_service = self.mock_crawler_progress_service
            service._movie_info_repository = self.mock_movie_info_repository
            service._movie_repository = self.mock_movie_repository
            service._download_url_repository = self.mock_download_url_repository
            
            # 创建数据目录
            service._data_dir = Path("./test_integration_data")
            service._data_dir.mkdir(exist_ok=True, parents=True)
            
            # 初始化重试计数
            service._retry_counts = {}
            
            logger.info("真实服务实例创建成功")
            return service
            
        except ImportError as e:
            logger.error(f"无法导入 MovieDetailCrawlerService: {e}")
            return None
    
    @patch('app.utils.drission_utils.CloudflareBypassBrowser')
    async def test_batch_crawl_with_mock_browser(self, mock_browser_class):
        """测试使用模拟浏览器的批量爬取"""
        logger.info("=== 测试使用模拟浏览器的批量爬取 ===")
        
        # 设置模拟浏览器
        mock_browser = Mock()
        mock_browser.quit = Mock()
        mock_browser_class.return_value = mock_browser
        
        service = await self.create_test_service()
        if not service:
            logger.warning("跳过集成测试：无法创建服务实例")
            return False
        
        # 模拟 _crawl_single_movie 方法
        async def mock_crawl_single_movie(movie_code, language, browser, max_retries=3):
            await asyncio.sleep(0.05)  # 模拟网络延迟
            
            if movie_code == "INTEGRATION_FAIL":
                return movie_code, None
            
            return movie_code, {
                "code": movie_code,
                "title": f"集成测试电影 {movie_code}",
                "actresses": ["集成测试女优"],
                "duration_seconds": 1800,
                "language": language
            }
        
        # 替换原方法
        service._crawl_single_movie = mock_crawl_single_movie
        
        # 执行测试
        movie_codes = ["INTEGRATION_001", "INTEGRATION_002", "INTEGRATION_FAIL", "INTEGRATION_003"]
        
        try:
            results = await service._batch_crawl_single_browser(
                movie_codes=movie_codes,
                language="ja",
                headless=True,
                max_retries=2
            )
            
            # 验证结果
            expected_success_count = 3  # 除了 INTEGRATION_FAIL 之外都应该成功
            actual_success_count = len(results)
            
            assert actual_success_count == expected_success_count, \
                f"期望成功 {expected_success_count} 部，实际成功 {actual_success_count} 部"
            
            # 验证失败的电影不在结果中
            assert "INTEGRATION_FAIL" not in results, "失败的电影不应该在结果中"
            
            # 验证浏览器被正确关闭
            mock_browser.quit.assert_called_once()
            
            logger.info("✅ 模拟浏览器批量爬取测试通过")
            return True
            
        except Exception as e:
            logger.error(f"❌ 模拟浏览器批量爬取测试失败: {str(e)}")
            return False
    
    async def test_error_handling(self):
        """测试错误处理机制"""
        logger.info("=== 测试错误处理机制 ===")
        
        service = await self.create_test_service()
        if not service:
            logger.warning("跳过错误处理测试：无法创建服务实例")
            return False
        
        # 模拟浏览器创建失败的情况
        with patch('app.utils.drission_utils.CloudflareBypassBrowser') as mock_browser_class:
            mock_browser_class.side_effect = Exception("浏览器创建失败")
            
            try:
                results = await service._batch_crawl_single_browser(
                    movie_codes=["ERROR_TEST"],
                    language="ja",
                    headless=True,
                    max_retries=1
                )
                
                # 在浏览器创建失败的情况下，应该返回空结果
                assert len(results) == 0, "浏览器创建失败时应该返回空结果"
                
                logger.info("✅ 错误处理测试通过")
                return True
                
            except Exception as e:
                logger.error(f"❌ 错误处理测试失败: {str(e)}")
                return False
    
    async def test_empty_movie_list(self):
        """测试空电影列表处理"""
        logger.info("=== 测试空电影列表处理 ===")
        
        service = await self.create_test_service()
        if not service:
            logger.warning("跳过空列表测试：无法创建服务实例")
            return False
        
        with patch('app.utils.drission_utils.CloudflareBypassBrowser') as mock_browser_class:
            mock_browser = Mock()
            mock_browser.quit = Mock()
            mock_browser_class.return_value = mock_browser
            
            try:
                results = await service._batch_crawl_single_browser(
                    movie_codes=[],  # 空列表
                    language="ja",
                    headless=True,
                    max_retries=2
                )
                
                assert len(results) == 0, "空电影列表应该返回空结果"
                
                # 即使是空列表，浏览器也应该被创建和关闭
                mock_browser_class.assert_called_once()
                mock_browser.quit.assert_called_once()
                
                logger.info("✅ 空电影列表测试通过")
                return True
                
            except Exception as e:
                logger.error(f"❌ 空电影列表测试失败: {str(e)}")
                return False
    
    async def test_different_parameters(self):
        """测试不同参数组合"""
        logger.info("=== 测试不同参数组合 ===")
        
        service = await self.create_test_service()
        if not service:
            logger.warning("跳过参数测试：无法创建服务实例")
            return False
        
        with patch('app.utils.drission_utils.CloudflareBypassBrowser') as mock_browser_class:
            mock_browser = Mock()
            mock_browser.quit = Mock()
            mock_browser_class.return_value = mock_browser
            
            # 模拟成功的爬取
            async def mock_crawl_single_movie(movie_code, language, browser, max_retries=3):
                return movie_code, {
                    "code": movie_code,
                    "title": f"参数测试电影 {movie_code}",
                    "language": language
                }
            
            service._crawl_single_movie = mock_crawl_single_movie
            
            try:
                # 测试不同语言
                for language in ["ja", "zh", "en"]:
                    results = await service._batch_crawl_single_browser(
                        movie_codes=["PARAM_TEST"],
                        language=language,
                        headless=True,
                        max_retries=1
                    )
                    
                    assert len(results) == 1, f"语言 {language} 测试失败"
                    assert results["PARAM_TEST"]["language"] == language, f"语言参数传递失败"
                
                # 测试不同的 headless 设置
                for headless in [True, False]:
                    results = await service._batch_crawl_single_browser(
                        movie_codes=["HEADLESS_TEST"],
                        language="ja",
                        headless=headless,
                        max_retries=1
                    )
                    
                    assert len(results) == 1, f"headless={headless} 测试失败"
                
                logger.info("✅ 不同参数组合测试通过")
                return True
                
            except Exception as e:
                logger.error(f"❌ 不同参数组合测试失败: {str(e)}")
                return False
    
    async def run_all_tests(self):
        """运行所有集成测试"""
        logger.info("开始运行 _batch_crawl_single_browser 集成测试")
        
        await self.setup_mocks()
        
        tests = [
            self.test_batch_crawl_with_mock_browser,
            self.test_error_handling,
            self.test_empty_movie_list,
            self.test_different_parameters
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test in tests:
            try:
                result = await test()
                if result:
                    passed_tests += 1
            except Exception as e:
                logger.error(f"测试执行异常: {str(e)}")
        
        logger.info(f"集成测试完成: {passed_tests}/{total_tests} 通过")
        
        if passed_tests == total_tests:
            logger.info("🎉 所有集成测试都通过了！")
        else:
            logger.warning(f"⚠️  有 {total_tests - passed_tests} 个测试失败")
        
        return passed_tests == total_tests

async def main():
    """主函数"""
    runner = IntegrationTestRunner()
    success = await runner.run_all_tests()
    
    if success:
        logger.info("所有测试通过，_batch_crawl_single_browser 方法工作正常")
        return 0
    else:
        logger.error("部分测试失败，请检查实现")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)