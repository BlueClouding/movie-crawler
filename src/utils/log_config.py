#!/usr/bin/env python3
"""
日志配置工具
支持按行数轮转的日志配置
"""

import sys
import os
from pathlib import Path
from loguru import logger
from typing import Optional


class LineBasedRotator:
    """基于行数的日志轮转器"""
    
    def __init__(self, max_lines: int = 5000):
        self.max_lines = max_lines
    
    def should_rotate(self, message, file):
        """检查是否需要轮转"""
        if not file.exists():
            return False
        
        try:
            with open(file, 'r', encoding='utf-8') as f:
                line_count = sum(1 for _ in f)
            return line_count >= self.max_lines
        except:
            return False
    
    def __call__(self, message, file):
        """轮转检查函数"""
        return self.should_rotate(message, file)


def setup_crawler_logging(
    log_file: str = "src/logs/crawler.log",
    max_lines: int = 5000,
    level: str = "INFO",
    console_output: bool = True
):
    """
    设置爬虫日志配置
    
    Args:
        log_file: 日志文件路径
        max_lines: 最大保留行数
        level: 日志级别
        console_output: 是否输出到控制台
    """
    
    # 确保日志目录存在
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 移除默认配置
    logger.remove()
    
    # 创建行数轮转器
    rotator = LineBasedRotator(max_lines)
    
    # 添加文件日志处理器
    logger.add(
        log_file,
        rotation=rotator,  # 使用自定义轮转器
        retention="7 days",  # 保留7天的备份文件
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{line} - {message}",
        enqueue=True,  # 异步写入，提高性能
        backtrace=True,  # 显示完整堆栈
        diagnose=True,   # 显示变量值
        encoding="utf-8"
    )
    
    # 添加控制台输出（如果启用）
    if console_output:
        logger.add(
            sys.stderr,
            level=level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
    
    logger.info(f"📝 日志配置完成: {log_file} (最大保留 {max_lines} 行)")
    return logger


def setup_simple_logging(
    log_file: str = "src/logs/crawler.log", 
    max_size: str = "10 MB",
    retention: str = "7 days",
    level: str = "INFO"
):
    """
    设置简单的基于文件大小的日志轮转
    
    Args:
        log_file: 日志文件路径
        max_size: 最大文件大小
        retention: 保留时间
        level: 日志级别
    """
    
    # 确保日志目录存在
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 移除默认配置
    logger.remove()
    
    # 添加文件日志处理器
    logger.add(
        log_file,
        rotation=max_size,
        retention=retention,
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{line} - {message}",
        enqueue=True,
        backtrace=True,
        diagnose=True,
        encoding="utf-8"
    )
    
    # 添加控制台输出
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    logger.info(f"📝 日志配置完成: {log_file} (最大 {max_size}, 保留 {retention})")
    return logger


def trim_log_file(log_file: str, max_lines: int = 5000):
    """
    手动修剪日志文件，保留最后N行
    
    Args:
        log_file: 日志文件路径
        max_lines: 保留的最大行数
    """
    log_path = Path(log_file)
    
    if not log_path.exists():
        return
    
    try:
        # 读取所有行
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 如果行数超过限制，保留最后N行
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
            
            # 写回文件
            with open(log_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            logger.info(f"📝 日志文件已修剪: 保留最后 {len(lines)} 行")
    
    except Exception as e:
        logger.error(f"❌ 修剪日志文件失败: {e}")


if __name__ == "__main__":
    # 测试日志配置
    setup_crawler_logging(max_lines=100)
    
    # 生成一些测试日志
    for i in range(10):
        logger.info(f"测试日志消息 {i+1}")
        logger.debug(f"调试信息 {i+1}")
        logger.warning(f"警告信息 {i+1}")
    
    logger.info("日志配置测试完成")
