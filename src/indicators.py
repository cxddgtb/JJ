#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
指标计算模块
计算各种基金技术指标和基本面指标
"""

import os
import re
import json
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union

from config import (
    OUTPUT_DIR, PROCESSED_DATA_DIR, ANALYSIS_RESULTS_DIR, INDICATORS_CONFIG,
    FUND_TYPES, LOG_CONFIG
)

# 设置日志
logging.basicConfig(
    level=LOG_CONFIG['level'],
    format=LOG_CONFIG['format'],
    handlers=[
        logging.FileHandler(LOG_CONFIG['file']),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """技术指标计算类"""

    @staticmethod
    def ma(data: pd.Series, period: int = 5) -> pd.Series:
        """
        计算移动平均线

        Args:
            data: 价格数据
            period: 周期

        Returns:
            MA指标
        """
        return data.rolling(window=period).mean()

    @staticmethod
    def ema(data: pd.Series, period: int = 12) -> pd.Series:
        """
        计算指数移动平均线

        Args:
            data: 价格数据
            period: 周期

        Returns:
            EMA指标
        """
        return data.ewm(span=period, adjust=False).mean()

    @staticmethod
    def macd(data: pd.Series, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict[str, pd.Series]:
        """
        计算MACD指标

        Args:
            data: 价格数据
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期

        Returns:
            MACD指标字典
        """
        ema_fast = TechnicalIndicators.ema(data, fast_period)
        ema_slow = TechnicalIndicators.ema(data, slow_period)
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema(macd_line, signal_period)
        histogram = macd_line - signal_line

        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """
        计算RSI指标

        Args:
            data: 价格数据
            period: 周期

        Returns:
            RSI指标
        """
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def kdj(high: pd.Series, low: pd.Series, close: pd.Series, 
            k_period: int = 9, d_period: int = 3, j_period: int = 3) -> Dict[str, pd.Series]:
        """
        计算KDJ指标

        Args:
            high: 最高价
            low: 最低价
            close: 收盘价
            k_period: K值周期
            d_period: D值周期
            j_period: J值周期

        Returns:
            KDJ指标字典
        """
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
        k = rsv.ewm(com=2).mean()
        d = k.ewm(com=2).mean()
        j = 3 * k - 2 * d

        return {
            'k': k,
            'd': d,
            'j': j
        }

    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, num_std: int = 2) -> Dict[str, pd.Series]:
        """
        计算布林带指标

        Args:
            data: 价格数据
            period: 周期
            num_std: 标准差倍数

        Returns:
            布林带指标字典
        """
        sma = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()

        upper_band = sma + (std * num_std)
        lower_band = sma - (std * num_std)

        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        }

    @staticmethod
    def wr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """
        计算威廉指标

        Args:
            high: 最高价
            low: 最低价
            close: 收盘价
            period: 周期

        Returns:
            WR指标
        """
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()

        wr = (highest_high - close) / (highest_high - lowest_low) * -100
        return wr

    @staticmethod
    def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
        """
        计算CCI指标

        Args:
            high: 最高价
            low: 最低价
            close: 收盘价
            period: 周期

        Returns:
            CCI指标
        """
        tp = (high + low + close) / 3
        sma = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(lambda x: np.fabs(x - x.mean()).mean())

        cci = (tp - sma) / (0.015 * mad)
        return cci

    @staticmethod
    def dmi(high: pd.Series, low: pd.Series, close: pd.Series, 
            period: int = 14, adx_period: int = 14) -> Dict[str, pd.Series]:
        """
        计算DMI指标

        Args:
            high: 最高价
            low: 最低价
            close: 收盘价
            period: 周期
            adx_period: ADX周期

        Returns:
            DMI指标字典
        """
        # 计算真实波幅TR
        tr1 = high - low
        tr2 = np.abs(high - close.shift(1))
        tr3 = np.abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # 计算方向移动
        plus_dm = high - high.shift(1)
        minus_dm = low.shift(1) - low

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        # 计算平滑后的TR、+DM、-DM
        tr_smooth = tr.ewm(com=period-1, adjust=False).mean()
        plus_dm_smooth = plus_dm.ewm(com=period-1, adjust=False).mean()
        minus_dm_smooth = minus_dm.ewm(com=period-1, adjust=False).mean()

        # 计算方向指标
        plus_di = 100 * (plus_dm_smooth / tr_smooth)
        minus_di = 100 * (minus_dm_smooth / tr_smooth)

        # 计算DX
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)

        # 计算ADX
        adx = dx.ewm(com=adx_period-1, adjust=False).mean()

        return {
            'plus_di': plus_di,
            'minus_di': minus_di,
            'adx': adx
        }

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        计算OBV指标

        Args:
            close: 收盘价
            volume: 成交量

        Returns:
            OBV指标
        """
        obv = np.where(close > close.shift(1), volume, 
                      np.where(close < close.shift(1), -volume, 0)).cumsum()
        return pd.Series(obv, index=close.index)


