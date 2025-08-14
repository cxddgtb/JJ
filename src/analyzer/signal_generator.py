"""
信号生成器 - 综合各种分析结果生成买卖信号
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from ..utils.logger import log_info, log_warning, log_error, log_debug
from ..config import SIGNAL_CONFIG, FUND_TYPES

class SignalType(Enum):
    """信号类型"""
    STRONG_BUY = "强烈买入"
    BUY = "买入"
    WEAK_BUY = "谨慎买入"
    HOLD = "持有"
    WEAK_SELL = "谨慎卖出"
    SELL = "卖出"
    STRONG_SELL = "强烈卖出"

@dataclass
class TradingSignal:
    """交易信号"""
    fund_code: str
    signal_type: SignalType
    confidence: float  # 0-1之间
    score: float  # 0-100分
    entry_price: float
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    holding_period: Optional[int] = None  # 预期持有天数
    reasoning: List[str] = None
    risk_level: str = "中等"
    position_size: str = "适中"  # 建议仓位大小
    timestamp: datetime = None

    def __post_init__(self):
        if self.reasoning is None:
            self.reasoning = []
        if self.timestamp is None:
            self.timestamp = datetime.now()

class SignalGenerator:
    """信号生成器"""

    def __init__(self):
        self.weight_config = {
            'technical': 0.35,      # 技术分析权重
            'fundamental': 0.30,    # 基本面分析权重
            'sentiment': 0.20,      # 情绪分析权重
            'market': 0.15          # 市场环境权重
        }

        # 不同基金类型的权重调整
        self.fund_type_weights = {
            'equity': {'technical': 0.4, 'fundamental': 0.3, 'sentiment': 0.2, 'market': 0.1},
            'bond': {'technical': 0.2, 'fundamental': 0.4, 'sentiment': 0.1, 'market': 0.3},
            'hybrid': {'technical': 0.35, 'fundamental': 0.35, 'sentiment': 0.2, 'market': 0.1},
            'index': {'technical': 0.5, 'fundamental': 0.2, 'sentiment': 0.2, 'market': 0.1},
            'money_market': {'technical': 0.1, 'fundamental': 0.3, 'sentiment': 0.1, 'market': 0.5}
        }

    def generate_signal(self, analysis_results: Dict) -> TradingSignal:
        """生成交易信号"""
        try:
            fund_code = analysis_results.get('fund_code', '')
            fund_type = self._determine_fund_type(analysis_results)

            # 获取各项分析结果
            technical_analysis = analysis_results.get('technical_analysis', {})
            fundamental_analysis = analysis_results.get('fundamental_analysis', {})
            sentiment_analysis = analysis_results.get('sentiment_analysis', {})
            market_analysis = analysis_results.get('market_analysis', {})

            # 计算各项得分
            technical_score = self._calculate_technical_score(technical_analysis)
            fundamental_score = self._calculate_fundamental_score(fundamental_analysis)
            sentiment_score = self._calculate_sentiment_score(sentiment_analysis)
            market_score = self._calculate_market_score(market_analysis)

            # 根据基金类型调整权重
            weights = self.fund_type_weights.get(fund_type, self.weight_config)

            # 计算综合得分
            composite_score = (
                technical_score * weights['technical'] +
                fundamental_score * weights['fundamental'] +
                sentiment_score * weights['sentiment'] +
                market_score * weights['market']
            )

            # 生成信号
            signal_type, confidence = self._determine_signal_type(composite_score, analysis_results)

            # 计算价格目标
            current_price = self._get_current_price(analysis_results)
            target_price, stop_loss = self._calculate_price_targets(
                signal_type, current_price, technical_analysis, fundamental_analysis
            )

            # 生成推理说明
            reasoning = self._generate_reasoning(
                signal_type, technical_analysis, fundamental_analysis, 
                sentiment_analysis, market_analysis
            )

            # 评估风险和建议仓位
            risk_level = self._assess_risk_level(analysis_results)
            position_size = self._suggest_position_size(signal_type, risk_level, composite_score)

            # 预期持有期间
            holding_period = self._estimate_holding_period(signal_type, fund_type, technical_analysis)

            return TradingSignal(
                fund_code=fund_code,
                signal_type=signal_type,
                confidence=confidence,
                score=round(composite_score, 1),
                entry_price=current_price,
                target_price=target_price,
                stop_loss=stop_loss,
                holding_period=holding_period,
                reasoning=reasoning,
                risk_level=risk_level,
                position_size=position_size
            )

        except Exception as e:
            log_error(f"生成交易信号失败: {e}")
            return self._create_default_signal(analysis_results.get('fund_code', ''))

    def _determine_fund_type(self, analysis_results: Dict) -> str:
        """确定基金类型"""
        fund_info = analysis_results.get('fundamental_analysis', {}).get('basic_info', {})
        fund_name = fund_info.get('fund_name', '')
        fund_type = fund_info.get('fund_type', '')

        # 根据基金名称和类型判断
        if any(keyword in fund_name for keyword in ['股票', '成长', '价值', '主题']):
            return 'equity'
        elif any(keyword in fund_name for keyword in ['债券', '纯债', '信用']):
            return 'bond'
        elif any(keyword in fund_name for keyword in ['混合', '配置', '平衡']):
            return 'hybrid'
        elif any(keyword in fund_name for keyword in ['指数', 'ETF', 'LOF']):
            return 'index'
        elif any(keyword in fund_name for keyword in ['货币', '现金']):
            return 'money_market'
        else:
            return 'hybrid'  # 默认为混合型

    def _calculate_technical_score(self, technical_analysis: Dict) -> float:
        """计算技术分析得分"""
        if not technical_analysis:
            return 50.0

        score = 50.0  # 基础分数

        try:
            # 移动平均线得分
            ma_data = technical_analysis.get('moving_averages', {})
            if ma_data.get('ma_alignment') == '多头排列':
                score += 15
            elif ma_data.get('ma_alignment') == '空头排列':
                score -= 15

            if ma_data.get('golden_cross'):
                score += 10
            elif ma_data.get('death_cross'):
                score -= 10

            # MACD得分
            macd_data = technical_analysis.get('macd', {})
            if macd_data.get('signal_cross') == '金叉':
                score += 8
            elif macd_data.get('signal_cross') == '死叉':
                score -= 8

            if macd_data.get('zero_cross') == '上穿零轴':
                score += 5
            elif macd_data.get('zero_cross') == '下穿零轴':
                score -= 5

            # RSI得分
            rsi_data = technical_analysis.get('rsi', {})
            rsi_value = rsi_data.get('rsi', 50)
            if 30 <= rsi_value <= 70:
                score += 5  # 正常范围
            elif rsi_value < 20:
                score += 10  # 超卖
            elif rsi_value > 80:
                score -= 10  # 超买

            # 布林带得分
            bb_data = technical_analysis.get('bollinger_bands', {})
            bb_signal = bb_data.get('bb_signal', '')
            if bb_signal == '接近下轨':
                score += 8
            elif bb_signal == '突破上轨':
                score -= 8

            # 成交量得分
            volume_data = technical_analysis.get('volume_indicators', {})
            if volume_data.get('volume_trend') == 'increasing':
                score += 5

            # 趋势得分
            trend_data = technical_analysis.get('trend_indicators', {})
            trend_strength = trend_data.get('trend_strength', 0)
            score += trend_strength * 10

            # 限制得分范围
            score = max(0, min(100, score))

        except Exception as e:
            log_debug(f"技术分析得分计算失败: {e}")
            return 50.0

        return score

    def _calculate_fundamental_score(self, fundamental_analysis: Dict) -> float:
        """计算基本面分析得分"""
        if not fundamental_analysis:
            return 50.0

        score = 50.0  # 基础分数

        try:
            # 业绩得分
            performance = fundamental_analysis.get('performance_metrics', {})
            annual_return = performance.get('annual_return', 0)
            sharpe_ratio = performance.get('sharpe_ratio', 0)
            max_drawdown = performance.get('max_drawdown', 0)

            # 年化收益率得分
            if annual_return > 15:
                score += 20
            elif annual_return > 8:
                score += 10
            elif annual_return > 0:
                score += 5
            elif annual_return < -10:
                score -= 15
            elif annual_return < 0:
                score -= 5

            # 夏普比率得分
            if sharpe_ratio > 1.5:
                score += 15
            elif sharpe_ratio > 1.0:
                score += 10
            elif sharpe_ratio > 0.5:
                score += 5
            elif sharpe_ratio < 0:
                score -= 10

            # 最大回撤得分
            if max_drawdown > -5:
                score += 10
            elif max_drawdown > -10:
                score += 5
            elif max_drawdown < -30:
                score -= 15
            elif max_drawdown < -20:
                score -= 10

            # 费用得分
            fee_analysis = fundamental_analysis.get('fee_analysis', {})
            management_fee = fee_analysis.get('management_fee_rate', 1.5)
            if management_fee < 1.0:
                score += 5
            elif management_fee > 2.0:
                score -= 5

            # 规模得分
            size_analysis = fundamental_analysis.get('size_analysis', {})
            fund_size = size_analysis.get('fund_size_category', '')
            if fund_size in ['大型', '中大型']:
                score += 5
            elif fund_size in ['迷你']:
                score -= 10

            # 经理得分
            manager_analysis = fundamental_analysis.get('manager_analysis', {})
            manager_experience = manager_analysis.get('avg_experience', 0)
            if manager_experience > 5:
                score += 5
            elif manager_experience > 10:
                score += 10

            # 限制得分范围
            score = max(0, min(100, score))

        except Exception as e:
            log_debug(f"基本面分析得分计算失败: {e}")
            return 50.0

        return score

    def _calculate_sentiment_score(self, sentiment_analysis: Dict) -> float:
        """计算情绪分析得分"""
        if not sentiment_analysis:
            return 50.0

        score = 50.0  # 基础分数

        try:
            news_sentiment = sentiment_analysis.get('news_sentiment', {})
            overall_sentiment = news_sentiment.get('overall_sentiment', 0)

            # 新闻情绪得分 (-1到1映射到0-100)
            sentiment_score = (overall_sentiment + 1) * 50

            # 社交媒体情绪
            social_sentiment = sentiment_analysis.get('social_sentiment', {})
            social_score = social_sentiment.get('overall_sentiment', 0)
            social_score = (social_score + 1) * 50

            # 机构情绪
            institutional_sentiment = sentiment_analysis.get('institutional_sentiment', {})
            institutional_score = institutional_sentiment.get('bullish_ratio', 0.5) * 100

            # 加权平均
            score = (sentiment_score * 0.4 + social_score * 0.3 + institutional_score * 0.3)

            # 情绪趋势调整
            sentiment_trend = news_sentiment.get('sentiment_trend', '')
            if sentiment_trend == '情绪改善':
                score += 5
            elif sentiment_trend == '情绪恶化':
                score -= 5

            # 限制得分范围
            score = max(0, min(100, score))

        except Exception as e:
            log_debug(f"情绪分析得分计算失败: {e}")
            return 50.0

        return score

    def _calculate_market_score(self, market_analysis: Dict) -> float:
        """计算市场环境得分"""
        if not market_analysis:
            return 50.0

        score = 50.0  # 基础分数

        try:
            # 市场趋势
            market_trend = market_analysis.get('market_trend', {})
            trend_direction = market_trend.get('direction', 'sideways')

            if trend_direction == 'up':
                score += 15
            elif trend_direction == 'down':
                score -= 15

            # VIX恐慌指数
            vix_level = market_analysis.get('vix_level', 20)
            if vix_level < 15:
                score += 10  # 低恐慌
            elif vix_level > 30:
                score -= 10  # 高恐慌

            # 利率环境
            interest_rate_trend = market_analysis.get('interest_rate_trend', 'stable')
            if interest_rate_trend == 'falling':
                score += 8  # 降息利好
            elif interest_rate_trend == 'rising':
                score -= 8  # 加息利空

            # 经济指标
            economic_indicators = market_analysis.get('economic_indicators', {})
            gdp_growth = economic_indicators.get('gdp_growth', 0)
            if gdp_growth > 6:
                score += 10
            elif gdp_growth < 2:
                score -= 10

            # 限制得分范围
            score = max(0, min(100, score))

        except Exception as e:
            log_debug(f"市场环境得分计算失败: {e}")
            return 50.0

        return score

    def _determine_signal_type(self, composite_score: float, analysis_results: Dict) -> Tuple[SignalType, float]:
        """确定信号类型和置信度"""
        # 获取配置
        buy_config = SIGNAL_CONFIG['buy_signals']
        sell_config = SIGNAL_CONFIG['sell_signals']
        hold_config = SIGNAL_CONFIG['hold_threshold']

        # 计算置信度
        confidence = min(1.0, abs(composite_score - 50) / 50)

        # 确定信号类型
        if composite_score >= buy_config['strong_buy']['score_threshold']:
            return SignalType.STRONG_BUY, min(confidence, buy_config['strong_buy']['confidence'])
        elif composite_score >= buy_config['buy']['score_threshold']:
            return SignalType.BUY, min(confidence, buy_config['buy']['confidence'])
        elif composite_score >= buy_config['weak_buy']['score_threshold']:
            return SignalType.WEAK_BUY, min(confidence, buy_config['weak_buy']['confidence'])
        elif composite_score <= sell_config['strong_sell']['score_threshold']:
            return SignalType.STRONG_SELL, min(confidence, sell_config['strong_sell']['confidence'])
        elif composite_score <= sell_config['sell']['score_threshold']:
            return SignalType.SELL, min(confidence, sell_config['sell']['confidence'])
        elif composite_score <= sell_config['weak_sell']['score_threshold']:
            return SignalType.WEAK_SELL, min(confidence, sell_config['weak_sell']['confidence'])
        else:
            return SignalType.HOLD, 0.5

    def _get_current_price(self, analysis_results: Dict) -> float:
        """获取当前价格"""
        try:
            # 从技术分析中获取最新价格
            technical = analysis_results.get('technical_analysis', {})
            latest_price = technical.get('latest_price', 0)

            if latest_price > 0:
                return latest_price

            # 从基本面分析中获取
            fundamental = analysis_results.get('fundamental_analysis', {})
            current_nav = fundamental.get('basic_info', {}).get('current_nav', 0)

            return current_nav if current_nav > 0 else 1.0

        except Exception:
            return 1.0

    def _calculate_price_targets(self, signal_type: SignalType, current_price: float, 
                               technical_analysis: Dict, fundamental_analysis: Dict) -> Tuple[Optional[float], Optional[float]]:
        """计算价格目标和止损位"""
        if current_price <= 0:
            return None, None

        try:
            target_price = None
            stop_loss = None

            if signal_type in [SignalType.STRONG_BUY, SignalType.BUY, SignalType.WEAK_BUY]:
                # 买入信号的目标价和止损

                # 技术分析支撑阻力位
                support_resistance = technical_analysis.get('support_resistance', {})
                resistance_levels = support_resistance.get('resistance_levels', [])
                support_levels = support_resistance.get('support_levels', [])

                if resistance_levels:
                    # 目标价设为下一个阻力位
                    next_resistance = min([r for r in resistance_levels if r > current_price], default=None)
                    if next_resistance:
                        target_price = next_resistance * 0.95  # 略低于阻力位

                if support_levels:
                    # 止损设为下一个支撑位
                    next_support = max([s for s in support_levels if s < current_price], default=None)
                    if next_support:
                        stop_loss = next_support * 1.02  # 略高于支撑位

                # 如果没有技术位，使用百分比
                if not target_price:
                    if signal_type == SignalType.STRONG_BUY:
                        target_price = current_price * 1.15  # 15%目标
                    elif signal_type == SignalType.BUY:
                        target_price = current_price * 1.10  # 10%目标
                    else:
                        target_price = current_price * 1.05  # 5%目标

                if not stop_loss:
                    stop_loss = current_price * 0.95  # 5%止损

            elif signal_type in [SignalType.STRONG_SELL, SignalType.SELL, SignalType.WEAK_SELL]:
                # 卖出信号只设止损（反弹卖出点）
                if signal_type == SignalType.STRONG_SELL:
                    stop_loss = current_price * 1.03  # 3%反弹即卖出
                elif signal_type == SignalType.SELL:
                    stop_loss = current_price * 1.05  # 5%反弹卖出
                else:
                    stop_loss = current_price * 1.08  # 8%反弹卖出

            return target_price, stop_loss

        except Exception as e:
            log_debug(f"计算价格目标失败: {e}")
            return None, None

    def _generate_reasoning(self, signal_type: SignalType, technical_analysis: Dict, 
                          fundamental_analysis: Dict, sentiment_analysis: Dict, 
                          market_analysis: Dict) -> List[str]:
        """生成推理说明"""
        reasoning = []

        try:
            # 技术面推理
            if technical_analysis:
                ma_alignment = technical_analysis.get('moving_averages', {}).get('ma_alignment', '')
                if ma_alignment == '多头排列':
                    reasoning.append("技术面：均线呈多头排列，趋势向好")
                elif ma_alignment == '空头排列':
                    reasoning.append("技术面：均线呈空头排列，趋势偏弱")

                macd_cross = technical_analysis.get('macd', {}).get('signal_cross', '')
                if macd_cross == '金叉':
                    reasoning.append("技术面：MACD出现金叉信号")
                elif macd_cross == '死叉':
                    reasoning.append("技术面：MACD出现死叉信号")

                rsi_signal = technical_analysis.get('rsi', {}).get('rsi_signal', '')
                if rsi_signal == '超卖':
                    reasoning.append("技术面：RSI显示超卖，存在反弹机会")
                elif rsi_signal == '超买':
                    reasoning.append("技术面：RSI显示超买，注意回调风险")

            # 基本面推理
            if fundamental_analysis:
                performance = fundamental_analysis.get('performance_metrics', {})
                annual_return = performance.get('annual_return', 0)
                sharpe_ratio = performance.get('sharpe_ratio', 0)

                if annual_return > 10:
                    reasoning.append(f"基本面：年化收益率{annual_return:.1f}%，表现优秀")
                elif annual_return < 0:
                    reasoning.append(f"基本面：年化收益率{annual_return:.1f}%，表现不佳")

                if sharpe_ratio > 1.0:
                    reasoning.append(f"基本面：夏普比率{sharpe_ratio:.2f}，风险调整后收益良好")
                elif sharpe_ratio < 0:
                    reasoning.append(f"基本面：夏普比率{sharpe_ratio:.2f}，风险调整后收益较差")

                fee_analysis = fundamental_analysis.get('fee_analysis', {})
                if fee_analysis.get('fee_level') == '低':
                    reasoning.append("基本面：费用水平较低，成本优势明显")
                elif fee_analysis.get('fee_level') == '高':
                    reasoning.append("基本面：费用水平较高，增加投资成本")

            # 情绪面推理
            if sentiment_analysis:
                news_sentiment = sentiment_analysis.get('news_sentiment', {})
                overall_sentiment = news_sentiment.get('overall_sentiment', 0)

                if overall_sentiment > 0.2:
                    reasoning.append("情绪面：新闻情绪偏正面，市场氛围乐观")
                elif overall_sentiment < -0.2:
                    reasoning.append("情绪面：新闻情绪偏负面，市场氛围悲观")

                sentiment_trend = news_sentiment.get('sentiment_trend', '')
                if sentiment_trend == '情绪改善':
                    reasoning.append("情绪面：情绪趋势向好，投资者信心回升")
                elif sentiment_trend == '情绪恶化':
                    reasoning.append("情绪面：情绪趋势恶化，投资者信心不足")

            # 市场环境推理
            if market_analysis:
                market_trend = market_analysis.get('market_trend', {}).get('direction', '')
                if market_trend == 'up':
                    reasoning.append("市场环境：大市趋势向上，有利于基金表现")
                elif market_trend == 'down':
                    reasoning.append("市场环境：大市趋势向下，不利于基金表现")

                vix_level = market_analysis.get('vix_level', 20)
                if vix_level < 15:
                    reasoning.append("市场环境：恐慌指数较低，市场相对稳定")
                elif vix_level > 30:
                    reasoning.append("市场环境：恐慌指数较高，市场波动较大")

            # 如果没有推理，添加默认说明
            if not reasoning:
                reasoning.append(f"综合分析显示{signal_type.value}信号")

        except Exception as e:
            log_debug(f"生成推理说明失败: {e}")
            reasoning = [f"综合分析显示{signal_type.value}信号"]

        return reasoning

    def _assess_risk_level(self, analysis_results: Dict) -> str:
        """评估风险水平"""
        try:
            risk_score = 0

            # 技术面风险
            technical = analysis_results.get('technical_analysis', {})
            volatility = technical.get('volatility_indicators', {}).get('volatility', 0)
            if volatility > 30:
                risk_score += 2
            elif volatility > 20:
                risk_score += 1

            # 基本面风险
            fundamental = analysis_results.get('fundamental_analysis', {})
            max_drawdown = fundamental.get('risk_metrics', {}).get('max_drawdown', 0)
            if max_drawdown < -30:
                risk_score += 2
            elif max_drawdown < -20:
                risk_score += 1

            # 市场环境风险
            market = analysis_results.get('market_analysis', {})
            vix_level = market.get('vix_level', 20)
            if vix_level > 30:
                risk_score += 2
            elif vix_level > 25:
                risk_score += 1

            # 确定风险等级
            if risk_score >= 4:
                return "高风险"
            elif risk_score >= 2:
                return "中等风险"
            else:
                return "低风险"

        except Exception:
            return "中等风险"

    def _suggest_position_size(self, signal_type: SignalType, risk_level: str, score: float) -> str:
        """建议仓位大小"""
        try:
            if signal_type in [SignalType.STRONG_BUY, SignalType.BUY]:
                if risk_level == "低风险" and score > 80:
                    return "重仓 (50-70%)"
                elif risk_level == "中等风险" or score > 70:
                    return "中仓 (30-50%)"
                else:
                    return "轻仓 (10-30%)"

            elif signal_type == SignalType.WEAK_BUY:
                if risk_level == "低风险":
                    return "轻仓 (10-30%)"
                else:
                    return "观察仓位 (5-15%)"

            elif signal_type == SignalType.HOLD:
                return "维持现有仓位"

            else:  # 卖出信号
                if signal_type == SignalType.STRONG_SELL:
                    return "清仓"
                elif signal_type == SignalType.SELL:
                    return "大幅减仓 (减持50-80%)"
                else:
                    return "适度减仓 (减持20-50%)"

        except Exception:
            return "适中仓位"

    def _estimate_holding_period(self, signal_type: SignalType, fund_type: str, technical_analysis: Dict) -> Optional[int]:
        """估计持有期间"""
        try:
            # 基于信号类型和基金类型
            base_periods = {
                SignalType.STRONG_BUY: {'equity': 90, 'bond': 180, 'hybrid': 120, 'index': 60, 'money_market': 30},
                SignalType.BUY: {'equity': 60, 'bond': 120, 'hybrid': 90, 'index': 45, 'money_market': 30},
                SignalType.WEAK_BUY: {'equity': 30, 'bond': 60, 'hybrid': 45, 'index': 30, 'money_market': 15},
                SignalType.HOLD: {'equity': 180, 'bond': 365, 'hybrid': 270, 'index': 180, 'money_market': 90},
            }

            if signal_type in base_periods:
                return base_periods[signal_type].get(fund_type, 60)
            else:
                return None  # 卖出信号不设持有期间

        except Exception:
            return None

    def _create_default_signal(self, fund_code: str) -> TradingSignal:
        """创建默认信号"""
        return TradingSignal(
            fund_code=fund_code,
            signal_type=SignalType.HOLD,
            confidence=0.5,
            score=50.0,
            entry_price=1.0,
            reasoning=["数据不足，建议观望"]
        )

    def generate_portfolio_signals(self, multiple_analysis: Dict[str, Dict]) -> Dict[str, TradingSignal]:
        """为投资组合生成信号"""
        portfolio_signals = {}

        for fund_code, analysis_results in multiple_analysis.items():
            try:
                signal = self.generate_signal(analysis_results)
                portfolio_signals[fund_code] = signal
                log_info(f"生成信号: {fund_code} - {signal.signal_type.value} (置信度: {signal.confidence:.2f})")
            except Exception as e:
                log_error(f"生成信号失败 {fund_code}: {e}")
                portfolio_signals[fund_code] = self._create_default_signal(fund_code)

        return portfolio_signals

    def rank_signals_by_attractiveness(self, signals: Dict[str, TradingSignal]) -> List[Tuple[str, TradingSignal]]:
        """按吸引力排序信号"""
        # 计算吸引力得分
        attractiveness_scores = []

        for fund_code, signal in signals.items():
            # 吸引力得分 = 综合得分 * 置信度 * 信号强度权重
            signal_weights = {
                SignalType.STRONG_BUY: 1.0,
                SignalType.BUY: 0.8,
                SignalType.WEAK_BUY: 0.6,
                SignalType.HOLD: 0.2,
                SignalType.WEAK_SELL: -0.6,
                SignalType.SELL: -0.8,
                SignalType.STRONG_SELL: -1.0
            }

            weight = signal_weights.get(signal.signal_type, 0)
            attractiveness = signal.score * signal.confidence * weight
            attractiveness_scores.append((fund_code, signal, attractiveness))

        # 按吸引力得分排序
        attractiveness_scores.sort(key=lambda x: x[2], reverse=True)

        return [(fund_code, signal) for fund_code, signal, _ in attractiveness_scores]

# 创建全局信号生成器实例
signal_generator = SignalGenerator()
