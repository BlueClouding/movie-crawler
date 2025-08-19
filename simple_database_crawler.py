#!/usr/bin/env python3
"""
简化版数据库爬虫 - 5个并行，使用parse_movie_page，支持重试
"""

import json
import time
import random
import re
import sys
from pathlib import Path
from loguru import logger
from DrissionPage import ChromiumPage, ChromiumOptions

# 配置日志 - 简化版本，保留最近的日志
logger.remove()  # 移除默认配置
logger.add(
    "src/logs/simple_crawler.log",
    rotation="5 MB",  # 文件大小轮转 - 大约5000行左右
    retention=3,  # 保留3个备份文件
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{line} - {message}",
    enqueue=True,  # 异步写入
    encoding="utf-8"
)
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)
from concurrent.futures import ThreadPoolExecutor
import threading
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 导入MovieDetailCrawler和日志配置
sys.path.append(str(Path(__file__).parent / "src"))

# 导入MovieDetailCrawler
movie_crawler_error = None
try:
    from test.test_drission_movie import MovieDetailCrawler
    HAS_MOVIE_CRAWLER = True
except ImportError as e:
    HAS_MOVIE_CRAWLER = False
    movie_crawler_error = str(e)

# 简单日志配置 - 已在上面配置完成

# 记录MovieDetailCrawler导入状态
if HAS_MOVIE_CRAWLER:
    logger.info("✅ 成功导入MovieDetailCrawler")
else:
    logger.warning(f"❌ 无法导入MovieDetailCrawler: {movie_crawler_error}")

