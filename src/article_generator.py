#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文章生成模块
根据基金分析结果生成买卖操作文章
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
    ARTICLE_CONFIG, OUTPUT_DIR, ANALYSIS_RESULTS_DIR, ARTICLES_DIR,
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

class ArticleGenerator:
    """文章生成器类"""

    def __init__(self, fund_type: str = 'mixed'):
        """
        初始化文章生成器

        Args:
            fund_type: 基金类型
        """
        self.fund_type = fund_type
        self.template_file = ARTICLE_CONFIG['template_file']

        # 加载文章模板
        self.template = self._load_template()

        # 加载分析提示词
        self.analysis_prompt = self._load_analysis_prompt()

    def _load_template(self) -> str:
        """加载文章模板"""
        try:
            with open(self.template_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"加载文章模板失败: {e}")
            # 使用默认模板
            return """
            # {title}

            {date}

            ## 市场概况

            {market_overview}

            ## 基金表现

            {fund_performance}

            ## 技术分析

            {technical_analysis}

            ## 基本面分析

            {fundamental_analysis}

            ## 新闻影响

            {news_impact}

            ## 买卖建议

            {suggestion}

            ### 操作原因

            {reasoning}

            ## 风险提示

            {risk_warning}

            ---
            *本文由基金分析系统自动生成，仅供参考，不构成投资建议。*
            """

    def _load_analysis_prompt(self) -> str:
        """加载分析提示词"""
        prompt_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                 'templates', 'analysis_prompt.txt')

        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"加载分析提示词失败: {e}")
            return ""

    def generate_article(self, analysis_result: Dict[str, Any], 
                        fund_data: Dict[str, Any], 
                        news_data: List[Dict[str, Any]]) -> str:
        """
        生成文章

        Args:
            analysis_result: 分析结果
            fund_data: 基金数据
            news_data: 新闻数据

        Returns:
            生成的文章
        """
        logger.info(f"开始生成{self.fund_type}基金文章")

        # 构建文章数据
        article_data = {
            'title': f"{self.fund_type}基金买卖点分析 - {datetime.now().strftime('%Y-%m-%d')}",
            'date': f"发布时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            'fund_type': self.fund_type,
            'fund_name': fund_data.get('name', '未知基金'),
            'fund_code': fund_data.get('code', '未知代码'),
            'market_overview': analysis_result.get('market_overview', '暂无市场概况'),
            'fund_performance': analysis_result.get('fund_performance', '暂无基金表现分析'),
            'technical_analysis': analysis_result.get('technical_analysis', '暂无技术分析'),
            'fundamental_analysis': analysis_result.get('fundamental_analysis', '暂无基本面分析'),
            'news_impact': analysis_result.get('news_impact', '暂无新闻影响分析'),
            'suggestion': f"{self._format_suggestion(analysis_result.get('suggestion', '持有'))}",
            'reasoning': analysis_result.get('reasoning', '暂无操作原因分析'),
            'risk_warning': analysis_result.get('risk_warning', '暂无风险提示'),
            'confidence': self._format_confidence(analysis_result.get('confidence', 0))
        }

        # 生成文章
        article = self.template.format(**article_data)

        # 添加文章摘要
        summary = self._generate_summary(article_data)
        article = f"{summary}

{article}"

        # 添加热门基金推荐
        recommended_funds = self._generate_recommendation(fund_data, news_data)
        article = f"{article}

## 热门基金推荐

