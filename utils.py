import hmac
import hashlib
import requests
import json
from datetime import datetime
import time
from config import API_KEY, API_SECRET, BINANCE_API_URL, KLINE_INTERVAL
from urllib.parse import urlencode

class BinanceAPI:
    """币安期货API调用接口"""
    
    def __init__(self, api_key, api_secret, base_url):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": api_key})
    
    def _sign_request(self, params):
        """签署请求"""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        params['signature'] = signature
        return params
    
    def _request(self, method, endpoint, params=None, signed=True):
        """发送请求"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if signed:
                params = params or {}
                params['timestamp'] = int(time.time() * 1000)
                params = self._sign_request(params)
            
            # 直接使用本地网络连接，不使用代理
            if method == 'GET':
                response = self.session.get(url, params=params, timeout=15)
            elif method == 'POST':
                response = self.session.post(url, params=params, timeout=15)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API错误: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.ConnectTimeout:
            print("❌ 连接超时: 无法连接到币安服务器，请检查网络连接")
            return None
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            return None
    
    def get_account_info(self):
        """获取账户信息"""
        return self._request('GET', '/fapi/v2/account')
    
    def get_all_orders(self, symbol):
        """获取所有订单"""
        params = {'symbol': symbol}
        return self._request('GET', '/fapi/v1/allOrders', params)
    
    def get_klines(self, symbol, interval, limit=100):
        """获取K线数据"""
        try:
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            result = self._request('GET', '/fapi/v1/klines', params, signed=False)
            # 验证返回的数据
            if result and isinstance(result, list) and len(result) > 0:
                return result
            return None
        except Exception as e:
            print(f"❌ 获取K线数据失败 ({symbol}): {e}")
            return None
    
    def get_funding_rate(self, symbol: str = None) -> dict:
        """获取资金费率"""
        try:
            params = {}
            if symbol:
                params['symbol'] = symbol
            result = self._request('GET', '/fapi/v1/premiumIndex', params, signed=False)
            if result:
                if isinstance(result, list):
                    return {r['symbol']: {'rate': float(r.get('lastFundingRate', 0)),
                            'next_time': int(r.get('nextFundingTime', 0))}
                            for r in result if 'symbol' in r}
                elif isinstance(result, dict):
                    return {result['symbol']: {'rate': float(result.get('lastFundingRate', 0)),
                            'next_time': int(result.get('nextFundingTime', 0))}}
            return {}
        except Exception as e:
            print(f"❌ 获取资金费率失败: {e}")
            return {}

    def get_mark_price(self, symbol=None):
        """获取标记价格"""
        params = {}
        if symbol:
            params['symbol'] = symbol
        return self._request('GET', '/fapi/v1/markPrice', params, signed=False)
    
    def get_open_positions(self):
        """获取开仓头寸"""
        equity = {}
        account_info = self.get_account_info()
        
        if not account_info:
            print("❌ 获取账户信息失败")
            return None
        
        try:
            positions = []
            mark_prices = {}
            
            # 获取所有标记价格以加快速度
            all_marks = self._request('GET', '/fapi/v1/markPrice', signed=False)
            if all_marks:
                if isinstance(all_marks, list):
                    for mark in all_marks:
                        if 'symbol' in mark and 'markPrice' in mark:
                            try:
                                mark_prices[mark['symbol']] = float(mark['markPrice'])
                            except (ValueError, TypeError):
                                continue
                else:
                    if 'symbol' in all_marks and 'markPrice' in all_marks:
                        try:
                            mark_prices[all_marks['symbol']] = float(all_marks['markPrice'])
                        except (ValueError, TypeError):
                            pass
            
            # 提取余额和头寸信息
            try:
                total_wallet_balance = float(account_info.get('totalWalletBalance', 0))
                total_unrealized_profit = float(account_info.get('totalUnrealizedProfit', 0))
                
                equity['total_wallet_balance'] = total_wallet_balance
                equity['total_unrealized_profit'] = total_unrealized_profit
                equity['total_margin_balance'] = float(account_info.get('totalMarginBalance', 0))
                equity['available_balance'] = float(account_info.get('availableBalance', 0))
            except (ValueError, TypeError) as e:
                print(f"❌ 解析账户余额数据失败: {e}")
                return None
            
            # 获取杠杆信息
            for position in account_info.get('positions', []):
                try:
                    position_amt = float(position.get('positionAmt', 0))
                    if position_amt != 0:
                        symbol = position.get('symbol', 'UNKNOWN')
                        entry_price = float(position.get('entryPrice', 0))
                        mark_price = mark_prices.get(symbol, entry_price)
                        # 计算盈亏
                        if position_amt > 0:  # 多单
                            unrealized_profit = position_amt * (mark_price - entry_price)
                            side = 'LONG'
                        else:  # 空单
                            unrealized_profit = abs(position_amt) * (entry_price - mark_price)
                            side = 'SHORT'

                        roi = (float(position.get('unrealizedProfit', 0)) / (abs(position_amt) * entry_price) * 100) if (abs(position_amt) * entry_price) > 0 else 0

                        position_info = {
                            'symbol': symbol,
                            'side': side,
                            'amount': abs(position_amt),
                            'entry_price': entry_price,
                            'mark_price': mark_price,
                            'unrealized_profit': float(position.get('unrealizedProfit', 0)),
                            'roi': roi,
                            'leverage': int(position.get('leverage', 1)),
                            'liquidation_price': float(position.get('liquidationPrice', 0)),
                            'margin_type': position.get('marginType', 'CROSSED'),
                            'isolated_wallet': float(position.get('isolatedWallet', 0)),
                            'position_side': position.get('positionSide', 'BOTH'),
                            'initial_margin': float(position.get('initialMargin', 0)),
                            'maint_margin': float(position.get('maintMargin', 0))
                        }

                        positions.append(position_info)
                except (ValueError, TypeError, KeyError) as e:
                    print(f"⚠️ 跳过无效头寸数据: {e}")
                    continue
            
            # 按symbol排序
            positions.sort(key=lambda x: x['symbol'])
            
            return {
                'positions': positions,
                'equity': equity,
                'timestamp': datetime.now()
            }
        
        except Exception as e:
            print(f"❌ 处理头寸信息时出错: {str(e)}")
            return None


def format_number(num, decimals=2):
    """格式化数字"""
    if isinstance(num, (int, float)):
        return f"{num:,.{decimals}f}"
    return str(num)


def get_price_change_color(value):
    """根据涨跌返回颜色"""
    if value > 0:
        return "green"
    elif value < 0:
        return "red"
    else:
        return "gray"


def calculate_roi_color(roi):
    """根据ROI返回颜色"""
    if roi > 5:
        return "darkgreen"
    elif roi > 0:
        return "green"
    elif roi > -5:
        return "orange"
    else:
        return "red"


# 初始化API客户端
api_client = BinanceAPI(API_KEY, API_SECRET, BINANCE_API_URL)


# ==================== DeepSeek AI 分析 ====================
class DeepSeekAnalyzer:
    """DeepSeek AI 分析交易数据"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com/chat/completions"
        self.model = "deepseek-reasoner"

    def analyze_symbol(self, symbol: str, price_info: dict, funding_rate: float = None, win_stats: dict = None):
        """分析单个货币，返回完整的分析文本"""
        try:
            json_template = """{
  "交易对": "%s",
  "是否应该入场": "是/否",
  "做多还是做空": "做多/做空/观望",
  "重仓还是轻仓": "重仓/轻仓/不建议入场",
  "目标入场价": "具体数字",
  "止损价": "具体数字",
  "止盈价": "具体数字",
  "上方压力位": "具体数字",
  "下方支撑位": "具体数字",
  "风险和利润比值": "1:2 或具体比例",
  "分析理由": "详细分析理由（技术面、基本面等）",
  "风险提示": "具体风险说明",
  "分析时间(UTC+8)": "北京时间，格式YYYY-MM-DD HH:MM"
}""" % symbol

            # 构建额外上下文
            extra_ctx = ""
            if funding_rate is not None:
                fr_pct = funding_rate * 100
                extra_ctx += f"当前资金费率: {fr_pct:+.4f}%（正=多头付费空头，负=空头付费多头）\n"
            if win_stats and win_stats.get('total', 0) > 0:
                extra_ctx += (f"历史AI建议胜率: {win_stats['win_rate']}% "
                              f"(近{win_stats['total']}条, 平均盈亏: {win_stats['avg_pnl']:+.2f})\n")

            prompt = (
                f"你是一位资深的加密货币交易分析师。请根据以下{symbol}的市场数据分析（时间请使用北京时间UTC+8）：\n\n"
                f"交易对: {symbol}\n"
                f"当前价格: ${price_info.get('current_price', 'N/A')}\n"
                f"24小时涨跌: {price_info.get('price_change_24h', 'N/A')}%\n"
                f"24小时最高: ${price_info.get('high_24h', 'N/A')}\n"
                f"24小时最低: ${price_info.get('low_24h', 'N/A')}\n"
                f"{extra_ctx}\n"
                "⚠️ 输出要求（必须遵守）：\n"
                "- 只输出一段纯JSON字符串，不能包含代码块标记、markdown、解释、前后缀、注释或额外文本\n"
                "- 键名必须与示例完全一致，值必须是可解析的字符串或数字，禁止返回 None/空字符串/未知\n"
                "- 所有价格字段必须是数字或可转为数字的字符串\n"
                "- 严禁返回中文全角引号或中文逗号，必须使用英文双引号和英文逗号\n\n"
                "严格按照以下JSON结构返回：\n\n"
                f"{json_template}\n\n"
                "⚠️ 警告：\n"
                "1. 所有字段都必须填写，不能为空\n"
                "2. 价格必须是具体数字，不能是\"None\"或\"未知\"\n"
                "3. 必须返回有效的JSON格式，不要有markdown代码块标记\n"
                "4. 理由和风险提示必须详细具体\n"
                "5. 只返回JSON，不要有任何其他文本\n\n"
                "请提供具体、可执行的建议。"
            )

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 3000,
                "temperature": 0.7,
                "stream": True
            }
            
            response = requests.post(self.base_url, json=payload, headers=headers, stream=True, timeout=60)
            
            if response.status_code == 200:
                # 流式返回，累积完整响应
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            if line.startswith(b'data: '):
                                line = line[6:]
                            if line == b'[DONE]':
                                break
                            
                            data = json.loads(line.decode('utf-8'))
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    full_response += delta['content']
                        except json.JSONDecodeError:
                            continue
                        except Exception:
                            continue
                
                return {
                    'success': True,
                    'data': full_response,
                    'symbol': symbol
                }
            else:
                return {
                    'success': False,
                    'error': f"API返回错误: {response.status_code}",
                    'symbol': symbol
                }
        except Exception as e:
            return {
                'success': False,
                'error': f"分析失败: {str(e)}",
                'symbol': symbol
            }
    
    def analyze_trading_data_stream(self, trading_summary: str):
        """使用DeepSeek流式分析交易数据"""
        try:
            stream_json_template = """{
  "建议交易的货币": "具体交易对名称如BTCUSDT",
  "是否应该入场": "是/否",
  "做多还是做空": "做多/做空/观望",
  "重仓还是轻仓": "重仓/轻仓/不建议入场",
  "开仓价": "具体数字",
  "止损价": "具体数字",
  "止盈价": "具体数字",
  "风险和利润比值": "1:2 或具体比例",
  "具体理由": "详细分析理由"
}"""

            prompt = (
                "你是一位资深的加密货币交易分析师。请根据以下实时交易数据分析：\n\n"
                f"{trading_summary}\n\n"
                "⚠️ 输出要求（必须遵守）：\n"
                "- 只输出一段纯JSON字符串，不能包含代码块标记、markdown、解释、前后缀、注释或额外文本\n"
                "- 键名必须与示例完全一致，值必须是可解析的字符串或数字，禁止返回 None/空字符串/未知\n"
                "- 所有价格字段必须是数字或可转为数字的字符串\n"
                "- 严禁返回中文全角引号或中文逗号，必须使用英文双引号和英文逗号\n\n"
                "严格按照以下JSON结构返回：\n\n"
                f"{stream_json_template}\n\n"
                "⚠️ 警告：\n"
                "1. 所有字段都必须填写，不能为空\n"
                "2. \"建议交易的货币\"必须写具体的交易对名称（如BTCUSDT、ETHUSDT等）\n"
                "3. 价格必须是具体数字，不能是\"None\"或\"未知\"\n"
                "4. 如果没有持仓，开仓价填写\"当前市场价\"\n"
                "5. 必须返回有效的JSON格式，不要有markdown代码块标记\n"
                "6. 理由必须详细具体，不能只写\"无\"\n\n"
                "请提供具体、可执行的建议。"
            )

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 4000,
                "temperature": 0.7,
                "stream": True
            }
            
            response = requests.post(self.base_url, json=payload, headers=headers, stream=True, timeout=60)
            
            if response.status_code == 200:
                # 流式返回
                for line in response.iter_lines():
                    if line:
                        try:
                            if line.startswith(b'data: '):
                                line = line[6:]
                            if line == b'[DONE]':
                                break
                            
                            data = json.loads(line.decode('utf-8'))
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    yield {
                                        'success': True,
                                        'content': delta['content']
                                    }
                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            yield {
                                'success': False,
                                'error': str(e)
                            }
            else:
                yield {
                    'success': False,
                    'error': f"API返回错误: {response.status_code}"
                }
        except Exception as e:
            yield {
                'success': False,
                'error': f"分析失败: {str(e)}"
            }


