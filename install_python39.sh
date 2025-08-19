#!/bin/bash

# Python 3.9 安装脚本 - 支持 CentOS/RHEL/AlmaLinux 系统
# 作者: Movie Crawler Project
# 版本: 1.0
# 日期: 2025-08-16

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 错误处理函数
error_exit() {
    log_error "$1"
    exit 1
}

# 检查是否为root用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error_exit "此脚本需要root权限运行，请使用 sudo 或切换到root用户"
    fi
}

# 检测操作系统
detect_os() {
    if [[ -f /etc/redhat-release ]]; then
        OS="centos"
        if grep -q "CentOS" /etc/redhat-release; then
            OS_VERSION=$(grep -oE '[0-9]+' /etc/redhat-release | head -1)
        elif grep -q "AlmaLinux" /etc/redhat-release; then
            OS="almalinux"
            OS_VERSION=$(grep -oE '[0-9]+' /etc/redhat-release | head -1)
        elif grep -q "Red Hat" /etc/redhat-release; then
            OS="rhel"
            OS_VERSION=$(grep -oE '[0-9]+' /etc/redhat-release | head -1)
        fi
        PACKAGE_MANAGER="yum"
        if command -v dnf >/dev/null 2>&1; then
            PACKAGE_MANAGER="dnf"
        fi
    else
        error_exit "不支持的操作系统。此脚本仅支持 CentOS/RHEL/AlmaLinux 系统"
    fi
    
    log_info "检测到操作系统: $OS $OS_VERSION"
    log_info "包管理器: $PACKAGE_MANAGER"
}

# 检查当前Python版本
check_current_python() {
    log_info "检查当前Python版本..."
    
    if command -v python3 >/dev/null 2>&1; then
        CURRENT_PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
        log_info "当前Python版本: $CURRENT_PYTHON_VERSION"
        
        # 检查是否已经是Python 3.9+
        MAJOR_VERSION=$(echo $CURRENT_PYTHON_VERSION | cut -d. -f1)
        MINOR_VERSION=$(echo $CURRENT_PYTHON_VERSION | cut -d. -f2)
        
        if [[ $MAJOR_VERSION -eq 3 && $MINOR_VERSION -ge 9 ]]; then
            log_success "当前Python版本 $CURRENT_PYTHON_VERSION 已满足要求 (>=3.9)"
            return 0
        else
            log_warning "当前Python版本 $CURRENT_PYTHON_VERSION 低于要求的3.9版本"
            return 1
        fi
    else
        log_warning "未检测到Python3，将进行全新安装"
        return 1
    fi
}

# 安装编译依赖
install_build_dependencies() {
    log_info "安装编译依赖包..."
    
    local packages=(
        "gcc"
        "gcc-c++"
        "make"
        "zlib-devel"
        "bzip2-devel"
        "openssl-devel"
        "ncurses-devel"
        "sqlite-devel"
        "readline-devel"
        "tk-devel"
        "gdbm-devel"
        "db4-devel"
        "libpcap-devel"
        "xz-devel"
        "expat-devel"
        "libffi-devel"
        "wget"
        "tar"
    )
    
    for package in "${packages[@]}"; do
        if ! rpm -q "$package" >/dev/null 2>&1; then
            log_info "安装 $package..."
            $PACKAGE_MANAGER install -y "$package" || log_warning "安装 $package 失败，继续执行"
        else
            log_info "$package 已安装"
        fi
    done
    
    log_success "编译依赖安装完成"
}

