#!/usr/bin/env python3
"""
Linux服务器版电影爬虫
适配无头模式和服务器环境
"""

import os
import sys
import time
import json
import random
import argparse
from pathlib import Path
from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 配置日志
logger.remove()
logger.add(
    "src/logs/crawler.log",
    rotation="10 MB",
    retention=5,
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{line} - {message}",
    enqueue=True,
    encoding="utf-8"
)
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

class LinuxMovieCrawler:
    """Linux服务器版电影爬虫"""
    
    def __init__(self, headless=True, max_workers=3):
        self.headless = headless
        self.max_workers = max_workers
        self.output_file = "crawl_results.jsonl"
        
        # 数据库配置
        self.db_url = self.get_db_url()
        self.engine = create_engine(self.db_url)
        self.Session = sessionmaker(bind=self.engine)
        
        # 浏览器配置
        self.browser = None
        self.tabs = []
        
        logger.info("🚀 Linux电影爬虫初始化完成")
    
    def get_db_url(self):
        """获取数据库连接URL"""
        # 从环境变量或配置文件读取
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'movie_crawler')
        db_user = os.getenv('DB_USER', 'crawler_user')
        db_password = os.getenv('DB_PASSWORD', 'your_password')
        
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    def setup_browser(self):
        """设置浏览器"""
        options = ChromiumOptions()
        
        if self.headless:
            options.headless(True)
        
        # Linux服务器优化配置
        options.set_argument('--no-sandbox')
        options.set_argument('--disable-dev-shm-usage')
        options.set_argument('--disable-gpu')
        options.set_argument('--disable-web-security')
        options.set_argument('--disable-features=VizDisplayCompositor')
        options.set_argument('--window-size=1920,1080')
        options.set_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            self.browser = ChromiumPage(addr_or_opts=options)
            logger.info("✅ 浏览器创建成功")
            
            # 建立会话
            self.browser.get("https://missav.ai/")
            time.sleep(3)
            
            # 创建多个标签页
            self.tabs = [self.browser]
            for i in range(self.max_workers - 1):
                try:
                    new_tab = self.browser.new_tab()
                    self.tabs.append(new_tab)
                    logger.info(f"✅ 创建标签页 {i+2}/{self.max_workers}")
                    time.sleep(1)
                except Exception as e:
                    logger.warning(f"⚠️ 创建标签页失败: {e}")
                    break
            
            logger.info(f"🎯 成功创建 {len(self.tabs)} 个标签页")
            return True
            
        except Exception as e:
            logger.error(f"❌ 浏览器创建失败: {e}")
            return False
    
    def get_movies_from_db(self, limit=None, offset_id=None):
        """从数据库获取电影列表"""
        session = self.Session()
        try:
            # 构建查询
            query = """
                SELECT id, link 
                FROM movies 
                WHERE link IS NOT NULL 
                AND link != ''
            """
            
            if offset_id:
                query += f" AND id > {offset_id}"
            
            query += " ORDER BY id"
            
            if limit:
                query += f" LIMIT {limit}"
            
            result = session.execute(text(query))
            raw_movies = [(row.id, row.link) for row in result]
            
            # 转换为完整URL并修正uncensored-leaked
            movies = []
            for movie_id, link in raw_movies:
                if link.startswith('dm3/v/') or link.startswith('dm4/v/'):
                    movie_code = link.split('/')[-1]
                    # 修正uncensored-leaked为uncensored-leak
                    if movie_code.endswith('-uncensored-leaked'):
                        original_code = movie_code
                        movie_code = movie_code.replace('-uncensored-leaked', '-uncensored-leak')
                        logger.info(f"🔧 修正URL: ID={movie_id}, {original_code} → {movie_code}")
                    full_url = f"https://missav.ai/ja/{movie_code}"
                    movies.append((movie_id, full_url, movie_code))
            
            logger.info(f"📊 从数据库获取到 {len(movies)} 部电影")
            return movies
            
        finally:
            session.close()
    
    def extract_movie_info(self, html, movie_id, movie_code, url):
        """提取电影信息（简化版）"""
        try:
            import re
            from bs4 import BeautifulSoup
            
            result = {
                'id': movie_id,
                'code': movie_code,
                'url': url,
                'timestamp': time.time(),
                'page_length': len(html),
                'extraction_type': 'linux_simple'
            }
            
            # 提取标题
            try:
                soup = BeautifulSoup(html, 'html.parser')
                h1_tag = soup.find('h1')
                if h1_tag:
                    result['title'] = h1_tag.get_text().strip()
                else:
                    result['title'] = movie_code
            except:
                result['title'] = movie_code
            
            # 提取M3U8链接
            m3u8_patterns = [
                r'https?://[^"\'>\s]+\.m3u8[^"\'>\s]*',
                r'"(https?://[^"]+\.m3u8[^"]*)"',
                r"'(https?://[^']+\.m3u8[^']*)'",
            ]
            
            all_m3u8 = []
            for pattern in m3u8_patterns:
                matches = re.findall(pattern, html)
                all_m3u8.extend(matches)
            
            unique_m3u8 = list(set(all_m3u8))[:5]
            result['m3u8_links'] = unique_m3u8
            
            # 提取磁力链接
            magnet_links = re.findall(r'magnet:\?[^"\'>\s]+', html)
            result['magnet_links'] = magnet_links[:10]
            
            # 设置状态
            if len(unique_m3u8) > 0:
                result['status'] = 'success_with_m3u8'
                logger.info(f"✅ 成功提取: {movie_code}, M3U8: {len(unique_m3u8)}, 磁力: {len(magnet_links)}")
            elif len(magnet_links) > 0:
                result['status'] = 'partial_success_magnet_only'
                logger.info(f"⚠️ 部分成功: {movie_code}, 磁力: {len(magnet_links)}")
            else:
                result['status'] = 'extraction_failed'
                logger.warning(f"🚫 提取失败: {movie_code}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 提取出错: {movie_code}, 错误: {e}")
            return None
    
    def crawl_movie(self, tab, movie_id, movie_url, movie_code):
        """爬取单部电影"""
        try:
            logger.info(f"📍 开始爬取: ID={movie_id}, {movie_code}")
            
            # 访问页面
            tab.get(movie_url)
            
            # 等待加载
            for check in range(5):
                time.sleep(1)
                html = tab.html
                current_url = tab.url
                
                if html and len(html) > 50000:
                    logger.info(f"✅ 页面已加载: ID={movie_id} ({len(html)} 字符)")
                    break
                elif check == 4:
                    logger.warning(f"⏳ 页面加载超时: ID={movie_id}")
            
            # 检查重定向
            final_movie_code = movie_code
            if current_url != movie_url:
                try:
                    final_movie_code = current_url.split('/')[-1]
                    logger.info(f"🔄 重定向: {movie_code} → {final_movie_code}")
                except:
                    pass
            
            # 提取信息
            if html and len(html) > 10000:
                movie_info = self.extract_movie_info(html, movie_id, final_movie_code, current_url)
                
                if movie_info:
                    # 保存到JSONL
                    with open(self.output_file, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(movie_info, ensure_ascii=False) + '\n')
                    
                    return movie_info['status'], movie_info.get('title', movie_code)[:50]
                else:
                    return 'extraction_failed', f"{movie_code}: 信息提取失败"
            else:
                return '404_or_empty', f"{movie_code}: 页面内容不足"
                
        except Exception as e:
            logger.error(f"❌ 爬取异常: ID={movie_id}, 错误: {e}")
            return 'exception', f"{movie_code}: {str(e)}"
    
    def run_batch(self, movies):
        """批量处理电影"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = {
            'success': 0,
            'partial_success': 0,
            'failed': 0,
            'total': len(movies)
        }
        
        with ThreadPoolExecutor(max_workers=len(self.tabs)) as executor:
            # 提交任务
            futures = []
            for i, (movie_id, movie_url, movie_code) in enumerate(movies):
                tab = self.tabs[i % len(self.tabs)]
                future = executor.submit(self.crawl_movie, tab, movie_id, movie_url, movie_code)
                futures.append((future, movie_id, movie_code))
            
            # 收集结果
            for future, movie_id, movie_code in futures:
                try:
                    status, message = future.result(timeout=60)
                    
                    if status in ['success_with_m3u8']:
                        results['success'] += 1
                        logger.info(f"✅ ID={movie_id}: {message}")
                    elif status in ['partial_success_magnet_only']:
                        results['partial_success'] += 1
                        logger.info(f"⚠️ ID={movie_id}: {message}")
                    else:
                        results['failed'] += 1
                        logger.warning(f"🚫 ID={movie_id}: {message}")
                        
                except Exception as e:
                    results['failed'] += 1
                    logger.error(f"💥 ID={movie_id}: 处理异常: {e}")
        
        return results
    
    def run(self, batch_size=10, max_movies=None):
        """运行爬虫"""
        if not self.setup_browser():
            return False
        
        try:
            # 获取最后处理的ID
            last_id = self.get_last_processed_id()
            logger.info(f"📍 从ID {last_id} 开始处理")
            
            total_results = {
                'success': 0,
                'partial_success': 0,
                'failed': 0,
                'total': 0
            }
            
            processed = 0
            while True:
                # 获取一批电影
                movies = self.get_movies_from_db(limit=batch_size, offset_id=last_id)
                
                if not movies:
                    logger.info("📊 没有更多电影需要处理")
                    break
                
                # 处理这批电影
                logger.info(f"🎬 处理批次: {len(movies)} 部电影")
                batch_results = self.run_batch(movies)
                
                # 累计结果
                for key in total_results:
                    total_results[key] += batch_results[key]
                
                processed += len(movies)
                last_id = movies[-1][0]  # 更新最后处理的ID
                
                logger.info(f"📊 批次完成: 成功={batch_results['success']}, 部分成功={batch_results['partial_success']}, 失败={batch_results['failed']}")
                
                # 检查是否达到最大处理数量
                if max_movies and processed >= max_movies:
                    logger.info(f"📊 达到最大处理数量: {max_movies}")
                    break
                
                # 批次间隔
                time.sleep(random.uniform(5, 10))
            
            # 输出最终统计
            logger.info("=" * 50)
            logger.info("📊 爬取完成")
            logger.info(f"总数: {total_results['total']}")
            logger.info(f"✅ 成功: {total_results['success']}")
            logger.info(f"⚠️ 部分成功: {total_results['partial_success']}")
            logger.info(f"🚫 失败: {total_results['failed']}")
            
            if total_results['total'] > 0:
                success_rate = (total_results['success'] + total_results['partial_success']) / total_results['total'] * 100
                logger.info(f"成功率: {success_rate:.1f}%")
            
            return True
            
        finally:
            if self.browser:
                self.browser.quit()
                logger.info("🔒 浏览器已关闭")
    
    def get_last_processed_id(self):
        """获取最后处理的ID"""
        try:
            if os.path.exists(self.output_file):
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1].strip()
                        if last_line:
                            data = json.loads(last_line)
                            return data.get('id', 0)
            return 0
        except:
            return 0

def main():
    parser = argparse.ArgumentParser(description='Linux电影爬虫')
    parser.add_argument('--headless', action='store_true', default=True, help='无头模式')
    parser.add_argument('--workers', type=int, default=3, help='并发数')
    parser.add_argument('--batch-size', type=int, default=10, help='批次大小')
    parser.add_argument('--max-movies', type=int, help='最大处理数量')
    parser.add_argument('--daemon', action='store_true', help='守护进程模式')
    
    args = parser.parse_args()
    
    # 加载环境变量
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    crawler = LinuxMovieCrawler(
        headless=args.headless,
        max_workers=args.workers
    )
    
    if args.daemon:
        # 守护进程模式 - 持续运行
        while True:
            try:
                logger.info("🔄 开始新一轮爬取...")
                crawler.run(batch_size=args.batch_size, max_movies=args.max_movies)
                logger.info("😴 等待下一轮...")
                time.sleep(3600)  # 等待1小时
            except KeyboardInterrupt:
                logger.info("👋 收到停止信号，退出...")
                break
            except Exception as e:
                logger.error(f"💥 运行异常: {e}")
                time.sleep(300)  # 等待5分钟后重试
    else:
        # 单次运行模式
        crawler.run(batch_size=args.batch_size, max_movies=args.max_movies)

if __name__ == "__main__":
    main()
