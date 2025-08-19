# AlmaLinux 8.10 VPS 部署指南

## 🚀 快速部署

### 1. 运行自动部署脚本

```bash
# 下载并运行部署脚本
wget https://your-server.com/almalinux_deployment_setup.sh
chmod +x almalinux_deployment_setup.sh
sudo ./almalinux_deployment_setup.sh
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

## 🔧 手动部署步骤（AlmaLinux特定）

### 1. 系统准备

```bash
# 更新系统
sudo dnf update -y

# 安装EPEL仓库
sudo dnf install -y epel-release

# 安装基础软件
sudo dnf install -y python3 python3-pip python3-devel git curl wget gcc gcc-c++ make
```

### 2. 安装Chrome（AlmaLinux方式）

```bash
# 创建Google Chrome仓库文件
sudo tee /etc/yum.repos.d/google-chrome.repo << 'EOF'
[google-chrome]
name=google-chrome
baseurl=http://dl.google.com/linux/chrome/rpm/stable/x86_64
enabled=1
gpgcheck=1
gpgkey=https://dl.google.com/linux/linux_signing_key.pub
EOF

# 安装Chrome
sudo dnf install -y google-chrome-stable

# 安装X11和依赖
sudo dnf install -y xorg-x11-server-Xvfb gtk3 libXScrnSaver alsa-lib \
    nss atk at-spi2-atk cups-libs drm libxkbcommon \
    libXcomposite libXdamage libXrandr mesa-libgbm \
    libXss libgconf
```

### 3. 安装PostgreSQL（AlmaLinux方式）

```bash
# 安装PostgreSQL
sudo dnf install -y postgresql postgresql-server postgresql-contrib postgresql-devel

# 初始化数据库
sudo postgresql-setup --initdb

# 启动服务
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库和用户
sudo -u postgres createdb movie_crawler
sudo -u postgres createuser -P crawler_user
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE movie_crawler TO crawler_user;"
```

### 4. 配置PostgreSQL认证

```bash
# 编辑pg_hba.conf允许本地连接
sudo vim /var/lib/pgsql/data/pg_hba.conf

# 找到以下行并修改：
# local   all             all                                     peer
# 改为：
# local   all             all                                     md5

# 重启PostgreSQL
sudo systemctl restart postgresql
```

### 5. 创建项目环境

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

## 🎯 AlmaLinux特定配置

### 1. SELinux配置

```bash
# 检查SELinux状态
getenforce

# 如果是Enforcing，需要配置SELinux策略
sudo setsebool -P httpd_can_network_connect 1

# 设置文件上下文
sudo semanage fcontext -a -t bin_t "/opt/movie_crawler/venv/bin/python"
sudo restorecon -R /opt/movie_crawler/
```

### 2. 防火墙配置

```bash
# 检查firewalld状态
sudo systemctl status firewalld

# 如果运行中，配置防火墙
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --reload

# 查看开放的端口
sudo firewall-cmd --list-all
```

### 3. 系统服务配置

```bash
# 重新加载systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start movie-crawler

# 设置开机自启
sudo systemctl enable movie-crawler

# 查看服务状态
sudo systemctl status movie-crawler
```

## 📊 监控和维护（AlmaLinux）

### 1. 查看日志

```bash
# 系统服务日志
sudo journalctl -u movie-crawler -f

# 应用日志
sudo tail -f /opt/movie_crawler/src/logs/crawler.log

# PostgreSQL日志
sudo tail -f /var/lib/pgsql/data/log/postgresql-*.log
```

### 2. 性能监控

```bash
# 安装htop
sudo dnf install -y htop

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

# 查看数据库大小
\l+

# 查看表大小
\dt+

# 查看连接数
SELECT count(*) FROM pg_stat_activity;
```

## 🚨 AlmaLinux故障排除

### 1. Chrome问题

```bash
# 检查Chrome版本
google-chrome --version

# 测试Chrome（无头模式）
google-chrome --headless --no-sandbox --dump-dom https://www.google.com

# 检查X11依赖
ldd /usr/bin/google-chrome | grep "not found"
```

### 2. PostgreSQL连接问题

```bash
# 检查PostgreSQL状态
sudo systemctl status postgresql

# 检查端口监听
sudo netstat -tlnp | grep 5432

# 测试本地连接
sudo -u postgres psql -c "SELECT 1;"

# 检查认证配置
sudo cat /var/lib/pgsql/data/pg_hba.conf
```

### 3. SELinux问题

```bash
# 查看SELinux拒绝日志
sudo ausearch -m AVC -ts recent

# 临时禁用SELinux（仅用于测试）
sudo setenforce 0

# 永久禁用SELinux（不推荐）
sudo sed -i 's/SELINUX=enforcing/SELINUX=disabled/' /etc/selinux/config
```

### 4. 权限问题

```bash
# 检查文件权限
ls -la /opt/movie_crawler/

# 修复权限
sudo chown -R crawler:crawler /opt/movie_crawler/
sudo chmod +x /opt/movie_crawler/start_crawler.sh
```

### 5. Python依赖问题

```bash
# 检查虚拟环境
source /opt/movie_crawler/venv/bin/activate
pip list

# 重新安装依赖
pip install --force-reinstall -r linux_requirements.txt

# 检查Python路径
which python
python --version
```

## 📈 AlmaLinux性能优化

### 1. 系统优化

```bash
# 增加文件描述符限制
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# 优化内核参数
echo "vm.swappiness=10" >> /etc/sysctl.conf
echo "net.core.somaxconn=65535" >> /etc/sysctl.conf
sysctl -p
```

### 2. PostgreSQL优化

```bash
# 编辑PostgreSQL配置
sudo vim /var/lib/pgsql/data/postgresql.conf

# 优化参数（根据服务器配置调整）
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
```

### 3. 创建swap文件（如果内存不足）

```bash
# 创建2GB swap文件
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 永久启用
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

## 🔒 安全配置

### 1. 用户安全

```bash
# 创建专用用户
sudo useradd -r -s /bin/bash -d /opt/movie_crawler crawler

# 禁用root SSH登录（可选）
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

### 2. 网络安全

```bash
# 只允许必要的服务
sudo firewall-cmd --permanent --remove-service=dhcpv6-client
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --reload
```

### 3. 自动更新

```bash
# 安装自动更新
sudo dnf install -y dnf-automatic

# 配置自动更新
sudo systemctl enable --now dnf-automatic.timer
```

这个指南专门针对AlmaLinux 8.10系统，使用正确的包管理器和系统配置！🎯
