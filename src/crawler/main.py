import os
import sys
import uvicorn
from crawler.config.settings import settings
from crawler import create_app # 从 app 包中导入 create_app 函数

# Add src directory to Python path
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
    sys.path.append(src_dir)

app = create_app() # 调用工厂函数创建 app 实例

if __name__ == "__main__":
    uvicorn.run(
        "crawler.main:app",  # 格式为 "模块路径:应用实例名"
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=True
    )