#!/usr/bin/env python3
"""
M3U8下载工具 - 带完整请求头绕过Cloudflare防护
"""

import os
import requests
import subprocess
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional

from loguru import logger


class M3U8DownloaderWithHeaders:
    """
    带完整请求头的M3U8下载器
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.output_dir = Path("output/downloads")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置完整的请求头，模拟真实浏览器
        self.headers = {
            'accept': '*/*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
            'cache-control': 'no-cache',
            'dnt': '1',
            'origin': 'https://surrit.store',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://surrit.store/',
            'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36'
        }
        
        self.session.headers.update(self.headers)
        
    def download_m3u8_content(self, url: str) -> Optional[str]:
        """下载M3U8文件内容"""
        try:
            logger.info(f"正在下载M3U8文件: {url}")
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                logger.success("M3U8文件下载成功")
                return response.text
            elif response.status_code == 403:
                logger.error("访问被拒绝 (403) - 可能需要更多反检测措施")
                return None
            elif response.status_code == 503:
                logger.error("服务不可用 (503) - Cloudflare防护激活")
                return None
            else:
                logger.error(f"下载失败，状态码: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {e}")
            return None
            
    def save_m3u8_file(self, content: str, filename: str = "downloaded_video.m3u8") -> str:
        """保存M3U8文件"""
        file_path = self.output_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.success(f"M3U8文件已保存: {file_path}")
        return str(file_path)
        
    def create_curl_command(self, url: str) -> str:
        """生成完整的curl命令"""
        curl_cmd = f"curl '{url}' \\"
        
        for key, value in self.headers.items():
            curl_cmd += f"\n  -H '{key}: {value}' \\"
            
        # 移除最后的反斜杠
        curl_cmd = curl_cmd.rstrip(' \\\\')
        
        return curl_cmd
        
    def create_ffmpeg_command_with_headers(self, m3u8_url: str, output_file: str) -> str:
        """生成带请求头的FFmpeg命令"""
        # 构建FFmpeg的headers参数
        headers_str = ""
        for key, value in self.headers.items():
            headers_str += f"{key}: {value}\r\n"
            
        ffmpeg_cmd = [
            'ffmpeg',
            '-headers', f'"{headers_str}"',
            '-i', f'"{m3u8_url}"',
            '-c', 'copy',
            '-bsf:a', 'aac_adtstoasc',
            '-y',
            f'"{output_file}"'
        ]
        
        return ' '.join(ffmpeg_cmd)
        
    def create_yt_dlp_command_with_headers(self, m3u8_url: str, output_file: str) -> str:
        """生成带请求头的yt-dlp命令"""
        # 构建yt-dlp的headers参数
        headers_args = []
        for key, value in self.headers.items():
            headers_args.extend(['--add-header', f'{key}:{value}'])
            
        ytdlp_cmd = [
            'yt-dlp',
            '--output', f'"{output_file.replace(".mp4", "")}"',
            *headers_args,
            f'"{m3u8_url}"'
        ]
        
        return ' '.join(ytdlp_cmd)
        
    def download_with_ffmpeg(self, m3u8_url: str, output_file: str) -> bool:
        """使用FFmpeg下载视频（带请求头）"""
        try:
            # 构建FFmpeg的headers参数
            headers_str = ""
            for key, value in self.headers.items():
                headers_str += f"{key}: {value}\r\n"
                
            cmd = [
                'ffmpeg',
                '-headers', headers_str,
                '-i', m3u8_url,
                '-c', 'copy',
                '-bsf:a', 'aac_adtstoasc',
                '-y',
                output_file
            ]
            
            logger.info(f"开始使用FFmpeg下载: {m3u8_url}")
            logger.info(f"输出文件: {output_file}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.success(f"下载成功: {output_file}")
                return True
            else:
                logger.error(f"FFmpeg下载失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"FFmpeg下载异常: {e}")
            return False
            
    def test_connection(self, url: str) -> Dict[str, any]:
        """测试连接并返回详细信息"""
        try:
            logger.info(f"测试连接: {url}")
            response = self.session.get(url, timeout=10)
            
            result = {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'content_length': len(response.content),
                'content_preview': response.text[:500] if response.text else None
            }
            
            if response.status_code == 200:
                logger.success(f"连接成功 - 状态码: {response.status_code}")
            else:
                logger.warning(f"连接异常 - 状态码: {response.status_code}")
                
            return result
            
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
    def print_usage_info(self, m3u8_url: str):
        """打印使用说明"""
        output_file = str(self.output_dir / "video_with_headers.mp4")
        
        print("\n" + "="*80)
        print("🔧 M3U8下载工具 - 绕过Cloudflare防护")
        print("="*80)
        
        print(f"\n📋 目标URL: {m3u8_url}")
        print(f"📁 输出目录: {self.output_dir}")
        
        print("\n🌐 完整curl命令:")
        print(self.create_curl_command(m3u8_url))
        
        print("\n🎬 FFmpeg下载命令:")
        print(self.create_ffmpeg_command_with_headers(m3u8_url, output_file))
        
        print("\n📺 yt-dlp下载命令:")
        print(self.create_yt_dlp_command_with_headers(m3u8_url, output_file))
        
        print("\n💡 使用说明:")
        print("1. 首先测试连接是否正常")
        print("2. 如果连接成功，可以直接下载M3U8内容")
        print("3. 使用FFmpeg或yt-dlp命令下载完整视频")
        print("4. 所有命令都包含了必要的请求头来绕过防护")
        
        print("\n⚠️  注意事项:")
        print("- 如果仍然被阻拦，可能需要使用代理或更换IP")
        print("- 某些网站可能需要额外的Cookie或Token")
        print("- 建议先测试连接再进行下载")
        print("="*80)


def main():
    """主函数"""
    # 用户提供的M3U8 URL
    m3u8_url = "https://faf8b60b.freshvibe64.store/blah3/XEn0ezAekFvTgxX3A7ZKZY_9hxR3jYNOCqeLthCPgxdQyIZi/video.m3u8"
    
    downloader = M3U8DownloaderWithHeaders()
    
    # 打印使用信息
    downloader.print_usage_info(m3u8_url)
    
    # 测试连接
    print("\n🔍 测试连接...")
    test_result = downloader.test_connection(m3u8_url)
    
    if test_result.get('success'):
        print("✅ 连接测试成功！")
        
        # 尝试下载M3U8内容
        content = downloader.download_m3u8_content(m3u8_url)
        if content:
            # 保存M3U8文件
            saved_file = downloader.save_m3u8_file(content, "video_with_headers.m3u8")
            print(f"\n📄 M3U8文件已保存: {saved_file}")
            
            # 显示内容预览
            print("\n📋 M3U8内容预览:")
            print("-" * 50)
            print(content[:1000] + "..." if len(content) > 1000 else content)
            print("-" * 50)
            
        else:
            print("❌ M3U8内容下载失败")
            
    else:
        print("❌ 连接测试失败")
        if 'error' in test_result:
            print(f"错误信息: {test_result['error']}")
        else:
            print(f"状态码: {test_result.get('status_code', 'Unknown')}")
            
    print("\n" + "="*80)


if __name__ == "__main__":
    main()