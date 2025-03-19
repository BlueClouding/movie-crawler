import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(app_name="crawler", log_level=logging.INFO, log_to_file=True):
    """
    设置详细的日志配置
    
    Args:
        app_name: 应用名称，用于日志文件命名
        log_level: 日志级别
        log_to_file: 是否将日志写入文件
    """
    # 创建日志目录
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 创建格式化器
    formatter = logging.Formatter(
        "%(levelname)-8s - %(asctime)s - %(name)s - %(filename)s:%(lineno)d - %(message)s"
    )
    
    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除任何现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 添加控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # 添加文件处理器（如果启用）
    if log_to_file:
        file_handler = RotatingFileHandler(
            log_dir / f"{app_name}.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)
    
    # 设置第三方库的日志级别
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    
    # 返回根日志记录器
    return root_logger

def get_logger(name):
    """
    获取指定名称的日志记录器
    
    Args:
        name: 日志记录器名称
    
    Returns:
        Logger: 日志记录器实例
    """
    return logging.getLogger(name)
