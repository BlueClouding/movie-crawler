#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 M3U8 重写功能
"""

import urllib.request
import urllib.parse
import gzip
import io

def test_m3u8_rewrite():
    """测试 M3U8 重写功能"""
    print("🧪 测试 M3U8 重写功能...")
    
    # 测试 URL
    m3u8_url = "https://vod2.bdzybf7.com/20240827/5Ej8Ej8E/2000kb/hls/index.m3u8"
    referer = "https://surrit.store/"
    
    # 构建代理 URL
    proxy_url = f"http://localhost:8001/proxy?url={urllib.parse.quote(m3u8_url)}&referer={urllib.parse.quote(referer)}"
    
    print(f"📡 代理URL: {proxy_url}")
    print(f"🎯 原始M3U8: {m3u8_url}")
    print(f"📎 Referer: {referer}")
    print()
    
    try:
        # 通过代理请求 M3U8
        print("🔄 通过代理请求 M3U8...")
        req = urllib.request.Request(proxy_url)
        
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read()
            content_type = response.headers.get('Content-Type', '')
            
            print(f"✅ 响应状态: {response.status}")
            print(f"📄 内容类型: {content_type}")
            print(f"📊 内容大小: {len(content)} 字节")
            print()
            
            # 解析内容
            try:
                # 处理 gzip 压缩
                if content[:2] == b'\x1f\x8b':
                    content = gzip.decompress(content)
                    print("🗜️ 检测到 gzip 压缩，已解压")
                
                # 解码文本
                text = content.decode('utf-8')
                lines = text.split('\n')
                
                print(f"📝 M3U8 内容分析:")
                print(f"   总行数: {len(lines)}")
                
                # 分析内容
                proxy_lines = 0
                segment_lines = 0
                
                for i, line in enumerate(lines[:20]):  # 只显示前20行
                    line = line.strip()
                    if line:
                        if line.startswith('#'):
                            print(f"   [{i+1:2d}] {line}")
                        elif line.startswith('http://localhost:8001/proxy'):
                            proxy_lines += 1
                            print(f"   [{i+1:2d}] 🔄 代理片段: {line[:80]}...")
                        elif line.startswith('http'):
                            segment_lines += 1
                            print(f"   [{i+1:2d}] 🎬 原始片段: {line}")
                        else:
                            print(f"   [{i+1:2d}] {line}")
                
                print(f"\n📊 统计信息:")
                print(f"   代理片段数: {proxy_lines}")
                print(f"   原始片段数: {segment_lines}")
                
                if proxy_lines > 0:
                    print("\n✅ M3U8 重写功能正常工作！")
                    print("🎯 视频片段已重写为通过代理服务器请求")
                    print(f"📎 所有片段将使用 Referer: {referer}")
                else:
                    print("\n⚠️ 未检测到重写的代理片段")
                    print("可能的原因:")
                    print("- M3U8 文件格式特殊")
                    print("- 重写逻辑需要调整")
                
            except Exception as e:
                print(f"❌ 内容解析失败: {e}")
                print(f"原始内容前100字节: {content[:100]}")
                
    except Exception as e:
        print(f"❌ 代理请求失败: {e}")
        print("请确保:")
        print("1. 代理服务器正在运行 (端口 8001)")
        print("2. 网络连接正常")
        print("3. M3U8 URL 有效")

if __name__ == "__main__":
    test_m3u8_rewrite()