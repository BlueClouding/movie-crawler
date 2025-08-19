#!/usr/bin/env python3
"""
测试被误判为404的电影
检查为什么这些实际存在的电影被判断为404
"""

import json
import time
import random
from pathlib import Path
from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions

def test_404_movies():
    """测试被误判为404的电影"""
    
    # 你提到的实际存在但被误判为404的电影
    test_movies = [
        "aczd-222",
        "sone-714", 
        "dass-645",
        "dass-599",
        "sone-717",
        "sone-711"
    ]
    
    logger.info(f"🧪 测试 {len(test_movies)} 部被误判为404的电影")
    
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
            
            # 详细分析页面内容
            html = browser.html
            current_url = browser.url
            
            if html:
                html_lower = html.lower()
                
                # 检查各种指标
                analysis = {
                    'movie_code': movie_code,
                    'original_url': url,
                    'final_url': current_url,
                    'html_length': len(html),
                    'redirected': current_url != url,
                }
                
                # 检查404指标
                has_404_text = any(indicator in html_lower for indicator in [
                    '404', 'not found', 'page not found', 'ページが見つかりません',
                    'お探しのページは見つかりませんでした', 'does not exist', 'error 404'
                ])
                analysis['has_404_text'] = has_404_text
                
                # 检查是否重定向到主页
                is_homepage = 'missav.ai' in current_url and current_url.count('/') <= 3
                analysis['is_homepage'] = is_homepage
                
                # 检查电影相关内容
                has_video_content = any(keyword in html_lower for keyword in [
                    'video', 'movie', 'player', 'download', 'm3u8', 'magnet'
                ])
                analysis['has_video_content'] = has_video_content
                
                # 检查基本网页内容
                has_basic_content = any(keyword in html_lower for keyword in [
                    'missav', 'title', 'content', 'body', 'main'
                ])
                analysis['has_basic_content'] = has_basic_content
                
                # 检查是否包含电影代码
                has_movie_code = movie_code.lower() in html_lower
                analysis['has_movie_code'] = has_movie_code
                
                # 检查页面标题
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html, 'html.parser')
                    title_tag = soup.find('title')
                    page_title = title_tag.get_text().strip() if title_tag else "无标题"
                    analysis['page_title'] = page_title
                    
                    h1_tag = soup.find('h1')
                    h1_text = h1_tag.get_text().strip() if h1_tag else "无H1"
                    analysis['h1_text'] = h1_text
                except:
                    analysis['page_title'] = "解析失败"
                    analysis['h1_text'] = "解析失败"
                
                # 判断是否应该被认为是404
                should_be_404 = (has_404_text or is_homepage or 
                                len(html) < 1000 or not has_basic_content)
                analysis['should_be_404'] = should_be_404
                
                # 记录结果
                results.append(analysis)
                
                # 输出分析结果
                logger.info(f"📊 {movie_code} 分析结果:")
                logger.info(f"  HTML长度: {analysis['html_length']}")
                logger.info(f"  重定向: {analysis['redirected']}")
                logger.info(f"  404文本: {analysis['has_404_text']}")
                logger.info(f"  主页重定向: {analysis['is_homepage']}")
                logger.info(f"  视频内容: {analysis['has_video_content']}")
                logger.info(f"  基本内容: {analysis['has_basic_content']}")
                logger.info(f"  包含代码: {analysis['has_movie_code']}")
                logger.info(f"  页面标题: {analysis['page_title'][:50]}...")
                logger.info(f"  H1文本: {analysis['h1_text'][:50]}...")
                logger.info(f"  应为404: {analysis['should_be_404']}")
                
                if not should_be_404:
                    logger.info(f"✅ {movie_code}: 确实存在，之前误判为404")
                else:
                    logger.info(f"🚫 {movie_code}: 确实是404或无效页面")
            else:
                logger.error(f"❌ {movie_code}: 无法获取页面内容")
                results.append({
                    'movie_code': movie_code,
                    'original_url': url,
                    'final_url': current_url,
                    'error': 'no_html_content'
                })
            
            # 间隔
            if i < len(test_movies):
                time.sleep(random.uniform(3, 6))
    
    finally:
        browser.quit()
        logger.info("🔒 浏览器已关闭")
    
    # 保存详细结果
    output_file = Path("404_analysis_results.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(f"💾 详细分析结果已保存到: {output_file}")
    
    # 统计结果
    valid_movies = [r for r in results if not r.get('should_be_404', True)]
    invalid_movies = [r for r in results if r.get('should_be_404', True)]
    
    logger.info(f"\n{'='*50}")
    logger.info("📊 404误判分析结果")
    logger.info(f"总数: {len(test_movies)}")
    logger.info(f"确实存在（被误判）: {len(valid_movies)}")
    logger.info(f"确实是404: {len(invalid_movies)}")
    
    if valid_movies:
        logger.info("\n✅ 确实存在的电影:")
        for movie in valid_movies:
            logger.info(f"  - {movie['movie_code']}: {movie.get('page_title', '未知')[:50]}...")
    
    if invalid_movies:
        logger.info("\n🚫 确实是404的电影:")
        for movie in invalid_movies:
            logger.info(f"  - {movie['movie_code']}: {movie.get('error', '404页面')}")
    
    return results

if __name__ == "__main__":
    logger.info("🧪 开始测试被误判为404的电影")
    logger.info("🎯 检查为什么实际存在的电影被判断为404")
    
    results = test_404_movies()
    
    logger.info("\n🎉 测试完成！")
    logger.info("💡 根据结果可以调整404检测逻辑")
