#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 curl 请求与代理服务器的对比
"""

import subprocess
import urllib.request
import urllib.parse
import json

def test_curl_request(url, referer=None):
    """使用 curl 测试请求"""
    print("=== CURL 测试 ===")
    
    cmd = ['curl', '-s', '-I']  # -s 静默模式, -I 只获取头信息
    
    # 添加 User-Agent
    cmd.extend(['-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'])
    
    # 添加 Referer
    if referer:
        cmd.extend(['-H', f'Referer: {referer}'])
        print(f"📎 设置Referer: {referer}")
    
    cmd.append(url)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        print(f"返回码: {result.returncode}")
        print(f"响应头:\n{result.stdout}")
        
        if result.stderr:
            print(f"错误信息: {result.stderr}")
            
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ CURL 请求超时")
        return False
    except Exception as e:
        print(f"❌ CURL 请求失败: {e}")
        return False

def test_proxy_request(url, referer=None):
    """测试代理服务器请求"""
    print("\n=== 代理服务器测试 ===")
    
    # 构建代理URL
    proxy_base = 'http://localhost:8001/proxy'
    params = {'url': url}
    if referer:
        params['referer'] = referer
        print(f"📎 设置Referer: {referer}")
    
    proxy_url = f"{proxy_base}?{urllib.parse.urlencode(params)}"
    print(f"代理URL: {proxy_url}")
    
    try:
        req = urllib.request.Request(proxy_url)
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read()
            print(f"状态码: {response.status}")
            print(f"内容类型: {response.headers.get('Content-Type')}")
            print(f"内容长度: {len(content)} 字节")
            
            # 如果是文本内容，显示前200个字符
            if len(content) < 1000:
                try:
                    text_content = content.decode('utf-8')
                    print(f"内容预览: {text_content[:200]}...")
                except:
                    print("内容预览: [二进制内容]")
            
            return True
    except Exception as e:
        print(f"❌ 代理请求失败: {e}")
        return False

def test_direct_python_request(url, referer=None):
    """使用 Python 直接请求测试"""
    print("\n=== Python 直接请求测试 ===")
    
    try:
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        if referer:
            req.add_header('Referer', referer)
            print(f"📎 设置Referer: {referer}")
        
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read()
            print(f"状态码: {response.status}")
            print(f"内容类型: {response.headers.get('Content-Type')}")
            print(f"内容长度: {len(content)} 字节")
            
            # 如果是文本内容，显示前200个字符
            if len(content) < 1000:
                try:
                    text_content = content.decode('utf-8')
                    print(f"内容预览: {text_content[:200]}...")
                except:
                    print("内容预览: [二进制内容]")
            
            return True
    except Exception as e:
        print(f"❌ Python 直接请求失败: {e}")
        return False

def main():
    # 测试URL（请替换为实际的M3U8 URL）
    test_url = input("请输入要测试的 M3U8 URL: ").strip()
    if not test_url:
        print("❌ 请提供有效的 URL")
        return
    
    test_referer = input("请输入 Referer URL (可选，直接回车跳过): ").strip()
    if not test_referer:
        test_referer = None
    
    print(f"\n🔍 测试URL: {test_url}")
    if test_referer:
        print(f"🔍 Referer: {test_referer}")
    
    print("\n" + "="*50)
    
    # 执行测试
    curl_success = test_curl_request(test_url, test_referer)
    proxy_success = test_proxy_request(test_url, test_referer)
    direct_success = test_direct_python_request(test_url, test_referer)
    
    print("\n" + "="*50)
    print("📊 测试结果汇总:")
    print(f"CURL 请求: {'✅ 成功' if curl_success else '❌ 失败'}")
    print(f"代理服务器: {'✅ 成功' if proxy_success else '❌ 失败'}")
    print(f"Python 直接请求: {'✅ 成功' if direct_success else '❌ 失败'}")
    
    if curl_success and not proxy_success:
        print("\n💡 建议: CURL 成功但代理失败，可能是代理服务器配置问题")
    elif not curl_success and not proxy_success and not direct_success:
        print("\n💡 建议: 所有方式都失败，可能是 URL 或 Referer 问题")
    elif curl_success and proxy_success:
        print("\n💡 建议: CURL 和代理都成功，浏览器问题可能是 CORS 或其他安全限制")

if __name__ == "__main__":
    main()