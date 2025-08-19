#!/bin/bash

# AlmaLinux 8.10 快速安装脚本
# 一键安装所有必要组件

set -e

echo "🚀 AlmaLinux 8.10 电影爬虫快速安装"
echo "=================================="

# 检查系统版本
if [ -f /etc/redhat-release ]; then
    echo "✅ 检测到系统: $(cat /etc/redhat-release)"
else
    echo "❌ 不支持的系统，此脚本仅适用于AlmaLinux/CentOS/RHEL"
    exit 1
fi

# 检查root权限
if [[ $EUID -ne 0 ]]; then
   echo "❌ 请使用root权限运行此脚本"
   echo "使用方法: sudo $0"
   exit 1
fi

echo ""
echo "📋 安装步骤："
echo "1. 更新系统包"
echo "2. 安装Python 3.9+"
echo "3. 安装PostgreSQL"
echo "4. 安装Google Chrome"
echo "5. 安装X11依赖"
echo "6. 创建项目环境"
echo "7. 配置服务"
echo ""

read -p "是否继续安装？(y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "安装已取消"
    exit 1
fi

echo ""
echo "🔄 开始安装..."

# 1. 更新系统
echo "📦 更新系统包..."
dnf update -y
dnf install -y epel-release

# 2. 安装Python和开发工具
echo "🐍 安装Python和开发工具..."
dnf groupinstall -y "Development Tools"
dnf install -y python3 python3-pip python3-devel \
    git curl wget vim unzip \
    gcc gcc-c++ make openssl-devel \
    libffi-devel bzip2-devel

# 升级pip
python3 -m pip install --upgrade pip

# 3. 安装PostgreSQL
echo "🗄️ 安装PostgreSQL..."
dnf install -y postgresql postgresql-server postgresql-contrib postgresql-devel

# 初始化PostgreSQL（如果还没有初始化）
if [ ! -f /var/lib/pgsql/data/postgresql.conf ]; then
    echo "🔧 初始化PostgreSQL数据库..."
    postgresql-setup --initdb
fi

# 启动PostgreSQL
systemctl start postgresql
systemctl enable postgresql

# 4. 安装Google Chrome
echo "🌐 安装Google Chrome..."
cat > /etc/yum.repos.d/google-chrome.repo << 'EOF'
[google-chrome]
name=google-chrome
baseurl=http://dl.google.com/linux/chrome/rpm/stable/x86_64
enabled=1
gpgcheck=1
gpgkey=https://dl.google.com/linux/linux_signing_key.pub
EOF

dnf install -y google-chrome-stable

# 5. 安装X11和Chrome依赖
echo "🖥️ 安装X11和Chrome依赖..."
dnf install -y xorg-x11-server-Xvfb \
    gtk3 libXScrnSaver alsa-lib \
    nss atk at-spi2-atk cups-libs \
    drm libxkbcommon libXcomposite \
    libXdamage libXrandr mesa-libgbm \
    libXss libgconf dbus-glib \
    xorg-x11-fonts-Type1 xorg-x11-fonts-75dpi \
    xorg-x11-fonts-100dpi liberation-fonts

# 6. 创建项目环境
echo "📁 创建项目环境..."
PROJECT_DIR="/opt/movie_crawler"
SERVICE_USER="crawler"

# 创建用户
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -s /bin/bash -d $PROJECT_DIR $SERVICE_USER
    echo "✅ 创建用户: $SERVICE_USER"
fi

# 创建目录
mkdir -p $PROJECT_DIR/{src/{test,utils,logs},data}
chown -R $SERVICE_USER:$SERVICE_USER $PROJECT_DIR

# 创建虚拟环境
echo "🐍 创建Python虚拟环境..."
cd $PROJECT_DIR
sudo -u $SERVICE_USER python3 -m venv venv
sudo -u $SERVICE_USER ./venv/bin/pip install --upgrade pip

# 7. 安装Python依赖
echo "📦 安装Python依赖..."
sudo -u $SERVICE_USER ./venv/bin/pip install \
    DrissionPage==4.1.0.18 \
    loguru \
    sqlalchemy \
    psycopg2-binary \
    beautifulsoup4 \
    requests \
    lxml \
    python-dotenv

# 8. 配置数据库
echo "🗄️ 配置数据库..."
DB_NAME="movie_crawler"
DB_USER="crawler_user"
DB_PASSWORD="crawler_$(openssl rand -hex 8)"

# 创建数据库和用户
sudo -u postgres psql << EOF
DROP DATABASE IF EXISTS $DB_NAME;
DROP USER IF EXISTS $DB_USER;
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER USER $DB_USER CREATEDB;
\q
EOF

# 9. 创建配置文件
echo "⚙️ 创建配置文件..."
cat > $PROJECT_DIR/.env << EOF
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD

