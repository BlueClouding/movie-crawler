import os
import sys
import uvicorn
import logging
from crawler.config.settings import settings
from crawler import create_app # 从 app 包中导入 create_app 函数
from common.utils.logging_config import setup_logging

# Add src directory to Python path
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
    sys.path.append(src_dir)

# 设置详细的日志配置
logger = setup_logging(app_name="crawler", log_level=logging.DEBUG)
logger.info("正在启动爬虫服务...")

# 调用工厂函数创建 app 实例
app = create_app()

if __name__ == "__main__":
    logger.info(f"启动服务器: {settings.SERVER_HOST}:{settings.SERVER_PORT}")
    uvicorn.run(
        "crawler.main:app",  # 格式为 "模块路径:应用实例名"
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=True,
        log_level="info"
    )