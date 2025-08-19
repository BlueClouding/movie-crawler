#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：验证更新后的feed_service.py中的无头浏览器登录和feed页面跳转处理功能

功能测试：
1. PlaywrightLoginService的登录功能
2. FeedService的get_total_feed_pages方法，验证跳转处理
3. 完整的process_feed_movies流程
4. 详细的日志输出和错误处理
5. 性能统计和结果展示
"""

import time
import logging
from datetime import datetime
from feed_service import FeedService, PlaywrightLoginService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_feed_login.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def test_playwright_login_service():
    """
    测试PlaywrightLoginService的登录功能
    """
    logger.info("=== 开始测试 PlaywrightLoginService 登录功能 ===")
    start_time = time.time()
    
    try:
        login_service = PlaywrightLoginService()
        logger.info("PlaywrightLoginService 实例创建成功")
        
        # 测试获取认证cookies
        logger.info("正在获取认证cookies...")
        cookies = login_service.get_auth_cookies()
        
        if cookies:
            logger.info(f"成功获取cookies，数量: {len(cookies)}")
            for cookie_name in cookies.keys():
                logger.info(f"  - Cookie: {cookie_name}")
            return True
        else:
            logger.error("获取cookies失败")
            return False
            
    except Exception as e:
        logger.error(f"PlaywrightLoginService测试失败: {str(e)}")
        return False
    finally:
        elapsed_time = time.time() - start_time
        logger.info(f"PlaywrightLoginService测试耗时: {elapsed_time:.2f}秒")

def test_feed_service_pages():
    """
    测试FeedService的get_total_feed_pages方法，验证跳转处理
    """
    logger.info("=== 开始测试 FeedService 页面获取和跳转处理 ===")
    start_time = time.time()
    
    try:
        feed_service = FeedService()
        logger.info("FeedService 实例创建成功")
        
        # 测试获取总页数
        logger.info("正在获取feed总页数...")
        total_pages = feed_service.get_total_feed_pages()
        
        if total_pages and total_pages > 0:
            logger.info(f"成功获取feed总页数: {total_pages}")
            return total_pages
        else:
            logger.error("获取feed总页数失败")
            return 0
            
    except Exception as e:
        logger.error(f"FeedService页面测试失败: {str(e)}")
        return 0
    finally:
        elapsed_time = time.time() - start_time
        logger.info(f"FeedService页面测试耗时: {elapsed_time:.2f}秒")

def test_feed_movies_processing(max_pages=2):
    """
    测试完整的process_feed_movies流程
    """
    logger.info(f"=== 开始测试完整的 process_feed_movies 流程 (最多{max_pages}页) ===")
    start_time = time.time()
    
    try:
        feed_service = FeedService()
        logger.info("FeedService 实例创建成功")
        
        # 处理feed电影数据
        logger.info(f"正在处理前{max_pages}页的feed电影数据...")
        results = feed_service.process_feed_movies(max_pages=max_pages)
        
        if results:
            logger.info("=== Feed电影处理结果统计 ===")
            logger.info(f"处理页数: {results.get('pages_processed', 0)}")
            logger.info(f"总电影数: {results.get('total_movies', 0)}")
            logger.info(f"新增电影: {results.get('new_movies', 0)}")
            logger.info(f"重复电影: {results.get('duplicate_movies', 0)}")
            logger.info(f"处理错误: {results.get('errors', 0)}")
            
            # 显示部分电影信息
            movies = results.get('movies', [])
            if movies:
                logger.info("=== 前5部电影信息示例 ===")
                for i, movie in enumerate(movies[:5], 1):
                    logger.info(f"电影 {i}:")
                    logger.info(f"  标题: {movie.get('title', 'N/A')}")
                    logger.info(f"  代码: {movie.get('code', 'N/A')}")
                    logger.info(f"  时长: {movie.get('duration', 'N/A')}")
                    logger.info(f"  点赞数: {movie.get('likes', 'N/A')}")
                    logger.info(f"  链接: {movie.get('detail_url', 'N/A')}")
            
            return results
        else:
            logger.error("process_feed_movies返回空结果")
            return None
            
    except Exception as e:
        logger.error(f"Feed电影处理测试失败: {str(e)}")
        return None
    finally:
        elapsed_time = time.time() - start_time
        logger.info(f"Feed电影处理测试耗时: {elapsed_time:.2f}秒")

def test_error_handling():
    """
    测试错误处理和重试机制
    """
    logger.info("=== 开始测试错误处理和重试机制 ===")
    start_time = time.time()
    
    try:
        feed_service = FeedService()
        
        # 测试cookie缓存失效处理
        logger.info("测试cookie缓存失效处理...")
        feed_service.login_service.invalidate_cookie_cache()
        logger.info("Cookie缓存已失效")
        
        # 重新获取页面，应该触发重新登录
        logger.info("重新获取页面，测试自动重新登录...")
        total_pages = feed_service.get_total_feed_pages()
        
        if total_pages and total_pages > 0:
            logger.info(f"自动重新登录成功，获取到{total_pages}页")
            return True
        else:
            logger.error("自动重新登录失败")
            return False
            
    except Exception as e:
        logger.error(f"错误处理测试失败: {str(e)}")
        return False
    finally:
        elapsed_time = time.time() - start_time
        logger.info(f"错误处理测试耗时: {elapsed_time:.2f}秒")

def main():
    """
    主测试函数
    """
    logger.info("=" * 60)
    logger.info("开始执行 feed_service.py 无头浏览器登录和跳转处理功能测试")
    logger.info(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    total_start_time = time.time()
    test_results = {
        'playwright_login': False,
        'feed_pages': 0,
        'feed_processing': None,
        'error_handling': False
    }
    
    # 1. 测试PlaywrightLoginService登录功能
    test_results['playwright_login'] = test_playwright_login_service()
    
    # 2. 测试FeedService页面获取和跳转处理
    test_results['feed_pages'] = test_feed_service_pages()
    
    # 3. 测试完整的feed电影处理流程
    test_results['feed_processing'] = test_feed_movies_processing(max_pages=2)
    
    # 4. 测试错误处理和重试机制
    test_results['error_handling'] = test_error_handling()
    
    # 总结测试结果
    total_elapsed_time = time.time() - total_start_time
    
    logger.info("=" * 60)
    logger.info("测试结果总结")
    logger.info("=" * 60)
    logger.info(f"PlaywrightLoginService登录测试: {'✓ 通过' if test_results['playwright_login'] else '✗ 失败'}")
    logger.info(f"FeedService页面获取测试: {'✓ 通过' if test_results['feed_pages'] > 0 else '✗ 失败'} (获取到{test_results['feed_pages']}页)")
    logger.info(f"Feed电影处理测试: {'✓ 通过' if test_results['feed_processing'] else '✗ 失败'}")
    logger.info(f"错误处理测试: {'✓ 通过' if test_results['error_handling'] else '✗ 失败'}")
    
    if test_results['feed_processing']:
        results = test_results['feed_processing']
        logger.info(f"电影处理统计: 总计{results.get('total_movies', 0)}部，新增{results.get('new_movies', 0)}部")
    
    logger.info(f"总测试耗时: {total_elapsed_time:.2f}秒")
    logger.info(f"测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 判断整体测试是否成功
    success_count = sum([
        test_results['playwright_login'],
        test_results['feed_pages'] > 0,
        test_results['feed_processing'] is not None,
        test_results['error_handling']
    ])
    
    logger.info("=" * 60)
    if success_count >= 3:
        logger.info("🎉 整体测试通过！无头浏览器登录和feed页面跳转处理功能正常工作")
    else:
        logger.warning(f"⚠️  部分测试失败，通过率: {success_count}/4")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()