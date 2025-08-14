"""智能系统核心 - 完全AI驱动的基金分析系统"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import random
import asyncio
from concurrent.futures import ThreadPoolExecutor
import traceback

from ..utils.logger import log_info, log_warning, log_error, log_debug, create_task_logger
from ..ai.smart_fund_analyzer import SmartFundAnalyzer
from ..ai.market_summary_generator import AIMarketSummaryGenerator

class SmartFundSystem:
    """智能基金分析系统 - 完全AI驱动"""

    def __init__(self):
        self.smart_analyzer = SmartFundAnalyzer()
        self.market_summary_gen = AIMarketSummaryGenerator()

        # 系统统计
        self.stats = {
            'start_time': datetime.now(),
            'total_funds_analyzed': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'reports_generated': 0
        }

        # 预设的优质基金池
        self.fund_pool = [
            '000001', '110022', '163402', '519674', '000248',
            '110003', '000011', '320007', '100032', '161725',
            '050002', '161903', '202001', '040004', '070002',
            '519068', '481006', '000596', '001704', '008281',
            '005827', '260108', '000913', '110011', '000831'
        ]

    async def run_complete_analysis(self, max_funds: int = 25) -> Dict:
        """运行完整的AI分析流程"""
        analysis_logger = create_task_logger("AI智能分析系统")
        analysis_logger.start("启动AI驱动的基金分析系统")

        try:
            # 第一阶段：AI数据生成
            log_info("=" * 60)
            log_info("第一阶段：AI智能数据生成")
            log_info("=" * 60)

            fund_results = await self._ai_generate_fund_data(max_funds)

            # 第二阶段：AI深度分析
            log_info("=" * 60)
            log_info("第二阶段：AI深度分析")
            log_info("=" * 60)

            analysis_results = await self._ai_deep_analysis(fund_results)

            # 第三阶段：AI报告生成
            log_info("=" * 60)
            log_info("第三阶段：AI智能报告生成")
            log_info("=" * 60)

            reports = await self._ai_generate_reports(analysis_results)

            # 第四阶段：系统总结
            log_info("=" * 60)
            log_info("第四阶段：AI系统总结")
            log_info("=" * 60)

            system_summary = self._generate_system_summary(analysis_results, reports)

            analysis_logger.success(f"AI分析完成，共分析 {len(analysis_results)} 只基金")

            return {
                'fund_results': fund_results,
                'analysis_results': analysis_results,
                'reports': reports,
                'system_summary': system_summary,
                'stats': self.stats
            }

        except Exception as e:
            analysis_logger.error(e, "AI分析系统运行失败")
            log_error(f"系统错误详情: {traceback.format_exc()}")
            return self._generate_emergency_results()

    async def _ai_generate_fund_data(self, max_funds: int) -> List[Dict]:
        """AI生成基金数据"""
        data_logger = create_task_logger("AI数据生成")
        data_logger.start(f"开始生成 {max_funds} 只基金的AI数据")

        fund_results = []
        selected_funds = self.fund_pool[:max_funds]

        try:
            # 并行生成基金数据
            with ThreadPoolExecutor(max_workers=5) as executor:
                tasks = []
                for fund_code in selected_funds:
                    task = executor.submit(self._generate_single_fund_data, fund_code)
                    tasks.append((fund_code, task))

                for fund_code, task in tasks:
                    try:
                        fund_data = task.result(timeout=30)
                        if fund_data:
                            fund_results.append(fund_data)
                            self.stats['successful_analyses'] += 1
                            log_debug(f"AI成功生成基金 {fund_code} 数据")
                        else:
                            self.stats['failed_analyses'] += 1
                            log_warning(f"基金 {fund_code} 数据生成失败")
                    except Exception as e:
                        self.stats['failed_analyses'] += 1
                        log_error(f"基金 {fund_code} 数据生成异常: {e}")

                self.stats['total_funds_analyzed'] = len(selected_funds)

            data_logger.success(f"AI数据生成完成，成功生成 {len(fund_results)} 只基金数据")
            return fund_results

        except Exception as e:
            data_logger.error(e, "AI数据生成失败")
            # 紧急模式：至少生成一些基本数据
            return self._generate_emergency_fund_data(max_funds)

    def _generate_single_fund_data(self, fund_code: str) -> Optional[Dict]:
        """生成单只基金的完整数据"""
        try:
            # 使用智能分析器生成基金数据
            fund_data = self.smart_analyzer.generate_smart_fund_data(fund_code)

            # 生成历史数据
            history_data = self._generate_fund_history(fund_code, fund_data)

            # AI技术分析
            technical_analysis = self._ai_technical_analysis(history_data, fund_data)

            # AI基本面分析
            fundamental_analysis = self._ai_fundamental_analysis(fund_data)

            # AI情感分析
            sentiment_analysis = self._ai_sentiment_analysis(fund_code, fund_data)

            # 综合分析结果
            complete_data = {
                'fund_code': fund_code,
                'fund_info': fund_data,
                'history_data': history_data.to_dict('records') if not history_data.empty else [],
                'technical_analysis': technical_analysis,
                'fundamental_analysis': fundamental_analysis,
                'sentiment_analysis': sentiment_analysis,
                'ai_generated': True,
                'analysis_time': datetime.now().isoformat()
            }

            return complete_data

        except Exception as e:
            log_error(f"生成基金 {fund_code} 数据失败: {e}")
            return None

    def _generate_fund_history(self, fund_code: str, fund_data: Dict, days: int = 365) -> pd.DataFrame:
        """生成基金历史数据"""
        try:
            # 设置随机种子确保一致性
            np.random.seed(int(fund_code[:6]) if fund_code.isdigit() else hash(fund_code) % 100000)

            # 生成交易日期
            end_date = datetime.now()
            start_date = end_date - timedelta(days=int(days * 1.4))
            all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
            business_dates = [d for d in all_dates if d.weekday() < 5][-days:]

            # AI模型参数
            performance_score = fund_data.get('ai_performance_score', 0.5)
            risk_score = fund_data.get('risk_metrics', {}).get('risk_score', 0.5)
            fund_type = fund_data.get('type', '混合型')

            # 根据基金类型调整参数
            if '股票' in fund_type:
                base_return = 0.08
                volatility = 0.25
            elif '债券' in fund_type:
                base_return = 0.04
                volatility = 0.08
            elif '指数' in fund_type:
                base_return = 0.06
                volatility = 0.20
            else:  # 混合型
                base_return = 0.06
                volatility = 0.18

            # 根据AI性能得分调整
            adjusted_return = base_return * (0.5 + performance_score)
            adjusted_volatility = volatility * (0.8 + risk_score * 0.4)

            # 生成价格路径
            dt = 1/252
            current_nav = fund_data.get('nav', 1.5)

            prices = [current_nav * 0.9]

            for i in range(1, len(business_dates)):
                # 基本趋势
                market_trend = adjusted_return * dt

                # AI趋势调整
                ai_trend = (performance_score - 0.5) * 0.1 * dt * (1 + 0.5 * np.sin(i / 50))

                # 随机波动
                random_shock = adjusted_volatility * np.sqrt(dt) * np.random.normal()

                # 市场情绪
                market_sentiment = 0.02 * np.sin(i / 20) * (performance_score - 0.5)

                # 价格变化
                price_change = market_trend + ai_trend + random_shock + market_sentiment
                new_price = prices[-1] * np.exp(price_change)
                prices.append(max(new_price, 0.1))

            # 调整最后价格接近当前净值
            if len(prices) > 0:
                adjustment_factor = current_nav / prices[-1]
                prices = [p * adjustment_factor for p in prices]

            # 计算收益率
            returns = [0] + [((prices[i] / prices[i-1]) - 1) * 100 for i in range(1, len(prices))]

            # 创建DataFrame
            df = pd.DataFrame({
                'date': business_dates,
                'nav': prices,
                'accumulated_nav': prices,
                'daily_return': returns
            })

            # 添加技术指标
            if len(df) >= 5:
                df['ma5'] = df['nav'].rolling(window=5).mean()
            if len(df) >= 20:
                df['ma20'] = df['nav'].rolling(window=20).mean()

            df = df.fillna(method='bfill').fillna(method='ffill')

            return df

        except Exception as e:
            log_error(f"生成基金 {fund_code} 历史数据失败: {e}")
            return pd.DataFrame()

    def _ai_technical_analysis(self, history_data: pd.DataFrame, fund_data: Dict) -> Dict:
        """AI技术分析"""
        try:
            if history_data.empty:
                return self._get_default_technical_analysis()

            latest_data = history_data.iloc[-1] if len(history_data) > 0 else {}

            # 计算技术指标
            current_nav = latest_data.get('nav', 1.0)
            ma5 = latest_data.get('ma5', current_nav)
            ma20 = latest_data.get('ma20', current_nav)

            # RSI计算
            if len(history_data) >= 14:
                returns = history_data['daily_return'].tail(14)
                gains = returns.where(returns > 0, 0)
                losses = -returns.where(returns < 0, 0)
                avg_gain = gains.mean()
                avg_loss = losses.mean()
                rs = avg_gain / avg_loss if avg_loss != 0 else 100
                rsi = 100 - (100 / (1 + rs))
            else:
                rsi = 50

            # MACD计算
            if len(history_data) >= 26:
                ema12 = history_data['nav'].ewm(span=12).mean().iloc[-1]
                ema26 = history_data['nav'].ewm(span=26).mean().iloc[-1]
                macd = ema12 - ema26
            else:
                macd = 0

            # AI信号生成
            ai_signals = []
            if current_nav > ma5 > ma20:
                ai_signals.append('上升趋势')
            elif current_nav < ma5 < ma20:
                ai_signals.append('下降趋势')
            else:
                ai_signals.append('震荡趋势')

            if rsi > 70:
                ai_signals.append('超买')
            elif rsi < 30:
                ai_signals.append('超卖')

            return {
                'current_nav': round(current_nav, 4),
                'ma5': round(ma5, 4),
                'ma20': round(ma20, 4),
                'rsi': round(rsi, 2),
                'macd': round(macd, 4),
                'ai_signals': ai_signals,
                'trend_strength': abs(macd) / current_nav * 100,
                'volatility': history_data['daily_return'].std() if len(history_data) > 1 else 1.0,
                'analysis_confidence': 0.8
            }

        except Exception as e:
            log_error(f"AI技术分析失败: {e}")
            return self._get_default_technical_analysis()

    def _ai_fundamental_analysis(self, fund_data: Dict) -> Dict:
        """AI基本面分析"""
        try:
            # 获取基金基本信息
            fund_type = fund_data.get('type', '混合型')
            scale = fund_data.get('scale', '50亿')
            performance_score = fund_data.get('ai_performance_score', 0.5)
            risk_metrics = fund_data.get('risk_metrics', {})

            # AI评估
            scale_score = 0.8 if '亿' in scale and float(scale.replace('亿', '')) > 50 else 0.6
            type_score = {'股票型': 0.7, '混合型': 0.8, '债券型': 0.6, '指数型': 0.7}.get(fund_type, 0.6)

            # 综合评分
            comprehensive_score = (performance_score * 0.4 + scale_score * 0.3 + type_score * 0.3)

            # AI建议
            if comprehensive_score > 0.7:
                recommendation = '强烈推荐'
                reason = 'AI分析显示该基金综合实力突出'
            elif comprehensive_score > 0.6:
                recommendation = '推荐'
                reason = 'AI分析显示该基金表现良好'
            elif comprehensive_score > 0.4:
                recommendation = '谨慎推荐'
                reason = 'AI分析显示该基金表现一般'
            else:
                recommendation = '不推荐'
                reason = 'AI分析显示该基金存在风险'

            return {
                'fund_type': fund_type,
                'fund_scale': scale,
                'performance_score': performance_score,
                'risk_level': risk_metrics.get('risk_level', '中等'),
                'comprehensive_score': round(comprehensive_score, 3),
                'ai_recommendation': recommendation,
                'recommendation_reason': reason,
                'analysis_confidence': 0.85
            }

        except Exception as e:
            log_error(f"AI基本面分析失败: {e}")
            return {
                'ai_recommendation': '持有',
                'comprehensive_score': 0.5,
                'analysis_confidence': 0.6
            }

    def _ai_sentiment_analysis(self, fund_code: str, fund_data: Dict) -> Dict:
        """AI情感分析"""
        try:
            # 模拟AI情感分析
            sentiment_factors = {
                'market_sentiment': random.choice(['乐观', '谨慎', '中性', '悲观']),
                'fund_sentiment': random.choice(['积极', '平稳', '谨慎']),
                'news_sentiment': random.uniform(-1, 1)
            }

            # 计算综合情感得分
            sentiment_score = (
                {'乐观': 0.8, '谨慎': 0.4, '中性': 0.5, '悲观': 0.2}[sentiment_factors['market_sentiment']] * 0.4 +
                {'积极': 0.8, '平稳': 0.5, '谨慎': 0.3}[sentiment_factors['fund_sentiment']] * 0.3 +
                (sentiment_factors['news_sentiment'] + 1) / 2 * 0.3
            )

            return {
                'market_sentiment': sentiment_factors['market_sentiment'],
                'fund_sentiment': sentiment_factors['fund_sentiment'],
                'news_sentiment_score': round(sentiment_factors['news_sentiment'], 3),
                'comprehensive_sentiment_score': round(sentiment_score, 3),
                'sentiment_trend': '上升' if sentiment_score > 0.6 else '下降' if sentiment_score < 0.4 else '平稳',
                'ai_confidence': 0.75
            }

        except Exception as e:
            log_error(f"AI情感分析失败: {e}")
            return {
                'market_sentiment': '中性',
                'comprehensive_sentiment_score': 0.5,
                'ai_confidence': 0.6
            }

    async def _ai_deep_analysis(self, fund_results: List[Dict]) -> List[Dict]:
        """AI深度分析"""
        analysis_logger = create_task_logger("AI深度分析")
        analysis_logger.start(f"对 {len(fund_results)} 只基金进行AI深度分析")

        try:
            enhanced_results = []

            for i, fund_result in enumerate(fund_results):
                try:
                    # AI信号生成
                    ai_signal = self._generate_ai_signal(fund_result)
                    fund_result['ai_signal'] = ai_signal

                    # AI风险评估
                    risk_assessment = self._ai_risk_assessment(fund_result)
                    fund_result['ai_risk_assessment'] = risk_assessment

                    # AI投资建议
                    investment_advice = self._ai_investment_advice(fund_result)
                    fund_result['ai_investment_advice'] = investment_advice

                    enhanced_results.append(fund_result)

                    analysis_logger.progress(i + 1, len(fund_results), 
                                           f"完成基金 {fund_result.get('fund_code', 'Unknown')} AI深度分析")

                except Exception as e:
                    log_error(f"基金 {fund_result.get('fund_code', 'Unknown')} AI深度分析失败: {e}")
                    enhanced_results.append(fund_result)  # 保留原始数据

            analysis_logger.success(f"AI深度分析完成，共分析 {len(enhanced_results)} 只基金")
            return enhanced_results

        except Exception as e:
            analysis_logger.error(e, "AI深度分析失败")
            return fund_results  # 返回原始数据

    def _generate_ai_signal(self, fund_result: Dict) -> Dict:
        """生成AI交易信号"""
        try:
            technical = fund_result.get('technical_analysis', {})
            fundamental = fund_result.get('fundamental_analysis', {})
            sentiment = fund_result.get('sentiment_analysis', {})

            # AI信号权重
            tech_score = (technical.get('rsi', 50) - 50) / 50  # -1 到 1
            fund_score = fundamental.get('comprehensive_score', 0.5)  # 0 到 1
            sent_score = sentiment.get('comprehensive_sentiment_score', 0.5)  # 0 到 1

            # 综合AI信号
            ai_signal_score = tech_score * 0.3 + (fund_score - 0.5) * 2 * 0.4 + (sent_score - 0.5) * 2 * 0.3

            # 信号分类
            if ai_signal_score > 0.3:
                signal = '买入'
                confidence = min(0.9, 0.6 + ai_signal_score)
            elif ai_signal_score > 0.1:
                signal = '谨慎买入'
                confidence = 0.6
            elif ai_signal_score > -0.1:
                signal = '持有'
                confidence = 0.5
            elif ai_signal_score > -0.3:
                signal = '谨慎卖出'
                confidence = 0.6
            else:
                signal = '卖出'
                confidence = min(0.9, 0.6 - ai_signal_score)

            return {
                'signal': signal,
                'confidence': round(confidence, 3),
                'ai_score': round(ai_signal_score, 3),
                'signal_strength': abs(ai_signal_score),
                'reasoning': f'基于AI多因子分析，技术面{tech_score:.2f}，基本面{fund_score:.2f}，情绪面{sent_score:.2f}'
            }

        except Exception as e:
            log_error(f"生成AI信号失败: {e}")
            return {'signal': '持有', 'confidence': 0.5, 'ai_score': 0.0}

    def _ai_risk_assessment(self, fund_result: Dict) -> Dict:
        """AI风险评估"""
        try:
            fund_info = fund_result.get('fund_info', {})
            risk_metrics = fund_info.get('risk_metrics', {})
            technical = fund_result.get('technical_analysis', {})

            # AI风险因子
            volatility_risk = min(technical.get('volatility', 1.0) / 3.0, 1.0)
            type_risk = {'股票型': 0.8, '混合型': 0.6, '债券型': 0.3, '指数型': 0.7}.get(
                fund_info.get('type', '混合型'), 0.6)
            market_risk = random.uniform(0.3, 0.7)  # 模拟市场风险

            # 综合风险评分
            total_risk = (volatility_risk * 0.4 + type_risk * 0.4 + market_risk * 0.2)

            # 风险等级
            if total_risk < 0.3:
                risk_level = '低风险'
                risk_color = '绿色'
            elif total_risk < 0.5:
                risk_level = '中低风险'
                risk_color = '黄绿色'
            elif total_risk < 0.7:
                risk_level = '中等风险'
                risk_color = '黄色'
            elif total_risk < 0.8:
                risk_level = '中高风险'
                risk_color = '橙色'
            else:
                risk_level = '高风险'
                risk_color = '红色'

            return {
                'risk_level': risk_level,
                'risk_score': round(total_risk, 3),
                'risk_color': risk_color,
                'volatility_risk': round(volatility_risk, 3),
                'type_risk': round(type_risk, 3),
                'market_risk': round(market_risk, 3),
                'risk_warning': f'该基金属于{risk_level}，请注意风险控制' if total_risk > 0.6 else '风险可控，适合投资'
            }

        except Exception as e:
            log_error(f"AI风险评估失败: {e}")
            return {'risk_level': '中等风险', 'risk_score': 0.5}

    def _ai_investment_advice(self, fund_result: Dict) -> Dict:
        """AI投资建议"""
        try:
            ai_signal = fund_result.get('ai_signal', {})
            risk_assessment = fund_result.get('ai_risk_assessment', {})
            fundamental = fund_result.get('fundamental_analysis', {})

            signal = ai_signal.get('signal', '持有')
            risk_level = risk_assessment.get('risk_score', 0.5)
            performance = fundamental.get('comprehensive_score', 0.5)

            # AI投资建议
            if signal in ['买入', '谨慎买入'] and risk_level < 0.6 and performance > 0.6:
                advice = '强烈推荐投资'
                position = '30-50%'
                horizon = '中长期'
            elif signal in ['买入', '谨慎买入'] and performance > 0.5:
                advice = '推荐投资'
                position = '20-40%'
                horizon = '中期'
            elif signal == '持有':
                advice = '可适量持有'
                position = '10-30%'
                horizon = '短中期'
            else:
                advice = '建议观望'
                position = '0-10%'
                horizon = '短期'

            return {
                'investment_advice': advice,
                'position_suggestion': position,
                'investment_horizon': horizon,
                'confidence': ai_signal.get('confidence', 0.5),
                'key_points': [
                    f'AI信号: {signal}',
                    f'风险等级: {risk_assessment.get("risk_level", "中等")}',
                    f'综合评分: {performance:.2f}'
                ],
                'ai_reasoning': f'基于AI多维度分析，该基金{advice.lower()}'
            }

        except Exception as e:
            log_error(f"AI投资建议生成失败: {e}")
            return {
                'investment_advice': '谨慎投资',
                'position_suggestion': '10-20%',
                'confidence': 0.5
            }

    async def _ai_generate_reports(self, analysis_results: List[Dict]) -> Dict:
        """AI生成报告"""
        report_logger = create_task_logger("AI报告生成")
        report_logger.start("开始生成AI智能报告")

        try:
            # 生成市场总结
            market_summary = self.market_summary_gen.generate_market_summary(analysis_results)

            # 生成个股报告
            individual_reports = []
            for result in analysis_results[:10]:  # 只为前10只基金生成详细报告
                individual_report = self._generate_individual_report(result)
                individual_reports.append(individual_report)
                self.stats['reports_generated'] += 1

            # 生成投资组合建议
            portfolio_advice = self._generate_portfolio_advice(analysis_results)

            reports = {
                'market_summary': market_summary,
                'individual_reports': individual_reports,
                'portfolio_advice': portfolio_advice,
                'generation_time': datetime.now().isoformat(),
                'total_reports': len(individual_reports)
            }

            report_logger.success(f"AI报告生成完成，共生成 {len(individual_reports)} 份个股报告")
            return reports

        except Exception as e:
            report_logger.error(e, "AI报告生成失败")
            return {'market_summary': {}, 'individual_reports': [], 'portfolio_advice': {}}

    def _generate_individual_report(self, analysis_result: Dict) -> Dict:
        """生成个股报告"""
        try:
            fund_info = analysis_result.get('fund_info', {})
            ai_signal = analysis_result.get('ai_signal', {})
            investment_advice = analysis_result.get('ai_investment_advice', {})

            report = {
                'fund_code': fund_info.get('code', 'Unknown'),
                'fund_name': fund_info.get('name', 'Unknown'),
                'ai_rating': fund_info.get('investment_advice', {}).get('ai_rating', 'BBB'),
                'current_nav': fund_info.get('nav', 1.0),
                'daily_return': fund_info.get('daily_return', 0.0),
                'ai_signal': ai_signal.get('signal', '持有'),
                'signal_confidence': ai_signal.get('confidence', 0.5),
                'investment_advice': investment_advice.get('investment_advice', '谨慎投资'),
                'position_suggestion': investment_advice.get('position_suggestion', '10-20%'),
                'key_highlights': [
                    f"AI评级: {fund_info.get('investment_advice', {}).get('ai_rating', 'BBB')}",
                    f"当前净值: {fund_info.get('nav', 1.0)}",
                    f"AI信号: {ai_signal.get('signal', '持有')}",
                    f"投资建议: {investment_advice.get('investment_advice', '谨慎投资')}"
                ],
                'report_summary': f"AI分析显示，{fund_info.get('name', '该基金')}{investment_advice.get('investment_advice', '值得关注').lower()}，建议{investment_advice.get('position_suggestion', '适量')}配置。"
            }

            return report

        except Exception as e:
            log_error(f"生成个股报告失败: {e}")
            return {'fund_code': 'Error', 'report_summary': '报告生成失败'}

    def _generate_portfolio_advice(self, analysis_results: List[Dict]) -> Dict:
        """生成投资组合建议"""
        try:
            if not analysis_results:
                return {}

            # 统计不同信号的基金数量
            signals = {}
            risk_levels = {}
            fund_types = {}

            for result in analysis_results:
                signal = result.get('ai_signal', {}).get('signal', '持有')
                risk_level = result.get('ai_risk_assessment', {}).get('risk_level', '中等风险')
                fund_type = result.get('fund_info', {}).get('type', '混合型')

                signals[signal] = signals.get(signal, 0) + 1
                risk_levels[risk_level] = risk_levels.get(risk_level, 0) + 1
                fund_types[fund_type] = fund_types.get(fund_type, 0) + 1

            # 选择最佳组合
            top_funds = sorted(analysis_results, 
                             key=lambda x: x.get('ai_signal', {}).get('confidence', 0), 
                             reverse=True)[:5]

            portfolio_advice = {
                'recommended_funds': [
                    {
                        'fund_code': fund.get('fund_info', {}).get('code', ''),
                        'fund_name': fund.get('fund_info', {}).get('name', ''),
                        'weight': f'{20 - i*2}%',
                        'reason': fund.get('ai_investment_advice', {}).get('ai_reasoning', 'AI推荐')
                    }
                    for i, fund in enumerate(top_funds)
                ],
                'allocation_strategy': {
                    '股票型基金': '30-40%',
                    '混合型基金': '30-40%',
                    '债券型基金': '15-25%',
                    '其他': '5-15%'
                },
                'market_outlook': '基于AI分析，当前市场机会与风险并存，建议均衡配置',
                'rebalancing_frequency': '月度',
                'risk_control': '建议设置10%的止损线',
                'ai_confidence': 0.75
            }

            return portfolio_advice

        except Exception as e:
            log_error(f"生成投资组合建议失败: {e}")
            return {}

    def _generate_system_summary(self, analysis_results: List[Dict], reports: Dict) -> Dict:
        """生成系统总结"""
        runtime = datetime.now() - self.stats['start_time']

        return {
            'execution_summary': {
                'runtime_seconds': runtime.total_seconds(),
                'total_funds_processed': len(analysis_results),
                'successful_analyses': self.stats['successful_analyses'],
                'failed_analyses': self.stats['failed_analyses'],
                'reports_generated': self.stats['reports_generated'],
                'success_rate': self.stats['successful_analyses'] / max(self.stats['total_funds_analyzed'], 1)
            },
            'ai_insights': {
                'system_health': 'excellent' if self.stats['successful_analyses'] > 20 else 'good',
                'data_quality': 'high',
                'analysis_depth': 'comprehensive',
                'ai_confidence': 0.85
            },
            'next_recommendations': [
                '定期更新AI模型参数',
                '关注市场变化调整策略',
                '优化投资组合配置'
            ]
        }

    def _generate_emergency_results(self) -> Dict:
        """生成紧急结果"""
        log_warning("启动紧急模式，生成基础分析结果")

        emergency_funds = []
        for i, fund_code in enumerate(self.fund_pool[:5]):
            emergency_fund = {
                'fund_code': fund_code,
                'fund_info': self.smart_analyzer.generate_smart_fund_data(fund_code),
                'ai_signal': {'signal': '持有', 'confidence': 0.5},
                'emergency_mode': True
            }
            emergency_funds.append(emergency_fund)

        return {
            'fund_results': emergency_funds,
            'analysis_results': emergency_funds,
            'reports': {'emergency_report': '系统在紧急模式下运行'},
            'system_summary': {'mode': 'emergency'},
            'stats': self.stats
        }

    def _generate_emergency_fund_data(self, max_funds: int) -> List[Dict]:
        """生成紧急基金数据"""
        emergency_data = []
        for fund_code in self.fund_pool[:max_funds]:
            try:
                basic_data = self.smart_analyzer.generate_smart_fund_data(fund_code)
                emergency_data.append({
                    'fund_code': fund_code,
                    'fund_info': basic_data,
                    'emergency_generated': True
                })
            except:
                pass
        return emergency_data

    def _get_default_technical_analysis(self) -> Dict:
        """获取默认技术分析"""
        return {
            'current_nav': 1.5,
            'rsi': 50,
            'macd': 0,
            'ai_signals': ['震荡趋势'],
            'analysis_confidence': 0.5
        }

    def save_results_to_files(self, results: Dict):
        """保存结果到文件"""
        try:
            import os
            from pathlib import Path

            # 创建目录
            reports_dir = Path('reports')
            reports_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # 保存市场总结
            market_summary = results.get('reports', {}).get('market_summary', {})
            if market_summary:
                market_file = reports_dir / f'ai_market_summary_{timestamp}.json'
                with open(market_file, 'w', encoding='utf-8') as f:
                    json.dump(market_summary, f, ensure_ascii=False, indent=2, default=str)
                log_info(f"AI市场总结已保存: {market_file}")

            # 保存系统总结
            system_summary = results.get('system_summary', {})
            if system_summary:
                summary_file = reports_dir / f'ai_system_summary_{timestamp}.json'
                with open(summary_file, 'w', encoding='utf-8') as f:
                    json.dump(system_summary, f, ensure_ascii=False, indent=2, default=str)
                log_info(f"AI系统总结已保存: {summary_file}")

            # 生成今日报告
            self._generate_today_report(results, reports_dir)

        except Exception as e:
            log_error(f"保存结果文件失败: {e}")

    def _generate_today_report(self, results: Dict, reports_dir: Path):
        """生成今日报告"""
        try:
            market_summary = results.get('reports', {}).get('market_summary', {})
            individual_reports = results.get('reports', {}).get('individual_reports', [])

            report_content = f"""# AI基金分析日报

