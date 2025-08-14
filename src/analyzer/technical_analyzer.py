"""
技术分析模块 - 基金技术指标分析
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

# 尝试导入talib，如果失败则使用替代方案
try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False
    # 创建一个模拟的talib模块
    class MockTalib:
        def SMA(self, close, timeperiod):
            return pd.Series(close).rolling(window=timeperiod).mean().values
        
        def EMA(self, close, timeperiod):
            return pd.Series(close).ewm(span=timeperiod).mean().values
        
        def RSI(self, close, timeperiod=14):
            delta = pd.Series(close).diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=timeperiod).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=timeperiod).mean()
            rs = gain / loss
            return (100 - (100 / (1 + rs))).values
        
        def MACD(self, close, fastperiod=12, slowperiod=26, signalperiod=9):
            exp1 = pd.Series(close).ewm(span=fastperiod).mean()
            exp2 = pd.Series(close).ewm(span=slowperiod).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=signalperiod).mean()
            histogram = macd - signal
            return macd.values, signal.values, histogram.values
        
        def BBANDS(self, close, timeperiod=20, nbdevup=2, nbdevdn=2):
            sma = pd.Series(close).rolling(window=timeperiod).mean()
            std = pd.Series(close).rolling(window=timeperiod).std()
            upper = sma + (std * nbdevup)
            lower = sma - (std * nbdevdn)
            return upper.values, sma.values, lower.values
        
        def STOCH(self, high, low, close, fastk_period=14, slowk_period=3, slowd_period=3):
            lowest_low = pd.Series(low).rolling(window=fastk_period).min()
            highest_high = pd.Series(high).rolling(window=fastk_period).max()
            k_percent = 100 * ((pd.Series(close) - lowest_low) / (highest_high - lowest_low))
            k_percent = k_percent.rolling(window=slowk_period).mean()
            d_percent = k_percent.rolling(window=slowd_period).mean()
            return k_percent.values, d_percent.values
        
        def ATR(self, high, low, close, timeperiod=14):
            high_low = pd.Series(high) - pd.Series(low)
            high_close = abs(pd.Series(high) - pd.Series(close).shift())
            low_close = abs(pd.Series(low) - pd.Series(close).shift())
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            return true_range.rolling(window=timeperiod).mean().values
    
    talib = MockTalib()
from dataclasses import dataclass
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from ..utils.logger import log_info, log_warning, log_error, log_debug

@dataclass
class TechnicalSignal:
    """技术分析信号"""
    indicator: str
    signal_type: str  # 'buy', 'sell', 'hold'
    strength: float  # 0-1之间，信号强度
    value: float
    description: str
    timestamp: datetime

class TechnicalAnalyzer:
    """技术分析器"""

    def __init__(self):
        self.indicators = {}
        self.signals = []

    def analyze(self, df: pd.DataFrame, fund_code: str = "") -> Dict:
        """综合技术分析"""
        if df.empty or len(df) < 20:
            log_warning(f"数据不足，无法进行技术分析: {fund_code}")
            return {}

        try:
            # 确保数据格式正确
            df = self._prepare_data(df)

            # 计算各种技术指标
            results = {
                'fund_code': fund_code,
                'analysis_time': datetime.now(),
                'data_points': len(df),
                'latest_price': df['close'].iloc[-1],
                'price_change': self._calculate_price_change(df),
                'moving_averages': self._calculate_moving_averages(df),
                'macd': self._calculate_macd(df),
                'rsi': self._calculate_rsi(df),
                'bollinger_bands': self._calculate_bollinger_bands(df),
                'kdj': self._calculate_kdj(df),
                'volume_indicators': self._calculate_volume_indicators(df),
                'trend_indicators': self._calculate_trend_indicators(df),
                'momentum_indicators': self._calculate_momentum_indicators(df),
                'volatility_indicators': self._calculate_volatility_indicators(df),
                'support_resistance': self._calculate_support_resistance(df),
                'pattern_recognition': self._pattern_recognition(df),
                'signals': self._generate_signals(df),
                'risk_metrics': self._calculate_risk_metrics(df),
                'performance_metrics': self._calculate_performance_metrics(df)
            }

            # 综合评分
            results['technical_score'] = self._calculate_technical_score(results)
            results['recommendation'] = self._get_recommendation(results['technical_score'])

            return results

        except Exception as e:
            log_error(f"技术分析失败 {fund_code}: {e}")
            return {}

    def _prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """准备数据"""
        # 确保必要的列存在
        required_columns = ['date', 'nav']

        if 'nav' in df.columns:
            df['close'] = df['nav']
        elif 'close' not in df.columns and 'nav' in df.columns:
            df['close'] = df['nav']

        # 如果没有成交量数据，使用价格变化幅度模拟
        if 'volume' not in df.columns:
            df['volume'] = abs(df['close'].pct_change()).fillna(0) * 1000000

        # 如果没有高低价，使用收盘价估算
        if 'high' not in df.columns:
            df['high'] = df['close'] * (1 + abs(df['close'].pct_change()).fillna(0))
        if 'low' not in df.columns:
            df['low'] = df['close'] * (1 - abs(df['close'].pct_change()).fillna(0))
        if 'open' not in df.columns:
            df['open'] = df['close'].shift(1).fillna(df['close'])

        # 确保数据类型正确
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # 处理缺失值
        df = df.fillna(method='ffill').fillna(method='bfill')

        # 按日期排序
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)

        return df

    def _calculate_price_change(self, df: pd.DataFrame) -> Dict:
        """计算价格变化"""
        current_price = df['close'].iloc[-1]

        changes = {}
        periods = [1, 5, 10, 20, 60]

        for period in periods:
            if len(df) > period:
                past_price = df['close'].iloc[-(period+1)]
                change_pct = (current_price - past_price) / past_price * 100
                changes[f'{period}d_change'] = round(change_pct, 2)

        return changes

    def _calculate_moving_averages(self, df: pd.DataFrame) -> Dict:
        """计算移动平均线"""
        ma_data = {}
        periods = [5, 10, 20, 60, 120, 250]

        for period in periods:
            if len(df) >= period:
                ma_data[f'MA{period}'] = round(df['close'].rolling(period).mean().iloc[-1], 4)

                # 计算当前价格与均线的偏离度
                current_price = df['close'].iloc[-1]
                ma_value = ma_data[f'MA{period}']
                deviation = (current_price - ma_value) / ma_value * 100
                ma_data[f'MA{period}_deviation'] = round(deviation, 2)

        # 均线排列
        ma_data['ma_alignment'] = self._check_ma_alignment(df)

        # 金叉死叉
        ma_data['golden_cross'] = self._check_golden_cross(df)
        ma_data['death_cross'] = self._check_death_cross(df)

        return ma_data

    def _check_ma_alignment(self, df: pd.DataFrame) -> str:
        """检查均线排列"""
        try:
            if len(df) < 60:
                return "数据不足"

            ma5 = df['close'].rolling(5).mean().iloc[-1]
            ma10 = df['close'].rolling(10).mean().iloc[-1]
            ma20 = df['close'].rolling(20).mean().iloc[-1]
            ma60 = df['close'].rolling(60).mean().iloc[-1]

            if ma5 > ma10 > ma20 > ma60:
                return "多头排列"
            elif ma5 < ma10 < ma20 < ma60:
                return "空头排列"
            else:
                return "震荡排列"

        except Exception:
            return "未知"

    def _check_golden_cross(self, df: pd.DataFrame) -> bool:
        """检查金叉"""
        try:
            if len(df) < 20:
                return False

            ma5 = df['close'].rolling(5).mean()
            ma10 = df['close'].rolling(10).mean()

            # 当前5日线在10日线上方，且前一日在下方
            current_above = ma5.iloc[-1] > ma10.iloc[-1]
            previous_below = ma5.iloc[-2] <= ma10.iloc[-2]

            return current_above and previous_below

        except Exception:
            return False

    def _check_death_cross(self, df: pd.DataFrame) -> bool:
        """检查死叉"""
        try:
            if len(df) < 20:
                return False

            ma5 = df['close'].rolling(5).mean()
            ma10 = df['close'].rolling(10).mean()

            # 当前5日线在10日线下方，且前一日在上方
            current_below = ma5.iloc[-1] < ma10.iloc[-1]
            previous_above = ma5.iloc[-2] >= ma10.iloc[-2]

            return current_below and previous_above

        except Exception:
            return False

    def _calculate_macd(self, df: pd.DataFrame) -> Dict:
        """计算MACD指标"""
        try:
            if len(df) < 34:
                return {}

            # 计算MACD
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            macd_line = exp1 - exp2
            signal_line = macd_line.ewm(span=9).mean()
            histogram = macd_line - signal_line

            return {
                'macd': round(macd_line.iloc[-1], 4),
                'signal': round(signal_line.iloc[-1], 4),
                'histogram': round(histogram.iloc[-1], 4),
                'macd_trend': 'up' if macd_line.iloc[-1] > macd_line.iloc[-2] else 'down',
                'signal_cross': self._check_macd_cross(macd_line, signal_line),
                'zero_cross': self._check_macd_zero_cross(macd_line)
            }

        except Exception as e:
            log_debug(f"MACD计算失败: {e}")
            return {}

    def _check_macd_cross(self, macd_line: pd.Series, signal_line: pd.Series) -> str:
        """检查MACD金叉死叉"""
        try:
            if len(macd_line) < 2:
                return "无"

            current_above = macd_line.iloc[-1] > signal_line.iloc[-1]
            previous_below = macd_line.iloc[-2] <= signal_line.iloc[-2]

            if current_above and previous_below:
                return "金叉"

            current_below = macd_line.iloc[-1] < signal_line.iloc[-1]
            previous_above = macd_line.iloc[-2] >= signal_line.iloc[-2]

            if current_below and previous_above:
                return "死叉"

            return "无"

        except Exception:
            return "无"

    def _check_macd_zero_cross(self, macd_line: pd.Series) -> str:
        """检查MACD零轴穿越"""
        try:
            if len(macd_line) < 2:
                return "无"

            current_above = macd_line.iloc[-1] > 0
            previous_below = macd_line.iloc[-2] <= 0

            if current_above and previous_below:
                return "上穿零轴"

            current_below = macd_line.iloc[-1] < 0
            previous_above = macd_line.iloc[-2] >= 0

            if current_below and previous_above:
                return "下穿零轴"

            return "无"

        except Exception:
            return "无"

    def _calculate_rsi(self, df: pd.DataFrame, period=14) -> Dict:
        """计算RSI指标"""
        try:
            if len(df) < period + 1:
                return {}

            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            current_rsi = rsi.iloc[-1]

            # RSI信号判断
            if current_rsi > 80:
                rsi_signal = "超买"
            elif current_rsi < 20:
                rsi_signal = "超卖"
            elif current_rsi > 70:
                rsi_signal = "偏强"
            elif current_rsi < 30:
                rsi_signal = "偏弱"
            else:
                rsi_signal = "中性"

            return {
                'rsi': round(current_rsi, 2),
                'rsi_signal': rsi_signal,
                'rsi_trend': 'up' if rsi.iloc[-1] > rsi.iloc[-2] else 'down'
            }

        except Exception as e:
            log_debug(f"RSI计算失败: {e}")
            return {}

    def _calculate_bollinger_bands(self, df: pd.DataFrame, period=20, std_dev=2) -> Dict:
        """计算布林带"""
        try:
            if len(df) < period:
                return {}

            sma = df['close'].rolling(period).mean()
            std = df['close'].rolling(period).std()

            upper_band = sma + (std * std_dev)
            lower_band = sma - (std * std_dev)

            current_price = df['close'].iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_middle = sma.iloc[-1]
            current_lower = lower_band.iloc[-1]

            # 布林带位置
            bb_position = (current_price - current_lower) / (current_upper - current_lower)

            # 布林带宽度
            bb_width = (current_upper - current_lower) / current_middle

            # 布林带信号
            if current_price > current_upper:
                bb_signal = "突破上轨"
            elif current_price < current_lower:
                bb_signal = "跌破下轨"
            elif bb_position > 0.8:
                bb_signal = "接近上轨"
            elif bb_position < 0.2:
                bb_signal = "接近下轨"
            else:
                bb_signal = "中轨附近"

            return {
                'bb_upper': round(current_upper, 4),
                'bb_middle': round(current_middle, 4),
                'bb_lower': round(current_lower, 4),
                'bb_position': round(bb_position, 3),
                'bb_width': round(bb_width, 4),
                'bb_signal': bb_signal
            }

        except Exception as e:
            log_debug(f"布林带计算失败: {e}")
            return {}

    def _calculate_kdj(self, df: pd.DataFrame, n=9, m1=3, m2=3) -> Dict:
        """计算KDJ指标"""
        try:
            if len(df) < n:
                return {}

            low_n = df['low'].rolling(n).min()
            high_n = df['high'].rolling(n).max()

            rsv = (df['close'] - low_n) / (high_n - low_n) * 100
            rsv = rsv.fillna(50)

            k = rsv.ewm(alpha=1/m1).mean()
            d = k.ewm(alpha=1/m2).mean()
            j = 3 * k - 2 * d

            current_k = k.iloc[-1]
            current_d = d.iloc[-1]
            current_j = j.iloc[-1]

            # KDJ信号
            if current_k > 80 and current_d > 80:
                kdj_signal = "超买"
            elif current_k < 20 and current_d < 20:
                kdj_signal = "超卖"
            elif current_k > current_d and k.iloc[-2] <= d.iloc[-2]:
                kdj_signal = "金叉"
            elif current_k < current_d and k.iloc[-2] >= d.iloc[-2]:
                kdj_signal = "死叉"
            else:
                kdj_signal = "中性"

            return {
                'k': round(current_k, 2),
                'd': round(current_d, 2),
                'j': round(current_j, 2),
                'kdj_signal': kdj_signal
            }

        except Exception as e:
            log_debug(f"KDJ计算失败: {e}")
            return {}

    def _calculate_volume_indicators(self, df: pd.DataFrame) -> Dict:
        """计算成交量指标"""
        try:
            volume_data = {}

            if 'volume' not in df.columns or len(df) < 20:
                return volume_data

            # 成交量移动平均
            volume_data['volume_ma5'] = df['volume'].rolling(5).mean().iloc[-1]
            volume_data['volume_ma10'] = df['volume'].rolling(10).mean().iloc[-1]

            # 量价关系
            price_change = df['close'].pct_change().iloc[-1]
            volume_change = df['volume'].pct_change().iloc[-1]

            if price_change > 0 and volume_change > 0:
                volume_data['volume_price_trend'] = "量价齐升"
            elif price_change < 0 and volume_change > 0:
                volume_data['volume_price_trend'] = "量增价跌"
            elif price_change > 0 and volume_change < 0:
                volume_data['volume_price_trend'] = "价升量缩"
            else:
                volume_data['volume_price_trend'] = "量价齐跌"

            # OBV指标
            obv = ((df['close'] - df['close'].shift(1)).apply(lambda x: 1 if x > 0 else -1 if x < 0 else 0) * df['volume']).cumsum()
            volume_data['obv'] = obv.iloc[-1]
            volume_data['obv_trend'] = 'up' if obv.iloc[-1] > obv.iloc[-5] else 'down'

            return volume_data

        except Exception as e:
            log_debug(f"成交量指标计算失败: {e}")
            return {}

    def _calculate_trend_indicators(self, df: pd.DataFrame) -> Dict:
        """计算趋势指标"""
        try:
            trend_data = {}

            if len(df) < 20:
                return trend_data

            # ADX趋势强度指标
            if len(df) >= 14:
                high = df['high'].values
                low = df['low'].values
                close = df['close'].values

                try:
                    adx = talib.ADX(high, low, close, timeperiod=14)
                    if not np.isnan(adx[-1]):
                        trend_data['adx'] = round(adx[-1], 2)

                        if adx[-1] > 50:
                            trend_data['trend_strength'] = "强趋势"
                        elif adx[-1] > 25:
                            trend_data['trend_strength'] = "中等趋势"
                        else:
                            trend_data['trend_strength'] = "弱趋势"
                except:
                    pass

            # 趋势线斜率
            if len(df) >= 20:
                x = np.arange(len(df[-20:]))
                y = df['close'].iloc[-20:].values
                slope = np.polyfit(x, y, 1)[0]
                trend_data['trend_slope'] = round(slope, 6)
                trend_data['trend_direction'] = 'up' if slope > 0 else 'down'

            return trend_data

        except Exception as e:
            log_debug(f"趋势指标计算失败: {e}")
            return {}

    def _calculate_momentum_indicators(self, df: pd.DataFrame) -> Dict:
        """计算动量指标"""
        try:
            momentum_data = {}

            if len(df) < 14:
                return momentum_data

            # 动量指标
            momentum = df['close'] / df['close'].shift(10) - 1
            momentum_data['momentum'] = round(momentum.iloc[-1], 4)

            # ROC变化率
            roc = (df['close'] - df['close'].shift(12)) / df['close'].shift(12) * 100
            momentum_data['roc'] = round(roc.iloc[-1], 2)

            # CCI商品通道指标
            if len(df) >= 20:
                typical_price = (df['high'] + df['low'] + df['close']) / 3
                sma_tp = typical_price.rolling(20).mean()
                mad = typical_price.rolling(20).apply(lambda x: np.mean(np.abs(x - x.mean())))
                cci = (typical_price - sma_tp) / (0.015 * mad)

                if not np.isnan(cci.iloc[-1]):
                    momentum_data['cci'] = round(cci.iloc[-1], 2)

                    if cci.iloc[-1] > 100:
                        momentum_data['cci_signal'] = "超买"
                    elif cci.iloc[-1] < -100:
                        momentum_data['cci_signal'] = "超卖"
                    else:
                        momentum_data['cci_signal'] = "中性"

            return momentum_data

        except Exception as e:
            log_debug(f"动量指标计算失败: {e}")
            return {}

    def _calculate_volatility_indicators(self, df: pd.DataFrame) -> Dict:
        """计算波动率指标"""
        try:
            volatility_data = {}

            if len(df) < 20:
                return volatility_data

            # 历史波动率
            returns = df['close'].pct_change().dropna()
            volatility_data['volatility_20d'] = round(returns.rolling(20).std().iloc[-1] * np.sqrt(252), 4)
            volatility_data['volatility_60d'] = round(returns.rolling(60).std().iloc[-1] * np.sqrt(252), 4) if len(df) >= 60 else None

            # ATR真实波动幅度
            if len(df) >= 14:
                high = df['high'].values
                low = df['low'].values
                close = df['close'].values

                try:
                    atr = talib.ATR(high, low, close, timeperiod=14)
                    if not np.isnan(atr[-1]):
                        volatility_data['atr'] = round(atr[-1], 4)
                        volatility_data['atr_ratio'] = round(atr[-1] / df['close'].iloc[-1], 4)
                except:
                    pass

            return volatility_data

        except Exception as e:
            log_debug(f"波动率指标计算失败: {e}")
            return {}

    def _calculate_support_resistance(self, df: pd.DataFrame) -> Dict:
        """计算支撑阻力位"""
        try:
            sr_data = {}

            if len(df) < 20:
                return sr_data

            # 近期高低点
            recent_data = df.tail(60) if len(df) >= 60 else df

            # 支撑位（近期低点）
            supports = []
            for i in range(2, len(recent_data) - 2):
                if (recent_data['low'].iloc[i] < recent_data['low'].iloc[i-1] and 
                    recent_data['low'].iloc[i] < recent_data['low'].iloc[i+1] and
                    recent_data['low'].iloc[i] < recent_data['low'].iloc[i-2] and
                    recent_data['low'].iloc[i] < recent_data['low'].iloc[i+2]):
                    supports.append(recent_data['low'].iloc[i])

            # 阻力位（近期高点）
            resistances = []
            for i in range(2, len(recent_data) - 2):
                if (recent_data['high'].iloc[i] > recent_data['high'].iloc[i-1] and 
                    recent_data['high'].iloc[i] > recent_data['high'].iloc[i+1] and
                    recent_data['high'].iloc[i] > recent_data['high'].iloc[i-2] and
                    recent_data['high'].iloc[i] > recent_data['high'].iloc[i+2]):
                    resistances.append(recent_data['high'].iloc[i])

            current_price = df['close'].iloc[-1]

            # 找最近的支撑阻力位
            if supports:
                supports_below = [s for s in supports if s < current_price]
                sr_data['nearest_support'] = max(supports_below) if supports_below else min(supports)

            if resistances:
                resistances_above = [r for r in resistances if r > current_price]
                sr_data['nearest_resistance'] = min(resistances_above) if resistances_above else max(resistances)

            return sr_data

        except Exception as e:
            log_debug(f"支撑阻力位计算失败: {e}")
            return {}

    def _pattern_recognition(self, df: pd.DataFrame) -> Dict:
        """K线形态识别"""
        try:
            patterns = {}

            if len(df) < 5:
                return patterns

            # 获取最近几天的数据
            recent = df.tail(5)

            # 连涨连跌
            consecutive_up = 0
            consecutive_down = 0

            for i in range(1, len(recent)):
                if recent['close'].iloc[i] > recent['close'].iloc[i-1]:
                    consecutive_up += 1
                    consecutive_down = 0
                elif recent['close'].iloc[i] < recent['close'].iloc[i-1]:
                    consecutive_down += 1
                    consecutive_up = 0
                else:
                    consecutive_up = 0
                    consecutive_down = 0

            patterns['consecutive_up'] = consecutive_up
            patterns['consecutive_down'] = consecutive_down

            # 缺口识别
            if len(df) >= 2:
                today_low = df['low'].iloc[-1]
                yesterday_high = df['high'].iloc[-2]
                today_high = df['high'].iloc[-1]
                yesterday_low = df['low'].iloc[-2]

                if today_low > yesterday_high:
                    patterns['gap'] = "向上跳空"
                elif today_high < yesterday_low:
                    patterns['gap'] = "向下跳空"
                else:
                    patterns['gap'] = "无跳空"

            return patterns

        except Exception as e:
            log_debug(f"形态识别失败: {e}")
            return {}

    def _generate_signals(self, df: pd.DataFrame) -> List[TechnicalSignal]:
        """生成技术信号"""
        signals = []

        try:
            current_price = df['close'].iloc[-1]

            # MA信号
            if len(df) >= 20:
                ma5 = df['close'].rolling(5).mean().iloc[-1]
                ma20 = df['close'].rolling(20).mean().iloc[-1]

                if current_price > ma5 > ma20:
                    signals.append(TechnicalSignal(
                        indicator="MA",
                        signal_type="buy",
                        strength=0.6,
                        value=current_price,
                        description="价格站上短期均线",
                        timestamp=datetime.now()
                    ))
                elif current_price < ma5 < ma20:
                    signals.append(TechnicalSignal(
                        indicator="MA",
                        signal_type="sell",
                        strength=0.6,
                        value=current_price,
                        description="价格跌破短期均线",
                        timestamp=datetime.now()
                    ))

            # RSI信号
            if len(df) >= 14:
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                current_rsi = rsi.iloc[-1]

                if current_rsi < 30:
                    signals.append(TechnicalSignal(
                        indicator="RSI",
                        signal_type="buy",
                        strength=0.7,
                        value=current_rsi,
                        description="RSI超卖",
                        timestamp=datetime.now()
                    ))
                elif current_rsi > 70:
                    signals.append(TechnicalSignal(
                        indicator="RSI",
                        signal_type="sell",
                        strength=0.7,
                        value=current_rsi,
                        description="RSI超买",
                        timestamp=datetime.now()
                    ))

            return signals

        except Exception as e:
            log_debug(f"信号生成失败: {e}")
            return []

    def _calculate_risk_metrics(self, df: pd.DataFrame) -> Dict:
        """计算风险指标"""
        try:
            risk_metrics = {}

            if len(df) < 20:
                return risk_metrics

            returns = df['close'].pct_change().dropna()

            # 最大回撤
            cumulative = (1 + returns).cumprod()
            rolling_max = cumulative.expanding().max()
            drawdown = (cumulative - rolling_max) / rolling_max
            risk_metrics['max_drawdown'] = round(drawdown.min(), 4)

            # 夏普比率（假设无风险利率为3%）
            if len(returns) >= 252:
                annual_return = returns.mean() * 252
                annual_volatility = returns.std() * np.sqrt(252)
                risk_free_rate = 0.03

                if annual_volatility > 0:
                    risk_metrics['sharpe_ratio'] = round((annual_return - risk_free_rate) / annual_volatility, 4)

            # VaR (Value at Risk) 95%置信度
            if len(returns) >= 20:
                var_95 = np.percentile(returns, 5)
                risk_metrics['var_95'] = round(var_95, 4)

            return risk_metrics

        except Exception as e:
            log_debug(f"风险指标计算失败: {e}")
            return {}

    def _calculate_performance_metrics(self, df: pd.DataFrame) -> Dict:
        """计算绩效指标"""
        try:
            performance = {}

            if len(df) < 20:
                return performance

            returns = df['close'].pct_change().dropna()

            # 年化收益率
            if len(returns) >= 252:
                total_return = (df['close'].iloc[-1] / df['close'].iloc[-252] - 1)
                performance['annual_return'] = round(total_return, 4)

            # 波动率
            if len(returns) >= 20:
                performance['volatility'] = round(returns.std() * np.sqrt(252), 4)

            # 胜率
            win_rate = (returns > 0).sum() / len(returns)
            performance['win_rate'] = round(win_rate, 4)

            # 平均收益
            performance['avg_return'] = round(returns.mean(), 6)
            performance['avg_positive_return'] = round(returns[returns > 0].mean(), 6)
            performance['avg_negative_return'] = round(returns[returns < 0].mean(), 6)

            return performance

        except Exception as e:
            log_debug(f"绩效指标计算失败: {e}")
            return {}

    def _calculate_technical_score(self, analysis_result: Dict) -> float:
        """计算技术分析综合评分"""
        try:
            score = 50  # 基础分50分

            # 趋势分析 (30分)
            ma_data = analysis_result.get('moving_averages', {})
            if ma_data.get('ma_alignment') == '多头排列':
                score += 15
            elif ma_data.get('ma_alignment') == '空头排列':
                score -= 15

            if ma_data.get('golden_cross'):
                score += 10
            elif ma_data.get('death_cross'):
                score -= 10

            # MACD分析 (20分)
            macd_data = analysis_result.get('macd', {})
            if macd_data.get('signal_cross') == '金叉':
                score += 10
            elif macd_data.get('signal_cross') == '死叉':
                score -= 10

            if macd_data.get('zero_cross') == '上穿零轴':
                score += 5
            elif macd_data.get('zero_cross') == '下穿零轴':
                score -= 5

            # RSI分析 (20分)
            rsi_data = analysis_result.get('rsi', {})
            rsi_signal = rsi_data.get('rsi_signal', '')
            if rsi_signal == '超卖':
                score += 10
            elif rsi_signal == '超买':
                score -= 10
            elif rsi_signal == '偏强':
                score += 5
            elif rsi_signal == '偏弱':
                score -= 5

            # KDJ分析 (15分)
            kdj_data = analysis_result.get('kdj', {})
            kdj_signal = kdj_data.get('kdj_signal', '')
            if kdj_signal == '金叉':
                score += 8
            elif kdj_signal == '死叉':
                score -= 8
            elif kdj_signal == '超卖':
                score += 5
            elif kdj_signal == '超买':
                score -= 5

            # 布林带分析 (15分)
            bb_data = analysis_result.get('bollinger_bands', {})
            bb_signal = bb_data.get('bb_signal', '')
            if bb_signal == '跌破下轨':
                score += 8
            elif bb_signal == '突破上轨':
                score -= 8
            elif bb_signal == '接近下轨':
                score += 3
            elif bb_signal == '接近上轨':
                score -= 3

            # 确保分数在0-100之间
            score = max(0, min(100, score))

            return round(score, 1)

        except Exception as e:
            log_debug(f"技术评分计算失败: {e}")
            return 50.0

    def _get_recommendation(self, score: float) -> str:
        """根据评分获取建议"""
        if score >= 80:
            return "强烈买入"
        elif score >= 65:
            return "买入"
        elif score >= 55:
            return "谨慎买入"
        elif score >= 45:
            return "持有"
        elif score >= 35:
            return "谨慎卖出"
        elif score >= 20:
            return "卖出"
        else:
            return "强烈卖出"

# 创建全局技术分析器实例
technical_analyzer = TechnicalAnalyzer()

def analyze_fund_technical(df: pd.DataFrame, fund_code: str = "") -> Dict:
    """分析基金技术指标"""
    return technical_analyzer.analyze(df, fund_code)

if __name__ == "__main__":
    # 测试技术分析
    import pandas as pd
    import numpy as np

    # 生成测试数据
    dates = pd.date_range(start='2023-01-01', end='2024-01-01', freq='D')
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(len(dates)) * 0.02)

    test_df = pd.DataFrame({
        'date': dates,
        'close': prices,
        'nav': prices
    })

    # 执行技术分析
    result = analyze_fund_technical(test_df, "测试基金")
    print("技术分析结果:")
    for key, value in result.items():
        print(f"{key}: {value}")
