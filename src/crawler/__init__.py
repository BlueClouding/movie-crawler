from fastapi import FastAPI
from crawler.api.router import api_router  # 保持相对路径
from crawler.config.settings import settings  # 保持相对路径

def create_app(): # 定义一个工厂函数来创建 app 实例
    app = FastAPI(
        title="Movie Database API",
        description="API for admin movie database",
        version="1.0.0",
    )

    app.include_router(api_router, prefix='/api')

    @app.get("/")
    def root():
        return {"message": "Welcome to Movie Database API. Go to /docs for documentation."}

    return app