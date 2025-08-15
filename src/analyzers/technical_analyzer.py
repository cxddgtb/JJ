#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.logger import setup_logger
from utils.config import Config

class TechnicalAnalyzer:
    def __init__(self):
        """初始化技术分析器"""
        self.logger = setup_logger('TechnicalAnalyzer')

    def calculate_sma(self, data, window=20):
        """
        计算简单移动平均线(SMA)

        Args:
            data (pd.Series): 价格数据
            window (int): 窗口大小

        Returns:
            pd.Series: SMA值
        """
        return data.rolling(window=window).mean()

    def calculate_ema(self, data, window=20):
        """
        计算指数移动平均线(EMA)

        Args:
            data (pd.Series): 价格数据
            window (int): 窗口大小

        Returns:
            pd.Series: EMA值
        """
        return data.ewm(span=window, adjust=False).mean()

    def calculate_macd(self, data, fast=12, slow=26, signal=9):
        """
        计算MACD指标

        Args:
            data (pd.Series): 价格数据
            fast (int): 快速EMA周期
            slow (int): 慢速EMA周期
            signal (int): 信号线周期

        Returns:
            dict: 包含MACD线、信号线和直方图的数据
        """
        # 计算快速和慢速EMA
        ema_fast = self.calculate_ema(data, fast)
        ema_slow = self.calculate_ema(data, slow)

        # 计算MACD线
        macd_line = ema_fast - ema_slow

        # 计算信号线
        signal_line = self.calculate_ema(macd_line, signal)

        # 计算直方图
        histogram = macd_line - signal_line

        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    def calculate_rsi(self, data, window=14):
        """
        计算相对强弱指数(RSI)

        Args:
            data (pd.Series): 价格数据
            window (int): 窗口大小

        Returns:
            pd.Series: RSI值
        """
        # 计算价格变化
        delta = data.diff()

        # 分离涨跌
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

        # 计算RSI
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_bollinger_bands(self, data, window=20, num_std=2):
        """
        计算布林带

        Args:
            data (pd.Series): 价格数据
            window (int): 窗口大小
            num_std (int): 标准差倍数

        Returns:
            dict: 包含中轨、上轨和下轨的数据
        """
        # 计算中轨(SMA)
        middle = self.calculate_sma(data, window)

        # 计算标准差
        std = data.rolling(window=window).std()

        # 计算上轨和下轨
        upper = middle + (std * num_std)
        lower = middle - (std * num_std)

        return {
            'middle': middle,
            'upper': upper,
            'lower': lower
        }

    def calculate_stochastic(self, high, low, close, k_window=14, d_window=3):
        """
        计算随机指标(KD)

        Args:
            high (pd.Series): 最高价
            low (pd.Series): 最低价
            close (pd.Series): 收盘价
            k_window (int): K值窗口大小
            d_window (int): D值窗口大小

        Returns:
            dict: 包含K值和D值的数据
        """
        # 计算最高价和最低价的滚动窗口最小值和最大值
        lowest_low = low.rolling(window=k_window).min()
        highest_high = high.rolling(window=k_window).max()

        # 计算K值
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))

        # 计算D值
        d_percent = k_percent.rolling(window=d_window).mean()

        return {
            'k': k_percent,
            'd': d_percent
        }

    def calculate_williams_r(self, high, low, close, window=14):
        """
        计算威廉指标(%R)

        Args:
            high (pd.Series): 最高价
            low (pd.Series): 最低价
            close (pd.Series): 收盘价
            window (int): 窗口大小

        Returns:
            pd.Series: %R值
        """
        # 计算最高价和最低价的滚动窗口最小值和最大值
        highest_high = high.rolling(window=window).max()
        lowest_low = low.rolling(window=window).min()

        # 计算威廉指标
        wr = -100 * (highest_high - close) / (highest_high - lowest_low)

        return wr

    def calculate_cci(self, high, low, close, window=20):
        """
        计算商品通道指数(CCI)

        Args:
            high (pd.Series): 最高价
            low (pd.Series): 最低价
            close (pd.Series): 收盘价
            window (int): 窗口大小

        Returns:
            pd.Series: CCI值
        """
        # 计算典型价格
        tp = (high + low + close) / 3

        # 计算典型价格的移动平均
        sma_tp = tp.rolling(window=window).mean()

        # 计算平均绝对偏差
        mad = tp.rolling(window=window).apply(lambda x: np.abs(x - x.mean()).mean())

        # 计算CCI
        cci = (tp - sma_tp) / (0.015 * mad)

        return cci

    def calculate_adx(self, high, low, close, window=14):
        """
        计算平均趋向指数(ADX)

        Args:
            high (pd.Series): 最高价
            low (pd.Series): 最低价
            close (pd.Series): 收盘价
            window (int): 窗口大小

        Returns:
            dict: 包含+DI、-DI和ADX的数据
        """
        # 计算价格变动
        up_move = high.diff()
        down_move = low.diff()

        # 计算真实波幅(TR)
        tr = pd.DataFrame({
            'hl': high - low,
            'hc': abs(high - close.shift(1)),
            'lc': abs(low - close.shift(1))
        }).max(axis=1)

        # 计算+DM和-DM
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        # 计算平滑的+DI、-DI和DX
        plus_di = 100 * (pd.Series(plus_dm).rolling(window=window).sum() / tr.rolling(window=window).sum())
        minus_di = 100 * (pd.Series(minus_dm).rolling(window=window).sum() / tr.rolling(window=window).sum())

        # 计算DX
        dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))

        # 计算ADX
        adx = dx.rolling(window=window).mean()

        return {
            'plus_di': plus_di,
            'minus_di': minus_di,
            'adx': adx
        }

    def calculate_obv(self, close, volume):
        """
        计算能量潮指标(OBV)

        Args:
            close (pd.Series): 收盘价
            volume (pd.Series): 交易量

        Returns:
            pd.Series: OBV值
        """
        # 计算价格变化方向
        price_change = close.diff()

        # 计算OBV
        obv = np.where(price_change > 0, volume, 
                      np.where(price_change < 0, -volume, 0)).cumsum()

        return pd.Series(obv, index=close.index)

    def calculate_mfi(self, high, low, close, volume, window=14):
        """
        计算资金流量指标(MFI)

        Args:
            high (pd.Series): 最高价
            low (pd.Series): 最低价
            close (pd.Series): 收盘价
            volume (pd.Series): 交易量
            window (int): 窗口大小

        Returns:
            pd.Series: MFI值
        """
        # 计算典型价格
        tp = (high + low + close) / 3

        # 计算资金流量
        money_flow = tp * volume

        # 计算正负资金流量
        positive_flow = money_flow.where(tp > tp.shift(1), 0).rolling(window=window).sum()
        negative_flow = money_flow.where(tp < tp.shift(1), 0).rolling(window=window).sum()

        # 计算MFI
        mfi = 100 - (100 / (1 + positive_flow / negative_flow))

        return mfi

    def calculate_indicators(self, data, high_col='high', low_col='low', 
                            close_col='close', volume_col='volume'):
        """
        计算所有技术指标

        Args:
            data (pd.DataFrame): 包含OHLCV数据的DataFrame
            high_col (str): 最高价列名
            low_col (str): 最低价列名
            close_col (str): 收盘价列名
            volume_col (str): 成交量列名

        Returns:
            dict: 包含所有技术指标的数据
        """
        try:
            # 提取必要的数据列
            high = data[high_col]
            low = data[low_col]
            close = data[close_col]
            volume = data.get(volume_col, pd.Series(1, index=data.index))

            # 计算各种指标
            indicators = {}

            # 移动平均线
            indicators['sma_5'] = self.calculate_sma(close, 5)
            indicators['sma_10'] = self.calculate_sma(close, 10)
            indicators['sma_20'] = self.calculate_sma(close, 20)
            indicators['sma_30'] = self.calculate_sma(close, 30)
            indicators['sma_60'] = self.calculate_sma(close, 60)

            indicators['ema_5'] = self.calculate_ema(close, 5)
            indicators['ema_10'] = self.calculate_ema(close, 10)
            indicators['ema_20'] = self.calculate_ema(close, 20)
            indicators['ema_30'] = self.calculate_ema(close, 30)
            indicators['ema_60'] = self.calculate_ema(close, 60)

            # MACD
            indicators['macd'] = self.calculate_macd(close)

            # RSI
            indicators['rsi'] = self.calculate_rsi(close)

            # 布林带
            indicators['bollinger_bands'] = self.calculate_bollinger_bands(close)

            # 随机指标
            indicators['stochastic'] = self.calculate_stochastic(high, low, close)

            # 威廉指标
            indicators['williams_r'] = self.calculate_williams_r(high, low, close)

            # CCI
            indicators['cci'] = self.calculate_cci(high, low, close)

            # ADX
            indicators['adx'] = self.calculate_adx(high, low, close)

            # OBV
            indicators['obv'] = self.calculate_obv(close, volume)

            # MFI
            indicators['mfi'] = self.calculate_mfi(high, low, close, volume)

            self.logger.info("技术指标计算完成")
            return indicators

        except Exception as e:
            self.logger.error(f"计算技术指标失败: {str(e)}")
            return {}

    def generate_signals(self, data, indicators):
        """
        基于技术指标生成交易信号

        Args:
            data (pd.DataFrame): 原始数据
            indicators (dict): 技术指标数据

        Returns:
            pd.DataFrame: 包含交易信号的DataFrame
        """
        try:
            # 创建信号DataFrame
            signals = pd.DataFrame(index=data.index)

            # 初始化信号列
            signals['signal'] = 0  # 0: 观望, 1: 买入, -1: 卖出

            # 移动平均线信号
            # 短期均线上穿长期均线 - 买入信号
            signals['ma_cross'] = np.where(
                (indicators['sma_5'] > indicators['sma_20']) & 
                (indicators['sma_5'].shift(1) <= indicators['sma_20'].shift(1)), 1, 0)

            # 短期均线下穿长期均线 - 卖出信号
            signals['ma_cross'] = np.where(
                (indicators['sma_5'] < indicators['sma_20']) & 
                (indicators['sma_5'].shift(1) >= indicators['sma_20'].shift(1)), -1, signals['ma_cross'])

            # MACD信号
            # MACD线上穿信号线 - 买入信号
            signals['macd_cross'] = np.where(
                (indicators['macd']['macd'] > indicators['macd']['signal']) & 
                (indicators['macd']['macd'].shift(1) <= indicators['macd']['signal'].shift(1)), 1, 0)

            # MACD线下穿信号线 - 卖出信号
            signals['macd_cross'] = np.where(
                (indicators['macd']['macd'] < indicators['macd']['signal']) & 
                (indicators['macd']['macd'].shift(1) >= indicators['macd']['signal'].shift(1)), -1, signals['macd_cross'])

            # RSI信号
            # RSI超卖后回升 - 买入信号
            signals['rsi_oversold'] = np.where(
                (indicators['rsi'] < 30) & (indicators['rsi'].shift(1) >= 30), 1, 0)

            # RSI超买后回落 - 卖出信号
            signals['rsi_overbought'] = np.where(
                (indicators['rsi'] > 70) & (indicators['rsi'].shift(1) <= 70), -1, 0)

            # 布林带信号
            # 价格下轨反弹 - 买入信号
            signals['bb_lower'] = np.where(
                (data['close'] <= indicators['bollinger_bands']['lower']) & 
                (data['close'].shift(1) > indicators['bollinger_bands']['lower'].shift(1)), 1, 0)

            # 价格上轨回落 - 卖出信号
            signals['bb_upper'] = np.where(
                (data['close'] >= indicators['bollinger_bands']['upper']) & 
                (data['close'].shift(1) < indicators['bollinger_bands']['upper'].shift(1)), -1, 0)

            # 随机指标信号
            # K值上穿D值 - 买入信号
            signals['stochastic_cross'] = np.where(
                (indicators['stochastic']['k'] > indicators['stochastic']['d']) & 
                (indicators['stochastic']['k'].shift(1) <= indicators['stochastic']['d'].shift(1)), 1, 0)

            # K值下穿D值 - 卖出信号
            signals['stochastic_cross'] = np.where(
                (indicators['stochastic']['k'] < indicators['stochastic']['d']) & 
                (indicators['stochastic']['k'].shift(1) >= indicators['stochastic']['d'].shift(1)), -1, signals['stochastic_cross'])

            # CCI信号
            # CCI从-100以下回升 - 买入信号
            signals['cci_oversold'] = np.where(
                (indicators['cci'] > -100) & (indicators['cci'].shift(1) <= -100), 1, 0)

            # CCI从+100以上回落 - 卖出信号
            signals['cci_overbought'] = np.where(
                (indicators['cci'] < 100) & (indicators['cci'].shift(1) >= 100), -1, 0)

            # ADX信号
            # ADX > 25 且 +DI > -DI - 趋势信号
            signals['adx_trend'] = np.where(
                (indicators['adx']['adx'] > 25) & 
                (indicators['adx']['plus_di'] > indicators['adx']['minus_di']), 1, 0)

            signals['adx_trend'] = np.where(
                (indicators['adx']['adx'] > 25) & 
                (indicators['adx']['plus_di'] < indicators['adx']['minus_di']), -1, signals['adx_trend'])

            # OBV信号
            # OBV突破移动平均线 - 买入信号
            signals['obv_ma'] = np.where(
                (indicators['obv'] > self.calculate_sma(indicators['obv'], 20)) & 
                (indicators['obv'].shift(1) <= self.calculate_sma(indicators['obv'], 20).shift(1)), 1, 0)

            # OBV跌破移动平均线 - 卖出信号
            signals['obv_ma'] = np.where(
                (indicators['obv'] < self.calculate_sma(indicators['obv'], 20)) & 
                (indicators['obv'].shift(1) >= self.calculate_sma(indicators['obv'], 20).shift(1)), -1, signals['obv_ma'])

            # MFI信号
            # MFI超卖后回升 - 买入信号
            signals['mfi_oversold'] = np.where(
                (indicators['mfi'] < 20) & (indicators['mfi'].shift(1) >= 20), 1, 0)

            # MFI超买后回落 - 卖出信号
            signals['mfi_overbought'] = np.where(
                (indicators['mfi'] > 80) & (indicators['mfi'].shift(1) <= 80), -1, 0)

            # 综合信号
            # 计算买入信号数量
            buy_signals = (
                signals['ma_cross'] + 
                signals['macd_cross'] + 
                signals['rsi_oversold'] + 
                signals['bb_lower'] + 
                signals['stochastic_cross'] + 
                signals['cci_oversold'] + 
                signals['adx_trend'] + 
                signals['obv_ma'] + 
                signals['mfi_oversold']
            )

            # 计算卖出信号数量
            sell_signals = (
                signals['ma_cross'] * -1 + 
                signals['macd_cross'] * -1 + 
                signals['rsi_overbought'] * -1 + 
                signals['bb_upper'] * -1 + 
                signals['stochastic_cross'] * -1 + 
                signals['cci_overbought'] * -1 + 
                signals['adx_trend'] * -1 + 
                signals['obv_ma'] * -1 + 
                signals['mfi_overbought'] * -1
            )

            # 生成综合信号
            # 买入信号: 至少3个买入指标
            signals['signal'] = np.where(buy_signals >= 3, 1, signals['signal'])

            # 卖出信号: 至少3个卖出指标
            signals['signal'] = np.where(sell_signals >= 3, -1, signals['signal'])

            # 观望信号
            signals['signal'] = np.where(signals['signal'] == 0, 0, signals['signal'])

            # 添加信号描述
            signals['signal_desc'] = signals['signal'].map({
                1: '买入',
                -1: '卖出',
                0: '观望'
            })

            self.logger.info("交易信号生成完成")
            return signals

        except Exception as e:
            self.logger.error(f"生成交易信号失败: {str(e)}")
            return pd.DataFrame()

    def analyze_fund(self, fund_data):
        """
        分析单个基金数据

        Args:
            fund_data (pd.DataFrame): 基金数据

        Returns:
            dict: 分析结果
        """
        try:
            # 确保数据包含必要的列
            required_columns = ['date', 'nav', 'high', 'low', 'close', 'volume']
            if not all(col in fund_data.columns for col in required_columns):
                self.logger.error(f"基金数据缺少必要的列: {required_columns}")
                return {}

            # 设置日期为索引
            fund_data = fund_data.set_index('date')

            # 计算技术指标
            indicators = self.calculate_indicators(fund_data)

            # 生成交易信号
            signals = self.generate_signals(fund_data, indicators)

            # 获取最新的信号
            latest_signal = signals.iloc[-1] if not signals.empty else {}

            # 计算各项指标的最新值
            latest_indicators = {}
            for indicator_name, indicator_data in indicators.items():
                if isinstance(indicator_data, dict):
                    # 处理嵌套字典，如MACD、布林带等
                    latest_indicators[indicator_name] = {}
                    for sub_name, sub_data in indicator_data.items():
                        if not sub_data.empty:
                            latest_indicators[indicator_name][sub_name] = sub_data.iloc[-1]
                elif not indicator_data.empty:
                    latest_indicators[indicator_name] = indicator_data.iloc[-1]

            # 构建分析结果
            analysis_result = {
                'fund_code': fund_data.get('code', '未知'),
                'fund_name': fund_data.get('name', '未知'),
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'latest_nav': fund_data['nav'].iloc[-1] if 'nav' in fund_data.columns else None,
                'latest_close': fund_data['close'].iloc[-1] if 'close' in fund_data.columns else None,
                'latest_signal': latest_signal.get('signal_desc', '观望'),
                'signal_strength': abs(latest_signal.get('signal', 0)),
                'indicators': latest_indicators,
                'signals_history': signals['signal_desc'].to_dict() if not signals.empty else {}
            }

            return analysis_result

        except Exception as e:
            self.logger.error(f"分析基金数据失败: {str(e)}")
            return {}

    def analyze_multiple_funds(self, funds_data):
        """
        分析多个基金数据

        Args:
            funds_data (pd.DataFrame): 多个基金数据

        Returns:
            list: 分析结果列表
        """
        try:
            # 按基金代码分组
            grouped = funds_data.groupby('code')

            # 分析每个基金
            analysis_results = []
            for fund_code, fund_data in grouped:
                result = self.analyze_fund(fund_data)
                if result:
                    analysis_results.append(result)

            # 按信号类型分组统计
            buy_count = sum(1 for r in analysis_results if r['latest_signal'] == '买入')
            sell_count = sum(1 for r in analysis_results if r['latest_signal'] == '卖出')
            hold_count = sum(1 for r in analysis_results if r['latest_signal'] == '观望')

            # 添加统计信息
            summary = {
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_funds': len(analysis_results),
                'buy_signal_count': buy_count,
                'sell_signal_count': sell_count,
                'hold_signal_count': hold_count,
                'buy_signal_ratio': buy_count / len(analysis_results) if analysis_results else 0,
                'sell_signal_ratio': sell_count / len(analysis_results) if analysis_results else 0,
                'hold_signal_ratio': hold_count / len(analysis_results) if analysis_results else 0
            }

            return {
                'summary': summary,
                'funds_analysis': analysis_results
            }

        except Exception as e:
            self.logger.error(f"分析多个基金数据失败: {str(e)}")
            return {}

    def save_analysis_results(self, results, output_file):
        """
        保存分析结果

        Args:
            results (dict): 分析结果
            output_file (str): 输出文件路径
        """
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            # 保存为JSON
            import json
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

            self.logger.info(f"分析结果已保存到: {output_file}")

        except Exception as e:
            self.logger.error(f"保存分析结果失败: {str(e)}")


def main():
    """主函数"""
    # 创建技术分析器实例
    analyzer = TechnicalAnalyzer()

    # 示例数据
    data = pd.DataFrame({
        'date': pd.date_range(start='2023-01-01', end='2023-06-30'),
        'open': np.random.uniform(1, 2, 151),
        'high': np.random.uniform(1.5, 2.5, 151),
        'low': np.random.uniform(0.5, 1.5, 151),
        'close': np.random.uniform(1, 2, 151),
        'volume': np.random.randint(1000, 10000, 151)
    })

    # 计算技术指标
    indicators = analyzer.calculate_indicators(data)

    # 生成交易信号
    signals = analyzer.generate_signals(data, indicators)

    # 打印最新信号
    if not signals.empty:
        latest_signal = signals.iloc[-1]
        print(f"最新信号: {latest_signal['signal_desc']}")

    # 分析单个基金
    fund_result = analyzer.analyze_fund(data)
    print(f"基金分析结果: {fund_result}")

    # 保存结果
    analyzer.save_analysis_results({'indicators': indicators, 'signals': signals}, 'analysis_results.json')


if __name__ == '__main__':
    main()
