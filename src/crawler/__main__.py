"""Main entry point for the crawler."""

import os
import argparse
import logging
from .core.crawler_manager import CrawlerManager

def setup_logging(log_dir='logs'):
    """Set up logging configuration.
    
    Args:
        log_dir (str): Directory to store log files
    """
    os.makedirs(log_dir, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, 'crawler.log')),
            logging.StreamHandler()
        ]
    )

def run_crawler(args):
    """Run the crawler with specified arguments.
    
    Args:
        args: Command line arguments
    """
    # 设置日志
    setup_logging()
    
    # 创建并启动爬虫管理器
    manager = CrawlerManager(
        clear_existing=args.clear,
        threads=args.threads,
        language=args.language
    )
    manager.start()

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Movie crawler')
    
    parser.add_argument('--clear', 
                       action='store_true',
                       help='Clear existing data')
                       
    parser.add_argument('--threads',
                       type=int,
                       default=3,
                       help='Number of threads to use')
                       
    parser.add_argument('--language',
                       type=str,
                       default='en',
                       choices=['en', 'ja', 'zh'],
                       help='Language code')
    
    args = parser.parse_args()
    run_crawler(args)

if __name__ == '__main__':
    main()
