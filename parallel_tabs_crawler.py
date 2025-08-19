#!/usr/bin/env python3
"""
并行标签页爬虫
同时打开5个标签页并行处理电影
"""

import time
import random
import json
import asyncio
from pathlib import Path
from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions
from concurrent.futures import ThreadPoolExecutor
import threading

class ParallelTabsCrawler:
    """并行标签页爬虫"""
    
    def __init__(self, max_tabs=5):
        self.max_tabs = max_tabs
        self.browser = None
        self.tabs = []
        self.results = []
        self.failed_movies = []
        self.lock = threading.Lock()
        
    def create_browser_with_tabs(self):
        """创建浏览器并打开多个标签页"""
        logger.info(f"🚀 创建浏览器并准备 {self.max_tabs} 个标签页")
        
        # 创建浏览器
        options = ChromiumOptions()
        options.headless(False)  # 显示浏览器便于观察
        options.set_argument('--window-size=1920,1080')
        options.set_argument('--disable-blink-features=AutomationControlled')
        
        self.browser = ChromiumPage(addr_or_opts=options)
        
        # 首先访问主页建立会话
        logger.info("📱 建立会话...")
        self.browser.get("https://missav.ai/")
        time.sleep(2)
        
        # 创建多个标签页
        self.tabs = [self.browser]  # 第一个标签页就是主页面
        
        for i in range(self.max_tabs - 1):
            try:
                new_tab = self.browser.new_tab()
                self.tabs.append(new_tab)
                logger.info(f"✅ 创建标签页 {i+2}/{self.max_tabs}")
                time.sleep(0.5)  # 短暂延迟避免创建过快
            except Exception as e:
                logger.warning(f"创建标签页 {i+2} 失败: {e}")
        
        logger.info(f"🎯 成功创建 {len(self.tabs)} 个标签页")
        return len(self.tabs)
    
    def extract_movie_info_from_tab(self, tab, movie_code):
        """从标签页提取电影信息"""
        try:
            html = tab.html
            if not html or len(html) < 1000:
                return None
            
            html_lower = html.lower()
            
            # 检查内容质量
            movie_indicators = 0
            if 'missav' in html_lower:
                movie_indicators += 1
            if movie_code.lower() in html_lower:
                movie_indicators += 1
            if any(word in html_lower for word in ['video', 'movie', 'player']):
                movie_indicators += 1
            
            if movie_indicators < 2:
                return None
            
            # 提取信息
            info = {
                'code': movie_code,
                'url': tab.url,
                'timestamp': time.time(),
                'page_length': len(html)
            }
            
            # 提取标题
            try:
                title_element = tab.ele('tag:h1')
                if title_element:
                    info['title'] = title_element.text.strip()
                else:
                    info['title'] = "未知标题"
            except:
                info['title'] = "未知标题"
            
            # 检查视频内容
            info['has_video_content'] = 'm3u8' in html_lower
            info['magnet_count'] = html_lower.count('magnet:')
            
            return info
            
        except Exception as e:
            logger.error(f"从标签页提取信息出错: {e}")
            return None
    
    def crawl_movie_in_tab(self, tab_index, movie_code):
        """在指定标签页中爬取电影"""
        tab = self.tabs[tab_index]
        url = f"https://missav.ai/ja/{movie_code}"
        
        try:
            logger.info(f"📍 [标签页{tab_index+1}] 访问: {movie_code}")
            
            # 访问页面
            tab.get(url)
            
            # 快速检查加载状态
            for check in range(3):  # 最多检查3秒
                time.sleep(1)
                html_length = len(tab.html) if tab.html else 0
                
                if html_length > 50000:
                    logger.info(f"✅ [标签页{tab_index+1}] {movie_code} 页面已加载 ({html_length} 字符)")
                    break
            
            # 快速滚动
            try:
                tab.scroll(500)
                time.sleep(0.3)
                tab.scroll(0)
            except:
                pass
            
            # 提取信息
            movie_info = self.extract_movie_info_from_tab(tab, movie_code)
            
            # 线程安全地保存结果
            with self.lock:
                if movie_info:
                    self.results.append(movie_info)
                    logger.info(f"✅ [标签页{tab_index+1}] {movie_code}: {movie_info.get('title', '未知')[:30]}...")
                    return True
                else:
                    self.failed_movies.append(movie_code)
                    logger.error(f"❌ [标签页{tab_index+1}] {movie_code}: 信息提取失败")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ [标签页{tab_index+1}] {movie_code}: {e}")
            with self.lock:
                self.failed_movies.append(movie_code)
            return False
    
    def parallel_crawl_batch(self, movie_codes):
        """并行爬取一批电影"""
        logger.info(f"🚀 并行处理 {len(movie_codes)} 部电影")
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=len(self.tabs)) as executor:
            futures = []
            
            for i, movie_code in enumerate(movie_codes):
                tab_index = i % len(self.tabs)  # 循环使用标签页
                future = executor.submit(self.crawl_movie_in_tab, tab_index, movie_code)
                futures.append((future, movie_code, tab_index))
            
            # 等待所有任务完成
            for future, movie_code, tab_index in futures:
                try:
                    success = future.result(timeout=30)  # 30秒超时
                except Exception as e:
                    logger.error(f"❌ [标签页{tab_index+1}] {movie_code} 超时或出错: {e}")
                    with self.lock:
                        self.failed_movies.append(movie_code)
    
    def batch_crawl(self, movie_codes, batch_size=None):
        """批量并行爬取"""
        if batch_size is None:
            batch_size = self.max_tabs
        
        logger.info(f"🚀 开始并行批量爬取 {len(movie_codes)} 部电影")
        logger.info(f"📊 使用 {len(self.tabs)} 个标签页，每批处理 {batch_size} 部")
        
        start_time = time.time()
        
        try:
            # 分批处理
            for i in range(0, len(movie_codes), batch_size):
                batch = movie_codes[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(movie_codes) + batch_size - 1) // batch_size
                
                logger.info(f"\n🎬 批次 {batch_num}/{total_batches}: {len(batch)} 部电影")
                logger.info(f"📋 {', '.join(batch)}")
                
                # 并行处理这一批
                self.parallel_crawl_batch(batch)
                
                # 批次间短暂休息
                if i + batch_size < len(movie_codes):
                    rest_time = random.uniform(2, 5)
                    logger.info(f"😴 批次间休息 {rest_time:.1f} 秒...")
                    time.sleep(rest_time)
                
                # 保存中间结果
                self.save_results()
                
                # 显示进度
                elapsed = time.time() - start_time
                processed = min(i + batch_size, len(movie_codes))
                avg_time = elapsed / processed
                remaining = (len(movie_codes) - processed) * avg_time
                
                logger.info(f"📊 进度: {processed}/{len(movie_codes)}, "
                          f"平均 {avg_time:.1f}秒/部, 预计剩余 {remaining/60:.1f}分钟")
        
        finally:
            # 最终保存
            self.save_results()
            
            # 关闭浏览器
            if self.browser:
                try:
                    self.browser.quit()
                    logger.info("🔒 浏览器已关闭")
                except:
                    pass
        
        # 输出统计
        total_time = time.time() - start_time
        success_count = len(self.results)
        failed_count = len(self.failed_movies)
        
        logger.info(f"\n{'='*50}")
        logger.info(f"📊 并行爬取完成")
        logger.info(f"总数: {len(movie_codes)}")
        logger.info(f"成功: {success_count}")
        logger.info(f"失败: {failed_count}")
        logger.info(f"成功率: {success_count/len(movie_codes)*100:.1f}%")
        logger.info(f"总时间: {total_time/60:.1f} 分钟")
        logger.info(f"平均速度: {total_time/len(movie_codes):.1f} 秒/部")
        logger.info(f"并行效率: 比单线程快 ~{self.max_tabs:.1f}x")
        
        return self.results
    
    def save_results(self):
        """保存结果"""
        if self.results:
            success_file = Path("parallel_crawl_results.json")
            with open(success_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 成功结果已保存: {success_file} ({len(self.results)} 部)")
        
        if self.failed_movies:
            failed_file = Path("parallel_failed_movies.json")
            with open(failed_file, 'w', encoding='utf-8') as f:
                json.dump(self.failed_movies, f, ensure_ascii=False, indent=2)
            logger.info(f"📝 失败列表已保存: {failed_file} ({len(self.failed_movies)} 部)")

def main():
    """主函数"""
    
    # 测试电影列表
    test_movies = [
        "ipzz-562", "sone-718", "ngod-266", "dass-659", "jur-320",
        "ure-122", "ipzz-563", "sone-719", "ngod-267", "dass-660",
        "jur-321", "ure-123", "ipzz-564", "sone-720", "ngod-268"
    ]
    
    logger.info("🚀 并行标签页爬虫")
    logger.info(f"📋 准备爬取 {len(test_movies)} 部电影")
    logger.info("⚡ 使用 5 个标签页并行处理")
    logger.info(f"🕐 预计总时间: ~{len(test_movies)*2/60:.1f} 分钟 (比单线程快5倍)")
    
    # 询问是否开始
    start = input(f"\n🚀 开始并行爬取 {len(test_movies)} 部电影? [y/n]: ").lower()
    if start != 'y':
        logger.info("👋 下次见！")
        return
    
    # 创建爬虫
    crawler = ParallelTabsCrawler(max_tabs=5)
    
    # 创建标签页
    actual_tabs = crawler.create_browser_with_tabs()
    if actual_tabs == 0:
        logger.error("❌ 无法创建标签页，退出")
        return
    
    # 开始并行爬取
    results = crawler.batch_crawl(test_movies)
    
    # 显示结果
    if results:
        logger.info("\n🎬 成功爬取的电影:")
        for result in results[:5]:
            logger.info(f"  ✅ {result['code']}: {result.get('title', '未知')[:40]}...")
        
        if len(results) > 5:
            logger.info(f"  ... 还有 {len(results)-5} 部电影")

if __name__ == "__main__":
    main()