class FundamentalIndicators:
    """基本面指标计算类"""

    @staticmethod
    def ytd_return(nav: pd.Series, nav_date: pd.Series) -> float:
        """
        计算年初至今收益率

        Args:
            nav: 净值序列
            nav_date: 净值日期序列

        Returns:
            年初至今收益率
        """
        # 获取年初日期
        current_year = datetime.now().year
        start_date = f"{current_year}-01-01"

        # 找到年初对应的净值
        start_nav = nav[nav_date >= start_date].iloc[0] if not nav[nav_date >= start_date].empty else nav.iloc[0]
        end_nav = nav.iloc[-1]

        return (end_nav - start_nav) / start_nav

    @staticmethod
    def annualized_return(nav: pd.Series, nav_date: pd.Series, years: float) -> float:
        """
        计算年化收益率

        Args:
            nav: 净值序列
            nav_date: 净值日期序列
            years: 年数

        Returns:
            年化收益率
        """
        start_nav = nav.iloc[0]
        end_nav = nav.iloc[-1]

        return (end_nav / start_nav) ** (1 / years) - 1

    @staticmethod
    def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.03) -> float:
        """
        计算夏普比率

        Args:
            returns: 收益率序列
            risk_free_rate: 无风险利率

        Returns:
            夏普比率
        """
        excess_returns = returns - risk_free_rate / 252  # 日化无风险利率
        return np.sqrt(252) * excess_returns.mean() / excess_returns.std()

    @staticmethod
    def sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.03) -> float:
        """
        计算索提诺比率

        Args:
            returns: 收益率序列
            risk_free_rate: 无风险利率

        Returns:
            索提诺比率
        """
        excess_returns = returns - risk_free_rate / 252  # 日化无风险利率
        downside_returns = excess_returns[excess_returns < 0]

        if len(downside_returns) == 0:
            return float('inf')

        return np.sqrt(252) * excess_returns.mean() / downside_returns.std()

    @staticmethod
    def max_drawdown(nav: pd.Series) -> float:
        """
        计算最大回撤

        Args:
            nav: 净值序列

        Returns:
            最大回撤
        """
        cumulative = nav / nav.iloc[0]
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()

    @staticmethod
    def volatility(returns: pd.Series) -> float:
        """
        计算波动率

        Args:
            returns: 收益率序列

        Returns:
            波动率
        """
        return returns.std() * np.sqrt(252)

    @staticmethod
    def alpha_beta(returns: pd.Series, benchmark_returns: pd.Series) -> Dict[str, float]:
        """
        计算Alpha和Beta

        Args:
            returns: 基金收益率序列
            benchmark_returns: 基准收益率序列

        Returns:
            Alpha和Beta字典
        """
        # 确保长度一致
        min_len = min(len(returns), len(benchmark_returns))
        returns = returns.iloc[-min_len:]
        benchmark_returns = benchmark_returns.iloc[-min_len:]

        # 计算协方差和方差
        covariance = returns.cov(benchmark_returns)
        benchmark_variance = benchmark_returns.var()

        # 计算Beta
        beta = covariance / benchmark_variance if benchmark_variance != 0 else 0

        # 计算Alpha
        alpha = returns.mean() - beta * benchmark_returns.mean()

        return {
            'alpha': alpha * 252,  # 年化Alpha
            'beta': beta
        }

    @staticmethod
    def information_ratio(returns: pd.Series, benchmark_returns: pd.Series) -> float:
        """
        计算信息比率

        Args:
            returns: 基金收益率序列
            benchmark_returns: 基准收益率序列

        Returns:
            信息比率
        """
        # 确保长度一致
        min_len = min(len(returns), len(benchmark_returns))
        returns = returns.iloc[-min_len:]
        benchmark_returns = benchmark_returns.iloc[-min_len:]

        # 计算跟踪误差
        tracking_error = (returns - benchmark_returns).std()

        if tracking_error == 0:
            return 0

        # 计算信息比率
        return np.sqrt(252) * (returns - benchmark_returns).mean() / tracking_error


