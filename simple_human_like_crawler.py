#!/usr/bin/env python3
"""
超级简单的人类模拟爬虫
就像人类手动操作浏览器一样
"""

import time
import random
from pathlib import Path
from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions

def create_human_like_browser():
    """创建一个像人类使用的浏览器"""
    
    # 配置浏览器选项
    options = ChromiumOptions()
    
    # 不要无头模式，让用户看到浏览器（更像人类）
    options.headless(False)

    # 设置窗口大小
    options.set_argument('--window-size=1920,1080')

    # 添加一些人类化的参数
    options.set_argument('--disable-blink-features=AutomationControlled')
    options.set_argument('--disable-web-security')
    options.set_argument('--allow-running-insecure-content')
    
    # 不禁用图片（人类会看图片）
    # options.set_argument('--disable-images')  # 注释掉这行
    
    # 创建浏览器
    browser = ChromiumPage(addr_or_opts=options)
    
    logger.info("浏览器创建成功，就像人类在使用一样")
    return browser

def human_like_wait():
    """像人类一样的等待时间（优化版）"""
    # 减少等待时间，但保持随机性避免检测
    wait_time = random.uniform(0, 1)  
    logger.info(f"快速等待 {wait_time:.1f} 秒后继续...")
    time.sleep(wait_time)

def human_like_scroll(browser):
    """像人类一样滚动页面"""
    try:
        # 随机滚动几次，就像人类在浏览
        scroll_times = random.randint(2, 5)
        for i in range(scroll_times):
            scroll_amount = random.randint(200, 800)
            # 修复滚动方法调用
            browser.scroll(scroll_amount)
            time.sleep(random.uniform(0.5, 2))
            logger.info(f"滚动页面 {i+1}/{scroll_times}")

        # 滚回顶部
        browser.scroll(0)
        time.sleep(1)
    except Exception as e:
        logger.warning(f"滚动页面时出错: {e}")

def extract_movie_info_simple(browser, movie_code):
    """简单提取电影信息"""
    try:
        # 获取页面HTML
        html = browser.html

        if not html or len(html) < 1000:
            logger.warning(f"页面内容太少: {len(html) if html else 0} 字符")
            return None

        logger.info(f"📄 页面内容长度: {len(html)} 字符")

        # 更智能的Cloudflare检测 - 只有同时包含多个指标才认为是挑战页面
        cf_indicators = 0
        html_lower = html.lower()

        if 'cloudflare' in html_lower:
            cf_indicators += 1
        if 'challenge' in html_lower:
            cf_indicators += 1
        if 'checking your browser' in html_lower:
            cf_indicators += 1
        if 'security check' in html_lower:
            cf_indicators += 1

        # 检查是否包含电影页面的正常内容
        movie_indicators = 0
        if 'missav' in html_lower:
            movie_indicators += 1
        if movie_code.lower() in html_lower:
            movie_indicators += 1
        if any(word in html_lower for word in ['video', 'movie', 'player', 'download']):
            movie_indicators += 1
        if any(word in html_lower for word in ['女优', 'actress', '时长', 'duration']):
            movie_indicators += 1

        logger.info(f"🔍 Cloudflare指标: {cf_indicators}, 电影内容指标: {movie_indicators}")

        # 如果有足够的电影内容指标，即使有少量CF指标也认为是成功页面
        if movie_indicators >= 2:
            logger.info("✅ 检测到足够的电影内容，认为页面加载成功")
        elif cf_indicators >= 2 and movie_indicators == 0:
            logger.warning("⚠️ 检测到Cloudflare挑战页面")
            return None
        else:
            logger.info("🤔 页面状态不明确，尝试提取信息...")
        
        # 简单提取标题
        title = "未知标题"
        try:
            title_element = browser.ele('tag:h1')
            if title_element:
                title = title_element.text.strip()
        except:
            pass
        
        # 简单提取其他信息
        info = {
            'code': movie_code,
            'title': title,
            'url': browser.url,
            'page_length': len(html),
            'timestamp': time.time()
        }
        
        logger.info(f"✅ 成功提取: {movie_code} - {title[:50]}...")
        return info
        
    except Exception as e:
        logger.error(f"提取信息时出错: {e}")
        return None

