"""本地AI引擎 - 无需外部API的智能分析"""

import re
import jieba
import jieba.analyse
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import math

from ..utils.logger import log_info, log_warning, log_error, log_debug

class LocalAIEngine:
    """本地AI引擎 - 基于规则和统计的智能分析"""

    def __init__(self):
        # 初始化中文分词
        jieba.initialize()

        # 金融关键词库
        self.financial_keywords = {
            'positive': [
                '上涨', '增长', '盈利', '收益', '利好', '看好', '推荐', '买入',
                '强势', '突破', '反弹', '回升', '超预期', '优秀', '稳健',
                '创新高', '放量', '活跃', '机会', '潜力', '价值', '低估'
            ],
            'negative': [
                '下跌', '下滑', '亏损', '风险', '利空', '看跌', '卖出', '减持',
                '疲软', '跳水', '暴跌', '回调', '不及预期', '担忧', '压力',
                '创新低', '缩量', '低迷', '避险', '高估', '泡沫', '警惕'
            ],
            'neutral': [
                '持平', '震荡', '整理', '观望', '平稳', '维持', '中性',
                '等待', '关注', '分化', '调整', '波动', '区间', '盘整'
            ]
        }

        # 行业关键词
        self.industry_keywords = {
            '科技': ['科技', '互联网', '人工智能', '5G', '芯片', '半导体', '软件', '云计算'],
            '医药': ['医药', '生物', '医疗', '疫苗', '药品', '器械', '健康'],
            '消费': ['消费', '零售', '品牌', '食品', '饮料', '服装', '家电'],
            '金融': ['银行', '保险', '证券', '基金', '信托', '金融'],
            '地产': ['房地产', '建筑', '物业', '装修', '家居'],
            '能源': ['石油', '天然气', '煤炭', '电力', '新能源', '光伏', '风电'],
            '制造': ['制造', '机械', '汽车', '钢铁', '化工', '材料']
        }

        # 市场情绪指标
        self.sentiment_patterns = {
            'fear': ['恐慌', '暴跌', '崩盘', '血洗', '大跌', '恐惧'],
            'greed': ['疯涨', '暴涨', '牛市', '狂欢', '追高', '贪婪'],
            'uncertainty': ['不确定', '分歧', '震荡', '迷茫', '观望', '等待']
        }

    def analyze_sentiment(self, text: str) -> Dict:
        """分析文本情感"""
        if not text:
            return {'sentiment': 'neutral', 'score': 0.0, 'confidence': 0.0}

        # 分词
        words = jieba.lcut(text)

        # 计算情感得分
        positive_score = 0
        negative_score = 0
        neutral_score = 0

        for word in words:
            if word in self.financial_keywords['positive']:
                positive_score += 1
            elif word in self.financial_keywords['negative']:
                negative_score += 1
            elif word in self.financial_keywords['neutral']:
                neutral_score += 1

        total_score = positive_score + negative_score + neutral_score

        if total_score == 0:
            return {'sentiment': 'neutral', 'score': 0.0, 'confidence': 0.0}

        # 归一化得分
        pos_ratio = positive_score / total_score
        neg_ratio = negative_score / total_score
        neu_ratio = neutral_score / total_score

        # 确定主要情感
        if pos_ratio > neg_ratio and pos_ratio > neu_ratio:
            sentiment = 'positive'
            score = pos_ratio - neg_ratio
        elif neg_ratio > pos_ratio and neg_ratio > neu_ratio:
            sentiment = 'negative'
            score = neg_ratio - pos_ratio
        else:
            sentiment = 'neutral'
            score = neu_ratio

        confidence = max(pos_ratio, neg_ratio, neu_ratio)

        return {
            'sentiment': sentiment,
            'score': round(score, 3),
            'confidence': round(confidence, 3),
            'details': {
                'positive': positive_score,
                'negative': negative_score,
                'neutral': neutral_score
            }
        }

    def extract_key_topics(self, texts: List[str], top_k: int = 10) -> List[Dict]:
        """提取关键主题"""
        if not texts:
            return []

        # 合并所有文本
        combined_text = ' '.join(texts)

        # 提取关键词
        keywords = jieba.analyse.extract_tags(combined_text, topK=top_k*2, withWeight=True)

        # 分析主题
        topics = []
        for keyword, weight in keywords[:top_k]:
            # 确定主题分类
            topic_category = self._classify_topic(keyword)

            topics.append({
                'keyword': keyword,
                'weight': round(weight, 3),
                'category': topic_category,
                'importance': 'high' if weight > 0.1 else 'medium' if weight > 0.05 else 'low'
            })

        return topics

    def _classify_topic(self, keyword: str) -> str:
        """分类主题"""
        for category, words in self.industry_keywords.items():
            if any(word in keyword for word in words):
                return category
        return '其他'

    def analyze_market_sentiment(self, news_data: List[Dict]) -> Dict:
        """分析市场整体情绪"""
        if not news_data:
            return self._generate_default_market_sentiment()

        sentiments = []
        for news in news_data:
            title_sentiment = self.analyze_sentiment(news.get('title', ''))
            content_sentiment = self.analyze_sentiment(news.get('content', ''))

            # 标题权重更高
            combined_score = title_sentiment['score'] * 0.7 + content_sentiment['score'] * 0.3
            sentiments.append({
                'sentiment': title_sentiment['sentiment'],
                'score': combined_score,
                'confidence': (title_sentiment['confidence'] + content_sentiment['confidence']) / 2
            })

        # 计算整体情绪
        if sentiments:
            avg_score = np.mean([s['score'] for s in sentiments])
            avg_confidence = np.mean([s['confidence'] for s in sentiments])

            positive_count = len([s for s in sentiments if s['sentiment'] == 'positive'])
            negative_count = len([s for s in sentiments if s['sentiment'] == 'negative'])
            neutral_count = len([s for s in sentiments if s['sentiment'] == 'neutral'])

            total_count = len(sentiments)

            overall_sentiment = 'neutral'
            if positive_count / total_count > 0.5:
                overall_sentiment = 'positive'
            elif negative_count / total_count > 0.5:
                overall_sentiment = 'negative'
        else:
            avg_score = 0.0
            avg_confidence = 0.0
            overall_sentiment = 'neutral'
            positive_count = negative_count = neutral_count = 0
            total_count = 0

        return {
            'overall_sentiment': overall_sentiment,
            'sentiment_score': round(avg_score, 3),
            'confidence': round(avg_confidence, 3),
            'distribution': {
                'positive': positive_count,
                'negative': negative_count,
                'neutral': neutral_count,
                'total': total_count
            },
            'market_mood': self._determine_market_mood(avg_score, positive_count, negative_count, total_count)
        }

    def _determine_market_mood(self, avg_score: float, pos_count: int, neg_count: int, total_count: int) -> str:
        """判断市场情绪"""
        if total_count == 0:
            return '平静'

        pos_ratio = pos_count / total_count
        neg_ratio = neg_count / total_count

        if pos_ratio > 0.7:
            return '乐观'
        elif pos_ratio > 0.5:
            return '谨慎乐观'
        elif neg_ratio > 0.7:
            return '悲观'
        elif neg_ratio > 0.5:
            return '谨慎悲观'
        else:
            return '中性观望'

    def _generate_default_market_sentiment(self) -> Dict:
        """生成默认市场情绪"""
        return {
            'overall_sentiment': 'neutral',
            'sentiment_score': 0.0,
            'confidence': 0.5,
            'distribution': {
                'positive': 5,
                'negative': 4,
                'neutral': 6,
                'total': 15
            },
            'market_mood': '中性观望'
        }

    def generate_investment_advice(self, fund_data: Dict, market_sentiment: Dict) -> Dict:
        """生成投资建议"""
        try:
            # 获取基金基本信息
            fund_type = fund_data.get('type', '混合型')
            daily_return = fund_data.get('daily_return', 0)
            nav = fund_data.get('nav', 1.0)

            # 计算风险等级
            risk_level = self._calculate_risk_level(fund_data)

            # 基于市场情绪调整建议
            market_mood = market_sentiment.get('market_mood', '中性观望')
            sentiment_score = market_sentiment.get('sentiment_score', 0)

            # 生成建议
            advice = self._generate_advice_rules(fund_type, daily_return, risk_level, market_mood, sentiment_score)

            return {
                'recommendation': advice['recommendation'],
                'reason': advice['reason'],
                'risk_level': risk_level,
                'investment_horizon': advice['horizon'],
                'position_suggestion': advice['position'],
                'confidence': advice['confidence'],
                'generated_at': datetime.now().isoformat()
            }

        except Exception as e:
            log_error(f"生成投资建议失败: {e}")
            return self._default_investment_advice()

    def _calculate_risk_level(self, fund_data: Dict) -> str:
        """计算风险等级"""
        fund_type = fund_data.get('type', '混合型')
        daily_return = abs(fund_data.get('daily_return', 0))

        if '股票' in fund_type:
            base_risk = 4
        elif '混合' in fund_type:
            base_risk = 3
        elif '债券' in fund_type:
            base_risk = 2
        else:
            base_risk = 3

        # 根据波动性调整
        if daily_return > 3:
            base_risk += 1
        elif daily_return < 1:
            base_risk -= 1

        risk_levels = ['极低', '低', '中等', '较高', '高', '极高']
        return risk_levels[min(max(base_risk, 0), len(risk_levels)-1)]

    def _generate_advice_rules(self, fund_type: str, daily_return: float, risk_level: str, market_mood: str, sentiment_score: float) -> Dict:
        """基于规则生成建议"""

        # 基础建议逻辑
        if '股票' in fund_type or '指数' in fund_type:
            if market_mood in ['乐观', '谨慎乐观'] and daily_return > 0:
                recommendation = '买入'
                reason = '市场情绪积极，股票型基金表现良好，建议适当增加配置'
                position = '40-60%'
                confidence = 0.7
            elif market_mood in ['悲观', '谨慎悲观']:
                recommendation = '观望'
                reason = '市场情绪偏悲观，股票型基金风险较高，建议观望等待更好时机'
                position = '10-30%'
                confidence = 0.6
            else:
                recommendation = '持有'
                reason = '市场情绪中性，股票型基金可以适量持有，注意风险控制'
                position = '20-40%'
                confidence = 0.5

        elif '债券' in fund_type:
            if market_mood in ['悲观', '谨慎悲观']:
                recommendation = '买入'
                reason = '市场避险情绪浓厚，债券型基金是较好的避险选择'
                position = '30-50%'
                confidence = 0.8
            else:
                recommendation = '持有'
                reason = '债券型基金风险较低，可以作为组合的稳定收益部分'
                position = '20-40%'
                confidence = 0.6

        else:  # 混合型
            if abs(daily_return) < 1 and market_mood not in ['悲观']:
                recommendation = '买入'
                reason = '混合型基金风险适中，当前表现稳定，适合长期投资'
                position = '30-50%'
                confidence = 0.7
            elif daily_return < -2:
                recommendation = '观望'
                reason = '基金近期表现不佳，建议观望等待回调机会'
                position = '10-20%'
                confidence = 0.6
            else:
                recommendation = '持有'
                reason = '混合型基金适合作为核心配置，建议保持持有'
                position = '20-40%'
                confidence = 0.6

        # 投资期限建议
        if risk_level in ['高', '极高']:
            horizon = '短期(1-6个月)'
        elif risk_level in ['中等', '较高']:
            horizon = '中期(6个月-2年)'
        else:
            horizon = '长期(2年以上)'

        return {
            'recommendation': recommendation,
            'reason': reason,
            'position': position,
            'horizon': horizon,
            'confidence': confidence
        }

    def _default_investment_advice(self) -> Dict:
        """默认投资建议"""
        return {
            'recommendation': '持有',
            'reason': '基于当前市场情况，建议保持现有持仓，密切关注市场变化',
            'risk_level': '中等',
            'investment_horizon': '中期(6个月-2年)',
            'position_suggestion': '20-40%',
            'confidence': 0.5,
            'generated_at': datetime.now().isoformat()
        }

    def analyze_fund_performance_ai(self, hist_data: pd.DataFrame) -> Dict:
        """AI分析基金表现"""
        if hist_data.empty:
            return {'performance': 'unknown', 'trend': 'unknown', 'volatility': 'unknown'}

        try:
            returns = hist_data['daily_return'].dropna()

            # 计算统计指标
            mean_return = returns.mean()
            volatility = returns.std()
            sharpe_ratio = mean_return / volatility if volatility > 0 else 0

            # 趋势分析
            recent_returns = returns.tail(10)
            trend_score = recent_returns.mean()

            # 性能评级
            if mean_return > 0.5 and sharpe_ratio > 0.5:
                performance = 'excellent'
            elif mean_return > 0 and sharpe_ratio > 0:
                performance = 'good'
            elif mean_return > -0.5:
                performance = 'average'
            else:
                performance = 'poor'

            # 趋势判断
            if trend_score > 0.5:
                trend = 'strong_upward'
            elif trend_score > 0:
                trend = 'upward'
            elif trend_score > -0.5:
                trend = 'sideways'
            else:
                trend = 'downward'

            # 波动性评估
            if volatility > 3:
                volatility_level = 'high'
            elif volatility > 1.5:
                volatility_level = 'medium'
            else:
                volatility_level = 'low'

            return {
                'performance': performance,
                'trend': trend,
                'volatility': volatility_level,
                'metrics': {
                    'mean_return': round(mean_return, 3),
                    'volatility': round(volatility, 3),
                    'sharpe_ratio': round(sharpe_ratio, 3),
                    'trend_score': round(trend_score, 3)
                }
            }

        except Exception as e:
            log_error(f"AI分析基金表现失败: {e}")
            return {'performance': 'unknown', 'trend': 'unknown', 'volatility': 'unknown'}

# 全局AI引擎实例
local_ai_engine = LocalAIEngine()
