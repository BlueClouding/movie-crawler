#!/usr/bin/env python3
"""
超级简单的手动辅助工具
让人类手动操作，程序只负责提取信息
"""

import time
import json
from pathlib import Path
from loguru import logger
from DrissionPage import ChromiumPage
import re

class ManualCrawlerHelper:
    """手动爬虫辅助工具"""
    
    def __init__(self):
        self.results = []
        self.current_movie = None
        
    def start_browser(self):
        """启动浏览器，让用户手动操作"""
        logger.info("🚀 启动浏览器...")
        logger.info("💡 请手动打开 https://missav.ai 并完成任何验证")
        
        # 连接到现有的Chrome实例（如果有的话）
        try:
            self.browser = ChromiumPage()
            logger.info("✅ 已连接到浏览器")
        except:
            logger.error("❌ 无法连接到浏览器，请先手动打开Chrome")
            return False
        
        return True
    
    def wait_for_user_navigation(self, target_movie_code):
        """等待用户手动导航到目标页面"""
        self.current_movie = target_movie_code
        target_url_pattern = f"missav.ai/ja/{target_movie_code}"
        
        logger.info(f"🎯 请手动导航到: https://missav.ai/ja/{target_movie_code}")
        logger.info("⏳ 等待您手动打开页面...")
        
        # 等待用户导航到正确页面
        while True:
            try:
                current_url = self.browser.url
                if target_url_pattern in current_url:
                    logger.info(f"✅ 检测到正确页面: {current_url}")
                    break
                else:
                    logger.info(f"📍 当前页面: {current_url}")
                    logger.info(f"⏳ 等待导航到包含 '{target_url_pattern}' 的页面...")
                    time.sleep(3)
            except Exception as e:
                logger.warning(f"检查URL时出错: {e}")
                time.sleep(3)
    
    def extract_movie_info(self):
        """从当前页面提取电影信息"""
        try:
            logger.info("📊 开始提取电影信息...")
            
            # 等待页面完全加载
            time.sleep(2)
            
            # 获取页面HTML
            html = self.browser.html
            
            if not html or len(html) < 5000:
                logger.warning(f"页面内容可能不完整: {len(html) if html else 0} 字符")
                return None
            
            # 提取基本信息
            info = {
                'code': self.current_movie,
                'url': self.browser.url,
                'timestamp': time.time()
            }
            
            # 提取标题
            try:
                title_element = self.browser.ele('tag:h1')
                if title_element:
                    info['title'] = title_element.text.strip()
                    logger.info(f"📝 标题: {info['title']}")
            except:
                info['title'] = "未知标题"
            
            # 提取女优信息
            try:
                actress_elements = self.browser.eles('css:.actress-name') or self.browser.eles('css:.text-secondary')
                actresses = []
                for elem in actress_elements:
                    if elem.text and elem.text.strip():
                        actresses.append(elem.text.strip())
                info['actresses'] = actresses[:5]  # 最多5个
                logger.info(f"👩 女优: {', '.join(actresses[:3])}")
            except:
                info['actresses'] = []
            
            # 提取时长
            try:
                duration_text = self.browser.ele('text:分钟') or self.browser.ele('text:min')
                if duration_text:
                    duration_match = re.search(r'(\d+)', duration_text.text)
                    if duration_match:
                        info['duration_minutes'] = int(duration_match.group(1))
                        logger.info(f"⏱️ 时长: {info['duration_minutes']} 分钟")
            except:
                info['duration_minutes'] = 0
            
            # 提取发布日期
            try:
                date_element = self.browser.ele('text:发布日期') or self.browser.ele('text:Release Date')
                if date_element:
                    info['release_date'] = date_element.text.strip()
                    logger.info(f"📅 发布日期: {info['release_date']}")
            except:
                info['release_date'] = "未知"
            
            # 简单检查M3U8链接
            try:
                if 'm3u8' in html.lower():
                    info['has_m3u8'] = True
                    logger.info("🎥 检测到视频流")
                else:
                    info['has_m3u8'] = False
            except:
                info['has_m3u8'] = False
            
            # 检查磁力链接
            try:
                magnet_count = html.lower().count('magnet:')
                info['magnet_count'] = magnet_count
                if magnet_count > 0:
                    logger.info(f"🧲 检测到 {magnet_count} 个磁力链接")
            except:
                info['magnet_count'] = 0
            
            logger.info("✅ 信息提取完成")
            return info
            
        except Exception as e:
            logger.error(f"提取信息时出错: {e}")
            return None
    
    def save_result(self, movie_info):
        """保存结果"""
        if movie_info:
            self.results.append(movie_info)
            
            # 保存到文件
            output_file = Path("manual_crawl_results.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 结果已保存到: {output_file}")
    
    def interactive_crawl(self, movie_codes):
        """交互式爬取"""
        logger.info(f"🎯 开始交互式爬取 {len(movie_codes)} 部电影")
        logger.info("💡 您需要手动导航，程序会自动提取信息")
        
        if not self.start_browser():
            return []
        
        for i, movie_code in enumerate(movie_codes, 1):
            logger.info(f"\n{'='*50}")
            logger.info(f"🎬 第 {i}/{len(movie_codes)} 部电影: {movie_code}")
            logger.info(f"{'='*50}")
            
            # 等待用户手动导航
            self.wait_for_user_navigation(movie_code)
            
            # 询问用户是否准备好提取
            input(f"\n✋ 请确认页面已完全加载，然后按回车键开始提取 {movie_code} 的信息...")
            
            # 提取信息
            movie_info = self.extract_movie_info()
            
            # 保存结果
            self.save_result(movie_info)
            
            if movie_info:
                logger.info(f"✅ {movie_code} 处理完成")
            else:
                logger.error(f"❌ {movie_code} 处理失败")
            
            # 如果不是最后一个，询问是否继续
            if i < len(movie_codes):
                continue_choice = input(f"\n🤔 是否继续处理下一部电影 ({movie_codes[i]})? [y/n]: ").lower()
                if continue_choice != 'y':
                    logger.info("🛑 用户选择停止")
                    break
        
        return self.results