def crawl_movies_like_human(movie_codes):
    """像人类一样爬取电影"""
    
    logger.info(f"🚀 开始像人类一样爬取 {len(movie_codes)} 部电影")
    
    # 创建浏览器
    browser = create_human_like_browser()
    
    results = []
    
    try:
        # 快速访问主页建立会话
        logger.info("📱 快速访问主页建立会话...")
        browser.get("https://missav.ai/")

        # 快速等待主页加载
        time.sleep(2)

        # 简单滚动一下
        try:
            browser.scroll(300)
            time.sleep(0.5)
            browser.scroll(0)
        except:
            pass

        logger.info("✅ 会话建立完成，开始快速访问电影页面")
        
        # 逐个访问电影页面
        for i, movie_code in enumerate(movie_codes, 1):
            logger.info(f"\n🎬 正在处理第 {i}/{len(movie_codes)} 部电影: {movie_code}")
            
            # 构建URL
            url = f"https://missav.ai/ja/{movie_code}"
            logger.info(f"📍 访问: {url}")
            
            # 访问页面
            browser.get(url)

            # 快速检查页面是否加载完成
            logger.info("⚡ 快速检查页面加载状态...")

            # 等待基本加载（最多3秒）
            max_wait = 3
            for check_count in range(max_wait):
                time.sleep(1)
                current_url = browser.url
                html_length = len(browser.html) if browser.html else 0

                logger.info(f"📊 检查 {check_count+1}/{max_wait}: URL={current_url}, HTML长度={html_length}")

                # 如果HTML长度足够且URL正确，立即继续
                if html_length > 50000 and movie_code in current_url:
                    logger.info("✅ 页面已充分加载，立即提取信息")
                    break
                elif html_length > 100000:  # 即使URL不完全匹配，如果内容足够多也继续
                    logger.info("✅ 页面内容充足，立即提取信息")
                    break

            # 快速滚动一下（可选，很快）
            try:
                browser.scroll(500)
                time.sleep(0.5)
                browser.scroll(0)
            except:
                pass
            
            # 提取信息
            movie_info = extract_movie_info_simple(browser, movie_code)
            
            if movie_info:
                results.append(movie_info)
                logger.info(f"✅ 成功: {movie_code}")
            else:
                logger.error(f"❌ 失败: {movie_code}")
            
            # 在电影之间等待，就像人类在思考下一步
            if i < len(movie_codes):
                logger.info(f"🤔 像人类一样思考下一步...")
                human_like_wait()
    
    except Exception as e:
        logger.error(f"爬取过程中出错: {e}")
    
    finally:
        # 关闭浏览器
        try:
            browser.quit()
            logger.info("🔒 浏览器已关闭")
        except:
            pass
    
    return results

def main():
    """主函数"""
    
    # 测试电影列表
    test_movies = [
        "ipzz-562",
        "sone-718", 
        "ngod-266"
    ]
    
    logger.info("🎯 使用超级简单的人类模拟方法")
    logger.info("💡 策略: 就像人类手动操作浏览器一样")
    logger.info(f"📋 测试电影: {test_movies}")
    
    # 开始爬取
    results = crawl_movies_like_human(test_movies)
    
    # 输出结果
    logger.info("\n" + "="*50)
    logger.info("📊 爬取结果")
    logger.info(f"总数: {len(test_movies)}")
    logger.info(f"成功: {len(results)}")
    logger.info(f"失败: {len(test_movies) - len(results)}")
    logger.info(f"成功率: {len(results)/len(test_movies)*100:.1f}%")
    
    for result in results:
        logger.info(f"✅ {result['code']}: {result['title']}")
    
    return results

if __name__ == "__main__":
    main()
