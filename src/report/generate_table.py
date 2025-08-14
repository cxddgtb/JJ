#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
买卖点表格生成模块
"""

import os
import json
import logging
import pandas as pd
from typing import Dict, List, Any, Optional

from ..utils.config import OUTPUT_DIR, REPORT_CONFIG

logger = logging.getLogger(__name__)

class GenerateTable:
    """买卖点表格生成类"""

    def __init__(self, buy_sell_points, ai_insights):
        """
        初始化表格生成器

        Args:
            buy_sell_points: 买卖点分析结果列表
            ai_insights: AI分析结果
        """
        self.buy_sell_points = buy_sell_points
        self.ai_insights = ai_insights

        self.config = REPORT_CONFIG
        self.table_format = self.config.get('table_format', 'markdown')

        self.output_dir = os.path.join(OUTPUT_DIR, 'tables')
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        logger.info("买卖点表格生成器初始化完成")

    def _generate_markdown_table(self):
        """
        生成Markdown格式的表格

        Returns:
            Markdown表格字符串
        """
        # 表头
        table = "| 基金代码 | 基金名称 | 基金类型 | 最新净值 | 日增长率 | 近一年收益率 | 长期得分 | 中期得分 | 短期得分 | 新闻情感 | 综合得分 | 操作建议 | AI预测 | 置信度 |\n"
        table += "|---------|---------|---------|---------|---------|------------|---------|---------|---------|---------|---------|---------|---------|---------|\n"

        # 表格内容
        for point in self.buy_sell_points:
            fund_code = point.get('code', '')
            fund_name = point.get('name', '')
            category = point.get('category', '')
            net_asset_value = point.get('net_asset_value', '')
            daily_growth_rate = point.get('daily_growth_rate', '')
            one_year_return = point.get('one_year_return', '')
            long_term_score = f"{point.get('long_term_score', 0):.2f}"
            mid_term_score = f"{point.get('mid_term_score', 0):.2f}"
            short_term_score = f"{point.get('short_term_score', 0):.2f}"
            news_sentiment_score = f"{point.get('news_sentiment_score', 0):.2f}"
            combined_score = f"{point.get('combined_score', 0):.2f}"
            recommendation = point.get('recommendation', '观望')

            # 获取AI预测
            ai_prediction = 'neutral'
            ai_confidence = 0.5

            fund_ai_insights = self.ai_insights.get('funds', {}).get(point.get('code'), {})
            if fund_ai_insights:
                ai_prediction = fund_ai_insights.get('prediction', 'neutral')
                ai_confidence = fund_ai_insights.get('confidence', 0.5)

            # 添加表格行
            table += f"| {fund_code} | {fund_name} | {category} | {net_asset_value} | {daily_growth_rate} | {one_year_return} | {long_term_score} | {mid_term_score} | {short_term_score} | {news_sentiment_score} | {combined_score} | {recommendation} | {ai_prediction} | {ai_confidence:.2f} |\n"

        return table

    def _generate_html_table(self):
        """
        生成HTML格式的表格

        Returns:
            HTML表格字符串
        """
        # 表头
        table = "<table border=\"1\"><thead><tr>"
        table += "<th>基金代码</th>"
        table += "<th>基金名称</th>"
        table += "<th>基金类型</th>"
        table += "<th>最新净值</th>"
        table += "<th>日增长率</th>"
        table += "<th>近一年收益率</th>"
        table += "<th>长期得分</th>"
        table += "<th>中期得分</th>"
        table += "<th>短期得分</th>"
        table += "<th>新闻情感</th>"
        table += "<th>综合得分</th>"
        table += "<th>操作建议</th>"
        table += "<th>AI预测</th>"
        table += "<th>置信度</th>"
        table += "</tr></thead><tbody>"

        # 表格内容
        for point in self.buy_sell_points:
            fund_code = point.get('code', '')
            fund_name = point.get('name', '')
            category = point.get('category', '')
            net_asset_value = point.get('net_asset_value', '')
            daily_growth_rate = point.get('daily_growth_rate', '')
            one_year_return = point.get('one_year_return', '')
            long_term_score = f"{point.get('long_term_score', 0):.2f}"
            mid_term_score = f"{point.get('mid_term_score', 0):.2f}"
            short_term_score = f"{point.get('short_term_score', 0):.2f}"
            news_sentiment_score = f"{point.get('news_sentiment_score', 0):.2f}"
            combined_score = f"{point.get('combined_score', 0):.2f}"
            recommendation = point.get('recommendation', '观望')

            # 获取AI预测
            ai_prediction = 'neutral'
            ai_confidence = 0.5

            fund_ai_insights = self.ai_insights.get('funds', {}).get(point.get('code'), {})
            if fund_ai_insights:
                ai_prediction = fund_ai_insights.get('prediction', 'neutral')
                ai_confidence = fund_ai_insights.get('confidence', 0.5)

            # 添加表格行
            table += "<tr>"
            table += f"<td>{fund_code}</td>"
            table += f"<td>{fund_name}</td>"
            table += f"<td>{category}</td>"
            table += f"<td>{net_asset_value}</td>"
            table += f"<td>{daily_growth_rate}</td>"
            table += f"<td>{one_year_return}</td>"
            table += f"<td>{long_term_score}</td>"
            table += f"<td>{mid_term_score}</td>"
            table += f"<td>{short_term_score}</td>"
            table += f"<td>{news_sentiment_score}</td>"
            table += f"<td>{combined_score}</td>"
            table += f"<td>{recommendation}</td>"
            table += f"<td>{ai_prediction}</td>"
            table += f"<td>{ai_confidence:.2f}</td>"
            table += "</tr>"

        # 表格结尾
        table += "</tbody></table>"

        return table

    def _generate_excel_table(self):
        """
        生成Excel格式的表格

        Returns:
            DataFrame对象
        """
        data = []

        for point in self.buy_sell_points:
            fund_code = point.get('code', '')
            fund_name = point.get('name', '')
            category = point.get('category', '')
            net_asset_value = point.get('net_asset_value', '')
            daily_growth_rate = point.get('daily_growth_rate', '')
            one_year_return = point.get('one_year_return', '')
            long_term_score = point.get('long_term_score', 0)
            mid_term_score = point.get('mid_term_score', 0)
            short_term_score = point.get('short_term_score', 0)
            news_sentiment_score = point.get('news_sentiment_score', 0)
            combined_score = point.get('combined_score', 0)
            recommendation = point.get('recommendation', '观望')

            # 获取AI预测
            ai_prediction = 'neutral'
            ai_confidence = 0.5

            fund_ai_insights = self.ai_insights.get('funds', {}).get(point.get('code'), {})
            if fund_ai_insights:
                ai_prediction = fund_ai_insights.get('prediction', 'neutral')
                ai_confidence = fund_ai_insights.get('confidence', 0.5)

            data.append({
                '基金代码': fund_code,
                '基金名称': fund_name,
                '基金类型': category,
                '最新净值': net_asset_value,
                '日增长率': daily_growth_rate,
                '近一年收益率': one_year_return,
                '长期得分': long_term_score,
                '中期得分': mid_term_score,
                '短期得分': short_term_score,
                '新闻情感': news_sentiment_score,
                '综合得分': combined_score,
                '操作建议': recommendation,
                'AI预测': ai_prediction,
                '置信度': ai_confidence
            })

        return pd.DataFrame(data)

    def _generate_summary_table(self):
        """
        生成汇总表格

        Returns:
            汇总表格字符串
        """
        # 统计各种操作建议的数量
        buy_count = sum(1 for point in self.buy_sell_points if point.get('recommendation') == '买入')
        sell_count = sum(1 for point in self.buy_sell_points if point.get('recommendation') == '卖出')
        hold_count = sum(1 for point in self.buy_sell_points if point.get('recommendation') == '观望')

        # 统计各种AI预测的数量
        bullish_count = 0
        bearish_count = 0
        neutral_count = 0

        for point in self.buy_sell_points:
            fund_ai_insights = self.ai_insights.get('funds', {}).get(point.get('code'), {})
            if fund_ai_insights:
                prediction = fund_ai_insights.get('prediction', 'neutral')
                if prediction == 'bullish':
                    bullish_count += 1
                elif prediction == 'bearish':
                    bearish_count += 1
                else:
                    neutral_count += 1

        # 生成汇总表格
        if self.table_format == 'markdown':
            summary = "## 基金买卖点分析汇总

"
            summary += "| 统计项 | 数量 | 占比 |
"
            summary += "|-------|------|------|
"
            summary += f"| 买入建议 | {buy_count} | {buy_count/len(self.buy_sell_points)*100:.1f}% |
"
            summary += f"| 卖出建议 | {sell_count} | {sell_count/len(self.buy_sell_points)*100:.1f}% |
"
            summary += f"| 观望建议 | {hold_count} | {hold_count/len(self.buy_sell_points)*100:.1f}% |
"
            summary += f"| 看涨预测 | {bullish_count} | {bullish_count/len(self.buy_sell_points)*100:.1f}% |
"
            summary += f"| 看跌预测 | {bearish_count} | {bearish_count/len(self.buy_sell_points)*100:.1f}% |
"
            summary += f"| 中性预测 | {neutral_count} | {neutral_count/len(self.buy_sell_points)*100:.1f}% |
"

            return summary
        elif self.table_format == 'html':
            summary = "<h2>基金买卖点分析汇总</h2>
"
            summary += "<table border="1">
"
            summary += "<thead>
"
            summary += "<tr>
"
            summary += "<th>统计项</th>
"
            summary += "<th>数量</th>
"
            summary += "<th>占比</th>
"
            summary += "</tr>
"
            summary += "</thead>
"
            summary += "<tbody>
"
            summary += f"<tr><td>买入建议</td><td>{buy_count}</td><td>{buy_count/len(self.buy_sell_points)*100:.1f}%</td></tr>
"
            summary += f"<tr><td>卖出建议</td><td>{sell_count}</td><td>{sell_count/len(self.buy_sell_points)*100:.1f}%</td></tr>
"
            summary += f"<tr><td>观望建议</td><td>{hold_count}</td><td>{hold_count/len(self.buy_sell_points)*100:.1f}%</td></tr>
"
            summary += f"<tr><td>看涨预测</td><td>{bullish_count}</td><td>{bullish_count/len(self.buy_sell_points)*100:.1f}%</td></tr>
"
            summary += f"<tr><td>看跌预测</td><td>{bearish_count}</td><td>{bearish_count/len(self.buy_sell_points)*100:.1f}%</td></tr>
"
            summary += f"<tr><td>中性预测</td><td>{neutral_count}</td><td>{neutral_count/len(self.buy_sell_points)*100:.1f}%</td></tr>
"
            summary += "</tbody>
"
            summary += "</table>"

            return summary
        else:
            return "不支持的表格格式"

    def generate(self):
        """
        生成买卖点表格
        """
        logger.info("开始生成买卖点表格...")

        # 按日期生成文件名
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')

        # 生成主表格
        if self.table_format == 'markdown':
            table_content = self._generate_markdown_table()
            filename = os.path.join(self.output_dir, f'buy_sell_table_{today}.md')

            with open(filename, 'w', encoding='utf-8') as f:
                f.write("# 基金买卖点分析表

")
                f.write(table_content)
                f.write("

")
                f.write(self._generate_summary_table())

            logger.info(f"Markdown表格已保存到 {filename}")
        elif self.table_format == 'html':
            table_content = self._generate_html_table()
            filename = os.path.join(self.output_dir, f'buy_sell_table_{today}.html')

            with open(filename, 'w', encoding='utf-8') as f:
                f.write("<!DOCTYPE html>
")
                f.write("<html>
")
                f.write("<head>
")
                f.write("<meta charset="UTF-8">
")
                f.write("<title>基金买卖点分析表</title>
")
                f.write("<style>
")
                f.write("body { font-family: Arial, sans-serif; margin: 20px; }
")
                f.write("h1, h2 { color: #333; }
")
                f.write("table { border-collapse: collapse; width: 100%; }
")
                f.write("th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
")
                f.write("th { background-color: #f2f2f2; }
")
                f.write("tr:nth-child(even) { background-color: #f9f9f9; }
")
                f.write("tr:hover { background-color: #f1f1f1; }
")
                f.write("</style>
")
                f.write("</head>
")
                f.write("<body>
")
                f.write("<h1>基金买卖点分析表</h1>
")
                f.write(table_content)
                f.write(self._generate_summary_table())
                f.write("</body>
")
                f.write("</html>")

            logger.info(f"HTML表格已保存到 {filename}")
        elif self.table_format == 'excel':
            df = self._generate_excel_table()
            filename = os.path.join(self.output_dir, f'buy_sell_table_{today}.xlsx')

            df.to_excel(filename, index=False)
            logger.info(f"Excel表格已保存到 {filename}")
        else:
            logger.warning(f"不支持的表格格式: {self.table_format}")
