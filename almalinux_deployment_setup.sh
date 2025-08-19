#!/bin/bash

# AlmaLinux 8.10 部署脚本
# 适用于 AlmaLinux/CentOS/RHEL 系统

set -e

echo "🚀 开始在 AlmaLinux 8.10 上部署电影爬虫服务..."

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目配置
PROJECT_DIR="/opt/movie_crawler"
SERVICE_USER="crawler"
DB_NAME="movie_crawler"
DB_USER="crawler_user"
DB_PASSWORD="your_secure_password_here"

# 检查是否为root用户
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}此脚本需要root权限运行${NC}"
   exit 1
fi

echo -e "${GREEN}1. 更新系统和安装基础软件...${NC}"
dnf update -y
dnf install -y wget curl git vim unzip epel-release

echo -e "${GREEN}2. 安装Python 3.9+...${NC}"
dnf install -y python3 python3-pip python3-devel gcc gcc-c++ make

# 安装虚拟环境工具
python3 -m pip install --upgrade pip
python3 -m pip install virtualenv

echo -e "${GREEN}3. 安装PostgreSQL...${NC}"
dnf install -y postgresql postgresql-server postgresql-contrib postgresql-devel

# 初始化PostgreSQL
if [ ! -f /var/lib/pgsql/data/postgresql.conf ]; then
    postgresql-setup --initdb
fi

echo -e "${GREEN}4. 安装Chrome浏览器...${NC}"
# 添加Google Chrome仓库
cat > /etc/yum.repos.d/google-chrome.repo << 'EOF'
[google-chrome]
name=google-chrome
baseurl=http://dl.google.com/linux/chrome/rpm/stable/x86_64
enabled=1
gpgcheck=1
gpgkey=https://dl.google.com/linux/linux_signing_key.pub
EOF

dnf install -y google-chrome-stable

echo -e "${GREEN}5. 安装Chrome依赖和X11...${NC}"
dnf install -y xorg-x11-server-Xvfb gtk3 libXScrnSaver alsa-lib \
    nss atk at-spi2-atk cups-libs drm libxkbcommon \
    libXcomposite libXdamage libXrandr mesa-libgbm \
    libXss libgconf

echo -e "${GREEN}6. 创建服务用户...${NC}"
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -s /bin/bash -d $PROJECT_DIR $SERVICE_USER
fi

echo -e "${GREEN}7. 创建项目目录...${NC}"
mkdir -p $PROJECT_DIR
mkdir -p $PROJECT_DIR/src/{test,utils,logs}
mkdir -p $PROJECT_DIR/data
chown -R $SERVICE_USER:$SERVICE_USER $PROJECT_DIR

echo -e "${GREEN}8. 配置PostgreSQL...${NC}"
systemctl start postgresql
systemctl enable postgresql

# 配置数据库
sudo -u postgres psql << EOF
DROP DATABASE IF EXISTS $DB_NAME;
DROP USER IF EXISTS $DB_USER;
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
ALTER USER $DB_USER CREATEDB;
\q
EOF

echo -e "${GREEN}9. 创建Python虚拟环境...${NC}"
cd $PROJECT_DIR
sudo -u $SERVICE_USER python3 -m venv venv
sudo -u $SERVICE_USER ./venv/bin/pip install --upgrade pip

echo -e "${GREEN}10. 安装Python依赖...${NC}"
sudo -u $SERVICE_USER ./venv/bin/pip install \
    DrissionPage==4.1.0.18 \
    loguru \
    sqlalchemy \
    psycopg2-binary \
    beautifulsoup4 \
    requests \
    lxml

echo -e "${GREEN}11. 创建配置文件...${NC}"
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

echo -e "${GREEN}12. 创建systemd服务文件...${NC}"
cat > /etc/systemd/system/movie-crawler.service << EOF
[Unit]
Description=Movie Crawler Service
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
Environment=DISPLAY=:99
ExecStartPre=/usr/bin/Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
ExecStart=$PROJECT_DIR/venv/bin/python linux_crawler.py --daemon
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}13. 创建启动脚本...${NC}"
cat > $PROJECT_DIR/start_crawler.sh << 'EOF'
#!/bin/bash

# 启动虚拟显示器（无头模式）
export DISPLAY=:99
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!

# 等待Xvfb启动
sleep 2

# 启动爬虫
cd /opt/movie_crawler
source venv/bin/activate
python linux_crawler.py

# 清理
kill $XVFB_PID 2>/dev/null || true
EOF

chmod +x $PROJECT_DIR/start_crawler.sh
chown $SERVICE_USER:$SERVICE_USER $PROJECT_DIR/start_crawler.sh

echo -e "${GREEN}14. 配置防火墙...${NC}"
# 检查firewalld是否运行
if systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --add-service=ssh
    firewall-cmd --reload
    echo "防火墙已配置"
else
    echo "防火墙未运行，跳过配置"
fi

echo -e "${GREEN}15. 配置SELinux...${NC}"
# 如果SELinux启用，设置适当的上下文
if command -v getenforce &> /dev/null && [ "$(getenforce)" != "Disabled" ]; then
    setsebool -P httpd_can_network_connect 1
    semanage fcontext -a -t bin_t "$PROJECT_DIR/venv/bin/python" 2>/dev/null || true
    restorecon -R $PROJECT_DIR 2>/dev/null || true
    echo "SELinux上下文已配置"
fi

echo -e "${GREEN}✅ AlmaLinux 部署完成！${NC}"
echo -e "${YELLOW}接下来的步骤：${NC}"
echo "1. 上传你的爬虫代码到 $PROJECT_DIR"
echo "2. 修改 $PROJECT_DIR/.env 中的数据库密码"
echo "3. 启动服务: systemctl start movie-crawler"
echo "4. 查看状态: systemctl status movie-crawler"
echo "5. 查看日志: journalctl -u movie-crawler -f"
echo ""
echo -e "${YELLOW}手动运行测试：${NC}"
echo "sudo -u $SERVICE_USER $PROJECT_DIR/start_crawler.sh"
echo ""
echo -e "${YELLOW}系统信息：${NC}"
echo "操作系统: $(cat /etc/redhat-release)"
echo "Python版本: $(python3 --version)"
echo "PostgreSQL版本: $(sudo -u postgres psql -c 'SELECT version();' | head -3 | tail -1)"
