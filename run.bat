@echo off
chcp 65001 >nul
echo ================================================
echo 币安仓位监控系统 - 启动脚本
echo ================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未检测到Python安装！
    echo 请访问 https://www.python.org/downloads/ 安装Python
    pause
    exit /b 1
)

echo ✓ Python 已安装
echo.

REM 升级pip
echo 正在升级pip...
python -m pip install --upgrade pip setuptools wheel -q

REM 清理缓存
echo 正在清理缓存...
python -m pip cache purge -q

REM 安装依赖（仅预编译轮子）
echo 正在安装依赖包（这可能需要1-2分钟）...
python -m pip install --no-cache-dir --only-binary=:all: streamlit>=1.25.0 requests>=2.28.0 plotly>=5.10.0 pytz>=2023.3

if errorlevel 1 (
    echo.
    echo 依赖安装失败
    echo 请查看: FINAL_FIX.md 文件获取帮助
    pause
    exit /b 1
)

echo.
echo ✓ 依赖已安装
echo.
echo 正在测试网络连接...
python -c "import requests; r = requests.get('https://fapi.binance.com/fapi/v1/ping', timeout=10); print('✓ 币安API连接正常' if r.status_code == 200 else '❌ 币安API连接失败')" 2>nul
if errorlevel 1 (
    echo ❌ 网络连接测试失败，请检查网络连接
    echo.
)

echo.
echo 正在启动应用...
echo.
echo 应用已打开，默认访问地址: http://localhost:8501
echo.
echo 按 Ctrl+C 停止应用
echo.

REM 启动Streamlit应用（使用python -m的方式更可靠）
python -m streamlit run main.py --logger.level=error --server.address=localhost --server.port=8501

pause