class VolumeIndicators:
    """成交量指标计算类"""

    @staticmethod
    def volume_ratio(volume: pd.Series, period: int = 20) -> pd.Series:
        """
        计算量比

        Args:
            volume: 成交量序列
            period: 周期

        Returns:
            量比序列
        """
        avg_volume = volume.rolling(window=period).mean()
        volume_ratio = volume / avg_volume
        return volume_ratio

    @staticmethod
    def volume_ma(volume: pd.Series, period: int = 5) -> pd.Series:
        """
        计算成交量移动平均

        Args:
            volume: 成交量序列
            period: 周期

        Returns:
            成交量移动平均序列
        """
        return volume.rolling(window=period).mean()

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        计算OBV指标

        Args:
            close: 收盘价序列
            volume: 成交量序列

        Returns:
            OBV序列
        """
        obv = np.where(close > close.shift(1), volume, 
                      np.where(close < close.shift(1), -volume, 0)).cumsum()
        return pd.Series(obv, index=close.index)

    @staticmethod
    def ad_line(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        计算AD线（累积/派发线）

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列
            volume: 成交量序列

        Returns:
            AD线序列
        """
        clv = ((close - low) - (high - close)) / (high - low)
        clv = clv.fillna(0)  # 处理除以0的情况
        ad = clv * volume
        return ad.cumsum()