class SimpleDatabaseCrawler:
    """简化版数据库爬虫"""
    
    def __init__(self):
        self.browser = None
        self.tabs = []
        self.results = []
        self.failed_movies = []
        self.lock = threading.Lock()
        self.max_retries = 3
        
        # 数据库连接
        self.db_url = "postgresql://postgres:123456@localhost:5432/movie_crawler"
        self.engine = create_engine(self.db_url)
        self.Session = sessionmaker(bind=self.engine)
        
        # 输出文件
        self.output_file = Path("simple_crawl_results.jsonl")
        
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
            
            # 转换为完整URL并修正uncensored-leaked -> uncensored-leak
            movies = []
            for movie_id, link in raw_movies:
                if link.startswith('dm3/v/'):
                    movie_code = link.split('/')[-1]
                    # 修正uncensored-leaked为uncensored-leak
                    if movie_code.endswith('-uncensored-leaked'):
                        movie_code = movie_code.replace('-uncensored-leaked', '-uncensored-leak')
                        logger.info(f"🔧 修正URL: ID={movie_id}, {link.split('/')[-1]} → {movie_code}")
                    full_url = f"https://missav.ai/ja/{movie_code}"
                    movies.append((movie_id, full_url, movie_code))
                elif link.startswith('https://missav.ai/'):
                    movie_code = link.split('/')[-1]
                    # 修正uncensored-leaked为uncensored-leak
                    if movie_code.endswith('-uncensored-leaked'):
                        original_code = movie_code
                        movie_code = movie_code.replace('-uncensored-leaked', '-uncensored-leak')
                        logger.info(f"🔧 修正URL: ID={movie_id}, {original_code} → {movie_code}")
                        full_url = f"https://missav.ai/ja/{movie_code}"
                    else:
                        full_url = link
                    movies.append((movie_id, full_url, movie_code))
                else:
                    parts = link.split('/')
                    if len(parts) > 0:
                        movie_code = parts[-1]
                        # 修正uncensored-leaked为uncensored-leak
                        if movie_code.endswith('-uncensored-leaked'):
                            original_code = movie_code
                            movie_code = movie_code.replace('-uncensored-leaked', '-uncensored-leak')
                            logger.info(f"🔧 修正URL: ID={movie_id}, {original_code} → {movie_code}")
                        full_url = f"https://missav.ai/ja/{movie_code}"
                        movies.append((movie_id, full_url, movie_code))
            
            logger.info(f"📊 从数据库获取到 {len(movies)} 部电影 (ID > {start_id})")
            return movies
            
        except Exception as e:
            logger.error(f"数据库查询失败: {e}")
            return []
        finally:
            session.close()
    
    def create_browser_with_tabs(self):
        """创建浏览器并打开5个标签页"""
        logger.info("🚀 创建浏览器并准备5个标签页")
        
        options = ChromiumOptions()
        options.headless(False)
        options.set_argument('--window-size=1920,1080')
        options.set_argument('--disable-blink-features=AutomationControlled')
        
        self.browser = ChromiumPage(addr_or_opts=options)


        # 建立会话
        logger.info("📱 建立会话...")
        self.browser.get("https://missav.ai/")
        time.sleep(2)
        
        # 创建5个标签页
        self.tabs = [self.browser]
        
        for i in range(4):  # 再创建4个，总共5个
            try:
                time.sleep(0.2)
                new_tab = self.browser.new_tab()
                self.tabs.append(new_tab)
                logger.info(f"✅ 创建标签页 {i+2}/5")
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"创建标签页 {i+2} 失败: {e}")
        
        logger.info(f"🎯 成功创建 {len(self.tabs)} 个标签页")
        return len(self.tabs)
    
    def extract_with_parse_movie_page(self, html, movie_id, movie_code, url):
        """优先提取M3U8的信息提取方法"""
        try:
            if HAS_MOVIE_CRAWLER:
                # 所有电影都优先提取M3U8
                logger.info(f"🎯 优先提取M3U8: {movie_code}")

                # 对于uncensored-leak电影，如果parse_movie_page失败，直接使用正则提取
                if movie_code.endswith('-uncensored-leak'):
                    logger.info(f"🔧 uncensored-leak电影，尝试直接正则提取: {movie_code}")

                    # 先尝试parse_movie_page
                    try:
                        crawler = MovieDetailCrawler(movie_code)
                        result = crawler.parse_movie_page(html)

                        # 检查是否成功提取到M3U8
                        m3u8_urls = result.get('m3u8_urls', [])
                        if len(m3u8_urls) > 0:
                            # 成功提取，使用完整结果
                            result['id'] = movie_id
                            result['timestamp'] = time.time()
                            result['page_length'] = len(html)
                            result['m3u8_links'] = m3u8_urls
                            result['extraction_status'] = 'success_with_m3u8'
                            result['extraction_type'] = 'full_parse_m3u8'
                            logger.info(f"✅ uncensored-leak完整提取成功: {movie_code}, M3U8数量: {len(m3u8_urls)}")
                            return result
                    except Exception as e:
                        logger.warning(f"⚠️ uncensored-leak完整提取失败: {movie_code}, 错误: {e}")


                else:
                    # 普通电影使用完整的parse_movie_page方法
                    crawler = MovieDetailCrawler(movie_code)
                    result = crawler.parse_movie_page(html)

                    # 添加数据库相关字段
                    result['id'] = movie_id
                    result['timestamp'] = time.time()
                    result['page_length'] = len(html)

                    # 检查M3U8提取情况 - 支持两种字段名
                    m3u8_urls = result.get('m3u8_urls', [])  # MovieDetailCrawler使用的字段名
                    m3u8_links = result.get('m3u8_links', [])  # 备用字段名

                    # 统一使用m3u8_links字段名
                    if m3u8_urls and not m3u8_links:
                        result['m3u8_links'] = m3u8_urls
                        m3u8_links = m3u8_urls

                    has_m3u8 = len(m3u8_links) > 0

                    if has_m3u8:
                        result['extraction_status'] = 'success_with_m3u8'
                        result['extraction_type'] = 'full_parse_m3u8'
                        logger.info(f"✅ 成功提取M3U8: {movie_code}, M3U8数量: {len(m3u8_links)}")
                        return result
                    else:
                        # 如果parse_movie_page没有提取到M3U8，尝试简单正则提取
                        logger.warning(f"⚠️ parse_movie_page未提取到M3U8，尝试正则提取: {movie_code}")

                        import re
                        # 提取M3U8链接
                        m3u8_links_regex = re.findall(r'https?://[^"\'>\s]+\.m3u8[^"\'>\s]*', html)

                        if m3u8_links_regex:
                            result['m3u8_links'] = m3u8_links_regex[:5]
                            result['extraction_status'] = 'success_with_regex_m3u8'
                            result['extraction_type'] = 'regex_m3u8'
                            logger.info(f"✅ 正则提取到M3U8: {movie_code}, M3U8数量: {len(m3u8_links_regex)}")
                            return result
                        else:
                            # 没有M3U8但有其他信息也算部分成功
                            result['extraction_status'] = 'partial_success_no_m3u8'
                            result['extraction_type'] = 'full_parse_no_m3u8'
                            logger.warning(f"⚠️ 未找到M3U8但提取了其他信息: {movie_code}")
                            return result
            else:
                # 简化版本 - 至少尝试提取M3U8
                import re
                m3u8_links = re.findall(r'https?://[^"\'>\s]+\.m3u8[^"\'>\s]*', html)
                magnet_links = re.findall(r'magnet:\?[^"\'>\s]+', html)

                info = {
                    'id': movie_id,
                    'code': movie_code,
                    'url': url,
                    'title': "简化提取",
                    'timestamp': time.time(),
                    'page_length': len(html),
                    'm3u8_links': m3u8_links[:5],
                    'magnet_links': magnet_links[:10],
                    'has_m3u8': len(m3u8_links) > 0,
                    'extraction_status': 'success_with_m3u8' if m3u8_links else 'fallback_no_m3u8',
                    'extraction_type': 'fallback'
                }
                logger.info(f"✅ 简化提取: {movie_code}, M3U8: {len(m3u8_links)}")
                return info

        except Exception as e:
            logger.error(f"提取信息出错: {e}")
            return None

    def extract_uncensored_leak_with_regex(self, html, movie_id, movie_code, url):
        """专门为uncensored-leak电影设计的正则提取方法"""
        try:
            import re
            from bs4 import BeautifulSoup

            logger.info(f"🔧 开始正则提取uncensored-leak: {movie_code}")

            # 基础信息
            result = {
                'id': movie_id,
                'code': movie_code,
                'url': url,
                'timestamp': time.time(),
                'page_length': len(html),
                'extraction_type': 'regex_uncensored_leak'
            }

            # 提取标题
            try:
                soup = BeautifulSoup(html, 'html.parser')
                h1_tag = soup.find('h1')
                if h1_tag:
                    title = h1_tag.get_text().strip()
                    result['title'] = title
                    logger.info(f"✅ 正则提取标题: {title[:50]}...")
                else:
                    result['title'] = movie_code
            except:
                result['title'] = movie_code

            # 提取M3U8链接 - 多种模式
            m3u8_patterns = [
                r'https?://[^"\'>\s]+\.m3u8[^"\'>\s]*',
                r'"(https?://[^"]+\.m3u8[^"]*)"',
                r"'(https?://[^']+\.m3u8[^']*)'",
            ]

            all_m3u8 = []
            for pattern in m3u8_patterns:
                matches = re.findall(pattern, html)
                all_m3u8.extend(matches)

            # 去重并限制数量
            unique_m3u8 = list(set(all_m3u8))[:5]
            result['m3u8_links'] = unique_m3u8
            result['m3u8_urls'] = unique_m3u8  # 兼容字段

            # 提取磁力链接
            magnet_links = re.findall(r'magnet:\?[^"\'>\s]+', html)
            result['magnet_links'] = magnet_links[:10]

            # 提取封面
            try:
                cover_match = re.search(r'og:image["\']?\s*content=["\']([^"\']+)', html)
                if cover_match:
                    result['cover'] = cover_match.group(1)
            except:
                pass

            # 提取时长
            try:
                duration_match = re.search(r'(\d+):\d+:\d+', html)
                if duration_match:
                    hours = int(duration_match.group(1))
                    minutes_match = re.search(r'\d+:(\d+):\d+', html)
                    seconds_match = re.search(r'\d+:\d+:(\d+)', html)
                    if minutes_match and seconds_match:
                        minutes = int(minutes_match.group(1))
                        seconds = int(seconds_match.group(1))
                        total_seconds = hours * 3600 + minutes * 60 + seconds
                        result['duration'] = total_seconds
            except:
                pass

            # 设置提取状态
            if len(unique_m3u8) > 0:
                result['extraction_status'] = 'success_with_regex_m3u8'
                logger.info(f"✅ 正则提取成功: {movie_code}, M3U8: {len(unique_m3u8)}, 磁力: {len(magnet_links)}")
            elif len(magnet_links) > 0:
                result['extraction_status'] = 'partial_success_magnet_only'
                logger.info(f"⚠️ 正则提取部分成功: {movie_code}, 无M3U8但有磁力: {len(magnet_links)}")
            else:
                result['extraction_status'] = 'regex_extraction_failed'
                logger.warning(f"🚫 正则提取失败: {movie_code}, 无M3U8和磁力")

            return result

        except Exception as e:
            logger.error(f"❌ 正则提取出错: {movie_code}, 错误: {e}")
            return {
                'id': movie_id,
                'code': movie_code,
                'url': url,
                'title': movie_code,
                'timestamp': time.time(),
                'page_length': len(html),
                'extraction_type': 'regex_failed',
                'extraction_status': 'regex_extraction_error',
                'error': str(e)
            }
    
    def check_404_or_not_found(self, html, current_url, original_url=None, movie_code=None):
        """检查页面是否为404或不存在（智能检测）"""
        if not html:
            return True

        html_lower = html.lower()

        # 检查是否被重定向到主页（URL路径太短）
        if 'missav.ai' in current_url and current_url.count('/') <= 3:
            logger.info(f"🚫 重定向到主页: {current_url}")
            return True

        # 检查页面内容是否过少
        if len(html) < 1000:
            logger.info(f"🚫 页面内容过少: {len(html)} 字符")
            return True

        # 智能404检测：检查页面是否有完整的电影信息
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            # 检查是否有电影标题（H1标签）
            h1_tag = soup.find('h1')
            has_movie_title = h1_tag and len(h1_tag.get_text().strip()) > 10

            # 检查是否包含电影代码
            has_movie_code = movie_code and movie_code.lower() in html_lower

            # 检查是否有视频相关内容
            has_video_content = any(keyword in html_lower for keyword in [
                'video', 'player', 'm3u8', 'magnet', 'download'
            ])

            # 如果有完整的电影信息，即使包含"404"文本也认为是有效页面
            if has_movie_title and has_movie_code and has_video_content:
                logger.info(f"✅ 检测到完整电影信息，认为是有效页面")
                return False

            # 只有在缺少关键信息时才检查404文本
            has_404_text = any(indicator in html_lower for indicator in [
                'page not found', 'ページが見つかりません',
                'お探しのページは見つかりませんでした', 'does not exist', 'error 404'
            ])

            # 更严格的404检测：必须同时满足多个条件
            if has_404_text and not (has_movie_title and has_movie_code):
                logger.info(f"🚫 检测到404错误页面（缺少电影信息）")
                return True

        except Exception as e:
            logger.warning(f"HTML解析出错: {e}")

        # 最后的兜底检查
        if not any(keyword in html_lower for keyword in [
            'missav', 'video', 'movie', 'title', 'content', 'body'
        ]):
            logger.warning(f"🚫 页面不包含任何有效内容标识")
            return True

        return False

    def create_404_placeholder(self, movie_id, movie_code, movie_url):
        """创建404占位符"""
        return {
            'id': movie_id,
            'code': movie_code,
            'url': movie_url,
            'status': '404',
            'title': 'NOT_FOUND',
            'error': 'Movie not found or page does not exist',
            'timestamp': time.time(),
            'page_length': 0
        }

    def crawl_single_movie_with_retry(self, tab, movie_data):
        """爬取单个电影（带重试和404检测，处理重定向）"""
        movie_id, movie_url, movie_code = movie_data

        for attempt in range(self.max_retries):
            try:
                logger.info(f"📍 尝试 {attempt+1}/{self.max_retries}: ID={movie_id}, {movie_code}")

                # 访问页面
                tab.get(movie_url)

                # 简单等待页面加载完成（浏览器自动处理重定向）
                for check in range(3):
                    time.sleep(0.3)
                    html = tab.html
                    current_url = tab.url

                    # 检查页面是否加载完成
                    if html and len(html) > 50000:
                        logger.info(f"✅ ID={movie_id} 页面已加载 ({len(html)} 字符)")
                        if current_url != movie_url:
                            logger.info(f"🔄 ID={movie_id} 最终URL: {current_url}")
                        break
                    elif check == 4:  # 最后一次检查
                        logger.warning(f"⏳ ID={movie_id} 页面加载超时，内容长度: {len(html) if html else 0}")

                # 检查是否为404或不存在
                html = tab.html
                current_url = tab.url

                if self.check_404_or_not_found(html, current_url, movie_url, movie_code):
                    logger.warning(f"🚫 ID={movie_id}: 检测到404或页面不存在")
                    placeholder = self.create_404_placeholder(movie_id, movie_code, movie_url)
                    return placeholder

                # 提取信息
                if html and len(html) > 10000:
                    # 检查是否发生了重定向，如果是则使用重定向后的电影代码
                    final_movie_code = movie_code
                    if current_url != movie_url:
                        # 从最终URL提取电影代码
                        try:
                            final_movie_code = current_url.split('/')[-1]
                            logger.info(f"🔄 ID={movie_id}: 使用重定向后的代码: {movie_code} → {final_movie_code}")
                        except:
                            logger.warning(f"⚠️ ID={movie_id}: 无法从重定向URL提取代码，使用原始代码")

                    movie_info = self.extract_with_parse_movie_page(html, movie_id, final_movie_code, current_url)

                    if movie_info:
                        # 优先检查M3U8 - 有M3U8就算成功
                        m3u8_links = movie_info.get('m3u8_links', [])
                        has_m3u8 = len(m3u8_links) > 0

                        if has_m3u8:
                            movie_info['status'] = 'success'
                            movie_info['success_reason'] = f'has_m3u8_{len(m3u8_links)}'
                            logger.info(f"✅ ID={movie_id}: 成功提取M3U8 ({len(m3u8_links)}个)")
                            return movie_info
                        elif movie_info.get('title') and movie_info.get('title') != "未知标题":
                            # 没有M3U8但有标题等其他信息也算成功
                            movie_info['status'] = 'success'
                            movie_info['success_reason'] = 'has_title_no_m3u8'
                            logger.info(f"✅ ID={movie_id}: 成功提取信息（无M3U8）")
                            return movie_info
                        else:
                            logger.warning(f"⚠️ ID={movie_id}: 信息提取不完整，重试")
                            if attempt < self.max_retries - 1:
                                time.sleep(0.5)
                                continue
                    else:
                        logger.warning(f"⚠️ ID={movie_id}: 信息提取失败，重试")
                        if attempt < self.max_retries - 1:
                            time.sleep(0.5)
                            continue
                else:
                    logger.warning(f"⚠️ ID={movie_id}: 页面内容不足，重试")
                    if attempt < self.max_retries - 1:
                        time.sleep(0.5)
                        continue

            except Exception as e:
                logger.error(f"❌ ID={movie_id} 尝试 {attempt+1} 失败: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2)
                    continue

        logger.error(f"💀 ID={movie_id}: 3次重试均失败")
        # 返回失败占位符
        return {
            'id': movie_id,
            'code': movie_code,
            'url': movie_url,
            'status': 'failed',
            'title': 'EXTRACTION_FAILED',
            'error': 'Failed after 3 retries',
            'timestamp': time.time(),
            'page_length': 0
        }
    
    def save_result(self, movie_info):
        """保存单个结果"""
        try:
            with open(self.output_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(movie_info, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"保存结果失败: {e}")
    
    def crawl_batch(self, movies):
        """爬取一批电影（5个并行）"""
        logger.info(f"🚀 开始爬取 {len(movies)} 部电影")
        
        # 创建浏览器
        if self.create_browser_with_tabs() == 0:
            logger.error("❌ 无法创建标签页")
            return
        
        start_time = time.time()
        
        try:
            # 分批处理，每批5个
            for i in range(0, len(movies), 5):
                batch = movies[i:i + 5]
                batch_num = i // 5 + 1
                total_batches = (len(movies) + 4) // 5
                
                logger.info(f"\n🎬 批次 {batch_num}/{total_batches}: {len(batch)} 部电影")
                
                # 并行处理这一批
                with ThreadPoolExecutor(max_workers=len(self.tabs)) as executor:
                    futures = []
                    
                    for j, movie_data in enumerate(batch):
                        tab = self.tabs[j % len(self.tabs)]
                        future = executor.submit(self.crawl_single_movie_with_retry, tab, movie_data)
                        futures.append((future, movie_data))
                    
                    # 收集结果
                    for future, movie_data in futures:
                        movie_id = movie_data[0]
                        try:
                            result = future.result(timeout=60)
                            if result:
                                with self.lock:
                                    self.results.append(result)
                                    self.save_result(result)

                                    # 根据状态显示不同信息
                                    if result.get('status') == '404':
                                        logger.info(f"🚫 ID={result['id']}: 404 NOT_FOUND")
                                    elif result.get('status') == 'failed':
                                        logger.info(f"💀 ID={result['id']}: EXTRACTION_FAILED")
                                    else:
                                        logger.info(f"✅ ID={result['id']}: {result.get('title', '未知')[:30]}...")
                            else:
                                # 这种情况不应该发生，但以防万一
                                movie_id, movie_url, movie_code = movie_data
                                error_result = {
                                    'id': movie_id,
                                    'code': movie_code,
                                    'url': movie_url,
                                    'status': 'error',
                                    'title': 'UNKNOWN_ERROR',
                                    'error': 'Unexpected None result',
                                    'timestamp': time.time(),
                                    'page_length': 0
                                }
                                with self.lock:
                                    self.results.append(error_result)
                                    self.save_result(error_result)
                                    logger.error(f"❓ ID={movie_id}: UNKNOWN_ERROR")
                        except Exception as e:
                            logger.error(f"❌ ID={movie_id} 处理异常: {e}")
                            # 创建异常占位符
                            movie_id, movie_url, movie_code = movie_data
                            exception_result = {
                                'id': movie_id,
                                'code': movie_code,
                                'url': movie_url,
                                'status': 'exception',
                                'title': 'PROCESSING_EXCEPTION',
                                'error': str(e),
                                'timestamp': time.time(),
                                'page_length': 0
                            }
                            with self.lock:
                                self.results.append(exception_result)
                                self.save_result(exception_result)
                                logger.error(f"💥 ID={movie_id}: PROCESSING_EXCEPTION")
                
                # 批次间休息
                if i + 5 < len(movies):
                    rest_time = random.uniform(2, 3)
                    logger.info(f"😴 批次间休息 {rest_time:.1f} 秒...")
                    time.sleep(rest_time)
        
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

        # 统计不同状态
        success_count = len([r for r in self.results if r.get('status') == 'success'])
        not_found_count = len([r for r in self.results if r.get('status') == '404'])
        failed_count = len([r for r in self.results if r.get('status') == 'failed'])
        exception_count = len([r for r in self.results if r.get('status') in ['exception', 'error']])
        total_processed = len(self.results)

        logger.info(f"\n{'='*50}")
        logger.info(f"📊 爬取完成")
        logger.info(f"总数: {len(movies)}")
        logger.info(f"已处理: {total_processed}")
        logger.info(f"✅ 成功: {success_count}")
        logger.info(f"🚫 404不存在: {not_found_count}")
        logger.info(f"💀 提取失败: {failed_count}")
        logger.info(f"💥 异常错误: {exception_count}")
        logger.info(f"成功率: {success_count/len(movies)*100:.1f}%")
        logger.info(f"有效处理率: {total_processed/len(movies)*100:.1f}%")
        logger.info(f"总时间: {total_time/60:.1f} 分钟")
        logger.info(f"输出文件: {self.output_file}")

        # 显示404电影的代码（便于检查）
        not_found_movies = [r['code'] for r in self.results if r.get('status') == '404']
        if not_found_movies:
            logger.info(f"🚫 404电影代码: {', '.join(not_found_movies[:10])}")
            if len(not_found_movies) > 10:
                logger.info(f"   ... 还有 {len(not_found_movies)-10} 个")

def main():
    """主函数"""
    
    logger.info("🚀 简化版数据库爬虫")
    logger.info("📊 功能特性:")
    logger.info("  - 5个标签页并行")
    logger.info("  - 使用parse_movie_page方法")
    logger.info("  - 失败重试3次")
    logger.info("  - 支持断点继续")
    
    # 询问处理数量
    limit_input = input("\n🔢 限制处理数量 (回车=不限制): ").strip()
    limit = int(limit_input) if limit_input.isdigit() else None
    
    # 确认开始
    start = input(f"\n🚀 开始爬取? [y/n]: ").lower()
    if start != 'y':
        logger.info("👋 下次见！")
        return
    
    # 创建爬虫
    crawler = SimpleDatabaseCrawler()
    
    # 获取断点
    start_id = crawler.get_last_processed_id()
    
    # 获取电影列表
    movies = crawler.get_movies_from_database(start_id, limit)
    if not movies:
        logger.info("📭 没有找到待处理的电影")
        return
    
    # 开始爬取
    crawler.crawl_batch(movies)

if __name__ == "__main__":
    main()
