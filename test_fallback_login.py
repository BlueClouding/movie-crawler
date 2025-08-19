#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试FeedService的备选登录方案
验证当Playwright登录失败时，是否能自动切换到CloudflareLoginService
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from feed_service import FeedService
from src.common.utils.logging_config import setup_logging
import logging

# 设置日志
logger = setup_logging(app_name="test_fallback", log_level=logging.INFO)

def test_fallback_login():
    """测试备选登录方案"""
    logger.info("开始测试FeedService的备选登录方案")
    
    # 创建FeedService实例（不使用手动cookie）
    service = FeedService()
    
    # 测试获取认证cookies的备选方案
    logger.info("测试get_auth_cookies_with_fallback方法")
    cookies = service.get_auth_cookies_with_fallback(force_refresh=True)
    
    if cookies:
        logger.info(f"成功获取cookies: {cookies[:100]}...")
        
        # 测试使用获取的cookies访问feed页面
        logger.info("测试使用获取的cookies访问feed页面")
        total_pages = service.get_total_feed_pages()
        logger.info(f"获取到的总页数: {total_pages}")
        
        if total_pages > 0:
            logger.info("备选登录方案测试成功！")
            return True
        else:
            logger.warning("获取到cookies但无法访问feed页面")
            return False
    else:
        logger.error("所有登录方案都失败")
        return False

def test_cloudflare_service_directly():
    """直接测试CloudflareLoginService"""
    logger.info("直接测试CloudflareLoginService")
    
    try:
        from cloudflare_login_service import CloudflareLoginService
        
        cloudflare_service = CloudflareLoginService()
        cookies = cloudflare_service.get_cookies(force_refresh=True)
        
        if cookies:
            logger.info(f"CloudflareLoginService直接测试成功: {cookies[:100]}...")
            return True
        else:
            logger.error("CloudflareLoginService直接测试失败")
            return False
            
    except Exception as e:
        logger.error(f"CloudflareLoginService直接测试出错: {e}")
        return False

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("开始测试备选登录方案")
    logger.info("=" * 60)
    
    # 首先直接测试CloudflareLoginService
    logger.info("\n1. 直接测试CloudflareLoginService")
    cloudflare_success = test_cloudflare_service_directly()
    
    # 然后测试FeedService的备选登录方案
    logger.info("\n2. 测试FeedService的备选登录方案")
    fallback_success = test_fallback_login()
    
    # 总结测试结果
    logger.info("\n=" * 60)
    logger.info("测试结果总结:")
    logger.info(f"CloudflareLoginService直接测试: {'成功' if cloudflare_success else '失败'}")
    logger.info(f"FeedService备选登录方案测试: {'成功' if fallback_success else '失败'}")
    
    if cloudflare_success and fallback_success:
        logger.info("✅ 所有测试通过！备选登录方案集成成功")
    elif cloudflare_success:
        logger.info("⚠️  CloudflareLoginService可用，但FeedService集成可能有问题")
    else:
        logger.info("❌ 测试失败，需要检查CloudflareLoginService配置")
    
    logger.info("=" * 60)