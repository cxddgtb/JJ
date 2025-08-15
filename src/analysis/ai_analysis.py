#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI分析模块
"""

import os
import json
import logging
import pandas as pd
import numpy as np
import requests
from typing import Dict, List, Any, Optional, Tuple

from ..utils.config import DATA_DIR, AI_CONFIG

logger = logging.getLogger(__name__)

class AIAnalysis:
    """AI分析类"""

    def __init__(self, fund_data: List[Dict[str, Any]], buy_sell_points: List[Dict[str, Any]], 
                 news_data: List[Dict[str, Any]]):
        """
        初始化AI分析器

        Args:
            fund_data: 基金数据列表
            buy_sell_points: 买卖点分析结果列表
            news_data: 新闻数据列表
        """
        self.fund_data = fund_data
        self.buy_sell_points = buy_sell_points
        self.news_data = news_data

        self.config = AI_CONFIG
        self.model_name = self.config.get('model_name', 'bert-base-chinese')
        self.max_length = self.config.get('max_length', 512)
        self.batch_size = self.config.get('batch_size', 16)
        self.threshold = self.config.get('threshold', 0.7)

        self.output_dir = os.path.join(DATA_DIR, 'analysis', 'ai')
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # 尝试使用HuggingFace的Transformers库进行本地分析
        self.use_local_model = False
        try:
            from transformers import BertTokenizer, BertModel, pipeline
            self.tokenizer = BertTokenizer.from_pretrained(self.model_name)
            self.model = BertModel.from_pretrained(self.model_name)
            self.sentiment_analyzer = pipeline('sentiment-analysis', model=self.model_name, tokenizer=self.tokenizer)
            self.use_local_model = True
            logger.info(f"成功加载本地模型: {self.model_name}")
        except Exception as e:
            logger.warning(f"无法加载本地模型 {self.model_name}: {str(e)}")
            logger.info("将使用在线API进行AI分析")

        logger.info("AI分析器初始化完成")

    def _analyze_news_with_api(self, news: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用在线API分析新闻

        Args:
            news: 新闻数据

        Returns:
            新闻分析结果
        """
        title = news.get('title', '')
        content = news.get('content', '')

        if not title and not content:
            return {
                'sentiment': 'neutral',
                'confidence': 0.5,
                'keywords': [],
                'summary': ''
            }

        text = f"{title} {content}"

        # 使用在线API进行情感分析
        try:
            # 这里使用一个公开的NLP API，实际使用时可以替换为其他API
            # 注意：实际应用中可能需要API密钥，这里仅作为示例
            api_url = "https://api.example.com/sentiment"
            headers = {
                "Content-Type": "application/json",
                # "Authorization": "Bearer YOUR_API_KEY"
            }
            data = {
                "text": text,
                "max_length": self.max_length
            }

            response = requests.post(api_url, headers=headers, json=data, timeout=10)

            if response.status_code == 200:
                result = response.json()

                return {
                    'sentiment': result.get('sentiment', 'neutral'),
                    'confidence': result.get('confidence', 0.5),
                    'keywords': result.get('keywords', []),
                    'summary': result.get('summary', '')
                }
            else:
                logger.warning(f"API请求失败，状态码: {response.status_code}")
                return {
                    'sentiment': 'neutral',
                    'confidence': 0.5,
                    'keywords': [],
                    'summary': ''
                }
        except Exception as e:
            logger.warning(f"使用API分析新闻失败: {str(e)}")
            return {
                'sentiment': 'neutral',
                'confidence': 0.5,
                'keywords': [],
                'summary': ''
            }

    def _analyze_news_with_local_model(self, news: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用本地模型分析新闻

        Args:
            news: 新闻数据

        Returns:
            新闻分析结果
        """
        title = news.get('title', '')
        content = news.get('content', '')

        if not title and not content:
            return {
                'sentiment': 'neutral',
                'confidence': 0.5,
                'keywords': [],
                'summary': ''
            }

        text = f"{title} {content}"

        # 截断文本到最大长度
        if len(text) > self.max_length:
            text = text[:self.max_length]

        try:
            # 使用本地模型进行情感分析
            sentiment_result = self.sentiment_analyzer(text)[0]

            # 提取关键词（简单实现，实际应用中可以使用更复杂的方法）
            words = text.split()
            word_freq = {}
            for word in words:
                if len(word) > 1:  # 忽略单字
                    word_freq[word] = word_freq.get(word, 0) + 1

            # 按频率排序并取前5个关键词
            keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            keywords = [word for word, freq in keywords]

            # 生成摘要（简单实现，实际应用中可以使用更复杂的摘要生成方法）
            summary = text[:100] + '...' if len(text) > 100 else text

            return {
                'sentiment': sentiment_result['label'].lower(),
                'confidence': sentiment_result['score'],
                'keywords': keywords,
                'summary': summary
            }
        except Exception as e:
            logger.warning(f"使用本地模型分析新闻失败: {str(e)}")
            return {
                'sentiment': 'neutral',
                'confidence': 0.5,
                'keywords': [],
                'summary': ''
            }

    def _analyze_news(self, news: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析新闻

        Args:
            news: 新闻数据

        Returns:
            新闻分析结果
        """
        if self.use_local_model:
            return self._analyze_news_with_local_model(news)
        else:
            return self._analyze_news_with_api(news)

    def _analyze_fund_with_api(self, fund: Dict[str, Any], buy_sell_point: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用在线API分析基金

        Args:
            fund: 基金数据
            buy_sell_point: 买卖点分析结果

        Returns:
            基金AI分析结果
        """
        fund_name = fund['name']
        fund_code = fund['code']

        # 准备分析数据
        analysis_data = {
            'fund_name': fund_name,
            'fund_code': fund_code,
            'category': fund.get('category', ''),
            'net_asset_value': fund.get('net_asset_value', ''),
            'daily_growth_rate': fund.get('daily_growth_rate', ''),
            'one_year_return': fund.get('one_year_return', ''),
            'recommendation': buy_sell_point.get('recommendation', '观望'),
            'long_term_score': buy_sell_point.get('long_term_score', 0.5),
            'mid_term_score': buy_sell_point.get('mid_term_score', 0.5),
            'short_term_score': buy_sell_point.get('short_term_score', 0.5),
            'news_sentiment_score': buy_sell_point.get('news_sentiment_score', 0.5),
            'combined_score': buy_sell_point.get('combined_score', 0.5)
        }

        # 使用在线API进行分析
        try:
            # 这里使用一个公开的AI分析API，实际使用时可以替换为其他API
            # 注意：实际应用中可能需要API密钥，这里仅作为示例
            api_url = "https://api.example.com/fund_analysis"
            headers = {
                "Content-Type": "application/json",
                # "Authorization": "Bearer YOUR_API_KEY"
            }

            response = requests.post(api_url, headers=headers, json=analysis_data, timeout=30)

            if response.status_code == 200:
                result = response.json()

                return {
                    'prediction': result.get('prediction', 'neutral'),
                    'confidence': result.get('confidence', 0.5),
                    'reason': result.get('reason', ''),
                    'risk_level': result.get('risk_level', 'medium'),
                    'expected_return': result.get('expected_return', 0.0),
                    'time_horizon': result.get('time_horizon', 'medium')
                }
            else:
                logger.warning(f"API请求失败，状态码: {response.status_code}")
                return {
                    'prediction': 'neutral',
                    'confidence': 0.5,
                    'reason': '',
                    'risk_level': 'medium',
                    'expected_return': 0.0,
                    'time_horizon': 'medium'
                }
        except Exception as e:
            logger.warning(f"使用API分析基金失败: {str(e)}")
            return {
                'prediction': 'neutral',
                'confidence': 0.5,
                'reason': '',
                'risk_level': 'medium',
                'expected_return': 0.0,
                'time_horizon': 'medium'
            }

    def _analyze_fund_with_local_model(self, fund: Dict[str, Any], buy_sell_point: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用本地模型分析基金

        Args:
            fund: 基金数据
            buy_sell_point: 买卖点分析结果

        Returns:
            基金AI分析结果
        """
        fund_name = fund['name']
        fund_code = fund['code']

        # 准备分析数据
        combined_score = buy_sell_point.get('combined_score', 0.5)
        recommendation = buy_sell_point.get('recommendation', '观望')

        # 基于综合得分和推荐进行预测
        if combined_score >= 0.7:
            prediction = 'bullish'
            reason = f"基金 {fund_name}({fund_code}) 的各项指标表现良好，综合得分为 {combined_score:.2f}，建议{recommendation}。"
            risk_level = 'low'
            expected_return = 0.1
            time_horizon = 'long'
        elif combined_score <= 0.3:
            prediction = 'bearish'
            reason = f"基金 {fund_name}({fund_code}) 的各项指标表现不佳，综合得分为 {combined_score:.2f}，建议{recommendation}。"
            risk_level = 'high'
            expected_return = -0.05
            time_horizon = 'short'
        else:
            prediction = 'neutral'
            reason = f"基金 {fund_name}({fund_code}) 的各项指标表现一般，综合得分为 {combined_score:.2f}，建议{recommendation}。"
            risk_level = 'medium'
            expected_return = 0.02
            time_horizon = 'medium'

        # 置信度基于综合得分与阈值的距离
        if recommendation == '买入':
            confidence = min(1.0, (combined_score - 0.5) * 2)
        elif recommendation == '卖出':
            confidence = min(1.0, (0.5 - combined_score) * 2)
        else:
            confidence = 1.0 - abs(combined_score - 0.5) * 2

        return {
            'prediction': prediction,
            'confidence': confidence,
            'reason': reason,
            'risk_level': risk_level,
            'expected_return': expected_return,
            'time_horizon': time_horizon
        }

    def _analyze_fund(self, fund: Dict[str, Any], buy_sell_point: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析基金

        Args:
            fund: 基金数据
            buy_sell_point: 买卖点分析结果

        Returns:
            基金AI分析结果
        """
        if self.use_local_model:
            return self._analyze_fund_with_local_model(fund, buy_sell_point)
        else:
            return self._analyze_fund_with_api(fund, buy_sell_point)

    def analyze(self) -> Dict[str, Any]:
        """
        进行AI分析

        Returns:
            AI分析结果
        """
        logger.info("开始进行AI分析...")

        # 使用多线程分析新闻
        from ..utils.thread_pool import run_with_thread_pool

        logger.info("分析新闻情感...")
        news_analysis_tasks = [{'news': news} for news in self.news_data]
        news_analysis_results = run_with_thread_pool(
            lambda kwargs: self._analyze_news(kwargs['news']),
            news_analysis_tasks
        )

        # 将新闻分析结果添加到新闻数据中
        analyzed_news = []
        for i, news in enumerate(self.news_data):
            if i < len(news_analysis_results):
                result = news_analysis_results[i]
                news['ai_analysis'] = result
                analyzed_news.append(news)

        # 使用多线程分析基金
        logger.info("分析基金...")
        fund_analysis_tasks = []
        for fund in self.fund_data:
            fund_code = fund['code']
            # 查找对应的买卖点分析结果
            buy_sell_point = None
            for point in self.buy_sell_points:
                if point.get('code') == fund_code:
                    buy_sell_point = point
                    break

            if buy_sell_point:
                fund_analysis_tasks.append({'fund': fund, 'buy_sell_point': buy_sell_point})

        fund_analysis_results = run_with_thread_pool(
            lambda kwargs: self._analyze_fund(kwargs['fund'], kwargs['buy_sell_point']),
            fund_analysis_tasks
        )

        # 将基金分析结果添加到买卖点数据中
        analyzed_buy_sell_points = []
        for i, task in enumerate(fund_analysis_tasks):
            if i < len(fund_analysis_results):
                result = fund_analysis_results[i]
                buy_sell_point = task['buy_sell_point']
                buy_sell_point['ai_analysis'] = result
                analyzed_buy_sell_points.append(buy_sell_point)

        # 生成市场整体分析
        logger.info("生成市场整体分析...")
        market_analysis = self._analyze_market(analyzed_buy_sell_points, analyzed_news)

        # 组合分析结果
        analysis_result = {
            'news_analysis': analyzed_news,
            'fund_analysis': analyzed_buy_sell_points,
            'market_analysis': market_analysis,
            'analysis_time': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # 保存分析结果
        self.save_analysis_results(analysis_result)

        logger.info("AI分析完成")
        return analysis_result

    def _analyze_market(self, buy_sell_points: List[Dict[str, Any]], news_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析市场整体情况

        Args:
            buy_sell_points: 买卖点分析结果列表
            news_data: 新闻数据列表

        Returns:
            市场整体分析结果
        """
        # 统计买卖点分布
        buy_count = sum(1 for point in buy_sell_points if point.get('recommendation') == '买入')
        sell_count = sum(1 for point in buy_sell_points if point.get('recommendation') == '卖出')
        hold_count = sum(1 for point in buy_sell_points if point.get('recommendation') == '观望')
        total_count = len(buy_sell_points)

        # 计算平均得分
        avg_combined_score = sum(point.get('combined_score', 0.5) for point in buy_sell_points) / total_count if total_count > 0 else 0.5
        avg_long_term_score = sum(point.get('long_term_score', 0.5) for point in buy_sell_points) / total_count if total_count > 0 else 0.5
        avg_mid_term_score = sum(point.get('mid_term_score', 0.5) for point in buy_sell_points) / total_count if total_count > 0 else 0.5
        avg_short_term_score = sum(point.get('short_term_score', 0.5) for point in buy_sell_points) / total_count if total_count > 0 else 0.5
        avg_news_sentiment_score = sum(point.get('news_sentiment_score', 0.5) for point in buy_sell_points) / total_count if total_count > 0 else 0.5

        # 分析新闻情感分布
        positive_news_count = sum(1 for news in news_data if news.get('ai_analysis', {}).get('sentiment') == 'positive')
        negative_news_count = sum(1 for news in news_data if news.get('ai_analysis', {}).get('sentiment') == 'negative')
        neutral_news_count = sum(1 for news in news_data if news.get('ai_analysis', {}).get('sentiment') == 'neutral')
        total_news_count = len(news_data)

        # 确定市场趋势
        market_trend = 'neutral'
        if avg_combined_score > 0.6:
            market_trend = 'bullish'
        elif avg_combined_score < 0.4:
            market_trend = 'bearish'

        # 生成市场分析摘要
        summary = f"根据对 {total_count} 只基金的分析，市场整体呈现{market_trend}趋势。"
        summary += f"其中，建议买入的基金有 {buy_count} 只，占比 {buy_count/total_count*100:.1f}%；"
        summary += f"建议卖出的基金有 {sell_count} 只，占比 {sell_count/total_count*100:.1f}%；"
        summary += f"建议观望的基金有 {hold_count} 只，占比 {hold_count/total_count*100:.1f}%。"

        if total_news_count > 0:
            summary += f"从新闻情感来看，正面新闻占比 {positive_news_count/total_news_count*100:.1f}%，"
            summary += f"负面新闻占比 {negative_news_count/total_news_count*100:.1f}%，"
            summary += f"中性新闻占比 {neutral_news_count/total_news_count*100:.1f}%。"

        return {
            'market_trend': market_trend,
            'buy_sell_distribution': {
                'buy': buy_count,
                'sell': sell_count,
                'hold': hold_count,
                'total': total_count
            },
            'average_scores': {
                'combined': avg_combined_score,
                'long_term': avg_long_term_score,
                'mid_term': avg_mid_term_score,
                'short_term': avg_short_term_score,
                'news_sentiment': avg_news_sentiment_score
            },
            'news_sentiment_distribution': {
                'positive': positive_news_count,
                'negative': negative_news_count,
                'neutral': neutral_news_count,
                'total': total_news_count
            },
            'summary': summary
        }

    def save_analysis_results(self, analysis_result: Dict[str, Any]) -> None:
        """
        保存分析结果

        Args:
            analysis_result: 分析结果
        """
        # 按日期保存
        from datetime import datetime
        today = datetime.now().strftime('%Y%m%d')
        filename = os.path.join(self.output_dir, f'ai_analysis_{today}.json')

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(analysis_result, f, ensure_ascii=False, indent=2)
            logger.info(f"AI分析结果已保存到 {filename}")
        except Exception as e:
            logger.error(f"保存AI分析结果失败: {str(e)}", exc_info=True)
