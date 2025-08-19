#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 MissAV 影片 M3U8 爬取功能
独立测试脚本，避免复杂的项目依赖
"""

import re
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any

class SimpleMissAVCrawler:
    """
    简化的 MissAV 爬虫，专门用于测试 M3U8 提取功能
    """
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def get_page_content(self, url: str) -> Optional[str]:
        """
        获取页面内容
        """
        try:
            print(f"🔍 正在访问: {url}")
            req = urllib.request.Request(url, headers=self.headers)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read()
                
                # 处理 gzip 压缩
                if content[:2] == b'\x1f\x8b':
                    import gzip
                    content = gzip.decompress(content)
                
                return content.decode('utf-8', errors='ignore')
                
        except Exception as e:
            print(f"❌ 页面访问失败: {e}")
            return None
    
    def extract_m3u8_info(self, html: str) -> Dict[str, Any]:
        """
        从HTML中提取M3U8加密信息
        """
        result = {"encrypted_code": None, "dictionary": None}
        soup = BeautifulSoup(html, "html.parser")
        scripts = soup.select("script")

        # 正则表达式模式，匹配加密的JavaScript代码
        pattern = re.compile(
            r"eval\(function\(p,a,c,k,e,d\)\{(.+?)\}\('(.+?)',([0-9]+),([0-9]+),'(.+?)'\.((?:split\('\|'\))|(?:split\('\|'\),0,\{\}))\)"
        )

        for script in scripts:
            script_content = script.string
            if script_content and "eval(function(p,a,c,k,e,d)" in script_content:
                matcher = pattern.search(script_content)
                if matcher:
                    dictionary_str = matcher.group(5)
                    dictionary = dictionary_str.split("|") if dictionary_str else []
                    encrypted_code = matcher.group(2)
                    result["encrypted_code"] = encrypted_code
                    result["dictionary"] = dictionary
                    print(f"✅ 成功提取到M3U8加密信息，字典长度: {len(dictionary)}")
                    return result

        print("⚠️ 未找到M3U8加密信息")
        return result
    
    def deobfuscate_m3u8(self, encrypted_code: Optional[str], dictionary: Optional[List[str]]) -> List[str]:
        """
        解密M3U8 URL信息
        """
        if not encrypted_code or not dictionary:
            print("❌ 解密M3U8失败: 加密代码或字典为空")
            return []

        parts = encrypted_code.split(";")
        results = []

        for part in parts:
            if "=" not in part:
                continue

            # 提取值部分，去除引号、反斜杠和空格
            value = (
                part.split("=")[1]
                .replace('"', "")
                .replace("'", "")
                .replace("\\", "")
                .replace(" ", "")
            )

            decoded = ""
            for c in value:
                if c in [".", "-", "/", ":"]:
                    decoded += c
                else:
                    try:
                        number = int(c, 16)
                        if 0 <= number < len(dictionary):
                            decoded += dictionary[number]
                    except ValueError:
                        # 如果不是十六进制字符，保留原字符
                        decoded += c

            if decoded and (".m3u8" in decoded or "/master" in decoded):
                results.append(decoded)
                print(f"🎯 解密出M3U8 URL: {decoded[:80]}...")

        return results
    
    def test_m3u8_with_proxy(self, m3u8_url: str, referer: str = "https://surrit.store/"):
        """
        通过代理服务器测试M3U8 URL
        """
        print(f"\n🔄 通过代理测试M3U8: {m3u8_url}")
        
        # 构建代理 URL
        proxy_url = f"http://localhost:8001/proxy?url={urllib.parse.quote(m3u8_url)}&referer={urllib.parse.quote(referer)}"
        
        try:
            req = urllib.request.Request(proxy_url)
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read()
                
                # 处理 gzip 压缩
                if content[:2] == b'\x1f\x8b':
                    import gzip
                    content = gzip.decompress(content)
                
                text = content.decode('utf-8')
                lines = text.split('\n')
                
                print(f"✅ M3U8 内容获取成功，共 {len(lines)} 行")
                
                # 分析内容
                proxy_lines = 0
                segment_lines = 0
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('http://localhost:8001/proxy'):
                        proxy_lines += 1
                    elif line.startswith('http') and '.ts' in line:
                        segment_lines += 1
                
                print(f"📊 代理片段数: {proxy_lines}")
                print(f"📊 原始片段数: {segment_lines}")
                
                if proxy_lines > 0:
                    print("✅ M3U8 重写功能正常工作！")
                else:
                    print("⚠️ 未检测到重写的代理片段")
                    
                return True
                
        except Exception as e:
            print(f"❌ 代理测试失败: {e}")
            return False
    
    def crawl_movie(self, movie_url: str) -> Dict[str, Any]:
        """
        爬取电影页面并提取M3U8信息
        """
        print(f"\n🎬 开始爬取电影: {movie_url}")
        
        # 获取页面内容
        html = self.get_page_content(movie_url)
        if not html:
            return {"success": False, "error": "页面内容获取失败"}
        
        print(f"📄 页面内容获取成功，长度: {len(html)} 字符")
        
        # 提取M3U8加密信息
        m3u8_info = self.extract_m3u8_info(html)
        
        if not m3u8_info["encrypted_code"] or not m3u8_info["dictionary"]:
            return {"success": False, "error": "未找到M3U8加密信息"}
        
        # 解密M3U8 URL
        m3u8_urls = self.deobfuscate_m3u8(
            m3u8_info["encrypted_code"], 
            m3u8_info["dictionary"]
        )
        
        if not m3u8_urls:
            return {"success": False, "error": "M3U8 URL解密失败"}
        
        print(f"🎯 成功解密出 {len(m3u8_urls)} 个M3U8 URL")
        
        # 测试每个M3U8 URL
        working_urls = []
        for url in m3u8_urls:
            if self.test_m3u8_with_proxy(url):
                working_urls.append(url)
        
        return {
            "success": True,
            "m3u8_urls": m3u8_urls,
            "working_urls": working_urls,
            "encrypted_info": m3u8_info
        }

def main():
    """
    主测试函数
    """
    print("🧪 MissAV M3U8 爬取测试")
    print("=" * 50)
    
    # 测试URL - 这里需要替换为实际的MissAV电影页面URL
    test_urls = [
        "https://surrit.store/e/8NZP3LR8",  # 示例URL，需要替换为实际的电影页面
        # 可以添加更多测试URL
    ]
    
    crawler = SimpleMissAVCrawler()
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n📋 测试 {i}/{len(test_urls)}: {url}")
        
        result = crawler.crawl_movie(url)
        
        if result["success"]:
            print(f"✅ 测试成功！")
            print(f"📊 找到 {len(result['m3u8_urls'])} 个M3U8 URL")
            print(f"🔄 其中 {len(result['working_urls'])} 个通过代理测试成功")
            
            # 保存结果
            output_file = f"missav_test_result_{i}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"💾 结果已保存到: {output_file}")
            
        else:
            print(f"❌ 测试失败: {result['error']}")
        
        # 延迟避免请求过快
        if i < len(test_urls):
            print("⏳ 等待 3 秒...")
            time.sleep(3)
    
    print("\n" + "=" * 50)
    print("🎉 测试完成！")
    print("\n💡 使用说明:")
    print("1. 确保代理服务器运行在 localhost:8001")
    print("2. 替换 test_urls 中的URL为实际的MissAV电影页面")
    print("3. 检查输出的JSON文件获取详细结果")

if __name__ == "__main__":
    main()