#!/usr/bin/env python3
"""
M3U8视频下载工具
支持下载HLS视频流或生成播放链接
"""

import os
import json
import subprocess
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Any, Optional

from loguru import logger


class M3U8Downloader:
    """
    M3U8视频下载器
    """
    
    def __init__(self, base_url: str = "https://surrit.store/e/8NZP3LR8"):
        self.base_url = base_url
        self.m3u8_dir = Path("output/m3u8_files")
        self.download_dir = Path("output/downloads")
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
    def load_analysis_report(self) -> List[Dict[str, Any]]:
        """加载分析报告"""
        report_path = Path("output/m3u8_analysis_report.json")
        if not report_path.exists():
            logger.error("分析报告不存在，请先运行analyze_m3u8.py")
            return []
            
        with open(report_path, 'r', encoding='utf-8') as f:
            return json.load(f)
            
    def get_best_quality_stream(self) -> Optional[Dict[str, Any]]:
        """获取最高质量的视频流"""
        analysis_results = self.load_analysis_report()
        
        best_stream = None
        max_bandwidth = 0
        
        for result in analysis_results:
            if result.get('type') == 'master_playlist':
                for stream in result.get('streams', []):
                    bandwidth = stream.get('bandwidth', 0)
                    if bandwidth > max_bandwidth:
                        max_bandwidth = bandwidth
                        best_stream = {
                            'file': result['filename'],
                            'stream': stream,
                            'file_path': result['file_path']
                        }
                        
        return best_stream
        
    def construct_full_url(self, relative_url: str) -> str:
        """构造完整的URL"""
        if relative_url.startswith('http'):
            return relative_url
            
        # 从base_url构造完整URL
        base_parts = self.base_url.rstrip('/').split('/')
        if relative_url.startswith('qc/') or relative_url.startswith('qa/'):
            # 这些是相对于视频页面的路径
            return f"{'/'.join(base_parts)}/{relative_url}"
        else:
            return urljoin(self.base_url, relative_url)
            
    def generate_download_commands(self) -> List[Dict[str, str]]:
        """生成下载命令"""
        analysis_results = self.load_analysis_report()
        commands = []
        
        for result in analysis_results:
            if result.get('type') == 'master_playlist':
                for i, stream in enumerate(result.get('streams', [])):
                    stream_url = self.construct_full_url(stream.get('url', ''))
                    resolution = stream.get('resolution', 'unknown')
                    bandwidth = stream.get('bandwidth', 0)
                    
                    output_filename = f"video_{resolution}_{bandwidth}.mp4"
                    output_path = self.download_dir / output_filename
                    
                    # FFmpeg命令
                    ffmpeg_cmd = [
                        'ffmpeg',
                        '-i', stream_url,
                        '-c', 'copy',
                        '-bsf:a', 'aac_adtstoasc',
                        str(output_path)
                    ]
                    
                    # yt-dlp命令（备选）
                    ytdlp_cmd = [
                        'yt-dlp',
                        '--output', str(output_path.with_suffix('')),
                        stream_url
                    ]
                    
                    commands.append({
                        'resolution': resolution,
                        'bandwidth': f"{bandwidth:,} bps",
                        'url': stream_url,
                        'output_file': str(output_path),
                        'ffmpeg_command': ' '.join(ffmpeg_cmd),
                        'ytdlp_command': ' '.join(ytdlp_cmd)
                    })
                    
        return commands
        
    def download_with_ffmpeg(self, stream_url: str, output_path: str) -> bool:
        """使用FFmpeg下载视频"""
        try:
            cmd = [
                'ffmpeg',
                '-i', stream_url,
                '-c', 'copy',
                '-bsf:a', 'aac_adtstoasc',
                '-y',  # 覆盖输出文件
                output_path
            ]
            
            logger.info(f"开始下载: {stream_url}")
            logger.info(f"输出文件: {output_path}")
            logger.info(f"命令: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.success(f"下载成功: {output_path}")
                return True
            else:
                logger.error(f"下载失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"下载异常: {e}")
            return False
            
    def download_with_ytdlp(self, stream_url: str, output_path: str) -> bool:
        """使用yt-dlp下载视频"""
        try:
            cmd = [
                'yt-dlp',
                '--output', output_path.replace('.mp4', ''),
                stream_url
            ]
            
            logger.info(f"使用yt-dlp下载: {stream_url}")
            logger.info(f"命令: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.success(f"下载成功: {output_path}")
                return True
            else:
                logger.error(f"下载失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"下载异常: {e}")
            return False
            
    def create_playlist_file(self, output_file: str = "output/video_playlist.m3u8"):
        """创建可直接播放的播放列表文件"""
        best_stream = self.get_best_quality_stream()
        if not best_stream:
            logger.error("未找到可用的视频流")
            return
            
        stream_url = self.construct_full_url(best_stream['stream'].get('url', ''))
        
        playlist_content = f"""#EXTM3U
#EXT-X-VERSION:3
#EXT-X-STREAM-INF:BANDWIDTH={best_stream['stream'].get('bandwidth', 0)},RESOLUTION={best_stream['stream'].get('resolution', '')}
{stream_url}
"""
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(playlist_content)
            
        logger.success(f"播放列表已创建: {output_path}")
        logger.info(f"可以使用VLC等播放器打开: {output_path}")
        
    def print_download_info(self):
        """打印下载信息"""
        commands = self.generate_download_commands()
        
        print("\n" + "="*60)
        print("📥 M3U8视频下载信息")
        print("="*60)
        
        if not commands:
            print("❌ 未找到可下载的视频流")
            return
            
        for i, cmd_info in enumerate(commands, 1):
            print(f"\n🎬 视频流 {i}:")
            print(f"   分辨率: {cmd_info['resolution']}")
            print(f"   带宽: {cmd_info['bandwidth']}")
            print(f"   URL: {cmd_info['url']}")
            print(f"   输出文件: {cmd_info['output_file']}")
            print(f"\n📋 FFmpeg命令:")
            print(f"   {cmd_info['ffmpeg_command']}")
            print(f"\n📋 yt-dlp命令:")
            print(f"   {cmd_info['ytdlp_command']}")
            
    def download_best_quality(self, use_ytdlp: bool = False):
        """下载最高质量的视频"""
        best_stream = self.get_best_quality_stream()
        if not best_stream:
            logger.error("未找到可用的视频流")
            return False
            
        stream_url = self.construct_full_url(best_stream['stream'].get('url', ''))
        resolution = best_stream['stream'].get('resolution', 'unknown')
        bandwidth = best_stream['stream'].get('bandwidth', 0)
        
        output_filename = f"video_best_{resolution}_{bandwidth}.mp4"
        output_path = str(self.download_dir / output_filename)
        
        logger.info(f"准备下载最高质量视频: {resolution} ({bandwidth:,} bps)")
        
        if use_ytdlp:
            return self.download_with_ytdlp(stream_url, output_path)
        else:
            return self.download_with_ffmpeg(stream_url, output_path)


def main():
    """主函数"""
    print("📥 M3U8视频下载工具")
    print("="*40)
    
    downloader = M3U8Downloader()
    
    # 显示下载信息
    downloader.print_download_info()
    
    # 创建播放列表文件
    downloader.create_playlist_file()
    
    print("\n" + "="*60)
    print("💡 使用说明:")
    print("1. 上面显示了所有可用的视频流和下载命令")
    print("2. 已创建播放列表文件，可直接用VLC播放器打开")
    print("3. 要下载视频，请确保安装了ffmpeg或yt-dlp")
    print("4. 复制上面的命令到终端执行即可下载")
    print("\n📋 安装下载工具:")
    print("   brew install ffmpeg")
    print("   pip install yt-dlp")
    print("="*60)


if __name__ == "__main__":
    main()