#!/usr/bin/env python3
"""
增强版Cloudflare绕过工具
针对最新的Cloudflare反爬虫机制进行优化
"""

import sys
import time
import random
import json
from pathlib import Path
from loguru import logger

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from src.app.utils.drission_utils import CloudflareBypassBrowser

class EnhancedCloudflareBypass:
    """增强版Cloudflare绕过类"""
    
    def __init__(self, headless: bool = True, use_proxy: bool = False):
        self.headless = headless
        self.use_proxy = use_proxy
        self.browser = None
        self.success_count = 0
        self.fail_count = 0
        
        # 创建用户数据目录
        self.user_data_dir = Path.home() / ".cache" / "enhanced_cf_bypass"
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
    
    def create_browser_with_enhanced_stealth(self):
        """创建具有增强隐身功能的浏览器"""
        try:
            # 使用随机用户数据目录避免指纹识别
            random_suffix = random.randint(1000, 9999)
            temp_user_data = self.user_data_dir / f"session_{random_suffix}"
            temp_user_data.mkdir(exist_ok=True)
            
            browser = CloudflareBypassBrowser(
                headless=self.headless,
                user_data_dir=str(temp_user_data),
                load_images=False,  # 不加载图片提高速度
                timeout=180,  # 增加超时时间
                wait_after_cf=10  # Cloudflare挑战后等待更长时间
            )
            
            # 应用增强的反检测措施
            self._apply_enhanced_stealth(browser)
            
            return browser
            
        except Exception as e:
            logger.error(f"创建浏览器失败: {e}")
            return None
    
    def _apply_enhanced_stealth(self, browser):
        """应用增强的反检测措施"""
        try:
            # 1. 更全面的navigator属性修改
            browser.run_js("""
            // 修改webdriver属性
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                configurable: true
            });
            
            // 修改plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {name: 'Chrome PDF Plugin', description: 'Portable Document Format'},
                    {name: 'Chrome PDF Viewer', description: 'PDF Viewer'},
                    {name: 'Native Client', description: 'Native Client'}
                ],
                configurable: true
            });
            
            // 修改languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en', 'zh-CN', 'zh'],
                configurable: true
            });
            
            // 修改platform
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32',
                configurable: true
            });
            
            // 修改hardwareConcurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 4,
                configurable: true
            });
            
            // 修改deviceMemory
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8,
                configurable: true
            });
            """)
            
            # 2. 移除自动化痕迹
            browser.run_js("""
            // 删除webdriver相关属性
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_JSON;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Proxy;
            
            // 修改chrome对象
            if (window.chrome) {
                Object.defineProperty(window.chrome, 'runtime', {
                    get: () => ({
                        onConnect: undefined,
                        onMessage: undefined
                    }),
                    configurable: true
                });
            }
            """)
            
            # 3. 模拟真实的屏幕和视口
            browser.run_js("""
            // 设置真实的屏幕尺寸
            Object.defineProperty(screen, 'width', {get: () => 1920});
            Object.defineProperty(screen, 'height', {get: () => 1080});
            Object.defineProperty(screen, 'availWidth', {get: () => 1920});
            Object.defineProperty(screen, 'availHeight', {get: () => 1040});
            Object.defineProperty(screen, 'colorDepth', {get: () => 24});
            Object.defineProperty(screen, 'pixelDepth', {get: () => 24});
            """)
            
            logger.info("增强反检测措施已应用")
            
        except Exception as e:
            logger.warning(f"应用增强反检测措施失败: {e}")
    
    def crawl_with_retry(self, url: str, max_retries: int = 3) -> dict:
        """使用重试机制爬取URL"""
        for attempt in range(max_retries):
            logger.info(f"尝试第 {attempt + 1}/{max_retries} 次爬取: {url}")
            
            browser = self.create_browser_with_enhanced_stealth()
            if not browser:
                continue
            
            try:
                # 随机延迟避免检测
                initial_delay = random.uniform(2, 5)
                logger.info(f"初始延迟 {initial_delay:.1f} 秒")
                time.sleep(initial_delay)
                
                # 尝试访问页面
                success = browser.get(url, wait_for_cf=True, timeout=180)
                
                if success:
                    # 额外等待确保页面完全加载
                    time.sleep(random.uniform(3, 6))
                    
                    html_content = browser.get_html()
                    
                    # 验证内容质量
                    if self._validate_content(html_content, url):
                        self.success_count += 1
                        logger.info(f"✅ 成功爬取: {url}")
                        return {
                            'success': True,
                            'html': html_content,
                            'attempt': attempt + 1
                        }
                    else:
                        logger.warning(f"内容验证失败: {url}")
                
            except Exception as e:
                logger.error(f"爬取过程中出错: {e}")
            
            finally:
                try:
                    browser.close()
                except:
                    pass
            
            # 失败后等待更长时间再重试
            if attempt < max_retries - 1:
                retry_delay = random.uniform(10, 20) * (attempt + 1)
                logger.info(f"等待 {retry_delay:.1f} 秒后重试")
                time.sleep(retry_delay)
        
        self.fail_count += 1
        logger.error(f"❌ 所有重试均失败: {url}")
        return {'success': False, 'html': None, 'attempt': max_retries}
    
    def _validate_content(self, html_content: str, url: str) -> bool:
        """验证页面内容是否有效"""
        if not html_content or len(html_content) < 10000:
            return False
        
        # 检查是否仍然是Cloudflare挑战页面
        cf_indicators = [
            'Cloudflare',
            'challenge',
            'cf-spinner',
            'cf-challenge',
            'security check',
            'checking your browser'
        ]
        
        html_lower = html_content.lower()
        for indicator in cf_indicators:
            if indicator in html_lower:
                logger.warning(f"检测到Cloudflare指标: {indicator}")
                return False
        
        # 检查是否包含预期的内容
        if 'missav' in url:
            expected_indicators = [
                'missav',
                'video',
                'movie',
                'title'
            ]
            
            found_indicators = sum(1 for indicator in expected_indicators if indicator in html_lower)
            if found_indicators < 2:
                logger.warning(f"预期内容指标不足: {found_indicators}/4")
                return False
        
        return True
    
    def test_multiple_urls(self, urls: list) -> dict:
        """测试多个URL的爬取成功率"""
        results = {
            'total': len(urls),
            'success': 0,
            'failed': 0,
            'details': []
        }
        
        for i, url in enumerate(urls, 1):
            logger.info(f"\n=== 测试 {i}/{len(urls)}: {url} ===")
            
            result = self.crawl_with_retry(url, max_retries=2)
            
            results['details'].append({
                'url': url,
                'success': result['success'],
                'attempt': result['attempt']
            })
            
            if result['success']:
                results['success'] += 1
            else:
                results['failed'] += 1
            
            # 测试间隔
            if i < len(urls):
                interval = random.uniform(15, 30)
                logger.info(f"等待 {interval:.1f} 秒后测试下一个URL")
                time.sleep(interval)
        
        return results

def main():
    """主测试函数"""
    logger.info("🚀 开始增强版Cloudflare绕过测试")
    
    # 测试URL
    test_urls = [
        "https://missav.ai/ja/ipzz-562",
        "https://missav.ai/ja/ngod-266",
        "https://missav.ai/ja/ure-122"
    ]
    
    bypass = EnhancedCloudflareBypass(headless=False)  # 显示浏览器便于调试
    
    results = bypass.test_multiple_urls(test_urls)
    
    logger.info("\n" + "="*50)
    logger.info("📊 测试结果统计")
    logger.info(f"总数: {results['total']}")
    logger.info(f"成功: {results['success']}")
    logger.info(f"失败: {results['failed']}")
    logger.info(f"成功率: {results['success']/results['total']*100:.1f}%")
    
    for detail in results['details']:
        status = "✅" if detail['success'] else "❌"
        logger.info(f"{status} {detail['url']} (尝试 {detail['attempt']} 次)")

if __name__ == "__main__":
    main()