class BackgroundAnalysisManager:
    """后台AI分析管理器（后端负责所有复杂逻辑）"""
    
    def __init__(self):
        self.last_analysis_time = {}  # 记录每个币种最后一次有效分析的时间
        self.analysis_interval = 300  # 5分钟间隔（秒）
    
    def validate_and_parse_json(self, raw_text: str, max_retries: int = 2) -> dict:
        """验证和解析AI返回的JSON，包括重试机制"""
        if not raw_text:
            return None
        
        text = raw_text.strip()
        
        # 移除markdown代码块标记
        if text.startswith('```json'):
            text = text[7:]
        if text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        
        text = text.strip()
        
        # 找JSON内容
        json_start = text.find('{')
        json_end = text.rfind('}')
        
        if json_start == -1 or json_end == -1 or json_end <= json_start:
            return None
        
        json_str = text[json_start:json_end+1]
        
        # 尝试解析JSON
        try:
            data = json.loads(json_str)
            # 验证必需字段
            required_fields = ['交易对', '是否应该入场', '做多还是做空', '目标入场价', '止损价', '止盈价']
            for field in required_fields:
                if field not in data:
                    return None
            return data
        except json.JSONDecodeError:
            return None
    
    def should_update_analysis(self, symbol: str) -> bool:
        """检查是否应该更新该币种的分析（5分钟间隔检查）"""
        current_time = time.time()
        last_time = self.last_analysis_time.get(symbol, 0)
        return current_time - last_time >= self.analysis_interval
    
    def fetch_and_store_analysis(self, api_client, deepseek_analyzer, symbol: str, kline_data: list, cache) -> dict:
        """从API获取分析并存储（带JSON验证和重试）"""
        try:
            # 检查是否需要更新
            if not self.should_update_analysis(symbol):
                # 返回缓存的有效分析
                cached = cache.get_analysis(symbol)
                if cached:
                    return {'success': True, 'data': cached, 'from_cache': True}
                return None
            
            # 获取价格信息和基础数据
            price_info = self._get_symbol_price_info(symbol, kline_data)
            if not price_info:
                return None
            
            # 获取资金费率和胜率统计
            funding_rate_value = None
            try:
                funding_rate_dict = api_client.get_funding_rate(symbol)
                if funding_rate_dict and symbol in funding_rate_dict:
                    funding_rate_value = funding_rate_dict[symbol].get('rate', 0)
            except:
                pass
            
            try:
                win_stats = cache.get_win_rate(symbol, limit=30)
            except:
                win_stats = None
            
            # 保存币安数据（7天）
            try:
                cache.save_binance_data(symbol, kline_data, funding_rate_value)
            except:
                pass
            
            # 重试获取AI分析，直到得到有效JSON
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    # 调用AI分析
                    result = deepseek_analyzer.analyze_symbol(symbol, price_info, funding_rate=funding_rate_value, win_stats=win_stats)
                    
                    if not result or not result.get('success'):
                        continue
                    
                    analysis_text = result.get('data', '').strip()
                    if not analysis_text:
                        continue
                    
                    # 验证和解析JSON
                    parsed_data = self.validate_and_parse_json(analysis_text)
                    if parsed_data:
                        # 验证成功，保存到缓存
                        cache_data = {
                            'analysis_text': analysis_text,
                            'parsed_data': parsed_data,
                            'price_info': price_info,
                            'timestamp': time.time(),
                            'funding_rate': funding_rate_value
                        }
                        cache.set_analysis(symbol, cache_data)
                        self.last_analysis_time[symbol] = time.time()
                        return {'success': True, 'data': cache_data}
                    
                except Exception as e:
                    print(f"❌ 第{attempt+1}次尝试失败 ({symbol}): {e}")
                    continue
            
            # 所有重试都失败，返回空
            print(f"❌ 无法获取有效分析 ({symbol})，已重试{max_attempts}次")
            return None
        
        except Exception as e:
            print(f"❌ 后台分析失败 ({symbol}): {e}")
            return None
    
    def _get_symbol_price_info(self, symbol: str, kline_data: list) -> dict:
        """提取价格信息（从前端移到后端）"""
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


# 初始化全局对象
background_manager = BackgroundAnalysisManager()


# 初始化 DeepSeek 分析器
from config import DEEPSEEK_API_KEY
deepseek_analyzer = DeepSeekAnalyzer(DEEPSEEK_API_KEY)