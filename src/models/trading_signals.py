#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import pandas as pd
import numpy as np
import logging
import json
from datetime import datetime
from collections import defaultdict

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.logger import setup_logger
from utils.config import Config

class TradingSignalsModel:
    def __init__(self):
        """初始化交易信号模型"""
        self.logger = setup_logger('TradingSignalsModel')

        # 技术指标权重
        self.technical_weights = {
            'ma_cross': 0.15,
            'macd_cross': 0.15,
            'rsi_oversold': 0.10,
            'rsi_overbought': 0.10,
            'bb_lower': 0.10,
            'bb_upper': 0.10,
            'stochastic_cross': 0.10,
            'cci_oversold': 0.05,
            'cci_overbought': 0.05,
            'adx_trend': 0.10
        }

        # 新闻情感权重
        self.news_weights = {
            'sentiment_intensity': 0.3,
            'impact_level': 0.2,
            'historical_correlation': 0.1
        }

    def load_technical_signals(self, technical_signals_file):
        """
        加载技术指标信号数据

        Args:
            technical_signals_file (str): 技术指标信号文件路径

        Returns:
            dict: 技术指标信号数据
        """
        try:
            with open(technical_signals_file, 'r', encoding='utf-8') as f:
                technical_signals = json.load(f)

            self.logger.info(f"技术指标信号数据加载完成，共{len(technical_signals.get('funds_analysis', []))}只基金")
            return technical_signals

        except Exception as e:
            self.logger.error(f"加载技术指标信号数据失败: {str(e)}")
            return {}

    def load_news_signals(self, news_signals_file):
        """
        加载新闻信号数据

        Args:
            news_signals_file (str): 新闻信号文件路径

        Returns:
            dict: 新闻信号数据
        """
        try:
            with open(news_signals_file, 'r', encoding='utf-8') as f:
                news_signals = json.load(f)

            self.logger.info("新闻信号数据加载完成")
            return news_signals

        except Exception as e:
            self.logger.error(f"加载新闻信号数据失败: {str(e)}")
            return {}

    def calculate_technical_score(self, fund_analysis):
        """
        计算技术指标评分

        Args:
            fund_analysis (dict): 单个基金的技术分析结果

        Returns:
            float: 技术指标评分
        """
        try:
            # 获取信号历史
            signals_history = fund_analysis.get('signals_history', {})

            # 统计各类信号数量
            signal_counts = defaultdict(int)
            for signal in signals_history.values():
                if signal == '买入':
                    signal_counts['buy'] += 1
                elif signal == '卖出':
                    signal_counts['sell'] += 1
                else:
                    signal_counts['hold'] += 1

            # 计算加权评分
            score = 0
            total_weight = 0

            # 计算各类信号评分
            for signal_type, weight in self.technical_weights.items():
                if signal_type in ['ma_cross', 'macd_cross', 'stochastic_cross', 'adx_trend']:
                    # 交叉信号类型
                    if signal_type in signals_history:
                        if signals_history[signal_type] == '买入':
                            score += weight * 1
                        elif signals_history[signal_type] == '卖出':
                            score += weight * -1
                        else:
                            score += weight * 0
                elif signal_type in ['rsi_oversold', 'bb_lower', 'cci_oversold']:
                    # 超卖信号类型
                    if signal_type in signals_history:
                        if signals_history[signal_type] == '买入':
                            score += weight * 1
                        else:
                            score += weight * 0
                elif signal_type in ['rsi_overbought', 'bb_upper', 'cci_overbought']:
                    # 超买信号类型
                    if signal_type in signals_history:
                        if signals_history[signal_type] == '卖出':
                            score += weight * -1
                        else:
                            score += weight * 0

                total_weight += weight

            # 归一化评分
            if total_weight > 0:
                score = score / total_weight

            return score

        except Exception as e:
            self.logger.error(f"计算技术指标评分失败: {str(e)}")
            return 0

    def calculate_news_score(self, fund_code, news_analysis):
        """
        计算新闻情感评分

        Args:
            fund_code (str): 基金代码
            news_analysis (dict): 新闻分析结果

        Returns:
            float: 新闻情感评分
        """
        try:
            # 获取与该基金相关的新闻情感
            # 这里简化处理，实际应用中应该分析与特定基金相关的新闻
            sentiment_intensity = news_analysis.get('sentiment_analysis', {}).get('average_score', 0)
            impact_level = news_analysis.get('impact_analysis', {}).get('impact_level', '低')

            # 根据影响级别设置权重
            impact_weights = {'高': 1.0, '中': 0.6, '低': 0.3}
            impact_weight = impact_weights.get(impact_level, 0.3)

            # 计算加权评分
            score = sentiment_intensity * impact_weight

            return score

        except Exception as e:
            self.logger.error(f"计算新闻情感评分失败: {str(e)}")
            return 0

    def generate_trading_signals(self, technical_signals, news_signals):
        """
        生成交易信号

        Args:
            technical_signals (dict): 技术指标信号数据
            news_signals (dict): 新闻信号数据

        Returns:
            dict: 交易信号结果
        """
        try:
            # 获取技术分析结果
            funds_analysis = technical_signals.get('funds_analysis', [])

            # 获取新闻分析结果
            sentiment_analysis = news_signals.get('sentiment_analysis', {})
            impact_analysis = news_signals.get('impact_analysis', {})

            # 初始化结果
            trading_signals = {
                'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'market_sentiment': sentiment_analysis.get('sentiment_trend', '中性'),
                'market_impact': impact_analysis.get('impact_level', '低'),
                'funds_signals': []
            }

            # 分析每只基金
            for fund_analysis in funds_analysis:
                fund_code = fund_analysis.get('fund_code', '未知')
                fund_name = fund_analysis.get('fund_name', '未知')

                # 计算技术指标评分
                technical_score = self.calculate_technical_score(fund_analysis)

                # 计算新闻情感评分
                news_score = self.calculate_news_score(fund_code, news_signals)

                # 综合评分
                total_score = technical_score * 0.6 + news_score * 0.4

                # 生成交易信号
                if total_score > 0.2:
                    signal = '买入'
                    signal_strength = '强'
                elif total_score > 0.05:
                    signal = '买入'
                    signal_strength = '中'
                elif total_score < -0.2:
                    signal = '卖出'
                    signal_strength = '强'
                elif total_score < -0.05:
                    signal = '卖出'
                    signal_strength = '中'
                else:
                    signal = '观望'
                    signal_strength = '弱'

                # 添加到结果
                trading_signals['funds_signals'].append({
                    'fund_code': fund_code,
                    'fund_name': fund_name,
                    'technical_score': technical_score,
                    'news_score': news_score,
                    'total_score': total_score,
                    'signal': signal,
                    'signal_strength': signal_strength,
                    'signal_details': {
                        'technical_factors': self.get_technical_factors(fund_analysis),
                        'news_factors': self.get_news_factors(news_signals, fund_code)
                    }
                })

            # 按综合评分排序
            trading_signals['funds_signals'].sort(key=lambda x: x['total_score'], reverse=True)

            # 统计信号分布
            signal_counts = defaultdict(int)
            for fund_signal in trading_signals['funds_signals']:
                signal = fund_signal['signal']
                signal_counts[signal] += 1

            trading_signals['signal_distribution'] = dict(signal_counts)

            self.logger.info("交易信号生成完成")
            return trading_signals

        except Exception as e:
            self.logger.error(f"生成交易信号失败: {str(e)}")
            return {}

    def get_technical_factors(self, fund_analysis):
        """
        获取技术指标影响因素

        Args:
            fund_analysis (dict): 基金技术分析结果

        Returns:
            list: 技术指标影响因素列表
        """
        try:
            factors = []

            # 获取信号历史
            signals_history = fund_analysis.get('signals_history', {})

            # 分析买入信号
            buy_signals = [signal for signal, action in signals_history.items() if action == '买入']
            if buy_signals:
                factors.append(f"技术指标显示买入信号: {', '.join(buy_signals)}")

            # 分析卖出信号
            sell_signals = [signal for signal, action in signals_history.items() if action == '卖出']
            if sell_signals:
                factors.append(f"技术指标显示卖出信号: {', '.join(sell_signals)}")

            return factors

        except Exception as e:
            self.logger.error(f"获取技术指标影响因素失败: {str(e)}")
            return []

    def get_news_factors(self, news_analysis, fund_code):
        """
        获取新闻影响因素

        Args:
            news_analysis (dict): 新闻分析结果
            fund_code (str): 基金代码

        Returns:
            list: 新闻影响因素列表
        """
        try:
            factors = []

            # 获取情感分析结果
            sentiment_analysis = news_analysis.get('sentiment_analysis', {})
            sentiment_trend = sentiment_analysis.get('sentiment_trend', '中性')

            if sentiment_trend == '积极':
                factors.append("市场整体情绪积极，利好基金投资")
            elif sentiment_trend == '消极':
                factors.append("市场整体情绪消极，利空基金投资")

            # 获取影响分析结果
            impact_analysis = news_analysis.get('impact_analysis', {})
            impact_level = impact_analysis.get('impact_level', '低')

            if impact_level == '高':
                factors.append("市场新闻影响级别高，需密切关注")
            elif impact_level == '中':
                factors.append("市场新闻影响级别中等，需适当关注")

            # 获取热门关键词
            top_keywords = sentiment_analysis.get('keyword_freq', {}).most_common(5)
            if top_keywords:
                keywords = [keyword for keyword, _ in top_keywords]
                factors.append(f"市场关注热点: {', '.join(keywords)}")

            return factors

        except Exception as e:
            self.logger.error(f"获取新闻影响因素失败: {str(e)}")
            return []

    def save_trading_signals(self, trading_signals, output_file):
        """
        保存交易信号结果

        Args:
            trading_signals (dict): 交易信号结果
            output_file (str): 输出文件路径
        """
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            # 保存为JSON
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(trading_signals, f, ensure_ascii=False, indent=2)

            self.logger.info(f"交易信号结果已保存到: {output_file}")

        except Exception as e:
            self.logger.error(f"保存交易信号结果失败: {str(e)}")

    def generate_trading_table(self, trading_signals):
        """
        生成交易信号表格

        Args:
            trading_signals (dict): 交易信号结果

        Returns:
            str: 交易信号表格文本
        """
        try:
            # 获取基金信号
            funds_signals = trading_signals.get('funds_signals', [])

            # 如果没有数据，返回空表格
            if not funds_signals:
                return "| 基金代码 | 基金名称 | 信号 | 强度 | 综合评分 | 技术评分 | 新闻评分 |
