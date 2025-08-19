#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试页面内容，查看实际获取到的HTML
"""

import urllib.request
import urllib.parse

def debug_page_content(url):
    """
    调试页面内容
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        print(f"🔍 正在访问: {url}")
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=30) as response:
            print(f"📊 响应状态: {response.status}")
            print(f"📄 响应头:")
            for key, value in response.headers.items():
                print(f"  {key}: {value}")
            
            content = response.read()
            
            # 处理 gzip 压缩
            if content[:2] == b'\x1f\x8b':
                import gzip
                content = gzip.decompress(content)
                print("🗜️ 检测到 gzip 压缩，已解压")
            
            text = content.decode('utf-8', errors='ignore')
            print(f"\n📝 页面内容 ({len(text)} 字符):")
            print("-" * 80)
            print(text)
            print("-" * 80)
            
            # 保存到文件
            with open('debug_page_content.html', 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"\n💾 页面内容已保存到: debug_page_content.html")
            
    except Exception as e:
        print(f"❌ 访问失败: {e}")

if __name__ == "__main__":
    # 测试不同的URL
    test_urls = [
        "https://surrit.store/e/8NZP3LR8",
        "https://missav.com/dm132/shmo-162",  # 示例MissAV URL
        "https://missav.com/",  # MissAV首页
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n{'='*60}")
        print(f"测试 {i}/{len(test_urls)}: {url}")
        print(f"{'='*60}")
        debug_page_content(url)
        
        if i < len(test_urls):
            input("\n按回车键继续下一个测试...")