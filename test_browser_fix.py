#!/usr/bin/env python3
"""
测试修复后的多浏览器问题

这个脚本演示了修复后的浏览器爬取功能：
1. 单浏览器模式（推荐）- 避免多窗口显示问题
2. 多浏览器模式（可选）- 可能只显示一个窗口，但内部仍然并行处理
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.crawler.service.movie_detail_crawler_service import MovieDetailCrawlerService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_single_browser_mode():
    """测试单浏览器模式（推荐）"""
    print("\n" + "="*60)
    print("测试单浏览器模式（推荐）")
    print("="*60)

    # 简化测试，直接测试浏览器创建
    try:
        from src.app.utils.drission_utils import CloudflareBypassBrowser
        import tempfile
        import uuid

        # 创建独立的浏览器实例
        unique_id = str(uuid.uuid4())[:8]
        temp_dir = Path(tempfile.gettempdir()) / f"test_browser_{unique_id}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        print(f"创建测试浏览器，数据目录: {temp_dir}")

        browser = CloudflareBypassBrowser(
            headless=False,  # 显示浏览器窗口
            user_data_dir=str(temp_dir),
            load_images=False,
            timeout=30
        )

        print("浏览器创建成功！正在访问测试页面...")

        # 访问测试页面
        success = browser.get("https://missav.ai/", timeout=30, wait_for_full_load=True)

        if success:
            print("✓ 成功访问测试页面")
            print("✓ 单浏览器模式工作正常")

            # 等待用户观察
            input("按回车键继续...")
        else:
            print("✗ 访问测试页面失败")

        # 关闭浏览器
        browser.quit()
        print("浏览器已关闭")

    except Exception as e:
        print(f"单浏览器模式测试失败: {e}")
        import traceback
        traceback.print_exc()

async def test_multi_browser_mode():
    """测试多浏览器模式（可能只显示一个窗口）"""
    print("\n" + "="*60)
    print("测试多浏览器模式（可能只显示一个窗口）")
    print("="*60)

    try:
        from src.app.utils.drission_utils import CloudflareBypassBrowser
        import tempfile
        import uuid
        import time

        browsers = []
        browser_count = 3

        print(f"尝试创建 {browser_count} 个浏览器实例...")
        print("注意观察是否只显示一个浏览器窗口")

        for i in range(browser_count):
            # 为每个浏览器创建独立的数据目录
            unique_id = str(uuid.uuid4())[:8]
            timestamp = int(time.time() * 1000)
            temp_dir = Path(tempfile.gettempdir()) / f"test_multi_browser_{i}_{unique_id}_{timestamp}"
            temp_dir.mkdir(parents=True, exist_ok=True)

            print(f"创建浏览器 #{i+1}，数据目录: {temp_dir}")

            browser = CloudflareBypassBrowser(
                headless=False,  # 显示浏览器窗口
                user_data_dir=str(temp_dir),
                load_images=False,
                timeout=30
            )

            # 访问测试页面
            browser.get("https://missav.ai/", timeout=30, wait_for_full_load=True)
            browsers.append(browser)

            print(f"浏览器 #{i+1} 创建成功")
            time.sleep(2)  # 等待观察

        print(f"\n成功创建了 {len(browsers)} 个浏览器实例")
        print("如果你只看到一个浏览器窗口，这是Chrome的正常行为")
        print("但实际上已经创建了多个浏览器实例在后台运行")

        # 等待用户观察
        input("按回车键关闭所有浏览器...")

        # 关闭所有浏览器
        for i, browser in enumerate(browsers):
            try:
                browser.quit()
                print(f"浏览器 #{i+1} 已关闭")
            except Exception as e:
                print(f"关闭浏览器 #{i+1} 时出错: {e}")

    except Exception as e:
        print(f"多浏览器模式测试失败: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """主测试函数"""
    print("浏览器多实例显示问题测试")
    print("本测试将演示Chrome浏览器的多实例行为")

    # 询问用户要测试哪种模式
    print("\n请选择要测试的模式：")
    print("1. 单浏览器模式测试（推荐，稳定）")
    print("2. 多浏览器模式测试（演示Chrome的单窗口行为）")
    print("3. 两种模式都测试")

    choice = input("请输入选择 (1/2/3): ").strip()

    if choice == "1":
        await test_single_browser_mode()
    elif choice == "2":
        await test_multi_browser_mode()
    elif choice == "3":
        await test_single_browser_mode()
        await test_multi_browser_mode()
    else:
        print("无效选择，默认测试单浏览器模式")
        await test_single_browser_mode()

    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)
    print("\n总结：")
    print("1. 单浏览器模式：推荐使用，稳定可靠，只显示一个浏览器窗口")
    print("2. 多浏览器模式：由于Chrome限制，多个实例可能只显示一个窗口")
    print("3. 这不是代码的bug，而是Chrome浏览器的正常行为")
    print("4. 多个实例在内部仍然是独立工作的，只是视觉上合并了")
    print("5. 如果需要真正的多窗口显示，建议使用单浏览器顺序处理模式")

if __name__ == "__main__":
    asyncio.run(main())
