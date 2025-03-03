import uvicorn
from app import create_app # 从 app 包中导入 create_app 函数
from app.config import settings # 保持相对路径

app = create_app() # 调用工厂函数创建 app 实例

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",  # 格式为 "模块路径:应用实例名"
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG
    )