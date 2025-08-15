#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
操作文章生成模块
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional

from ..utils.config import OUTPUT_DIR, REPORT_CONFIG

logger = logging.getLogger(__name__)

class GenerateArticle:
    """操作文章生成类"""

    def __init__(self, buy_sell_points: List[Dict[str, Any]], ai_insights: Dict[str, Any], 
                 news_data: List[Dict[str, Any]], fund_data: List[Dict[str, Any]]):
        """
        初始化文章生成器

        Args:
            buy_sell_points: 买卖点分析结果列表
            ai_insights: AI分析结果
            news_data: 新闻数据列表
            fund_data: 基金数据列表
        """
        self.buy_sell_points = buy_sell_points
        self.ai_insights = ai_insights
        self.news_data = news_data
        self.fund_data = fund_data

        self.config = REPORT_CONFIG
        self.article_template = self.config.get('article_template', 'default')

        self.output_dir = os.path.join(OUTPUT_DIR, 'articles')
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        logger.info("操作文章生成器初始化完成")

    def _extract_key_news(self) -> List[Dict[str, Any]]:
        """
        提取关键新闻

        Returns:
            关键新闻列表
        """
        # 按新闻来源和时间筛选重要新闻
        key_news = []

        # 简单实现：选择前5条新闻
        for news in self.news_data[:5]:
            key_news.append({
                'title': news.get('title', ''),
                'source': news.get('source', ''),
                'publish_date': news.get('publish_date', ''),
                'summary': news.get('content', '')[:200] + '...' if len(news.get('content', '')) > 200 else news.get('content', '')
            })

        return key_news

    def _extract_top_funds(self, recommendation: str) -> List[Dict[str, Any]]:
        """
        提取推荐操作的基金

        Args:
            recommendation: 推荐操作类型 (买入/卖出/观望)

        Returns:
            推荐操作的基金列表
        """
        # 筛选特定推荐操作的基金
        filtered_funds = [point for point in self.buy_sell_points if point.get('recommendation') == recommendation]

        # 按综合得分排序
        if recommendation == '买入':
            filtered_funds.sort(key=lambda x: x.get('combined_score', 0), reverse=True)
        else:  # 卖出
            filtered_funds.sort(key=lambda x: x.get('combined_score', 0))

        # 选择前5只基金
        top_funds = filtered_funds[:5]

        # 补充基金详细信息
        result = []
        for fund in top_funds:
            fund_code = fund.get('code', '')

            # 查找基金详细信息
            fund_detail = next((f for f in self.fund_data if f.get('code') == fund_code), {})

            # 获取AI分析结果
            ai_analysis = self.ai_insights.get('funds', {}).get(fund_code, {})

            result.append({
                'code': fund_code,
                'name': fund.get('name', ''),
                'category': fund.get('category', ''),
                'net_asset_value': fund.get('net_asset_value', ''),
                'daily_growth_rate': fund.get('daily_growth_rate', ''),
                'one_year_return': fund.get('one_year_return', ''),
                'combined_score': fund.get('combined_score', 0),
                'ai_prediction': ai_analysis.get('prediction', 'neutral'),
                'ai_confidence': ai_analysis.get('confidence', 0),
                'ai_reason': ai_analysis.get('reason', '')
            })

        return result

    def _generate_article_content(self) -> str:
        """
        生成文章内容

        Returns:
            文章内容
        """
        # 提取关键新闻
        key_news = self._extract_key_news()

        # 提取推荐买入的基金
        buy_funds = self._extract_top_funds('买入')

        # 提取推荐卖出的基金
        sell_funds = self._extract_top_funds('卖出')

        # 提取推荐观望的基金
        hold_funds = self._extract_top_funds('观望')

        # 生成文章内容
        content = "# 基金买卖操作建议报告

"

        # 添加报告日期
        from datetime import datetime
        report_date = datetime.now().strftime('%Y年%m月%d日')
        content += f"**报告日期：{report_date}**

"

        # 添加市场概述
        content += "## 市场概述

