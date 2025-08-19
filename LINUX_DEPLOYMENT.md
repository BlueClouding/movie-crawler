# Linux VPS 部署指南

## 🚀 快速部署

### 1. 运行自动部署脚本

```bash
# 下载并运行部署脚本
wget https://your-server.com/linux_deployment_setup.sh
chmod +x linux_deployment_setup.sh
sudo ./linux_deployment_setup.sh
```

### 2. 上传项目文件

```bash
# 方法1: 使用scp上传
scp linux_crawler.py root@your-server:/opt/movie_crawler/
scp linux_requirements.txt root@your-server:/opt/movie_crawler/
scp -r src/ root@your-server:/opt/movie_crawler/

# 方法2: 使用git克隆
cd /opt/movie_crawler
git clone your-repository-url .
```

### 3. 安装Python依赖

```bash
cd /opt/movie_crawler
sudo -u crawler ./venv/bin/pip install -r linux_requirements.txt
```

### 4. 配置数据库

```bash
# 修改数据库密码
sudo nano /opt/movie_crawler/.env

# 导入数据库结构（如果有SQL文件）
sudo -u postgres psql movie_crawler < database_schema.sql
```

### 5. 启动服务

```bash
# 启动服务
sudo systemctl start movie-crawler

# 设置开机自启
sudo systemctl enable movie-crawler

# 查看状态
sudo systemctl status movie-crawler

# 查看日志
sudo journalctl -u movie-crawler -f
```

## 🔧 手动部署步骤

### 1. 系统准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础软件
sudo apt install -y python3 python3-pip python3-venv git curl wget
```

### 2. 安装Chrome

```bash
# 添加Google Chrome仓库
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list

# 安装Chrome
sudo apt update
sudo apt install -y google-chrome-stable

# 安装依赖
sudo apt install -y libnss3 libgconf-2-4 libxss1 libappindicator1 libindicator7 xvfb libgbm1 libasound2
```

### 3. 安装PostgreSQL

```bash
# 安装PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# 启动服务
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库
sudo -u postgres createdb movie_crawler
sudo -u postgres createuser -P crawler_user
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE movie_crawler TO crawler_user;"
```

### 4. 创建项目环境

```bash
# 创建项目目录
sudo mkdir -p /opt/movie_crawler
cd /opt/movie_crawler

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r linux_requirements.txt
```

### 5. 配置环境变量

```bash
# 创建.env文件
cat > .env << EOF
DB_HOST=localhost
DB_PORT=5432
DB_NAME=movie_crawler
DB_USER=crawler_user
DB_PASSWORD=your_secure_password
HEADLESS=true
MAX_WORKERS=3
BATCH_SIZE=10
EOF
```

## 🎯 运行方式

### 1. 手动运行

```bash
cd /opt/movie_crawler
source venv/bin/activate

# 单次运行
python linux_crawler.py --batch-size 20 --max-movies 100

# 无头模式运行
python linux_crawler.py --headless --workers 5

# 守护进程模式
python linux_crawler.py --daemon
```

### 2. 系统服务运行

```bash
# 启动服务
sudo systemctl start movie-crawler

# 停止服务
sudo systemctl stop movie-crawler

# 重启服务
sudo systemctl restart movie-crawler

# 查看状态
sudo systemctl status movie-crawler
```

### 3. 使用screen后台运行

```bash
# 安装screen
sudo apt install -y screen

# 创建screen会话
screen -S crawler

# 在screen中运行
cd /opt/movie_crawler
source venv/bin/activate
python linux_crawler.py --daemon

# 分离screen (Ctrl+A, D)
# 重新连接: screen -r crawler
```

## 📊 监控和维护

### 1. 查看日志

```bash
# 系统服务日志
sudo journalctl -u movie-crawler -f

# 应用日志
tail -f /opt/movie_crawler/src/logs/crawler.log

# 查看结果文件
tail -f /opt/movie_crawler/crawl_results.jsonl
```

### 2. 性能监控

```bash
# 查看进程
ps aux | grep python

# 查看资源使用
htop

# 查看磁盘使用
df -h
du -sh /opt/movie_crawler/
```

### 3. 数据库维护

```bash
# 连接数据库
sudo -u postgres psql movie_crawler

# 查看表大小
\dt+

# 查看记录数
SELECT COUNT(*) FROM movies;
```

## 🔒 安全配置

### 1. 防火墙设置

```bash
# 安装ufw
sudo apt install -y ufw

# 允许SSH
sudo ufw allow 22/tcp

# 启用防火墙
sudo ufw enable
```

### 2. 用户权限

```bash
# 创建专用用户
sudo useradd -r -s /bin/bash -d /opt/movie_crawler crawler

# 设置目录权限
sudo chown -R crawler:crawler /opt/movie_crawler
sudo chmod 755 /opt/movie_crawler
```

## 🚨 故障排除

### 1. Chrome问题

```bash
# 检查Chrome版本
google-chrome --version

# 测试Chrome
google-chrome --headless --no-sandbox --dump-dom https://www.google.com
```

### 2. 数据库连接问题

```bash
# 测试数据库连接
sudo -u postgres psql movie_crawler -c "SELECT 1;"

# 检查PostgreSQL状态
sudo systemctl status postgresql
```

### 3. 权限问题

```bash
# 检查文件权限
ls -la /opt/movie_crawler/

# 修复权限
sudo chown -R crawler:crawler /opt/movie_crawler/
```

### 4. 内存不足

```bash
# 查看内存使用
free -h

# 创建swap文件
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## 📈 性能优化

### 1. 调整并发数

```bash
# 根据服务器配置调整
python linux_crawler.py --workers 2  # 低配置服务器
python linux_crawler.py --workers 5  # 高配置服务器
```

### 2. 批次大小优化

```bash
# 小批次（稳定）
python linux_crawler.py --batch-size 5

# 大批次（高效）
python linux_crawler.py --batch-size 20
```

### 3. 资源限制

```bash
# 限制内存使用
ulimit -v 2097152  # 2GB

# 限制进程数
ulimit -u 1024
```
