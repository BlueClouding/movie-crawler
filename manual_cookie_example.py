#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动Cookie使用示例

本文件展示如何正确使用FeedService的手动cookie功能，
包括如何获取有效的cookie、处理cookie失效等常见问题。
"""

import logging
from feed_service import FeedService

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_cookie_from_browser_guide():
    """
    如何从浏览器获取Cookie的详细指南
    """
    guide = """
    ==================== 如何获取Cookie ====================
    
    1. 打开浏览器（推荐Chrome或Firefox）
    2. 访问 https://123av.com 并完成登录
    3. 登录成功后，按F12打开开发者工具
    4. 切换到 "Network" (网络) 标签页
    5. 刷新页面或访问任意页面
    6. 在网络请求列表中找到任意一个请求
    7. 点击该请求，在右侧详情中找到 "Request Headers"
    8. 复制 "Cookie:" 后面的完整内容
    
    Cookie格式示例：
    session_id=abc123; user_token=xyz789; remember_me=true; _ga=GA1.2.123456789
    
    注意事项：
    - Cookie包含多个键值对，用分号分隔
    - 不要包含 "Cookie:" 这个前缀
    - 确保复制完整，不要遗漏任何部分
    - Cookie有时效性，过期后需要重新获取
    
    ========================================================
    """
    print(guide)

def example_with_manual_cookie():
    """
    使用手动Cookie的示例
    """
    print("\n=== 手动Cookie使用示例 ===")
    
    # 这里需要替换为你从浏览器获取的真实cookie
    # 格式："key1=value1; key2=value2; key3=value3"
    manual_cookie = "请替换为你的真实cookie"
    
    if manual_cookie == "请替换为你的真实cookie":
        print("❌ 请先替换为真实的cookie值")
        print("请参考上面的指南获取cookie")
        return
    
    try:
        # 创建FeedService实例，传入手动cookie
        feed_service = FeedService(manual_cookie=manual_cookie)
        
        print("✅ FeedService已创建，使用手动cookie")
        
        # 测试获取总页数
        total_pages = feed_service.get_total_feed_pages()
        print(f"📄 总页数: {total_pages}")
        
        if total_pages > 0:
            print("✅ 手动cookie有效，可以正常访问")
            
            # 测试获取第一页电影
            movies = feed_service.get_movies_from_feed_page(1)
            print(f"🎬 第一页找到 {len(movies)} 部电影")
            
        else:
            print("❌ 无法获取页面内容，cookie可能已失效")
            print("请检查cookie是否正确或重新获取")
            
    except Exception as e:
        logger.error(f"使用手动cookie时出错: {e}")
        print(f"❌ 错误: {e}")

def example_with_auto_login():
    """
    使用自动登录的示例（对比）
    """
    print("\n=== 自动登录使用示例（对比） ===")
    
    try:
        # 创建FeedService实例，不传入manual_cookie
        feed_service = FeedService()
        
        print("✅ FeedService已创建，使用自动登录")
        
        # 测试获取总页数
        total_pages = feed_service.get_total_feed_pages()
        print(f"📄 总页数: {total_pages}")
        
        if total_pages > 0:
            print("✅ 自动登录成功，可以正常访问")
        else:
            print("❌ 自动登录失败")
            
    except Exception as e:
        logger.error(f"使用自动登录时出错: {e}")
        print(f"❌ 错误: {e}")

def troubleshooting_guide():
    """
    常见问题和解决方案
    """
    guide = """
    ==================== 常见问题解决方案 ====================
    
    问题1: 持续收到401错误
    原因: Cookie已过期或无效
    解决: 重新从浏览器获取最新的cookie
    
    问题2: Cookie格式错误
    原因: 复制时包含了多余的内容或格式不正确
    解决: 确保只复制Cookie值，不包含"Cookie:"前缀
    
    问题3: 页面跳转到登录页面
    原因: Cookie失效或网站检测到异常访问
    解决: 重新登录并获取新的cookie
    
    问题4: 网络请求失败
    原因: 网络连接问题或网站暂时不可用
    解决: 检查网络连接，稍后重试
    
    问题5: 手动cookie vs 自动登录的选择
    - 手动cookie: 适合批量处理，避免频繁登录
    - 自动登录: 适合交互式使用，自动处理登录状态
    
    最佳实践:
    1. 定期更新cookie（建议每天更新）
    2. 监控日志输出，及时发现问题
    3. 在生产环境中使用异常处理
    4. 考虑实现cookie自动刷新机制
    
    ========================================================
    """
    print(guide)

def validate_cookie_format(cookie_string):
    """
    验证Cookie格式是否正确
    """
    if not cookie_string or cookie_string.strip() == "":
        return False, "Cookie不能为空"
    
    if cookie_string.startswith("Cookie:"):
        return False, "Cookie不应包含'Cookie:'前缀"
    
    if "=" not in cookie_string:
        return False, "Cookie格式不正确，应包含键值对"
    
    # 基本格式检查
    parts = cookie_string.split(";")
    for part in parts:
        part = part.strip()
        if part and "=" not in part:
            return False, f"Cookie部分格式错误: {part}"
    
    return True, "Cookie格式看起来正确"

def main():
    """
    主函数 - 运行所有示例
    """
    print("🚀 FeedService手动Cookie使用指南")
    print("=" * 50)
    
    # 显示获取cookie的指南
    get_cookie_from_browser_guide()
    
    # 手动cookie示例
    example_with_manual_cookie()
    
    # 自动登录示例（对比）
    example_with_auto_login()
    
    # 故障排除指南
    troubleshooting_guide()
    
    print("\n✨ 使用完成！")
    print("如果遇到问题，请检查日志输出或参考故障排除指南")

if __name__ == "__main__":
    main()