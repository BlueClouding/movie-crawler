"""Main entry point for the crawler."""

import argparse
import logging
import os
import glob
from datetime import datetime
from .core.progress_manager import ProgressManager
from .core.crawler_manager import CrawlerManager

def setup_logging(log_dir='logs'):
    """Set up logging configuration.
    
    Args:
        log_dir (str): Directory for log files
    """
    from logging.handlers import RotatingFileHandler
    
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'crawler.log')
    
    # 配置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 配置文件处理器，最大 30MB，保留 1 个备份
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=30*1024*1024,  # 30MB
        backupCount=1,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # 配置控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # 配置 root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # 移除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 添加新的处理器
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # 设置 urllib3 的日志级别为 INFO
    logging.getLogger('urllib3').setLevel(logging.INFO)

def run_crawler(args):
    """Run the crawler with the given arguments.
    
    Args:
        args: Command line arguments
    """
    logger = logging.getLogger(__name__)
    
    # Ensure directories exist
    os.makedirs('movie_details', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('genres', exist_ok=True)
    
    # Initialize progress manager
    progress_manager = ProgressManager(language=args.language)
    
    # Clear progress if requested
    if args.clear:
        progress_manager.clear_progress()
    
    # Create and start crawler manager
    if not args.skip_details:
        manager = CrawlerManager(
            clear_existing=args.clear,
            threads=args.threads,
            progress_manager=progress_manager,
            language=args.language
        )
        manager.start()

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='123AV Crawler')
    parser.add_argument('--clear', action='store_true', help='Clear existing data')
    parser.add_argument('--threads', type=int, default=3, help='Number of threads')
    parser.add_argument('--skip-details', action='store_true', help='Skip detail crawling')
    parser.add_argument('--language', type=str, default='en', help='Language code (e.g., en, jp)')
    args = parser.parse_args()
    
    # Set up logging
    setup_logging()
    
    # Run crawler
    run_crawler(args)

if __name__ == '__main__':
    main()
