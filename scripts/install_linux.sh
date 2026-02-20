#!/bin/bash

################################################################################
# 币安期货AI分析系统 - Linux自动安装脚本
################################################################################
#
# 功能：全自动安装币安期货AI分析系统到Linux服务器
# 支持系统：Ubuntu 20.04+, Debian 11+, Rocky Linux 8+, CentOS 8+
# 使用权限：需要sudo权限
# 用法：sudo ./install_linux.sh
#
# 安装内容：
#   1. Python 3.11+ 和 pip
#   2. 创建虚拟环境
#   3. 安装Python依赖（requirements.txt）
#   4. 创建 .env 配置文件（交互式输入）
#   5. 创建 systemd 服务文件
#   6. 启动系统服务
#
# 安装路径：/opt/binance-ai-analyzer/
# 服务名称：binance-ai-analyzer
#
################################################################################

set -e  # 任何命令失败时停止执行

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

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

# 检查是否以root身份运行
if [[ $EUID -ne 0 ]]; then
    log_error "此脚本需要root权限执行"
    echo "请使用以下命令运行："
    echo "  sudo ./install_linux.sh"
    exit 1
fi

# 检查操作系统
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        VERSION=$VERSION_ID
    else
        log_error "无法检测操作系统"
        exit 1
    fi
}

# 安装系统依赖
install_system_packages() {
    log_info "检测操作系统: $OS $VERSION"
    
    case "$OS" in
        ubuntu|debian)
            log_info "更新系统包列表..."
            apt-get update -qq
            
            log_info "安装系统依赖..."
            apt-get install -y \
                python3.11 \
                python3.11-venv \
                python3.11-dev \
                python3-pip \
                git \
                curl \
                wget \
                build-essential \
                libssl-dev \
                libffi-dev > /dev/null 2>&1
            ;;
        rocky|centos|rhel)
            log_info "安装系统依赖..."
            dnf groupinstall -y "Development Tools" > /dev/null 2>&1
            dnf install -y \
                python3.11 \
                python3.11-devel \
                git \
                curl \
                wget > /dev/null 2>&1
            ;;
        *)
            log_warning "不支持的Linux发行版: $OS"
            log_info "请参考README.md手动安装"
            exit 1
            ;;
    esac
    
    log_success "系统依赖安装完成"
}

# 创建应用目录
create_app_directory() {
    APP_DIR="/opt/binance-ai-analyzer"
    
    log_info "创建应用目录: $APP_DIR"
    
    if [[ -d "$APP_DIR" ]]; then
        log_warning "目录已存在，备份旧版本..."
        mv "$APP_DIR" "${APP_DIR}.$(date +%Y%m%d_%H%M%S).bak"
    fi
    
    mkdir -p "$APP_DIR"
    cd "$APP_DIR"
    
    log_success "应用目录已创建"
}

# 获取应用代码
get_application_code() {
    log_info "获取应用代码..."
    
    # 从GitHub克隆项目
    if git clone https://github.com/guanzihao166/binance_api.git "$APP_DIR"; then
        log_success "项目代码克隆完成"
    else
        log_error "克隆项目失败，请检查网络连接"
        exit 1
    fi
    
    log_success "应用代码已就位"
}

# 创建Python虚拟环境
create_virtual_environment() {
    log_info "创建Python虚拟环境..."
    
    python3.11 -m venv "$APP_DIR/venv" || python3 -m venv "$APP_DIR/venv"
    
    # 激活虚拟环境
    source "$APP_DIR/venv/bin/activate"
    
    # 升级pip
    pip install -q --upgrade pip setuptools wheel
    
    log_success "虚拟环境创建完成"
}

# 安装Python依赖
install_python_packages() {
    log_info "安装Python依赖包（这可能需要几分钟）..."
    
    cd "$APP_DIR"
    
    # 激活虚拟环境
    source "$APP_DIR/venv/bin/activate"
    
    # 安装要求的包
    if [[ -f "requirements.txt" ]]; then
        pip install -q -r requirements.txt
        log_success "Python依赖安装完成"
    else
        log_error "找不到 requirements.txt 文件"
        exit 1
    fi
}

# 交互式输入API密钥
get_api_keys() {
    log_info "配置API密钥（安全提示：输入内容不会显示）"
    echo ""
    
    # 币安API密钥
    read -p "请输入币安API密钥: " -r BINANCE_API_KEY
    if [[ -z "$BINANCE_API_KEY" ]]; then
        log_error "币安API密钥不能为空"
        exit 1
    fi
    
    read -p "请输入币安API密钥秘密: " -r BINANCE_API_SECRET
    if [[ -z "$BINANCE_API_SECRET" ]]; then
        log_error "币安API密钥秘密不能为空"
        exit 1
    fi
    
    # DeepSeek API密钥
    read -p "请输入DeepSeek API密钥: " -r DEEPSEEK_API_KEY
    if [[ -z "$DEEPSEEK_API_KEY" ]]; then
        log_error "DeepSeek API密钥不能为空"
        exit 1
    fi
    
    echo ""
    log_success "API密钥已保存"
}

