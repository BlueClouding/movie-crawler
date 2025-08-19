#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M3U8代理服务器
用于解决跨域和Referer设置问题
"""

import http.server
import socketserver
import urllib.request
import urllib.parse
import json
import os
import gzip
import io
import re
import ssl
import requests
import warnings
from urllib.error import HTTPError, URLError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 禁用 SSL 警告
requests.packages.urllib3.disable_warnings()
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

class M3U8ProxyHandler(http.server.BaseHTTPRequestHandler):
    """M3U8代理请求处理器"""
    
    def do_GET(self):
        """处理GET请求"""
        if self.path == '/':
            self.serve_index()
        elif self.path.startswith('/proxy?'):
            self.handle_proxy_request()
        else:
            self.send_error(404, "Not Found")
    
    def do_OPTIONS(self):
        """处理OPTIONS预检请求"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def send_cors_headers(self):
        """发送CORS头"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Referer')
        self.send_header('Access-Control-Max-Age', '86400')
    
    def serve_index(self):
        """提供首页"""
        html_content = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>M3U8代理服务器</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .info { background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .example { background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; font-family: monospace; }
        .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
        .btn:hover { background: #0056b3; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔄 M3U8代理服务器</h1>
        
        <div class="info">
            <h3>📋 服务说明</h3>
            <p>这个代理服务器可以帮助您:</p>
            <ul>
                <li>✅ 解决M3U8视频的跨域访问问题</li>
                <li>✅ 自动设置正确的Referer头</li>
                <li>✅ 支持各种视频网站的防盗链</li>
                <li>✅ 提供统一的API接口</li>
            </ul>
        </div>
        
        <div class="info">
            <h3>🔗 API使用方法</h3>
            <p><strong>代理URL格式:</strong></p>
            <div class="example">
                http://localhost:8001/proxy?url=[M3U8_URL]&referer=[REFERER_URL]
            </div>
            
            <p><strong>参数说明:</strong></p>
            <ul>
                <li><code>url</code>: 要代理的M3U8链接 (必需)</li>
                <li><code>referer</code>: 设置的Referer头 (可选)</li>
            </ul>
        </div>
        
        <div class="info">
            <h3>💡 使用示例</h3>
            <p><strong>原始M3U8链接:</strong></p>
            <div class="example">
                https://example.com/video.m3u8
            </div>
            
            <p><strong>通过代理访问:</strong></p>
            <div class="example">
                http://localhost:8001/proxy?url=https://example.com/video.m3u8&referer=https://surrit.store/
            </div>
            
            <button class="btn" onclick="window.open('http://localhost:8000/m3u8_player.html', '_blank')">🎬 打开播放器</button>
            <button class="btn" onclick="testProxy()">🔍 测试代理</button>
        </div>
        
        <div id="testResult"></div>
    </div>
    
    <script>
        function testProxy() {
            const resultDiv = document.getElementById('testResult');
            resultDiv.innerHTML = '<div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">🔄 正在测试代理服务器...</div>';
            
            const testUrl = 'http://localhost:8001/proxy?url=https://httpbin.org/get&referer=https://surrit.store/';
            
            fetch(testUrl)
                .then(response => response.text())
                .then(data => {
                    resultDiv.innerHTML = `
                        <div style="background: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <h4>✅ 代理测试成功!</h4>
                            <p>代理服务器工作正常，可以正常处理请求。</p>
                        </div>
                    `;
                })
                .catch(error => {
                    resultDiv.innerHTML = `
                        <div style="background: #f8d7da; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <h4>❌ 代理测试失败</h4>
                            <p>错误信息: ${error.message}</p>
                            <p>请检查代理服务器是否正常运行。</p>
                        </div>
                    `;
                });
        }
    </script>
</body>
</html>
        '''
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def handle_proxy_request(self):
        """处理代理请求"""
        try:
            # 解析查询参数
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            
            if 'url' not in params:
                self.send_error(400, "Missing 'url' parameter")
                return
            
            target_url = params['url'][0]
            referer = params.get('referer', [''])[0]
            
            print(f"🔄 代理请求: {target_url}")
            if referer:
                print(f"📎 设置Referer: {referer}")
            
            # 设置请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'cross-site'
            }
            
            if referer:
                headers['Referer'] = referer
            
            # 创建会话并配置 SSL
            session = requests.Session()
            
            # 配置重试策略
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            # 发送请求（禁用 SSL 验证，增加更多选项）
            response = session.get(
                target_url, 
                headers=headers, 
                timeout=30, 
                verify=False,
                allow_redirects=True,
                stream=False
            )
            response.raise_for_status()
            
            content = response.content
            content_type = response.headers.get('Content-Type', 'application/vnd.apple.mpegurl')
            
            # 如果是 M3U8 文件，需要重写其中的 URL
            if 'mpegurl' in content_type.lower() or target_url.endswith('.m3u8'):
                content = self.rewrite_m3u8_content(content, target_url, referer or 'https://surrit.store/')
            
            # 发送响应
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(content)
            
            print(f"✅ 代理成功: {len(content)} 字节")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 请求错误: {e}")
            self.send_error(502, f"Proxy Error: {str(e)}")
        except Exception as e:
            print(f"❌ 代理错误: {e}")
            self.send_error(500, f"Proxy Error: {str(e)}")
    
    def rewrite_m3u8_content(self, content, base_url, referer):
        """重写 M3U8 内容，将片段 URL 重写为通过代理服务器请求"""
        try:
            # 处理 gzip 压缩的内容
            if content[:2] == b'\x1f\x8b':
                content = gzip.decompress(content)
            
            # 解码为文本
            text = content.decode('utf-8')
            
            # 获取基础 URL（用于相对路径解析）
            base_parts = urllib.parse.urlparse(base_url)
            base_dir = '/'.join(base_parts.path.split('/')[:-1])
            base_without_file = f"{base_parts.scheme}://{base_parts.netloc}{base_dir}"
            
            lines = text.split('\n')
            rewritten_lines = []
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    # 这是一个 URL 行
                    if line.startswith('http'):
                        # 绝对 URL
                        segment_url = line
                    else:
                        # 相对 URL，需要拼接
                        if line.startswith('/'):
                            segment_url = f"{base_parts.scheme}://{base_parts.netloc}{line}"
                        else:
                            segment_url = f"{base_without_file}/{line}"
                    
                    # 重写为通过代理服务器请求
                    proxy_url = f"http://localhost:{self.server.server_port}/proxy?url={urllib.parse.quote(segment_url)}&referer={urllib.parse.quote(referer)}"
                    rewritten_lines.append(proxy_url)
                    print(f"🔄 重写片段URL: {segment_url} -> 代理")
                else:
                    rewritten_lines.append(line)
            
            # 重新编码为字节
            rewritten_content = '\n'.join(rewritten_lines).encode('utf-8')
            print(f"📝 M3U8重写完成: {len(lines)} 行 -> {len(rewritten_lines)} 行")
            return rewritten_content
            
        except Exception as e:
            print(f"❌ M3U8重写失败: {e}")
            return content
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"[{self.log_date_time_string()}] {format % args}")

def find_free_port(start_port=8001, max_attempts=100):
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

def start_proxy_server():
    """启动代理服务器"""
    print("🔄 启动M3U8代理服务器...")
    
    # 查找可用端口
    try:
        port = find_free_port(8001)
        print(f"🔍 找到可用端口: {port}")
    except RuntimeError as e:
        print(f"❌ 错误: {e}")
        return
    
    try:
        with socketserver.TCPServer(("", port), M3U8ProxyHandler) as httpd:
            server_url = f"http://localhost:{port}"
            
            print("\n" + "="*60)
            print("🔄 M3U8代理服务器已启动!")
            print("="*60)
            print(f"📡 代理服务器: {server_url}")
            print(f"🎬 播放器地址: http://localhost:8000/m3u8_player.html")
            print("="*60)
            print("\n📋 使用说明:")
            print("1. 代理服务器可以解决跨域和Referer问题")
            print("2. 在播放器中使用代理URL格式:")
            print(f"   {server_url}/proxy?url=[M3U8_URL]&referer=[REFERER]")
            print("3. 按 Ctrl+C 停止服务器")
            print("\n💡 示例:")
            print(f"原始链接: https://example.com/video.m3u8")
            print(f"代理链接: {server_url}/proxy?url=https://example.com/video.m3u8&referer=https://surrit.store/")
            print()
            
            print(f"🔄 代理服务器运行中... (端口 {port})")
            print("按 Ctrl+C 停止服务器\n")
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n\n🛑 代理服务器已停止")
    except Exception as e:
        print(f"❌ 代理服务器启动失败: {e}")

if __name__ == "__main__":
    start_proxy_server()