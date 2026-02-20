"""
币安期货AI分析系统 - 配置管理模块

所有敏感信息（API密钥）应通过环境变量传入，不应硬编码在代码中。

使用方法：
    # Linux/Mac
    export BINANCE_API_KEY="your-key"
    export BINANCE_API_SECRET="your-secret"
    export DEEPSEEK_API_KEY="your-key"
    
    # Windows
    set BINANCE_API_KEY=your-key
    set BINANCE_API_SECRET=your-secret
    set DEEPSEEK_API_KEY=your-key
"""

import os
from typing import Optional


def _get_env_or_fail(key: str, description: str) -> str:
    """
    获取环境变量，若未设置则抛出异常
    
    Args:
        key: 环境变量名
        description: 变量描述（用于错误提示）
    
    Returns:
        环境变量的值
    
    Raises:
        ValueError: 如果环境变量未设置
    """
    value = os.getenv(key)
    if not value:
        raise ValueError(
            f"缺少必需的环境变量: {key} ({description})\n"
            f"请设置环境变量后重试。示例: export {key}=your-value"
        )
    return value


# ==================== 必需的API密钥（必须通过环境变量提供） ====================
try:
    API_KEY = _get_env_or_fail("BINANCE_API_KEY", "币安期货API密钥")
    API_SECRET = _get_env_or_fail("BINANCE_API_SECRET", "币安期货API密钥秘密")
    DEEPSEEK_API_KEY = _get_env_or_fail("DEEPSEEK_API_KEY", "DeepSeek AI API密钥")
except ValueError as e:
    print(f"⚠️ 配置错误: {e}")
    raise


# ==================== 交易所API配置 ====================
"""币安期货 Restful API 端点"""
BINANCE_API_URL = "https://fapi.binance.com"

"""币安期货 WebSocket 端点（未来使用）"""
BINANCE_WS_URL = "wss://fstream.binance.com"


# ==================== 数据刷新配置 ====================
"""
数据刷新间隔（秒）
- 建议值：2-5秒，在数据实时性和API限速之间平衡
- 生产环境建议设置为 5 秒
"""
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL", "2"))

"""
K线时间间隔
- 支持值: 1m, 5m, 15m, 30m, 1h, 4h, 1d
- 默认使用1小时K线用于分析
"""
KLINE_INTERVAL = os.getenv("KLINE_INTERVAL", "1h")


# ==================== 应用配置 ====================
"""应用标题，显示在浏览器标签和页面标题中"""
TITLE = os.getenv("APP_TITLE", "币安期货AI分析系统")

"""应用主题（暗色主题）"""
THEME = "dark"


# ==================== Streamlit服务器配置 ====================
"""
Streamlit服务器监听端口
- 默认: 8501
- 建议Linux部署时使用: 8501
"""
SERVER_PORT = int(os.getenv("SERVER_PORT", "8501"))

"""
Streamlit服务器监听地址
- 0.0.0.0: 监听所有网络接口（用于远程访问）
- 127.0.0.1: 仅本地访问
"""
SERVER_ADDRESS = os.getenv("SERVER_ADDRESS", "0.0.0.0")


# ==================== 数据库配置 ====================
"""SQLite数据库文件路径"""
DATABASE_PATH = os.getenv("DATABASE_PATH", "./analysis_cache.db")

"""数据缓存时间（秒）：7天"""
CACHE_TTL_SECONDS = 7 * 24 * 3600

"""后台AI分析间隔（秒）：5分钟"""
AI_ANALYSIS_INTERVAL = 300


# ==================== 日志配置 ====================
"""是否启用详细日志输出"""
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"