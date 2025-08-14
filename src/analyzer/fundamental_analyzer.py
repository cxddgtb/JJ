"""
基本面分析模块 - 基金基本面指标分析
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import akshare as ak

from ..utils.logger import log_info, log_warning, log_error, log_debug

@dataclass
class FundamentalMetrics:
    """基本面指标"""
    fund_code: str
    fund_name: str
    fund_type: str
    fund_size: float
    management_fee: float
    custody_fee: float
    sales_fee: float
    establishment_date: str
    fund_manager: str
    management_company: str
    risk_level: str
    investment_target: str
    investment_scope: str
    benchmark: str

    # 业绩指标
    total_return: float
    annual_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    calmar_ratio: float
    sortino_ratio: float

    # 风险指标
    beta: float
    alpha: float
    tracking_error: float
    information_ratio: float
    var_95: float

    # 持仓分析
    stock_position_ratio: float
    bond_position_ratio: float
    cash_position_ratio: float
    top10_holdings_ratio: float
    industry_concentration: float

    # 评级
    morningstar_rating: Optional[int]
    company_rating: Optional[str]
    fund_score: float

class FundamentalAnalyzer:
    """基本面分析器"""

    def __init__(self):
        self.risk_free_rate = 0.025  # 无风险利率，假设为2.5%
        self.market_return = 0.08    # 市场平均回报率

    def analyze(self, fund_code: str, fund_data: Dict, history_data: pd.DataFrame) -> Dict:
        """综合基本面分析"""
        try:
            # 基础信息分析
            basic_info = self._analyze_basic_info(fund_code, fund_data)

            # 业绩分析
            performance_metrics = self._analyze_performance(history_data)

            # 风险分析
            risk_metrics = self._analyze_risk(history_data, fund_data)

            # 费用分析
            fee_analysis = self._analyze_fees(fund_data)

            # 规模分析
            size_analysis = self._analyze_fund_size(fund_data)

            # 经理分析
            manager_analysis = self._analyze_fund_manager(fund_data)

            # 持仓分析
            holdings_analysis = self._analyze_holdings(fund_data)

            # 同类比较
            peer_comparison = self._compare_with_peers(fund_code, fund_data)

            # 投资风格分析
            style_analysis = self._analyze_investment_style(fund_data, history_data)

            # 市场环境适应性
            market_adaptation = self._analyze_market_adaptation(history_data)

            # 综合评分
            fundamental_score = self._calculate_fundamental_score({
                'performance': performance_metrics,
                'risk': risk_metrics,
                'fees': fee_analysis,
                'size': size_analysis,
                'manager': manager_analysis,
                'holdings': holdings_analysis
            })

            return {
                'fund_code': fund_code,
                'analysis_time': datetime.now(),
                'basic_info': basic_info,
                'performance_metrics': performance_metrics,
                'risk_metrics': risk_metrics,
                'fee_analysis': fee_analysis,
                'size_analysis': size_analysis,
                'manager_analysis': manager_analysis,
                'holdings_analysis': holdings_analysis,
                'peer_comparison': peer_comparison,
                'style_analysis': style_analysis,
                'market_adaptation': market_adaptation,
                'fundamental_score': fundamental_score,
                'recommendation': self._get_recommendation(fundamental_score),
                'strengths': self._identify_strengths(fund_data, performance_metrics, risk_metrics),
                'weaknesses': self._identify_weaknesses(fund_data, performance_metrics, risk_metrics),
                'investment_advice': self._generate_investment_advice(fundamental_score, risk_metrics)
            }

        except Exception as e:
            log_error(f"基本面分析失败 {fund_code}: {e}")
            return {}

    def _analyze_basic_info(self, fund_code: str, fund_data: Dict) -> Dict:
        """分析基础信息"""
        try:
            # 从akshare获取详细信息
            fund_info = self._get_fund_basic_info(fund_code)

            return {
                'fund_code': fund_code,
                'fund_name': fund_data.get('name', ''),
                'fund_type': fund_data.get('type', ''),
                'establishment_date': fund_info.get('establishment_date', ''),
                'fund_manager': ', '.join([m.get('name', '') for m in fund_data.get('managers', [])]),
                'management_company': fund_info.get('management_company', ''),
                'custodian_bank': fund_info.get('custodian_bank', ''),
                'fund_size': fund_data.get('fund_size', 0),
                'total_shares': fund_info.get('total_shares', 0),
                'risk_level': fund_info.get('risk_level', ''),
                'investment_objective': fund_info.get('investment_objective', ''),
                'investment_scope': fund_info.get('investment_scope', ''),
                'benchmark': fund_info.get('benchmark', ''),
                'dividend_policy': fund_info.get('dividend_policy', ''),
                'operation_years': self._calculate_operation_years(fund_info.get('establishment_date', '')),
                'is_index_fund': '指数' in fund_data.get('name', ''),
                'is_etf': 'ETF' in fund_data.get('name', ''),
                'is_money_market': fund_data.get('type', '') == '货币市场基金'
            }

        except Exception as e:
            log_debug(f"基础信息分析失败: {e}")
            return {}

    def _get_fund_basic_info(self, fund_code: str) -> Dict:
        """获取基金基础信息"""
        try:
            # 使用akshare获取基金信息
            fund_info_df = ak.fund_em_open_fund_info(fund=fund_code, indicator="基金信息")

            if not fund_info_df.empty:
                info = fund_info_df.to_dict('records')[0] if len(fund_info_df) > 0 else {}
                return {
                    'establishment_date': info.get('成立日期', ''),
                    'management_company': info.get('基金公司', ''),
                    'custodian_bank': info.get('托管银行', ''),
                    'risk_level': info.get('风险等级', ''),
                    'investment_objective': info.get('投资目标', ''),
                    'investment_scope': info.get('投资范围', ''),
                    'benchmark': info.get('业绩比较基准', ''),
                    'dividend_policy': info.get('分红政策', ''),
                    'total_shares': info.get('基金份额', 0)
                }

        except Exception as e:
            log_debug(f"获取基金基础信息失败: {e}")

        return {}

    def _calculate_operation_years(self, establishment_date: str) -> float:
        """计算运作年限"""
        try:
            if not establishment_date:
                return 0

            est_date = pd.to_datetime(establishment_date)
            years = (datetime.now() - est_date).days / 365.25
            return round(years, 2)

        except Exception:
            return 0

    def _analyze_performance(self, history_data: pd.DataFrame) -> Dict:
        """分析业绩表现"""
        if history_data.empty:
            return {}

        try:
            # 确保数据格式正确
            if 'nav' in history_data.columns:
                returns = history_data['nav'].pct_change().dropna()
            elif 'close' in history_data.columns:
                returns = history_data['close'].pct_change().dropna()
            else:
                return {}

            if returns.empty:
                return {}

            # 计算各种业绩指标
            total_return = (history_data.iloc[-1]['nav'] / history_data.iloc[0]['nav'] - 1) * 100 if 'nav' in history_data.columns else 0

            # 年化收益率
            days = len(history_data)
            annual_return = ((1 + total_return/100) ** (252/days) - 1) * 100 if days > 0 else 0

            # 波动率（年化）
            volatility = returns.std() * np.sqrt(252) * 100

            # 夏普比率
            excess_return = annual_return - self.risk_free_rate * 100
            sharpe_ratio = excess_return / volatility if volatility > 0 else 0

            # 最大回撤
            cumulative = (1 + returns).cumprod()
            rolling_max = cumulative.expanding().max()
            drawdown = (cumulative / rolling_max - 1) * 100
            max_drawdown = drawdown.min()

            # 卡玛比率
            calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

            # 下行波动率和索提诺比率
            downside_returns = returns[returns < 0]
            downside_vol = downside_returns.std() * np.sqrt(252) * 100 if len(downside_returns) > 0 else 0
            sortino_ratio = excess_return / downside_vol if downside_vol > 0 else 0

            # 不同期间收益率
            period_returns = self._calculate_period_returns(history_data)

            # 收益率分布
            return_distribution = self._analyze_return_distribution(returns)

            # 胜率统计
            win_rate = (returns > 0).sum() / len(returns) * 100 if len(returns) > 0 else 0

            return {
                'total_return': round(total_return, 2),
                'annual_return': round(annual_return, 2),
                'volatility': round(volatility, 2),
                'sharpe_ratio': round(sharpe_ratio, 3),
                'max_drawdown': round(max_drawdown, 2),
                'calmar_ratio': round(calmar_ratio, 3),
                'sortino_ratio': round(sortino_ratio, 3),
                'downside_volatility': round(downside_vol, 2),
                'win_rate': round(win_rate, 2),
                'period_returns': period_returns,
                'return_distribution': return_distribution,
                'performance_grade': self._grade_performance(annual_return, volatility, sharpe_ratio)
            }

        except Exception as e:
            log_debug(f"业绩分析失败: {e}")
            return {}

    def _calculate_period_returns(self, history_data: pd.DataFrame) -> Dict:
        """计算不同期间收益率"""
        period_returns = {}

        try:
            if 'nav' in history_data.columns:
                nav_col = 'nav'
            elif 'close' in history_data.columns:
                nav_col = 'close'
            else:
                return {}

            current_nav = history_data[nav_col].iloc[-1]

            # 定义时间期间
            periods = {
                '1周': 7,
                '1月': 30,
                '3月': 90,
                '6月': 180,
                '1年': 252,
                '2年': 504,
                '3年': 756
            }

            for period_name, days in periods.items():
                if len(history_data) > days:
                    past_nav = history_data[nav_col].iloc[-(days+1)]
                    period_return = (current_nav / past_nav - 1) * 100
                    period_returns[period_name] = round(period_return, 2)

        except Exception as e:
            log_debug(f"期间收益率计算失败: {e}")

        return period_returns

    def _analyze_return_distribution(self, returns: pd.Series) -> Dict:
        """分析收益率分布"""
        try:
            return {
                'mean': round(returns.mean() * 100, 3),
                'median': round(returns.median() * 100, 3),
                'std': round(returns.std() * 100, 3),
                'skewness': round(returns.skew(), 3),
                'kurtosis': round(returns.kurtosis(), 3),
                'min': round(returns.min() * 100, 3),
                'max': round(returns.max() * 100, 3),
                'percentiles': {
                    '5%': round(returns.quantile(0.05) * 100, 3),
                    '25%': round(returns.quantile(0.25) * 100, 3),
                    '75%': round(returns.quantile(0.75) * 100, 3),
                    '95%': round(returns.quantile(0.95) * 100, 3)
                }
            }
        except Exception:
            return {}

    def _grade_performance(self, annual_return: float, volatility: float, sharpe_ratio: float) -> str:
        """评定业绩等级"""
        score = 0

        # 年化收益率评分 (0-40分)
        if annual_return >= 15:
            score += 40
        elif annual_return >= 10:
            score += 30
        elif annual_return >= 5:
            score += 20
        elif annual_return >= 0:
            score += 10

        # 波动率评分 (0-30分，波动率越低分数越高)
        if volatility <= 10:
            score += 30
        elif volatility <= 15:
            score += 25
        elif volatility <= 20:
            score += 20
        elif volatility <= 30:
            score += 15
        else:
            score += 5

        # 夏普比率评分 (0-30分)
        if sharpe_ratio >= 2:
            score += 30
        elif sharpe_ratio >= 1.5:
            score += 25
        elif sharpe_ratio >= 1:
            score += 20
        elif sharpe_ratio >= 0.5:
            score += 15
        elif sharpe_ratio >= 0:
            score += 10

        # 评级
        if score >= 85:
            return "A+"
        elif score >= 75:
            return "A"
        elif score >= 65:
            return "B+"
        elif score >= 55:
            return "B"
        elif score >= 45:
            return "C+"
        elif score >= 35:
            return "C"
        else:
            return "D"

    def _analyze_risk(self, history_data: pd.DataFrame, fund_data: Dict) -> Dict:
        """分析风险指标"""
        if history_data.empty:
            return {}

        try:
            if 'nav' in history_data.columns:
                returns = history_data['nav'].pct_change().dropna()
            elif 'close' in history_data.columns:
                returns = history_data['close'].pct_change().dropna()
            else:
                return {}

            # Beta值计算（需要基准指数数据，这里简化处理）
            beta = self._calculate_beta(returns)

            # Alpha值
            annual_return = returns.mean() * 252 * 100
            expected_return = self.risk_free_rate * 100 + beta * (self.market_return * 100 - self.risk_free_rate * 100)
            alpha = annual_return - expected_return

            # VaR计算
            var_95 = returns.quantile(0.05) * 100
            var_99 = returns.quantile(0.01) * 100

            # CVaR计算
            cvar_95 = returns[returns <= returns.quantile(0.05)].mean() * 100
            cvar_99 = returns[returns <= returns.quantile(0.01)].mean() * 100

            # 跟踪误差（简化处理）
            tracking_error = returns.std() * np.sqrt(252) * 100

            # 信息比率
            information_ratio = alpha / tracking_error if tracking_error > 0 else 0

            # 风险等级评估
            risk_level = self._assess_risk_level(returns.std() * np.sqrt(252), fund_data.get('type', ''))

            return {
                'beta': round(beta, 3),
                'alpha': round(alpha, 2),
                'tracking_error': round(tracking_error, 2),
                'information_ratio': round(information_ratio, 3),
                'var_95': round(var_95, 3),
                'var_99': round(var_99, 3),
                'cvar_95': round(cvar_95, 3),
                'cvar_99': round(cvar_99, 3),
                'risk_level': risk_level,
                'risk_grade': self._grade_risk(returns.std() * np.sqrt(252), var_95)
            }

        except Exception as e:
            log_debug(f"风险分析失败: {e}")
            return {}

    def _calculate_beta(self, returns: pd.Series) -> float:
        """计算Beta值（简化处理，假设市场收益）"""
        try:
            # 这里应该使用相应的基准指数数据，简化处理使用固定值
            market_returns = np.random.normal(self.market_return/252, 0.02, len(returns))

            if len(returns) > 1:
                correlation = np.corrcoef(returns, market_returns)[0, 1]
                return_vol = returns.std()
                market_vol = np.std(market_returns)
                beta = correlation * (return_vol / market_vol) if market_vol > 0 else 1.0
                return max(0, min(3, beta))  # 限制Beta在合理范围内

        except Exception:
            pass

        return 1.0  # 默认值

    def _assess_risk_level(self, volatility: float, fund_type: str) -> str:
        """评估风险等级"""
        # 根据基金类型和波动率判断风险等级
        if fund_type == '货币市场基金':
            return '低风险'
        elif fund_type == '债券型基金':
            if volatility < 0.05:
                return '低风险'
            elif volatility < 0.1:
                return '中低风险'
            else:
                return '中等风险'
        elif fund_type == '混合型基金':
            if volatility < 0.1:
                return '中低风险'
            elif volatility < 0.2:
                return '中等风险'
            else:
                return '中高风险'
        else:  # 股票型等
            if volatility < 0.15:
                return '中等风险'
            elif volatility < 0.25:
                return '中高风险'
            else:
                return '高风险'

    def _grade_risk(self, volatility: float, var_95: float) -> str:
        """风险等级评定"""
        risk_score = 0

        # 波动率评分（波动率越低分数越高）
        if volatility <= 0.1:
            risk_score += 50
        elif volatility <= 0.15:
            risk_score += 40
        elif volatility <= 0.2:
            risk_score += 30
        elif volatility <= 0.3:
            risk_score += 20
        else:
            risk_score += 10

        # VaR评分
        if var_95 >= -2:
            risk_score += 50
        elif var_95 >= -4:
            risk_score += 40
        elif var_95 >= -6:
            risk_score += 30
        elif var_95 >= -8:
            risk_score += 20
        else:
            risk_score += 10

        if risk_score >= 80:
            return "A"
        elif risk_score >= 60:
            return "B"
        elif risk_score >= 40:
            return "C"
        else:
            return "D"

    def _analyze_fees(self, fund_data: Dict) -> Dict:
        """分析费用结构"""
        try:
            # 这里需要从数据源获取费用信息，简化处理
            management_fee = fund_data.get('management_fee', 1.5)  # 管理费
            custodian_fee = fund_data.get('custodian_fee', 0.25)   # 托管费
            sales_fee = fund_data.get('sales_fee', 1.2)            # 销售服务费

            # 综合费用率
            total_fee_rate = management_fee + custodian_fee + sales_fee

            # 费用等级评估
            if total_fee_rate <= 1.0:
                fee_grade = "低"
            elif total_fee_rate <= 2.0:
                fee_grade = "中"
            else:
                fee_grade = "高"

            return {
                'management_fee': management_fee,
                'custodian_fee': custodian_fee,
                'sales_fee': sales_fee,
                'total_fee_rate': round(total_fee_rate, 2),
                'fee_grade': fee_grade,
                'fee_competitiveness': self._assess_fee_competitiveness(total_fee_rate, fund_data.get('type', ''))
            }

        except Exception as e:
            log_debug(f"费用分析失败: {e}")
            return {}

    def _assess_fee_competitiveness(self, total_fee: float, fund_type: str) -> str:
        """评估费用竞争力"""
        # 不同类型基金的费用基准不同
        if fund_type == '货币市场基金':
            if total_fee <= 0.3:
                return "优秀"
            elif total_fee <= 0.5:
                return "良好"
            else:
                return "一般"
        elif fund_type == '债券型基金':
            if total_fee <= 0.8:
                return "优秀"
            elif total_fee <= 1.2:
                return "良好"
            else:
                return "一般"
        else:  # 股票型、混合型
            if total_fee <= 1.5:
                return "优秀"
            elif total_fee <= 2.0:
                return "良好"
            else:
                return "一般"

    def _analyze_fund_size(self, fund_data: Dict) -> Dict:
        """分析基金规模"""
        try:
            fund_size = fund_data.get('fund_size', 0)  # 单位：亿元

            # 规模等级
            if fund_size >= 100:
                size_grade = "超大型"
            elif fund_size >= 50:
                size_grade = "大型"
            elif fund_size >= 10:
                size_grade = "中型"
            elif fund_size >= 2:
                size_grade = "小型"
            else:
                size_grade = "迷你型"

            # 规模风险评估
            if fund_size < 0.5:
                size_risk = "清盘风险"
            elif fund_size < 2:
                size_risk = "流动性风险"
            elif fund_size > 500:
                size_risk = "船大难掉头"
            else:
                size_risk = "正常"

            return {
                'fund_size': fund_size,
                'size_grade': size_grade,
                'size_risk': size_risk,
                'optimal_size': self._assess_optimal_size(fund_data.get('type', ''))
            }

        except Exception as e:
            log_debug(f"规模分析失败: {e}")
            return {}

    def _assess_optimal_size(self, fund_type: str) -> str:
        """评估最优规模"""
        if fund_type == '货币市场基金':
            return "规模越大越好，降低成本"
        elif fund_type == '债券型基金':
            return "中大型较好，10-100亿"
        elif fund_type == '指数型基金':
            return "大型较好，便于跟踪指数"
        else:  # 主动管理型
            return "中型较好，5-50亿元"

    def _analyze_fund_manager(self, fund_data: Dict) -> Dict:
        """分析基金经理"""
        try:
            managers = fund_data.get('managers', [])

            if not managers:
                return {}

            # 分析主要基金经理
            main_manager = managers[0] if managers else {}

            manager_analysis = {
                'manager_count': len(managers),
                'main_manager': main_manager.get('name', ''),
                'tenure_years': self._calculate_tenure_years(main_manager.get('start_date', '')),
                'tenure_return': main_manager.get('tenure_return', 0),
                'experience_grade': self._grade_manager_experience(main_manager),
                'management_style': self._analyze_management_style(main_manager, fund_data)
            }

            return manager_analysis

        except Exception as e:
            log_debug(f"基金经理分析失败: {e}")
            return {}

    def _calculate_tenure_years(self, start_date: str) -> float:
        """计算任职年限"""
        try:
            if not start_date:
                return 0

            start = pd.to_datetime(start_date)
            years = (datetime.now() - start).days / 365.25
            return round(years, 2)

        except Exception:
            return 0

    def _grade_manager_experience(self, manager: Dict) -> str:
        """评级基金经理经验"""
        tenure_years = self._calculate_tenure_years(manager.get('start_date', ''))
        tenure_return = manager.get('tenure_return', 0)

        experience_score = 0

        # 任职年限评分
        if tenure_years >= 5:
            experience_score += 50
        elif tenure_years >= 3:
            experience_score += 40
        elif tenure_years >= 1:
            experience_score += 30
        else:
            experience_score += 10

        # 任职回报评分
        if tenure_return >= 100:
            experience_score += 50
        elif tenure_return >= 50:
            experience_score += 40
        elif tenure_return >= 20:
            experience_score += 30
        elif tenure_return >= 0:
            experience_score += 20
        else:
            experience_score += 10

        if experience_score >= 80:
            return "A"
        elif experience_score >= 60:
            return "B"
        else:
            return "C"

    def _analyze_management_style(self, manager: Dict, fund_data: Dict) -> str:
        """分析管理风格"""
        # 简化处理，根据基金类型和经理信息推断
        fund_type = fund_data.get('type', '')

        if '指数' in fund_data.get('name', ''):
            return "被动管理"
        elif fund_type == '股票型基金':
            return "主动成长型"
        elif fund_type == '债券型基金':
            return "稳健收益型"
        else:
            return "均衡配置型"

    def _analyze_holdings(self, fund_data: Dict) -> Dict:
        """分析持仓结构"""
        try:
            holdings_data = fund_data.get('top_stock_holdings', [])

            if not holdings_data:
                return {}

            # 计算持仓集中度
            top5_ratio = sum(h.get('hold_ratio', 0) for h in holdings_data[:5])
            top10_ratio = sum(h.get('hold_ratio', 0) for h in holdings_data[:10])

            # 行业分析（简化处理）
            industry_concentration = self._analyze_industry_concentration(holdings_data)

            return {
                'top5_holdings_ratio': round(top5_ratio, 2),
                'top10_holdings_ratio': round(top10_ratio, 2),
                'holdings_count': len(holdings_data),
                'concentration_level': self._assess_concentration_level(top10_ratio),
                'industry_concentration': industry_concentration,
                'diversification_grade': self._grade_diversification(top10_ratio, len(holdings_data))
            }

        except Exception as e:
            log_debug(f"持仓分析失败: {e}")
            return {}

    def _analyze_industry_concentration(self, holdings: List[Dict]) -> Dict:
        """分析行业集中度"""
        # 简化处理，实际需要获取股票的行业信息
        return {
            'industry_count': len(set(h.get('stock_name', '')[:2] for h in holdings)),  # 简化处理
            'concentration_risk': '中等'  # 简化处理
        }

    def _assess_concentration_level(self, top10_ratio: float) -> str:
        """评估集中度水平"""
        if top10_ratio >= 80:
            return "高度集中"
        elif top10_ratio >= 60:
            return "中度集中"
        elif top10_ratio >= 40:
            return "适度集中"
        else:
            return "高度分散"

    def _grade_diversification(self, top10_ratio: float, holdings_count: int) -> str:
        """评级分散化程度"""
        diversification_score = 0

        # 集中度评分（集中度越低分数越高）
        if top10_ratio <= 30:
            diversification_score += 50
        elif top10_ratio <= 50:
            diversification_score += 40
        elif top10_ratio <= 70:
            diversification_score += 30
        else:
            diversification_score += 20

        # 持仓数量评分
        if holdings_count >= 100:
            diversification_score += 50
        elif holdings_count >= 50:
            diversification_score += 40
        elif holdings_count >= 20:
            diversification_score += 30
        else:
            diversification_score += 20

        if diversification_score >= 80:
            return "A"
        elif diversification_score >= 60:
            return "B"
        else:
            return "C"

    def _compare_with_peers(self, fund_code: str, fund_data: Dict) -> Dict:
        """同类基金比较"""
        try:
            # 这里应该获取同类基金数据进行比较，简化处理
            fund_type = fund_data.get('type', '')

            return {
                'peer_group': fund_type,
                'performance_ranking': "前25%",  # 简化处理
                'risk_ranking': "中等",       # 简化处理
                'fee_ranking': "中等",        # 简化处理
                'size_ranking': "中等",       # 简化处理
                'overall_ranking': "良好"      # 简化处理
            }

        except Exception as e:
            log_debug(f"同类比较失败: {e}")
            return {}

    def _analyze_investment_style(self, fund_data: Dict, history_data: pd.DataFrame) -> Dict:
        """分析投资风格"""
        try:
            fund_type = fund_data.get('type', '')
            fund_name = fund_data.get('name', '')

            # 风格分析
            style_analysis = {
                'investment_style': self._determine_investment_style(fund_name, fund_type),
                'risk_preference': self._determine_risk_preference(fund_type),
                'sector_preference': self._analyze_sector_preference(fund_data),
                'geographic_focus': self._analyze_geographic_focus(fund_name),
                'investment_approach': 'ACTIVE' if '指数' not in fund_name else 'PASSIVE'
            }

            return style_analysis

        except Exception as e:
            log_debug(f"投资风格分析失败: {e}")
            return {}

    def _determine_investment_style(self, fund_name: str, fund_type: str) -> str:
        """确定投资风格"""
        if '价值' in fund_name:
            return "价值投资"
        elif '成长' in fund_name:
            return "成长投资"
        elif '消费' in fund_name:
            return "主题投资"
        elif '指数' in fund_name:
            return "指数投资"
        elif fund_type == '债券型基金':
            return "固定收益"
        else:
            return "均衡投资"

    def _determine_risk_preference(self, fund_type: str) -> str:
        """确定风险偏好"""
        risk_map = {
            '货币市场基金': '保守型',
            '债券型基金': '稳健型',
            '混合型基金': '平衡型',
            '股票型基金': '积极型'
        }
        return risk_map.get(fund_type, '平衡型')

    def _analyze_sector_preference(self, fund_data: Dict) -> str:
        """分析行业偏好"""
        fund_name = fund_data.get('name', '')

        sector_keywords = {
            '科技': '科技',
            '医疗': '医疗健康',
            '消费': '消费',
            '金融': '金融',
            '地产': '房地产',
            '新能源': '新能源',
            '军工': '军工',
            '环保': '环保'
        }

        for keyword, sector in sector_keywords.items():
            if keyword in fund_name:
                return sector

        return '均衡配置'

    def _analyze_geographic_focus(self, fund_name: str) -> str:
        """分析地域焦点"""
        if 'A股' in fund_name or '沪深' in fund_name:
            return '中国A股'
        elif '港股' in fund_name:
            return '香港股市'
        elif '美股' in fund_name:
            return '美国股市'
        elif 'QDII' in fund_name:
            return '海外市场'
        else:
            return '境内市场'

    def _analyze_market_adaptation(self, history_data: pd.DataFrame) -> Dict:
        """分析市场环境适应性"""
        try:
            if history_data.empty:
                return {}

            if 'nav' in history_data.columns:
                returns = history_data['nav'].pct_change().dropna()
            else:
                returns = history_data['close'].pct_change().dropna()

            # 分析不同市场环境下的表现
            bull_market_performance = self._analyze_bull_market_performance(returns)
            bear_market_performance = self._analyze_bear_market_performance(returns)
            sideways_market_performance = self._analyze_sideways_market_performance(returns)

            return {
                'bull_market_adaptation': bull_market_performance,
                'bear_market_adaptation': bear_market_performance,
                'sideways_market_adaptation': sideways_market_performance,
                'overall_adaptability': self._assess_overall_adaptability(
                    bull_market_performance, bear_market_performance, sideways_market_performance
                )
            }

        except Exception as e:
            log_debug(f"市场适应性分析失败: {e}")
            return {}

    def _analyze_bull_market_performance(self, returns: pd.Series) -> str:
        """分析牛市表现"""
        bull_returns = returns[returns > 0.02]  # 大涨日
        if len(bull_returns) > 0:
            avg_bull_return = bull_returns.mean()
            if avg_bull_return > 0.05:
                return "优秀"
            elif avg_bull_return > 0.03:
                return "良好"
            else:
                return "一般"
        return "数据不足"

    def _analyze_bear_market_performance(self, returns: pd.Series) -> str:
        """分析熊市表现"""
        bear_returns = returns[returns < -0.02]  # 大跌日
        if len(bear_returns) > 0:
            avg_bear_return = bear_returns.mean()
            if avg_bear_return > -0.03:
                return "优秀"
            elif avg_bear_return > -0.05:
                return "良好"
            else:
                return "一般"
        return "数据不足"

    def _analyze_sideways_market_performance(self, returns: pd.Series) -> str:
        """分析震荡市表现"""
        sideways_returns = returns[(returns >= -0.02) & (returns <= 0.02)]
        if len(sideways_returns) > 0:
            volatility = sideways_returns.std()
            if volatility < 0.01:
                return "优秀"
            elif volatility < 0.015:
                return "良好"
            else:
                return "一般"
        return "数据不足"

    def _assess_overall_adaptability(self, bull: str, bear: str, sideways: str) -> str:
        """评估整体适应性"""
        scores = {'优秀': 3, '良好': 2, '一般': 1, '数据不足': 0}
        total_score = scores.get(bull, 0) + scores.get(bear, 0) + scores.get(sideways, 0)

        if total_score >= 8:
            return "强"
        elif total_score >= 5:
            return "中等"
        else:
            return "弱"

    def _calculate_fundamental_score(self, analysis_results: Dict) -> float:
        """计算基本面综合评分"""
        try:
            score = 0

            # 业绩评分 (40%)
            performance = analysis_results.get('performance', {})
            annual_return = performance.get('annual_return', 0)
            sharpe_ratio = performance.get('sharpe_ratio', 0)
            max_drawdown = performance.get('max_drawdown', 0)

            perf_score = 0
            if annual_return > 15:
                perf_score += 15
            elif annual_return > 8:
                perf_score += 12
            elif annual_return > 0:
                perf_score += 8

            if sharpe_ratio > 1.5:
                perf_score += 15
            elif sharpe_ratio > 1:
                perf_score += 12
            elif sharpe_ratio > 0.5:
                perf_score += 8

            if max_drawdown > -10:
                perf_score += 10
            elif max_drawdown > -20:
                perf_score += 8
            elif max_drawdown > -30:
                perf_score += 5

            score += perf_score * 0.4

            # 风险评分 (25%)
            risk = analysis_results.get('risk', {})
            risk_grade = risk.get('risk_grade', 'D')
            risk_score_map = {'A': 25, 'B': 20, 'C': 15, 'D': 10}
            score += risk_score_map.get(risk_grade, 10) * 0.25

            # 费用评分 (15%)
            fees = analysis_results.get('fees', {})
            fee_grade = fees.get('fee_competitiveness', '一般')
            fee_score_map = {'优秀': 15, '良好': 12, '一般': 8}
            score += fee_score_map.get(fee_grade, 8) * 0.15

            # 规模评分 (10%)
            size = analysis_results.get('size', {})
            size_grade = size.get('size_grade', '小型')
            size_score_map = {'大型': 10, '中型': 8, '小型': 6, '迷你型': 3}
            score += size_score_map.get(size_grade, 6) * 0.1

            # 经理评分 (10%)
            manager = analysis_results.get('manager', {})
            manager_grade = manager.get('experience_grade', 'C')
            manager_score_map = {'A': 10, 'B': 8, 'C': 6}
            score += manager_score_map.get(manager_grade, 6) * 0.1

            return round(score, 2)

        except Exception as e:
            log_debug(f"基本面评分计算失败: {e}")
            return 50.0  # 默认中等评分

    def _get_recommendation(self, fundamental_score: float) -> Dict:
        """生成投资建议"""
        if fundamental_score >= 80:
            return {
                'action': 'STRONG_BUY',
                'confidence': 0.9,
                'reason': '基本面表现优秀，建议重点配置'
            }
        elif fundamental_score >= 70:
            return {
                'action': 'BUY',
                'confidence': 0.75,
                'reason': '基本面表现良好，建议适度配置'
            }
        elif fundamental_score >= 60:
            return {
                'action': 'HOLD',
                'confidence': 0.6,
                'reason': '基本面表现一般，建议观望'
            }
        elif fundamental_score >= 50:
            return {
                'action': 'WEAK_SELL',
                'confidence': 0.7,
                'reason': '基本面表现较差，建议减仓'
            }
        else:
            return {
                'action': 'SELL',
                'confidence': 0.8,
                'reason': '基本面表现很差，建议清仓'
            }

    def _identify_strengths(self, fund_data: Dict, performance: Dict, risk: Dict) -> List[str]:
        """识别优势"""
        strengths = []

        # 检查各项指标的优势
        if performance.get('sharpe_ratio', 0) > 1.5:
            strengths.append("夏普比率优秀，风险调整后收益突出")

        if performance.get('annual_return', 0) > 15:
            strengths.append("年化收益率表现优异")

        if performance.get('max_drawdown', 0) > -10:
            strengths.append("最大回撤控制良好，下行风险较小")

        if risk.get('risk_grade') == 'A':
            strengths.append("风险控制能力强")

        fund_size = fund_data.get('fund_size', 0)
        if 10 <= fund_size <= 100:
            strengths.append("基金规模适中，便于灵活操作")

        return strengths

    def _identify_weaknesses(self, fund_data: Dict, performance: Dict, risk: Dict) -> List[str]:
        """识别劣势"""
        weaknesses = []

        if performance.get('annual_return', 0) < 0:
            weaknesses.append("年化收益率为负，表现较差")

        if performance.get('max_drawdown', 0) < -30:
            weaknesses.append("最大回撤过大，下行风险较高")

        if performance.get('sharpe_ratio', 0) < 0:
            weaknesses.append("夏普比率为负，风险调整后收益较差")

        if risk.get('risk_grade') == 'D':
            weaknesses.append("风险控制能力较弱")

        fund_size = fund_data.get('fund_size', 0)
        if fund_size < 2:
            weaknesses.append("基金规模较小，存在清盘风险")
        elif fund_size > 500:
            weaknesses.append("基金规模过大，可能影响操作灵活性")

        return weaknesses

    def _generate_investment_advice(self, fundamental_score: float, risk_metrics: Dict) -> str:
        """生成投资建议"""
        advice = []

        if fundamental_score >= 80:
            advice.append("该基金基本面表现优秀，建议作为核心持仓。")
        elif fundamental_score >= 70:
            advice.append("该基金基本面表现良好，可以考虑适度配置。")
        elif fundamental_score >= 60:
            advice.append("该基金基本面表现一般，建议观望或小仓位尝试。")
        else:
            advice.append("该基金基本面表现较差，不建议投资。")

        # 根据风险等级给出建议
        risk_level = risk_metrics.get('risk_level', '中等风险')
        if '高风险' in risk_level:
            advice.append("该基金风险等级较高，适合风险承受能力强的投资者。")
        elif '低风险' in risk_level:
            advice.append("该基金风险等级较低，适合稳健型投资者。")

        # 投资期限建议
        if fundamental_score >= 70:
            advice.append("建议长期持有（1年以上），以获得更好的复合收益。")
        else:
            advice.append("如果投资，建议密切关注市场变化，适时调整。")

        return " ".join(advice)

# 创建默认实例
fundamental_analyzer = FundamentalAnalyzer()
