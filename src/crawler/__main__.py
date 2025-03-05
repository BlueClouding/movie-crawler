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

async def run_crawler(args):
    """Run the crawler with specified arguments.
    
    Args:
        args: Command line arguments
    """
    import asyncio
    from app.config.settings import settings
    
    # 设置日志
    setup_logging()
    
    # 创建并启动爬虫管理器
    manager = CrawlerManager(
        base_url=args.base_url,
        task_id=args.task_id,
        language=args.language,
        threads=args.threads,
        clear_existing=args.clear,
        output_dir=args.output_dir
    )
    
    # 初始化并启动爬虫
    await manager.initialize_and_start()

def main():
    """Main entry point."""
    import asyncio
    
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
                       default='ja',
                       choices=['en', 'ja', 'zh'],
                       help='Language code')
                       
    parser.add_argument('--base-url',
                       type=str,
                       default='http://123av.com',
                       help='Base URL for the website')
                       
    parser.add_argument('--task-id',
                       type=int,
                       default=1,
                       help='Task ID for tracking progress')
                       
    parser.add_argument('--output-dir',
                       type=str,
                       help='Directory to save images')
    
    args = parser.parse_args()
    
    # 运行爬虫（异步）
    asyncio.run(run_crawler(args))

if __name__ == '__main__':
    main()
