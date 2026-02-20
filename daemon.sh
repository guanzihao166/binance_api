#!/bin/bash
################################################################################
# 币安期货AI分析系统 - 后台运行管理脚本
################################################################################
#
# 功能：启动/停止/重启应用，并在后台运行
#
# 使用方法：
#   ./daemon.sh start     # 启动应用
#   ./daemon.sh stop      # 停止应用
#   ./daemon.sh restart   # 重启应用
#   ./daemon.sh status    # 查看运行状态
#   ./daemon.sh logs      # 查看应用日志
#
################################################################################

set -e

# 配置变量
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/venv"
PID_FILE="$APP_DIR/.streamlit.pid"
LOG_FILE="$APP_DIR/streamlit.log"
ENV_FILE="$APP_DIR/.env"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 检查虚拟环境
check_venv() {
    if [[ ! -d "$VENV_DIR" ]]; then
        log_error "未检测到虚拟环境: $VENV_DIR"
        log_info "正在创建虚拟环境..."
        python3.11 -m venv "$VENV_DIR" 2>/dev/null || python3 -m venv "$VENV_DIR"
        
        log_info "升级 pip..."
        "$VENV_DIR/bin/pip" install -q --upgrade pip setuptools wheel
        
        log_info "安装依赖..."
        "$VENV_DIR/bin/pip" install -q -r "$APP_DIR/requirements.txt"
        
        log_success "虚拟环境已创建"
    fi
}

# 检查 .env 文件
check_env_file() {
    if [[ ! -f "$ENV_FILE" ]]; then
        log_warning ".env 文件不存在"
        log_warning "请执行以下命令创建配置文件："
        log_warning "  cp .env.example .env"
        log_warning "  vim .env  # 编辑并填入你的API密钥"
        echo ""
        return 1
    fi
    
    # 检查必需的环境变量
    local missing=0
    for var in BINANCE_API_KEY BINANCE_API_SECRET DEEPSEEK_API_KEY; do
        if ! grep -q "^$var=" "$ENV_FILE" || grep -q "^$var=$\|^$var=''"; then
            log_warning "缺少配置: $var"
            missing=1
        fi
    done
    
    if [[ $missing -eq 1 ]]; then
        log_warning "请编辑 .env 文件填入完整的API密钥"
        return 1
    fi
    
    return 0
}

# 启动应用
start_app() {
    log_info "启动币安期货AI分析系统..."
    
    # 检查虚拟环境和配置
    check_venv
    if ! check_env_file; then
        exit 1
    fi
    
    # 如果应用已运行，先停止
    if [[ -f "$PID_FILE" ]]; then
        local old_pid=$(cat "$PID_FILE")
        if ps -p "$old_pid" > /dev/null 2>&1; then
            log_warning "应用已在运行 (PID: $old_pid)，正在停止..."
            kill "$old_pid" 2>/dev/null || true
            sleep 1
        fi
    fi
    
    # 加载 .env 文件中的环境变量
    export $(cat "$ENV_FILE" | grep -v "^#" | grep "=" | xargs)
    
    # 后台启动 streamlit
    log_info "应用启动命令: $VENV_DIR/bin/streamlit run main.py"
    
    # 使用 nohup 在后台运行
    nohup "$VENV_DIR/bin/streamlit" run "$APP_DIR/main.py" \
        --server.address=0.0.0.0 \
        --server.port=8501 \
        --logger.level=info \
        > "$LOG_FILE" 2>&1 &
    
    local pid=$!
    echo "$pid" > "$PID_FILE"
    
    # 等待应用启动
    sleep 2
    
    if ps -p "$pid" > /dev/null; then
        log_success "应用已启动 (PID: $pid)"
        log_info "日志文件: $LOG_FILE"
        echo ""
        echo "应用信息："
        echo "  地址: http://localhost:8501"
        echo "  日志: tail -f $LOG_FILE"
        echo "  停止: ./daemon.sh stop"
        echo ""
    else
        log_error "应用启动失败，查看日志:"
        tail -20 "$LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
}

# 停止应用
stop_app() {
    if [[ ! -f "$PID_FILE" ]]; then
        log_warning "应用未运行 (找不到PID文件)"
        return
    fi
    
    local pid=$(cat "$PID_FILE")
    
    if ! ps -p "$pid" > /dev/null 2>&1; then
        log_warning "应用未运行 (PID: $pid 不存在)"
        rm -f "$PID_FILE"
        return
    fi
    
    log_info "停止应用 (PID: $pid)..."
    kill "$pid" 2>/dev/null || true
    
    # 等待进程结束
    local count=0
    while ps -p "$pid" > /dev/null 2>&1 && [[ $count -lt 10 ]]; do
        sleep 0.5
        ((count++))
    done
    
    # 如果仍未结束，强制杀死
    if ps -p "$pid" > /dev/null 2>&1; then
        log_warning "应用未正常退出，强制杀死..."
        kill -9 "$pid" 2>/dev/null || true
    fi
    
    rm -f "$PID_FILE"
    log_success "应用已停止"
}

# 重启应用
restart_app() {
    log_info "重启应用..."
    stop_app
    sleep 1
    start_app
}

# 查看运行状态
status_app() {
    if [[ ! -f "$PID_FILE" ]]; then
        echo -e "${YELLOW}应用未运行${NC}"
        return
    fi
    
    local pid=$(cat "$PID_FILE")
    
    if ps -p "$pid" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 应用正在运行${NC}"
        echo "  PID: $pid"
        echo "  地址: http://localhost:8501"
        echo "  日志: $LOG_FILE"
    else
        echo -e "${YELLOW}⚠️  PID 文件存在但进程不运行${NC}"
        echo "  PID: $pid"
        rm -f "$PID_FILE"
    fi
}

# 查看日志
show_logs() {
    if [[ ! -f "$LOG_FILE" ]]; then
        log_error "日志文件不存在: $LOG_FILE"
        return
    fi
    
    log_info "（按 Ctrl+C 退出）"
    echo ""
    tail -f "$LOG_FILE"
}

# 主程序
case "${1:-status}" in
    start)
        start_app
        ;;
    stop)
        stop_app
        ;;
    restart)
        restart_app
        ;;
    status)
        status_app
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "使用方法: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "命令说明："
        echo "  start   - 启动应用"
        echo "  stop    - 停止应用"
        echo "  restart - 重启应用"
        echo "  status  - 查看运行状态"
        echo "  logs    - 实时查看日志"
        echo ""
        echo "示例："
        echo "  ./daemon.sh start          # 启动应用"
        echo "  ./daemon.sh status         # 查看状态"
        echo "  ./daemon.sh logs           # 查看日志"
        echo "  ./daemon.sh restart        # 重启应用"
        exit 1
        ;;
esac