{recommended_funds}"

        return article

    def _format_suggestion(self, suggestion: str) -> str:
        """
        格式化买卖建议

        Args:
            suggestion: 原始建议

        Returns:
            格式化后的建议
        """
        if suggestion == '买入':
            return """
            ### 买入建议
            **建议买入**

            根据当前市场状况和基金表现，建议投资者可以考虑适量买入该基金。
            """
        elif suggestion == '卖出':
            return """
            ### 卖出建议
            **建议卖出**

            根据当前市场状况和基金表现，建议投资者可以考虑卖出该基金。
            """
        else:
            return """
            ### 持有建议
            **建议持有**

            根据当前市场状况和基金表现，建议投资者继续持有该基金，密切关注市场变化。
            """

    def _format_confidence(self, confidence: float) -> str:
        """
        格式化置信度

        Args:
            confidence: 置信度值

        Returns:
            格式化后的置信度
        """
        if confidence >= 0.8:
            return "高"
        elif confidence >= 0.6:
            return "中高"
        elif confidence >= 0.4:
            return "中"
        else:
            return "低"

    def _generate_summary(self, article_data: Dict[str, Any]) -> str:
        """
        生成文章摘要

        Args:
            article_data: 文章数据

        Returns:
            文章摘要
        """
        return f"""
        ## 摘要

        本文对{article_data['fund_name']}（代码：{article_data['fund_code']}）进行了全面分析，涵盖市场概况、基金表现、技术分析、基本面分析和新闻影响等方面。

        分析显示，{article_data['fund_name']}当前建议为{article_data['suggestion'].split('建议')[-1].strip()}，分析置信度为{self._format_confidence(article_data.get('confidence', 0))}。

        主要原因：{article_data['reasoning'][:100]}...
        """

    def _generate_recommendation(self, fund_data: Dict[str, Any], 
                              news_data: List[Dict[str, Any]]) -> str:
        """
        生成基金推荐

        Args:
            fund_data: 基金数据
            news_data: 新闻数据

        Returns:
            基金推荐
        """
        # 这里可以根据实际需求实现更复杂的推荐逻辑
        # 简单实现：返回一个示例推荐

        return """
        1. **华夏成长混合** (000001): 历史悠久，业绩稳定，适合长期持有。
        2. **易方达蓝筹精选混合** (005827): 聚焦优质蓝筹股，长期表现优异。
        3. **广发稳健增长混合** (270001): 注重风险控制，适合稳健型投资者。

        *注：以上推荐仅供参考，投资者应根据自身风险承受能力做出投资决策。*
        """

    def generate_batch_article(self, analysis_results: Dict[str, Dict[str, Any]], 
                            fund_data_list: List[Dict[str, Any]], 
                            news_data_list: List[Dict[str, Any]]) -> str:
        """
        生成批量分析文章

        Args:
            analysis_results: 批量分析结果
            fund_data_list: 基金数据列表
            news_data_list: 新闻数据列表

        Returns:
            批量分析文章
        """
        logger.info(f"开始生成{self.fund_type}基金批量分析文章")

        # 生成文章标题和开头
        title = f"{self.fund_type}基金批量分析报告 - {datetime.now().strftime('%Y-%m-%d')}"
        date = f"发布时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        # 生成市场概况
        market_overview = self._generate_market_overview(analysis_results, fund_data_list)

        # 生成基金表现总结
        performance_summary = self._generate_performance_summary(analysis_results)

        # 生成买卖建议总结
        suggestion_summary = self._generate_suggestion_summary(analysis_results)

        # 生成热门基金推荐
        recommended_funds = self._generate_batch_recommendation(analysis_results, fund_data_list)

        # 构建文章
        article = f"""
        # {title}

        {date}

        ## 市场概况

        {market_overview}

        ## 基金表现总结

        {performance_summary}

        ## 买卖建议总结

        {suggestion_summary}

        ## 热门基金推荐

        {recommended_funds}

        ---
        *本文由基金分析系统自动生成，仅供参考，不构成投资建议。*
        """

        return article

    def _generate_market_overview(self, analysis_results: Dict[str, Dict[str, Any]], 
                                fund_data_list: List[Dict[str, Any]]) -> str:
        """
        生成市场概况

        Args:
            analysis_results: 批量分析结果
            fund_data_list: 基金数据列表

        Returns:
            市场概况
        """
        # 统计买入、卖出、持有建议的数量
        buy_count = sum(1 for r in analysis_results.values() if r.get('suggestion') == '买入')
        sell_count = sum(1 for r in analysis_results.values() if r.get('suggestion') == '卖出')
        hold_count = sum(1 for r in analysis_results.values() if r.get('suggestion') == '持有')

        # 计算平均置信度
        avg_confidence = np.mean([r.get('confidence', 0) for r in analysis_results.values()])

        # 生成市场概况
        overview = f"""
        根据对{len(analysis_results)}只{self.fund_type}基金的分析，当前市场呈现以下特点：

        - 买入建议：{buy_count}只基金
        - 卖出建议：{sell_count}只基金
        - 持有建议：{hold_count}只基金
        - 平均置信度：{self._format_confidence(avg_confidence)}

        总体来看，当前{self.fund_type}基金市场{'偏多' if buy_count > sell_count else '偏空' if sell_count > buy_count else '中性'}，
        投资者应根据自身风险承受能力和投资目标做出相应决策。
        """

        return overview

    def _generate_performance_summary(self, analysis_results: Dict[str, Dict[str, Any]]) -> str:
        """
        生成基金表现总结

        Args:
            analysis_results: 批量分析结果

        Returns:
            基金表现总结
        """
        # 这里可以根据实际需求实现更复杂的总结逻辑
        # 简单实现：返回一个示例总结

        return """
        根据分析结果，大部分{self.fund_type}基金近期表现{'良好' if True else '一般'}，部分基金显示出较强的增长潜力，
        但同时也存在一定风险。投资者在选择基金时应综合考虑基金的历史业绩、基金经理能力、投资策略等因素。
        """

    def _generate_suggestion_summary(self, analysis_results: Dict[str, Dict[str, Any]]) -> str:
        """
        生成买卖建议总结

        Args:
            analysis_results: 批量分析结果

        Returns:
            买卖建议总结
        """
        # 统计买入、卖出、持有建议的数量
        buy_count = sum(1 for r in analysis_results.values() if r.get('suggestion') == '买入')
        sell_count = sum(1 for r in analysis_results.values() if r.get('suggestion') == '卖出')
        hold_count = sum(1 for r in analysis_results.values() if r.get('suggestion') == '持有')

        # 生成建议总结
        summary = f"""
        根据分析结果，我们建议：

        - 买入{buy_count}只基金：这些基金显示出较好的增长潜力和投资价值。
        - 卖出{sell_count}只基金：这些基金可能面临一定风险或增长乏力。
        - 持有{hold_count}只基金：这些基金表现相对稳定，建议继续观察。

        投资者应根据自身风险承受能力和投资目标，合理配置资产，分散投资风险。
        """

        return summary

    def _generate_batch_recommendation(self, analysis_results: Dict[str, Dict[str, Any]], 
                                     fund_data_list: List[Dict[str, Any]]) -> str:
        """
        生成批量基金推荐

        Args:
            analysis_results: 批量分析结果
            fund_data_list: 基金数据列表

        Returns:
            基金推荐
        """
        # 筛选买入建议的基金
        buy_funds = [
            (code, result) for code, result in analysis_results.items() 
            if result.get('suggestion') == '买入'
        ]

        # 按置信度排序
        buy_funds.sort(key=lambda x: x[1].get('confidence', 0), reverse=True)

        # 生成推荐列表
        recommendations = []
        for i, (code, result) in enumerate(buy_funds[:5]):  # 只推荐前5只
            fund_name = next((f.get('name', '未知基金') for f in fund_data_list if f.get('code') == code), '未知基金')
            recommendations.append(f"{i+1}. **{fund_name}** (代码：{code}): 置信度 {self._format_confidence(result.get('confidence', 0))}")

        return "
