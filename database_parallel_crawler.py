#!/usr/bin/env python3
"""
数据库并行爬虫 - 支持断点继续
从数据库按ID顺序处理，10个并行，支持断点继续
"""

import json
import time
import random
import re
import sys
from pathlib import Path
from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions
from concurrent.futures import ThreadPoolExecutor
import threading
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from bs4 import BeautifulSoup

# 添加src路径以导入测试模块
src_path = Path(__file__).parent / "src"
sys.path.append(str(src_path))
try:
    from test.test_drission_movie import MovieDetailCrawler
    HAS_DRISSION_CRAWLER = True
    logger.info("成功导入MovieDetailCrawler")
except ImportError:
    HAS_DRISSION_CRAWLER = False
    logger.warning("无法导入MovieDetailCrawler，将使用简化的HTML解析")

class DatabaseParallelCrawler:
    """数据库并行爬虫"""
    
    def __init__(self, max_tabs=5, batch_size=5):
        self.max_tabs = max_tabs
        self.batch_size = batch_size
        self.browser = None
        self.tabs = []
        self.results = []
        self.failed_movies = []
        self.lock = threading.Lock()
        self.max_retries = 3  # 最大重试次数
        
        # 数据库连接
        self.db_url = "postgresql://postgres:123456@localhost:5432/movie_crawler"
        self.engine = create_engine(self.db_url)
        self.Session = sessionmaker(bind=self.engine)
        
        # 输出文件
        self.output_file = Path("database_crawl_results.jsonl")
        
    def get_last_processed_id(self):
        """从JSONL文件获取最后处理的ID"""
        if not self.output_file.exists():
            return 0
        
        last_id = 0
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line.strip())
                        if 'id' in data:
                            last_id = max(last_id, data['id'])
            logger.info(f"📍 找到最后处理的ID: {last_id}")
        except Exception as e:
            logger.warning(f"读取断点文件失败: {e}")
        
        return last_id
    
    def get_movies_from_database(self, start_id=0, limit=None):
        """从数据库获取电影列表"""
        session = self.Session()
        try:
            query = """
                SELECT id, link
                FROM movies
                WHERE id > :start_id
                AND link IS NOT NULL
                AND link != ''
                ORDER BY id ASC
            """

            if limit:
                query += f" LIMIT {limit}"

            result = session.execute(text(query), {"start_id": start_id})
            raw_movies = [(row.id, row.link) for row in result]

            # 转换为完整URL
            movies = []
            for movie_id, link in raw_movies:
                # 如果link是相对路径，转换为完整URL
                if link.startswith('dm3/v/'):
                    # 提取电影代码
                    movie_code = link.split('/')[-1]  # 例如: dm3/v/345simm-656 -> 345simm-656
                    full_url = f"https://missav.ai/ja/{movie_code}"
                    movies.append((movie_id, full_url))
                elif link.startswith('https://missav.ai/'):
                    # 已经是完整URL
                    movies.append((movie_id, link))
                else:
                    # 其他格式，尝试提取电影代码
                    parts = link.split('/')
                    if len(parts) > 0:
                        movie_code = parts[-1]
                        full_url = f"https://missav.ai/ja/{movie_code}"
                        movies.append((movie_id, full_url))

            logger.info(f"📊 从数据库获取到 {len(movies)} 部电影 (ID > {start_id})")
            if movies:
                logger.info(f"📋 示例: ID={movies[0][0]}, URL={movies[0][1]}")
            return movies

        except Exception as e:
            logger.error(f"数据库查询失败: {e}")
            return []
        finally:
            session.close()
    
    def create_browser_with_tabs(self):
        """创建浏览器并打开多个标签页"""
        logger.info(f"🚀 创建浏览器并准备 {self.max_tabs} 个标签页")
        
        options = ChromiumOptions()
        options.headless(False)
        options.set_argument('--window-size=1920,1080')
        options.set_argument('--disable-blink-features=AutomationControlled')
        
        self.browser = ChromiumPage(addr_or_opts=options)
        
        # 建立会话
        logger.info("📱 建立会话...")
        self.browser.get("https://missav.ai/")
        time.sleep(2)
        
        # 创建多个标签页
        self.tabs = [self.browser]
        
        for i in range(self.max_tabs - 1):
            try:
                new_tab = self.browser.new_tab()
                self.tabs.append(new_tab)
                logger.info(f"✅ 创建标签页 {i+2}/{self.max_tabs}")
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"创建标签页 {i+2} 失败: {e}")
        
        logger.info(f"🎯 成功创建 {len(self.tabs)} 个标签页")
        return len(self.tabs)
    
    def extract_movie_info_from_html(self, html, movie_id, movie_code, url):
        """使用parse_movie_page方法提取电影信息"""
        try:
            if HAS_DRISSION_CRAWLER:
                # 使用MovieDetailCrawler的parse_movie_page方法
                crawler = MovieDetailCrawler(movie_code)
                result = crawler.parse_movie_page(html)

                # 添加数据库ID
                result['id'] = movie_id
                result['timestamp'] = time.time()
                result['page_length'] = len(html)

                logger.info(f"使用parse_movie_page成功提取: {movie_code}")
                return result
            else:
                # 简化版本的HTML解析
                soup = BeautifulSoup(html, 'html.parser')

                info = {
                    'id': movie_id,
                    'code': movie_code,
                    'url': url,
                    'timestamp': time.time(),
                    'page_length': len(html)
                }

                # 提取标题
                title_tag = soup.find('h1')
                if title_tag:
                    info['title'] = title_tag.get_text().strip()
                else:
                    info['title'] = "未知标题"

                # 提取女优信息
                actresses = []
                actress_links = soup.find_all('a', href=re.compile(r'/actresses/'))
                for link in actress_links:
                    actress_name = link.get_text().strip()
                    if actress_name and actress_name not in actresses:
                        actresses.append(actress_name)
                info['actresses'] = actresses[:5]  # 最多5个

                # 检查M3U8和磁力链接
                html_lower = html.lower()
                info['has_m3u8'] = 'm3u8' in html_lower
                info['magnet_count'] = html_lower.count('magnet:')

                # 提取磁力链接
                magnet_links = re.findall(r'magnet:\?[^"\'>\s]+', html)
                info['magnet_links'] = magnet_links[:10]  # 最多10个

                logger.info(f"使用简化解析成功提取: {movie_code}")
                return info

        except Exception as e:
            logger.error(f"提取信息出错: {e}")
            return None
    
    def crawl_movie_in_tab_with_retry(self, tab_index, movie_data):
        """在指定标签页中爬取电影（带重试机制）"""
        movie_id, movie_url = movie_data
        tab = self.tabs[tab_index]

        # 从URL提取电影代码
        movie_code = movie_url.split('/')[-1] if '/' in movie_url else "unknown"

        # 重试机制
        for attempt in range(self.max_retries):
            try:
                logger.info(f"📍 [标签页{tab_index+1}] 尝试 {attempt+1}/{self.max_retries}: ID={movie_id}, {movie_code}")

                # 访问页面
                tab.get(movie_url)

                # 快速检查加载状态
                for check in range(3):
                    time.sleep(1)
                    html = tab.html
                    html_length = len(html) if html else 0

                    if html_length > 50000:
                        logger.info(f"✅ [标签页{tab_index+1}] ID={movie_id} 页面已加载 ({html_length} 字符)")
                        break

                # 快速滚动
                try:
                    tab.scroll(500)
                    time.sleep(0.3)
                    tab.scroll(0)
                except:
                    pass

                # 提取信息
                html = tab.html
                if html and len(html) > 10000:
                    movie_info = self.extract_movie_info_from_html(html, movie_id, movie_code, movie_url)

                    # 验证提取结果
                    if movie_info and movie_info.get('title') and movie_info.get('title') != "未知标题":
                        # 线程安全地保存结果
                        with self.lock:
                            self.results.append(movie_info)
                            self.save_single_result(movie_info)
                            logger.info(f"✅ [标签页{tab_index+1}] ID={movie_id}: {movie_info.get('title', '未知')[:30]}...")
                            return True
                    else:
                        logger.warning(f"⚠️ [标签页{tab_index+1}] ID={movie_id}: 信息提取不完整，尝试重试")
                        if attempt < self.max_retries - 1:
                            time.sleep(2)  # 重试前等待
                            continue
                else:
                    logger.warning(f"⚠️ [标签页{tab_index+1}] ID={movie_id}: 页面内容不足，尝试重试")
                    if attempt < self.max_retries - 1:
                        time.sleep(2)  # 重试前等待
                        continue

            except Exception as e:
                logger.error(f"❌ [标签页{tab_index+1}] ID={movie_id} 尝试 {attempt+1} 失败: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2)  # 重试前等待
                    continue

        # 所有重试都失败了
        with self.lock:
            self.failed_movies.append(movie_data)
        logger.error(f"💀 [标签页{tab_index+1}] ID={movie_id}: 3次重试均失败，跳过")
        return False
    
    def save_single_result(self, movie_info):
        """保存单个结果到JSONL文件"""
        try:
            with open(self.output_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(movie_info, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"保存结果失败: {e}")
    
    def parallel_crawl_batch(self, movie_batch):
        """并行爬取一批电影"""
        logger.info(f"🚀 并行处理 {len(movie_batch)} 部电影")
        
        with ThreadPoolExecutor(max_workers=len(self.tabs)) as executor:
            futures = []
            
            for i, movie_data in enumerate(movie_batch):
                tab_index = i % len(self.tabs)
                future = executor.submit(self.crawl_movie_in_tab_with_retry, tab_index, movie_data)
                futures.append((future, movie_data, tab_index))

            # 等待所有任务完成
            for future, movie_data, tab_index in futures:
                try:
                    success = future.result(timeout=60)  # 增加超时时间以适应重试
                except Exception as e:
                    movie_id = movie_data[0]
                    logger.error(f"❌ [标签页{tab_index+1}] ID={movie_id} 超时或出错: {e}")
                    with self.lock:
                        self.failed_movies.append(movie_data)
    
    def run_database_crawl(self, limit=None):
        """运行数据库爬取"""
        logger.info("🚀 开始数据库并行爬取")
        
        # 获取断点
        start_id = self.get_last_processed_id()
        
        # 获取电影列表
        movies = self.get_movies_from_database(start_id, limit)
        if not movies:
            logger.info("📭 没有找到待处理的电影")
            return
        
        # 创建浏览器
        actual_tabs = self.create_browser_with_tabs()
        if actual_tabs == 0:
            logger.error("❌ 无法创建标签页")
            return
        
        logger.info(f"📊 准备处理 {len(movies)} 部电影，批次大小: {self.batch_size}")
        
        start_time = time.time()
        
        try:
            # 分批处理
            for i in range(0, len(movies), self.batch_size):
                batch = movies[i:i + self.batch_size]
                batch_num = i // self.batch_size + 1
                total_batches = (len(movies) + self.batch_size - 1) // self.batch_size
                
                logger.info(f"\n🎬 批次 {batch_num}/{total_batches}: {len(batch)} 部电影")
                logger.info(f"📋 ID范围: {batch[0][0]} - {batch[-1][0]}")
                
                # 并行处理这一批
                self.parallel_crawl_batch(batch)
                
                # 批次间休息
                if i + self.batch_size < len(movies):
                    rest_time = random.uniform(3, 5)
                    logger.info(f"😴 批次间休息 {rest_time:.1f} 秒...")
                    time.sleep(rest_time)
                
                # 显示进度
                elapsed = time.time() - start_time
                processed = min(i + self.batch_size, len(movies))
                avg_time = elapsed / processed
                remaining = (len(movies) - processed) * avg_time
                
                logger.info(f"📊 进度: {processed}/{len(movies)}, "
                          f"平均 {avg_time:.1f}秒/部, 预计剩余 {remaining/60:.1f}分钟")
        
        finally:
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
        logger.info(f"📊 数据库爬取完成")
        logger.info(f"总数: {len(movies)}")
        logger.info(f"成功: {success_count}")
        logger.info(f"失败: {failed_count}")
        logger.info(f"成功率: {success_count/len(movies)*100:.1f}%")
        logger.info(f"总时间: {total_time/60:.1f} 分钟")
        logger.info(f"平均速度: {total_time/len(movies):.1f} 秒/部")
        logger.info(f"输出文件: {self.output_file}")

def main():
    """主函数"""
    
    logger.info("🚀 数据库并行爬虫")
    logger.info("📊 功能特性:")
    logger.info("  - 从数据库按ID顺序处理")
    logger.info("  - 5个标签页并行")
    logger.info("  - 批次大小: 5部电影")
    logger.info("  - 批次间隔: 3-5秒")
    logger.info("  - 支持断点继续")
    logger.info("  - 使用parse_movie_page方法提取")
    logger.info("  - 失败重试3次")
    logger.info("  - 输出到JSONL文件")
    
    # 询问处理数量
    limit_input = input("\n🔢 限制处理数量 (回车=不限制): ").strip()
    limit = int(limit_input) if limit_input.isdigit() else None
    
    if limit:
        logger.info(f"📊 将处理最多 {limit} 部电影")
    else:
        logger.info("📊 将处理所有待处理电影")
    
    # 确认开始
    start = input(f"\n🚀 开始数据库爬取? [y/n]: ").lower()
    if start != 'y':
        logger.info("👋 下次见！")
        return
    
    # 创建爬虫并开始
    crawler = DatabaseParallelCrawler(max_tabs=5, batch_size=5)
    crawler.run_database_crawl(limit=limit)

if __name__ == "__main__":
    main()
