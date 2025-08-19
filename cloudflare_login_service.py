#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloudflare登录服务 - 使用CloudflareBypassBrowser替代Playwright实现登录功能

功能：
- 使用CloudflareBypassBrowser绕过Cloudflare防护
- 实现用户登录并获取认证cookies
- 提供cookie缓存机制
- 包含完善的错误处理和日志记录
- 保持与PlaywrightLoginService相同的接口
"""

import json
import time
import logging
from datetime import datetime
from typing import Optional, Dict, List
# 直接导入DrissionPage，避免复杂的依赖问题
from DrissionPage import ChromiumPage, ChromiumOptions
from pathlib import Path
import random

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CloudflareLoginService:
    """
    使用DrissionPage实现的登录服务
    替代PlaywrightLoginService，绕过Cloudflare防护
    """
    
    def __init__(self, username: str = "12345", password: str = "kongqy", 
                 base_url: str = "https://123av.com", cache_duration: int = 3600):
        """
        初始化CloudflareLoginService
        
        Args:
            username: 登录用户名
            password: 登录密码
            base_url: 基础URL
            cache_duration: cookie缓存时长（秒）
        """
        self.username = username
        self.password = password
        self.base_url = base_url
        self.cache_duration = cache_duration
        self.cached_cookies = None
        self.cache_timestamp = None
        self.page = None
        
        logger.info(f"CloudflareLoginService初始化完成，目标网站: {base_url}")
        
    def _init_browser(self):
        """初始化浏览器"""
        if self.page is None:
            try:
                # 创建浏览器配置
                co = ChromiumOptions()
                
                # 配置无头模式
                co.headless()
                
                # 创建用户数据目录
                user_data_dir = Path.home() / ".cache" / "cloudflare_login_browser"
                user_data_dir.mkdir(parents=True, exist_ok=True)
                co.user_data_dir = str(user_data_dir)
                
                # 禁用图片加载
                co.no_imgs = True
                
                # 设置超时
                co.page_load_timeout = 30
                co.script_timeout = 30
                co.connection_timeout = 10
                
                # 随机用户代理
                user_agents = [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                ]
                co.user_agent = random.choice(user_agents)
                
                # 反检测参数
                args = [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-infobars',
                    '--disable-extensions',
                    '--no-sandbox',
                    '--disable-gpu',
                    '--disable-notifications',
                ]
                for arg in args:
                    co.set_argument(arg)
                
                # 初始化页面
                self.page = ChromiumPage(co)
                
                # 应用反检测JS
                self._apply_stealth_js()
                
                logger.info("DrissionPage浏览器初始化成功")
                
            except Exception as e:
                logger.error(f"初始化浏览器失败: {e}")
                raise
    
    def _apply_stealth_js(self):
        """应用反检测JavaScript"""
        if not self.page:
            return
            
        try:
            # 修改 navigator.webdriver
            self.page.run_js("""
            try {
                Object.defineProperty(navigator, 'webdriver', {
                    get: function() { return false; }
                });
            } catch(e) {}
            """)
            
            # 修改其他属性
            self.page.run_js("""
            try {
                if (navigator.plugins && navigator.plugins.length === 0) {
                    Object.defineProperty(navigator, 'plugins', {
                        get: function() { return [1, 2, 3, 4, 5]; }
                    });
                }
                if (navigator.languages && navigator.languages.length === 0) {
                    Object.defineProperty(navigator, 'languages', {
                        get: function() { return ['zh-CN', 'zh', 'en-US', 'en']; }
                    });
                }
            } catch(e) {}
            """)
            
            logger.debug("反检测JS脚本注入成功")
        except Exception as e:
            logger.warning(f"注入反检测JS脚本失败: {e}")
    
    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self.cached_cookies or not hasattr(self, 'cache_timestamp'):
            return False
        
        current_time = time.time()
        return (current_time - self.cache_timestamp) < self.cache_duration
    
    def _is_cloudflare_challenge(self) -> bool:
        """检测是否有Cloudflare挑战"""
        if not self.page:
            return False
            
        try:
            # 检查标题
            title = self.page.run_js("return document.title;")
            if title and ('Cloudflare' in title or '安全检查' in title):
                return True
                
            # 检查页面内容
            content_check = """
            return {
                'hasCloudflareCaptcha': !!document.querySelector('#challenge-form') || 
                                        !!document.querySelector('#cf-hcaptcha') ||
                                        !!document.querySelector('#cf-spinner'),
                'hasCloudflareText': document.body && (
                    document.body.textContent.includes('Cloudflare') ||
                    document.body.textContent.includes('检查站点连接是否安全')
                )
            };
            """
            
            result = self.page.run_js(content_check)
            return result.get('hasCloudflareCaptcha', False) or result.get('hasCloudflareText', False)
            
        except Exception as e:
            logger.warning(f"检查Cloudflare挑战时出错: {e}")
            return False
    
    def _wait_for_cloudflare_challenge(self, max_wait: int = 30) -> bool:
        """等待Cloudflare挑战完成"""
        start_time = time.time()
        while time.time() - start_time < max_wait:
            if not self._is_cloudflare_challenge():
                logger.info("Cloudflare挑战已通过")
                time.sleep(2)  # 额外等待确保页面加载完成
                return True
            logger.info("等待Cloudflare挑战通过...")
            time.sleep(2)
        
        logger.warning("Cloudflare挑战等待超时")
        return False
    
    def login(self) -> Optional[str]:
        """执行登录并返回cookie字符串"""
        try:
            # 检查缓存
            if self._is_cache_valid():
                logger.info("使用缓存的cookies")
                return self.cached_cookies if isinstance(self.cached_cookies, str) else self._format_cookies(self.cached_cookies)
            
            logger.info("缓存已过期或不存在，开始登录流程")
            
            # 执行登录
            cookies = self._perform_login()
            if cookies:
                cookie_string = self._format_cookies(cookies)
                
                # 缓存cookies
                self.cached_cookies = cookies
                self.cache_timestamp = time.time()
                
                logger.info(f"登录成功，获取到 {len(cookies)} 个cookies")
                logger.info(f"Cookie缓存将在 {datetime.fromtimestamp(self.cache_timestamp + self.cache_duration)} 过期")
                
                return cookie_string
            else:
                logger.error("登录失败")
                return None
                
        except Exception as e:
            logger.error(f"登录过程中发生错误: {e}")
            return None
    
    def get_auth_cookies(self, force_refresh: bool = False) -> str:
        """获取认证cookies"""
        try:
            if force_refresh:
                logger.info("强制刷新cookies")
                self.invalidate_cookie_cache()
            
            # 执行登录
            cookie_string = self.login()
            if cookie_string:
                logger.info(f"获取到cookies: {cookie_string[:100]}...")
                return cookie_string
            else:
                logger.error("获取cookies失败")
                return ""
                
        except Exception as e:
            logger.error(f"获取认证cookies时发生错误: {e}")
            return ""
    
    def invalidate_cookie_cache(self):
        """使cookie缓存失效"""
        self.cached_cookies = None
        if hasattr(self, 'cache_timestamp'):
            delattr(self, 'cache_timestamp')
        logger.info("Cookie缓存已失效")
    
    def _format_cookies(self, cookies) -> str:
        """格式化cookies为HTTP头格式"""
        if not cookies:
            return ""
        
        cookie_pairs = []
        
        # 处理不同格式的cookies
        if isinstance(cookies, dict):
            # 如果cookies是字典格式
            for name, value in cookies.items():
                cookie_pairs.append(f"{name}={value}")
        elif isinstance(cookies, list):
            # 如果cookies是列表格式
            for cookie in cookies:
                if isinstance(cookie, dict):
                    name = cookie.get('name', '')
                    value = cookie.get('value', '')
                    if name:
                        cookie_pairs.append(f"{name}={value}")
                else:
                    # 如果是字符串格式
                    cookie_pairs.append(str(cookie))
        else:
            logger.warning(f"未知的cookies格式: {type(cookies)}")
            return str(cookies) if cookies else ""
        
        return "; ".join(cookie_pairs)
    
    def format_cookies_for_http_header(self, cookies) -> str:
        """格式化cookies为HTTP头格式（与PlaywrightLoginService保持一致）"""
        if not cookies:
            return ""
        
        # 如果已经是字符串格式，直接返回
        if isinstance(cookies, str):
            return cookies
            
        # 否则使用_format_cookies方法
        return self._format_cookies(cookies)
    
    def _perform_login(self) -> Optional[Dict]:
        """执行登录操作"""
        try:
            self._init_browser()
            
            # 先访问主页获取基础cookies
            main_url = f"{self.base_url}/ja"
            logger.info(f"访问主页获取基础cookies: {main_url}")
            self.page.get(main_url, timeout=30)
            
            # 检查Cloudflare挑战
            if self._is_cloudflare_challenge():
                logger.info("检测到Cloudflare挑战，等待解决...")
                if not self._wait_for_cloudflare_challenge():
                    logger.error("Cloudflare挑战解决失败")
                    return None
            
            # 等待页面加载
            time.sleep(2)
            
            # 使用API端点进行登录（与PlaywrightLoginService保持一致）
            login_data = {
                "username": self.username,
                "password": self.password,
                "remember_me": 1
            }
            
            api_url = f"{self.base_url}/ja/ajax/user/signin"
            logger.info(f"使用API端点登录: {api_url}")
            
            # 使用传统的XMLHttpRequest进行登录请求
            login_data_json = json.dumps(login_data)
            js_code = f"""
            var xhr = new XMLHttpRequest();
            xhr.open('POST', '/ja/ajax/user/signin', false);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.setRequestHeader('Accept', 'application/json, text/plain, */*');
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            xhr.setRequestHeader('Cache-Control', 'no-cache');
            xhr.setRequestHeader('Pragma', 'no-cache');
            
            try {{
                xhr.send('{login_data_json}');
                return {{
                    status: xhr.status,
                    text: xhr.responseText
                }};
            }} catch (error) {{
                return {{
                    status: 0,
                    text: 'Error: ' + error.message
                }};
            }}
            """
            
            # 执行JavaScript登录请求
            try:
                result = self.page.run_js(js_code)
                if result is None:
                    logger.error("JavaScript执行返回None")
                    return None
                    
                logger.info(f"登录API响应状态: {result.get('status', 'unknown')}")
                logger.info(f"登录API响应内容: {result.get('text', 'no response')}")
                
                if result.get('status') == 200:
                    # 检查响应内容是否包含错误信息
                    try:
                        response_data = json.loads(result.get('text', '{}'))
                        if 'errors' in response_data and response_data['errors']:
                            logger.error(f"API登录失败: {response_data['errors']}")
                            return None
                        else:
                            logger.info("API登录成功")
                    except json.JSONDecodeError:
                        logger.info("API登录成功 (无法解析JSON响应)")
                    
                    # 等待cookies更新
                    time.sleep(2)
                    
                    # 获取cookies
                    cookies = self.page.cookies()
                    if cookies:
                        # 如果cookies是列表格式，转换为字典格式
                        if isinstance(cookies, list):
                            cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                        else:
                            cookies_dict = cookies
                        
                        logger.info(f"登录成功，获取到 {len(cookies_dict)} 个cookies")
                        return cookies_dict
                    else:
                        logger.error("登录后未获取到cookies")
                        return None
                else:
                    logger.warning(f"API登录失败，状态码: {result.get('status')}")
                    return None
                    
            except Exception as js_error:
                logger.error(f"执行JavaScript登录请求时出错: {js_error}")
                return None
                
        except Exception as e:
            logger.error(f"登录过程中出错: {e}")
            return None
        finally:
            if self.page:
                try:
                    self.page.quit()
                except:
                    pass
                self.page = None
    
    def get_cookies(self) -> Optional[Dict]:
        """获取登录cookies（同步版本）"""
        # 检查缓存
        if self._is_cache_valid():
            logger.info("使用缓存的cookies")
            return self.cached_cookies
        
        # 执行登录
        logger.info("缓存已过期或不存在，开始登录")
        cookies = self._perform_login()
        
        if cookies:
            # 更新缓存
            self.cached_cookies = cookies
            self.cache_timestamp = time.time()
            logger.info(f"登录成功，cookies已缓存，有效期: {self.cache_duration}秒")
            return cookies
        else:
            logger.error("登录失败")
            return None
    
    async def get_cookies_async(self) -> Optional[Dict]:
        """获取登录cookies（异步版本）"""
        # 在线程池中执行同步操作
        import asyncio
        import concurrent.futures
        
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(executor, self.get_cookies)
    
    def clear_cache(self):
        """清除缓存的cookies"""
        self.cached_cookies = None
        self.cache_timestamp = None
        logger.info("cookies缓存已清除")
    
    def format_cookies_for_http_header(self, cookies) -> str:
        """格式化cookies为HTTP头格式"""
        if not cookies:
            return ""
        
        cookie_pairs = []
        
        # 处理不同格式的cookies
        if isinstance(cookies, dict):
            # 如果cookies是字典格式
            for name, value in cookies.items():
                cookie_pairs.append(f"{name}={value}")
        elif isinstance(cookies, list):
            # 如果cookies是列表格式
            for cookie in cookies:
                if isinstance(cookie, dict):
                    name = cookie.get('name', '')
                    value = cookie.get('value', '')
                    if name:
                        cookie_pairs.append(f"{name}={value}")
                else:
                    # 如果是字符串格式
                    cookie_pairs.append(str(cookie))
        else:
            logger.warning(f"未知的cookies格式: {type(cookies)}")
            return str(cookies) if cookies else ""
        
        return "; ".join(cookie_pairs)
    
    def close(self):
        """关闭浏览器资源"""
        if self.page:
            try:
                self.page.quit()
                self.page = None
                logger.info("DrissionPage浏览器已关闭")
            except Exception as e:
                logger.error(f"关闭浏览器时出错: {e}")
    
    def __del__(self):
        """析构函数，确保浏览器资源被释放"""
        if self.page:
            try:
                self.page.quit()
            except:
                pass

# 测试函数
def test_cloudflare_login():
    """测试CloudflareLoginService功能"""
    print("=" * 60)
    print("开始测试CloudflareLoginService登录服务")
    print("=" * 60)
    
    try:
        # 创建CloudflareLoginService实例
        login_service = CloudflareLoginService()
        
        print(f"登录配置:")
        print(f"  - 网站: {login_service.base_url}")
        print(f"  - 用户名: {login_service.username}")
        print(f"  - 密码: {'*' * len(login_service.password)}")
        print(f"  - 缓存时长: {login_service.cache_duration}秒")
        print()
        
        # 测试登录
        print("🔐 开始登录...")
        start_time = time.time()
        
        cookies = login_service.get_auth_cookies()
        
        end_time = time.time()
        duration = end_time - start_time
        
        if cookies:
            print(f"✅ 登录成功! (耗时: {duration:.2f}秒)")
            print(f"📋 获取的cookies: {cookies[:100]}..." if len(cookies) > 100 else f"📋 获取的cookies: {cookies}")
            
            # 测试缓存功能
            print("\n🔄 测试cookie缓存功能...")
            cached_cookies = login_service.get_auth_cookies()
            if cached_cookies == cookies:
                print("✅ Cookie缓存功能正常")
            else:
                print("❌ Cookie缓存功能异常")
            
            # 测试强制刷新
            print("\n🔄 测试强制刷新功能...")
            refreshed_cookies = login_service.get_auth_cookies(force_refresh=True)
            if refreshed_cookies:
                print("✅ 强制刷新功能正常")
            else:
                print("❌ 强制刷新功能异常")
                
        else:
            print(f"❌ 登录失败! (耗时: {duration:.2f}秒)")
            print("\n可能的原因:")
            print("  - 网络连接问题")
            print("  - 登录凭据错误")
            print("  - 网站登录接口变更")
            print("  - Cloudflare防护机制")
            
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        print(f"❌ 测试失败: {e}")
        print("\n可能的解决方案:")
        print("  - 检查网络连接")
        print("  - 验证登录凭据")
        print("  - 检查DrissionPage依赖")
        print("  - 查看详细日志")
    
    finally:
        # 清理资源
        try:
            login_service.close()
        except:
            pass

if __name__ == "__main__":
    test_cloudflare_login()