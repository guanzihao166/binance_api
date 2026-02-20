#!/bin/bash

################################################################################
# 币安期货AI分析系统 - Linux自动安装脚本
################################################################################
#
# 功能：全自动安装币安期货AI分析系统到Linux服务器
# 支持系统：Ubuntu 20.04+, Debian 11+, Rocky Linux 8+, CentOS 8+
# 使用权限：需要sudo权限
# 用法：
#   sudo ./install_linux.sh                    # 在当前目录拉取代码
#   sudo ./install_linux.sh /custom/path       # 在指定目录拉取代码
#
# 安装内容：
#   1. Python 3.11+ 和 pip
#   2. 创建虚拟环境
#   3. 安装Python依赖（requirements.txt）
#   4. 创建 .env 配置文件（交互式输入）
#   5. 创建 systemd 服务文件
#   6. 启动系统服务
#
# 注：目录位置由第一个参数指定，默认为当前目录 (.)
#
################################################################################

set -e  # 任何命令失败时停止执行

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# 全局配置
APP_DIR="${1:-.}"  # 使用第一个参数作为目录，默认为当前目录 (.)
SERVICE_NAME="binance-ai-analyzer"
GITHUB_REPO="https://github.com/guanzihao166/binance_api.git"

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

# 检查应用目录
check_and_backup_app_dir() {
    # 如果是当前目录，则跳过备份
    if [[ "$APP_DIR" == "." ]]; then
        log_info "在当前目录拉取代码"
        return 0
    fi
    
    log_info "检查应用目录: $APP_DIR"
    
    if [[ -d "$APP_DIR" ]]; then
        log_warning "目录已存在，备份旧版本..."
        # 确保目录名不以斜杠结尾
        APP_DIR_CLEAN=${APP_DIR%/}
        mv "$APP_DIR_CLEAN" "${APP_DIR_CLEAN}.$(date +%Y%m%d_%H%M%S).bak"
    fi
}

# 获取应用代码
get_application_code() {
    log_info "获取应用代码..."
    
    # 从GitHub克隆项目
    if [[ "$APP_DIR" == "." ]]; then
        # 当前目录模式：使用"."作为目标
        if git clone "$GITHUB_REPO" .; then
            log_success "项目代码克隆完成"
        else
            log_error "克隆项目失败，请检查网络连接"
            exit 1
        fi
    else
        # 指定目录模式：创建新目录
        if git clone "$GITHUB_REPO" "$APP_DIR"; then
            log_success "项目代码克隆完成"
            cd "$APP_DIR"
        else
            log_error "克隆项目失败，请检查网络连接"
            exit 1
        fi
    fi
    
    log_success "应用代码已就位"
}

# 创建便捷启动脚本
create_startup_script() {
    log_info "创建便捷启动脚本..."
    
    STARTUP_SCRIPT="$APP_DIR/start.sh"
    
    cat > "$STARTUP_SCRIPT" << 'EOF'
#!/bin/bash
# 币安期货AI分析系统启动脚本

cd "$(dirname "$0")"
echo "启动币安期货AI分析系统..."
echo "访问地址: http://localhost:8501"
echo ""

# 使用虚拟环境中的 streamlit 运行应用
./venv/bin/streamlit run main.py \
    --server.address=0.0.0.0 \
    --server.port=8501 \
    --logger.level=info
EOF

    chmod +x "$STARTUP_SCRIPT"
    log_success "启动脚本已创建: $APP_DIR/start.sh"
}

# 创建Python虚拟环境
create_virtual_environment() {
    log_info "创建Python虚拟环境..."
    
    python3.11 -m venv "$APP_DIR/venv" || python3 -m venv "$APP_DIR/venv"
    
    # 使用虚拟环境的完整路径来升级pip（不依赖于激活）
    "$APP_DIR/venv/bin/python" -m pip install -q --upgrade pip setuptools wheel
    
    log_success "虚拟环境创建完成"
    log_info "虚拟环境位置: $APP_DIR/venv"
}

# 安装Python依赖
install_python_packages() {
    log_info "安装Python依赖包（这可能需要几分钟）..."
    
    cd "$APP_DIR"
    
    # 使用虚拟环境的完整路径来安装依赖
    if [[ -f "requirements.txt" ]]; then
        "$APP_DIR/venv/bin/pip" install -q -r requirements.txt
        log_success "Python依赖安装完成"
    else
        log_error "找不到 requirements.txt 文件"
        exit 1
    fi
}

