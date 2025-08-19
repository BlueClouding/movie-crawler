#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的无头浏览器登录脚本
用于快速获取123av.com的登录cookie

使用方法:
python simple_login.py

或者在其他脚本中导入使用:
from simple_login import get_login_cookies
cookies = get_login_cookies()
"""

import asyncio
import logging
from datetime import datetime
from playwright.async_api import async_playwright

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleLoginService:
    """简化的登录服务"""
    
    def __init__(self, username="12345", password="kongqy"):
        self.base_url = "https://123av.com"
        self.username = username
        self.password = password
    
    async def get_cookies_async(self) -> str:
        """异步获取登录cookies"""
        try:
            async with async_playwright() as p:
                # 启动无头浏览器
                browser = await p.chromium.launch(headless=True, timeout=30000)
                
                try:
                    # 创建浏览器上下文
                    context = await browser.new_context(
                        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
                    )
                    
                    page = await context.new_page()
                    
                    # 访问主页
                    logger.info("访问网站主页...")
                    await page.goto(f"{self.base_url}/ja")
                    await page.wait_for_load_state("networkidle")
                    
                    # 准备登录数据
                    login_data = {
                        "username": self.username,
                        "password": self.password,
                        "remember_me": 1
                    }
                    
                    logger.info(f"发送登录请求到API端点...")
                    
                    # 通过API端点登录
                    response = await page.evaluate("""
                        async (data) => {
                            const response = await fetch('/ja/ajax/user/signin', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'Accept': 'application/json, text/plain, */*',
                                    'X-Requested-With': 'XMLHttpRequest'
                                },
                                body: JSON.stringify(data)
                            });
                            return {
                                status: response.status,
                                text: await response.text()
                            };
                        }
                    """, login_data)
                    
                    logger.info(f"登录响应状态: {response['status']}")
                    
                    if response['status'] == 200:
                        # 等待cookies更新
                        await page.wait_for_timeout(2000)
                        
                        # 提取cookies
                        cookies = await context.cookies()
                        cookie_string = self._format_cookies(cookies)
                        
                        if cookie_string:
                            logger.info(f"成功获取cookies，长度: {len(cookie_string)}字符")
                            return cookie_string
                        else:
                            logger.warning("未获取到有效cookies")
                            return ""
                    else:
                        logger.error(f"登录失败，状态码: {response['status']}")
                        return ""
                        
                finally:
                    await browser.close()
                    
        except Exception as e:
            logger.error(f"登录过程中发生错误: {e}")
            return ""
    
    def _format_cookies(self, cookies) -> str:
        """格式化cookies为HTTP头格式"""
        if not cookies:
            return ""
        
        cookie_pairs = []
        for cookie in cookies:
            cookie_pairs.append(f"{cookie['name']}={cookie['value']}")
        
        return "; ".join(cookie_pairs)
    
    def get_cookies(self) -> str:
        """同步方式获取cookies"""
        try:
            # 检查是否已经在事件循环中
            try:
                loop = asyncio.get_running_loop()
                # 如果已经在事件循环中，使用线程池执行
                import concurrent.futures
                
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(self.get_cookies_async())
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    return future.result(timeout=60)
                    
            except RuntimeError:
                # 没有运行的事件循环，可以直接创建新的
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(self.get_cookies_async())
                finally:
                    loop.close()
        except Exception as e:
            logger.error(f"获取cookies失败: {e}")
            return ""

def get_login_cookies(username="12345", password="kongqy") -> str:
    """
    便捷函数：获取登录cookies
    
    Args:
        username: 登录用户名，默认为"12345"
        password: 登录密码，默认为"kongqy"
    
    Returns:
        str: 格式化的cookie字符串，失败时返回空字符串
    """
    service = SimpleLoginService(username, password)
    return service.get_cookies()

if __name__ == "__main__":
    print("=" * 50)
    print("简单无头浏览器登录演示")
    print("=" * 50)
    
    # 检查依赖
    try:
        import playwright
        print("✅ Playwright已安装")
    except ImportError:
        print("❌ 请先安装Playwright: pip install playwright")
        print("❌ 然后安装浏览器: playwright install chromium")
        exit(1)
    
    print(f"开始时间: {datetime.now()}")
    print()
    
    # 获取cookies
    start_time = datetime.now()
    cookies = get_login_cookies()
    end_time = datetime.now()
    
    duration = (end_time - start_time).total_seconds()
    
    if cookies:
        print(f"✅ 登录成功！耗时: {duration:.2f}秒")
        print(f"获取的cookies:")
        print(cookies)
        print(f"\ncookies长度: {len(cookies)}字符")
        
        # 保存到文件
        with open('cookies.txt', 'w', encoding='utf-8') as f:
            f.write(cookies)
        print("\n✅ cookies已保存到 cookies.txt 文件")
        
    else:
        print(f"❌ 登录失败！耗时: {duration:.2f}秒")
        print("请检查:")
        print("- 网络连接")
        print("- 登录凭据")
        print("- Playwright安装")
    
    print("\n=" * 50)
    print("演示完成")
    print("=" * 50)