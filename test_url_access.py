#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试URL访问"""

import requests
import time

def test_url_access():
    """测试URL访问"""
    test_urls = [
        "https://missav.ai/ja/345simm-656",
        "https://missav.ai/ja/kaad-031",
        "https://missav.ai/ja/sone-714",
        "https://missav.ai/ja/dass-645"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for url in test_urls:
        try:
            print(f"测试URL: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            print(f"  状态码: {response.status_code}")
            print(f"  响应长度: {len(response.text)}")
            
            # 检查是否包含电影标题或其他关键信息
            if 'title' in response.text.lower() or 'missav' in response.text.lower():
                print(f"  ✅ 页面包含预期内容")
            else:
                print(f"  ❌ 页面可能不包含预期内容")
                
            print("  ---")
            time.sleep(2)  # 避免请求过快
            
        except Exception as e:
            print(f"  ❌ 访问失败: {e}")
            print("  ---")

if __name__ == '__main__':
    test_url_access()