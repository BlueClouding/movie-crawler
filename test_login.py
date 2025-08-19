#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：使用无头浏览器进行模拟登录并获取cookie

使用说明：
1. 确保已安装playwright: pip install playwright
2. 安装浏览器: playwright install chromium
3. 运行脚本: python test_login.py

功能：
- 使用Playwright无头浏览器模拟登录123av.com
- 通过API端点(/ja/ajax/user/signin)进行认证
- 获取并缓存登录后的cookies
- 支持cookie缓存机制(1小时有效期)
"""

import sys
import os
import logging
from datetime import datetime

# 添加当前目录到Python路径，以便导入feed_service模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from feed_service import PlaywrightLoginService
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保feed_service.py文件在同一目录下")
    sys.exit(1)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def test_playwright_login():
    """
    测试Playwright登录服务
    """
    print("=" * 60)
    print("开始测试无头浏览器模拟登录")
    print("=" * 60)
    
    try:
        # 创建PlaywrightLoginService实例
        login_service = PlaywrightLoginService()
        
        print(f"登录配置:")
        print(f"  - 网站: {login_service.base_url}")
        print(f"  - 用户名: {login_service.login_username}")
        print(f"  - 密码: {'*' * len(login_service.login_password)}")
        print(f"  - 缓存时长: {login_service.cookie_cache_duration_seconds}秒")
        print()
        
        # 第一次获取cookies（会执行实际登录）
        print("第一次获取cookies（执行登录）...")
        start_time = datetime.now()
        
        cookies = login_service.get_auth_cookies()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if cookies:
            print(f"✅ 登录成功！耗时: {duration:.2f}秒")
            print(f"获取的cookies: {cookies[:100]}..." if len(cookies) > 100 else f"获取的cookies: {cookies}")
            print(f"cookies长度: {len(cookies)}字符")
            
            # 检查缓存状态
            if login_service.cached_cookies:
                expiry_time = datetime.fromtimestamp(login_service.cookie_expiry_time)
                print(f"cookies已缓存，过期时间: {expiry_time}")
            
            print()
            
            # 第二次获取cookies（应该使用缓存）
            print("第二次获取cookies（应该使用缓存）...")
            start_time = datetime.now()
            
            cached_cookies = login_service.get_auth_cookies()
            
            end_time = datetime.now()
            cache_duration = (end_time - start_time).total_seconds()
            
            if cached_cookies == cookies:
                print(f"✅ 缓存工作正常！耗时: {cache_duration:.2f}秒")
                print("cookies内容一致，确认使用了缓存")
            else:
                print(f"⚠️  缓存可能有问题，cookies内容不一致")
            
            print()
            
            # 测试强制刷新
            print("测试强制刷新cookies...")
            start_time = datetime.now()
            
            fresh_cookies = login_service.get_auth_cookies(force_refresh=True)
            
            end_time = datetime.now()
            refresh_duration = (end_time - start_time).total_seconds()
            
            if fresh_cookies:
                print(f"✅ 强制刷新成功！耗时: {refresh_duration:.2f}秒")
                print(f"新cookies长度: {len(fresh_cookies)}字符")
            else:
                print(f"❌ 强制刷新失败")
                
        else:
            print(f"❌ 登录失败！耗时: {duration:.2f}秒")
            print("可能的原因:")
            print("  - 网络连接问题")
            print("  - 登录凭据错误")
            print("  - 网站登录接口变更")
            print("  - Playwright浏览器未正确安装")
            
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        print(f"❌ 测试失败: {e}")
        print("\n可能的解决方案:")
        print("1. 检查网络连接")
        print("2. 确保已安装playwright: pip install playwright")
        print("3. 安装浏览器: playwright install chromium")
        print("4. 检查登录凭据是否正确")
        return False
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)
    return True

def test_cookie_invalidation():
    """
    测试cookie缓存失效功能
    """
    print("\n测试cookie缓存失效功能...")
    
    try:
        login_service = PlaywrightLoginService()
        
        # 先获取cookies
        cookies = login_service.get_auth_cookies()
        if not cookies:
            print("❌ 无法获取cookies，跳过缓存失效测试")
            return False
            
        print(f"✅ 获取cookies成功，长度: {len(cookies)}")
        
        # 检查缓存状态
        if login_service.cached_cookies:
            print("✅ cookies已缓存")
        
        # 使缓存失效
        login_service.invalidate_cookie_cache()
        print("✅ 缓存已失效")
        
        # 检查缓存是否真的失效了
        if not login_service.cached_cookies and not login_service.cookie_expiry_time:
            print("✅ 缓存失效验证成功")
            return True
        else:
            print("❌ 缓存失效验证失败")
            return False
            
    except Exception as e:
        print(f"❌ 缓存失效测试失败: {e}")
        return False

if __name__ == "__main__":
    print("Playwright无头浏览器登录测试")
    print(f"测试时间: {datetime.now()}")
    print()
    
    # 检查依赖
    try:
        import playwright
        print("✅ Playwright已安装")
    except ImportError:
        print("❌ Playwright未安装，请运行: pip install playwright")
        sys.exit(1)
    
    try:
        import requests
        print("✅ Requests已安装")
    except ImportError:
        print("❌ Requests未安装，请运行: pip install requests")
        sys.exit(1)
        
    try:
        from bs4 import BeautifulSoup
        print("✅ BeautifulSoup已安装")
    except ImportError:
        print("❌ BeautifulSoup未安装，请运行: pip install beautifulsoup4")
        sys.exit(1)
    
    print()
    
    # 执行主要测试
    success = test_playwright_login()
    
    # 执行缓存失效测试
    if success:
        test_cookie_invalidation()
    
    print("\n测试说明:")
    print("- 第一次获取cookies会执行实际的浏览器登录过程")
    print("- 第二次获取cookies会使用缓存，速度更快")
    print("- 强制刷新会重新执行登录过程")
    print("- cookies缓存有效期为1小时")
    print("- 如果登录失败，请检查网络连接和登录凭据")