"
        content += "近期基金市场波动较大，各类型基金表现不一。通过综合分析长期、中期和短期指标，结合市场新闻和AI模型预测，我们为投资者提供以下买卖操作建议。

"

        # 添加关键新闻
        content += "## 关键市场新闻

"
        for news in key_news:
            content += f"### {news['title']}

"
            content += f"**来源：** {news['source']}  
"
            content += f"**日期：** {news['publish_date']}  
"
            content += f"**摘要：** {news['summary']}

"

        # 添加买入建议
        content += "## 推荐买入基金

"
        content += "以下是我们根据综合分析推荐的买入基金，这些基金在各项指标上表现良好，具有较好的投资价值：

"

        for fund in buy_funds:
            content += f"### {fund['name']} ({fund['code']})

"
            content += f"**基金类型：** {fund['category']}  
"
            content += f"**最新净值：** {fund['net_asset_value']}  
"
            content += f"**日增长率：** {fund['daily_growth_rate']}  
"
            content += f"**近一年收益率：** {fund['one_year_return']}  
"
            content += f"**综合得分：** {fund['combined_score']:.2f}  
"
            content += f"**AI预测：** {fund['ai_prediction']} (置信度: {fund['ai_confidence']:.2f})  
"
            content += f"**分析原因：** {fund['ai_reason']}

"

        # 添加卖出建议
        content += "## 推荐卖出基金

"
        content += "以下是我们根据综合分析推荐的卖出基金，这些基金在各项指标上表现不佳，可能存在较大风险：

"

        for fund in sell_funds:
            content += f"### {fund['name']} ({fund['code']})

"
            content += f"**基金类型：** {fund['category']}  
"
            content += f"**最新净值：** {fund['net_asset_value']}  
"
            content += f"**日增长率：** {fund['daily_growth_rate']}  
"
            content += f"**近一年收益率：** {fund['one_year_return']}  
"
            content += f"**综合得分：** {fund['combined_score']:.2f}  
"
            content += f"**AI预测：** {fund['ai_prediction']} (置信度: {fund['ai_confidence']:.2f})  
"
            content += f"**分析原因：** {fund['ai_reason']}

"

        # 添加观望建议
        content += "## 推荐观望基金

"
        content += "以下是我们根据综合分析建议观望的基金，这些基金表现一般，建议投资者保持关注，等待更好的买入或卖出时机：

"

        for fund in hold_funds:
            content += f"### {fund['name']} ({fund['code']})

"
            content += f"**基金类型：** {fund['category']}  
"
            content += f"**最新净值：** {fund['net_asset_value']}  
"
            content += f"**日增长率：** {fund['daily_growth_rate']}  
"
            content += f"**近一年收益率：** {fund['one_year_return']}  
"
            content += f"**综合得分：** {fund['combined_score']:.2f}  
"
            content += f"**AI预测：** {fund['ai_prediction']} (置信度: {fund['ai_confidence']:.2f})  
"
            content += f"**分析原因：** {fund['ai_reason']}

"

        # 添加投资建议
        content += "## 投资建议

"
        content += "1. **分散投资**：不要将所有资金投入单一基金，建议分散投资于不同类型的基金，降低风险。

"
        content += "2. **长期持有**：对于优质基金，建议长期持有，避免频繁交易导致的高额手续费。

"
        content += "3. **定期调整**：定期审视投资组合，根据市场变化和基金表现调整投资策略。

"
        content += "4. **关注风险**：投资有风险，入市需谨慎。请根据自身风险承受能力做出投资决策。

"

        # 添加免责声明
        content += "## 免责声明

"
        content += "本报告仅供参考，不构成投资建议。投资者应根据自身情况谨慎决策，对因使用本报告所导致的任何损失，本报告作者不承担责任。

"

        return content

    def generate(self) -> None:
        """
        生成操作文章
        """
        logger.info("开始生成操作文章...")

        # 生成文章内容
        content = self._generate_article_content()

        # 按日期生成文件名
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        filename = os.path.join(self.output_dir, f'investment_advice_{today}.md')

        # 保存文章
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"操作文章已保存到 {filename}")
