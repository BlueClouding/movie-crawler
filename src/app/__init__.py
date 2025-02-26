from fastapi import FastAPI
from app.api.router import api_router  # 保持相对路径
from app.config import settings  # 保持相对路径

def create_app(): # 定义一个工厂函数来创建 app 实例
    app = FastAPI(
        title="Movie Database API",
        description="API for managing movie database",
        version="1.0.0",
    )

    app.include_router(api_router, prefix='/api_v1')

    @app.get("/")
    def root():
        return {"message": "Welcome to Movie Database API. Go to /docs for documentation."}

    return app

# 不再在 __init__.py 中直接创建 app 实例，而是在 main.py 中调用 create_app()