# 配置API密钥（支持交互式和非交互式环境）
get_api_keys() {
    # 检查是否为交互式环境 (-t 0 检查标准输入是否是终端)
    if [[ -t 0 ]]; then
        # 交互式环境：提示用户输入
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
    else
        # 非交互式环境：从环境变量读取
        log_info "检测到非交互式环境，从环境变量读取API配置..."
        
        BINANCE_API_KEY="${BINANCE_API_KEY:-}"
        BINANCE_API_SECRET="${BINANCE_API_SECRET:-}"
        DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-}"
        
        # 如果环境变量为空，使用占位符（需要后续手动配置）
        if [[ -z "$BINANCE_API_KEY" ]] || [[ -z "$BINANCE_API_SECRET" ]] || [[ -z "$DEEPSEEK_API_KEY" ]]; then
            log_warning "检测到部分API密钥未配置"
            log_warning "请设置以下环境变量后重新运行："
            log_warning "  export BINANCE_API_KEY='your-key'"
            log_warning "  export BINANCE_API_SECRET='your-secret'"
            log_warning "  export DEEPSEEK_API_KEY='your-key'"
            log_warning ""
            
            # 使用占位符，允许脚本继续运行
            BINANCE_API_KEY="${BINANCE_API_KEY:-PLACEHOLDER_API_KEY}"
            BINANCE_API_SECRET="${BINANCE_API_SECRET:-PLACEHOLDER_API_SECRET}"
            DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-PLACEHOLDER_DEEPSEEK_KEY}"
            
            log_warning "使用占位符继续安装，请在安装后编辑 .env 文件配置真实密钥"
        else
            log_success "从环境变量读取API密钥成功"
        fi
    fi
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
    # 如果在当前目录运行，跳过systemd服务创建
    if [[ "$APP_DIR" == "." ]]; then
        log_warning "当前目录模式，跳过systemd服务创建"
        log_info "可手动运行: streamlit run main.py"
        return 0
    fi
    
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
    # 如果在当前目录运行，跳过systemd相关操作
    if [[ "$APP_DIR" == "." ]]; then
        return 0
    fi
    
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
    
    if [[ "$APP_DIR" == "." ]]; then
        # 当前目录模式
        echo -e "${BLUE}ℹ️  应用信息：${NC}"
        echo "  应用路径: 当前目录"
        echo "  配置文件: ./.env"
        echo "  虚拟环境: ./venv"
        echo ""
        echo -e "${BLUE}▶️  启动应用 - 方法1（推荐）：${NC}"
        echo "  运行: ./start.sh"
        echo ""
        echo -e "${BLUE}▶️  启动应用 - 方法2（手动激活虚拟环境）：${NC}"
        echo "  1. 激活虚拟环境: source venv/bin/activate"
        echo "  2. 运行应用: streamlit run main.py"
        echo "  3. 关闭应用: deactivate（退出虚拟环境）"
        echo ""
        echo -e "${BLUE}▶️  启动应用 - 方法3（直接使用虚拟环境中的streamlit）：${NC}"
        echo "  运行: ./venv/bin/streamlit run main.py"
        echo ""
        echo -e "${BLUE}🌐 访问应用：${NC}"
        echo "  本地访问: http://localhost:8501"
        echo ""
        echo -e "${BLUE}⚙️  修改配置：${NC}"
        echo "  编辑 ./.env 文件"
        echo "  重新启动应用"
        echo ""
    else
        # 指定目录模式
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
    fi
    
    # 检查是否使用了占位符
    ENV_FILE="${APP_DIR}/.env"
    if [[ "$APP_DIR" == "." ]]; then
        ENV_FILE="./.env"
    fi
    
    if [[ -f "$ENV_FILE" ]] && grep -q "PLACEHOLDER" "$ENV_FILE"; then
        echo -e "${RED}❌ 警告：检测到占位符API密钥${NC}"
        echo -e "${YELLOW}   请立即编辑 $ENV_FILE 文件${NC}"
        echo -e "${YELLOW}   用真实的API密钥替换以下字段：${NC}"
        echo -e "${YELLOW}   - BINANCE_API_KEY${NC}"
        echo -e "${YELLOW}   - BINANCE_API_SECRET${NC}"
        echo -e "${YELLOW}   - DEEPSEEK_API_KEY${NC}"
        echo ""
    fi
    
    echo -e "${BLUE}📚 文档：${NC}"
    echo "  README: $APP_DIR/README.md"
    echo "  快速开始: $APP_DIR/QUICKSTART.md"
    echo ""
    echo -e "${YELLOW}⚠️  重要提示：${NC}"
    echo "  - API密钥已安全保存在 $ENV_FILE"
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
    check_and_backup_app_dir
    get_application_code
    create_virtual_environment
    install_python_packages
    create_startup_script
    get_api_keys
    create_env_file
    create_systemd_service
    enable_and_start_service
    show_completion_info
}

# 执行安装
main