".join(recommendations) if recommendations else "暂无特别推荐的基金。"

    def save_article(self, article: str, filename: Optional[str] = None) -> str:
        """
        保存文章

        Args:
            article: 文章内容
            filename: 文件名，如果为None则自动生成

        Returns:
            保存的文件路径
        """
        os.makedirs(ARTICLES_DIR, exist_ok=True)

        if filename is None:
            filename = f"{self.fund_type}_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        output_file = os.path.join(ARTICLES_DIR, filename)

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(article)
            logger.info(f"文章已保存至: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"保存文章失败: {e}")
            raise

    def generate_and_save_article(self, analysis_result: Dict[str, Any], 
                                fund_data: Dict[str, Any], 
                                news_data: List[Dict[str, Any]]) -> str:
        """
        生成并保存文章

        Args:
            analysis_result: 分析结果
            fund_data: 基金数据
            news_data: 新闻数据

        Returns:
            保存的文件路径
        """
        article = self.generate_article(analysis_result, fund_data, news_data)
        return self.save_article(article)

    def generate_and_save_batch_article(self, analysis_results: Dict[str, Dict[str, Any]], 
                                      fund_data_list: List[Dict[str, Any]], 
                                      news_data_list: List[Dict[str, Any]]) -> str:
        """
        生成并保存批量分析文章

        Args:
            analysis_results: 批量分析结果
            fund_data_list: 基金数据列表
            news_data_list: 新闻数据列表

        Returns:
            保存的文件路径
        """
        article = self.generate_batch_article(analysis_results, fund_data_list, news_data_list)
        return self.save_article(article)
