#!/usr/bin/env python3
"""
VSCode远程开发调试辅助脚本
"""

import os
import sys
import time
from pathlib import Path
from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions

def debug_single_movie(movie_code="fc2-ppv-4600833", headless=False):
    """调试单个电影"""
    
    logger.info(f"🎬 开始调试电影: {movie_code}")
    
    # 配置浏览器
    options = ChromiumOptions()
    if headless:
        options.headless(True)
    
    # Linux服务器配置
    options.set_argument('--no-sandbox')
    options.set_argument('--disable-dev-shm-usage')
    options.set_argument('--disable-gpu')
    options.set_argument('--window-size=1920,1080')
    
    try:
        browser = ChromiumPage(addr_or_opts=options)
        logger.info("✅ 浏览器创建成功")
        
        # 构建URL
        url = f"https://missav.ai/ja/{movie_code}"
        logger.info(f"📍 访问URL: {url}")
        
        # 访问页面
        browser.get(url)
        time.sleep(3)
        
        # 获取页面信息
        html = browser.html
        current_url = browser.url
        
        logger.info(f"📊 页面信息:")
        logger.info(f"  当前URL: {current_url}")
        logger.info(f"  HTML长度: {len(html) if html else 0}")
        logger.info(f"  是否重定向: {current_url != url}")
        
        if html:
            # 检查页面内容
            import re
            from bs4 import BeautifulSoup
            
            # 提取标题
            soup = BeautifulSoup(html, 'html.parser')
            h1_tag = soup.find('h1')
            title = h1_tag.get_text().strip() if h1_tag else "未找到标题"
            logger.info(f"  标题: {title}")
            
            # 检查M3U8
            m3u8_links = re.findall(r'https?://[^"\'>\s]+\.m3u8[^"\'>\s]*', html)
            logger.info(f"  M3U8链接数: {len(m3u8_links)}")
            
            # 检查磁力链接
            magnet_links = re.findall(r'magnet:\?[^"\'>\s]+', html)
            logger.info(f"  磁力链接数: {len(magnet_links)}")
            
            # 保存HTML用于分析
            debug_file = f"debug_{movie_code}.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(html)
            logger.info(f"💾 HTML已保存到: {debug_file}")
            
            return {
                'title': title,
                'm3u8_count': len(m3u8_links),
                'magnet_count': len(magnet_links),
                'html_length': len(html),
                'redirected': current_url != url,
                'final_url': current_url
            }
        
        else:
            logger.error("❌ 无法获取页面内容")
            return None
        
    except Exception as e:
        logger.error(f"❌ 调试过程出错: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        if 'browser' in locals():
            browser.quit()
            logger.info("🔒 浏览器已关闭")

if __name__ == "__main__":
    # 设置断点进行调试
    result = debug_single_movie("fc2-ppv-4600833", headless=True)
    print(f"调试结果: {result}")
