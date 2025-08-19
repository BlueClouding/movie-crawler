#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M3U8 视频加载问题诊断工具
"""

import urllib.request
import urllib.parse
import re
import gzip
import io
from urllib.parse import urljoin, urlparse

def analyze_m3u8_content(url, referer=None):
    """分析 M3U8 文件内容"""
    print(f"🔍 分析 M3U8: {url}")
    
    try:
        # 通过代理获取 M3U8 内容
        proxy_url = f"http://localhost:8001/proxy?url={urllib.parse.quote(url)}"
        if referer:
            proxy_url += f"&referer={urllib.parse.quote(referer)}"
            print(f"📎 使用 Referer: {referer}")
        
        req = urllib.request.Request(proxy_url)
        with urllib.request.urlopen(req, timeout=30) as response:
            raw_content = response.read()
            
            # 尝试解压 gzip 内容
            try:
                if raw_content.startswith(b'\x1f\x8b'):  # gzip magic number
                    content = gzip.decompress(raw_content).decode('utf-8')
                    print(f"✅ M3U8 内容获取成功 (gzip压缩, {len(content)} 字符)")
                else:
                    content = raw_content.decode('utf-8')
                    print(f"✅ M3U8 内容获取成功 ({len(content)} 字符)")
            except UnicodeDecodeError:
                # 如果仍然无法解码，显示原始字节
                print(f"❌ 内容解码失败，原始内容 ({len(raw_content)} 字节):")
                print(f"前20字节: {raw_content[:20]}")
                print(f"十六进制: {raw_content[:20].hex()}")
                return
            
            print("\n📄 M3U8 内容:")
            print("-" * 50)
            print(content)
            print("-" * 50)
            
            # 分析 M3U8 类型
            if '#EXT-X-STREAM-INF' in content:
                print("\n📊 检测到: Master Playlist (多码率)")
                analyze_master_playlist(content, url, referer)
            elif '#EXTINF' in content:
                print("\n📊 检测到: Media Playlist (视频片段)")
                analyze_media_playlist(content, url, referer)
            else:
                print("\n❌ 未识别的 M3U8 格式")
                
    except Exception as e:
        print(f"❌ M3U8 分析失败: {e}")

def analyze_master_playlist(content, base_url, referer):
    """分析主播放列表"""
    lines = content.strip().split('\n')
    playlists = []
    
    for i, line in enumerate(lines):
        if line.startswith('#EXT-X-STREAM-INF'):
            # 解析码率信息
            bandwidth_match = re.search(r'BANDWIDTH=(\d+)', line)
            resolution_match = re.search(r'RESOLUTION=(\d+x\d+)', line)
            
            bandwidth = bandwidth_match.group(1) if bandwidth_match else 'Unknown'
            resolution = resolution_match.group(1) if resolution_match else 'Unknown'
            
            # 获取下一行的 URL
            if i + 1 < len(lines):
                playlist_url = lines[i + 1].strip()
                if not playlist_url.startswith('http'):
                    playlist_url = urljoin(base_url, playlist_url)
                
                playlists.append({
                    'url': playlist_url,
                    'bandwidth': bandwidth,
                    'resolution': resolution
                })
    
    print(f"\n📋 发现 {len(playlists)} 个播放列表:")
    for i, playlist in enumerate(playlists):
        print(f"  {i+1}. 码率: {playlist['bandwidth']} bps, 分辨率: {playlist['resolution']}")
        print(f"     URL: {playlist['url']}")
    
    # 测试第一个播放列表
    if playlists:
        print(f"\n🔍 测试第一个播放列表...")
        analyze_m3u8_content(playlists[0]['url'], referer)

def analyze_media_playlist(content, base_url, referer):
    """分析媒体播放列表"""
    lines = content.strip().split('\n')
    segments = []
    
    for i, line in enumerate(lines):
        if line.startswith('#EXTINF'):
            # 获取时长
            duration_match = re.search(r'#EXTINF:([\d.]+)', line)
            duration = duration_match.group(1) if duration_match else 'Unknown'
            
            # 获取下一行的片段 URL
            if i + 1 < len(lines):
                segment_url = lines[i + 1].strip()
                if not segment_url.startswith('http'):
                    segment_url = urljoin(base_url, segment_url)
                
                segments.append({
                    'url': segment_url,
                    'duration': duration
                })
    
    print(f"\n📹 发现 {len(segments)} 个视频片段")
    if segments:
        total_duration = sum(float(seg['duration']) for seg in segments if seg['duration'] != 'Unknown')
        print(f"📊 总时长: {total_duration:.1f} 秒")
        
        # 测试前3个片段的可访问性
        print(f"\n🔍 测试前3个片段的可访问性...")
        for i, segment in enumerate(segments[:3]):
            test_segment_access(segment['url'], referer, i+1)

def test_segment_access(segment_url, referer, index):
    """测试视频片段的可访问性"""
    try:
        proxy_url = f"http://localhost:8001/proxy?url={urllib.parse.quote(segment_url)}"
        if referer:
            proxy_url += f"&referer={urllib.parse.quote(referer)}"
        
        req = urllib.request.Request(proxy_url)
        req.get_method = lambda: 'HEAD'  # 只获取头信息
        
        with urllib.request.urlopen(req, timeout=10) as response:
            content_length = response.headers.get('Content-Length', 'Unknown')
            content_type = response.headers.get('Content-Type', 'Unknown')
            print(f"  ✅ 片段 {index}: {content_length} 字节, 类型: {content_type}")
            
    except Exception as e:
        print(f"  ❌ 片段 {index}: 访问失败 - {e}")

def main():
    print("🔧 M3U8 视频加载问题诊断工具")
    print("=" * 50)
    
    # 使用测试中的 URL
    test_url = "https://faf8b60b.freshvibe64.store/blah3/XEn0ezAekFvTgxX3A7ZKZY_9hxR3jYNOCqeLthCPgxdQyIZi/video.m3u8"
    test_referer = "https://surrit.store/"
    
    print(f"📋 测试 URL: {test_url}")
    print(f"📋 Referer: {test_referer}")
    print()
    
    analyze_m3u8_content(test_url, test_referer)
    
    print("\n" + "=" * 50)
    print("💡 诊断建议:")
    print("1. 检查 M3U8 文件格式是否正确")
    print("2. 验证视频片段 URL 是否可访问")
    print("3. 确认 Referer 设置是否正确")
    print("4. 检查浏览器控制台的详细错误信息")

if __name__ == "__main__":
    main()