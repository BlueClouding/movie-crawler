#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试手动传入cookie功能的脚本

使用说明：
1. 打开浏览器，登录到 https://123av.com/ja
2. 打开开发者工具 (F12)
3. 进入 Network 标签页
4. 刷新页面或访问任意页面
5. 找到任意请求，查看 Request Headers 中的 Cookie 值
6. 复制完整的 Cookie 字符串，替换下面的 MANUAL_COOKIE 变量

示例 Cookie 格式：
_ga=GA1.1.1641394730.1737617680; locale=ja; session=abcd1234efgh5678; x-token=your_actual_token_here;
"""

import logging
from feed_service import FeedService

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 请将此处替换为您从浏览器复制的实际cookie
# 注意：这里的cookie是示例，需要替换为真实有效的cookie
MANUAL_COOKIE = "_ga=GA1.1.1641394730.1737617680; locale=ja; session=YOUR_SESSION_HERE; x-token=YOUR_TOKEN_HERE;"

def test_manual_cookie():
    """测试手动传入cookie功能"""
    print("=== 测试手动传入cookie功能 ===")
    
    # 检查cookie是否为示例cookie
    if "YOUR_SESSION_HERE" in MANUAL_COOKIE or "YOUR_TOKEN_HERE" in MANUAL_COOKIE:
        print("❌ 检测到示例cookie，请先替换为真实的cookie")
        print("请按照脚本顶部的使用说明获取真实cookie")
        return False
    
    try:
        # 创建FeedService实例，传入手动cookie
        feed_service = FeedService(manual_cookie=MANUAL_COOKIE)
        
        print("\n1. 测试获取feed页面总数...")
        total_pages = feed_service.get_total_feed_pages()
        print(f"总页数: {total_pages}")
        
        if total_pages > 0:
            print("\n2. 测试获取第一页电影信息...")
            movies = feed_service.get_movies_from_feed_page(1)
            print(f"第一页找到 {len(movies)} 个电影")
            
            # 显示前3个电影信息
            for i, movie in enumerate(list(movies)[:3]):
                print(f"电影 {i+1}: {movie.title} (ID: {movie.original_id})")
            
            print("\n✅ 手动cookie测试成功")
            return True
        else:
            print("\n❌ 手动cookie测试失败：无法获取页面数据")
            print("可能的原因：")
            print("1. Cookie已过期，请重新获取")
            print("2. Cookie格式不正确")
            print("3. 网站结构发生变化")
            return False
        
    except Exception as e:
        print(f"❌ 手动cookie测试失败: {e}")
        logger.error(f"手动cookie测试错误: {e}")
        return False

def test_backward_compatibility():
    """测试向后兼容性（不传入cookie参数）"""
    print("\n=== 测试向后兼容性（自动登录） ===")
    
    try:
        # 创建FeedService实例，不传入cookie参数（使用自动登录）
        feed_service = FeedService()
        
        print("\n1. 测试获取feed页面总数（自动登录）...")
        total_pages = feed_service.get_total_feed_pages()
        print(f"总页数: {total_pages}")
        
        if total_pages > 0:
            print("\n2. 测试获取第一页电影信息（自动登录）...")
            movies = feed_service.get_movies_from_feed_page(1)
            print(f"第一页找到 {len(movies)} 个电影")
            print("\n✅ 向后兼容性测试成功")
            return True
        else:
            print("\n❌ 自动登录测试失败")
            return False
        
    except Exception as e:
        print(f"❌ 向后兼容性测试失败: {e}")
        logger.error(f"向后兼容性测试错误: {e}")
        return False

def test_invalid_manual_cookie():
    """测试传入无效的手动cookie"""
    print("\n=== 测试无效的手动cookie ===")
    
    try:
        # 创建FeedService实例，传入无效的cookie
        invalid_cookie = "invalid_cookie=test; expired_session=123;"
        feed_service = FeedService(manual_cookie=invalid_cookie)
        
        print("\n1. 测试获取feed页面总数（无效cookie）...")
        total_pages = feed_service.get_total_feed_pages()
        print(f"总页数: {total_pages}")
        
        if total_pages == 0:
            print("\n✅ 无效cookie测试成功：正确识别并处理了无效cookie")
            return True
        else:
            print("\n❌ 无效cookie测试异常：应该返回0页")
            return False
        
    except Exception as e:
        print(f"❌ 无效cookie测试失败: {e}")
        logger.error(f"无效cookie测试错误: {e}")
        return False

def main():
    """主测试函数"""
    print("开始测试FeedService的手动cookie功能...\n")
    
    results = []
    
    # 测试1: 手动传入cookie
    results.append(test_manual_cookie())
    
    # 测试2: 向后兼容性
    results.append(test_backward_compatibility())
    
    # 测试3: 无效的手动cookie
    results.append(test_invalid_manual_cookie())
    
    print("\n=== 测试结果汇总 ===")
    test_names = ["手动cookie功能", "向后兼容性", "无效cookie处理"]
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{i+1}. {name}: {status}")
    
    success_count = sum(results)
    print(f"\n总计: {success_count}/{len(results)} 个测试通过")
    
    print("\n=== 使用说明 ===")
    print("1. 要使用手动cookie功能，请按照脚本顶部的说明获取真实cookie")
    print("2. 将获取的cookie字符串替换脚本中的MANUAL_COOKIE变量")
    print("3. 如果不传入manual_cookie参数，系统将自动使用Playwright登录获取cookie")
    print("4. 手动cookie失效时不会自动重新登录，需要手动更新cookie")

if __name__ == "__main__":
    main()