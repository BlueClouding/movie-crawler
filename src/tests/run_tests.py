#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
运行测试脚本
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 导入测试模块
from test_html_fetcher import save_html, analyze_html_structure
from test_parser_updater import analyze_genres_html, analyze_movie_html

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Run crawler tests')
    parser.add_argument('--base-url', type=str, default='http://123av.com', help='Base URL')
    parser.add_argument('--language', type=str, default='ja', help='Language code')
    parser.add_argument('--output-dir', type=str, default='src/tests/html_data', help='Output directory')
    parser.add_argument('--skip-fetch', action='store_true', help='Skip fetching HTML')
    parser.add_argument('--skip-analysis', action='store_true', help='Skip HTML analysis')
    args = parser.parse_args()
    
    # 确保输出目录存在
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 构建URL
    genres_url = f"{args.base_url}/{args.language}/genres"
    genres_output_path = os.path.join(args.output_dir, 'genres.html')
    
    # 步骤1: 获取HTML
    if not args.skip_fetch:
        logger.info("Step 1: Fetching HTML content...")
        save_html(genres_url, genres_output_path)
    else:
        logger.info("Skipping HTML fetch")
    
    # 步骤2: 分析HTML
    if not args.skip_analysis and os.path.exists(genres_output_path):
        logger.info("Step 2: Analyzing HTML content...")
        analyze_genres_html(genres_output_path, args.base_url, args.language)
        
        # 分析所有电影HTML
        for filename in os.listdir(args.output_dir):
            if filename.startswith('movie_') and filename.endswith('.html'):
                movie_html_path = os.path.join(args.output_dir, filename)
                analyze_movie_html(movie_html_path, args.base_url, args.language)
    else:
        logger.info("Skipping HTML analysis")
    
    logger.info("Tests completed")

if __name__ == '__main__':
    main()
