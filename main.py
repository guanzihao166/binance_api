"""
币安期货AI分析系统 - Streamlit前端应用（main.py）

核心功能：
    1. 实时账户监控：钱包余额、保证金、持仓信息、盈亏统计
    2. K线数据展示：交互式蜡烛线图，支持多时间框架
    3. AI智能分析：显示缓存的DeepSeek分析结果，后台自动更新
    4. 命中率跟踪：历史分析记录，支持标记命中/失误和盈亏输入
    5. 市场分析：7天数据统计，波动率和资金费率分析

架构说明：
    - 前端职责：仅显示数据，不进行复杂计算
    - API调用：委托给utils.py的BinanceAPI类
    - AI分析：由后台BackgroundAnalysisManager线程处理
    - 数据存储：使用database.py的SQLite缓存
    - 配置管理：从config.py读取环境变量

数据刷新流程：
    1. 用户访问页面时，自动加载账户信息和仓位数据
    2. K线数据通过fetch_kline_parallel()并行获取
    3. AI分析结果从数据库缓存读取（5分钟最多更新一次）
    4. 页面自动按REFRESH_INTERVAL刷新数据

注意事项：
    - 不支持实时AI分析请求（由后台自动处理）
    - K线图的更新频率受REFRESH_INTERVAL限制
    - 所有敏感API调用都应捕获异常，用户友好地显示错误

模块依赖：
    - streamlit: Web应用框架
    - plotly: 交互式图表
    - utils: BinanceAPI客户端和AI分析器
    - database: SQLite数据库操作
    - config: 环境变量和全局配置

作者：Your Name
版本：3.0
最后更新：2026-02-20
"""

import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils import api_client, deepseek_analyzer
from database import cache
from config import TITLE, KLINE_INTERVAL, REFRESH_INTERVAL
import pytz
import time
import json

if 'ai_fail_count' not in st.session_state:
    st.session_state.ai_fail_count = 0
if 'last_fail_time' not in st.session_state:
    st.session_state.last_fail_time = None

