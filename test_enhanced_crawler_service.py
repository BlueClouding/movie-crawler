#!/usr/bin/env python3
"""
测试增强版电影详情爬虫服务
使用改进的Cloudflare绕过策略
"""

import sys
import asyncio
import logging
from pathlib import Path
from typing import List

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_enhanced_crawler():
    """测试增强版爬虫服务"""
    
    # 由于这个服务依赖FastAPI的依赖注入，我们需要手动创建依赖
    # 这里我们创建一个简化版本用于测试
    
    from src.crawler.service.movie_detail_crawler_service import MovieDetailCrawlerService
    
    # 创建模拟的依赖项
    class MockCrawlerProgressService:
        def __init__(self):
            pass
    
    class MockMovieInfoRepository:
        def __init__(self):
            pass
        
        async def get_movie_info_by_code(self, code):
            return None
        
        async def create_movie_info(self, data):
            logger.info(f"模拟创建电影信息: {data.get('code', 'unknown')}")
            return True
        
        async def update_movie_info(self, code, updates):
            logger.info(f"模拟更新电影信息: {code}")
            return True
    
    class MockMovieRepository:
        def __init__(self):
            pass
        
        async def get_new_movies(self, limit):
            return []
    
    class MockDownloadUrlRepository:
        def __init__(self):
            pass
        
        async def create_download_url(self, data):
            logger.info(f"模拟保存下载链接: {data.get('code', 'unknown')}")
            return True
    
    # 手动创建服务实例
    service = MovieDetailCrawlerService.__new__(MovieDetailCrawlerService)
    
    # 手动初始化
    service._logger = logging.getLogger(MovieDetailCrawlerService.__name__)
    service._crawler_progress_service = MockCrawlerProgressService()
    service._movie_info_repository = MockMovieInfoRepository()
    service._movie_repository = MockMovieRepository()
    service._download_url_repository = MockDownloadUrlRepository()
    
    # 创建数据目录
    service._data_dir = Path(__file__).parent / "test_data"
    service._data_dir.mkdir(exist_ok=True, parents=True)
    
    # 初始化重试计数
    service._retry_counts = {}
    
    logger.info("🚀 开始测试增强版电影详情爬虫服务")
    
    # 测试电影代码列表
    test_movie_codes = [
        "ipzz-562",
        "ngod-266", 
        "sone-718"
    ]
    
    logger.info(f"📋 测试电影列表: {test_movie_codes}")
    
    try:
        # 使用单浏览器模式进行测试
        results = await service.batch_crawl_movie_details(
            movie_codes=test_movie_codes,
            language="ja",
            headless=False,  # 显示浏览器便于调试
            max_retries=2,
            use_single_browser=True  # 使用单浏览器模式
        )
        
        # 输出结果统计
        logger.info("\n" + "="*50)
        logger.info("📊 测试结果统计")
        logger.info(f"总数: {len(test_movie_codes)}")
        logger.info(f"成功: {len(results)}")
        logger.info(f"失败: {len(test_movie_codes) - len(results)}")
        logger.info(f"成功率: {len(results)/len(test_movie_codes)*100:.1f}%")
        
        # 详细结果
        for movie_code in test_movie_codes:
            if movie_code in results:
                info = results[movie_code]
                logger.info(f"✅ {movie_code}: {info.get('title', '未知标题')[:50]}")
                logger.info(f"   女优: {', '.join(info.get('actresses', []))}")
                logger.info(f"   时长: {info.get('duration_seconds', 0)} 秒")
                logger.info(f"   发布日期: {info.get('release_date', '未知')}")
            else:
                logger.info(f"❌ {movie_code}: 爬取失败")
        
        return results
        
    except Exception as e:
        logger.error(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return {}

async def test_single_movie():
    """测试单个电影的爬取"""
    
    from src.crawler.service.movie_detail_crawler_service import MovieDetailCrawlerService
    from src.app.utils.drission_utils import CloudflareBypassBrowser
    
    logger.info("🎬 开始测试单个电影爬取")
    
    # 创建服务实例（简化版）
    service = MovieDetailCrawlerService.__new__(MovieDetailCrawlerService)
    service._logger = logging.getLogger("SingleMovieTest")
    
    # 创建浏览器实例
    browser = None
    try:
        browser = CloudflareBypassBrowser(
            headless=False,  # 显示浏览器
            load_images=False,
            timeout=180,
            wait_after_cf=10
        )
        
        # 测试单个电影
        movie_code = "ipzz-562"
        logger.info(f"正在测试电影: {movie_code}")
        
        result_code, movie_info = await service._crawl_single_movie(
            movie_code=movie_code,
            language="ja",
            browser=browser,
            max_retries=2
        )
        
        if movie_info:
            logger.info(f"✅ 成功爬取电影: {movie_code}")
            logger.info(f"标题: {movie_info.get('title', '未知')}")
            logger.info(f"女优: {', '.join(movie_info.get('actresses', []))}")
            logger.info(f"时长: {movie_info.get('duration_seconds', 0)} 秒")
        else:
            logger.error(f"❌ 爬取失败: {movie_code}")
        
        return movie_info
        
    except Exception as e:
        logger.error(f"单个电影测试出错: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        if browser:
            try:
                browser.quit()
                logger.info("浏览器已关闭")
            except:
                pass

async def main():
    """主函数"""
    logger.info("🔧 选择测试模式:")
    logger.info("1. 批量测试 (3个电影)")
    logger.info("2. 单个电影测试")
    
    # 默认运行单个电影测试，因为它更容易调试
    choice = "2"
    
    if choice == "1":
        await test_enhanced_crawler()
    elif choice == "2":
        await test_single_movie()
    else:
        logger.info("运行单个电影测试...")
        await test_single_movie()

if __name__ == "__main__":
    asyncio.run(main())
