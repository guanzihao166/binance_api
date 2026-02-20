#!/bin/bash

echo "================================================"
echo "币安仓位监控系统 - 启动脚本"
echo "================================================"
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未检测到Python安装！"
    echo "请访问 https://www.python.org/downloads/ 安装Python"
    exit 1
fi

echo "✓ Python 已安装"
python3 --version
echo ""

# 检查requirements.txt
if [ ! -f "requirements.txt" ]; then
    echo "错误: 未找到 requirements.txt 文件"
    exit 1
fi

echo "正在检查依赖..."
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "正在安装依赖包，请稍候..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "依赖安装失败，请检查网络连接"
        exit 1
    fi
fi

echo "✓ 依赖已就绪"
echo ""
echo "正在启动应用..."
echo ""
echo "应用已打开，默认访问地址: http://localhost:8501"
echo ""
echo "按 Ctrl+C 停止应用"
echo ""

# 启动Streamlit应用
python3 -m streamlit run main.py --logger.level=error
