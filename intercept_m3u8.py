#!/usr/bin/env python3
"""
使用浏览器模拟器访问链接并拦截m3u8文件的脚本
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict
from urllib.parse import urlparse

from loguru import logger
from playwright.async_api import Page, Response

# 添加项目路径
sys.path.append(str(Path(__file__).parent / 'src'))

from app.utils.stealth_utils import StealthBrowser


class M3U8Interceptor:
    """
    M3U8文件拦截器，用于监听和捕获网络请求中的m3u8文件
    """
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser = None
        self.page = None
        self.intercepted_m3u8_urls = []
        self.all_requests = []
        
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
        
    async def start(self):
        """启动浏览器"""
        self.browser = StealthBrowser(headless=self.headless)
        await self.browser.start()
        self.page = self.browser.page
        
        # 设置请求拦截器
        await self._setup_request_interceptor()
        logger.info("浏览器已启动，开始监听网络请求")
        
    async def close(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            logger.info("浏览器已关闭")
            
    async def _setup_request_interceptor(self):
        """设置网络请求拦截器"""
        
        async def handle_request(request):
            """处理请求"""
            url = request.url
            method = request.method
            
            # 记录所有请求
            request_info = {
                'url': url,
                'method': method,
                'headers': dict(request.headers),
                'resource_type': request.resource_type
            }
            self.all_requests.append(request_info)
            
            # 检查是否为m3u8文件
            if self._is_m3u8_url(url):
                logger.success(f"🎯 发现M3U8文件: {url}")
                self.intercepted_m3u8_urls.append({
                    'url': url,
                    'method': method,
                    'headers': dict(request.headers),
                    'timestamp': asyncio.get_event_loop().time()
                })
            
            # 记录视频相关请求
            if self._is_video_related(url):
                logger.info(f"📹 视频相关请求: {url}")
                
        async def handle_response(response: Response):
            """处理响应"""
            url = response.url
            status = response.status
            content_type = response.headers.get('content-type', '')
            
            # 检查响应是否为m3u8内容
            if self._is_m3u8_content(url, content_type):
                logger.success(f"🎯 M3U8响应: {url} (状态: {status})")
                try:
                    # 尝试获取响应内容
                    if status == 200:
                        content = await response.text()
                        await self._save_m3u8_content(url, content)
                except Exception as e:
                    logger.warning(f"无法获取M3U8内容: {e}")
                    
        # 绑定事件监听器
        if self.page:
            self.page.on('request', handle_request)
            self.page.on('response', handle_response)
        
    def _is_m3u8_url(self, url: str) -> bool:
        """检查URL是否为m3u8文件"""
        return (
            url.endswith('.m3u8') or 
            '/playlist.m3u8' in url or
            'master.m3u8' in url or
            'm3u8' in url.lower()
        )
        
    def _is_m3u8_content(self, url: str, content_type: str) -> bool:
        """检查响应内容是否为m3u8"""
        return (
            self._is_m3u8_url(url) or
            'application/vnd.apple.mpegurl' in content_type.lower() or
            'application/x-mpegurl' in content_type.lower() or
            'audio/mpegurl' in content_type.lower()
        )
        
    def _is_video_related(self, url: str) -> bool:
        """检查是否为视频相关请求"""
        video_extensions = ['.mp4', '.ts', '.m4s', '.webm', '.mkv', '.avi']
        video_keywords = ['video', 'stream', 'media', 'hls', 'dash']
        
        url_lower = url.lower()
        return (
            any(ext in url_lower for ext in video_extensions) or
            any(keyword in url_lower for keyword in video_keywords)
        )
        
    async def _save_m3u8_content(self, url: str, content: str):
        """保存m3u8文件内容"""
        try:
            # 创建输出目录
            output_dir = Path('output/m3u8_files')
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成文件名
            parsed_url = urlparse(url)
            filename = parsed_url.path.split('/')[-1] or 'playlist.m3u8'
            if not filename.endswith('.m3u8'):
                filename += '.m3u8'
                
            # 避免文件名冲突
            counter = 1
            original_filename = filename
            while (output_dir / filename).exists():
                name, ext = original_filename.rsplit('.', 1)
                filename = f"{name}_{counter}.{ext}"
                counter += 1
                
            file_path = output_dir / filename
            
            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            logger.success(f"💾 M3U8文件已保存: {file_path}")
            
            # 同时保存URL信息
            info_file = file_path.with_suffix('.json')
            info_data = {
                'url': url,
                'filename': filename,
                'timestamp': asyncio.get_event_loop().time(),
                'content_length': len(content)
            }
            
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(info_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"保存M3U8文件失败: {e}")
            
    async def visit_url(self, url: str, wait_time: int = 10):
        """访问指定URL并等待页面加载"""
        try:
            logger.info(f"🌐 正在访问: {url}")
            
            # 访问页面
            if self.page:
                await self.page.goto(url, wait_until='networkidle', timeout=30000)
            logger.info("✅ 页面加载完成")
            
            # 等待一段时间以捕获所有网络请求
            logger.info(f"⏳ 等待 {wait_time} 秒以捕获网络请求...")
            await asyncio.sleep(wait_time)
            
            # 尝试点击播放按钮（如果存在）
            await self._try_play_video()
            
            # 再等待一段时间
            logger.info("⏳ 等待额外的网络请求...")
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"访问URL失败: {e}")
            
    async def _try_play_video(self):
        """尝试点击播放按钮"""
        try:
            # 常见的播放按钮选择器
            play_selectors = [
                'button[aria-label*="play"]',
                'button[title*="play"]',
                '.play-button',
                '.video-play-button',
                '[class*="play"]',
                'video',
                '.player',
                '[data-testid*="play"]'
            ]
            
            if self.page:
                for selector in play_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        if elements:
                            logger.info(f"🎮 尝试点击播放按钮: {selector}")
                            await elements[0].click()
                            await asyncio.sleep(2)
                            break
                    except Exception:
                        continue
                    
        except Exception as e:
            logger.debug(f"点击播放按钮失败: {e}")
            
    def print_summary(self):
        """打印拦截结果摘要"""
        logger.info("\n" + "="*50)
        logger.info("📊 拦截结果摘要")
        logger.info("="*50)
        
        logger.info(f"🔍 总请求数: {len(self.all_requests)}")
        logger.info(f"🎯 发现M3U8文件数: {len(self.intercepted_m3u8_urls)}")
        
        if self.intercepted_m3u8_urls:
            logger.info("\n📋 发现的M3U8文件:")
            for i, m3u8_info in enumerate(self.intercepted_m3u8_urls, 1):
                logger.info(f"  {i}. {m3u8_info['url']}")
        else:
            logger.warning("❌ 未发现任何M3U8文件")
            
        # 显示视频相关请求
        video_requests = [req for req in self.all_requests if self._is_video_related(req['url'])]
        if video_requests:
            logger.info(f"\n📹 视频相关请求数: {len(video_requests)}")
            for i, req in enumerate(video_requests[:5], 1):  # 只显示前5个
                logger.info(f"  {i}. {req['url']}")
            if len(video_requests) > 5:
                logger.info(f"  ... 还有 {len(video_requests) - 5} 个请求")


async def main():
    """主函数"""
    # 配置日志
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    
    # 目标URL
    target_url = "https://surrit.store/e/8NZP3LR8"
    
    logger.info("🚀 启动M3U8拦截器")
    
    try:
        async with M3U8Interceptor(headless=False) as interceptor:
            # 访问目标URL
            await interceptor.visit_url(target_url, wait_time=15)
            
            # 打印结果摘要
            interceptor.print_summary()
            
            # 保存完整的请求日志
            output_dir = Path('output')
            output_dir.mkdir(exist_ok=True)
            
            with open(output_dir / 'all_requests.json', 'w', encoding='utf-8') as f:
                json.dump(interceptor.all_requests, f, indent=2, ensure_ascii=False)
                
            with open(output_dir / 'm3u8_urls.json', 'w', encoding='utf-8') as f:
                json.dump(interceptor.intercepted_m3u8_urls, f, indent=2, ensure_ascii=False)
                
            logger.info(f"📁 详细日志已保存到 output/ 目录")
            
    except KeyboardInterrupt:
        logger.info("👋 用户中断操作")
    except Exception as e:
        logger.error(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())