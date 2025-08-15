#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
中期指标计算模块
"""

import os
import json
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple

from ..utils.config import DATA_DIR, INDICATORS_CONFIG

logger = logging.getLogger(__name__)

class MidTermIndicators:
    """中期指标计算类"""

    def __init__(self, fund_data: List[Dict[str, Any]]):
        """
        初始化中期指标计算器

        Args:
            fund_data: 基金数据列表
        """
        self.fund_data = fund_data
        self.config = INDICATORS_CONFIG.get('mid_term', {})
        self.ma_periods = self.config.get('ma_periods', [5, 10, 20])
        self.rsi_period = self.config.get('rsi_period', 9)
        self.macd_params = self.config.get('macd_params', {'fast': 6, 'slow': 13, 'signal': 5})

        self.output_dir = os.path.join(DATA_DIR, 'indicators', 'mid_term')
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        logger.info("中期指标计算器初始化完成")

    def _calculate_ma(self, prices: List[float], period: int) -> List[float]:
        """
        计算移动平均线

        Args:
            prices: 价格列表
            period: 周期

        Returns:
            移动平均线值列表
        """
        if len(prices) < period:
            return [np.nan] * len(prices)

        ma = []
        for i in range(len(prices)):
            if i < period - 1:
                ma.append(np.nan)
            else:
                ma.append(np.mean(prices[i - period + 1:i + 1]))

        return ma

    def _calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """
        计算指数移动平均线

        Args:
            prices: 价格列表
            period: 周期

        Returns:
            指数移动平均线值列表
        """
        if len(prices) < period:
            return [np.nan] * len(prices)

        ema = [np.nan] * (period - 1)
        ema.append(np.mean(prices[:period]))

        multiplier = 2 / (period + 1)

        for i in range(period, len(prices)):
            ema.append((prices[i] - ema[i-1]) * multiplier + ema[i-1])

        return ema

    def _calculate_rsi(self, prices: List[float], period: int) -> List[float]:
        """
        计算相对强弱指数

        Args:
            prices: 价格列表
            period: 周期

        Returns:
            RSI值列表
        """
        if len(prices) <= period:
            return [np.nan] * len(prices)

        # 计算价格变化
        deltas = np.diff(prices)
        seed = deltas[:period+1]

        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period

        if down == 0:
            rs = 100
        else:
            rs = up / down

        rsi = [100 - (100 / (1 + rs))]

        for i in range(period, len(deltas)):
            delta = deltas[i]

            if delta > 0:
                upval = delta
                downval = 0
            else:
                upval = 0
                downval = -delta

            up = (up * (period - 1) + upval) / period
            down = (down * (period - 1) + downval) / period

            if down == 0:
                rs = 100
            else:
                rs = up / down

            rsi.append(100 - (100 / (1 + rs)))

        return [np.nan] * (period) + rsi

    def _calculate_macd(self, prices: List[float], fast: int, slow: int, signal: int) -> Tuple[List[float], List[float], List[float]]:
        """
        计算MACD指标

        Args:
            prices: 价格列表
            fast: 快线周期
            slow: 慢线周期
            signal: 信号线周期

        Returns:
            (MACD线, 信号线, 柱状图)
        """
        if len(prices) < slow:
            nan_list = [np.nan] * len(prices)
            return nan_list, nan_list, nan_list

        # 计算快线和慢线的EMA
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)

        # 计算MACD线
        macd_line = []
        for i in range(len(prices)):
            if np.isnan(ema_fast[i]) or np.isnan(ema_slow[i]):
                macd_line.append(np.nan)
            else:
                macd_line.append(ema_fast[i] - ema_slow[i])

        # 计算信号线
        signal_line = self._calculate_ema(macd_line, signal)

        # 计算柱状图
        histogram = []
        for i in range(len(prices)):
            if np.isnan(macd_line[i]) or np.isnan(signal_line[i]):
                histogram.append(np.nan)
            else:
                histogram.append(macd_line[i] - signal_line[i])

        return macd_line, signal_line, histogram

    def _calculate_kdj(self, high_prices: List[float], low_prices: List[float], close_prices: List[float], 
                      k_period: int = 9, d_period: int = 3, j_period: int = 3) -> Tuple[List[float], List[float], List[float]]:
        """
        计算KDJ指标

        Args:
            high_prices: 最高价列表
            low_prices: 最低价列表
            close_prices: 收盘价列表
            k_period: K线周期
            d_period: D线周期
            j_period: J线周期

        Returns:
            (K值, D值, J值)
        """
        if len(close_prices) < k_period:
            nan_list = [np.nan] * len(close_prices)
            return nan_list, nan_list, nan_list

        k_values = [np.nan] * (k_period - 1)
        d_values = [np.nan] * (k_period - 1)
        j_values = [np.nan] * (k_period - 1)

        # 计算初始K值
        rsv = (close_prices[k_period - 1] - min(low_prices[:k_period])) / (max(high_prices[:k_period]) - min(low_prices[:k_period])) * 100
        k_values.append(50 * (1 / k_period) + rsv * ((k_period - 1) / k_period))

        # 计算后续K值
        for i in range(k_period, len(close_prices)):
            high = max(high_prices[i - k_period + 1:i + 1])
            low = min(low_prices[i - k_period + 1:i + 1])
            rsv = (close_prices[i] - low) / (high - low) * 100
            k_values.append(rsv * (1 / k_period) + k_values[i - 1] * ((k_period - 1) / k_period))

        # 计算D值
        for i in range(k_period - 1, len(k_values)):
            if i < k_period - 1 + d_period - 1:
                d_values.append(np.nan)
            else:
                d_values.append(sum(k_values[i - d_period + 1:i + 1]) / d_period)

        # 计算J值
        for i in range(len(k_values)):
            if i < len(d_values) or np.isnan(d_values[i]):
                j_values.append(np.nan)
            else:
                j_values.append(3 * k_values[i] - 2 * d_values[i])

        return k_values, d_values, j_values

    def _calculate_cci(self, high_prices: List[float], low_prices: List[float], close_prices: List[float], 
                      period: int = 14) -> List[float]:
        """
        计算CCI指标

        Args:
            high_prices: 最高价列表
            low_prices: 最低价列表
            close_prices: 收盘价列表
            period: 周期

        Returns:
            CCI值列表
        """
        if len(close_prices) < period:
            return [np.nan] * len(close_prices)

        cci_values = [np.nan] * (period - 1)

        for i in range(period - 1, len(close_prices)):
            high = high_prices[i - period + 1:i + 1]
            low = low_prices[i - period + 1:i + 1]
            close = close_prices[i - period + 1:i + 1]

            tp = [(h + l + c) / 3 for h, l, c in zip(high, low, close)]
            sma_tp = sum(tp) / period

            md = sum([abs(x - sma_tp) for x in tp]) / period

            if md == 0:
                cci_values.append(0)
            else:
                cci_values.append((tp[-1] - sma_tp) / (0.015 * md))

        return cci_values

    def _calculate_indicators_for_fund(self, fund: Dict[str, Any]) -> Dict[str, Any]:
        """
        为单个基金计算指标

        Args:
            fund: 基金数据

        Returns:
            包含指标的基金数据
        """
        fund_code = fund['code']
        fund_name = fund['name']

        logger.debug(f"计算基金 {fund_name}({fund_code}) 的中期指标...")

        # 获取历史净值数据
        nav_history = fund.get('nav_history', [])
        if not nav_history:
            logger.warning(f"基金 {fund_name}({fund_code}) 没有历史净值数据，跳过计算指标")
            return fund

        # 提取净值数据
        nav_values = []
        for item in nav_history:
            try:
                nav = float(item.get('net_asset_value', 0))
                if nav > 0:
                    nav_values.append(nav)
            except (ValueError, TypeError):
                continue

        if len(nav_values) < 20:  # 至少需要20个数据点
            logger.warning(f"基金 {fund_name}({fund_code}) 历史净值数据不足，跳过计算指标")
            return fund

        # 计算移动平均线
        ma_indicators = {}
        for period in self.ma_periods:
            ma_values = self._calculate_ma(nav_values, period)
            ma_indicators[f'ma_{period}'] = ma_values[-1] if not np.isnan(ma_values[-1]) else None

        # 计算RSI
        rsi_values = self._calculate_rsi(nav_values, self.rsi_period)
        rsi = rsi_values[-1] if not np.isnan(rsi_values[-1]) else None

        # 计算MACD
        fast = self.macd_params.get('fast', 6)
        slow = self.macd_params.get('slow', 13)
        signal = self.macd_params.get('signal', 5)

        macd_line, signal_line, histogram = self._calculate_macd(nav_values, fast, slow, signal)
        macd = macd_line[-1] if not np.isnan(macd_line[-1]) else None
        macd_signal = signal_line[-1] if not np.isnan(signal_line[-1]) else None
        macd_histogram = histogram[-1] if not np.isnan(histogram[-1]) else None

        # 计算KDJ（使用净值作为最高价、最低价和收盘价）
        k_values, d_values, j_values = self._calculate_kdj(nav_values, nav_values, nav_values)
        k = k_values[-1] if not np.isnan(k_values[-1]) else None
        d = d_values[-1] if not np.isnan(d_values[-1]) else None
        j = j_values[-1] if not np.isnan(j_values[-1]) else None

        # 计算CCI
        cci_values = self._calculate_cci(nav_values, nav_values, nav_values)
        cci = cci_values[-1] if not np.isnan(cci_values[-1]) else None

        # 计算趋势信号
        trend_signal = 'neutral'
        if ma_indicators.get('ma_5') and ma_indicators.get('ma_10') and ma_indicators.get('ma_20'):
            if nav_values[-1] > ma_indicators['ma_5'] > ma_indicators['ma_10'] > ma_indicators['ma_20']:
                trend_signal = 'bullish'
            elif nav_values[-1] < ma_indicators['ma_5'] < ma_indicators['ma_10'] < ma_indicators['ma_20']:
                trend_signal = 'bearish'

        # 计算动量信号
        momentum_signal = 'neutral'
        if rsi is not None:
            if rsi > 70:
                momentum_signal = 'overbought'
            elif rsi < 30:
                momentum_signal = 'oversold'

        # 计算KDJ信号
        kdj_signal = 'neutral'
        if k is not None and d is not None and j is not None:
            if k > d and j > k:
                kdj_signal = 'bullish'
            elif k < d and j < k:
                kdj_signal = 'bearish'

        # 计算CCI信号
        cci_signal = 'neutral'
        if cci is not None:
            if cci > 100:
                cci_signal = 'overbought'
            elif cci < -100:
                cci_signal = 'oversold'

        # 计算MACD信号
        macd_signal_type = 'neutral'
        if macd is not None and macd_signal is not None and macd_histogram is not None:
            if macd > macd_signal and macd_histogram > 0:
                macd_signal_type = 'bullish'
            elif macd < macd_signal and macd_histogram < 0:
                macd_signal_type = 'bearish'

        # 计算综合信号
        bullish_count = sum([
            1 if trend_signal == 'bullish' else 0,
            1 if momentum_signal == 'oversold' else 0,
            1 if kdj_signal == 'bullish' else 0,
            1 if cci_signal == 'oversold' else 0,
            1 if macd_signal_type == 'bullish' else 0
        ])

        bearish_count = sum([
            1 if trend_signal == 'bearish' else 0,
            1 if momentum_signal == 'overbought' else 0,
            1 if kdj_signal == 'bearish' else 0,
            1 if cci_signal == 'overbought' else 0,
            1 if macd_signal_type == 'bearish' else 0
        ])

        if bullish_count > bearish_count:
            combined_signal = 'bullish'
        elif bearish_count > bullish_count:
            combined_signal = 'bearish'
        else:
            combined_signal = 'neutral'

        # 添加指标到基金数据
        fund['mid_term_indicators'] = {
            'ma': ma_indicators,
            'rsi': rsi,
            'macd': {
                'line': macd,
                'signal': macd_signal,
                'histogram': macd_histogram
            },
            'kdj': {
                'k': k,
                'd': d,
                'j': j
            },
            'cci': cci,
            'signals': {
                'trend': trend_signal,
                'momentum': momentum_signal,
                'kdj': kdj_signal,
                'cci': cci_signal,
                'macd': macd_signal_type,
                'combined': combined_signal
            },
            'calculate_time': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        return fund

    def calculate(self) -> List[Dict[str, Any]]:
        """
        计算所有基金的中期指标

        Returns:
            包含中期指标的基金数据列表
        """
        logger.info("开始计算所有基金的中期指标...")

        # 使用多线程计算指标
        from ..utils.thread_pool import run_with_thread_pool

        # 准备任务列表
        tasks = [{'fund': fund} for fund in self.fund_data]

        # 执行任务
        funds_with_indicators = run_with_thread_pool(
            lambda kwargs: self._calculate_indicators_for_fund(kwargs['fund']),
            tasks
        )

        # 保存指标数据
        self.save_indicators_data(funds_with_indicators)

        logger.info(f"成功计算 {len(funds_with_indicators)} 只基金的中期指标")
        return funds_with_indicators

    def save_indicators_data(self, fund_data: List[Dict[str, Any]]) -> None:
        """
        保存指标数据

        Args:
            fund_data: 包含指标的基金数据列表
        """
        if not fund_data:
            logger.warning("基金数据列表为空，不保存指标数据")
            return

        # 按日期保存
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        filename = os.path.join(self.output_dir, f'mid_term_indicators_{today}.json')

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(fund_data, f, ensure_ascii=False, indent=2)
            logger.info(f"中期指标数据已保存到 {filename}")
        except Exception as e:
            logger.error(f"保存中期指标数据失败: {str(e)}", exc_info=True)