# 爬虫配置
HEADLESS=true
MAX_WORKERS=3
BATCH_SIZE=10
RETRY_TIMES=3

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=$PROJECT_DIR/src/logs/crawler.log
EOF

chown $SERVICE_USER:$SERVICE_USER $PROJECT_DIR/.env
chmod 600 $PROJECT_DIR/.env

# 10. 创建测试脚本
echo "🧪 创建测试脚本..."
cat > $PROJECT_DIR/test_installation.py << 'EOF'
#!/usr/bin/env python3
"""
安装测试脚本
"""

import sys
import os

def test_imports():
    """测试Python包导入"""
    print("🧪 测试Python包导入...")
    
    try:
        import DrissionPage
        print("✅ DrissionPage 导入成功")
    except ImportError as e:
        print(f"❌ DrissionPage 导入失败: {e}")
        return False
    
    try:
        import sqlalchemy
        print("✅ SQLAlchemy 导入成功")
    except ImportError as e:
        print(f"❌ SQLAlchemy 导入失败: {e}")
        return False
    
    try:
        import psycopg2
        print("✅ psycopg2 导入成功")
    except ImportError as e:
        print(f"❌ psycopg2 导入失败: {e}")
        return False
    
    try:
        from loguru import logger
        print("✅ loguru 导入成功")
    except ImportError as e:
        print(f"❌ loguru 导入失败: {e}")
        return False
    
    return True

def test_chrome():
    """测试Chrome"""
    print("🌐 测试Chrome...")
    
    import subprocess
    try:
        result = subprocess.run(['google-chrome', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Chrome版本: {result.stdout.strip()}")
            return True
        else:
            print("❌ Chrome测试失败")
            return False
    except Exception as e:
        print(f"❌ Chrome测试异常: {e}")
        return False

def test_database():
    """测试数据库连接"""
    print("🗄️ 测试数据库连接...")
    
    # 加载环境变量
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        from sqlalchemy import create_engine, text
        
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'movie_crawler')
        db_user = os.getenv('DB_USER', 'crawler_user')
        db_password = os.getenv('DB_PASSWORD')
        
        db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            if result.scalar() == 1:
                print("✅ 数据库连接成功")
                return True
            else:
                print("❌ 数据库连接失败")
                return False
                
    except Exception as e:
        print(f"❌ 数据库连接异常: {e}")
        return False

def main():
    print("🚀 开始安装测试...")
    print("=" * 40)
    
    success = True
    
    success &= test_imports()
    print()
    
    success &= test_chrome()
    print()
    
    success &= test_database()
    print()
    
    if success:
        print("🎉 所有测试通过！安装成功！")
        return 0
    else:
        print("💥 部分测试失败，请检查安装")
        return 1

if __name__ == "__main__":
    sys.exit(main())
EOF

chmod +x $PROJECT_DIR/test_installation.py
chown $SERVICE_USER:$SERVICE_USER $PROJECT_DIR/test_installation.py

# 11. 配置防火墙和SELinux
echo "🔒 配置安全设置..."

# 配置防火墙
if systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --add-service=ssh
    firewall-cmd --reload
    echo "✅ 防火墙已配置"
fi

# 配置SELinux
if command -v getenforce &> /dev/null && [ "$(getenforce)" != "Disabled" ]; then
    setsebool -P httpd_can_network_connect 1 2>/dev/null || true
    echo "✅ SELinux已配置"
fi

# 12. 运行测试
echo ""
echo "🧪 运行安装测试..."
cd $PROJECT_DIR
sudo -u $SERVICE_USER ./venv/bin/python test_installation.py

echo ""
echo "🎉 AlmaLinux 8.10 安装完成！"
echo "================================"
echo ""
echo "📋 安装信息："
echo "项目目录: $PROJECT_DIR"
echo "服务用户: $SERVICE_USER"
echo "数据库名: $DB_NAME"
echo "数据库用户: $DB_USER"
echo "数据库密码: $DB_PASSWORD"
echo ""
echo "📁 配置文件位置："
echo "环境变量: $PROJECT_DIR/.env"
echo "虚拟环境: $PROJECT_DIR/venv"
echo ""
echo "🔧 下一步操作："
echo "1. 上传爬虫代码到 $PROJECT_DIR"
echo "2. 运行测试: sudo -u $SERVICE_USER $PROJECT_DIR/venv/bin/python test_installation.py"
echo "3. 启动爬虫: sudo -u $SERVICE_USER $PROJECT_DIR/venv/bin/python linux_crawler.py"
echo ""
echo "💡 有用的命令："
echo "查看日志: tail -f $PROJECT_DIR/src/logs/crawler.log"
echo "连接数据库: sudo -u postgres psql $DB_NAME"
echo "切换用户: sudo -u $SERVICE_USER -i"