# 创建配置文件
create_env_file() {
    log_info "创建配置文件 .env"
    
    ENV_FILE="$APP_DIR/.env"
    
    cat > "$ENV_FILE" << EOF
# 币安期货API配置
BINANCE_API_KEY=${BINANCE_API_KEY}
BINANCE_API_SECRET=${BINANCE_API_SECRET}

# DeepSeek AI API配置
DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}

# 应用配置
REFRESH_INTERVAL=2
KLINE_INTERVAL=1h
APP_TITLE=币安期货AI分析系统
SERVER_PORT=8501
SERVER_ADDRESS=0.0.0.0
DATABASE_PATH=./analysis_cache.db
DEBUG_MODE=false
EOF

    chmod 600 "$ENV_FILE"
    log_success "配置文件已创建: $ENV_FILE"
}

# 创建systemd服务文件
create_systemd_service() {
    log_info "创建systemd服务文件..."
    
    SERVICE_FILE="/etc/systemd/system/binance-ai-analyzer.service"
    
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Binance AI Analyzer - 币安期货AI分析系统
Documentation=https://github.com/guanzihao166/binance_api
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
EnvironmentFile=$APP_DIR/.env

ExecStart=$APP_DIR/venv/bin/streamlit run main.py \\
    --server.address=0.0.0.0 \\
    --server.port=8501 \\
    --logger.level=info

Restart=on-failure
RestartSec=10
StartLimitInterval=60s
StartLimitBurst=5

# 日志配置
StandardOutput=journal
StandardError=journal
SyslogIdentifier=binance-ai

# 资源限制
LimitNOFILE=65535
LimitNPROC=65535

[Install]
WantedBy=multi-user.target
EOF

    chmod 644 "$SERVICE_FILE"
    log_success "systemd服务文件已创建: $SERVICE_FILE"
}

# 启用和启动服务
enable_and_start_service() {
    log_info "启用systemd服务..."
    
    systemctl daemon-reload
    systemctl enable binance-ai-analyzer
    
    log_info "启动服务..."
    systemctl start binance-ai-analyzer
    
    sleep 2
    
    # 检查服务状态
    if systemctl is-active --quiet binance-ai-analyzer; then
        log_success "服务已成功启动"
    else
        log_error "服务启动失败，请检查日志："
        echo "  journalctl -u binance-ai-analyzer -f"
        exit 1
    fi
}

# 显示安装完成信息
show_completion_info() {
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  币安期货AI分析系统安装完成！${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BLUE}ℹ️  应用信息：${NC}"
    echo "  应用路径: $APP_DIR"
    echo "  服务名称: binance-ai-analyzer"
    echo "  配置文件: $APP_DIR/.env"
    echo ""
    echo -e "${BLUE}📋 常用命令：${NC}"
    echo "  查看服务状态: systemctl status binance-ai-analyzer"
    echo "  查看实时日志: journalctl -u binance-ai-analyzer -f"
    echo "  重启服务: systemctl restart binance-ai-analyzer"
    echo "  停止服务: systemctl stop binance-ai-analyzer"
    echo "  启动服务: systemctl start binance-ai-analyzer"
    echo ""
    echo -e "${BLUE}🌐 访问应用：${NC}"
    echo "  本地访问: http://localhost:8501"
    echo "  远程访问: http://your-server-ip:8501"
    echo ""
    echo -e "${BLUE}⚙️  修改配置：${NC}"
    echo "  编辑 $APP_DIR/.env 文件"
    echo "  运行：systemctl restart binance-ai-analyzer"
    echo ""
    echo -e "${BLUE}📚 文档：${NC}"
    echo "  README: $APP_DIR/README.md"
    echo "  快速开始: $APP_DIR/QUICKSTART.md"
    echo ""
    echo -e "${YELLOW}⚠️  重要提示：${NC}"
    echo "  - API密钥已安全保存在 $APP_DIR/.env"
    echo "  - 禁止将 .env 文件提交到Git"
    echo "  - 定期检查日志排查问题"
    echo "  - 使用Nginx反向代理以启用HTTPS（推荐）"
    echo ""
    echo -e "${GREEN}✅ 安装成功！系统已准备就绪。${NC}"
    echo ""
}

# 错误处理
trap 'log_error "安装过程中出错"; exit 1' ERR

# 主安装流程
main() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  币安期货AI分析系统 - Linux自动安装${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
    echo ""
    
    detect_os
    install_system_packages
    create_app_directory
    get_application_code
    create_virtual_environment
    install_python_packages
    get_api_keys
    create_env_file
    create_systemd_service
    enable_and_start_service
    show_completion_info
}

# 执行安装
main
