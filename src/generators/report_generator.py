#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import pandas as pd
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.logger import setup_logger
from utils.config import Config

class ReportGenerator:
    def __init__(self):
        """初始化报告生成器"""
        self.logger = setup_logger('ReportGenerator')

    def load_trading_signals(self, signals_file):
        """
        加载交易信号数据

        Args:
            signals_file (str): 交易信号文件路径

        Returns:
            dict: 交易信号数据
        """
        try:
            with open(signals_file, 'r', encoding='utf-8') as f:
                signals_data = json.load(f)

            self.logger.info(f"交易信号数据加载完成，共{len(signals_data.get('funds_signals', []))}只基金")
            return signals_data

        except Exception as e:
            self.logger.error(f"加载交易信号数据失败: {str(e)}")
            return {}

    def generate_trading_table(self, trading_signals):
        """
        生成交易信号表格

        Args:
            trading_signals (dict): 交易信号数据

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

                # 格式化评分，保留两位小数
                total_score_str = f"{total_score:.2f}"
                technical_score_str = f"{technical_score:.2f}"
                news_score_str = f"{news_score:.2f}"

                table += f"| {fund_code} | {fund_name} | {signal} | {strength} | {total_score_str} | {technical_score_str} | {news_score_str} |
"

            return table

        except Exception as e:
            self.logger.error(f"生成交易信号表格失败: {str(e)}")
            return "| 生成表格时出错 |
"

    def generate_signal_summary(self, trading_signals):
        """
        生成信号摘要

        Args:
            trading_signals (dict): 交易信号数据

        Returns:
            str: 信号摘要文本
        """
        try:
            # 获取基金信号
            funds_signals = trading_signals.get('funds_signals', [])

            # 统计信号分布
            signal_counts = {'买入': 0, '卖出': 0, '观望': 0}
            total_score = 0

            for fund_signal in funds_signals:
                signal = fund_signal.get('signal', '观望')
                if signal in signal_counts:
                    signal_counts[signal] += 1

                total_score += fund_signal.get('total_score', 0)

            # 计算平均评分
            avg_score = total_score / len(funds_signals) if funds_signals else 0

            # 构建摘要
            summary = f"## 信号摘要

"
            summary += f"- 分析时间: {trading_signals.get('generation_time', '未知')}
"
            summary += f"- 市场情绪: {trading_signals.get('market_sentiment', '未知')}
"
            summary += f"- 市场影响: {trading_signals.get('market_impact', '未知')}
"
            summary += f"- 分析基金总数: {len(funds_signals)}
"
            summary += f"- 买入信号: {signal_counts['买入']}只 ({signal_counts['买入']/len(funds_signals)*100:.1f}%)
"
            summary += f"- 卖出信号: {signal_counts['卖出']}只 ({signal_counts['卖出']/len(funds_signals)*100:.1f}%)
"
            summary += f"- 观望信号: {signal_counts['观望']}只 ({signal_counts['观望']/len(funds_signals)*100:.1f}%)
"
            summary += f"- 平均综合评分: {avg_score:.2f}
"

            return summary

        except Exception as e:
            self.logger.error(f"生成信号摘要失败: {str(e)}")
            return "## 信号摘要

生成摘要时出错
"

    def generate_signal_details(self, trading_signals):
        """
        生成信号详情

        Args:
            trading_signals (dict): 交易信号数据

        Returns:
            str: 信号详情文本
        """
        try:
            # 获取基金信号
            funds_signals = trading_signals.get('funds_signals', [])

            # 如果没有数据，返回空文本
            if not funds_signals:
                return "## 信号详情

暂无数据
"

            # 构建详情
            details = "## 信号详情

"

            for fund_signal in funds_signals:
                fund_code = fund_signal.get('fund_code', '未知')
                fund_name = fund_signal.get('fund_name', '未知')
                signal = fund_signal.get('signal', '观望')
                strength = fund_signal.get('signal_strength', '弱')
                total_score = fund_signal.get('total_score', 0)

                details += f"### {fund_code} - {fund_name}

"
                details += f"- 交易信号: {signal} (强度: {strength})
"
                details += f"- 综合评分: {total_score:.2f}
"

                # 技术指标影响因素
                technical_factors = fund_signal.get('signal_details', {}).get('technical_factors', [])
                if technical_factors:
                    details += "- 技术指标影响因素:
"
                    for factor in technical_factors:
                        details += f"  - {factor}
"

                # 新闻影响因素
                news_factors = fund_signal.get('signal_details', {}).get('news_factors', [])
                if news_factors:
                    details += "- 新闻影响因素:
"
                    for factor in news_factors:
                        details += f"  - {factor}
"

                details += "
"

            return details

        except Exception as e:
            self.logger.error(f"生成信号详情失败: {str(e)}")
            return "## 信号详情

生成详情时出错
"

    def generate_recommendations(self, trading_signals):
        """
        生成投资建议

        Args:
            trading_signals (dict): 交易信号数据

        Returns:
            str: 投资建议文本
        """
        try:
            # 获取基金信号
            funds_signals = trading_signals.get('funds_signals', [])

            # 如果没有数据，返回空文本
            if not funds_signals:
                return "## 投资建议

暂无数据
"

            # 按信号类型分组
            buy_signals = [f for f in funds_signals if f.get('signal') == '买入']
            sell_signals = [f for f in funds_signals if f.get('signal') == '卖出']
            hold_signals = [f for f in funds_signals if f.get('signal') == '观望']

            # 构建建议
            recommendations = "## 投资建议

"

            # 买入建议
            if buy_signals:
                recommendations += "### 建议买入基金

"
                for fund_signal in buy_signals[:5]:  # 只显示前5只
                    fund_code = fund_signal.get('fund_code', '未知')
                    fund_name = fund_signal.get('fund_name', '未知')
                    strength = fund_signal.get('signal_strength', '弱')
                    total_score = fund_signal.get('total_score', 0)

                    recommendations += f"- {fund_code} - {fund_name} (强度: {strength}, 评分: {total_score:.2f})
"

                if len(buy_signals) > 5:
                    recommendations += f"...以及其他{len(buy_signals)-5}只基金
"

                recommendations += "
"

            # 卖出建议
            if sell_signals:
                recommendations += "### 建议卖出基金

"
                for fund_signal in sell_signals[:5]:  # 只显示前5只
                    fund_code = fund_signal.get('fund_code', '未知')
                    fund_name = fund_signal.get('fund_name', '未知')
                    strength = fund_signal.get('signal_strength', '弱')
                    total_score = fund_signal.get('total_score', 0)

                    recommendations += f"- {fund_code} - {fund_name} (强度: {strength}, 评分: {total_score:.2f})
"

                if len(sell_signals) > 5:
                    recommendations += f"...以及其他{len(sell_signals)-5}只基金
"

                recommendations += "
"

            # 观望建议
            if hold_signals:
                recommendations += "### 建议观望基金

"
                for fund_signal in hold_signals[:5]:  # 只显示前5只
                    fund_code = fund_signal.get('fund_code', '未知')
                    fund_name = fund_signal.get('fund_name', '未知')
                    strength = fund_signal.get('signal_strength', '弱')
                    total_score = fund_signal.get('total_score', 0)

                    recommendations += f"- {fund_code} - {fund_name} (强度: {strength}, 评分: {total_score:.2f})
"

                if len(hold_signals) > 5:
                    recommendations += f"...以及其他{len(hold_signals)-5}只基金
"

                recommendations += "
"

            # 风险提示
            recommendations += "### 风险提示

"
            recommendations += "- 以上分析仅供参考，不构成投资建议
"
            recommendations += "- 基金投资有风险，需谨慎决策
"
            recommendations += "- 建议结合自身风险承受能力进行投资
"
            recommendations += "- 定期关注市场变化，及时调整投资策略
"

            return recommendations

        except Exception as e:
            self.logger.error(f"生成投资建议失败: {str(e)}")
            return "## 投资建议

生成建议时出错
"

    def generate_report(self, trading_signals, output_file):
        """
        生成完整报告

        Args:
            trading_signals (dict): 交易信号数据
            output_file (str): 输出文件路径
        """
        try:
            # 生成报告各部分
            header = f"# 基金数据分析与买卖点预测报告

"
            header += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"

            summary = self.generate_signal_summary(trading_signals)
            table = self.generate_trading_table(trading_signals)
            details = self.generate_signal_details(trading_signals)
            recommendations = self.generate_recommendations(trading_signals)

            # 合并报告
            report = header + summary + "
" + table + "
" + details + "
" + recommendations

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            # 保存报告
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)

            self.logger.info(f"报告已生成并保存到: {output_file}")

        except Exception as e:
            self.logger.error(f"生成报告失败: {str(e)}")


def main():
    """主函数"""
    # 创建报告生成器实例
    generator = ReportGenerator()

    # 示例数据
    trading_signals = {
        'generation_time': '2023-06-01 12:00:00',
        'market_sentiment': '积极',
        'market_impact': '中',
        'funds_signals': [
            {
                'fund_code': '110022',
                'fund_name': '易方达蓝筹精选',
                'technical_score': 0.65,
                'news_score': 0.45,
                'total_score': 0.58,
                'signal': '买入',
                'signal_strength': '中',
                'signal_details': {
                    'technical_factors': [
                        '5日均线上穿20日均线',
                        'MACD金叉形成',
                        'RSI指标从超卖区回升'
                    ],
                    'news_factors': [
                        '市场整体情绪积极，利好基金投资',
                        '基金公司业绩表现良好'
                    ]
                }
            },
            {
                'fund_code': '000217',
                'fund_name': '国泰估值优势',
                'technical_score': -0.35,
                'news_score': -0.20,
                'total_score': -0.30,
                'signal': '卖出',
                'signal_strength': '中',
                'signal_details': {
                    'technical_factors': [
                        '5日均线下穿20日均线',
                        'MACD死叉形成',
                        'RSI指标进入超买区'
                    ],
                    'news_factors': [
                        '市场整体情绪消极，利空基金投资'
                    ]
                }
            },
            {
                'fund_code': '000345',
                'fund_name': '长城行业',
                'technical_score': 0.10,
                'news_score': 0.05,
                'total_score': 0.08,
                'signal': '观望',
                'signal_strength': '弱',
                'signal_details': {
                    'technical_factors': [
                        '均线系统纠缠，方向不明'
                    ],
                    'news_factors': [
                        '市场情绪中性，无明显利好或利空'
                    ]
                }
            }
        ]
    }

    # 生成报告
    generator.generate_report(trading_signals, 'trading_signals_report.md')


if __name__ == '__main__':
    main()
