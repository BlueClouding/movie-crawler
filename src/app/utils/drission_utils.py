"""
Utilities for using DrissionPage to bypass Cloudflare detection.

DrissionPage 是一个结合了浏览器与请求的自动化工具，能有效绕过 Cloudflare 保护。
"""
import os
import time
import random
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions


class CloudflareBypassBrowser:
    """
    使用 DrissionPage 绕过 Cloudflare 检测的浏览器类
    
    DrissionPage 结合了真实浏览器与请求的能力，可有效绕过反爬措施
    """
    
    def __init__(
        self,
        headless: bool = False,
        user_data_dir: Optional[str] = None,
        proxy: Optional[str] = None,
        load_images: bool = True,
        timeout: int = 30
    ):
        """
        初始化 CloudflareBypassBrowser

        Args:
            headless: 是否以无头模式运行
            user_data_dir: 用户数据目录路径，用于持久化会话
            proxy: 代理服务器地址，如 "http://127.0.0.1:7890"
            load_images: 是否加载图片
            timeout: 默认超时时间（秒）
        """
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.proxy = proxy
        self.load_images = load_images
        self.timeout = timeout
        self.page = None
        self._cf_challenge_solved = False  # 标记是否已经解决了Cloudflare挑战
        self._last_html = None  # 缓存最后一次获取的HTML
        
        # 立即初始化浏览器
        self._init_browser()
    
    def _init_browser(self):
        """初始化浏览器配置并启动"""
        try:
            # 创建浏览器配置
            co = ChromiumOptions()
            
            # 配置显示模式（headless）
            # DrissionPage 中使用 headless 参数而不是 visible
            co.headless = self.headless
            
            # 用户数据目录配置
            if self.user_data_dir:
                data_dir = Path(self.user_data_dir)
                data_dir.mkdir(parents=True, exist_ok=True)
                # 使用用户数据目录
                co.user_data_dir = str(data_dir)
            
            # 代理设置
            if self.proxy:
                # 直接设置代理属性
                co.proxy = self.proxy
            
            # 图片加载设置
            if not self.load_images:
                co.no_imgs = True
            
            # 设置超时
            co.page_load_timeout = self.timeout
            co.script_timeout = self.timeout
            co.connection_timeout = 10
            
            # 随机用户代理
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
            ]
            # 直接设置用户代理
            co.user_agent = random.choice(user_agents)
            
            # 反检测相关的参数
            args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--disable-extensions',
                '--no-sandbox',
                '--disable-gpu',
            ]
            # 使用 set_argument 添加参数
            for arg in args:
                co.set_argument(arg)
            
            # 在DrissionPage中直接使用CDP命令来避免检测
            # 我们将在浏览器初始化后注入反检测JavaScript
            
            # 浏览器偏好使用参数设置
            # 禁用通知
            co.set_argument('--disable-notifications')
            # 禁用密码保存
            co.set_argument('--password-store=basic')
            
            # 初始化浏览器
            self.page = ChromiumPage(co)
            
            # 使用 JavaScript 进一步隐藏自动化特征
            self._apply_stealth_js()
            
            logger.info("DrissionPage浏览器初始化成功")
            
        except Exception as e:
            logger.error(f"DrissionPage浏览器初始化失败: {e}")
            if self.page:
                try:
                    self.page.quit()
                except:
                    pass
            raise
    
    def _apply_stealth_js(self):
        """应用额外的JS脚本来增强隐身效果"""
        if not self.page:
            return
            
        # 给浏览器注入反检测 JavaScript
        stealth_js = """
        // 修改 navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false,
        });
        
        // 修改 navigator.plugins
        if (navigator.plugins.length === 0) {
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        }
        
        // 修改 navigator.languages
        if (navigator.languages.length === 0) {
            Object.defineProperty(navigator, 'languages', {
                get: () => ['zh-CN', 'zh', 'en-US', 'en'],
            });
        }
        
        // 移除 Automation Controller 属性
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        """
        
        try:
            self.page.run_js(stealth_js)
            logger.debug("注入了反检测JS脚本")
        except Exception as e:
            logger.warning(f"注入反检测JS脚本失败: {e}")
    
    def get(self, url: str, wait_for_cf: bool = False, timeout: int = 30, wait_for_full_load: bool = False, dom_ready_timeout: int = 5) -> bool:
        """
        打开URL并处理Cloudflare挑战
        
        Args:
            url: 要访问的URL
            wait_for_cf: 是否等待Cloudflare挑战完成
            timeout: 访问超时时间（秒）
            wait_for_full_load: 是否等待页面完全加载，默认为False只等待DOM就绪
            dom_ready_timeout: DOM就绪等待超时时间（秒），默认5秒
        
        Returns:
            是否成功打开页面
        """
        if not self.page:
            return False
            
        try:
            logger.info(f"正在访问: {url}")
            # 如果已经解决了Cloudflare挑战，可以使用更激进的优化
            if self._cf_challenge_solved and not wait_for_full_load:
                # 已经通过了Cloudflare挑战，可以使用更激进的优化
                try:
                    # 在页面加载前设置拦截器来阻止不必要的资源加载
                    self.page.run_js("""
                    // 在页面开始加载前设置拦截器
                    window.addEventListener('beforeunload', function() {
                        // 设置拦截器禁用图片、CSS等资源加载
                        var originalOpen = XMLHttpRequest.prototype.open;
                        XMLHttpRequest.prototype.open = function() {
                            if (arguments[1] && (
                                arguments[1].endsWith('.jpg') || 
                                arguments[1].endsWith('.png') || 
                                arguments[1].endsWith('.gif') || 
                                arguments[1].endsWith('.css') || 
                                arguments[1].endsWith('.woff') || 
                                arguments[1].endsWith('.woff2')
                            )) {
                                // 阻止加载这些资源
                                return;
                            }
                            return originalOpen.apply(this, arguments);
                        };
                    });
                    """)
                except Exception as e:
                    logger.warning(f"设置资源拦截失败: {e}")
            elif not wait_for_full_load:
                # 首次访问时不要过度优化，可能影响Cloudflare检测
                try:
                    # 使用较温和的方式禁用图片和其他资源加载
                    self.page.run_js("""
                    // 在DOM加载后清除不必要的资源
                    document.addEventListener('DOMContentLoaded', function() {
                        // 延迟执行以避免影响Cloudflare检测
                        setTimeout(function() {
                            var images = document.getElementsByTagName('img');
                            for (var i = 0; i < images.length; i++) {
                                images[i].loading = 'lazy';
                            }
                        }, 1000);
                    });
                    """)
                except Exception as e:
                    logger.warning(f"禁用资源加载失败: {e}")
            
            # 根据是否已解决Cloudflare挑战来决定超时时间
            if self._cf_challenge_solved:
                # 已通过挑战，可以使用更短的超时
                actual_timeout = min(dom_ready_timeout, timeout) if not wait_for_full_load else timeout
            else:
                # 首次访问或未通过挑战，给予更长的超时时间
                actual_timeout = timeout
                
            # 访问页面
            self.page.get(url, timeout=actual_timeout)
            
            # 如果不需要等待完全加载，在DOM就绪后立即停止加载
            if not wait_for_full_load:
                # 检查DOM是否已就绪
                is_ready = self.page.run_js('return document.readyState !== "loading"')
                
                if not is_ready:
                    # 如果DOM还没有就绪，等待一个短暂停
                    time.sleep(0.5)
                
                # 停止加载其他资源
                self.page.run_js('window.stop()')
                
                # 清除不必要的资源
                try:
                    self.page.run_js("""
                    // 清除不必要的资源以加快渲染
                    (function() {
                        // 清除图片
                        var imgs = document.querySelectorAll('img');
                        for (var i = 0; i < imgs.length; i++) {
                            if (imgs[i].src && !imgs[i]._originalSrc) {
                                imgs[i]._originalSrc = imgs[i].src;
                                imgs[i].src = '';
                            }
                        }
                        
                        // 清除所有iframe
                        var frames = document.querySelectorAll('iframe');
                        for (var i = 0; i < frames.length; i++) {
                            if (frames[i].src) {
                                frames[i].src = 'about:blank';
                            }
                        }
                        
                        // 禁用未加载的脚本
                        var scripts = document.querySelectorAll('script[src]:not([loaded])');
                        for (var i = 0; i < scripts.length; i++) {
                            scripts[i].src = '';
                        }
                    })();
                    """)
                except Exception as e:
                    logger.warning(f"清除资源失败: {e}")
            
            # 检查是否遇到Cloudflare挑战
            if self._is_cloudflare_challenge():
                logger.info("检测到 Cloudflare 挑战，等待解决中...")
                
                if wait_for_cf:
                    # 等待解决Cloudflare挑战
                    if not self._wait_for_cloudflare_challenge():
                        logger.warning("等待解决Cloudflare挑战失败")
                        return False
                    else:
                        # 标记已经解决了Cloudflare挑战
                        self._cf_challenge_solved = True
                        logger.info("已成功解决Cloudflare挑战")
                else:
                    # 不等待，直接返回失败
                    logger.warning("遇到Cloudflare挑战，但未设置等待")
                    return False
            
            # 检查页面内容是否正常加载
            html = self.get_html()
            if html and len(html) > 100:  # 降低判断标准，只要有一些内容就认为成功
                return True
            else:
                logger.warning("页面内容异常或为空")
                return False
                
        except Exception as e:
            logger.error(f"访问 {url} 时出错: {str(e)}")
            # 即使出错也返回true，允许用户手动解决
            return True
    
    def _is_cloudflare_challenge(self) -> bool:
        """
        检查当前页面是否显示 Cloudflare 挑战

        Returns:
            bool: 如果检测到 Cloudflare 挑战则返回 True
        """
        if not self.page:
            return False
            
        try:
            # 获取页面内容
            html = self.page.html.lower()
            title = self.page.title.lower() if self.page.title else ""
            
            # Cloudflare 挑战的典型特征
            cf_indicators = [
                'cloudflare',
                'checking your browser',
                'just a moment',
                'please wait',
                'security check',
                'please turn javascript on',
                'challenge-running',
                'cf-challenge',
                'cf_chl',
                'ray id'
            ]
            
            # 检查页面内容
            for indicator in cf_indicators:
                if indicator in html or indicator in title:
                    return True
                    
            # 检查特定元素
            cf_elements = [
                '//h1[contains(text(), "Checking your browser")]',
                '//h1[contains(text(), "Just a moment")]',
                '//div[contains(@class, "cf-browser-verification")]',
                '//div[contains(@id, "cf-")]',
                '//iframe[@id="cf-chl-widget"]'
            ]
            
            for xpath in cf_elements:
                try:
                    if self.page.ele(xpath, timeout=0.5):
                        return True
                except:
                    continue
                    
            return False
            
        except Exception as e:
            logger.warning(f"检查 Cloudflare 挑战时出错: {e}")
            return False
    
    def _wait_for_cloudflare(self, max_wait: int = 60):
        """
        等待 Cloudflare 挑战完成

        Args:
            max_wait: 最大等待时间（秒），默认60秒

        Returns:
            bool: 是否成功通过挑战
        """
        return self._wait_for_cloudflare_challenge(max_wait)
        
    def _wait_for_cloudflare_challenge(self, max_wait: int = 60):
        """
        等待 Cloudflare 挑战完成

        Args:
            max_wait: 最大等待时间（秒），默认60秒

        Returns:
            bool: 是否成功通过挑战
        """
        start_time = time.time()
        logger.info(f"等待通过 Cloudflare 挑战，最多等待 {max_wait} 秒...")
        
        while time.time() - start_time < max_wait:
            # 检查是否仍在 Cloudflare 挑战页面
            if not self._is_cloudflare_challenge():
                logger.info("已通过 Cloudflare 挑战！")
                return True
                
            # 等待一会儿再检查
            time.sleep(2)
            
        logger.warning(f"等待 {max_wait} 秒后仍未通过 Cloudflare 挑战")
        return False
    
    def get_html(self):
        """
        获取当前页面的 HTML 内容

        Returns:
            str: HTML 内容
        """
        if not self.page:
            return ""
        
        # 获取并缓存HTML内容
        self._last_html = self.page.html
        return self._last_html
        
    @property
    def html(self):
        """
        HTML属性，兼容性支持，返回当前页面的HTML内容
        
        Returns:
            str: HTML内容
        """
        # 如果有缓存的HTML且不为空，则返回缓存
        if self._last_html:
            return self._last_html
        # 否则重新获取
        return self.get_html()
    
    def get_cookies(self) -> Dict:
        """
        获取当前页面的所有 cookies

        Returns:
            Dict: cookies 字典
        """
        if not self.page:
            return {}
        return self.page.get_cookies()
    
    def set_cookies(self, cookies: Union[Dict, List[Dict]]):
        """
        设置 cookies

        Args:
            cookies: 要设置的 cookies，可以是字典或字典列表
        """
        if not self.page:
            return
            
        if isinstance(cookies, dict):
            for name, value in cookies.items():
                self.page.set_cookies({name: value})
        elif isinstance(cookies, list):
            for cookie in cookies:
                self.page.set_cookies(cookie)
    
    def find_element(self, selector: str, timeout: int = 10):
        """
        查找页面元素

        Args:
            selector: 选择器（CSS 或 XPath）
            timeout: 超时时间（秒）

        Returns:
            找到的元素或 None
        """
        if not self.page:
            return None
            
        try:
            return self.page.ele(selector, timeout=timeout)
        except Exception as e:
            logger.debug(f"未找到元素 {selector}: {e}")
            return None
    
    def find_elements(self, selector: str, timeout: int = 10):
        """
        查找多个页面元素

        Args:
            selector: 选择器（CSS 或 XPath）
            timeout: 超时时间（秒）

        Returns:
            元素列表
        """
        if not self.page:
            return []
            
        try:
            return self.page.eles(selector, timeout=timeout)
        except Exception as e:
            logger.debug(f"未找到元素 {selector}: {e}")
            return []
    
    def scroll_to_bottom(self):
        """
        滚动到页面底部
        """
        if not self.page:
            return
            
        try:
            self.page.run_js("window.scrollTo(0, document.body.scrollHeight);")            
        except Exception as e:
            logger.error(f"滚动失败: {e}")
    
    def scroll_by(self, y_offset: int = 500):
        """
        页面垂直滚动

        Args:
            y_offset: 垂直滚动像素
        """
        if not self.page:
            return
            
        try:
            self.page.run_js(f"window.scrollBy(0, {y_offset});")            
        except Exception as e:
            logger.error(f"滚动失败: {e}")
    
    def wait(self, seconds: float):
        """
        等待指定秒数

        Args:
            seconds: 等待秒数
        """
        time.sleep(seconds)
    
    def close(self):
        """
        关闭浏览器并释放资源
        """
        if self.page:
            try:
                self.page.quit()
                logger.info("浏览器已关闭")
            except Exception as e:
                logger.error(f"关闭浏览器时出错: {e}")
            finally:
                self.page = None


