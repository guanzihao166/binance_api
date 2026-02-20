#!/bin/bash

echo "================================================"
echo "币安期货AI分析系统 - 启动脚本"
echo "================================================"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查Python版本
if ! command -v python3.11 &> /dev/null && ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未检测到Python安装！"
    echo "请安装 Python 3.11 或更高版本"
    exit 1
fi

PYTHON_CMD="python3.11"
if ! command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3"
fi

echo "✓ Python 已安装: $($PYTHON_CMD --version)"
echo ""

# 检查虚拟环境是否存在
if [[ ! -d "venv" ]]; then
    echo "⚠️  未检测到虚拟环境，正在创建..."
    $PYTHON_CMD -m venv venv || {
        echo "❌ 虚拟环境创建失败"
        exit 1
    }
    echo "✓ 虚拟环境已创建"
    echo ""
    
    # 创建虚拟环境后立即升级pip
    echo "正在升级pip..."
    ./venv/bin/pip install -q --upgrade pip setuptools wheel
    echo ""
fi

# 激活虚拟环境
echo "✓ 激活虚拟环境"
source venv/bin/activate

# 检查requirements.txt
if [[ ! -f "requirements.txt" ]]; then
    echo "❌ 错误: 未找到 requirements.txt 文件"
    exit 1
fi

# 安装/更新依赖
echo "正在检查依赖..."
if ! python -c "import streamlit" 2>/dev/null; then
    echo "正在安装依赖包，请稍候..."
    pip install -q -r requirements.txt
    if [[ $? -ne 0 ]]; then
        echo "❌ 依赖安装失败，请检查网络连接"
        deactivate
        exit 1
    fi
fi

echo "✓ 依赖已就绪"
echo ""

# 检查.env文件
if [[ ! -f ".env" ]]; then
    echo "⚠️  未检测到 .env 配置文件"
    echo "请复制 .env.example 并修改:"
    echo "  cp .env.example .env"
    echo "  vim .env"
    echo ""
fi

echo "✓ 正在启动应用..."
echo ""
echo "================================================"
echo "币安期货AI分析系统已启动"
echo "访问地址: http://localhost:8501"
echo "按 Ctrl+C 停止应用"
echo "================================================"
echo ""

# 启动Streamlit应用
streamlit run main.py \
    --server.address=0.0.0.0 \
    --server.port=8501 \
    --logger.level=info

# 脚本退出时退出虚拟环境
deactivate
