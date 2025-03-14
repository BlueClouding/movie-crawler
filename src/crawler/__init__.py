import logging
from fastapi import FastAPI
from crawler.api.router import api_router  # 保持相对路径
from crawler.config.settings import settings  # 保持相对路径
from common.utils.logging_config import setup_logging
from common.utils.exception_handlers import register_exception_handlers
from common.utils.middlewares import setup_middlewares

# 设置全局日志配置
logger = setup_logging(app_name="crawler", log_level=logging.DEBUG)

def create_app(): # 定义一个工厂函数来创建 app 实例
    app = FastAPI(
        title="Movie Database API",
        description="API for admin movie database",
        version="1.0.0",
    )

    # 注册异常处理器
    register_exception_handlers(app)
    
    # 设置全局中间件
    setup_middlewares(app)

    # 注册路由
    app.include_router(api_router, prefix='/api')

    @app.get("/")
    def root():
        return {"message": "Welcome to Movie Database API. Go to /docs for documentation."}

    # 记录应用启动日志
    logger.info("Movie Database API 已启动")

    return app