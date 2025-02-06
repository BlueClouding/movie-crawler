"""Crawler manager module for coordinating crawlers."""

import logging
import os
import threading
import time
from .genre_processor import GenreProcessor
from .detail_crawler import DetailCrawler

class CrawlerManager:
    """Manager for coordinating genre processor and detail crawler."""
    
    def __init__(self, clear_existing=False, threads=3, progress_manager=None, language='en'):
        """Initialize the crawler manager.
        
        Args:
            clear_existing (bool): Whether to clear existing data
            threads (int): Number of threads to use
            progress_manager: Optional progress manager instance
            language (str): Language code (e.g., 'en', 'jp')
        """
        self.clear_existing = clear_existing
        self.threads = threads
        self.progress_manager = progress_manager
        self.language = language
        self.logger = logging.getLogger(__name__)
        
        # 创建处理器和爬虫
        self.genre_processor = GenreProcessor(progress_manager, language)
        self.detail_crawler = DetailCrawler(
            clear_existing=clear_existing,
            threads=threads,
            progress_manager=progress_manager,
            language=language
        )
        
        # 创建事件标志
        self.genre_processing_done = threading.Event()
        self.detail_processing_done = threading.Event()
    
    def _genre_processor_thread(self):
        """Genre processor thread function."""
        try:
            # 获取所有类型
            genres = self.genre_processor.process_genres()
            if not genres:
                self.logger.error("Failed to get genres")
                return
            
            # 处理每个类型
            for genre in genres:
                try:
                    self.genre_processor.process_genre(genre)
                except Exception as e:
                    self.logger.error(f"Error processing genre {genre['name']}: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Error in genre processor: {str(e)}")
        finally:
            # 标记类型处理完成
            self.genre_processing_done.set()
    
    def _detail_crawler_thread(self):
        """Detail crawler thread function."""
        try:
            # 等待一会，让 genre_processor 先创建一些文件
            time.sleep(10)
            
            # 获取语言目录
            language_dir = os.path.join('genre_movie', self.language)
            
            # 等待语言目录创建
            while not os.path.exists(language_dir):
                if self.genre_processing_done.is_set():
                    self.logger.info("Genre processing finished without creating language directory")
                    return
                time.sleep(5)
            
            # 开始处理
            while not self.genre_processing_done.is_set() or os.listdir(language_dir):
                try:
                    # 获取所有类型目录
                    genre_dirs = [d for d in os.listdir(language_dir) 
                                  if os.path.isdir(os.path.join(language_dir, d))]
                    
                    if genre_dirs:
                        self.logger.info(f"Found {len(genre_dirs)} genre directories")
                        self.detail_crawler.start()
                    
                except Exception as e:
                    self.logger.error(f"Error in detail crawler: {str(e)}")
                
                # 等待一会再检查
                time.sleep(10)
                
        except Exception as e:
            self.logger.error(f"Error in detail crawler thread: {str(e)}")
        finally:
            # 标记详情爬虫完成
            self.detail_processing_done.set()
    
    def start(self):
        """Start the crawling process."""
        # 创建并启动类型处理线程
        genre_thread = threading.Thread(target=self._genre_processor_thread)
        genre_thread.start()
        
        # 创建并启动详情爬虫线程
        detail_thread = threading.Thread(target=self._detail_crawler_thread)
        detail_thread.start()
        
        # 等待所有线程完成
        genre_thread.join()
        detail_thread.join()
        
        self.logger.info("All crawling tasks completed")