# 下载并编译安装Python 3.9
install_python39() {
    log_info "开始安装Python 3.9..."
    
    local PYTHON_VERSION="3.9.19"
    local PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz"
    local TEMP_DIR="/tmp/python39_install"
    
    # 创建临时目录
    mkdir -p "$TEMP_DIR"
    cd "$TEMP_DIR"
    
    # 下载Python源码
    log_info "下载Python ${PYTHON_VERSION}源码..."
    if ! wget -O "Python-${PYTHON_VERSION}.tgz" "$PYTHON_URL"; then
        error_exit "下载Python源码失败"
    fi
    
    # 解压源码
    log_info "解压Python源码..."
    tar -xzf "Python-${PYTHON_VERSION}.tgz"
    cd "Python-${PYTHON_VERSION}"
    
    # 配置编译选项
    log_info "配置编译选项..."
    ./configure --enable-optimizations \
                --with-ensurepip=install \
                --enable-shared \
                --prefix=/usr/local/python39 \
                LDFLAGS="-Wl,-rpath /usr/local/python39/lib" || error_exit "配置失败"
    
    # 编译（使用多核心加速）
    local CPU_CORES=$(nproc)
    log_info "开始编译Python（使用 $CPU_CORES 个CPU核心）..."
    make -j"$CPU_CORES" || error_exit "编译失败"
    
    # 安装
    log_info "安装Python 3.9..."
    make altinstall || error_exit "安装失败"
    
    # 创建软链接
    log_info "创建Python 3.9软链接..."
    ln -sf /usr/local/python39/bin/python3.9 /usr/local/bin/python3.9
    ln -sf /usr/local/python39/bin/pip3.9 /usr/local/bin/pip3.9
    
    # 更新系统默认python3链接
    if [[ -L /usr/bin/python3 ]]; then
        rm -f /usr/bin/python3
    fi
    ln -sf /usr/local/python39/bin/python3.9 /usr/bin/python3
    
    if [[ -L /usr/bin/pip3 ]]; then
        rm -f /usr/bin/pip3
    fi
    ln -sf /usr/local/python39/bin/pip3.9 /usr/bin/pip3
    
    # 更新动态链接库配置
    echo "/usr/local/python39/lib" > /etc/ld.so.conf.d/python39.conf
    ldconfig
    
    # 清理临时文件
    cd /
    rm -rf "$TEMP_DIR"
    
    log_success "Python 3.9安装完成"
}

# 验证安装
verify_installation() {
    log_info "验证Python 3.9安装..."
    
    # 检查Python版本
    if command -v python3 >/dev/null 2>&1; then
        INSTALLED_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
        log_success "Python版本: $INSTALLED_VERSION"
        
        # 验证版本是否为3.9+
        MAJOR=$(echo $INSTALLED_VERSION | cut -d. -f1)
        MINOR=$(echo $INSTALLED_VERSION | cut -d. -f2)
        
        if [[ $MAJOR -eq 3 && $MINOR -ge 9 ]]; then
            log_success "Python版本验证通过"
        else
            error_exit "Python版本验证失败，当前版本: $INSTALLED_VERSION"
        fi
    else
        error_exit "Python3命令未找到"
    fi
    
    # 检查pip
    if command -v pip3 >/dev/null 2>&1; then
        PIP_VERSION=$(pip3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
        log_success "Pip版本: $PIP_VERSION"
    else
        error_exit "Pip3命令未找到"
    fi
    
    # 测试requests安装
    log_info "测试安装requests>=2.31.0..."
    if pip3 install "requests>=2.31.0" --quiet; then
        log_success "requests>=2.31.0安装成功"
        
        # 验证requests版本
        REQUESTS_VERSION=$(python3 -c "import requests; print(requests.__version__)" 2>/dev/null)
        log_success "Requests版本: $REQUESTS_VERSION"
    else
        log_error "requests>=2.31.0安装失败"
        return 1
    fi
}

# 主函数
main() {
    log_info "开始Python 3.9安装流程..."
    
    # 检查root权限
    check_root
    
    # 检测操作系统
    detect_os
    
    # 检查当前Python版本
    if check_current_python; then
        log_info "Python版本已满足要求，跳过安装"
        verify_installation
        return 0
    fi
    
    # 安装编译依赖
    install_build_dependencies
    
    # 安装Python 3.9
    install_python39
    
    # 验证安装
    verify_installation
    
    log_success "Python 3.9安装流程完成！"
    log_info "现在可以使用 python3 和 pip3 命令"
    log_info "Python路径: /usr/local/python39/bin/python3.9"
    log_info "Pip路径: /usr/local/python39/bin/pip3.9"
}

# 执行主函数
main "$@"