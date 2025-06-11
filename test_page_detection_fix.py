#!/usr/bin/env python3
"""
测试页面检测逻辑修复

这个脚本测试修复后的页面检测逻辑，确保不会出现"页面未完全加载"的误报。
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_page_detection():
    """测试页面检测逻辑"""
    print("\n" + "="*60)
    print("测试页面检测逻辑修复")
    print("="*60)
    
    try:
        from src.app.utils.drission_utils import CloudflareBypassBrowser
        import tempfile
        import uuid
        
        # 创建浏览器实例
        unique_id = str(uuid.uuid4())[:8]
        temp_dir = Path(tempfile.gettempdir()) / f"test_page_detection_{unique_id}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"创建测试浏览器，数据目录: {temp_dir}")
        
        browser = CloudflareBypassBrowser(
            headless=False,  # 显示浏览器窗口以便观察
            user_data_dir=str(temp_dir),
            load_images=False,
            timeout=30
        )
        
        # 测试电影URL列表
        test_urls = [
            "https://missav.ai/ja/REBDB-917",  # 之前失败的URL
            "https://missav.ai/ja/RBK-033",   # 之前失败的URL
            "https://missav.ai/ja/SSIS-001",  # 一个常见的测试URL
        ]
        
        print(f"将测试 {len(test_urls)} 个URL的页面检测")
        
        for i, url in enumerate(test_urls):
            print(f"\n--- 测试 {i+1}/{len(test_urls)}: {url} ---")
            
            try:
                # 访问页面
                print(f"正在访问: {url}")
                success = browser.get(url, timeout=30, wait_for_full_load=False)
                
                if not success:
                    print(f"❌ 浏览器访问失败: {url}")
                    continue
                
                time.sleep(2)  # 给页面一些加载时间
                
                # 执行改进后的页面检测脚本
                check_script = """
                () => {
                    // 检查页面基本结构是否加载完成
                    const body = document.body;
                    if (!body) {
                        return {'status': 'loading', 'reason': 'body not found'};
                    }
                    
                    // 检查页面内容长度
                    const bodyText = body.innerText || body.textContent || '';
                    if (bodyText.length < 100) {
                        return {'status': 'loading', 'reason': 'content too short'};
                    }
                    
                    // 检查是否有Cloudflare挑战页面
                    if (bodyText.includes('Checking your browser') || 
                        bodyText.includes('Please wait') ||
                        bodyText.includes('DDoS protection')) {
                        return {'status': 'loading', 'reason': 'cloudflare challenge'};
                    }
                    
                    // 检查多种可能的页面元素
                    const indicators = [
                        document.querySelector('meta[property="og:title"]'),
                        document.querySelector('.movie-info-panel'),
                        document.querySelector('h1'),
                        document.querySelector('.video-player'),
                        document.querySelector('.movie-detail'),
                        document.querySelector('title')
                    ];
                    
                    const foundIndicators = indicators.filter(el => el !== null);
                    
                    if (foundIndicators.length > 0) {
                        const title = document.querySelector('meta[property="og:title"]')?.getAttribute('content') ||
                                    document.querySelector('h1')?.textContent ||
                                    document.title ||
                                    'Found content';
                        return {'status': 'ready', 'title': title.trim(), 'indicators': foundIndicators.length};
                    }
                    
                    // 如果没有找到特定元素，但页面内容足够长，也认为加载完成
                    if (bodyText.length > 1000) {
                        return {'status': 'ready', 'title': 'Content loaded', 'contentLength': bodyText.length};
                    }
                    
                    return {'status': 'loading', 'reason': 'no indicators found'};
                }
                """
                
                # 执行检测脚本
                page_status = browser.run_js(check_script)
                
                if isinstance(page_status, dict):
                    status = page_status.get('status', 'unknown')
                    if status == 'ready':
                        title = page_status.get('title', 'Unknown')
                        indicators = page_status.get('indicators', 0)
                        content_length = page_status.get('contentLength', 0)
                        
                        print(f"✅ 页面检测通过")
                        print(f"   标题: {title[:50]}...")
                        if indicators:
                            print(f"   找到 {indicators} 个页面指示器")
                        if content_length:
                            print(f"   页面内容长度: {content_length} 字符")
                    else:
                        reason = page_status.get('reason', 'unknown')
                        print(f"⚠️  页面检测未通过，原因: {reason}")
                        print(f"   但根据新逻辑，仍会继续处理")
                else:
                    print(f"❌ 页面检测脚本执行失败")
                
                # 获取HTML内容长度
                html_content = browser.html
                if html_content:
                    print(f"   HTML内容长度: {len(html_content)} 字符")
                else:
                    print(f"   无法获取HTML内容")
                
            except Exception as e:
                print(f"❌ 测试URL时出错: {e}")
            
            # 在URL之间添加延迟
            if i < len(test_urls) - 1:
                time.sleep(2)
        
        # 关闭浏览器
        browser.quit()
        print("\n浏览器已关闭")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """主测试函数"""
    print("页面检测逻辑修复测试")
    print("本测试将验证修复后的页面检测逻辑是否能正确处理各种页面")
    
    await test_page_detection()
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)
    print("\n修复说明：")
    print("1. 改进了页面检测逻辑，使用更宽松的检查条件")
    print("2. 检查多种页面元素，而不是依赖特定元素")
    print("3. 如果页面内容足够长，即使没有特定元素也认为加载完成")
    print("4. 信任CloudflareBypassBrowser的判断，避免误报")
    print("5. 降低了HTML内容长度的要求")

if __name__ == "__main__":
    asyncio.run(main())
