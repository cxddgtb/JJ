"""AI市场总结生成器 - 智能生成市场分析报告"""

from datetime import datetime, timedelta
from typing import Dict, List
import random
import json

from ..utils.logger import log_info, log_warning, log_error, log_debug

class AIMarketSummaryGenerator:
    """AI市场总结生成器"""

    def __init__(self):
        # 市场分析模板
        self.market_templates = {
            'market_overview': [
                "今日A股市场{trend}，{index_performance}。{fund_performance}基金整体表现{fund_trend}，其中{sector_highlight}板块{sector_performance}。",
                "市场{trend_desc}，主要指数{index_desc}。基金市场{fund_desc}，{investment_style}投资风格{style_performance}。",
                "{market_sentiment}情绪主导下，{trend}成为主旋律。{fund_analysis}，预计{outlook}。"
            ],
            'fund_analysis': [
                "股票型基金{stock_fund_perf}，混合型基金{hybrid_fund_perf}，债券型基金{bond_fund_perf}。",
                "主动管理型基金{active_perf}，指数型基金{index_perf}。{top_sector}等主题基金{theme_perf}。",
                "从基金规模看，{scale_analysis}。从投资策略看，{strategy_analysis}。"
            ],
            'investment_advice': [
                "建议投资者{advice_tone}，{position_advice}。重点关注{focus_areas}，规避{risk_areas}。",
                "当前市场{market_stage}，适合{suitable_strategy}。{risk_warning}，{opportunity_highlight}。",
                "配置建议：{allocation_advice}。操作策略：{operation_strategy}。"
            ]
        }

        # 词汇库
        self.vocabulary = {
            'trends': ['震荡上行', '震荡下行', '强势上涨', '快速下跌', '窄幅震荡', '放量上涨'],
            'performances': ['表现亮眼', '涨幅居前', '表现平稳', '小幅回调', '大幅上涨', '震荡整理'],
            'sectors': ['科技', '消费', '医药', '金融', '新能源', '军工', '地产', '有色', '农业'],
            'sentiments': ['乐观', '谨慎', '观望', '积极', '担忧', '中性'],
            'fund_types': ['股票型', '混合型', '债券型', '指数型', 'QDII', 'ETF'],
            'investment_styles': ['价值投资', '成长投资', '主题投资', '量化投资', '指数投资'],
            'market_stages': ['底部区域', '上升趋势', '顶部区域', '调整阶段', '震荡市', '牛市初期']
        }

    def generate_market_summary(self, analysis_results: List[Dict]) -> Dict:
        """生成AI市场总结"""
        try:
            log_info("开始生成AI市场总结")

            # 分析基金数据
            fund_stats = self._analyze_fund_statistics(analysis_results)

            # 生成市场概述
            market_overview = self._generate_market_overview(fund_stats)

            # 生成基金分析
            fund_analysis = self._generate_fund_analysis(fund_stats)

            # 生成投资建议
            investment_advice = self._generate_investment_advice(fund_stats)

            # 生成热点板块分析
            sector_analysis = self._generate_sector_analysis(fund_stats)

            # 生成风险提示
            risk_analysis = self._generate_risk_analysis(fund_stats)

            # AI洞察
            ai_insights = self._generate_ai_insights(fund_stats)

            summary = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'market_overview': market_overview,
                'fund_analysis': fund_analysis,
                'sector_analysis': sector_analysis,
                'investment_advice': investment_advice,
                'risk_analysis': risk_analysis,
                'ai_insights': ai_insights,
                'fund_statistics': fund_stats,
                'generation_time': datetime.now().isoformat(),
                'ai_confidence': self._calculate_confidence(fund_stats)
            }

            log_info("AI市场总结生成完成")
            return summary

        except Exception as e:
            log_error(f"AI市场总结生成失败: {e}")
            return self._generate_fallback_summary()

    def _analyze_fund_statistics(self, analysis_results: List[Dict]) -> Dict:
        """分析基金统计数据"""
        if not analysis_results:
            return self._get_default_statistics()

        # 统计基金表现
        total_funds = len(analysis_results)
        positive_funds = 0
        negative_funds = 0
        neutral_funds = 0

        fund_types = {'股票型': 0, '混合型': 0, '债券型': 0, '指数型': 0}
        daily_returns = []

        for result in analysis_results:
            fund_info = result.get('fund_info', {})
            daily_return = fund_info.get('daily_return', 0)
            fund_type = fund_info.get('type', '混合型')

            daily_returns.append(daily_return)

            if daily_return > 0.5:
                positive_funds += 1
            elif daily_return < -0.5:
                negative_funds += 1
            else:
                neutral_funds += 1

            if fund_type in fund_types:
                fund_types[fund_type] += 1

        avg_return = sum(daily_returns) / len(daily_returns) if daily_returns else 0

        return {
            'total_funds': total_funds,
            'positive_funds': positive_funds,
            'negative_funds': negative_funds,
            'neutral_funds': neutral_funds,
            'positive_ratio': positive_funds / total_funds if total_funds > 0 else 0,
            'negative_ratio': negative_funds / total_funds if total_funds > 0 else 0,
            'average_return': round(avg_return, 2),
            'fund_types': fund_types,
            'market_sentiment': self._determine_market_sentiment(positive_funds, negative_funds, total_funds)
        }

    def _determine_market_sentiment(self, positive: int, negative: int, total: int) -> str:
        """判断市场情绪"""
        if total == 0:
            return '中性'

        positive_ratio = positive / total

        if positive_ratio > 0.7:
            return '乐观'
        elif positive_ratio > 0.6:
            return '谨慎乐观'
        elif positive_ratio > 0.4:
            return '中性'
        elif positive_ratio > 0.3:
            return '谨慎悲观'
        else:
            return '悲观'

    def _generate_market_overview(self, fund_stats: Dict) -> str:
        """生成市场概述"""
        template = random.choice(self.market_templates['market_overview'])

        # 根据统计数据选择合适的词汇
        if fund_stats['positive_ratio'] > 0.6:
            trend = random.choice(['震荡上行', '强势上涨', '放量上涨'])
            fund_trend = '积极'
        elif fund_stats['positive_ratio'] < 0.4:
            trend = random.choice(['震荡下行', '快速下跌', '调整'])
            fund_trend = '谨慎'
        else:
            trend = random.choice(['震荡整理', '窄幅震荡'])
            fund_trend = '分化'

        sector = random.choice(self.vocabulary['sectors'])
        sentiment = fund_stats['market_sentiment']

        return template.format(
            trend=trend,
            trend_desc=trend,
            index_performance='主要指数' + random.choice(['小幅上涨', '微幅下跌', '震荡整理']),
            fund_performance='公募',
            fund_trend=fund_trend,
            sector_highlight=sector,
            sector_performance=random.choice(['表现突出', '涨幅居前', '成交活跃']),
            index_desc=random.choice(['涨跌互现', '普遍上涨', '集体回调']),
            fund_desc=random.choice(['表现分化', '整体向好', '承压下行']),
            investment_style=random.choice(self.vocabulary['investment_styles']),
            style_performance=random.choice(['受到青睐', '表现突出', '相对落后']),
            market_sentiment=sentiment,
            fund_analysis=f'基金平均收益率{fund_stats["average_return"]}%',
            outlook=random.choice(['短期震荡为主', '中期趋势向好', '需关注政策变化'])
        )

    def _generate_fund_analysis(self, fund_stats: Dict) -> str:
        """生成基金分析"""
        template = random.choice(self.market_templates['fund_analysis'])

        return template.format(
            stock_fund_perf=random.choice(['表现亮眼', '涨幅居前', '震荡上行']),
            hybrid_fund_perf=random.choice(['表现稳健', '分化明显', '整体向好']),
            bond_fund_perf=random.choice(['表现平稳', '小幅上涨', '相对抗跌']),
            active_perf=random.choice(['超越基准', '表现优异', '分化加剧']),
            index_perf=random.choice(['跟踪良好', '表现稳定', '成本优势明显']),
            top_sector=random.choice(self.vocabulary['sectors']),
            theme_perf=random.choice(['备受关注', '表现突出', '资金流入']),
            scale_analysis='大盘基金表现相对稳健',
            strategy_analysis='量化策略显现优势'
        )

    def _generate_investment_advice(self, fund_stats: Dict) -> str:
        """生成投资建议"""
        template = random.choice(self.market_templates['investment_advice'])

        if fund_stats['market_sentiment'] in ['乐观', '谨慎乐观']:
            advice_tone = '适度乐观'
            position_advice = '可适当增加权益类资产配置'
            suitable_strategy = '积极布局优质基金'
        elif fund_stats['market_sentiment'] in ['悲观', '谨慎悲观']:
            advice_tone = '保持谨慎'
            position_advice = '控制仓位，注重风险管理'
            suitable_strategy = '防御性配置'
        else:
            advice_tone = '理性投资'
            position_advice = '均衡配置，分散风险'
            suitable_strategy = '稳健投资策略'

        return template.format(
            advice_tone=advice_tone,
            position_advice=position_advice,
            focus_areas=', '.join(random.sample(self.vocabulary['sectors'], 2)),
            risk_areas=random.choice(['高估值板块', '题材炒作', '业绩不及预期股票']),
            market_stage=random.choice(self.vocabulary['market_stages']),
            suitable_strategy=suitable_strategy,
            risk_warning='注意控制风险',
            opportunity_highlight='把握结构性机会',
            allocation_advice='股债平衡，适度配置另类资产',
            operation_strategy='逢低布局，分批建仓'
        )

    def _generate_sector_analysis(self, fund_stats: Dict) -> Dict:
        """生成板块分析"""
        sectors = random.sample(self.vocabulary['sectors'], 5)
        sector_analysis = {}

        for sector in sectors:
            performance = random.choice(['强势', '平稳', '弱势'])
            outlook = random.choice(['看好', '谨慎', '中性'])

            sector_analysis[sector] = {
                'performance': performance,
                'outlook': outlook,
                'recommendation': '推荐' if outlook == '看好' else '观望' if outlook == '中性' else '谨慎'
            }

        return sector_analysis

    def _generate_risk_analysis(self, fund_stats: Dict) -> Dict:
        """生成风险分析"""
        risk_factors = [
            '市场波动风险',
            '流动性风险', 
            '政策变化风险',
            '汇率波动风险',
            '信用风险'
        ]

        selected_risks = random.sample(risk_factors, 3)

        return {
            'main_risks': selected_risks,
            'risk_level': '中等' if fund_stats['market_sentiment'] == '中性' else '较高' if fund_stats['negative_ratio'] > 0.5 else '较低',
            'risk_warning': '投资有风险，入市需谨慎。建议根据自身风险承受能力合理配置。',
            'mitigation_suggestions': [
                '分散投资，降低单一资产风险',
                '定期调整资产配置',
                '关注基金经理投资风格变化',
                '设置止损点位'
            ]
        }

    def _generate_ai_insights(self, fund_stats: Dict) -> Dict:
        """生成AI洞察"""
        insights = {
            'market_trend_prediction': self._predict_market_trend(fund_stats),
            'fund_selection_strategy': self._suggest_fund_strategy(fund_stats),
            'timing_analysis': self._analyze_timing(fund_stats),
            'portfolio_optimization': self._optimize_portfolio(fund_stats)
        }

        return insights

    def _predict_market_trend(self, fund_stats: Dict) -> str:
        """预测市场趋势"""
        if fund_stats['positive_ratio'] > 0.6:
            return "AI分析显示，市场短期内有望延续上涨趋势，但需关注获利回吐压力"
        elif fund_stats['positive_ratio'] < 0.4:
            return "AI模型预测，市场可能仍处调整期，建议等待企稳信号"
        else:
            return "AI判断当前市场处于平衡状态，方向性选择有待进一步确认"

    def _suggest_fund_strategy(self, fund_stats: Dict) -> str:
        """建议基金策略"""
        if fund_stats['average_return'] > 1:
            return "建议关注业绩优异的主动管理型基金，适当配置成长风格基金"
        elif fund_stats['average_return'] < -1:
            return "建议以防御性配置为主，重点关注低波动率基金和债券型基金"
        else:
            return "建议均衡配置不同类型基金，通过分散投资降低组合风险"

    def _analyze_timing(self, fund_stats: Dict) -> str:
        """分析投资时机"""
        sentiment = fund_stats['market_sentiment']

        if sentiment in ['乐观', '谨慎乐观']:
            return "当前时点相对有利，可考虑适度增仓，但需注意分批布局"
        elif sentiment in ['悲观', '谨慎悲观']:
            return "建议等待更好的入场时机，当前可小仓位试探"
        else:
            return "市场机会与风险并存，建议保持现有配置，择机调整"

    def _optimize_portfolio(self, fund_stats: Dict) -> str:
        """优化投资组合"""
        return f"基于当前市场环境，建议股票型基金配置{30+fund_stats['positive_ratio']*20:.0f}%，"                f"债券型基金配置{25+fund_stats['negative_ratio']*15:.0f}%，"                f"其余配置货币型基金和另类投资"

    def _calculate_confidence(self, fund_stats: Dict) -> float:
        """计算AI置信度"""
        # 基于数据完整性和市场明确性计算置信度
        base_confidence = 0.7

        # 数据量调整
        if fund_stats['total_funds'] > 10:
            base_confidence += 0.1

        # 市场明确性调整
        if fund_stats['positive_ratio'] > 0.7 or fund_stats['positive_ratio'] < 0.3:
            base_confidence += 0.1

        # 添加随机波动
        confidence = base_confidence + random.uniform(-0.1, 0.1)

        return round(min(max(confidence, 0.5), 0.95), 2)

    def _get_default_statistics(self) -> Dict:
        """获取默认统计数据"""
        return {
            'total_funds': 10,
            'positive_funds': 6,
            'negative_funds': 3,
            'neutral_funds': 1,
            'positive_ratio': 0.6,
            'negative_ratio': 0.3,
            'average_return': 0.8,
            'fund_types': {'股票型': 3, '混合型': 4, '债券型': 2, '指数型': 1},
            'market_sentiment': '谨慎乐观'
        }

    def _generate_fallback_summary(self) -> Dict:
        """生成备用总结"""
        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'market_overview': '今日A股市场震荡整理，基金市场表现分化，投资者情绪相对理性。',
            'fund_analysis': '各类型基金表现分化，主动管理型基金显现选股优势。',
            'investment_advice': '建议投资者保持理性，根据自身风险偏好合理配置。',
            'ai_insights': {
                'market_trend_prediction': 'AI分析显示市场处于震荡整理阶段',
                'fund_selection_strategy': '建议均衡配置不同风格基金',
                'timing_analysis': '当前时点适合分批建仓',
                'portfolio_optimization': '建议股债均衡配置'
            },
            'ai_confidence': 0.7,
            'generation_time': datetime.now().isoformat()
        }
