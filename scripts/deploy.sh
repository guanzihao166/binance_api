#!/bin/bash

################################################################################
# 币安期货AI分析系统 - 部署更新脚本
################################################################################
#
# 功能：更新应用代码并重启服务
# 使用权限：需要sudo权限
# 用法：sudo ./deploy.sh
#
# 执行步骤：
#   1. 停止现有服务
#   2. 拉取最新代码（git pull）
#   3. 更新Python依赖
#   4. 重启服务
#   5. 验证服务状态
#
# 可选参数：
#   --no-restart: 仅更新代码和依赖，不重启服务
#   --quick: 快速部署（跳过依赖更新）
#
################################################################################

set -e

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

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查权限
if [[ $EUID -ne 0 ]]; then
    log_error "此脚本需要root权限执行"
    echo "请使用以下命令运行："
    echo "  sudo ./deploy.sh"
    exit 1
fi

# 解析参数
NO_RESTART=false
QUICK_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-restart)
            NO_RESTART=true
            shift
            ;;
        --quick)
            QUICK_MODE=true
            shift
            ;;
        *)
            log_error "未知参数: $1"
            exit 1
            ;;
    esac
done

# 应用配置
APP_DIR="/opt/binance-ai-analyzer"
SERVICE_NAME="binance-ai-analyzer"

# 验证应用目录存在
if [[ ! -d "$APP_DIR" ]]; then
    log_error "应用目录不存在: $APP_DIR"
    echo "请先运行 install_linux.sh 进行初始化安装"
    exit 1
fi

# 进入应用目录
cd "$APP_DIR"

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  币安期货AI分析系统 - 部署更新${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""

# 备份当前代码
log_info "备份当前代码..."
BACKUP_DIR="$APP_DIR/.backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
find . -maxdepth 1 -type f -name "*.py" -o -name "*.txt" | xargs -I {} cp {} "$BACKUP_DIR/" 2>/dev/null || true
log_success "备份完成: $BACKUP_DIR"

# 停止服务
log_info "停止服务..."
if systemctl is-active --quiet "$SERVICE_NAME"; then
    systemctl stop "$SERVICE_NAME"
    sleep 2
    log_success "服务已停止"
else
    log_info "服务未运行"
fi

# 更新代码
log_info "更新代码..."
if [[ -d ".git" ]]; then
    git pull origin master || {
        log_error "代码更新失败，尝试恢复备份..."
        exit 1
    }
    log_success "代码更新完成"
else
    log_error "此目录不是git仓库，无法自动更新"
    echo "请确保在项目目录中运行此脚本"
    exit 1
fi

# 更新Python依赖（仅非快速模式）
if [[ "$QUICK_MODE" == false ]]; then
    log_info "更新Python依赖..."
    source "$APP_DIR/venv/bin/activate"
    
    if [[ -f "requirements.txt" ]]; then
        pip install -q --upgrade -r requirements.txt
        log_success "依赖更新完成"
    else
        log_error "找不到 requirements.txt"
        exit 1
    fi
else
    log_info "跳过依赖更新（快速模式）"
fi

# 验证环境
log_info "验证应用环境..."
source "$APP_DIR/venv/bin/activate"
python -c "import streamlit; import plotly; import pandas" 2>/dev/null || {
    log_error "环境验证失败，某些依赖可能缺失"
    exit 1
}
log_success "环境验证通过"

# 重启服务（除非指定 --no-restart）
if [[ "$NO_RESTART" == false ]]; then
    log_info "重启服务..."
    systemctl restart "$SERVICE_NAME"
    sleep 3
    
    # 检查服务状态
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "服务已启动"
    else
        log_error "服务启动失败"
        log_info "查看详细日志:"
        echo "  journalctl -u $SERVICE_NAME -n 50"
        exit 1
    fi
else
    log_info "跳过服务重启（--no-restart）"
fi

# 显示部署完成信息
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  部署更新完成！${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}ℹ️  部署信息：${NC}"
echo "  应用目录: $APP_DIR"
echo "  服务名称: $SERVICE_NAME"
echo "  备份路径: $BACKUP_DIR"
echo ""

if [[ "$NO_RESTART" == false ]]; then
    echo -e "${BLUE}📋 服务状态：${NC}"
    systemctl status "$SERVICE_NAME" --no-pager | head -10
    echo ""
    echo -e "${BLUE}🌐 访问应用：${NC}"
    echo "  http://localhost:8501 (本地)"
    echo "  http://your-server-ip:8501 (远程)"
else
    log_info "手动启动服务："
    echo "  systemctl start $SERVICE_NAME"
fi

echo ""
echo -e "${BLUE}📚 常用命令：${NC}"
echo "  查看日志: journalctl -u $SERVICE_NAME -f"
echo "  重启服务: systemctl restart $SERVICE_NAME"
echo "  停止服务: systemctl stop $SERVICE_NAME"
echo "  查看备份: ls -la $APP_DIR/.backups/"
echo ""

echo -e "${GREEN}✅ 部署成功！${NC}"
echo ""
