#!/usr/bin/env python3
"""
测试URL修正功能
专门测试uncensored-leaked -> uncensored-leak的修正
"""

import json
import time
import random
import sys
from pathlib import Path
from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 导入MovieDetailCrawler
sys.path.append(str(Path(__file__).parent / "src"))
try:
    from test.test_drission_movie import MovieDetailCrawler
    HAS_MOVIE_CRAWLER = True
    logger.info("✅ 成功导入MovieDetailCrawler")
except ImportError as e:
    HAS_MOVIE_CRAWLER = False
    logger.warning(f"❌ 无法导入MovieDetailCrawler: {e}")

def test_url_correction():
    """测试URL修正功能"""
    
    # 数据库连接
    db_url = "postgresql://postgres:123456@localhost:5432/movie_crawler"
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    
    # 获取uncensored-leaked电影
    session = Session()
    try:
        result = session.execute(text("""
            SELECT id, link 
            FROM movies 
            WHERE link LIKE '%uncensored-leaked%' 
            LIMIT 3
        """))
        raw_movies = [(row.id, row.link) for row in result]
    finally:
        session.close()
    
    logger.info(f"📊 找到 {len(raw_movies)} 部uncensored-leaked电影")
    
    # 测试URL修正逻辑
    corrected_movies = []
    for movie_id, link in raw_movies:
        if link.startswith('dm3/v/') or link.startswith('dm4/v/'):
            movie_code = link.split('/')[-1]
            # 修正uncensored-leaked为uncensored-leak
            if movie_code.endswith('-uncensored-leaked'):
                original_code = movie_code
                movie_code = movie_code.replace('-uncensored-leaked', '-uncensored-leak')
                logger.info(f"🔧 修正URL: ID={movie_id}, {original_code} → {movie_code}")
            full_url = f"https://missav.ai/ja/{movie_code}"
            corrected_movies.append((movie_id, full_url, movie_code))
    
    # 创建浏览器测试
    logger.info("🚀 创建浏览器测试修正后的URL")
    
    options = ChromiumOptions()
    options.headless(False)
    options.set_argument('--window-size=1920,1080')
    
    browser = ChromiumPage(addr_or_opts=options)
    
    # 建立会话
    browser.get("https://missav.ai/")
    time.sleep(2)
    
    results = []
    
    try:
        for i, (movie_id, movie_url, movie_code) in enumerate(corrected_movies, 1):
            logger.info(f"\n🎬 测试 {i}/{len(corrected_movies)}: ID={movie_id}, {movie_code}")
            logger.info(f"📍 URL: {movie_url}")
            
            # 访问页面
            browser.get(movie_url)
            
            # 等待加载
            for check in range(3):
                time.sleep(1)
                html = browser.html
                current_url = browser.url
                
                if html and len(html) > 50000:
                    logger.info(f"✅ 页面已加载 ({len(html)} 字符)")
                    if current_url != movie_url:
                        logger.info(f"🔄 最终URL: {current_url}")
                    break
            
            # 检查页面内容
            html = browser.html
            if html and len(html) > 10000:
                # 简单检查是否包含电影相关内容
                html_lower = html.lower()
                if any(keyword in html_lower for keyword in ['video', 'movie', 'player', 'download', 'm3u8']):
                    logger.info(f"✅ {movie_code}: URL修正成功，页面包含电影内容")
                    
                    # 尝试提取信息
                    if HAS_MOVIE_CRAWLER:
                        try:
                            crawler = MovieDetailCrawler(movie_code)
                            result = crawler.parse_movie_page(html)
                            if result and result.get('title'):
                                logger.info(f"🎬 成功提取标题: {result['title'][:50]}...")
                                results.append({
                                    'id': movie_id,
                                    'code': movie_code,
                                    'url': movie_url,
                                    'final_url': current_url,
                                    'title': result['title'],
                                    'status': 'success'
                                })
                            else:
                                logger.warning(f"⚠️ {movie_code}: 页面加载成功但信息提取失败")
                                results.append({
                                    'id': movie_id,
                                    'code': movie_code,
                                    'url': movie_url,
                                    'final_url': current_url,
                                    'status': 'extraction_failed'
                                })
                        except Exception as e:
                            logger.error(f"❌ {movie_code}: 提取过程出错: {e}")
                            results.append({
                                'id': movie_id,
                                'code': movie_code,
                                'url': movie_url,
                                'final_url': current_url,
                                'status': 'error',
                                'error': str(e)
                            })
                    else:
                        logger.info(f"✅ {movie_code}: URL修正成功（未测试信息提取）")
                        results.append({
                            'id': movie_id,
                            'code': movie_code,
                            'url': movie_url,
                            'final_url': current_url,
                            'status': 'page_loaded'
                        })
                else:
                    logger.warning(f"🚫 {movie_code}: 页面不包含电影相关内容，可能是404")
                    results.append({
                        'id': movie_id,
                        'code': movie_code,
                        'url': movie_url,
                        'final_url': current_url,
                        'status': '404'
                    })
            else:
                logger.error(f"❌ {movie_code}: 页面内容不足")
                results.append({
                    'id': movie_id,
                    'code': movie_code,
                    'url': movie_url,
                    'status': 'page_load_failed'
                })
            
            # 间隔
            if i < len(corrected_movies):
                time.sleep(random.uniform(3, 6))
    
    finally:
        browser.quit()
        logger.info("🔒 浏览器已关闭")
    
    # 输出结果
    logger.info(f"\n{'='*50}")
    logger.info("📊 URL修正测试结果")
    logger.info(f"总数: {len(corrected_movies)}")
    logger.info(f"成功: {len([r for r in results if r['status'] == 'success'])}")
    logger.info(f"页面加载成功: {len([r for r in results if r['status'] in ['success', 'page_loaded']])}")
    logger.info(f"404: {len([r for r in results if r['status'] == '404'])}")
    
    # 保存结果
    output_file = Path("url_correction_test_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(f"💾 结果已保存到: {output_file}")
    
    return results

if __name__ == "__main__":
    logger.info("🧪 开始测试URL修正功能")
    logger.info("🎯 测试uncensored-leaked → uncensored-leak修正")
    
    results = test_url_correction()
    
    logger.info("\n🎉 测试完成！")
    for result in results:
        status_emoji = {
            'success': '✅',
            'page_loaded': '📄',
            '404': '🚫',
            'extraction_failed': '⚠️',
            'error': '❌',
            'page_load_failed': '💀'
        }.get(result['status'], '❓')
        
        logger.info(f"{status_emoji} {result['code']}: {result['status']}")