def test_cloudflare_bypass(url: str = "https://missav.ai/ja"):
    """
    测试绕过 Cloudflare 的能力
    
    Args:
        url: 要测试的网址，最好是受 Cloudflare 保护的
    """
    # 创建用户数据目录
    user_data_dir = Path.home() / ".cache" / "cf_bypass_browser"
    user_data_dir.mkdir(parents=True, exist_ok=True)
    
    # 初始化浏览器
    browser = CloudflareBypassBrowser(
        headless=False,  # 显示浏览器便于调试
        user_data_dir=str(user_data_dir),
        load_images=False  # 不加载图片，提高速度
    )
    
    try:
        # 访问网站
        success = browser.get(url)
        
        if success:
            # 获取页面内容
            html = browser.get_html()
            print(f"成功加载页面！内容长度: {len(html)} 字节")
            
            # 获取页面标题
            title_element = browser.find_element("//title")
            if title_element:
                print(f"页面标题: {title_element.text}")
                
            # 尝试查找一些内容
            content_elements = browser.find_elements("//h1 | //h2 | //h3")
            if content_elements:
                print("\n页面内容摘要:")
                for i, element in enumerate(content_elements[:5]):
                    print(f"  {i+1}. {element.text.strip()}")
            
            # 获取 cookies
            cookies = browser.get_cookies()
            cf_cookies = {k: v for k, v in cookies.items() if 'cf_' in k}
            if cf_cookies:
                print("\nCloudflare Cookies:")
                for name, value in cf_cookies.items():
                    print(f"  {name}: {value[:10]}...")
            
        else:
            print("加载页面失败，可能是 Cloudflare 检测或其他问题")
            
    finally:
        # 等待一会儿再关闭浏览器
        browser.wait(2)
        browser.close()


if __name__ == "__main__":
    # 测试在受 Cloudflare 保护的网站上的表现
    test_cloudflare_bypass()
