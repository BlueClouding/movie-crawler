#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进版并发爬取脚本 - 数据库批量处理，支持断点继续
"""

import json
import time
import logging
import random
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(asctime)s - %(name)s - %(filename)s:%(lineno)d - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

def wait_for_cloudflare_bypass(tab, max_wait_time=30):
    """等待Cloudflare验证完成"""
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        html_content = tab.html
        
        # 检查是否是Cloudflare验证页面
        if "请稍候" in html_content or "Please wait" in html_content or "challenge-platform" in html_content:
            logger.info("检测到Cloudflare验证页面，等待验证完成...")
            time.sleep(2)
            continue
        
        # 检查页面是否包含实际内容
        if len(html_content) > 5000:  # 实际页面通常比验证页面长得多
            logger.info("Cloudflare验证完成，页面加载成功")
            return True
        
        time.sleep(1)
    
    logger.warning(f"等待Cloudflare验证超时 ({max_wait_time}秒)")
    return False

def improved_concurrent_crawl():
    """改进版并发爬取"""
    
    # 测试数据目录
    test_data_dir = Path("test_536VOLA_data")
    test_data_dir.mkdir(exist_ok=True)
    
    # 用户数据目录
    user_data_dir = Path("chrome_user_data")
    user_data_dir.mkdir(exist_ok=True)
    
    # 测试电影代码
    movie_codes = ["HZHB-004", "VERO-085"]
    language = "ja"
    
    # 结果存储
    results = {
        'success': [],
        'failed': [],
        'total': len(movie_codes),
        'movies': {}
    }
    
    lock = Lock()
    browser = None
    
    try:
        # 创建浏览器实例
        from app.utils.drission_utils import CloudflareBypassBrowser
        from test.test_drission_movie import MovieDetailCrawler
        
        browser = CloudflareBypassBrowser(
            headless=False,  # 使用有头模式，有助于通过Cloudflare验证
            user_data_dir=str(user_data_dir),
            load_images=True,
            timeout=60
        )
        
        # 先访问主页，建立会话
        logger.info("访问主页建立会话...")
        browser.get("https://missav.ai")
        time.sleep(5)
        
        def crawl_single_movie_in_tab(movie_code):
            """在单个标签页中爬取电影信息"""
            tab = None
            try:
                if browser is None:
                    raise Exception("浏览器对象为空")
                
                # 创建新标签页
                tab = browser.page.new_tab()
                if tab is None:
                    raise Exception("无法创建新标签页")
                
                logger.info(f"[标签页] 正在处理: {movie_code}")
                
                # 构建URL并访问
                url = f"https://missav.ai/{language}/{movie_code}"
                logger.info(f"[标签页] 访问URL: {url}")
                tab.get(url)
                
                # 等待Cloudflare验证完成
                if not wait_for_cloudflare_bypass(tab, max_wait_time=30):
                    raise Exception("Cloudflare验证超时")
                
                # 额外等待页面完全加载
                time.sleep(3)
                
                # 获取HTML内容
                html_content = tab.html
                logger.info(f"[标签页] HTML内容长度: {len(html_content)}")
                
                # 保存HTML文件用于调试
                debug_html_file = test_data_dir / f"{movie_code}_{language}_improved_debug.html"
                with open(debug_html_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"[标签页] HTML已保存到: {debug_html_file}")
                
                # 检查HTML内容是否包含电影代码
                if movie_code in html_content:
                    logger.info(f"[标签页] HTML包含电影代码: {movie_code}")
                else:
                    logger.warning(f"[标签页] HTML不包含电影代码: {movie_code}")
                
                # 检查是否仍然是验证页面
                if "请稍候" in html_content or "challenge-platform" in html_content:
                    raise Exception("仍然是Cloudflare验证页面")
                
                # 解析电影信息
                crawler = MovieDetailCrawler(movie_code)
                logger.info(f"[标签页] 开始解析电影信息: {movie_code}")
                movie_info = crawler.parse_movie_page(html_content)
                
                # 详细记录解析结果
                if movie_info:
                    logger.info(f"[标签页] 解析结果类型: {type(movie_info)}")
                    if isinstance(movie_info, dict):
                        title = movie_info.get('title')
                        logger.info(f"[标签页] 标题字段: {title[:50] if title else 'Empty'}...")
                        logger.info(f"[标签页] 标题存在: {bool(title)}")
                else:
                    logger.warning(f"[标签页] 解析结果为空: {movie_info}")
                
                # 保存解析结果用于调试
                debug_json_file = test_data_dir / f"{movie_code}_{language}_improved_debug.json"
                with open(debug_json_file, 'w', encoding='utf-8') as f:
                    json.dump(movie_info, f, ensure_ascii=False, indent=2)
                logger.info(f"[标签页] 解析结果已保存到: {debug_json_file}")
                
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
        
        # 使用线程池进行并发处理（减少并发数）
        with ThreadPoolExecutor(max_workers=2) as executor:  # 减少并发数避免触发反爬虫
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
        
        # 保存成功的结果到JSONL文件
        if results['movies']:
            output_path = test_data_dir / "improved_concurrent_results.jsonl"
            with open(output_path, 'w', encoding='utf-8') as f:
                for movie_code, movie_info in results['movies'].items():
                    json_line = json.dumps(movie_info, ensure_ascii=False)
                    f.write(json_line + '\n')
            logger.info(f"成功结果已保存到: {output_path}")
        
        # 输出统计信息
        logger.info("\n=== 改进版并发爬取完成 ===")
        logger.info(f"总数: {results['total']}")
        logger.info(f"成功: {len(results['success'])}")
        logger.info(f"失败: {len(results['failed'])}")
        
        if results['success']:
            logger.info(f"成功列表: {', '.join(results['success'])}")
        if results['failed']:
            logger.info(f"失败列表: {', '.join(results['failed'])}")
        
    except Exception as e:
        logger.error(f"改进版并发爬取过程中发生错误: {str(e)}")
        import traceback
        logger.error(f"异常详情: {traceback.format_exc()}")
    finally:
        if browser is not None:
            browser.close()
            logger.info("浏览器已关闭")

if __name__ == "__main__":
    improved_concurrent_crawl()