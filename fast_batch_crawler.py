#!/usr/bin/env python3
"""
快速批量爬虫
基于成功的快速方法，处理大量电影
"""

import time
import random
import json
from pathlib import Path
from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions

class FastBatchCrawler:
    """快速批量爬虫"""
    
    def __init__(self):
        self.results = []
        self.failed_movies = []
        self.browser = None
        
    def create_fast_browser(self):
        """创建快速浏览器"""
        options = ChromiumOptions()
        options.headless(False)  # 可以改为True来隐藏浏览器
        options.set_argument('--window-size=1920,1080')
        options.set_argument('--disable-blink-features=AutomationControlled')
        
        self.browser = ChromiumPage(addr_or_opts=options)
        logger.info("🚀 快速浏览器创建成功")
        
        # 快速建立会话
        logger.info("📱 建立会话...")
        self.browser.get("https://missav.ai/")
        time.sleep(2)
        
        try:
            self.browser.scroll(300)
            time.sleep(0.5)
            self.browser.scroll(0)
        except:
            pass
        
        logger.info("✅ 会话建立完成")
    
    def fast_extract_info(self, movie_code):
        """快速提取电影信息"""
        try:
            html = self.browser.html
            if not html or len(html) < 1000:
                return None
            
            html_lower = html.lower()
            
            # 快速内容检查
            movie_indicators = 0
            if 'missav' in html_lower:
                movie_indicators += 1
            if movie_code.lower() in html_lower:
                movie_indicators += 1
            if any(word in html_lower for word in ['video', 'movie', 'player']):
                movie_indicators += 1
            
            if movie_indicators < 2:
                return None
            
            # 快速提取基本信息
            info = {
                'code': movie_code,
                'url': self.browser.url,
                'timestamp': time.time(),
                'page_length': len(html)
            }
            
            # 提取标题
            try:
                title_element = self.browser.ele('tag:h1')
                if title_element:
                    info['title'] = title_element.text.strip()
                else:
                    info['title'] = "未知标题"
            except:
                info['title'] = "未知标题"
            
            # 检查视频内容
            info['has_video_content'] = 'm3u8' in html_lower or 'video' in html_lower
            info['magnet_count'] = html_lower.count('magnet:')
            
            return info
            
        except Exception as e:
            logger.error(f"提取信息出错: {e}")
            return None
    
    def crawl_single_movie(self, movie_code):
        """爬取单个电影（超快速）"""
        url = f"https://missav.ai/ja/{movie_code}"
        logger.info(f"📍 访问: {movie_code}")
        
        try:
            # 访问页面
            self.browser.get(url)
            
            # 快速检查加载状态（最多2秒）
            for check in range(2):
                time.sleep(1)
                html_length = len(self.browser.html) if self.browser.html else 0
                
                if html_length > 50000:
                    logger.info(f"✅ {movie_code} 页面已加载 ({html_length} 字符)")
                    break
            
            # 快速滚动
            try:
                self.browser.scroll(500)
                time.sleep(0.3)
                self.browser.scroll(0)
            except:
                pass
            
            # 提取信息
            movie_info = self.fast_extract_info(movie_code)
            
            if movie_info:
                self.results.append(movie_info)
                logger.info(f"✅ {movie_code}: {movie_info.get('title', '未知')[:30]}...")
                return True
            else:
                self.failed_movies.append(movie_code)
                logger.error(f"❌ {movie_code}: 信息提取失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ {movie_code}: {e}")
            self.failed_movies.append(movie_code)
            return False
    
    def batch_crawl(self, movie_codes, save_interval=10):
        """批量爬取电影"""
        logger.info(f"🚀 开始快速批量爬取 {len(movie_codes)} 部电影")
        
        # 创建浏览器
        self.create_fast_browser()
        
        start_time = time.time()
        
        try:
            for i, movie_code in enumerate(movie_codes, 1):
                logger.info(f"\n🎬 [{i}/{len(movie_codes)}] {movie_code}")
                
                # 爬取电影
                success = self.crawl_single_movie(movie_code)
                
                # 定期保存结果
                if i % save_interval == 0:
                    self.save_results()
                    elapsed = time.time() - start_time
                    avg_time = elapsed / i
                    remaining = (len(movie_codes) - i) * avg_time
                    logger.info(f"📊 进度: {i}/{len(movie_codes)}, 平均 {avg_time:.1f}秒/部, 预计剩余 {remaining/60:.1f}分钟")
                
                # 快速间隔
                if i < len(movie_codes):
                    wait_time = random.uniform(2, 5)  # 2-5秒
                    time.sleep(wait_time)
        
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
        logger.info(f"📊 批量爬取完成")
        logger.info(f"总数: {len(movie_codes)}")
        logger.info(f"成功: {success_count}")
        logger.info(f"失败: {failed_count}")
        logger.info(f"成功率: {success_count/len(movie_codes)*100:.1f}%")
        logger.info(f"总时间: {total_time/60:.1f} 分钟")
        logger.info(f"平均速度: {total_time/len(movie_codes):.1f} 秒/部")
        
        return self.results
    
    def save_results(self):
        """保存结果到文件"""
        if self.results:
            # 保存成功结果
            success_file = Path("fast_crawl_results.json")
            with open(success_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 成功结果已保存: {success_file} ({len(self.results)} 部)")
        
        if self.failed_movies:
            # 保存失败列表
            failed_file = Path("failed_movies.json")
            with open(failed_file, 'w', encoding='utf-8') as f:
                json.dump(self.failed_movies, f, ensure_ascii=False, indent=2)
            logger.info(f"📝 失败列表已保存: {failed_file} ({len(self.failed_movies)} 部)")

def main():
    """主函数"""
    
    # 测试电影列表（可以扩展到更多）
    test_movies = [
        "ipzz-562", "sone-718", "ngod-266",
        "dass-659", "jur-320", "ure-122",
        "ipzz-563", "sone-719", "ngod-267",
        "dass-660", "jur-321", "ure-123"
    ]
    
    logger.info("🚀 快速批量爬虫")
    logger.info(f"📋 准备爬取 {len(test_movies)} 部电影")
    logger.info("⚡ 预计速度: ~10秒/部")
    logger.info(f"🕐 预计总时间: ~{len(test_movies)*10/60:.1f} 分钟")
    
    # 询问是否开始
    start = input(f"\n🚀 开始爬取 {len(test_movies)} 部电影? [y/n]: ").lower()
    if start != 'y':
        logger.info("👋 下次见！")
        return
    
    # 创建爬虫并开始
    crawler = FastBatchCrawler()
    results = crawler.batch_crawl(test_movies, save_interval=5)
    
    # 显示部分结果
    if results:
        logger.info("\n🎬 成功爬取的电影:")
        for result in results[:5]:  # 只显示前5个
            logger.info(f"  ✅ {result['code']}: {result.get('title', '未知')[:40]}...")
        
        if len(results) > 5:
            logger.info(f"  ... 还有 {len(results)-5} 部电影")

if __name__ == "__main__":
    main()
