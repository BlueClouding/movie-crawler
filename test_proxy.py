#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试代理服务器连接
"""

import requests
import urllib.parse

def test_proxy_connection():
    """测试代理服务器连接"""
    proxy_base = 'http://localhost:8001'
    
    print("🔍 测试代理服务器连接...")
    
    # 测试1: 检查代理服务器是否运行
    try:
        response = requests.get(f"{proxy_base}/", timeout=5)
        print(f"✅ 代理服务器首页访问成功 (状态码: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"❌ 代理服务器首页访问失败: {e}")
        return False
    
    # 测试2: 测试代理功能
    test_url = "https://faf8b60b.freshvibe64.store/blah3/XEn0ezAekFvTgxX3A7ZKZY_9hxR3jYNOCqeLthCPgxdQyIZi/video.m3u8"
    referer = "https://surrit.store/"
    
    proxy_url = f"{proxy_base}/proxy?url={urllib.parse.quote(test_url)}&referer={urllib.parse.quote(referer)}"
    
    print(f"🔄 测试代理URL: {proxy_url}")
    
    try:
        response = requests.get(proxy_url, timeout=10)
        print(f"✅ 代理请求成功 (状态码: {response.status_code})")
        print(f"📊 响应大小: {len(response.content)} 字节")
        
        # 检查响应内容
        if response.content:
            content_preview = response.text[:200] if response.text else "[二进制内容]"
            print(f"📄 内容预览: {content_preview}...")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 代理请求失败: {e}")
        return False

def test_direct_connection():
    """测试直接连接（用于对比）"""
    test_url = "https://faf8b60b.freshvibe64.store/blah3/XEn0ezAekFvTgxX3A7ZKZY_9hxR3jYNOCqeLthCPgxdQyIZi/video.m3u8"
    referer = "https://surrit.store/"
    
    print("\n🔍 测试直接连接（用于对比）...")
    
    headers = {
        'Referer': referer,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(test_url, headers=headers, timeout=10)
        print(f"✅ 直接请求成功 (状态码: {response.status_code})")
        print(f"📊 响应大小: {len(response.content)} 字节")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ 直接请求失败: {e}")
        return False

if __name__ == "__main__":
    print("🧪 开始测试代理服务器...\n")
    
    proxy_ok = test_proxy_connection()
    direct_ok = test_direct_connection()
    
    print("\n" + "="*50)
    print("📋 测试结果总结:")
    print(f"🔄 代理连接: {'✅ 正常' if proxy_ok else '❌ 失败'}")
    print(f"🔗 直接连接: {'✅ 正常' if direct_ok else '❌ 失败'}")
    
    if proxy_ok:
        print("\n💡 建议: 代理服务器工作正常，请在播放器中确保勾选'使用代理服务器'选项")
    else:
        print("\n⚠️  建议: 代理服务器连接有问题，请检查服务器是否正常运行")
    
    print("="*50)