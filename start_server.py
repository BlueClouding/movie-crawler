#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M3U8播放器本地服务器
用于托管HTML播放器页面，支持跨域访问
"""

import http.server
import socketserver
import webbrowser
import os
import sys
from urllib.parse import urlparse

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """支持CORS的HTTP请求处理器"""
    
    def end_headers(self):
        # 添加CORS头
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()
    
    def do_OPTIONS(self):
        """处理OPTIONS预检请求"""
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"[{self.log_date_time_string()}] {format % args}")

def find_free_port(start_port=8000, max_attempts=100):
    """查找可用端口"""
    import socket
    
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    
    raise RuntimeError(f"无法找到可用端口 (尝试了 {start_port} 到 {start_port + max_attempts - 1})")

def start_server():
    """启动本地服务器"""
    # 切换到脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print("🚀 启动M3U8播放器服务器...")
    print(f"📁 工作目录: {script_dir}")
    
    # 查找可用端口
    try:
        port = find_free_port(8000)
        print(f"🔍 找到可用端口: {port}")
    except RuntimeError as e:
        print(f"❌ 错误: {e}")
        return
    
    # 检查HTML文件是否存在
    html_file = 'm3u8_player.html'
    if not os.path.exists(html_file):
        print(f"❌ 错误: 找不到 {html_file} 文件")
        print(f"请确保 {html_file} 文件在当前目录中")
        return
    
    try:
        # 创建服务器
        with socketserver.TCPServer(("", port), CORSHTTPRequestHandler) as httpd:
            server_url = f"http://localhost:{port}"
            player_url = f"{server_url}/{html_file}"
            
            print("\n" + "="*60)
            print("🎬 M3U8播放器服务器已启动!")
            print("="*60)
            print(f"📡 服务器地址: {server_url}")
            print(f"🎥 播放器地址: {player_url}")
            print("="*60)
            print("\n📋 使用说明:")
            print("1. 浏览器会自动打开播放器页面")
            print("2. 在页面中输入M3U8链接和Referer")
            print("3. 点击'加载视频'开始播放")
            print("4. 按 Ctrl+C 停止服务器")
            print("\n💡 提示:")
            print("- 如果遇到跨域问题，可能需要使用代理服务器")
            print("- 某些视频可能需要特定的Referer才能播放")
            print("- 支持自适应码率和多种视频格式")
            print()
            
            # 自动打开浏览器
            try:
                print("🌐 正在打开浏览器...")
                webbrowser.open(player_url)
            except Exception as e:
                print(f"⚠️ 无法自动打开浏览器: {e}")
                print(f"请手动访问: {player_url}")
            
            print(f"\n🔄 服务器运行中... (端口 {port})")
            print("按 Ctrl+C 停止服务器\n")
            
            # 启动服务器
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n\n🛑 服务器已停止")
        print("👋 感谢使用M3U8播放器!")
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        print("请检查端口是否被占用或权限是否足够")

if __name__ == "__main__":
    try:
        start_server()
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        sys.exit(1)