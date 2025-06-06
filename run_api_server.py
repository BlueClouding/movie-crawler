#!/usr/bin/env python
"""
电影爬虫API服务启动脚本

运行此脚本启动FastAPI服务，提供电影爬虫的REST API接口。
"""
import os
import sys
from pathlib import Path
import uvicorn
from loguru import logger

# 设置项目根目录
ROOT_DIR = Path(__file__).parent
sys.path.append(str(ROOT_DIR))

# 确保必要的目录存在
os.makedirs("data", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# 设置日志
logger.add("logs/api_server.log", rotation="10 MB", level="INFO")

if __name__ == "__main__":
    logger.info("启动电影爬虫API服务...")
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式下启用热重载
        log_level="info"
    )
