import sqlite3
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

class AnalysisCache:
    """AI分析缓存数据库"""
    
    def __init__(self, db_path: str = "analysis_cache.db"):
        self.db_path = db_path
        self.ttl_seconds = 7 * 24 * 3600  # 7天缓存时效（604800秒）
        self.binance_ttl_seconds = 7 * 24 * 3600  # 币安数据保留7天
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS analysis_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT UNIQUE NOT NULL,
                        analysis_data TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol ON analysis_cache(symbol)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON analysis_cache(timestamp)')
                # 历史表：存储最近的分析记录用于回退/研究/命中率
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS analysis_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        analysis_data TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        hit INTEGER DEFAULT NULL,
                        pnl REAL DEFAULT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_hist_symbol ON analysis_history(symbol)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_hist_timestamp ON analysis_history(timestamp)')
                # 兼容：旧表无 hit/pnl 列时自动添加
                try:
                    cursor.execute('ALTER TABLE analysis_history ADD COLUMN hit INTEGER DEFAULT NULL')
                except sqlite3.OperationalError:
                    pass
                try:
                    cursor.execute('ALTER TABLE analysis_history ADD COLUMN pnl REAL DEFAULT NULL')
                except sqlite3.OperationalError:
                    pass
                # 币安API数据表（K线+资金费率，保留7天用于摘要分析）
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS binance_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        kline_data TEXT NOT NULL,
                        funding_rate REAL DEFAULT NULL,
                        timestamp REAL NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_bd_symbol ON binance_data(symbol)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_bd_timestamp ON binance_data(timestamp)')
                conn.commit()
        except Exception as e:
            print(f"❌ 数据库初始化失败: {e}")
    
    def set_analysis(self, symbol: str, analysis_data: dict) -> bool:
        """保存分析结果到缓存"""
        try:
            # 输入验证
            if not symbol or not isinstance(analysis_data, dict):
                print(f"❌ 无效的输入: symbol={symbol}, data_type={type(analysis_data)}")
                return False
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                timestamp = time.time()
                # 使用INSERT OR REPLACE实现插入或更新
                cursor.execute('''
                    INSERT OR REPLACE INTO analysis_cache 
                    (symbol, analysis_data, timestamp) 
                    VALUES (?, ?, ?)
                ''', (symbol, json.dumps(analysis_data, ensure_ascii=False), timestamp))

                # 写入历史表，便于回退和累计分析
                cursor.execute('''
                    INSERT INTO analysis_history (symbol, analysis_data, timestamp)
                    VALUES (?, ?, ?)
                ''', (symbol, json.dumps(analysis_data, ensure_ascii=False), timestamp))

                # 控制历史表体积，保留最近500条（要求至少100条，适度冗余）
                cursor.execute('''
                    DELETE FROM analysis_history
                    WHERE id NOT IN (
                        SELECT id FROM analysis_history
                        ORDER BY timestamp DESC
                        LIMIT 500
                    )
                ''')
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"❌ 数据库错误 ({symbol}): {e}")
            return False
        except (TypeError, ValueError) as e:
            print(f"❌ 数据序列化失败 ({symbol}): {e}")
            return False
        except Exception as e:
            print(f"❌ 保存分析结果失败 ({symbol}): {e}")
            return False
    
    def get_analysis(self, symbol: str) -> dict:
        """获取分析结果（检查缓存有效性）"""
        try:
            if not symbol:
                return None
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT analysis_data, timestamp FROM analysis_cache 
                    WHERE symbol = ?
                ''', (symbol,))
                result = cursor.fetchone()
                
                if not result:
                    return None
                
                analysis_data_str, timestamp = result
                current_time = time.time()
                
                # 检查缓存是否过期
                if current_time - timestamp > self.ttl_seconds:
                    # 缓存已过期，删除它
                    try:
                        cursor.execute('DELETE FROM analysis_cache WHERE symbol = ?', (symbol,))
                        conn.commit()
                    except Exception:
                        pass
                    return None
                
                try:
                    # 返回缓存数据和剩余时间
                    remaining_time = self.ttl_seconds - (current_time - timestamp)
                    analysis_data = json.loads(analysis_data_str)
                    analysis_data['_cache_remaining_time'] = remaining_time
                    return analysis_data
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"⚠️ 缓存数据损坏 ({symbol}): {e}")
                    # 删除损坏的数据
                    try:
                        cursor.execute('DELETE FROM analysis_cache WHERE symbol = ?', (symbol,))
                        conn.commit()
                    except Exception:
                        pass
                    return None
        except sqlite3.Error as e:
            print(f"❌ 数据库错误 ({symbol}): {e}")
            return None
        except Exception as e:
            print(f"❌ 读取缓存失败 ({symbol}): {e}")
            return None
    
    def is_cache_valid(self, symbol: str) -> bool:
        """检查缓存是否有效"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT timestamp FROM analysis_cache 
                    WHERE symbol = ?
                ''', (symbol,))
                result = cursor.fetchone()
                
                if not result:
                    return False
                
                timestamp = result[0]
                current_time = time.time()
                
                # 检查缓存是否过期
                if current_time - timestamp > self.ttl_seconds:
                    cursor.execute('DELETE FROM analysis_cache WHERE symbol = ?', (symbol,))
                    conn.commit()
                    return False
                
                return True
        except Exception as e:
            print(f"⚠️ 检查缓存有效性失败 ({symbol}): {e}")
            return False
    
    def delete_analysis(self, symbol: str) -> bool:
        """删除分析缓存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM analysis_cache WHERE symbol = ?', (symbol,))
                conn.commit()
                return True
        except Exception as e:
            print(f"❌ 删除缓存失败 ({symbol}): {e}")
            return False
    
    def clear_all(self) -> bool:
        """清空所有缓存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM analysis_cache')
                conn.commit()
                return True
        except Exception as e:
            print(f"❌ 清空缓存失败: {e}")
            return False
    
    def get_all_valid(self) -> dict:
        """获取所有有效的缓存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT symbol, analysis_data, timestamp FROM analysis_cache
                ''')
                results = cursor.fetchall()
                
                current_time = time.time()
                valid_cache = {}
                expired_symbols = []
                
                for symbol, analysis_data_str, timestamp in results:
                    if current_time - timestamp > self.ttl_seconds:
                        expired_symbols.append(symbol)
                    else:
                        analysis_data = json.loads(analysis_data_str)
                        analysis_data['_cache_remaining_time'] = self.ttl_seconds - (current_time - timestamp)
                        valid_cache[symbol] = analysis_data
                
                # 删除过期数据
                for symbol in expired_symbols:
                    cursor.execute('DELETE FROM analysis_cache WHERE symbol = ?', (symbol,))
                conn.commit()
                
                return valid_cache
        except Exception as e:
            print(f"❌ 获取所有缓存失败: {e}")
            return {}

    def get_recent_within(self, symbol: str, seconds: int = 300) -> dict:
        """获取指定时间窗口内最近的分析记录（即便缓存已过期，用于降级显示）"""
        try:
            if not symbol:
                return None
            cutoff = time.time() - seconds
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT analysis_data, timestamp FROM analysis_history
                    WHERE symbol = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''', (symbol, cutoff))
                row = cursor.fetchone()
                if not row:
                    return None
                analysis_data_str, ts = row
                data = json.loads(analysis_data_str)
                data['_cache_remaining_time'] = max(0, seconds - (time.time() - ts))
                data['_from_history'] = True
                return data
        except Exception as e:
            print(f"⚠️ 获取历史记录失败 ({symbol}): {e}")
            return None
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM analysis_cache')
                total = cursor.fetchone()[0]
                
                current_time = time.time()
                cursor.execute('''
                    SELECT COUNT(*) FROM analysis_cache 
                    WHERE ? - timestamp <= ?
                ''', (current_time, self.ttl_seconds))
                valid = cursor.fetchone()[0]
                
                return {
                    'total_records': total,
                    'valid_records': valid,
                    'expired_records': total - valid,
                    'ttl_seconds': self.ttl_seconds
                }
        except Exception as e:
            print(f"❌ 获取缓存统计失败: {e}")
            return {}

    # ==================== 命中率/盈亏标记 ====================
    def mark_hit(self, history_id: int, hit: int, pnl: float = None) -> bool:
        """标记某条历史分析是否命中 hit=1命中 hit=0未命中"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE analysis_history SET hit = ?, pnl = ? WHERE id = ?
                ''', (hit, pnl, history_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ 标记命中失败: {e}")
            return False

    def get_history_list(self, symbol: str = None, limit: int = 50) -> list:
        """获取历史分析列表，可按币种筛选"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if symbol:
                    cursor.execute('''
                        SELECT id, symbol, analysis_data, timestamp, hit, pnl
                        FROM analysis_history WHERE symbol = ?
                        ORDER BY timestamp DESC LIMIT ?
                    ''', (symbol, limit))
                else:
                    cursor.execute('''
                        SELECT id, symbol, analysis_data, timestamp, hit, pnl
                        FROM analysis_history
                        ORDER BY timestamp DESC LIMIT ?
                    ''', (limit,))
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    results.append({
                        'id': row[0], 'symbol': row[1],
                        'analysis_data': row[2], 'timestamp': row[3],
                        'hit': row[4], 'pnl': row[5]
                    })
                return results
        except Exception as e:
            print(f"❌ 获取历史列表失败: {e}")
            return []

    def get_win_rate(self, symbol: str = None, limit: int = 30) -> dict:
        """获取胜率统计 (最近N条已标记的记录，limit=None表示全部)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if symbol:
                    if limit is None:
                        cursor.execute('''
                            SELECT hit, pnl FROM analysis_history
                            WHERE symbol = ? AND hit IS NOT NULL
                            ORDER BY timestamp DESC
                        ''', (symbol,))
                    else:
                        cursor.execute('''
                            SELECT hit, pnl FROM analysis_history
                            WHERE symbol = ? AND hit IS NOT NULL
                            ORDER BY timestamp DESC LIMIT ?
                        ''', (symbol, limit))
                else:
                    if limit is None:
                        cursor.execute('''
                            SELECT hit, pnl FROM analysis_history
                            WHERE hit IS NOT NULL
                            ORDER BY timestamp DESC
                        ''')
                    else:
                        cursor.execute('''
                            SELECT hit, pnl FROM analysis_history
                            WHERE hit IS NOT NULL
                            ORDER BY timestamp DESC LIMIT ?
                        ''', (limit,))
                rows = cursor.fetchall()
                if not rows:
                    return {'total': 0, 'wins': 0, 'losses': 0, 'win_rate': 0.0, 'avg_pnl': 0.0}
                total = len(rows)
                wins = sum(1 for r in rows if r[0] == 1)
                losses = total - wins
                pnl_list = [r[1] for r in rows if r[1] is not None]
                avg_pnl = sum(pnl_list) / len(pnl_list) if pnl_list else 0.0
                return {
                    'total': total, 'wins': wins, 'losses': losses,
                    'win_rate': round(wins / total * 100, 1) if total > 0 else 0.0,
                    'avg_pnl': round(avg_pnl, 2)
                }
        except Exception as e:
            print(f"❌ 获取胜率统计失败: {e}")
            return {'total': 0, 'wins': 0, 'losses': 0, 'win_rate': 0.0, 'avg_pnl': 0.0}

    def get_distinct_symbols(self) -> list:
        """获取历史中所有不重复的交易对"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT DISTINCT symbol FROM analysis_history ORDER BY symbol')
                return [r[0] for r in cursor.fetchall()]
        except Exception:
            return []

    # ==================== 币安数据存储（7天） ====================
    def save_binance_data(self, symbol: str, kline_data: list, funding_rate: float = None) -> bool:
        """保存币安API返回的K线数据和资金费率（7天存储）"""
        try:
            if not symbol or not kline_data:
                return False
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                timestamp = time.time()
                cursor.execute('''
                    INSERT INTO binance_data (symbol, kline_data, funding_rate, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (symbol, json.dumps(kline_data, ensure_ascii=False), funding_rate, timestamp))
                # 清理7天之前的数据
                cutoff = timestamp - self.binance_ttl_seconds
                cursor.execute('DELETE FROM binance_data WHERE timestamp < ?', (cutoff,))
                conn.commit()
                return True
        except Exception as e:
            print(f"❌ 保存币安数据失败: {e}")
            return False

    def get_binance_analytics(self, symbol: str = None, days: int = 7) -> dict:
        """从币安数据表获取分析统计（价格波动、资金费率趋势等）"""
        try:
            cutoff = time.time() - days * 24 * 3600
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if symbol:
                    cursor.execute('''
                        SELECT kline_data, funding_rate FROM binance_data
                        WHERE symbol = ? AND timestamp >= ?
                        ORDER BY timestamp DESC
                    ''', (symbol, cutoff))
                else:
                    cursor.execute('''
                        SELECT symbol, kline_data, funding_rate FROM binance_data
                        WHERE timestamp >= ?
                        ORDER BY timestamp DESC
                    ''', (cutoff,))
                rows = cursor.fetchall()
                if not rows:
                    return {}
                
                analytics = {'symbol': symbol or 'all', 'period_days': days, 'records': len(rows)}
                
                if symbol:
                    # 单币种分析
                    prices = []
                    funding_rates = []
                    for row in rows:
                        try:
                            kline = json.loads(row[0])
                            if kline and len(kline) > 0:
                                prices.append(float(kline[-1].get('close', 0)))
                            if row[1] is not None:
                                funding_rates.append(float(row[1]))
                        except:
                            pass
                    
                    if prices:
                        analytics['avg_price'] = round(sum(prices) / len(prices), 2)
                        analytics['max_price'] = round(max(prices), 2)
                        analytics['min_price'] = round(min(prices), 2)
                        analytics['price_volatility'] = round((max(prices) - min(prices)) / (sum(prices) / len(prices)) * 100, 2) if prices else 0
                    
                    if funding_rates:
                        analytics['avg_funding_rate'] = round(sum(funding_rates) / len(funding_rates), 6)
                        analytics['max_funding_rate'] = round(max(funding_rates), 6)
                        analytics['min_funding_rate'] = round(min(funding_rates), 6)
                
                return analytics
        except Exception as e:
            print(f"❌ 获取币安分析统计失败: {e}")
            return {}


# 全局缓存实例
cache = AnalysisCache()
