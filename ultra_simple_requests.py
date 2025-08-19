#!/usr/bin/env python3
"""
终极简单方法：直接用requests
看看能不能直接获取页面，绕过所有复杂的浏览器操作
"""

import requests
import time
import random
from bs4 import BeautifulSoup
from loguru import logger

def create_human_like_session():
    """创建一个像人类的requests会话"""
    session = requests.Session()
    
    # 设置真实的浏览器头
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    })
    
    return session

def simple_get_page(session, url, max_retries=3):
    """简单获取页面"""
    
    for attempt in range(max_retries):
        try:
            logger.info(f"📡 尝试 {attempt + 1}/{max_retries}: {url}")
            
            # 随机延迟，像人类一样
            if attempt > 0:
                delay = random.uniform(5, 15)
                logger.info(f"⏳ 等待 {delay:.1f} 秒后重试...")
                time.sleep(delay)
            
            # 发送请求
            response = session.get(url, timeout=30)
            
            logger.info(f"📊 状态码: {response.status_code}")
            logger.info(f"📏 内容长度: {len(response.text)} 字符")
            
            # 检查是否成功
            if response.status_code == 200:
                # 检查是否是Cloudflare页面
                if 'cloudflare' in response.text.lower() or 'challenge' in response.text.lower():
                    logger.warning("⚠️ 检测到Cloudflare挑战页面")
                    continue
                
                # 检查是否包含预期内容
                if 'missav' in response.text.lower() and len(response.text) > 10000:
                    logger.info("✅ 成功获取页面内容")
                    return response.text
                else:
                    logger.warning("⚠️ 页面内容可能不完整")
                    continue
            
            elif response.status_code == 403:
                logger.warning("🚫 403 Forbidden - 可能被Cloudflare阻止")
                continue
            
            elif response.status_code == 503:
                logger.warning("⏳ 503 Service Unavailable - 服务器忙碌")
                continue
            
            else:
                logger.warning(f"❓ 未知状态码: {response.status_code}")
                continue
                
        except requests.exceptions.Timeout:
            logger.warning("⏰ 请求超时")
            continue
        except requests.exceptions.ConnectionError:
            logger.warning("🔌 连接错误")
            continue
        except Exception as e:
            logger.error(f"❌ 请求出错: {e}")
            continue
    
    logger.error(f"❌ 所有重试均失败: {url}")
    return None

def extract_movie_info_from_html(html, movie_code):
    """从HTML中提取电影信息"""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        info = {
            'code': movie_code,
            'timestamp': time.time()
        }
        
        # 提取标题
        title_tag = soup.find('h1') or soup.find('title')
        if title_tag:
            info['title'] = title_tag.get_text().strip()
            logger.info(f"📝 标题: {info['title'][:50]}...")
        else:
            info['title'] = "未知标题"
        
        # 检查是否包含视频相关内容
        html_lower = html.lower()
        
        # 检查M3U8
        if 'm3u8' in html_lower:
            info['has_m3u8'] = True
            logger.info("🎥 检测到M3U8视频流")
        else:
            info['has_m3u8'] = False
        
        # 检查磁力链接
        magnet_count = html_lower.count('magnet:')
        info['magnet_count'] = magnet_count
        if magnet_count > 0:
            logger.info(f"🧲 检测到 {magnet_count} 个磁力链接")
        
        # 页面质量评估
        info['page_length'] = len(html)
        info['has_video_content'] = 'video' in html_lower or 'player' in html_lower
        
        logger.info("✅ 信息提取完成")
        return info
        
    except Exception as e:
        logger.error(f"❌ 提取信息时出错: {e}")
        return None

def test_simple_requests(movie_codes):
    """测试简单的requests方法"""
    
    logger.info("🚀 测试终极简单方法：直接用requests")
    logger.info("💡 看看能否绕过所有复杂的浏览器操作")
    
    # 创建会话
    session = create_human_like_session()
    
    # 首先测试主页
    logger.info("🏠 首先测试主页访问...")
    main_page = simple_get_page(session, "https://missav.ai/")
    
    if main_page:
        logger.info("✅ 主页访问成功")
    else:
        logger.warning("⚠️ 主页访问失败，但继续尝试电影页面...")
    
    # 测试电影页面
    results = []
    
    for i, movie_code in enumerate(movie_codes, 1):
        logger.info(f"\n{'='*50}")
        logger.info(f"🎬 第 {i}/{len(movie_codes)} 部电影: {movie_code}")
        logger.info(f"{'='*50}")
        
        url = f"https://missav.ai/ja/{movie_code}"
        
        # 获取页面
        html = simple_get_page(session, url)
        
        if html:
            # 提取信息
            movie_info = extract_movie_info_from_html(html, movie_code)
            if movie_info:
                results.append(movie_info)
                logger.info(f"✅ {movie_code} 处理成功")
            else:
                logger.error(f"❌ {movie_code} 信息提取失败")
        else:
            logger.error(f"❌ {movie_code} 页面获取失败")
        
        # 电影之间的延迟
        if i < len(movie_codes):
            delay = random.uniform(10, 30)
            logger.info(f"😴 等待 {delay:.1f} 秒后处理下一部电影...")
            time.sleep(delay)
    
    return results

def main():
    """主函数"""
    
    # 测试电影列表
    test_movies = [
        "ipzz-562",
        "sone-718", 
        "ngod-266"
    ]
    
    logger.info("🎯 终极简单测试")
    logger.info("💭 你说得对，这本来应该很简单！")
    logger.info("🧪 让我们看看最简单的requests能否成功...")
    logger.info(f"📋 测试电影: {test_movies}")
    
    # 开始测试
    results = test_simple_requests(test_movies)
    
    # 输出结果
    logger.info("\n" + "="*50)
    logger.info("📊 终极简单测试结果")
    logger.info(f"总数: {len(test_movies)}")
    logger.info(f"成功: {len(results)}")
    logger.info(f"失败: {len(test_movies) - len(results)}")
    logger.info(f"成功率: {len(results)/len(test_movies)*100:.1f}%")
    
    if results:
        logger.info("\n✅ 成功的电影:")
        for result in results:
            logger.info(f"  - {result['code']}: {result.get('title', '未知')[:50]}...")
    
    if len(results) == 0:
        logger.info("\n💭 看来即使是最简单的requests也被Cloudflare拦截了...")
        logger.info("🤷‍♂️ 这就是为什么需要复杂的绕过方法的原因")
        logger.info("💡 建议使用手动辅助工具: python super_simple_manual_helper.py")
    elif len(results) == len(test_movies):
        logger.info("\n🎉 太棒了！原来最简单的方法就是最好的！")
        logger.info("💡 看来Cloudflare对requests没有那么严格")
    else:
        logger.info("\n🤔 部分成功，可能需要调整策略")

if __name__ == "__main__":
    main()
