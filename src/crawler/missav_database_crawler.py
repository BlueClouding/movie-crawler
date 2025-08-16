"""MissAV 数据库集成爬虫类，从数据库获取待爬取电影代码并进行批量爬取"""

import asyncio
import logging
import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# 导入数据库管理器
from common.utils.database_manager import DatabaseManager

# 导入现有的批量爬虫
sys.path.append(str(Path(__file__).parent.parent.parent))
from test_ja_only_536VOLA_001 import BatchMovieCrawler
from src.crawler.main_database_crawler import DirectMovieCrawler

logger = logging.getLogger(__name__)

class MissAVDatabaseCrawler:
    """MissAV 数据库集成爬虫类
    
    该类负责：
    1. 从数据库获取待爬取的电影代码
    2. 调用现有的 BatchMovieCrawler 进行爬取
    3. 更新数据库中的爬取状态
    4. 保存爬取结果到 JSONL 文件
    """
    
    def __init__(self, language: str = "ja", batch_size: int = 1):
        """初始化数据库爬虫

        Args:
            language: 爬取语言，默认为日语
            batch_size: 每批次爬取的电影数量，默认为1（降低并发以绕过Cloudflare）
        """
        self.language = language
        self.batch_size = batch_size
        self.db_manager = DatabaseManager()
        self.batch_crawler = BatchMovieCrawler(language=language)
        self.direct_crawler = DirectMovieCrawler(language=language)
        
        # 创建输出目录
        self.output_dir = Path("crawl_results")
        self.output_dir.mkdir(exist_ok=True)
        
        # 确保BatchMovieCrawler需要的目录存在
        test_data_dir = Path("test_536VOLA_data")
        test_data_dir.mkdir(exist_ok=True)
        crawl_results_dir = test_data_dir / "crawl_results"
        crawl_results_dir.mkdir(exist_ok=True)
        
        logger.info(f"初始化 MissAV 数据库爬虫 - 语言: {language}, 批次大小: {batch_size}")
    
    async def run_migration(self) -> bool:
        """运行数据库迁移，添加 miss_status 字段
        
        Returns:
            bool: 迁移是否成功
        """
        migration_file = Path("migrations/add_miss_status_to_movies.sql")
        if not migration_file.exists():
            logger.error(f"迁移文件不存在: {migration_file}")
            return False
        
        logger.info("开始执行数据库迁移...")
        success = await self.db_manager.execute_migration(str(migration_file))
        
        if success:
            logger.info("数据库迁移执行成功")
        else:
            logger.error("数据库迁移执行失败")
        
        return success
    
    async def get_pending_movies(self) -> List[str]:
        """获取待爬取的电影代码
        
        Returns:
            List[str]: 电影代码列表
        """
        logger.info(f"正在获取 {self.batch_size} 个待爬取的电影代码...")
        codes = await self.db_manager.get_pending_movie_codes(limit=self.batch_size)
        
        if codes:
            logger.info(f"获取到 {len(codes)} 个待爬取电影: {', '.join(codes)}")
        else:
            logger.info("没有找到待爬取的电影")
        
        return codes
    
    async def update_movies_status(self, codes: List[str], status: str) -> bool:
        """更新电影爬取状态
        
        Args:
            codes: 电影代码列表
            status: 新状态
            
        Returns:
            bool: 更新是否成功
        """
        if not codes:
            return True
        
        logger.info(f"更新 {len(codes)} 个电影状态为: {status}")
        return await self.db_manager.update_movie_status(codes, status)
    
    def crawl_movies_batch(self, movie_codes: List[str]) -> Dict[str, Any]:
        """批量爬取电影信息
        
        Args:
            movie_codes: 电影代码列表
            
        Returns:
            Dict[str, Any]: 爬取结果
        """
        if not movie_codes:
            return {'success': [], 'failed': [], 'total': 0, 'movies': {}}
        
        logger.info(f"开始批量爬取 {len(movie_codes)} 个电影...")
        
        # 生成输出文件名（包含时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"batch_crawl_{timestamp}.jsonl"
        output_path = self.output_dir / output_file
        
        # 使用成功的并发标签页方法进行爬取（直接复用成功案例）
        results = self.batch_crawler.crawl_movies_concurrent_tabs(
            movie_codes=movie_codes,
            output_file=str(output_path),
            max_tabs=3  # 使用3个并发标签页，与成功案例一致
        )
        
        logger.info(f"批量爬取完成 - 成功: {len(results['success'])}, 失败: {len(results['failed'])}")
        return results
    
    async def process_single_batch(self) -> Dict[str, Any]:
        """处理单个批次的电影爬取
        
        Returns:
            Dict: 包含处理结果的字典
        """
        try:
            # 获取待爬取的电影URL
            movie_urls = await self.db_manager.get_pending_movie_codes(limit=self.batch_size)
            
            if not movie_urls:
                logger.info("没有待爬取的电影")
                return {
                    'processed': 0,
                    'success': 0,
                    'failed': 0,
                    'success_codes': [],
                    'failed_codes': []
                }
            
            logger.info(f"获取到 {len(movie_urls)} 个待爬取电影URL: {movie_urls}")
            
            # 更新状态为processing
            await self.db_manager.update_movie_status(movie_urls, 'processing')
            
            # 使用DirectMovieCrawler的并发爬取方法
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"database_batch_{timestamp}.jsonl"
            
            logger.info(f"使用增强版爬虫服务处理 {len(movie_urls)} 个电影")

            # 使用增强版爬虫服务
            crawl_results = await self._use_enhanced_crawler_service(movie_urls, output_file)
            
            logger.info(f"并发爬取完成，结果: {crawl_results}")
            
            # 根据爬取结果更新数据库状态
            success_urls = crawl_results.get('success', [])
            failed_urls = crawl_results.get('failed', [])
            
            if success_urls:
                await self.db_manager.update_movie_status(success_urls, 'completed')
                logger.info(f"成功爬取 {len(success_urls)} 部电影: {success_urls}")
                
            if failed_urls:
                await self.db_manager.update_movie_status(failed_urls, 'failed')
                logger.info(f"爬取失败 {len(failed_urls)} 部电影: {failed_urls}")
            
            return {
                'processed': len(movie_urls),
                'success': len(success_urls),
                'failed': len(failed_urls),
                'success_codes': success_urls,
                'failed_codes': failed_urls
            }
            
        except Exception as e:
            logger.error(f"处理批次时发生错误: {e}")
            # 将所有电影状态重置为pending
            if 'movie_urls' in locals():
                await self.db_manager.update_movie_status(movie_urls, 'pending')
            return {
                'processed': 0,
                'success': 0,
                'failed': 0,
                'success_codes': [],
                'failed_codes': [],
                'error': str(e)
            }
    
    async def run_continuous_crawling(self, max_batches: Optional[int] = None) -> Dict[str, Any]:
        """运行连续爬取，直到没有待爬取的电影
        
        Args:
            max_batches: 最大批次数，None 表示无限制
            
        Returns:
            Dict[str, Any]: 总体统计结果
        """
        logger.info("开始连续爬取模式...")
        
        total_stats = {
            'total_batches': 0,
            'total_processed': 0,
            'total_success': 0,
            'total_failed': 0,
            'batch_results': []
        }
        
        batch_count = 0
        
        while True:
            batch_count += 1
            
            # 检查是否达到最大批次限制
            if max_batches and batch_count > max_batches:
                logger.info(f"达到最大批次限制 ({max_batches})，停止爬取")
                break
            
            logger.info(f"\n=== 开始第 {batch_count} 批次爬取 ===")
            
            # 处理单个批次
            batch_result = await self.process_single_batch()
            
            # 如果没有待处理的电影，结束循环
            if batch_result['processed'] == 0:
                logger.info("没有更多待爬取的电影，结束连续爬取")
                break
            
            # 更新总体统计
            total_stats['total_batches'] += 1
            total_stats['total_processed'] += batch_result['processed']
            total_stats['total_success'] += batch_result['success']
            total_stats['total_failed'] += batch_result['failed']
            total_stats['batch_results'].append(batch_result)
            
            logger.info(f"第 {batch_count} 批次完成 - 处理: {batch_result['processed']}, "
                       f"成功: {batch_result['success']}, 失败: {batch_result['failed']}")
            
            # 批次间延迟
            if batch_result['processed'] > 0:
                logger.info("批次间等待 5 秒...")
                time.sleep(5)
        
        # 输出最终统计
        logger.info("\n=== 连续爬取完成 ===")
        logger.info(f"总批次数: {total_stats['total_batches']}")
        logger.info(f"总处理数: {total_stats['total_processed']}")
        logger.info(f"总成功数: {total_stats['total_success']}")
        logger.info(f"总失败数: {total_stats['total_failed']}")
        
        return total_stats
    
    async def get_status_summary(self) -> Dict[str, int]:
        """获取电影爬取状态统计
        
        Returns:
            Dict[str, int]: 状态统计
        """
        return await self.db_manager.get_movie_status_count()
    
    async def close(self):
        """关闭数据库连接"""
        await self.db_manager.close()
        logger.info("数据库爬虫已关闭")

    async def _use_enhanced_crawler_service(self, movie_urls, output_file):
        """使用增强版爬虫服务处理电影列表"""
        from src.crawler.service.movie_detail_crawler_service import MovieDetailCrawlerService

        # 创建模拟的依赖项
        class MockCrawlerProgressService:
            pass

        class MockMovieInfoRepository:
            async def get_movie_info_by_code(self, code):
                return None
            async def create_movie_info(self, data):
                logger.info(f"保存电影信息: {data.get('code', 'unknown')}")
                return True
            async def update_movie_info(self, code, updates):
                logger.info(f"更新电影信息: {code}")
                return True

        class MockMovieRepository:
            async def get_new_movies(self, limit):
                return []

        class MockDownloadUrlRepository:
            async def create_download_url(self, data):
                logger.info(f"保存下载链接: {data.get('code', 'unknown')}")
                return True

        # 创建服务实例
        enhanced_service = MovieDetailCrawlerService.__new__(MovieDetailCrawlerService)
        enhanced_service._logger = logger
        enhanced_service._crawler_progress_service = MockCrawlerProgressService()
        enhanced_service._movie_info_repository = MockMovieInfoRepository()
        enhanced_service._movie_repository = MockMovieRepository()
        enhanced_service._download_url_repository = MockDownloadUrlRepository()
        enhanced_service._data_dir = Path(__file__).parent.parent.parent / "crawl_results"
        enhanced_service._data_dir.mkdir(exist_ok=True, parents=True)
        enhanced_service._retry_counts = {}

        # 提取电影代码
        movie_codes = [url.split('/')[-1] for url in movie_urls]

        try:
            # 使用增强版服务爬取
            results = await enhanced_service.batch_crawl_movie_details(
                movie_codes=movie_codes,
                language=self.language,
                headless=True,  # 生产环境使用无头模式
                max_retries=2,
                use_single_browser=True
            )

            # 转换结果格式以兼容原有逻辑
            success_codes = list(results.keys())
            failed_codes = [code for code in movie_codes if code not in success_codes]

            # 重建完整URL
            success_urls = [f"https://missav.ai/{self.language}/{code}" for code in success_codes]
            failed_urls = [f"https://missav.ai/{self.language}/{code}" for code in failed_codes]

            return {
                'success': success_urls,
                'failed': failed_urls,
                'total': len(movie_codes),
                'movies': results
            }

        except Exception as e:
            logger.error(f"增强版爬虫服务出错: {e}")
            # 回退到原有方法
            return self.direct_crawler.crawl_movies_concurrent_tabs(
                movie_codes=movie_urls,
                output_file=output_file,
                max_tabs=1
            )


async def main():
    """主函数 - 测试数据库集成爬虫"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    crawler = None
    try:
        # 创建爬虫实例
        crawler = MissAVDatabaseCrawler(language="ja", batch_size=2)
        
        # 获取当前状态统计
        logger.info("=== 当前电影爬取状态统计 ===")
        status_summary = await crawler.get_status_summary()
        for status, count in status_summary.items():
            logger.info(f"{status}: {count}")
        
        # 处理一个批次进行测试
        logger.info("\n=== 开始测试批次处理 ===")
        result = await crawler.process_single_batch()
        
        logger.info("\n=== 测试结果 ===")
        logger.info(f"处理数量: {result['processed']}")
        logger.info(f"成功数量: {result['success']}")
        logger.info(f"失败数量: {result['failed']}")
        
        if result.get('codes'):
            logger.info(f"处理的电影代码: {', '.join(result['codes'])}")
        
        if result.get('success_codes'):
            logger.info(f"成功的电影代码: {', '.join(result['success_codes'])}")
            
        if result.get('failed_codes'):
            logger.info(f"失败的电影代码: {', '.join(result['failed_codes'])}")
        
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
    finally:
        if crawler:
            await crawler.close()


if __name__ == "__main__":
    asyncio.run(main())