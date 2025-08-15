#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
买卖点分析模块
"""

import os
import json
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple

from ..utils.config import DATA_DIR, BUY_SELL_CONFIG

logger = logging.getLogger(__name__)

class BuySellAnalysis:
    """买卖点分析类"""

    def __init__(self, fund_data: List[Dict[str, Any]], long_term_data: List[Dict[str, Any]], 
                 mid_term_data: List[Dict[str, Any]], short_term_data: List[Dict[str, Any]], 
                 news_data: List[Dict[str, Any]]):
        """
        初始化买卖点分析器

        Args:
            fund_data: 基金数据列表
            long_term_data: 长期指标数据列表
            mid_term_data: 中期指标数据列表
            short_term_data: 短期指标数据列表
            news_data: 新闻数据列表
        """
        self.fund_data = fund_data
        self.long_term_data = long_term_data
        self.mid_term_data = mid_term_data
        self.short_term_data = short_term_data
        self.news_data = news_data

        self.config = BUY_SELL_CONFIG
        self.buy_threshold = self.config.get('buy_threshold', 0.7)
        self.sell_threshold = self.config.get('sell_threshold', 0.3)
        self.weight = self.config.get('weight', {
            'long_term': 0.4,
            'mid_term': 0.3,
            'short_term': 0.2,
            'news_sentiment': 0.1
        })

        self.output_dir = os.path.join(DATA_DIR, 'analysis', 'buy_sell')
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        logger.info("买卖点分析器初始化完成")

    def _analyze_news_sentiment(self, fund: Dict[str, Any]) -> float:
        """
        分析新闻情感

        Args:
            fund: 基金数据

        Returns:
            情感得分 (0-1)
        """
        fund_name = fund['name']
        fund_code = fund['code']

        # 简单的关键词匹配（实际应用中可以使用更复杂的NLP模型）
        positive_keywords = ['上涨', '增长', '收益', '盈利', '利好', '反弹', '走强', '看好', '买入', '增持']
        negative_keywords = ['下跌', '亏损', '风险', '利空', '回调', '走弱', '看空', '卖出', '减持']

        # 筛选与基金相关的新闻
        relevant_news = []
        for news in self.news_data:
            content = news.get('content', '')
            title = news.get('title', '')

            # 检查新闻是否与基金相关
            if fund_name in content or fund_name in title or fund_code in content or fund_code in title:
                relevant_news.append(news)

        if not relevant_news:
            return 0.5  # 没有相关新闻，返回中性值

        # 计算情感得分
        positive_count = 0
        negative_count = 0

        for news in relevant_news:
            content = news.get('content', '') + ' ' + news.get('title', '')

            for keyword in positive_keywords:
                positive_count += content.count(keyword)

            for keyword in negative_keywords:
                negative_count += content.count(keyword)

        # 计算情感得分
        total_count = positive_count + negative_count
        if total_count == 0:
            return 0.5  # 没有情感关键词，返回中性值

        sentiment_score = positive_count / total_count

        logger.debug(f"基金 {fund_name}({fund_code}) 的新闻情感得分: {sentiment_score:.2f}")
        return sentiment_score

    def _analyze_fund_indicators(self, fund: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析基金指标

        Args:
            fund: 基金数据

        Returns:
            指标分析结果
        """
        fund_code = fund['code']
        fund_name = fund['name']

        # 获取基金的长期指标
        long_term_indicators = None
        for item in self.long_term_data:
            if item.get('code') == fund_code:
                long_term_indicators = item.get('long_term_indicators', {})
                break

        # 获取基金的中期指标
        mid_term_indicators = None
        for item in self.mid_term_data:
            if item.get('code') == fund_code:
                mid_term_indicators = item.get('mid_term_indicators', {})
                break

        # 获取基金的短期指标
        short_term_indicators = None
        for item in self.short_term_data:
            if item.get('code') == fund_code:
                short_term_indicators = item.get('short_term_indicators', {})
                break

        if not long_term_indicators or not mid_term_indicators or not short_term_indicators:
            logger.warning(f"基金 {fund_name}({fund_code}) 缺少指标数据，无法进行分析")
            return {
                'long_term_score': 0.5,
                'mid_term_score': 0.5,
                'short_term_score': 0.5,
                'news_sentiment_score': 0.5,
                'combined_score': 0.5,
                'recommendation': '观望'
            }

        # 分析长期指标
        long_term_signals = long_term_indicators.get('signals', {})
        long_term_score = 0.5  # 默认中性

        if long_term_signals.get('combined') == 'bullish':
            long_term_score = 0.8
        elif long_term_signals.get('combined') == 'bearish':
            long_term_score = 0.2

        # 分析中期指标
        mid_term_signals = mid_term_indicators.get('signals', {})
        mid_term_score = 0.5  # 默认中性

        if mid_term_signals.get('combined') == 'bullish':
            mid_term_score = 0.8
        elif mid_term_signals.get('combined') == 'bearish':
            mid_term_score = 0.2

        # 分析短期指标
        short_term_signals = short_term_indicators.get('signals', {})
        short_term_score = 0.5  # 默认中性

        if short_term_signals.get('combined') == 'bullish':
            short_term_score = 0.8
        elif short_term_signals.get('combined') == 'bearish':
            short_term_score = 0.2

        # 分析新闻情感
        news_sentiment_score = self._analyze_news_sentiment(fund)

        # 计算综合得分
        combined_score = (
            long_term_score * self.weight.get('long_term', 0.4) +
            mid_term_score * self.weight.get('mid_term', 0.3) +
            short_term_score * self.weight.get('short_term', 0.2) +
            news_sentiment_score * self.weight.get('news_sentiment', 0.1)
        )

        # 生成建议
        if combined_score >= self.buy_threshold:
            recommendation = '买入'
        elif combined_score <= self.sell_threshold:
            recommendation = '卖出'
        else:
            recommendation = '观望'

        logger.debug(f"基金 {fund_name}({fund_code}) 的综合得分: {combined_score:.2f}, 建议: {recommendation}")

        return {
            'long_term_score': long_term_score,
            'mid_term_score': mid_term_score,
            'short_term_score': short_term_score,
            'news_sentiment_score': news_sentiment_score,
            'combined_score': combined_score,
            'recommendation': recommendation,
            'long_term_signals': long_term_signals,
            'mid_term_signals': mid_term_signals,
            'short_term_signals': short_term_signals
        }

    def analyze(self) -> List[Dict[str, Any]]:
        """
        分析所有基金的买卖点

        Returns:
            买卖点分析结果列表
        """
        logger.info("开始分析所有基金的买卖点...")

        # 使用多线程分析
        from ..utils.thread_pool import run_with_thread_pool

        # 准备任务列表
        tasks = [{'fund': fund} for fund in self.fund_data]

        # 执行任务
        analysis_results = run_with_thread_pool(
            lambda kwargs: self._analyze_fund_indicators(kwargs['fund']),
            tasks
        )

        # 将分析结果添加到基金数据中
        buy_sell_points = []
        for i, fund in enumerate(self.fund_data):
            if i < len(analysis_results):
                result = analysis_results[i]
                fund['buy_sell_analysis'] = result
                buy_sell_points.append({
                    'code': fund['code'],
                    'name': fund['name'],
                    'category': fund.get('category', ''),
                    'net_asset_value': fund.get('net_asset_value', ''),
                    'daily_growth_rate': fund.get('daily_growth_rate', ''),
                    'one_year_return': fund.get('one_year_return', ''),
                    'long_term_score': result.get('long_term_score', 0.5),
                    'mid_term_score': result.get('mid_term_score', 0.5),
                    'short_term_score': result.get('short_term_score', 0.5),
                    'news_sentiment_score': result.get('news_sentiment_score', 0.5),
                    'combined_score': result.get('combined_score', 0.5),
                    'recommendation': result.get('recommendation', '观望'),
                    'analysis_time': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
                })

        # 保存分析结果
        self.save_analysis_results(buy_sell_points)

        logger.info(f"成功分析 {len(buy_sell_points)} 只基金的买卖点")
        return buy_sell_points

    def save_analysis_results(self, analysis_results: List[Dict[str, Any]]) -> None:
        """
        保存分析结果

        Args:
            analysis_results: 分析结果列表
        """
        if not analysis_results:
            logger.warning("分析结果列表为空，不保存数据")
            return

        # 按日期保存
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        filename = os.path.join(self.output_dir, f'buy_sell_analysis_{today}.json')

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(analysis_results, f, ensure_ascii=False, indent=2)
            logger.info(f"买卖点分析结果已保存到 {filename}")
        except Exception as e:
            logger.error(f"保存买卖点分析结果失败: {str(e)}", exc_info=True)
