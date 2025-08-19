#!/bin/bash

# VSCode远程开发环境设置脚本

set -e

echo "🚀 设置VSCode远程开发环境..."

PROJECT_DIR="/opt/movie_crawler"
VSCODE_DIR="$PROJECT_DIR/.vscode"

# 创建.vscode目录
mkdir -p "$VSCODE_DIR"

echo "📁 创建VSCode配置文件..."

# 复制配置文件
if [ -f "vscode_settings.json" ]; then
    cp vscode_settings.json "$VSCODE_DIR/settings.json"
    echo "✅ settings.json 已创建"
fi

if [ -f "vscode_launch.json" ]; then
    cp vscode_launch.json "$VSCODE_DIR/launch.json"
    echo "✅ launch.json 已创建"
fi

# 创建tasks.json
cat > "$VSCODE_DIR/tasks.json" << 'EOF'
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "启动爬虫服务",
            "type": "shell",
            "command": "sudo systemctl start movie-crawler",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            }
        },
        {
            "label": "停止爬虫服务",
            "type": "shell",
            "command": "sudo systemctl stop movie-crawler",
            "group": "build"
        },
        {
            "label": "查看服务状态",
            "type": "shell",
            "command": "sudo systemctl status movie-crawler",
            "group": "test"
        },
        {
            "label": "查看服务日志",
            "type": "shell",
            "command": "sudo journalctl -u movie-crawler -f",
            "group": "test",
            "isBackground": true
        },
        {
            "label": "安装Python依赖",
            "type": "shell",
            "command": "./venv/bin/pip install -r linux_requirements.txt",
            "group": "build",
            "options": {
                "cwd": "${workspaceFolder}"
            }
        },
        {
            "label": "启动虚拟显示器",
            "type": "shell",
            "command": "Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &",
            "group": "build",
            "isBackground": true
        }
    ]
}
EOF

echo "✅ tasks.json 已创建"

# 创建扩展推荐文件
cat > "$VSCODE_DIR/extensions.json" << 'EOF'
{
    "recommendations": [
        "ms-python.python",
        "ms-python.debugpy",
        "mtxr.sqltools",
        "mtxr.sqltools-driver-pg",
        "eamodio.gitlens",
        "ms-python.black-formatter",
        "ms-python.pylint",
        "ms-python.isort",
        "redhat.vscode-yaml",
        "ms-vscode.vscode-json"
    ]
}
EOF

echo "✅ extensions.json 已创建"

# 创建开发辅助脚本
cat > "$PROJECT_DIR/dev_helper.py" << 'EOF'
#!/usr/bin/env python3
"""
开发辅助脚本
"""

import os
import sys
from pathlib import Path

def setup_environment():
    """设置开发环境"""
    # 加载环境变量
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    # 添加src到Python路径
    src_path = Path(__file__).parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

def test_imports():
    """测试导入"""
    try:
        from DrissionPage import ChromiumPage
        print("✅ DrissionPage 导入成功")
    except ImportError as e:
        print(f"❌ DrissionPage 导入失败: {e}")
    
    try:
        from sqlalchemy import create_engine
        print("✅ SQLAlchemy 导入成功")
    except ImportError as e:
        print(f"❌ SQLAlchemy 导入失败: {e}")
    
    try:
        from loguru import logger
        print("✅ Loguru 导入成功")
    except ImportError as e:
        print(f"❌ Loguru 导入失败: {e}")

if __name__ == "__main__":
    setup_environment()
    test_imports()
EOF

chmod +x "$PROJECT_DIR/dev_helper.py"
echo "✅ dev_helper.py 已创建"

# 设置权限
chown -R crawler:crawler "$VSCODE_DIR"
chown crawler:crawler "$PROJECT_DIR/dev_helper.py"

echo "🎯 VSCode远程开发环境设置完成！"
echo ""
echo "📋 接下来的步骤："
echo "1. 在本地VSCode中安装 Remote-SSH 扩展"
echo "2. 配置SSH连接到这台服务器"
echo "3. 连接后打开文件夹: $PROJECT_DIR"
echo "4. 安装推荐的扩展"
echo "5. 选择Python解释器: $PROJECT_DIR/venv/bin/python"
echo ""
echo "🔧 可用的调试配置："
echo "- 运行爬虫 (测试模式)"
echo "- 调试单个电影"
echo "- 运行原版爬虫"
echo "- 测试数据库连接"
echo "- 守护进程模式 (调试)"
echo ""
echo "⚡ 可用的任务："
echo "- 启动/停止爬虫服务"
echo "- 查看服务状态和日志"
echo "- 安装Python依赖"
echo "- 启动虚拟显示器"
