#!/usr/bin/env python3
"""
测试uncensored-leak电影的提取问题
专门检查为什么这类电影提取失败
"""

import json
import time
import sys
from pathlib import Path
from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions

# 导入爬虫
sys.path.append('.')
from simple_database_crawler import SimpleDatabaseCrawler

def test_uncensored_leak_movies():
    """测试uncensored-leak电影提取"""
    
    # 测试数据 - 你提到的有问题的电影
    test_movies = [
        "gtj-061-uncensored-leak",
        "rbk-016-uncensored-leak",
        "gvg-340-uncensored-leak",  # 之前失败的
        "hmn-021-uncensored-leak",  # 之前成功的，作为对比
    ]
    
    logger.info(f"🧪 测试 {len(test_movies)} 部uncensored-leak电影")
    
    # 创建爬虫实例
    crawler = SimpleDatabaseCrawler()
    
    # 创建浏览器
    options = ChromiumOptions()
    options.headless(False)
    options.set_argument('--window-size=1920,1080')
    
    browser = ChromiumPage(addr_or_opts=options)
    
    # 建立会话
    browser.get("https://missav.ai/")
    time.sleep(2)
    
    results = []
    
    try:
        for i, movie_code in enumerate(test_movies, 1):
            logger.info(f"\n🎬 测试 {i}/{len(test_movies)}: {movie_code}")
            
            url = f"https://missav.ai/ja/{movie_code}"
            logger.info(f"📍 URL: {url}")
            
            # 访问页面
            browser.get(url)
            
            # 等待加载
            for check in range(5):
                time.sleep(1)
                html = browser.html
                current_url = browser.url
                
                logger.info(f"⏳ 检查 {check+1}/5: HTML长度={len(html) if html else 0}, URL={current_url}")
                
                if html and len(html) > 50000:
                    logger.info(f"✅ 页面已充分加载")
                    break
                elif check == 4:
                    logger.warning(f"⚠️ 页面加载可能不完整")
            
            # 获取最终状态
            html = browser.html
            current_url = browser.url
            
            if html:
                # 检查重定向
                final_movie_code = movie_code
                if current_url != url:
                    try:
                        final_movie_code = current_url.split('/')[-1]
                        logger.info(f"🔄 重定向: {movie_code} → {final_movie_code}")
                    except:
                        logger.warning(f"⚠️ 无法从重定向URL提取代码")
                
                # 检查404
                is_404 = crawler.check_404_or_not_found(html, current_url, url, final_movie_code)
                logger.info(f"🔍 404检查结果: {is_404}")
                
                if not is_404:
                    # 尝试提取信息
                    logger.info(f"🎯 开始提取信息，使用代码: {final_movie_code}")
                    
                    movie_info = crawler.extract_with_parse_movie_page(
                        html, 
                        999990 + i, 
                        final_movie_code,
                        current_url
                    )
                    
                    if movie_info:
                        # 分析提取结果
                        m3u8_links = movie_info.get('m3u8_links', [])
                        m3u8_urls = movie_info.get('m3u8_urls', [])
                        magnet_links = movie_info.get('magnet_links', [])
                        title = movie_info.get('title', '未知')
                        extraction_status = movie_info.get('extraction_status', '未知')
                        
                        logger.info(f"📊 提取结果分析:")
                        logger.info(f"  标题: {title[:50]}...")
                        logger.info(f"  M3U8 links: {len(m3u8_links)}")
                        logger.info(f"  M3U8 urls: {len(m3u8_urls)}")
                        logger.info(f"  磁力链接: {len(magnet_links)}")
                        logger.info(f"  提取状态: {extraction_status}")
                        
                        # 检查是否有任何M3U8
                        total_m3u8 = len(m3u8_links) + len(m3u8_urls)
                        
                        if total_m3u8 > 0:
                            logger.info(f"✅ {movie_code}: 成功提取M3U8 ({total_m3u8}个)")
                            status = "success"
                        elif title and title != "未知" and title != "uncensored-leak":
                            logger.info(f"⚠️ {movie_code}: 有标题但无M3U8")
                            status = "partial_success"
                        else:
                            logger.warning(f"🚫 {movie_code}: 提取失败")
                            status = "extraction_failed"
                        
                        results.append({
                            'movie_code': movie_code,
                            'final_code': final_movie_code,
                            'url': url,
                            'final_url': current_url,
                            'title': title,
                            'm3u8_count': total_m3u8,
                            'magnet_count': len(magnet_links),
                            'extraction_status': extraction_status,
                            'status': status,
                            'html_length': len(html)
                        })
                        
                        # 如果提取失败，进行详细分析
                        if status == "extraction_failed":
                            logger.info(f"🔍 详细分析 {movie_code}:")
                            
                            # 检查HTML中是否包含M3U8
                            import re
                            m3u8_in_html = re.findall(r'https?://[^"\'>\s]+\.m3u8[^"\'>\s]*', html)
                            logger.info(f"  HTML中的M3U8: {len(m3u8_in_html)}")
                            
                            # 检查是否包含magnet
                            magnet_in_html = re.findall(r'magnet:\?[^"\'>\s]+', html)
                            logger.info(f"  HTML中的磁力: {len(magnet_in_html)}")
                            
                            # 检查是否包含电影代码
                            code_in_html = movie_code.lower() in html.lower()
                            logger.info(f"  包含电影代码: {code_in_html}")
                            
                            # 检查页面类型
                            if "首页" in html or "homepage" in html.lower():
                                logger.info(f"  页面类型: 可能是首页")
                            elif "404" in html.lower():
                                logger.info(f"  页面类型: 可能是404页面")
                            else:
                                logger.info(f"  页面类型: 正常电影页面")
                    else:
                        logger.error(f"❌ {movie_code}: 提取方法返回None")
                        results.append({
                            'movie_code': movie_code,
                            'final_code': final_movie_code,
                            'url': url,
                            'final_url': current_url,
                            'status': 'extraction_method_failed',
                            'html_length': len(html)
                        })
                else:
                    logger.error(f"🚫 {movie_code}: 检测为404页面")
                    results.append({
                        'movie_code': movie_code,
                        'url': url,
                        'final_url': current_url,
                        'status': '404_detected',
                        'html_length': len(html)
                    })
            else:
                logger.error(f"❌ {movie_code}: 无法获取页面内容")
                results.append({
                    'movie_code': movie_code,
                    'url': url,
                    'status': 'no_html_content'
                })
            
            # 间隔
            if i < len(test_movies):
                time.sleep(3)
    
    finally:
        browser.quit()
        logger.info("🔒 浏览器已关闭")
    
    # 保存详细结果
    output_file = Path("uncensored_leak_test_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(f"💾 详细分析结果已保存到: {output_file}")
    
    # 统计结果
    success_count = len([r for r in results if r.get('status') == 'success'])
    partial_count = len([r for r in results if r.get('status') == 'partial_success'])
    failed_count = len([r for r in results if r.get('status') in ['extraction_failed', 'extraction_method_failed']])
    not_found_count = len([r for r in results if r.get('status') == '404_detected'])
    
    logger.info(f"\n{'='*50}")
    logger.info("📊 uncensored-leak电影测试结果")
    logger.info(f"总数: {len(test_movies)}")
    logger.info(f"✅ 完全成功: {success_count}")
    logger.info(f"⚠️ 部分成功: {partial_count}")
    logger.info(f"💀 提取失败: {failed_count}")
    logger.info(f"🚫 404不存在: {not_found_count}")
    
    # 详细结果
    for result in results:
        status_emoji = {
            'success': '✅',
            'partial_success': '⚠️',
            'extraction_failed': '💀',
            'extraction_method_failed': '❌',
            '404_detected': '🚫',
            'no_html_content': '💥'
        }.get(result.get('status'), '❓')
        
        m3u8_info = f" (M3U8: {result.get('m3u8_count', 0)})" if result.get('m3u8_count') is not None else ""
        logger.info(f"{status_emoji} {result['movie_code']}: {result.get('status', 'unknown')}{m3u8_info}")
    
    return results

if __name__ == "__main__":
    logger.info("🧪 开始测试uncensored-leak电影提取问题")
    logger.info("🎯 检查为什么这类电影在浏览器有数据但提取失败")
    
    results = test_uncensored_leak_movies()
    
    logger.info("\n🎉 测试完成！")
    logger.info("💡 根据结果可以分析uncensored-leak电影的提取问题")