def main():
    """主函数"""
    
    # 测试电影列表
    test_movies = [
        "ipzz-562",
        "sone-718", 
        "ngod-266"
    ]
    
    logger.info("🎯 超级简单的手动辅助爬虫")
    logger.info("💡 策略: 您手动操作浏览器，程序自动提取信息")
    logger.info("🔧 这样可以100%绕过Cloudflare，因为是真人操作！")
    logger.info(f"📋 待处理电影: {test_movies}")
    
    print("\n" + "="*60)
    print("📋 使用说明:")
    print("1. 程序会启动浏览器连接")
    print("2. 请手动打开 https://missav.ai")
    print("3. 完成任何Cloudflare验证")
    print("4. 程序会提示您导航到特定电影页面")
    print("5. 页面加载完成后按回车，程序自动提取信息")
    print("6. 重复直到所有电影处理完成")
    print("="*60)
    
    start_choice = input("\n🚀 准备开始了吗? [y/n]: ").lower()
    if start_choice != 'y':
        logger.info("👋 下次见！")
        return
    
    # 创建助手并开始
    helper = ManualCrawlerHelper()
    results = helper.interactive_crawl(test_movies)
    
    # 输出最终结果
    logger.info("\n" + "="*50)
    logger.info("📊 最终结果")
    logger.info(f"总数: {len(test_movies)}")
    logger.info(f"成功: {len(results)}")
    logger.info(f"成功率: {len(results)/len(test_movies)*100:.1f}%")
    
    for result in results:
        logger.info(f"✅ {result['code']}: {result.get('title', '未知')}")

if __name__ == "__main__":
    main()