# 页面配置
from config import SERVER_PORT, SERVER_ADDRESS, TITLE
st.set_page_config(
    page_title=TITLE,
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS样式
st.markdown("""
<style>
    .main { background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 100%); }
    body { color: #fff; font-family: 'Segoe UI', sans-serif; }
    .title-section {
        background: linear-gradient(90deg, #1f77b4 0%, #2ca02c 100%);
        padding: 2rem; border-radius: 1rem; margin-bottom: 2rem;box-shadow: 0 10px 30px rgba(31, 119, 180, 0.4);
    }
    .title-section h1 { color: white; font-size: 2.5em; font-weight: 900; margin: 0; }
    .metric-card {
        background: linear-gradient(135deg, rgba(31, 119, 180, 0.15) 0%, rgba(44, 160, 44, 0.05) 100%);
        padding: 1.5rem; border-radius: 1rem;
        border: 1px solid rgba(31, 119, 180, 0.3);
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
    }
    .metric-card:hover { transform: translateY(-5px); box-shadow: 0 15px 40px rgba(31, 119, 180, 0.5); }
    .big-number { font-size: 2.5em; font-weight: 900; margin: 0.5rem 0; }
    .metric-label { font-size: 0.85em; color: #aaa; text-transform: uppercase; letter-spacing: 1px; }
    .profit .big-number { color: #2ca02c; }
    .loss .big-number { color: #d62728; }
    .key-metric-box {
        background: linear-gradient(135deg, #1f77b4 0%, #0d47a1 100%);
        padding: 2rem; border-radius: 1rem; color: white; margin: 2rem 0;
        box-shadow: 0 10px 30px rgba(31, 119, 180, 0.4);
    }
    .key-metric-box.profit { background: linear-gradient(135deg, #2ca02c 0%, #1a6b1a 100%); }
    .key-metric-box.loss { background: linear-gradient(135deg, #d62728 0%, #8b1a1a 100%); }
    .key-metric-label { font-size: 1em; color: rgba(255,255,255,0.9); text-transform: uppercase; }
    .key-metric-value { font-size: 3em; font-weight: 900; }
    .divider { height: 1px; background: linear-gradient(90deg, transparent, rgba(31, 119, 180, 0.3), transparent); margin: 2rem 0; }
    .status-bar {
        display: flex; justify-content: space-between; padding: 1rem;
        background: rgba(31, 119, 180, 0.1); border-radius: 0.5rem; margin-bottom: 1.5rem;
    }
    .status-text { color: #aaa; font-size: 0.9em; }
    .status-time { color: #2ca02c; font-weight: 700; }
</style>
""", unsafe_allow_html=True)


def load_kline_data(symbol: str, interval: str = '1h', limit: int = 100, quiet: bool = False):
    """
    从币安API加载K线数据并转换为标准格式。
    
    此函数是K线数据获取的核心，与币安API通信获取历史收盘数据。
    数据经过验证和格式化后用于画图和分析。
    
    参数：
        symbol (str): 交易对代码，如"BTCUSDT"或"ETHUSDT"
        interval (str): K线时间框架。支持值：
                       '1m','5m','15m','30m','1h','2h','4h','6h','8h','12h','1d','3d','1w','1M'
                       默认值: '1h'（1小时）
        limit (int): 要获取的K线数量，范围1-1500
                    默认值: 100
        quiet (bool): 是否禁用错误输出（用于后台静默加载）
                     默认值: False
    
    返回值：
        list: 格式化后的K线数据列表，每条包含以下字段：
              {
                  'open_time': datetime - K线开始时间 (UTC)
                  'open': float - 开盘价
                  'high': float - 最高价
                  'low': float - 最低价
                  'close': float - 收盘价
                  'volume': float - 成交量
              }
        None: 如果数据获取失败或数据为空
    
    异常处理：
        - API连接失败：返回None，打印错误信息（quiet=False时）
        - 数据验证失败：返回None
    
    使用示例：
        >>> klines = load_kline_data('BTCUSDT', '1h', 100)
        >>> if klines:
        ...     for k in klines:
        ...         print(f"{k['open_time']}: O={k['open']} H={k['high']}")
    
    性能考虑：
        - API配额有限，避免频繁调用（建议 REFRESH_INTERVAL >= 2秒）
        - limit越小，响应越快
        - 此函数应与fetch_kline_parallel()配合使用以获得性能优势
    """
    try:
        klines = api_client.get_klines(symbol, interval, limit)
        if not klines:
            return None
        # 添加数据验证
        if len(klines) == 0:
            return None
        return [{
            'open_time': datetime.fromtimestamp(int(k[0]) / 1000, tz=pytz.UTC),
            'open': float(k[1]), 'high': float(k[2]), 'low': float(k[3]),
            'close': float(k[4]), 'volume': float(k[7])
        } for k in klines]
    except (ValueError, IndexError, TypeError) as e:
        if not quiet:
            st.error(f"❌ K线数据解析失败 ({symbol}): {e}")
        return None
    except Exception as e:
        if not quiet:
            st.error(f"❌ K线数据加载失败 ({symbol}): {e}")
        return None


def fetch_kline_parallel(symbols, interval: str = '1h', limit: int = 100):
    """并行获取多个交易对的K线数据
    
    使用ThreadPoolExecutor并行请求多个K线数据，显著提升性能。
    每个请求在独立线程执行，不阻塞UI。
    
    参数：
        symbols (list): 交易对代码列表，如 ['BTCUSDT', 'ETHUSDT']
        interval (str): K线时间框架，默认值 '1h'  
        limit (int): 每个交易对获取的K线数量，范围1-1500，默认100
    
    返回值：
        dict: 格式为 {symbol: kline_data_list}，失败的交易对映射为 None
    """
    results = {}
    if not symbols:
        return results
    max_workers = min(8, len(symbols))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(load_kline_data, symbol, interval, limit, True): symbol
            for symbol in symbols
        }
        for future in as_completed(future_map):
            symbol = future_map[future]
            try:
                data = future.result()
                if data:
                    results[symbol] = data
            except Exception as e:
                # 静默失败，后续显示错误
                results[symbol] = None
    return results


