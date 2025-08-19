#!/usr/bin/env python3
"""
测试重定向修复
专门测试857omg-004 → omg-004的重定向处理
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

def test_redirect_fix():
    """测试重定向修复"""
    
    # 测试数据
    test_movie = {
        'id': 999999,
        'code': '857omg-004',
        'url': 'https://missav.ai/ja/857omg-004'
    }
    
    logger.info(f"🧪 测试重定向修复: {test_movie['code']}")
    logger.info(f"📍 原始URL: {test_movie['url']}")
    
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
    
    try:
        logger.info(f"🎬 开始测试: {test_movie['code']}")
        
        # 访问页面
        browser.get(test_movie['url'])
        
        # 等待加载
        for check in range(5):
            time.sleep(1)
            html = browser.html
            current_url = browser.url
            
            logger.info(f"⏳ 检查 {check+1}/5: HTML长度={len(html) if html else 0}, URL={current_url}")
            
            if html and len(html) > 50000:
                logger.info(f"✅ 页面已充分加载")
                break
        
        # 获取最终状态
        html = browser.html
        current_url = browser.url
        
        logger.info(f"📊 最终状态:")
        logger.info(f"  原始URL: {test_movie['url']}")
        logger.info(f"  最终URL: {current_url}")
        logger.info(f"  HTML长度: {len(html) if html else 0}")
        
        # 检查重定向
        if current_url != test_movie['url']:
            logger.info(f"🔄 检测到重定向")
            
            # 提取重定向后的电影代码
            try:
                final_movie_code = current_url.split('/')[-1]
                logger.info(f"🔧 重定向后的代码: {test_movie['code']} → {final_movie_code}")
            except:
                logger.error(f"❌ 无法从重定向URL提取代码")
                final_movie_code = test_movie['code']
        else:
            logger.info(f"📍 没有重定向")
            final_movie_code = test_movie['code']
        
        # 检查404
        if crawler.check_404_or_not_found(html, current_url, test_movie['url'], final_movie_code):
            logger.error(f"🚫 检测到404或页面不存在")
            return False
        
        # 尝试提取信息
        if html and len(html) > 10000:
            logger.info(f"🎯 开始提取信息，使用代码: {final_movie_code}")
            
            movie_info = crawler.extract_with_parse_movie_page(
                html, 
                test_movie['id'], 
                final_movie_code,  # 使用重定向后的代码
                current_url
            )
            
            if movie_info:
                # 检查M3U8
                m3u8_links = movie_info.get('m3u8_links', [])
                has_m3u8 = len(m3u8_links) > 0
                
                logger.info(f"📊 提取结果:")
                logger.info(f"  标题: {movie_info.get('title', '未知')[:50]}...")
                logger.info(f"  M3U8数量: {len(m3u8_links)}")
                logger.info(f"  磁力数量: {len(movie_info.get('magnet_links', []))}")
                logger.info(f"  提取状态: {movie_info.get('extraction_status', '未知')}")
                
                if has_m3u8:
                    logger.info(f"✅ 成功提取M3U8，修复成功！")
                    return True
                else:
                    logger.warning(f"⚠️ 未提取到M3U8，但有其他信息")
                    return True
            else:
                logger.error(f"❌ 信息提取失败")
                return False
        else:
            logger.error(f"❌ 页面内容不足")
            return False
    
    finally:
        browser.quit()
        logger.info("🔒 浏览器已关闭")

if __name__ == "__main__":
    logger.info("🧪 开始测试重定向修复")
    logger.info("🎯 测试857omg-004 → omg-004重定向处理")
    
    success = test_redirect_fix()
    
    if success:
        logger.info("🎉 重定向修复测试成功！")
    else:
        logger.error("💀 重定向修复测试失败！")