|---------|---------|------|------|---------|---------|---------|
"

            # 构建表格
            table = "| 基金代码 | 基金名称 | 信号 | 强度 | 综合评分 | 技术评分 | 新闻评分 |
"
            table += "|---------|---------|------|------|---------|---------|---------|
"

            for fund_signal in funds_signals:
                fund_code = fund_signal.get('fund_code', '未知')
                fund_name = fund_signal.get('fund_name', '未知')
                signal = fund_signal.get('signal', '观望')
                strength = fund_signal.get('signal_strength', '弱')
                total_score = fund_signal.get('total_score', 0)
                technical_score = fund_signal.get('technical_score', 0)
                news_score = fund_signal.get('news_score', 0)

                table += f"| {fund_code} | {fund_name} | {signal} | {strength} | {total_score:.2f} | {technical_score:.2f} | {news_score:.2f} |
"

            return table

        except Exception as e:
            self.logger.error(f"生成交易信号表格失败: {str(e)}")
            return "| 基金代码 | 基金名称 | 信号 | 强度 | 综合评分 | 技术评分 | 新闻评分 |
|---------|---------|------|------|---------|---------|---------|
"


def main():
    """主函数"""
    # 创建交易信号模型实例
    model = TradingSignalsModel()

    # 示例数据
    technical_signals = {
        'funds_analysis': [
            {
                'fund_code': '000001',
                'fund_name': '华夏成长',
                'signals_history': {
                    'ma_cross': '买入',
                    'macd_cross': '观望',
                    'rsi_oversold': '买入',
                    'rsi_overbought': '观望',
                    'bb_lower': '买入',
                    'bb_upper': '观望',
                    'stochastic_cross': '买入',
                    'cci_oversold': '观望',
                    'cci_overbought': '观望',
                    'adx_trend': '观望'
                }
            },
            {
                'fund_code': '000002',
                'fund_name': '华夏回报',
                'signals_history': {
                    'ma_cross': '卖出',
                    'macd_cross': '卖出',
                    'rsi_oversold': '观望',
                    'rsi_overbought': '卖出',
                    'bb_lower': '观望',
                    'bb_upper': '卖出',
                    'stochastic_cross': '观望',
                    'cci_oversold': '观望',
                    'cci_overbought': '卖出',
                    'adx_trend': '卖出'
                }
            }
        ]
    }

    news_signals = {
        'sentiment_analysis': {
            'average_score': 0.2,
            'sentiment_trend': '积极',
            'keyword_freq': Counter(['基金', '市场', '政策', '投资', '股票'])
        },
        'impact_analysis': {
            'impact_level': '中'
        }
    }

    # 生成交易信号
    trading_signals = model.generate_trading_signals(technical_signals, news_signals)

    # 生成交易表格
    trading_table = model.generate_trading_table(trading_signals)
    print("交易信号表格:")
    print(trading_table)

    # 保存结果
    model.save_trading_signals(trading_signals, 'trading_signals.json')


if __name__ == '__main__':
    main()