def plot_candlestick(symbol: str, data_list: list):
    """绘制交互式K线蜡烛图
    
    使用Plotly库生成高质量的K线图表，支持缩放、平移等交互功能。
    
    参数：
        symbol (str): 交易对代码，如 'BTCUSDT'（用于图表标题）
        data_list (list): K线数据列表，每个元素含open/high/low/close/volume字段
    
    返回值：
        plotly.graph_objects.Figure: 可交互的K线图Figure对象
        None: 如果data_list为空或无有效数据
    """
    if not data_list:
        return None
    fig = go.Figure(data=[go.Candlestick(
        x=[d['open_time'] for d in data_list],
        open=[d['open'] for d in data_list],
        high=[d['high'] for d in data_list],
        low=[d['low'] for d in data_list],
        close=[d['close'] for d in data_list],
        name=symbol,
        increasing_line_color='#d62728',  # 红色表示上涨
        decreasing_line_color='#2ca02c'   # 绿色表示下跌
    )])
    fig.update_layout(
        title=f"{symbol} K线图({KLINE_INTERVAL})",
        yaxis_title="价格 (USD)", xaxis_title="时间",
        template="plotly_dark", height=400,
        margin=dict(l=40, r=40, t=50, b=40),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0.2)'
    )
    return fig


def display_position_card(position: dict):
    """显示单个持仓卡片
    
    用HTML美化的卡片形式显示一个交易对的完整持仓信息。
    
    参数：
        position (dict): 持仓息字典，需包含symbol/side等字段
    
    返回值：无（直接使用st.markdown显示）
    """
    symbol, side = position['symbol'], position['side']
    entry_price, mark_price = position['entry_price'], position['mark_price']
    unrealized_profit, roi = position['unrealized_profit'], position['roi']
    leverage = position['leverage']
    
    price_change = ((mark_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
    # 调换颜色：绿色下跌，红色上涨
    color = '#d62728' if price_change >= 0 else '#2ca02c'
    
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown(f"### {symbol}")
        # 调换颜色：LONG红色，SHORT绿色
        badge_color = '#d62728' if side == 'LONG' else '#2ca02c'
        st.markdown(f"<span style='background:rgba({badge_color},0.2);color:{badge_color};padding:0.3rem 0.8rem;border-radius:0.3rem;border:1px solid {badge_color};'>{side} | {leverage}x</span>", unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("开仓价", f"${entry_price:.2f}")
    c2.metric("当前价", f"${mark_price:.2f}")
    c3.markdown(f"<div style='text-align:center'><small style='color:#888'>价格变化</small><br><span style='font-size:1.4em;color:{color}'>{price_change:+.2f}%</span></div>", unsafe_allow_html=True)
    c4.metric("数量", f"{position['amount']:.6f}".rstrip('0').rstrip('.'))
    
    c1, c2, c3, c4 = st.columns(4)
    # 调换颜色：盈利红色，亏损绿色
    profit_color = '#d62728' if unrealized_profit >= 0 else '#2ca02c'
    c1.markdown(f"<div style='text-align:center'><small style='color:#888'>未实现盈亏</small><br><span style='font-size:1.4em;color:{profit_color}'>${unrealized_profit:+,.2f}</span></div>", unsafe_allow_html=True)
    c2.markdown(f"<div style='text-align:center'><small style='color:#888'>ROI</small><br><span style='font-size:1.4em;color:{profit_color}'>{roi:+.2f}%</span></div>", unsafe_allow_html=True)
    liq = position.get('liquidation_price', 0)
    c3.metric("强平价", f"${liq:.2f}" if liq > 0 else "N/A")
    c4.metric("杠杆", f"{leverage}x")
    
    st.divider()
    kline_data = load_kline_data(symbol, KLINE_INTERVAL, 100)
    if kline_data:
        fig = plot_candlestick(symbol, kline_data)
        if fig:
            st.plotly_chart(fig, use_container_width=True)


def get_symbol_price_info(symbol: str, kline_data: list) -> dict:
    """获取单个货币的价格信息"""
    if not kline_data or len(kline_data) == 0:
        return None
    
    try:
        latest = kline_data[-1]
        previous = kline_data[-2] if len(kline_data) > 1 else kline_data[-1]
        
        current_price = latest['close']
        high_24h = max([k['high'] for k in kline_data])
        low_24h = min([k['low'] for k in kline_data])
        price_change_24h = ((current_price - previous['close']) / previous['close'] * 100) if previous['close'] > 0 else 0
        
        return {
            'current_price': round(current_price, 2),
            'high_24h': round(high_24h, 2),
            'low_24h': round(low_24h, 2),
            'price_change_24h': round(price_change_24h, 2)
        }
    except Exception as e:
        print(f"❌ 获取价格信息失败 ({symbol}): {e}")
        return None


def prefetch_ai_analysis(symbols: list, kline_map: dict):
    """并行预取多个交易对的AI分析并写入缓存"""
    if not symbols or not kline_map:
        return
    max_workers = min(5, len(symbols))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for symbol in symbols:
            kline_data = kline_map.get(symbol)
            if not kline_data:
                continue
            futures[executor.submit(_fetch_and_cache_ai, symbol, kline_data)] = symbol
        # 等待完成
        for future in as_completed(futures):
            _ = future.result()


def _fetch_and_cache_ai(symbol: str, kline_data: list):
    """后台任务：使用后台管理器获取和验证AI分析"""
    from utils import background_manager
    return background_manager.fetch_and_store_analysis(api_client, deepseek_analyzer, symbol, kline_data, cache)


def prefetch_ai_analysis_background(symbols: list, kline_map: dict):
    """后台定时任务：每5分钟更新所有币种的AI分析"""
    max_workers = min(5, len(symbols))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for symbol in symbols:
            kline_data = kline_map.get(symbol)
            if not kline_data:
                continue
            futures[executor.submit(_fetch_and_cache_ai, symbol, kline_data)] = symbol
        # 等待完成
        for future in as_completed(futures):
            try:
                _ = future.result()
            except:
                pass


def display_symbol_ai_analysis(symbol: str):
    """显示单个货币的最近AI分析（前端只显示，不请求）"""
    try:
        # 获取最近的有效分析（后端已完成JSON验证和重试）
        cached_analysis = cache.get_analysis(symbol)
        
        if not cached_analysis:
            st.info("📝 正在获取AI分析中... (后台每5分钟更新一次)")
            return
        
        # 显示分析结果（已验证的JSON）
        remaining_time = cached_analysis.get('_cache_remaining_time', 0)
        st.markdown(f"#### 🤖 AI分析建议 (缓存有效: {remaining_time:.0f}秒)")
        
        # 直接显示已解析的数据（后端已完成JSON验证）
        parsed_data = cached_analysis.get('parsed_data')
        analysis_text = cached_analysis.get('analysis_text', '')
        
        if parsed_data:
            display_analysis_result(parsed_data)
        else:
            # 后端验证失败，尝试在前端解析（fallback）
            if analysis_text:
                display_analysis_result_text(analysis_text)
            else:
                st.error("⚠️ 无法获取有效的AI分析")
    except Exception as e:
        st.error(f"❌ 显示AI分析失败: {str(e)}")


def display_analysis_result(parsed_data: dict):
    """显示已验证的分析结果（后端已完成JSON验证）"""
    try:
        if not isinstance(parsed_data, dict):
            st.error("⚠️ 分析数据格式错误")
            return
        
        # 获取入场建议
        entry = parsed_data.get('是否应该入场', '未提供')
        if isinstance(entry, bool):
            entry_text = '✅ 入场' if entry else '❌ 不入场'
        elif entry in ['是', 'Yes', 'YES', 'true', 'True']:
            entry_text = '✅ 入场'
        else:
            entry_text = '❌ 不入场'
        
        # 设置背景色
        bg_color = '#2ca02c' if '✅' in entry_text else '#d62728'
        
        st.markdown(f"""
        <div style="background-color: {bg_color}; color: #ffffff; padding: 1.5rem; border-radius: 1rem; text-align: center; margin: 1rem 0; box-shadow: 0 5px 15px rgba(0,0,0,0.3);">
            <h3 style="margin: 0; font-size: 1.8em; font-weight: bold;">{entry_text}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # 显示关键信息
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**交易方向:** {parsed_data.get('做多还是做空', '未提供')}")
            st.markdown(f"**仓位建议:** {parsed_data.get('重仓还是轻仓', '未提供')}")
        with col2:
            st.markdown(f"**入场价:** {parsed_data.get('目标入场价', parsed_data.get('开仓价', '未提供'))}")
            st.markdown(f"**止损价:** {parsed_data.get('止损价', '未提供')}")
        
        st.markdown(f"**风险收益比:** {parsed_data.get('风险和利润比值', '未提供')}")
        
        # 显示压力位与支撑位
        col_r, col_s = st.columns(2)
        with col_r:
            st.metric("💹 上方阻力", parsed_data.get('上方压力位', '未提供'))
        with col_s:
            st.metric("💧 下方支撑", parsed_data.get('下方支撑位', '未提供'))
        
        # 显示分析理由
        reason = parsed_data.get('分析理由', '')
        if reason:
            with st.expander("📝 详细分析"):
                st.markdown(reason)
        
        # 显示风险提示
        risk = parsed_data.get('风险提示', '')
        if risk:
            with st.expander("⚠️ 风险提示"):
                st.markdown(risk)
    
    except Exception as e:
        st.error(f"❌ 显示分析失败: {e}")


def display_analysis_result_text(analysis_text: str):
    """降级方案：从原始文本解析JSON（后端验证失败时使用）"""
    try:
        from utils import background_manager
        parsed = background_manager.validate_and_parse_json(analysis_text)
        if parsed:
            display_analysis_result(parsed)
        else:
            st.error("⚠️ AI返回的JSON格式无效，无法解析")
            st.code(analysis_text[:500], language="json")
    except Exception as e:
        st.error(f"❌ 解析失败: {e}")


def detect_mobile():
    """检测是否为移动设备"""
    try:
        if 'screen_width' not in st.session_state:
            st.session_state.screen_width = 1200
        return st.session_state.screen_width < 768
    except:
        return False


def display_ai_summary():
    """显示今日AI分析摘要（基于币安数据进行分析）"""
    try:
        st.markdown("### 📋 今日AI分析摘要")
        symbols = cache.get_distinct_symbols()
        
        col1, col2 = st.columns(2)
        with col1:
            # 左侧：AI分析统计
            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                hist_count = len(cache.get_history_list(None, limit=1000))
                st.metric("📊 总分析数", hist_count, "条")
            with col_b:
                st.metric("🔷 覆盖币种", len(symbols) if symbols else 0, "种")
            with col_c:
                try:
                    win_rate_all = cache.get_win_rate(None, limit=100)
                    st.metric("📈 胜率", f"{win_rate_all.get('win_rate', 0):.1f}%", f"{win_rate_all.get('wins', 0)}胜")
                except:
                    st.metric("📈 胜率", "N/A", "")
            with col_d:
                try:
                    avg_pnl = cache.get_win_rate(None, limit=100).get('avg_pnl', 0)
                    st.metric("💰 平均盈亏", f"{avg_pnl:+.2f}", "USD")
                except:
                    st.metric("💰 平均盈亏", "N/A", "")
        
        with col2:
            # 右侧：币安数据分析
            st.markdown("#### 🔍 市场数据分析（7天）")
            try:
                # 获取所有币种的7天平均数据
                volatility_data = []
                for sym in (symbols or [])[:10]:  # 最多分析10个币种
                    analytics = cache.get_binance_analytics(sym, days=7)
                    if analytics and 'price_volatility' in analytics:
                        volatility_data.append({
                            '币种': sym,
                            '波动率': f"{analytics['price_volatility']:.2f}%",
                            '平均价格': f"${analytics.get('avg_price', 0):.2f}",
                            '资金费率': f"{analytics.get('avg_funding_rate', 0)*100:.4f}%"
                        })
                
                if volatility_data:
                    st.dataframe(volatility_data, hide_index=True, use_container_width=True)
                else:
                    st.info("📭 暂无充足的市场数据（需要至少有K线数据）")
            except Exception as e:
                st.info(f"📝 市场分析数据生成中... ({e})")
        
        st.divider()
    except Exception as e:
        st.warning(f"⚠️ 摘要展示出错: {e}")


def show_history_panel():
    """显示历史记录面板，支持标记命中/盈亏和胜率分析"""
    try:
        st.markdown("### 📜 历史命中率分析")
        symbols = cache.get_distinct_symbols()
        if not symbols:
            st.info("📭 暂无历史记录")
            return
        
        # 显示整体胜率统计
        st.markdown("#### 📊 整体胜率统计")
        col1, col2, col3, col4, col5 = st.columns(5)
        try:
            all_stats = cache.get_win_rate(None, limit=None)  # 全部记录
            with col1:
                st.metric("📈 总分析数", all_stats.get('total', 0), "条")
            with col2:
                st.metric("✅ 命中", all_stats.get('wins', 0), f"{all_stats.get('win_rate', 0):.1f}%")
            with col3:
                st.metric("❌ 失误", all_stats.get('losses', 0), f"{100-all_stats.get('win_rate', 0):.1f}%")
            with col4:
                avg_pnl = all_stats.get('avg_pnl', 0)
                st.metric("💰 平均盈亏", f"{avg_pnl:+.2f}",  "USD")
            with col5:
                # 整体效益指标
                total_wins_pnl = sum([r.get('pnl', 0) for r in cache.get_history_list(None, limit=1000) if r.get('hit') == 1 and r.get('pnl')]) if all_stats['wins'] > 0 else 0
                st.metric("🎯 胜率效益", f"{all_stats.get('win_rate', 0)*2:.1f}" if all_stats.get('win_rate', 0) >= 50 else f"{all_stats.get('win_rate', 0):.1f}", "")
        except:
            st.info("📝 统计数据生成中...")
        
        st.divider()
    except Exception as e:
        st.warning(f"⚠️ 历史面板出错: {e}")


def main():
    """主函数"""
    if 'ai_analysis_cache' not in st.session_state:
        st.session_state.ai_analysis_cache = None
        st.session_state.page_load_time = time.time()
    
    # 检测移动端
    is_mobile = detect_mobile()
    if is_mobile:
        st.markdown("<style>.main { max-width: 100%; } .block-container { max-width: 100% !important; padding: 0.5rem; }</style>", unsafe_allow_html=True)
    
    # 检查AI失败告警
    if st.session_state.ai_fail_count >= 2:
        if st.session_state.last_fail_time and (datetime.now() - st.session_state.last_fail_time) < timedelta(minutes=5):
            st.warning(f"⚠️ AI分析连续失败 {st.session_state.ai_fail_count} 次（最后尝试：{st.session_state.last_fail_time.strftime('%H:%M:%S')}），已降级显示历史记录")
    
    st.markdown(f'<div class="title-section"><h1>📊 {TITLE}</h1></div>', unsafe_allow_html=True)
    
    with st.spinner("🔄 加载数据..."):
        data = api_client.get_open_positions()
    
    if data is None:
        st.error("❌ 无法连接到币安API")
        return
    
    positions = data['positions']
    equity = data['equity']
    timestamp = data['timestamp']
    tz = pytz.timezone('Asia/Shanghai')
    local_time = timestamp.astimezone(tz)
    st.markdown(f'<div class="status-bar"><span class="status-text">🏢 币安期货</span><span class="status-text">更新:<span class="status-time">{local_time.strftime("%H:%M:%S")}</span></span></div>', unsafe_allow_html=True)
    
    st.markdown("### 💼 账户概览")
    total_balance = equity['total_wallet_balance']
    total_profit = equity['total_unrealized_profit']
    margin_balance = equity['total_margin_balance']
    available = equity['available_balance']
    total_roi = (total_profit / total_balance * 100) if total_balance > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f'<div class="metric-card"><div class="metric-label">钱包余额</div><div class="big-number">${total_balance:,.2f}</div></div>', unsafe_allow_html=True)
    col2.markdown(f'<div class="metric-card"><div class="metric-label">保证金余额</div><div class="big-number">${margin_balance:,.2f}</div></div>', unsafe_allow_html=True)
    col3.markdown(f'<div class="metric-card"><div class="metric-label">可用余额</div><div class="big-number">${available:,.2f}</div></div>', unsafe_allow_html=True)
    col4.markdown(f'<div class="metric-card {"profit" if total_profit >= 0 else "loss"}"><div class="metric-label">未实现盈亏</div><div class="big-number">${total_profit:+,.2f}</div></div>', unsafe_allow_html=True)
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="key-metric-box {"profit" if total_roi >= 0 else "loss"}"><div class="key-metric-label">📈 总回报率</div><div class="key-metric-value">{total_roi:+.2f}%</div><div style="margin-top:0.5rem;opacity:0.8">盈亏: ${total_profit:+,.2f} | 总资产: ${total_balance:,.2f}</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    st.markdown(f"### 📍仓位监控 ({len(positions)} 个)")
    if positions:
        st.dataframe([{
            '交易对': p['symbol'], '方向': p['side'],
            '数量': f"{p['amount']:.6f}".rstrip('0').rstrip('.'),
            '开仓价': f"${p['entry_price']:.2f}",
            '当前价': f"${p['mark_price']:.2f}",
            'ROI': f"{p['roi']:+.2f}%",
            '盈亏': f"${p['unrealized_profit']:+,.2f}"
        } for p in positions], hide_index=True)
        
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown("#### 📋 仓位详情")
        
        tabs = st.tabs([f"{p['symbol']} ({p['side']})" for p in positions])
        for tab, pos in zip(tabs, positions):
            with tab:
                display_position_card(pos)
    else:
        st.info("📭 当前没有开仓头寸")
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        st.markdown("#### 📊 主流货币K线图")
        
        # 并行加载主流货币K线数据
        mainstream_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'DODOUSDT', 'ZECUSDT']
        with st.spinner("🚀 并发加载主流货币K线与AI分析..."):
            kline_map = fetch_kline_parallel(mainstream_symbols, KLINE_INTERVAL, 100)
            # 启动后台AI分析任务（5分钟循环）
            prefetch_ai_analysis_background(mainstream_symbols, kline_map)

        tabs = st.tabs(mainstream_symbols)
        for tab, symbol in zip(tabs, mainstream_symbols):
            with tab:
                kline_data = kline_map.get(symbol)
                if kline_data and len(kline_data) > 0:
                    current_price = kline_data[-1]['close']
                    open_price = kline_data[-1]['open']
                    price_change = ((current_price - open_price) / open_price * 100) if open_price > 0 else 0
                    change_color = '#d62728' if price_change >= 0 else '#2ca02c'
                    high_price = kline_data[-1]['high']
                    low_price = kline_data[-1]['low']
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("当前价格", f"${current_price:.2f}")
                    col2.markdown(f"<div style='text-align:center'><small style='color:#888'>当前涨跌</small><br><span style='font-size:1.4em;color:{change_color}'>{price_change:+.2f}%</span></div>", unsafe_allow_html=True)
                    col3.metric("最高价", f"${high_price:.2f}")
                    col4.metric("最低价", f"${low_price:.2f}")
                    
                    fig = plot_candlestick(symbol, kline_data)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                    
                    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
                    display_symbol_ai_analysis(symbol)
                else:
                    st.error(f"❌ 无法加载 {symbol} K线数据")
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown("### 🤖 AI 交易分析")
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄刷新分析", type="primary"):
            st.session_state.ai_analysis_cache = None
            st.session_state.page_load_time = 0  # 强制重新分析
            st.rerun()
    
    current_time = time.time()
    is_first_load = (current_time - st.session_state.page_load_time) < 2
    
    if st.session_state.ai_analysis_cache is None and is_first_load:
        trading_summary = f"账户:余额${total_balance:.2f},盈亏${total_profit:+,.2f},ROI{total_roi:+.2f}%\n仓位({len(positions)}个):"
        for p in positions:
            trading_summary += f"\n- {p['symbol']} {p['side']}开仓${p['entry_price']:.2f} 现价${p['mark_price']:.2f} ROI{p['roi']:+.2f}%"
        
        with st.spinner("🤖 AI分析中..."):
            analysis = ""
            error_occurred = False
            try:
                for chunk in deepseek_analyzer.analyze_trading_data_stream(trading_summary):
                    if chunk.get('success') and chunk.get('content'):
                        analysis += chunk['content']
                    elif not chunk.get('success'):
                        error_occurred = True
                        error_msg = chunk.get('error', '未知错误')
                        st.error(f"❌ AI分析失败: {error_msg}")
                        break
                
                if not error_occurred and analysis:
                    st.session_state.ai_analysis_cache = analysis
                elif not error_occurred and not analysis:
                    st.session_state.ai_analysis_cache = "error_empty"
                    st.warning("⚠️ AI未返回任何分析内容，请检查DeepSeek API配置或点击「刷新分析」重试")
                else:
                    st.session_state.ai_analysis_cache = "error_api"
            except Exception as e:
                st.error(f"❌ AI分析异常: {e}")
                st.session_state.ai_analysis_cache = f"error: {e}"
    
    if st.session_state.ai_analysis_cache:
        # 检查是否是错误状态
        if st.session_state.ai_analysis_cache.startswith("error"):
            st.warning("⚠️ AI分析未完成或出现错误，请点击「刷新分析」重试")
        else:
            display_ai_analysis(st.session_state.ai_analysis_cache)
    
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    display_ai_summary()
    show_history_panel()
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 手动刷新"):
            st.rerun()
    
    import streamlit.components.v1 as components
    components.html('<script>setTimeout(()=>location.reload(),5000)</script>', height=0)


if __name__ == "__main__":
    main()
