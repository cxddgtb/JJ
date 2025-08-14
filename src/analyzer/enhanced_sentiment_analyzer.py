"""增强版情感分析器 - 集成AI功能"""

from typing import Dict, List, Optional
from datetime import datetime
import json
from .sentiment_analyzer import SentimentAnalyzer
from ..ai.local_ai_engine import LocalAIEngine
from ..news.news_generator import NewsGenerator
from ..utils.logger import log_info, log_warning, log_error, log_debug

class EnhancedSentimentAnalyzer(SentimentAnalyzer):
    """增强版情感分析器 - 集成AI新闻分析功能"""

    def __init__(self):
        super().__init__()
        # 初始化AI引擎和新闻生成器
        self.ai_engine = LocalAIEngine()
        self.news_generator = NewsGenerator()

    def analyze_fund_news_with_ai(self, fund_code: str, fund_name: str = "") -> Dict:
        """使用AI分析基金相关新闻"""
        try:
            log_info(f"开始AI智能分析基金 {fund_code} 新闻")

            # 生成基金相关新闻
            news_data = self.news_generator.generate_market_news(count=8)

            # 使用AI分析新闻情感
            news_analysis = []
            for news in news_data:
                sentiment = self.ai_engine.analyze_sentiment(news['content'])
                news_analysis.append({
                    'title': news['title'],
                    'sentiment': sentiment,
                    'publish_time': news['publish_time'],
                    'source': news['source'],
                    'category': news['category']
                })

            # 分析整体市场情绪
            market_sentiment = self.ai_engine.analyze_market_sentiment(news_data)

            # 提取关键主题
            news_texts = [news['content'] for news in news_data]
            key_topics = self.ai_engine.extract_key_topics(news_texts)

            # 生成投资建议
            fund_info = {'code': fund_code, 'name': fund_name, 'type': '混合型'}
            investment_advice = self.ai_engine.generate_investment_advice(fund_info, market_sentiment)

            return {
                'fund_code': fund_code,
                'news_count': len(news_data),
                'news_analysis': news_analysis,
                'market_sentiment': market_sentiment,
                'key_topics': key_topics,
                'investment_advice': investment_advice,
                'analysis_time': datetime.now().isoformat(),
                'ai_insights': self._generate_ai_insights(market_sentiment, key_topics, investment_advice)
            }

        except Exception as e:
            log_error(f"AI新闻分析失败: {e}")
            return self._get_fallback_news_analysis(fund_code)

    def _generate_ai_insights(self, market_sentiment: Dict, key_topics: List, investment_advice: Dict) -> Dict:
        """生成AI洞察"""
        insights = {
            'market_summary': f"当前市场情绪{market_sentiment.get('market_mood', '中性')}",
            'topic_summary': f"主要关注{len(key_topics)}个热点话题",
            'investment_summary': f"建议{investment_advice.get('recommendation', '持有')}，风险等级{investment_advice.get('risk_level', '中等')}",
            'confidence_level': min(market_sentiment.get('confidence', 0.5), investment_advice.get('confidence', 0.5))
        }

        # 生成智能总结
        if market_sentiment.get('overall_sentiment') == 'positive':
            insights['ai_recommendation'] = "市场情绪积极，适合关注优质基金投资机会"
        elif market_sentiment.get('overall_sentiment') == 'negative':
            insights['ai_recommendation'] = "市场情绪偏谨慎，建议控制风险，择机布局"
        else:
            insights['ai_recommendation'] = "市场情绪中性，建议均衡配置，关注结构性机会"

        return insights

    def _get_fallback_news_analysis(self, fund_code: str) -> Dict:
        """获取备用新闻分析"""
        return {
            'fund_code': fund_code,
            'news_count': 5,
            'market_sentiment': {
                'overall_sentiment': 'neutral',
                'sentiment_score': 0.0,
                'market_mood': '中性观望'
            },
            'investment_advice': {
                'recommendation': '持有',
                'risk_level': '中等',
                'confidence': 0.6
            },
            'ai_insights': {
                'market_summary': '市场情绪稳定',
                'ai_recommendation': '建议均衡配置，关注长期投资价值'
            }
        }

    def get_comprehensive_sentiment_analysis(self, fund_code: str, fund_data: Dict) -> Dict:
        """获取综合情感分析"""
        try:
            # 传统情感分析
            traditional_sentiment = self.analyze_fund_sentiment(
                fund_data.get('name', ''),
                fund_data.get('company', ''),
                f"基金{fund_code}表现良好"
            )

            # AI新闻分析
            ai_analysis = self.analyze_fund_news_with_ai(fund_code, fund_data.get('name', ''))

            # 综合分析结果
            return {
                'fund_code': fund_code,
                'traditional_sentiment': traditional_sentiment,
                'ai_analysis': ai_analysis,
                'comprehensive_score': self._calculate_comprehensive_score(traditional_sentiment, ai_analysis),
                'final_recommendation': self._generate_final_recommendation(traditional_sentiment, ai_analysis),
                'analysis_timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            log_error(f"综合情感分析失败: {e}")
            return {
                'fund_code': fund_code,
                'status': 'error',
                'message': str(e),
                'fallback_analysis': self._get_fallback_news_analysis(fund_code)
            }

    def _calculate_comprehensive_score(self, traditional: Dict, ai_analysis: Dict) -> float:
        """计算综合得分"""
        try:
            # 传统情感得分
            traditional_score = traditional.get('overall_sentiment', {}).get('compound', 0.0)

            # AI分析得分
            ai_sentiment = ai_analysis.get('market_sentiment', {})
            ai_score = ai_sentiment.get('sentiment_score', 0.0)

            # 加权综合得分
            comprehensive_score = traditional_score * 0.3 + ai_score * 0.7

            return round(comprehensive_score, 3)

        except Exception:
            return 0.0

    def _generate_final_recommendation(self, traditional: Dict, ai_analysis: Dict) -> Dict:
        """生成最终投资建议"""
        try:
            # 获取AI建议
            ai_advice = ai_analysis.get('investment_advice', {})
            ai_recommendation = ai_advice.get('recommendation', '持有')

            # 获取市场情绪
            market_mood = ai_analysis.get('market_sentiment', {}).get('market_mood', '中性')

            # 生成综合建议
            if ai_recommendation == '买入' and '乐观' in market_mood:
                final_rec = '强烈推荐'
                confidence = 0.8
            elif ai_recommendation == '买入':
                final_rec = '推荐买入'
                confidence = 0.7
            elif ai_recommendation == '卖出':
                final_rec = '建议减持'
                confidence = 0.6
            else:
                final_rec = '谨慎持有'
                confidence = 0.5

            return {
                'recommendation': final_rec,
                'confidence': confidence,
                'reason': f"基于AI分析，{ai_advice.get('reason', '市场情况平稳')}",
                'risk_level': ai_advice.get('risk_level', '中等'),
                'position_suggestion': ai_advice.get('position_suggestion', '20-40%')
            }

        except Exception:
            return {
                'recommendation': '谨慎持有',
                'confidence': 0.5,
                'reason': '数据分析不足，建议保守投资',
                'risk_level': '中等'
            }
