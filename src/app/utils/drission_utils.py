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
        timeout: int = 60,
        wait_after_cf: int = 5
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
        self.wait_after_cf = wait_after_cf  # Cloudflare挑战后的额外等待时间
        self.page = None
        self._cf_challenge_solved = False  # 标记是否已经解决了Cloudflare挑战
        self._last_html = None  # 缓存最后一次获取的HTML
        self.wait = self  # 添加wait属性指向self，使browser.wait可用
        
        # 立即初始化浏览器
        self._init_browser()
    
    def _init_browser(self):
        """初始化浏览器配置并启动"""
        try:
            # 创建浏览器配置
            co = ChromiumOptions()
            
            # 配置显示模式（headless）
            # DrissionPage 中使用 headless() 方法设置无头模式
            if self.headless:
                co.headless()  # 启用无头模式
            
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
            
            # 设置超时（降低以提高效率）
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
            
        # 分段注入反检测JavaScript，提高成功率
        try:
            # 1. 修改 navigator.webdriver (最关键的属性)
            self.page.run_js("""
            try {
                Object.defineProperty(navigator, 'webdriver', {
                    get: function() { return false; }
                });
                console.log('Successfully modified navigator.webdriver');
            } catch(e) { console.error('Failed to modify webdriver:', e); }
            """)
            
            # 2. 修改 navigator.plugins
            self.page.run_js("""
            try {
                if (navigator.plugins && navigator.plugins.length === 0) {
                    Object.defineProperty(navigator, 'plugins', {
                        get: function() { return [1, 2, 3, 4, 5]; }
                    });
                    console.log('Successfully modified navigator.plugins');
                }
            } catch(e) { console.error('Failed to modify plugins:', e); }
            """)
            
            # 3. 修改 navigator.languages
            self.page.run_js("""
            try {
                if (navigator.languages && navigator.languages.length === 0) {
                    Object.defineProperty(navigator, 'languages', {
                        get: function() { return ['zh-CN', 'zh', 'en-US', 'en']; }
                    });
                    console.log('Successfully modified navigator.languages');
                }
            } catch(e) { console.error('Failed to modify languages:', e); }
            """)
            
            # 4. 移除 Automation Controller 属性 (安全地)
            self.page.run_js("""
            try {
                if (window.cdc_adoQpoasnfa76pfcZLmcfl_Array) {
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                }
                if (window.cdc_adoQpoasnfa76pfcZLmcfl_Promise) {
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                }
                if (window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol) {
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                }
                console.log('Successfully removed automation properties');
            } catch(e) { console.error('Failed to remove automation properties:', e); }
            """)
            
            logger.debug("成功注入反检测JS脚本")
        except Exception as e:
            logger.warning(f"注入反检测JS脚本失败: {e}")
            # 即使注入失败，也继续执行，不要中断程序
    
    def get(self, url: str, wait_for_cf: bool = True, timeout: int = 60, wait_for_full_load: bool = True, dom_ready_timeout: int = 10) -> bool:
        """
        打开URL并处理Cloudflare挑战
        
        Args:
            url: 要访问的URL
            wait_for_cf: 是否等待Cloudflare挑战完成
            timeout: 访问超时时间（秒）
            wait_for_full_load: 是否等待页面完全加载，默认为True
            dom_ready_timeout: DOM就绪等待超时时间（秒），默认10秒
        
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
            
            # 检查是否有 Cloudflare 挑战
            if self._is_cloudflare_challenge():
                logger.info("检测到 Cloudflare 挑战，等待解决中...")
                
                if wait_for_cf:
                    # 等待 Cloudflare 挑战完成
                    cf_passed = self._wait_for_cloudflare_challenge()
                    if not cf_passed:
                        logger.error("Cloudflare 挑战解决失败")
                        return False
                    logger.info("Cloudflare 挑战已解决，继续加载页面")
                else:
                    logger.warning("遇到Cloudflare挑战，但未设置等待")
                    return False
            
            # 页面加载完成后，添加随机延迟模拟人类浏览行为
            if not self._cf_challenge_solved:
                # 首次访问时添加更长的随机延迟
                browse_delay = random.uniform(2.0, 5.0)
                logger.debug(f"首次访问，模拟浏览行为等待 {browse_delay:.1f} 秒")
                time.sleep(browse_delay)
            else:
                # 已通过挑战的页面，添加较短的随机延迟
                browse_delay = random.uniform(1.0, 3.0)
                logger.debug(f"已通过挑战，快速浏览等待 {browse_delay:.1f} 秒")
                time.sleep(browse_delay)
            
            # 30%概率执行额外的人类行为模拟
            if random.random() < 0.3:
                logger.debug("执行额外的人类行为模拟")
                try:
                    # 简化版的人类行为模拟，避免过度延迟
                    scroll_action = random.choice([
                        "window.scrollBy(0, Math.random() * 100);",
                        "window.scrollTo(0, Math.random() * 200);"
                    ])
                    self.page.run_js(scroll_action)
                    time.sleep(random.uniform(0.5, 1.5))
                except Exception as e:
                    logger.debug(f"额外行为模拟失败: {e}")
            
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
    
    def run_js(self, script):
        """运行JavaScript脚本并返回结果
        
        Args:
            script: JavaScript脚本字符串
            
        Returns:
            执行结果
        """
        if not self.page:
            raise RuntimeError("浏览器尚未初始化")
        return self.page.run_js(script)
    
    def _is_cloudflare_challenge(self):
        """检测页面是否包含Cloudflare挑战
        
        Returns:
            bool: 如果检测到 Cloudflare 挑战则返回 True
        """
        if not self.page:
            return False
            
        try:
            # 先检查页面是否已经正确加载了主要内容
            # 如果页面已经加载了较多有效内容，则认为不需要等待Cloudflare
            content_loaded = """
            return {
                'validContent': !!document.querySelector('h1') && 
                               document.querySelectorAll('a').length > 20 &&
                               document.querySelectorAll('div').length > 50,
                'bodyLength': document.body ? document.body.innerHTML.length : 0,
                'hasMoviePanel': !!document.querySelector('.movie-info-panel') ||
                                !!document.querySelector('.grid-cols-2')
            };
            """
            
            content_status = self.page.run_js(content_loaded)
            # 如果页面内容已充分加载，不需要再等待Cloudflare挑战
            if (content_status.get('validContent', False) or 
                content_status.get('hasMoviePanel', False) or 
                content_status.get('bodyLength', 0) > 100000):
                logger.info("检测到页面已经包含完整内容，无需继续等待Cloudflare")
                return False
            
            # 检查标题是否包含 Cloudflare 相关内容
            title = self.page.run_js("return document.title;")
            if title and ('Cloudflare' in title or '安全检查' in title or 'Security Challenge' in title or 'チェックしています' in title):
                return True
                
            # 检查页面内容是否包含 Cloudflare 特征
            content_check = """
            return {
                'hasCloudflareCaptcha': !!document.querySelector('#challenge-form') || 
                                        !!document.querySelector('#cf-hcaptcha') ||
                                        !!document.querySelector('#cf-spinner') ||
                                        !!document.querySelector('[id*="cloudflare"]'),
                'hasCloudflareText': document.body && (
                    document.body.textContent.includes('Cloudflare') ||
                    document.body.textContent.includes('检查站点连接是否安全') ||
                    document.body.textContent.includes('Checking if the site connection is secure') ||
                    document.body.textContent.includes('セキュリティチェック')
                )
            };
            """
            
            result = self.page.run_js(content_check)
            return result.get('hasCloudflareCaptcha', False) or result.get('hasCloudflareText', False)
            
        except Exception as e:
            logger.warning(f"检查 Cloudflare 挑战时出错: {e}")
            return False
    
    def _wait_for_cloudflare_challenge(self, max_wait: int = 60):
        """
        等待 Cloudflare 挑战完成

        Args:
            max_wait: 最大等待时间（秒），默认60秒

        Returns:
            bool: 是否成功通过挑战
        """
        import random
        
        start_time = time.time()
        check_count = 0
        
        logger.info(f"开始等待 Cloudflare 挑战，最大等待时间: {max_wait}秒")
        
        while time.time() - start_time < max_wait:
            check_count += 1
            
            if not self._is_cloudflare_challenge():
                logger.info(f"Cloudflare 挑战已通过 (检查次数: {check_count})")
                self._cf_challenge_solved = True
                # 添加额外等待时间，确保页面完全加载
                logger.info(f"等待额外的 {self.wait_after_cf} 秒以确保内容加载完全")
                time.sleep(self.wait_after_cf)
                return True
            
            elapsed = int(time.time() - start_time)
            logger.info(f"等待 Cloudflare 挑战通过... (已等待: {elapsed}s/{max_wait}s, 检查次数: {check_count})")
            
            # 添加随机延迟，模拟人类行为
            base_wait = 2
            random_delay = random.uniform(0.5, 1.5)
            actual_wait = base_wait + random_delay
            
            # 20%概率添加额外的"阅读"延迟，模拟人类阅读行为
            if random.random() < 0.2:
                reading_delay = random.uniform(3, 8)
                logger.debug(f"模拟阅读行为，额外等待 {reading_delay:.1f} 秒")
                actual_wait += reading_delay
            
            time.sleep(actual_wait)
        
        # 挑战超时，尝试多级重试
        logger.warning(f"Cloudflare 挑战等待超时 ({max_wait}秒)，开始重试机制")
        return self._retry_cloudflare_challenge()
    
    def _retry_cloudflare_challenge(self, max_retries: int = 5) -> bool:
        """
        多级重试机制处理 Cloudflare 挑战
        基于成功案例优化的重试策略
        
        Args:
            max_retries: 最大重试次数，默认5次
            
        Returns:
            bool: 是否成功通过挑战
        """
        import random
        
        for retry_count in range(max_retries):
            logger.info(f"开始第 {retry_count + 1}/{max_retries} 次重试")
            
            try:
                # 策略1: 温和刷新页面
                if retry_count == 0:
                    logger.info("重试策略1: 温和刷新页面")
                    self.page.run_js("location.reload();")
                    wait_time = random.uniform(10, 15)
                    logger.info(f"等待页面加载 {wait_time:.1f} 秒")
                    time.sleep(wait_time)
                    
                # 策略2: 强制刷新页面
                elif retry_count == 1:
                    logger.info("重试策略2: 强制刷新页面")
                    self.page.run_js("location.reload(true);")
                    wait_time = random.uniform(12, 18)
                    logger.info(f"等待页面强制加载 {wait_time:.1f} 秒")
                    time.sleep(wait_time)
                    
                # 策略3: 清除缓存并刷新
                elif retry_count == 2:
                    logger.info("重试策略3: 清除缓存并刷新")
                    self.page.run_js("""
                        // 清除本地存储
                        try {
                            localStorage.clear();
                            sessionStorage.clear();
                        } catch(e) {
                            console.log('清除存储失败:', e);
                        }
                        // 强制刷新
                        location.reload(true);
                    """)
                    wait_time = random.uniform(15, 20)
                    logger.info(f"等待页面重新加载 {wait_time:.1f} 秒")
                    time.sleep(wait_time)
                    
                # 策略4: 模拟用户交互后刷新
                elif retry_count == 3:
                    logger.info("重试策略4: 模拟用户交互后刷新")
                    # 模拟人类行为
                    self._simulate_human_behavior()
                    # 刷新页面
                    self.page.run_js("location.reload(true);")
                    wait_time = random.uniform(18, 25)
                    logger.info(f"等待页面加载 {wait_time:.1f} 秒")
                    time.sleep(wait_time)
                    
                # 策略5: 浏览器重启（最后手段）
                else:
                    logger.info("重试策略5: 浏览器重启（最后手段）")
                    if self._restart_browser():
                        wait_time = random.uniform(20, 30)
                        logger.info(f"浏览器重启成功，等待 {wait_time:.1f} 秒")
                        time.sleep(wait_time)
                    else:
                        logger.error("浏览器重启失败")
                        continue
                
                # 检查是否通过挑战
                if not self._is_cloudflare_challenge():
                    logger.info(f"✅ 重试成功！第 {retry_count + 1} 次重试通过 Cloudflare 挑战")
                    self._cf_challenge_solved = True
                    # 成功后额外等待，确保页面完全加载
                    time.sleep(self.wait_after_cf)
                    return True
                else:
                    logger.warning(f"❌ 第 {retry_count + 1} 次重试失败，仍然检测到 Cloudflare 挑战")
                    
            except Exception as e:
                logger.error(f"第 {retry_count + 1} 次重试过程中出错: {e}")
                # 如果是严重错误，尝试重启浏览器
                if "disconnected" in str(e).lower() or "session" in str(e).lower():
                    logger.warning("检测到浏览器连接问题，尝试重启")
                    self._restart_browser()
                
            # 重试间隔（递增延迟）
            if retry_count < max_retries - 1:
                base_interval = 5 + retry_count * 2  # 递增延迟
                interval = random.uniform(base_interval, base_interval + 5)
                logger.info(f"等待 {interval:.1f} 秒后进行下一次重试")
                time.sleep(interval)
        
        logger.error(f"❌ 所有 {max_retries} 次重试尝试均失败，无法通过 Cloudflare 挑战")
        return False
    
    def _simulate_human_behavior(self):
        """
        模拟人类行为，增加通过 Cloudflare 挑战的成功率
        增强版随机延迟和行为模拟
        """
        import random
        
        try:
            logger.debug("开始模拟人类行为")
            
            # 1. 随机滚动页面（增加更多变化）
            scroll_actions = [
                "window.scrollTo(0, Math.random() * 300);",
                "window.scrollBy(0, Math.random() * 200 - 100);",
                "window.scrollTo(0, document.body.scrollHeight * Math.random());",
                "window.scrollTo({top: Math.random() * 500, behavior: 'smooth'});",
                "window.scrollBy({top: Math.random() * 150 - 75, behavior: 'smooth'});"
            ]
            self.page.run_js(random.choice(scroll_actions))
            # 滚动后随机等待，模拟用户观察内容
            scroll_wait = random.uniform(0.8, 2.5)
            logger.debug(f"滚动后等待 {scroll_wait:.1f} 秒")
            time.sleep(scroll_wait)
            
            # 2. 模拟鼠标移动（增加更自然的移动模式）
            mouse_moves = random.randint(2, 5)  # 随机移动次数
            self.page.run_js(f"""
                for(let i = 0; i < {mouse_moves}; i++) {{
                    setTimeout(() => {{
                        // 更自然的鼠标移动轨迹
                        const x = Math.random() * window.innerWidth;
                        const y = Math.random() * window.innerHeight;
                        document.dispatchEvent(new MouseEvent('mousemove', {{
                            clientX: x,
                            clientY: y,
                            bubbles: true
                        }}));
                        
                        // 偶尔触发hover事件
                        if (Math.random() < 0.3) {{
                            const element = document.elementFromPoint(x, y);
                            if (element) {{
                                element.dispatchEvent(new MouseEvent('mouseenter', {{
                                    bubbles: true
                                }}));
                            }}
                        }}
                    }}, i * (150 + Math.random() * 100));
                }}
            """)
            mouse_wait = random.uniform(1.2, 3.0)
            logger.debug(f"鼠标移动后等待 {mouse_wait:.1f} 秒")
            time.sleep(mouse_wait)
            
            # 3. 模拟键盘事件（增加多种按键）
            keys = ['Tab', 'ArrowDown', 'ArrowUp', 'Space']
            selected_key = random.choice(keys)
            self.page.run_js(f"""
                document.dispatchEvent(new KeyboardEvent('keydown', {{
                    key: '{selected_key}',
                    bubbles: true
                }}));
            """)
            key_wait = random.uniform(0.5, 1.2)
            logger.debug(f"按键 {selected_key} 后等待 {key_wait:.1f} 秒")
            time.sleep(key_wait)
            
            # 4. 模拟点击事件（在安全区域，增加多次点击）
            click_count = random.randint(1, 3)
            for i in range(click_count):
                self.page.run_js("""
                    const safeX = window.innerWidth * 0.1 + Math.random() * window.innerWidth * 0.8;
                    const safeY = window.innerHeight * 0.1 + Math.random() * window.innerHeight * 0.8;
                    document.dispatchEvent(new MouseEvent('click', {
                        clientX: safeX,
                        clientY: safeY,
                        bubbles: true
                    }));
                """)
                if i < click_count - 1:  # 不是最后一次点击
                    click_interval = random.uniform(0.8, 2.0)
                    logger.debug(f"点击间隔等待 {click_interval:.1f} 秒")
                    time.sleep(click_interval)
            
            # 5. 最终等待，模拟用户思考时间
            final_wait = random.uniform(1.0, 3.5)
            logger.debug(f"人类行为模拟完成，最终等待 {final_wait:.1f} 秒")
            time.sleep(final_wait)
            
        except Exception as e:
            logger.warning(f"模拟人类行为时出错: {e}")
    
    def _restart_browser(self) -> bool:
        """
        重启浏览器实例
        
        Returns:
            bool: 重启是否成功
        """
        try:
            logger.info("正在重启浏览器...")
            
            # 保存当前URL
            current_url = None
            if self.page:
                try:
                    current_url = self.page.url
                except:
                    pass
            
            # 关闭当前浏览器
            if self.browser:
                try:
                    self.browser.quit()
                except:
                    pass
            
            # 重置状态
            self.browser = None
            self.page = None
            self._cf_challenge_solved = False
            
            # 短暂等待
            time.sleep(random.uniform(2, 4))
            
            # 重新初始化浏览器
            self._init_browser()
            
            if not self.browser or not self.page:
                logger.error("浏览器重启失败：无法创建新实例")
                return False
            
            # 如果有之前的URL，尝试重新访问
            if current_url and current_url != "data:,":
                try:
                    logger.info(f"重新访问页面: {current_url}")
                    self.page.get(current_url, timeout=self.timeout)
                    time.sleep(random.uniform(3, 6))
                except Exception as e:
                    logger.warning(f"重新访问页面失败: {e}")
            
            logger.info("✅ 浏览器重启成功")
            return True
            
        except Exception as e:
            logger.error(f"浏览器重启过程中出错: {e}")
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
        
    def load_complete(self, timeout: int = 30):
        """
        等待页面加载完成
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否加载完成
        """
        if not self.page:
            return False
            
        try:
            # 1. 等待DOM准备好
            start_time = time.time()
            while time.time() - start_time < timeout:
                ready_state = self.page.run_js("return document.readyState;")
                if ready_state == "complete":
                    break
                time.sleep(0.5)
                
            # 2. 检查页面内容是否已经加载
            content_check = """
            return {
                'length': document.body ? document.body.innerHTML.length : 0,
                'title': document.title,
                'elements': document.querySelectorAll('*').length
            }
            """
            
            # 多次检查页面内容是否增长
            last_count = 0
            stable_count = 0
            for _ in range(5):
                if time.time() - start_time >= timeout:
                    break
                    
                content_info = self.page.run_js(content_check)
                current_count = content_info.get('elements', 0)
                
                if current_count > 100 and abs(current_count - last_count) < 10:
                    # 内容稳定了
                    stable_count += 1
                    if stable_count >= 2:
                        return True
                else:
                    stable_count = 0
                    
                last_count = current_count
                time.sleep(1)
                
            logger.info(f"页面加载完成，元素数量: {last_count}")
            return last_count > 100
        except Exception as e:
            logger.error(f"等待页面加载完成时出错: {e}")
            return False
    
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
                
    def quit(self):
        """
        关闭浏览器并释放资源（别名方法，兼容性支持）
        """
        self.close()


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