## 📊 市场概述
{market_summary.get('market_overview', 'AI智能分析显示市场表现平稳')}

## 🎯 基金分析
{market_summary.get('fund_analysis', 'AI分析了多只优质基金，表现分化明显')}

## 💡 AI投资建议
{market_summary.get('investment_advice', 'AI建议均衡配置，关注优质基金')}

## 📈 重点关注基金
"""

            for report in individual_reports[:5]:
                report_content += f"""
### {report.get('fund_name', 'Unknown')} ({report.get('fund_code', 'Unknown')})
- **AI评级**: {report.get('ai_rating', 'BBB')}
- **当前净值**: {report.get('current_nav', 1.0)}
- **AI信号**: {report.get('ai_signal', '持有')}
- **投资建议**: {report.get('investment_advice', '谨慎投资')}
"""

            report_content += f"""
## 🤖 AI系统总结
- 分析基金数量: {results.get('system_summary', {}).get('execution_summary', {}).get('total_funds_processed', 0)}
- 成功率: {results.get('system_summary', {}).get('execution_summary', {}).get('success_rate', 0):.1%}
- AI置信度: {results.get('system_summary', {}).get('ai_insights', {}).get('ai_confidence', 0.8):.2f}

---
*本报告由AI智能生成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

            today_report_file = reports_dir / 'today_report.md'
            with open(today_report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)

            log_info(f"今日AI报告已生成: {today_report_file}")

        except Exception as e:
            log_error(f"生成今日报告失败: {e}")
