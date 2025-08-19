#!/usr/bin/env python3
"""
M3U8文件分析工具
分析拦截到的m3u8文件并提供详细信息
"""

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Any

from loguru import logger


class M3U8Analyzer:
    """
    M3U8文件分析器
    """
    
    def __init__(self, m3u8_dir: str = "output/m3u8_files"):
        self.m3u8_dir = Path(m3u8_dir)
        self.analysis_results = []
        
    def analyze_all_files(self):
        """分析所有m3u8文件"""
        if not self.m3u8_dir.exists():
            logger.error(f"目录不存在: {self.m3u8_dir}")
            return
            
        m3u8_files = list(self.m3u8_dir.glob("*.m3u8"))
        if not m3u8_files:
            logger.warning("未找到任何m3u8文件")
            return
            
        logger.info(f"找到 {len(m3u8_files)} 个m3u8文件")
        
        for file_path in m3u8_files:
            logger.info(f"\n分析文件: {file_path.name}")
            analysis = self.analyze_file(file_path)
            self.analysis_results.append(analysis)
            self.print_analysis(analysis)
            
    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """分析单个m3u8文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            analysis = {
                'filename': file_path.name,
                'file_path': str(file_path),
                'file_size': file_path.stat().st_size,
                'type': 'unknown',
                'segments': [],
                'streams': [],
                'metadata': {},
                'total_duration': 0,
                'segment_count': 0
            }
            
            lines = content.strip().split('\n')
            
            # 检查是否为有效的m3u8文件
            if not lines or lines[0] != '#EXTM3U':
                analysis['type'] = 'invalid'
                return analysis
                
            # 分析文件类型和内容
            if '#EXT-X-STREAM-INF:' in content:
                analysis['type'] = 'master_playlist'
                analysis['streams'] = self._parse_master_playlist(lines)
            elif '#EXTINF:' in content:
                analysis['type'] = 'media_playlist'
                segments, total_duration = self._parse_media_playlist(lines)
                analysis['segments'] = segments
                analysis['total_duration'] = total_duration
                analysis['segment_count'] = len(segments)
            else:
                analysis['type'] = 'unknown_playlist'
                
            # 解析元数据
            analysis['metadata'] = self._parse_metadata(lines)
            
            return analysis
            
        except Exception as e:
            logger.error(f"分析文件失败 {file_path}: {e}")
            return {
                'filename': file_path.name,
                'error': str(e),
                'type': 'error'
            }
            
    def _parse_master_playlist(self, lines: List[str]) -> List[Dict[str, Any]]:
        """解析主播放列表"""
        streams = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('#EXT-X-STREAM-INF:'):
                # 解析流信息
                stream_info = self._parse_stream_inf(line)
                
                # 下一行应该是流的URL
                if i + 1 < len(lines):
                    stream_url = lines[i + 1].strip()
                    if not stream_url.startswith('#'):
                        stream_info['url'] = stream_url
                        streams.append(stream_info)
                        i += 1
            i += 1
            
        return streams
        
    def _parse_media_playlist(self, lines: List[str]) -> tuple:
        """解析媒体播放列表"""
        segments = []
        total_duration = 0
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('#EXTINF:'):
                # 解析段信息
                duration_match = re.search(r'#EXTINF:([\d.]+)', line)
                duration = float(duration_match.group(1)) if duration_match else 0
                
                # 下一行应该是段的URL
                if i + 1 < len(lines):
                    segment_url = lines[i + 1].strip()
                    if not segment_url.startswith('#'):
                        segments.append({
                            'duration': duration,
                            'url': segment_url
                        })
                        total_duration += duration
                        i += 1
            i += 1
            
        return segments, total_duration
        
    def _parse_stream_inf(self, line: str) -> Dict[str, Any]:
        """解析EXT-X-STREAM-INF行"""
        stream_info = {}
        
        # 解析带宽
        bandwidth_match = re.search(r'BANDWIDTH=(\d+)', line)
        if bandwidth_match:
            stream_info['bandwidth'] = int(bandwidth_match.group(1))
            
        # 解析分辨率
        resolution_match = re.search(r'RESOLUTION=(\d+x\d+)', line)
        if resolution_match:
            stream_info['resolution'] = resolution_match.group(1)
            
        # 解析编解码器
        codecs_match = re.search(r'CODECS="([^"]+)"', line)
        if codecs_match:
            stream_info['codecs'] = codecs_match.group(1)
            
        return stream_info
        
    def _parse_metadata(self, lines: List[str]) -> Dict[str, Any]:
        """解析元数据"""
        metadata = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith('#EXT-X-VERSION:'):
                metadata['version'] = int(line.split(':')[1])
            elif line.startswith('#EXT-X-TARGETDURATION:'):
                metadata['target_duration'] = int(line.split(':')[1])
            elif line.startswith('#EXT-X-MEDIA-SEQUENCE:'):
                metadata['media_sequence'] = int(line.split(':')[1])
            elif line.startswith('#EXT-X-PLAYLIST-TYPE:'):
                metadata['playlist_type'] = line.split(':')[1]
            elif line == '#EXT-X-ENDLIST':
                metadata['end_list'] = True
                
        return metadata
        
    def print_analysis(self, analysis: Dict[str, Any]):
        """打印分析结果"""
        print("\n" + "="*60)
        print(f"📁 文件: {analysis['filename']}")
        print(f"📊 大小: {analysis.get('file_size', 0):,} 字节")
        print(f"🎯 类型: {analysis['type']}")
        
        if analysis['type'] == 'master_playlist':
            print(f"🎬 包含 {len(analysis['streams'])} 个视频流:")
            for i, stream in enumerate(analysis['streams'], 1):
                bandwidth = stream.get('bandwidth', 0)
                resolution = stream.get('resolution', 'N/A')
                url = stream.get('url', 'N/A')
                print(f"  {i}. 分辨率: {resolution}, 带宽: {bandwidth:,} bps")
                print(f"     URL: {url}")
                
        elif analysis['type'] == 'media_playlist':
            duration = analysis.get('total_duration', 0)
            segment_count = analysis.get('segment_count', 0)
            print(f"⏱️  总时长: {duration:.1f} 秒 ({duration/60:.1f} 分钟)")
            print(f"📦 段数量: {segment_count}")
            
            # 显示前几个段的信息
            segments = analysis.get('segments', [])
            if segments:
                print("📋 前5个视频段:")
                for i, segment in enumerate(segments[:5], 1):
                    print(f"  {i}. 时长: {segment['duration']}s, URL: {segment['url'][:50]}...")
                    
        # 显示元数据
        metadata = analysis.get('metadata', {})
        if metadata:
            print("\n📋 元数据:")
            for key, value in metadata.items():
                print(f"  {key}: {value}")
                
    def save_analysis_report(self, output_file: str = "output/m3u8_analysis_report.json"):
        """保存分析报告"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.analysis_results, f, indent=2, ensure_ascii=False)
            
        logger.info(f"📄 分析报告已保存到: {output_path}")
        
    def print_summary(self):
        """打印总结"""
        print("\n" + "="*60)
        print("📊 M3U8文件分析总结")
        print("="*60)
        
        total_files = len(self.analysis_results)
        master_playlists = sum(1 for r in self.analysis_results if r.get('type') == 'master_playlist')
        media_playlists = sum(1 for r in self.analysis_results if r.get('type') == 'media_playlist')
        
        print(f"📁 总文件数: {total_files}")
        print(f"🎬 主播放列表: {master_playlists}")
        print(f"📺 媒体播放列表: {media_playlists}")
        
        # 找到最有价值的视频流
        best_streams = []
        for result in self.analysis_results:
            if result.get('type') == 'master_playlist':
                for stream in result.get('streams', []):
                    if 'bandwidth' in stream and 'resolution' in stream:
                        best_streams.append({
                            'file': result['filename'],
                            'bandwidth': stream['bandwidth'],
                            'resolution': stream['resolution'],
                            'url': stream.get('url', '')
                        })
                        
        if best_streams:
            # 按带宽排序
            best_streams.sort(key=lambda x: x['bandwidth'], reverse=True)
            print("\n🏆 推荐的视频流 (按质量排序):")
            for i, stream in enumerate(best_streams[:3], 1):
                print(f"  {i}. {stream['resolution']} - {stream['bandwidth']:,} bps")
                print(f"     来源: {stream['file']}")
                print(f"     URL: {stream['url']}")


def main():
    """主函数"""
    print("🔍 M3U8文件分析工具")
    print("="*40)
    
    analyzer = M3U8Analyzer()
    analyzer.analyze_all_files()
    analyzer.print_summary()
    analyzer.save_analysis_report()
    
    print("\n✅ 分析完成!")


if __name__ == "__main__":
    main()