#!/usr/bin/env python3
"""MissAV 数据库集成爬虫主程序

该程序提供完整的数据库集成爬虫功能：
1. 执行数据库迁移
2. 从数据库获取待爬取电影代码
3. 批量爬取电影信息
4. 更新数据库状态
5. 生成统计报告
"""

import asyncio
import argparse
import logging
import sys
import json
import time
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from sqlalchemy import text
from src.common.utils.database_manager import DatabaseManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('database_crawler.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

class DirectMovieCrawler:
    """直接电影爬虫类，使用test_ja_only_536VOLA_001.py中验证的并发爬取方法"""
    
    def __init__(self, language="ja", output_dir="crawl_results"):
        self.language = language
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.user_data_dir = Path.home() / ".cache" / "missav_crawler" / "chrome_data"
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
    
    def crawl_movies_concurrent_tabs(self, movie_codes, output_file="batch_results_concurrent.jsonl", max_tabs=1):
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
                """使用独立浏览器实例爬取单个电影"""
                try:
                    logger.info(f"[标签页] 正在处理: {movie_code}")

                    # 从完整的link路径中提取电影代码（如 'v/jur-319' -> 'jur-319'）
                    actual_movie_code = movie_code.split('/')[-1] if '/' in movie_code else movie_code
                    
                    # 构建URL并访问
                    url = f"https://missav.ai/{self.language}/{actual_movie_code}"

                    # 使用增强的重试机制爬取
                    movie_info = self._crawl_with_enhanced_retry(url, actual_movie_code, max_retries=2)
                    
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
                    # 临时浏览器已在try块中关闭
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
            output_path = self.output_dir / output_file
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

    def _crawl_with_enhanced_retry(self, url: str, movie_code: str, max_retries: int = 2) -> dict:
        """使用增强重试机制爬取单个URL"""
        import random
        from test.test_drission_movie import MovieDetailCrawler

        for attempt in range(max_retries):
            logger.info(f"尝试第 {attempt + 1}/{max_retries} 次爬取: {url}")

            # 创建临时浏览器实例
            random_suffix = random.randint(1000, 9999)
            temp_user_data = self.user_data_dir / f"temp_{movie_code}_{random_suffix}"
            temp_user_data.mkdir(exist_ok=True)

            temp_browser = None
            try:
                from app.utils.drission_utils import CloudflareBypassBrowser

                temp_browser = CloudflareBypassBrowser(
                    headless=True,
                    user_data_dir=str(temp_user_data),
                    load_images=False,  # 不加载图片以提高速度
                    timeout=180,  # 增加超时时间
                    wait_after_cf=10  # Cloudflare挑战后等待更长时间
                )

                # 智能延迟避免检测（增加延迟时间）
                initial_delay = random.uniform(10, 30)  # 增加到10-30秒
                logger.info(f"初始延迟 {initial_delay:.1f} 秒以避免检测")
                time.sleep(initial_delay)

                # 尝试访问页面
                success = temp_browser.get(url, wait_for_cf=True, timeout=180)

                if success:
                    # 额外等待确保页面完全加载
                    time.sleep(random.uniform(2, 4))

                    html_content = temp_browser.get_html()

                    # 验证内容质量
                    if self._validate_content(html_content, url):
                        # 解析电影信息
                        crawler = MovieDetailCrawler(movie_code)
                        movie_info = crawler.parse_movie_page(html_content)

                        if movie_info and movie_info.get('title'):
                            logger.info(f"✅ 成功爬取: {url}")
                            return movie_info
                        else:
                            logger.warning(f"解析失败: {url}")
                    else:
                        logger.warning(f"内容验证失败: {url}")

            except Exception as e:
                logger.error(f"爬取过程中出错: {e}")

            finally:
                if temp_browser:
                    try:
                        temp_browser.close()
                    except:
                        pass

                # 清理临时目录
                try:
                    import shutil
                    if temp_user_data.exists():
                        shutil.rmtree(temp_user_data, ignore_errors=True)
                except:
                    pass

            # 失败后等待再重试（增加延迟时间）
            if attempt < max_retries - 1:
                retry_delay = random.uniform(30, 60) * (attempt + 1)  # 增加到30-60秒基础延迟
                logger.info(f"等待 {retry_delay:.1f} 秒后重试")
                time.sleep(retry_delay)

        logger.error(f"❌ 所有重试均失败: {url}")
        return {}

    def _validate_content(self, html_content: str, url: str) -> bool:
        """验证页面内容是否有效"""
        if not html_content or len(html_content) < 10000:
            return False

        # 检查是否仍然是Cloudflare挑战页面
        cf_indicators = [
            'cloudflare',
            'challenge',
            'cf-spinner',
            'cf-challenge',
            'security check',
            'checking your browser'
        ]

        html_lower = html_content.lower()
        for indicator in cf_indicators:
            if indicator in html_lower:
                logger.warning(f"检测到Cloudflare指标: {indicator}")
                return False

        # 检查是否包含预期的内容
        expected_indicators = [
            'missav',
            'video',
            'movie',
            'title'
        ]

        found_indicators = sum(1 for indicator in expected_indicators if indicator in html_lower)
        if found_indicators < 2:
            logger.warning(f"预期内容指标不足: {found_indicators}/4")
            return False

        return True

async def run_migration_only():
    """仅运行数据库迁移"""
    logger.info("=== 运行数据库迁移 ===")

    # 动态导入避免循环导入
    from src.crawler.missav_database_crawler import MissAVDatabaseCrawler
    crawler = MissAVDatabaseCrawler()
    try:
        success = await crawler.run_migration()
        if success:
            logger.info("数据库迁移成功完成")
            return True
        else:
            logger.error("数据库迁移失败")
            return False
    finally:
        await crawler.close()

async def show_status_summary():
    """显示电影爬取状态统计"""
    logger.info("=== 电影爬取状态统计 ===")
    
    db_manager = DatabaseManager()
    try:
        # 直接查询数据库获取状态统计
        async with db_manager.get_session() as session:
            # 查询各种状态的电影数量
            completed_query = text("SELECT COUNT(*) FROM movies WHERE miss_status = 'completed'")
            failed_query = text("SELECT COUNT(*) FROM movies WHERE miss_status = 'failed'")
            pending_query = text("SELECT COUNT(*) FROM movies WHERE miss_status = 'pending'")
            processing_query = text("SELECT COUNT(*) FROM movies WHERE miss_status = 'processing'")
            total_query = text("SELECT COUNT(*) FROM movies")
            
            completed_result = await session.execute(completed_query)
            failed_result = await session.execute(failed_query)
            pending_result = await session.execute(pending_query)
            processing_result = await session.execute(processing_query)
            total_result = await session.execute(total_query)
            
            stats = {
                'completed': completed_result.scalar(),
                'failed': failed_result.scalar(),
                'pending': pending_result.scalar(),
                'processing': processing_result.scalar(),
                'total': total_result.scalar()
            }
        
        print("\n电影爬取状态统计:")
        print("=" * 30)
        print(f"已完成: {stats['completed']}")
        print(f"失败: {stats['failed']}")
        print(f"待爬取: {stats['pending']}")
        print(f"爬取中: {stats['processing']}")
        print(f"总计: {stats['total']}")
        print()
        
        return stats
    finally:
        await db_manager.close()

async def run_single_batch(language: str = "ja", batch_size: int = 5):
    """运行单个批次的爬取
    
    Args:
        language: 爬取语言
        batch_size: 批次大小
    """
    logger.info(f"=== 运行单批次爬取 (语言: {language}, 批次大小: {batch_size}) ===")
    
    # 创建数据库管理器和直接爬虫
    db_manager = DatabaseManager()
    direct_crawler = DirectMovieCrawler(language=language)
    
    try:
        # 显示爬取前状态
        await show_status_summary()
        
        # 1. 获取待爬取的电影代码
        logger.info(f"正在获取 {batch_size} 个待爬取的电影代码...")
        movie_codes = await db_manager.get_pending_movie_codes(limit=batch_size)
        
        if not movie_codes:
            result = {
                'processed': 0,
                'success': 0,
                'failed': 0,
                'codes': [],
                'success_codes': [],
                'failed_codes': []
            }
            print("\n没有找到待爬取的电影")
            return result
        
        logger.info(f"获取到 {len(movie_codes)} 个待爬取电影: {', '.join(movie_codes)}")
        logger.info(f"电影代码详情: {movie_codes}")
        
        # 2. 更新状态为 processing
        await db_manager.update_movie_status(movie_codes, 'processing')
        
        try:
            # 3. 使用直接爬虫执行爬取
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"batch_crawl_{timestamp}.jsonl"
            
            logger.info(f"开始调用 crawl_movies_concurrent_tabs 方法...")
            logger.info(f"电影代码: {movie_codes}")
            logger.info(f"输出文件: {output_file}")
            
            crawl_results = direct_crawler.crawl_movies_concurrent_tabs(
                movie_codes=movie_codes,
                output_file=output_file,
                max_tabs=1  # 降低并发度以绕过Cloudflare
            )
            
            logger.info(f"爬取完成，结果: {crawl_results}")
            
            # 4. 根据爬取结果更新数据库状态
            if crawl_results['success']:
                await db_manager.update_movie_status(crawl_results['success'], 'completed')
            
            if crawl_results['failed']:
                await db_manager.update_movie_status(crawl_results['failed'], 'failed')
            
            result = {
                'processed': len(movie_codes),
                'success': len(crawl_results['success']),
                'failed': len(crawl_results['failed']),
                'codes': movie_codes,
                'success_codes': crawl_results['success'],
                'failed_codes': crawl_results['failed']
            }
            
        except Exception as e:
            logger.error(f"批次处理过程中发生错误: {e}")
            # 如果爬取过程出错，将状态重置为 pending
            await db_manager.update_movie_status(movie_codes, 'pending')
            
            result = {
                'processed': len(movie_codes),
                'success': 0,
                'failed': len(movie_codes),
                'codes': movie_codes,
                'success_codes': [],
                'failed_codes': movie_codes,
                'error': str(e)
            }
        
        # 显示结果
        print("\n单批次爬取结果:")
        print("-" * 40)
        print(f"处理电影数: {result['processed']}")
        print(f"成功爬取: {result['success']}")
        print(f"失败数量: {result['failed']}")
        
        if result['success_codes']:
            print(f"成功代码: {', '.join(result['success_codes'])}")
        
        if result['failed_codes']:
            print(f"失败代码: {', '.join(result['failed_codes'])}")
        
        if 'error' in result:
            print(f"错误信息: {result['error']}")
        
        print()
        
        # 显示爬取后状态
        await show_status_summary()
        
        return result
    finally:
        await db_manager.close()

async def run_continuous_crawling(language: str = "ja", batch_size: int = 5, max_batches: Optional[int] = None):
    """运行连续爬取
    
    Args:
        language: 爬取语言
        batch_size: 批次大小
        max_batches: 最大批次数
    """
    logger.info(f"=== 运行连续爬取 (语言: {language}, 批次大小: {batch_size}) ===")
    if max_batches:
        logger.info(f"最大批次数: {max_batches}")
    
    # 创建数据库管理器和直接爬虫
    db_manager = DatabaseManager()
    direct_crawler = DirectMovieCrawler(language=language)
    
    try:
        # 显示爬取前状态
        print("爬取前状态:")
        await show_status_summary()
        
        # 执行连续爬取
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
            
            # 获取待爬取的电影代码
            movie_codes = await db_manager.get_pending_movie_codes(limit=batch_size)
            
            if not movie_codes:
                logger.info("没有更多待爬取的电影，结束连续爬取")
                break
            
            # 更新状态为 processing
            await db_manager.update_movie_status(movie_codes, 'processing')
            
            try:
                # 执行爬取
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"batch_crawl_{timestamp}.jsonl"
                
                crawl_results = direct_crawler.crawl_movies_concurrent_tabs(
                    movie_codes=movie_codes,
                    output_file=output_file,
                    max_tabs=1  # 降低并发度以绕过Cloudflare
                )
                
                # 根据爬取结果更新数据库状态
                if crawl_results['success']:
                    await db_manager.update_movie_status(crawl_results['success'], 'completed')
                
                if crawl_results['failed']:
                    await db_manager.update_movie_status(crawl_results['failed'], 'failed')
                
                batch_result = {
                    'processed': len(movie_codes),
                    'success': len(crawl_results['success']),
                    'failed': len(crawl_results['failed']),
                    'codes': movie_codes,
                    'success_codes': crawl_results['success'],
                    'failed_codes': crawl_results['failed']
                }
                
            except Exception as e:
                logger.error(f"批次处理过程中发生错误: {e}")
                # 如果爬取过程出错，将状态重置为 pending
                await db_manager.update_movie_status(movie_codes, 'pending')
                
                batch_result = {
                    'processed': len(movie_codes),
                    'success': 0,
                    'failed': len(movie_codes),
                    'codes': movie_codes,
                    'success_codes': [],
                    'failed_codes': movie_codes,
                    'error': str(e)
                }
            
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
        
        # 显示最终结果
        print("\n连续爬取最终统计:")
        print("=" * 50)
        print(f"总批次数: {total_stats['total_batches']}")
        print(f"总处理数: {total_stats['total_processed']}")
        print(f"总成功数: {total_stats['total_success']}")
        print(f"总失败数: {total_stats['total_failed']}")
        
        if total_stats['total_processed'] > 0:
            success_rate = (total_stats['total_success'] / total_stats['total_processed']) * 100
            print(f"成功率: {success_rate:.1f}%")
        
        print()
        
        # 显示爬取后状态
        print("爬取后状态:")
        await show_status_summary()
        
        return total_stats
    finally:
        await db_manager.close()

def create_argument_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="MissAV 数据库集成爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s --migrate                    # 仅运行数据库迁移
  %(prog)s --status                     # 显示爬取状态统计
  %(prog)s --single                     # 运行单批次爬取
  %(prog)s --continuous                 # 运行连续爬取
  %(prog)s --continuous --max-batches 3 # 运行最多3个批次
  %(prog)s --single --language en --batch-size 3  # 自定义参数
"""
    )
    
    # 操作模式
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--migrate', action='store_true', help='仅运行数据库迁移')
    mode_group.add_argument('--status', action='store_true', help='显示电影爬取状态统计')
    mode_group.add_argument('--single', action='store_true', help='运行单批次爬取')
    mode_group.add_argument('--continuous', action='store_true', help='运行连续爬取直到完成')
    
    # 爬取参数
    parser.add_argument('--language', default='ja', choices=['ja', 'en', 'zh'], 
                       help='爬取语言 (默认: ja)')
    parser.add_argument('--batch-size', type=int, default=5, 
                       help='每批次爬取的电影数量 (默认: 5)')
    parser.add_argument('--max-batches', type=int, 
                       help='连续爬取的最大批次数 (仅用于 --continuous)')
    
    # 日志级别
    parser.add_argument('--log-level', default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='日志级别 (默认: INFO)')
    
    return parser

async def main():
    """主函数"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # 设置日志级别
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    try:
        if args.migrate:
            success = await run_migration_only()
            sys.exit(0 if success else 1)
        
        elif args.status:
            await show_status_summary()
        
        elif args.single:
            result = await run_single_batch(
                language=args.language,
                batch_size=args.batch_size
            )
            # 如果没有找到待爬取的电影，正常退出
            if result['processed'] == 0:
                logger.info("没有找到待爬取的电影")
                sys.exit(0)
            # 如果有处理但全部失败，返回错误码
            elif result['success'] == 0:
                logger.error("所有电影爬取都失败了")
                sys.exit(1)
        
        elif args.continuous:
            stats = await run_continuous_crawling(
                language=args.language,
                batch_size=args.batch_size,
                max_batches=args.max_batches
            )
            # 如果有处理但成功率过低，返回错误码
            if stats['total_processed'] > 0:
                success_rate = stats['total_success'] / stats['total_processed']
                if success_rate < 0.5:  # 成功率低于50%
                    logger.warning(f"成功率过低: {success_rate:.1f}%")
                    sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("用户中断程序")
        sys.exit(130)
    except Exception as e:
        logger.error(f"程序执行出错: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())