#!/usr/bin/env python3
"""
调试Cloudflare绕过问题的脚本
用于诊断M3U8提取失败的原因
"""

import sys
import time
import re
from pathlib import Path
from bs4 import BeautifulSoup
from loguru import logger

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from src.app.utils.drission_utils import CloudflareBypassBrowser

def analyze_page_content(html_content: str) -> dict:
    """分析页面内容，检查是否包含预期的元素"""
    soup = BeautifulSoup(html_content, "html.parser")
    
    analysis = {
        'page_length': len(html_content),
        'title': soup.title.string if soup.title else "无标题",
        'has_cloudflare_challenge': False,
        'has_movie_content': False,
        'script_count': len(soup.find_all('script')),
        'has_eval_function': False,
        'has_m3u8_pattern': False,
        'cloudflare_indicators': []
    }
    
    # 检查Cloudflare挑战指标
    cf_indicators = [
        'Cloudflare',
        '安全检查',
        'Security Challenge',
        'チェックしています',
        'cf-spinner',
        'challenge-form'
    ]
    
    for indicator in cf_indicators:
        if indicator in html_content:
            analysis['cloudflare_indicators'].append(indicator)
            analysis['has_cloudflare_challenge'] = True
    
    # 检查电影内容
    movie_indicators = [
        'class="grid-cols-2"',
        'property="og:title"',
        'property="og:video"',
        'missav.ai',
        'video-player'
    ]
    
    for indicator in movie_indicators:
        if indicator in html_content:
            analysis['has_movie_content'] = True
            break
    
    # 检查JavaScript加密代码
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string:
            if 'eval(function(p,a,c,k,e,d)' in script.string:
                analysis['has_eval_function'] = True
            if 'm3u8' in script.string.lower():
                analysis['has_m3u8_pattern'] = True
    
    return analysis

def test_cloudflare_bypass_detailed():
    """详细测试Cloudflare绕过功能"""
    logger.info("🚀 开始详细测试Cloudflare绕过功能")
    
    # 测试URL列表
    test_urls = [
        "https://missav.ai/ja/ure-122",
        "https://missav.ai/ja/jur-307",
        "https://missav.ai/ja"  # 主页
    ]
    
    # 创建用户数据目录
    user_data_dir = Path.home() / ".cache" / "cf_bypass_debug"
    user_data_dir.mkdir(parents=True, exist_ok=True)
    
    browser = None
    try:
        # 初始化浏览器
        logger.info("🔧 初始化浏览器...")
        browser = CloudflareBypassBrowser(
            headless=False,  # 显示浏览器便于调试
            user_data_dir=str(user_data_dir),
            load_images=False,  # 不加载图片，提高速度
            wait_after_cf=8  # 增加Cloudflare挑战后的等待时间
        )
        
        for i, url in enumerate(test_urls, 1):
            logger.info(f"\n📋 测试 {i}/{len(test_urls)}: {url}")
            
            # 访问页面
            success = browser.get(url, wait_for_cf=True, timeout=120)
            
            if success:
                logger.info("✅ 页面加载成功")
                
                # 获取页面内容
                html_content = browser.get_html()
                
                # 分析页面内容
                analysis = analyze_page_content(html_content)
                
                logger.info(f"📊 页面分析结果:")
                logger.info(f"  - 页面长度: {analysis['page_length']} 字符")
                logger.info(f"  - 标题: {analysis['title']}")
                logger.info(f"  - Script标签数量: {analysis['script_count']}")
                logger.info(f"  - 包含Cloudflare挑战: {analysis['has_cloudflare_challenge']}")
                logger.info(f"  - 包含电影内容: {analysis['has_movie_content']}")
                logger.info(f"  - 包含eval函数: {analysis['has_eval_function']}")
                logger.info(f"  - 包含M3U8模式: {analysis['has_m3u8_pattern']}")
                
                if analysis['cloudflare_indicators']:
                    logger.warning(f"  - Cloudflare指标: {analysis['cloudflare_indicators']}")
                
                # 如果是电影页面，尝试提取M3U8信息
                if 'ure-122' in url or 'jur-307' in url:
                    logger.info("🎬 尝试提取M3U8信息...")
                    m3u8_result = extract_m3u8_debug(html_content)
                    
                    if m3u8_result['found']:
                        logger.info(f"✅ 成功找到M3U8加密信息")
                        logger.info(f"  - 加密代码长度: {len(m3u8_result['encrypted_code'])}")
                        logger.info(f"  - 字典长度: {len(m3u8_result['dictionary'])}")
                    else:
                        logger.error("❌ 未找到M3U8加密信息")
                        
                        # 保存页面内容用于调试
                        debug_file = f"debug_page_{url.split('/')[-1]}.html"
                        with open(debug_file, 'w', encoding='utf-8') as f:
                            f.write(html_content)
                        logger.info(f"💾 页面内容已保存到: {debug_file}")
                
                # 等待一段时间再测试下一个URL
                if i < len(test_urls):
                    logger.info("⏳ 等待5秒后测试下一个URL...")
                    time.sleep(5)
                    
            else:
                logger.error(f"❌ 页面加载失败: {url}")
    
    except Exception as e:
        logger.error(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if browser:
            logger.info("🔒 关闭浏览器...")
            browser.close()

def extract_m3u8_debug(html_content: str) -> dict:
    """调试版本的M3U8提取函数"""
    result = {
        'found': False,
        'encrypted_code': '',
        'dictionary': [],
        'debug_info': []
    }
    
    soup = BeautifulSoup(html_content, "html.parser")
    scripts = soup.find_all('script')
    
    result['debug_info'].append(f"找到 {len(scripts)} 个script标签")
    
    # 正则表达式模式
    pattern = re.compile(
        r"eval\(function\(p,a,c,k,e,d\)\{(.+?)\}\('(.+?)',([0-9]+),([0-9]+),'(.+?)'\.((?:split\('\|'\))|(?:split\('\|'\),0,\{\}))\)"
    )
    
    for i, script in enumerate(scripts):
        if script.string:
            script_content = script.string
            result['debug_info'].append(f"Script {i+1}: 长度 {len(script_content)} 字符")
            
            if "eval(function(p,a,c,k,e,d)" in script_content:
                result['debug_info'].append(f"Script {i+1}: 包含eval函数")
                
                matcher = pattern.search(script_content)
                if matcher:
                    dictionary_str = matcher.group(5)
                    dictionary = dictionary_str.split("|") if dictionary_str else []
                    encrypted_code = matcher.group(2)
                    
                    result['found'] = True
                    result['encrypted_code'] = encrypted_code
                    result['dictionary'] = dictionary
                    result['debug_info'].append(f"Script {i+1}: 成功匹配加密模式")
                    break
                else:
                    result['debug_info'].append(f"Script {i+1}: eval函数存在但模式不匹配")
    
    return result

if __name__ == "__main__":
    test_cloudflare_bypass_detailed()