class IndicatorCalculator:
    """指标计算器主类"""

    def __init__(self, fund_type: str = 'mixed'):
        """
        初始化指标计算器

        Args:
            fund_type: 基金类型
        """
        self.fund_type = fund_type
        self.technical_indicators = TechnicalIndicators()
        self.fundamental_indicators = FundamentalIndicators()
        self.volume_indicators = VolumeIndicators()

        # 创建输出目录
        self.indicators_output_dir = os.path.join(PROCESSED_DATA_DIR, 'indicators')
        os.makedirs(self.indicators_output_dir, exist_ok=True)

    def calculate_all_indicators(self, fund_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, Any]]:
        """
        计算所有基金的所有指标

        Args:
            fund_data: 基金数据字典

        Returns:
            所有指标结果字典
        """
        logger.info(f"开始计算{self.fund_type}基金的所有指标")

        all_results = {}

        for fund_code, data in fund_data.items():
            try:
                logger.info(f"正在计算{fund_code}的指标")

                # 确保数据包含必要的列
                required_columns = ['close', 'high', 'low', 'volume', 'amount']
                for col in required_columns:
                    if col not in data.columns:
                        logger.warning(f"{fund_code}缺少{col}列，跳过该基金")
                        continue

                # 计算技术指标
                technical_results = self._calculate_technical_indicators(data)

                # 计算基本面指标
                fundamental_results = self._calculate_fundamental_indicators(data)

                # 计算成交量指标
                volume_results = self._calculate_volume_indicators(data)

                # 合并结果
                all_results[fund_code] = {
                    'technical': technical_results,
                    'fundamental': fundamental_results,
                    'volume': volume_results
                }

                # 保存单个基金的指标结果
                self._save_single_fund_indicators(fund_code, all_results[fund_code])

            except Exception as e:
                logger.error(f"计算{fund_code}指标失败: {e}")
                continue

        # 保存所有指标的汇总结果
        self._save_all_indicators(all_results)

        return all_results

    def _calculate_technical_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        计算技术指标

        Args:
            data: 基金数据

        Returns:
            技术指标结果
        """
        results = {}

        try:
            # 计算移动平均线
            for period in [5, 10, 20, 30, 60]:
                results[f'MA_{period}'] = self.technical_indicators.ma(data['close'], period).iloc[-1]

            # 计算指数移动平均线
            for period in [5, 10, 20, 30, 60]:
                results[f'EMA_{period}'] = self.technical_indicators.ema(data['close'], period).iloc[-1]

            # 计算MACD
            macd = self.technical_indicators.macd(data['close'])
            results['MACD'] = macd['macd'].iloc[-1]
            results['MACD_Signal'] = macd['signal'].iloc[-1]
            results['MACD_Histogram'] = macd['histogram'].iloc[-1]

            # 计算RSI
            for period in [6, 12, 24]:
                results[f'RSI_{period}'] = self.technical_indicators.rsi(data['close'], period).iloc[-1]

            # 计算KDJ
            kdj = self.technical_indicators.kdj(data['high'], data['low'], data['close'])
            results['KDJ_K'] = kdj['k'].iloc[-1]
            results['KDJ_D'] = kdj['d'].iloc[-1]
            results['KDJ_J'] = kdj['j'].iloc[-1]

            # 计算布林带
            bb = self.technical_indicators.bollinger_bands(data['close'])
            results['BB_Upper'] = bb['upper'].iloc[-1]
            results['BB_Middle'] = bb['middle'].iloc[-1]
            results['BB_Lower'] = bb['lower'].iloc[-1]
            results['BB_Width'] = results['BB_Upper'] - results['BB_Lower']

            # 计算威廉指标
            results['WR_14'] = self.technical_indicators.wr(data['high'], data['low'], data['close']).iloc[-1]

            # 计算CCI
            results['CCI_20'] = self.technical_indicators.cci(data['high'], data['low'], data['close']).iloc[-1]

            # 计算DMI
            dmi = self.technical_indicators.dmi(data['high'], data['low'], data['close'])
            results['DMI_Plus_DI'] = dmi['plus_di'].iloc[-1]
            results['DMI_Minus_DI'] = dmi['minus_di'].iloc[-1]
            results['DMI_ADX'] = dmi['adx'].iloc[-1]

            # 计算OBV
            results['OBV'] = self.technical_indicators.obv(data['close'], data['volume']).iloc[-1]

            # 计算价格变动
            results['Price_Change'] = data['close'].iloc[-1] - data['close'].iloc[-2]
            results['Price_Change_Percent'] = results['Price_Change'] / data['close'].iloc[-2] * 100

            # 计算价格趋势
            results['Price_Trend'] = 1 if results['Price_Change'] > 0 else -1

            # 计算价格位置（相对于布林带）
            if results['BB_Width'] > 0:
                results['BB_Position'] = (data['close'].iloc[-1] - results['BB_Lower']) / results['BB_Width']
            else:
                results['BB_Position'] = 0.5

        except Exception as e:
            logger.error(f"计算技术指标失败: {e}")

        return results

    def _calculate_fundamental_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        计算基本面指标

        Args:
            data: 基金数据

        Returns:
            基本面指标结果
        """
        results = {}

        try:
            # 计算收益率
            returns = data['close'].pct_change().dropna()

            # 计算年初至今收益率
            results['YTD_Return'] = self.fundamental_indicators.ytd_return(data['close'], data.index)

            # 计算年化收益率
            results['1Y_Return'] = self.fundamental_indicators.annualized_return(data['close'], data.index, 1)
            results['3Y_Return'] = self.fundamental_indicators.annualized_return(data['close'], data.index, 3)
            results['5Y_Return'] = self.fundamental_indicators.annualized_return(data['close'], data.index, 5)

            # 计算夏普比率
            results['Sharpe_Ratio'] = self.fundamental_indicators.sharpe_ratio(returns)

            # 计算索提诺比率
            results['Sortino_Ratio'] = self.fundamental_indicators.sortino_ratio(returns)

            # 计算最大回撤
            results['Max_Drawdown'] = self.fundamental_indicators.max_drawdown(data['close'])

            # 计算波动率
            results['Volatility'] = self.fundamental_indicators.volatility(returns)

            # 计算Alpha和Beta（使用沪深300作为基准）
            try:
                # 这里应该加载基准数据，简化处理
                benchmark_returns = pd.Series(0.0001, index=returns.index)  # 假设基准收益率为0.01%
                alpha_beta = self.fundamental_indicators.alpha_beta(returns, benchmark_returns)
                results['Alpha'] = alpha_beta['alpha']
                results['Beta'] = alpha_beta['beta']
            except:
                results['Alpha'] = 0
                results['Beta'] = 1

            # 计算信息比率
            try:
                # 这里应该加载基准数据，简化处理
                benchmark_returns = pd.Series(0.0001, index=returns.index)  # 假设基准收益率为0.01%
                results['Information_Ratio'] = self.fundamental_indicators.information_ratio(returns, benchmark_returns)
            except:
                results['Information_Ratio'] = 0

            # 计算基金规模（这里简化处理）
            results['Fund_Scale'] = 100000000  # 假设规模为1亿

            # 计算基金评级（这里简化处理）
            results['Fund_Rating'] = 3  # 假设评级为3星

        except Exception as e:
            logger.error(f"计算基本面指标失败: {e}")

        return results

    def _calculate_volume_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        计算成交量指标

        Args:
            data: 基金数据

        Returns:
            成交量指标结果
        """
        results = {}

        try:
            # 计算量比
            for period in [5, 10, 20]:
                results[f'Volume_Ratio_{period}'] = self.volume_indicators.volume_ratio(data['volume'], period).iloc[-1]

            # 计算成交量移动平均
            for period in [5, 10, 20]:
                results[f'Volume_MA_{period}'] = self.volume_indicators.volume_ma(data['volume'], period).iloc[-1]

            # 计算OBV
            results['OBV'] = self.volume_indicators.obv(data['close'], data['volume']).iloc[-1]

            # 计算AD线
            results['AD_Line'] = self.volume_indicators.ad_line(data['high'], data['low'], data['close'], data['volume']).iloc[-1]

            # 计算成交量变动
            results['Volume_Change'] = data['volume'].iloc[-1] - data['volume'].iloc[-2]
            results['Volume_Change_Percent'] = results['Volume_Change'] / data['volume'].iloc[-2] * 100 if data['volume'].iloc[-2] != 0 else 0

            # 计算成交量趋势
            results['Volume_Trend'] = 1 if results['Volume_Change'] > 0 else -1

            # 计算换手率（这里简化处理）
            results['Turnover_Rate'] = 0.01  # 假设换手率为1%

            # 计算成交金额变动
            results['Amount_Change'] = data['amount'].iloc[-1] - data['amount'].iloc[-2]
            results['Amount_Change_Percent'] = results['Amount_Change'] / data['amount'].iloc[-2] * 100 if data['amount'].iloc[-2] != 0 else 0

            # 计算成交金额趋势
            results['Amount_Trend'] = 1 if results['Amount_Change'] > 0 else -1

        except Exception as e:
            logger.error(f"计算成交量指标失败: {e}")

        return results

    def _save_single_fund_indicators(self, fund_code: str, indicators: Dict[str, Any]):
        """
        保存单个基金的指标结果

        Args:
            fund_code: 基金代码
            indicators: 指标结果
        """
        output_file = os.path.join(self.indicators_output_dir, f'{fund_code}_indicators.json')

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(indicators, f, ensure_ascii=False, indent=2)

    def _save_all_indicators(self, all_indicators: Dict[str, Dict[str, Any]]):
        """
        保存所有基金的指标结果

        Args:
            all_indicators: 所有指标结果
        """
        output_file = os.path.join(self.indicators_output_dir, f'all_indicators_{self.fund_type}.json')

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_indicators, f, ensure_ascii=False, indent=2)

    def generate_indicators_report(self, all_indicators: Dict[str, Dict[str, Any]]) -> str:
        """
        生成指标分析报告

        Args:
            all_indicators: 所有指标结果

        Returns:
            报告文本
        """
        logger.info(f"开始生成{self.fund_type}基金的指标分析报告")

        report = f"# {self.fund_type}基金指标分析报告

"
        report += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"

        # 添加基金类型描述
        if self.fund_type in FUND_TYPES:
            report += f"## 基金类型: {FUND_TYPES[self.fund_type]['name']}

"
            report += f"{FUND_TYPES[self.fund_type]['description']}

"

        # 添加技术指标分析
        report += "## 技术指标分析

"

        # 计算平均指标值
        avg_technical = {}
        for fund_code, indicators in all_indicators.items():
            if 'technical' in indicators:
                for key, value in indicators['technical'].items():
                    if isinstance(value, (int, float)):
                        if key not in avg_technical:
                            avg_technical[key] = []
                        avg_technical[key].append(value)

        # 计算并显示平均指标值
        report += "### 平均技术指标

"
        report += "| 指标 | 平均值 | 说明 |
"
        report += "|------|--------|------|
"

        for key, values in avg_technical.items():
            if values:
                avg_value = sum(values) / len(values)
                report += f"| {key} | {avg_value:.4f} | {self._get_indicator_description(key)} |
"

        report += "
"

        # 添加基本面指标分析
        report += "## 基本面指标分析

"

        # 计算平均指标值
        avg_fundamental = {}
        for fund_code, indicators in all_indicators.items():
            if 'fundamental' in indicators:
                for key, value in indicators['fundamental'].items():
                    if isinstance(value, (int, float)):
                        if key not in avg_fundamental:
                            avg_fundamental[key] = []
                        avg_fundamental[key].append(value)

        # 计算并显示平均指标值
        report += "### 平均基本面指标

"
        report += "| 指标 | 平均值 | 说明 |
"
        report += "|------|--------|------|
"

        for key, values in avg_fundamental.items():
            if values:
                avg_value = sum(values) / len(values)
                report += f"| {key} | {avg_value:.4f} | {self._get_indicator_description(key)} |
"

        report += "
"

        # 添加成交量指标分析
        report += "## 成交量指标分析

"

        # 计算平均指标值
        avg_volume = {}
        for fund_code, indicators in all_indicators.items():
            if 'volume' in indicators:
                for key, value in indicators['volume'].items():
                    if isinstance(value, (int, float)):
                        if key not in avg_volume:
                            avg_volume[key] = []
                        avg_volume[key].append(value)

        # 计算并显示平均指标值
        report += "### 平均成交量指标

"
        report += "| 指标 | 平均值 | 说明 |
"
        report += "|------|--------|------|
"

        for key, values in avg_volume.items():
            if values:
                avg_value = sum(values) / len(values)
                report += f"| {key} | {avg_value:.4f} | {self._get_indicator_description(key)} |
"

        report += "
"

        # 添加市场趋势分析
        report += "## 市场趋势分析

"

        # 分析价格趋势
        price_trend_up = 0
        price_trend_down = 0

        for fund_code, indicators in all_indicators.items():
            if 'technical' in indicators and 'Price_Trend' in indicators['technical']:
                if indicators['technical']['Price_Trend'] > 0:
                    price_trend_up += 1
                else:
                    price_trend_down += 1

        total_funds = price_trend_up + price_trend_down
        if total_funds > 0:
            up_percentage = price_trend_up / total_funds * 100
            down_percentage = price_trend_down / total_funds * 100

            report += f"价格趋势分析:
"
            report += f"- 上涨基金数量: {price_trend_up} ({up_percentage:.2f}%)
"
            report += f"- 下跌基金数量: {price_trend_down} ({down_percentage:.2f}%)

"

            if up_percentage > down_percentage:
                report += "市场整体呈现上涨趋势。

"
            else:
                report += "市场整体呈现下跌趋势。

"

        # 分析成交量趋势
        volume_trend_up = 0
        volume_trend_down = 0

        for fund_code, indicators in all_indicators.items():
            if 'volume' in indicators and 'Volume_Trend' in indicators['volume']:
                if indicators['volume']['Volume_Trend'] > 0:
                    volume_trend_up += 1
                else:
                    volume_trend_down += 1

        if total_funds > 0:
            up_percentage = volume_trend_up / total_funds * 100
            down_percentage = volume_trend_down / total_funds * 100

            report += f"成交量趋势分析:
"
            report += f"- 成交量放大基金数量: {volume_trend_up} ({up_percentage:.2f}%)
"
            report += f"- 成交量萎缩基金数量: {volume_trend_down} ({down_percentage:.2f}%)

"

            if up_percentage > down_percentage:
                report += "市场整体成交量呈放大趋势。

"
            else:
                report += "市场整体成交量呈萎缩趋势。

"

        # 添加风险评估
        report += "## 风险评估

"

        # 计算平均波动率
        volatility_values = []
        for fund_code, indicators in all_indicators.items():
            if 'fundamental' in indicators and 'Volatility' in indicators['fundamental']:
                volatility_values.append(indicators['fundamental']['Volatility'])

        if volatility_values:
            avg_volatility = sum(volatility_values) / len(volatility_values)

            report += f"平均波动率: {avg_volatility:.4f}

"

            if avg_volatility < 0.1:
                report += "市场整体风险较低。

"
            elif avg_volatility < 0.2:
                report += "市场整体风险适中。

"
            else:
                report += "市场整体风险较高。

"

        # 添加投资建议
        report += "## 投资建议

"

        # 根据技术指标给出建议
        report += "### 技术面建议

"

        # 计算MACD信号
        macd_signals = []
        for fund_code, indicators in all_indicators.items():
            if 'technical' in indicators and 'MACD' in indicators['technical'] and 'MACD_Signal' in indicators['technical']:
                macd = indicators['technical']['MACD']
                signal = indicators['technical']['MACD_Signal']
                if macd > signal:
                    macd_signals.append('买入')
                elif macd < signal:
                    macd_signals.append('卖出')
                else:
                    macd_signals.append('观望')

        if macd_signals:
            buy_count = macd_signals.count('买入')
            sell_count = macd_signals.count('卖出')
            hold_count = macd_signals.count('观望')

            report += f"MACD信号分析:
"
            report += f"- 买入信号: {buy_count}
"
            report += f"- 卖出信号: {sell_count}
"
            report += f"- 观望信号: {hold_count}

"

            if buy_count > sell_count:
                report += "从MACD指标来看，市场整体呈现买入信号。

"
            elif sell_count > buy_count:
                report += "从MACD指标来看，市场整体呈现卖出信号。

"
            else:
                report += "从MACD指标来看，市场整体呈现观望信号。

"

        # 根据RSI给出建议
        report += "### RSI建议

"

        rsi_signals = []
        for fund_code, indicators in all_indicators.items():
            if 'technical' in indicators and 'RSI_14' in indicators['technical']:
                rsi = indicators['technical']['RSI_14']
                if rsi < 30:
                    rsi_signals.append('超卖')
                elif rsi > 70:
                    rsi_signals.append('超买')
                else:
                    rsi_signals.append('正常')

        if rsi_signals:
            oversold_count = rsi_signals.count('超卖')
            overbought_count = rsi_signals.count('超买')
            normal_count = rsi_signals.count('正常')

            report += f"RSI信号分析:
"
            report += f"- 超卖信号: {oversold_count}
"
            report += f"- 超买信号: {overbought_count}
"
            report += f"- 正常信号: {normal_count}

"

            if oversold_count > overbought_count:
                report += "从RSI指标来看，市场整体处于超卖状态，存在反弹机会。

"
            elif overbought_count > oversold_count:
                report += "从RSI指标来看，市场整体处于超买状态，需要注意回调风险。

"
            else:
                report += "从RSI指标来看，市场整体处于正常状态。

"

        # 根据布林带给出建议
        report += "### 布林带建议

"

        bb_signals = []
        for fund_code, indicators in all_indicators.items():
            if 'technical' in indicators and 'BB_Position' in indicators['technical']:
                bb_pos = indicators['technical']['BB_Position']
                if bb_pos < 0.1:
                    bb_signals.append('超卖')
                elif bb_pos > 0.9:
                    bb_signals.append('超买')
                else:
                    bb_signals.append('正常')

        if bb_signals:
            oversold_count = bb_signals.count('超卖')
            overbought_count = bb_signals.count('超买')
            normal_count = bb_signals.count('正常')

            report += f"布林带信号分析:
"
            report += f"- 超卖信号: {oversold_count}
"
            report += f"- 超买信号: {overbought_count}
"
            report += f"- 正常信号: {normal_count}

"

            if oversold_count > overbought_count:
                report += "从布林带指标来看，市场整体处于超卖状态，存在反弹机会。

"
            elif overbought_count > oversold_count:
                report += "从布林带指标来看，市场整体处于超买状态，需要注意回调风险。

"
            else:
                report += "从布林带指标来看，市场整体处于正常状态。

"

        # 保存报告
        report_file = os.path.join(ANALYSIS_RESULTS_DIR, f'indicators_report_{self.fund_type}.md')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"指标分析报告已保存至: {report_file}")

        return report

    def _get_indicator_description(self, indicator_name: str) -> str:
        """
        获取指标描述

        Args:
            indicator_name: 指标名称

        Returns:
            指标描述
        """
        descriptions = {
            # 技术指标
            'MA_5': '5日移动平均线',
            'MA_10': '10日移动平均线',
            'MA_20': '20日移动平均线',
            'MA_30': '30日移动平均线',
            'MA_60': '60日移动平均线',
            'EMA_5': '5日指数移动平均线',
            'EMA_10': '10日指数移动平均线',
            'EMA_20': '20日指数移动平均线',
            'EMA_30': '30日指数移动平均线',
            'EMA_60': '60日指数移动平均线',
            'MACD': 'MACD指标',
            'MACD_Signal': 'MACD信号线',
            'MACD_Histogram': 'MACD柱状图',
            'RSI_6': '6日RSI指标',
            'RSI_12': '12日RSI指标',
            'RSI_24': '24日RSI指标',
            'KDJ_K': 'KDJ指标K值',
            'KDJ_D': 'KDJ指标D值',
            'KDJ_J': 'KDJ指标J值',
            'BB_Upper': '布林带上轨',
            'BB_Middle': '布林带中轨',
            'BB_Lower': '布林带下轨',
            'BB_Width': '布林带带宽',
            'WR_14': '14日威廉指标',
            'CCI_20': '20日CCI指标',
            'DMI_Plus_DI': 'DMI指标+DI',
            'DMI_Minus_DI': 'DMI指标-DI',
            'DMI_ADX': 'ADX指标',
            'OBV': 'OBV指标',
            'Price_Change': '价格变动',
            'Price_Change_Percent': '价格变动百分比',
            'Price_Trend': '价格趋势',
            'BB_Position': '布林带位置',

            # 基本面指标
            'YTD_Return': '年初至今收益率',
            '1Y_Return': '1年年化收益率',
            '3Y_Return': '3年年化收益率',
            '5Y_Return': '5年年化收益率',
            'Sharpe_Ratio': '夏普比率',
            'Sortino_Ratio': '索提诺比率',
            'Max_Drawdown': '最大回撤',
            'Volatility': '波动率',
            'Alpha': 'Alpha系数',
            'Beta': 'Beta系数',
            'Information_Ratio': '信息比率',
            'Fund_Scale': '基金规模',
            'Fund_Rating': '基金评级',

            # 成交量指标
            'Volume_Ratio_5': '5日量比',
            'Volume_Ratio_10': '10日量比',
            'Volume_Ratio_20': '20日量比',
            'Volume_MA_5': '5日成交量移动平均',
            'Volume_MA_10': '10日成交量移动平均',
            'Volume_MA_20': '20日成交量移动平均',
            'Volume_Change': '成交量变动',
            'Volume_Change_Percent': '成交量变动百分比',
            'Volume_Trend': '成交量趋势',
            'Turnover_Rate': '换手率',
            'Amount_Change': '成交金额变动',
            'Amount_Change_Percent': '成交金额变动百分比',
            'Amount_Trend': '成交金额趋势',
            'AD_Line': 'AD线'
        }

        return descriptions.get(indicator_name, '未知指标')


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='计算基金指标')
    parser.add_argument('--fund-type', type=str, default='mixed', help='基金类型')
    args = parser.parse_args()

    # 创建指标计算器
    calculator = IndicatorCalculator(args.fund_type)

    # 加载基金数据
    fund_data = {}

    # 这里应该加载基金数据，简化处理
    # 实际应用中，应该从数据爬取模块获取数据

    # 计算所有指标
    all_indicators = calculator.calculate_all_indicators(fund_data)

    # 生成指标报告
    report = calculator.generate_indicators_report(all_indicators)

    print(report)


if __name__ == '__main__':
    main()
