#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金分析器模块
包含技术分析、买卖点判断、风险评估等功能
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import talib
import logging
from typing import Dict, List, Tuple, Any
import json
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class FundAnalyzer:
    """基金分析器类"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def analyze_single_fund(self, fund_data: Dict) -> Dict:
        """分析单个基金"""
        try:
            fund_code = fund_data['fund_code']
            nav_data = pd.DataFrame(fund_data['nav_data'])
            
            if nav_data.empty:
                return None
                
            # 技术分析
            technical_analysis = self.perform_technical_analysis(nav_data)
            
            # 风险评估
            risk_assessment = self.assess_risk(nav_data)
            
            # 买卖点判断
            trading_signals = self.generate_trading_signals(nav_data, technical_analysis)
            
            # 综合评分
            overall_score = self.calculate_overall_score(technical_analysis, risk_assessment, trading_signals)
            
            analysis_result = {
                'fund_code': fund_code,
                'fund_info': fund_data['fund_info'],
                'technical_analysis': technical_analysis,
                'risk_assessment': risk_assessment,
                'trading_signals': trading_signals,
                'overall_score': overall_score,
                'analysis_time': datetime.now().isoformat()
            }
            
            self.logger.info(f"基金 {fund_code} 分析完成")
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"分析基金 {fund_data.get('fund_code', 'unknown')} 失败: {e}")
            return None
    
    def perform_technical_analysis(self, nav_data: pd.DataFrame) -> Dict:
        """执行技术分析"""
        try:
            # 确保数据格式正确
            nav_data['净值日期'] = pd.to_datetime(nav_data['净值日期'])
            nav_data['累计净值'] = pd.to_numeric(nav_data['累计净值'], errors='coerce')
            nav_data = nav_data.sort_values('净值日期').dropna()
            
            if len(nav_data) < 30:
                return {}
            
            # 计算技术指标
            close_prices = nav_data['累计净值'].values
            
            # 移动平均线
            ma5 = talib.SMA(close_prices, timeperiod=5)
            ma10 = talib.SMA(close_prices, timeperiod=10)
            ma20 = talib.SMA(close_prices, timeperiod=20)
            ma60 = talib.SMA(close_prices, timeperiod=60)
            
            # MACD
            macd, macd_signal, macd_hist = talib.MACD(close_prices)
            
            # RSI
            rsi = talib.RSI(close_prices, timeperiod=14)
            
            # KDJ
            k, d = talib.STOCH(close_prices, close_prices, close_prices)
            j = 3 * k - 2 * d
            
            # 布林带
            upper, middle, lower = talib.BBANDS(close_prices)
            
            # 计算趋势强度
            trend_strength = self.calculate_trend_strength(close_prices)
            
            # 计算波动率
            volatility = self.calculate_volatility(close_prices)
            
            # 计算动量指标
            momentum = self.calculate_momentum(close_prices)
            
            technical_analysis = {
                'moving_averages': {
                    'ma5': ma5[-1] if not np.isnan(ma5[-1]) else 0,
                    'ma10': ma10[-1] if not np.isnan(ma10[-1]) else 0,
                    'ma20': ma20[-1] if not np.isnan(ma20[-1]) else 0,
                    'ma60': ma60[-1] if not np.isnan(ma60[-1]) else 0,
                    'ma_trend': 'bullish' if ma5[-1] > ma20[-1] else 'bearish'
                },
                'macd': {
                    'macd': macd[-1] if not np.isnan(macd[-1]) else 0,
                    'signal': macd_signal[-1] if not np.isnan(macd_signal[-1]) else 0,
                    'histogram': macd_hist[-1] if not np.isnan(macd_hist[-1]) else 0,
                    'signal': 'buy' if macd[-1] > macd_signal[-1] else 'sell'
                },
                'rsi': {
                    'value': rsi[-1] if not np.isnan(rsi[-1]) else 50,
                    'signal': 'oversold' if rsi[-1] < 30 else 'overbought' if rsi[-1] > 70 else 'neutral'
                },
                'kdj': {
                    'k': k[-1] if not np.isnan(k[-1]) else 50,
                    'd': d[-1] if not np.isnan(d[-1]) else 50,
                    'j': j[-1] if not np.isnan(j[-1]) else 50,
                    'signal': 'buy' if k[-1] < 20 and d[-1] < 20 else 'sell' if k[-1] > 80 and d[-1] > 80 else 'neutral'
                },
                'bollinger_bands': {
                    'upper': upper[-1] if not np.isnan(upper[-1]) else 0,
                    'middle': middle[-1] if not np.isnan(middle[-1]) else 0,
                    'lower': lower[-1] if not np.isnan(lower[-1]) else 0,
                    'position': 'upper' if close_prices[-1] > upper[-1] else 'lower' if close_prices[-1] < lower[-1] else 'middle'
                },
                'trend_strength': trend_strength,
                'volatility': volatility,
                'momentum': momentum
            }
            
            return technical_analysis
            
        except Exception as e:
            self.logger.error(f"技术分析失败: {e}")
            return {}
    
    def calculate_trend_strength(self, prices: np.ndarray) -> float:
        """计算趋势强度"""
        try:
            if len(prices) < 20:
                return 0
            
            # 计算线性回归斜率
            x = np.arange(len(prices))
            slope, _ = np.polyfit(x, prices, 1)
            
            # 计算R²
            y_pred = slope * x + _
            r_squared = 1 - np.sum((prices - y_pred) ** 2) / np.sum((prices - np.mean(prices)) ** 2)
            
            # 趋势强度 = 斜率 * R²
            trend_strength = abs(slope) * r_squared
            
            return float(trend_strength)
        except:
            return 0
    
    def calculate_volatility(self, prices: np.ndarray) -> float:
        """计算波动率"""
        try:
            returns = np.diff(prices) / prices[:-1]
            volatility = np.std(returns) * np.sqrt(252)  # 年化波动率
            return float(volatility)
        except:
            return 0
    
    def calculate_momentum(self, prices: np.ndarray) -> float:
        """计算动量指标"""
        try:
            if len(prices) < 20:
                return 0
            
            # 计算20日动量
            momentum = (prices[-1] / prices[-20] - 1) * 100
            return float(momentum)
        except:
            return 0
    
    def assess_risk(self, nav_data: pd.DataFrame) -> Dict:
        """风险评估"""
        try:
            nav_data['累计净值'] = pd.to_numeric(nav_data['累计净值'], errors='coerce')
            nav_data = nav_data.dropna()
            
            if len(nav_data) < 30:
                return {'risk_level': 'unknown', 'risk_score': 0}
            
            prices = nav_data['累计净值'].values
            
            # 计算最大回撤
            max_drawdown = self.calculate_max_drawdown(prices)
            
            # 计算夏普比率
            sharpe_ratio = self.calculate_sharpe_ratio(prices)
            
            # 计算VaR
            var_95 = self.calculate_var(prices, 0.95)
            
            # 计算风险评分
            risk_score = self.calculate_risk_score(max_drawdown, sharpe_ratio, var_95)
            
            # 确定风险等级
            if risk_score < 0.3:
                risk_level = '低风险'
            elif risk_score < 0.7:
                risk_level = '中风险'
            else:
                risk_level = '高风险'
            
            return {
                'risk_level': risk_level,
                'risk_score': risk_score,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'var_95': var_95
            }
            
        except Exception as e:
            self.logger.error(f"风险评估失败: {e}")
            return {'risk_level': 'unknown', 'risk_score': 0}
    
    def calculate_max_drawdown(self, prices: np.ndarray) -> float:
        """计算最大回撤"""
        try:
            peak = prices[0]
            max_dd = 0
            
            for price in prices:
                if price > peak:
                    peak = price
                dd = (peak - price) / peak
                if dd > max_dd:
                    max_dd = dd
            
            return float(max_dd)
        except:
            return 0
    
    def calculate_sharpe_ratio(self, prices: np.ndarray) -> float:
        """计算夏普比率"""
        try:
            returns = np.diff(prices) / prices[:-1]
            excess_return = np.mean(returns) - 0.03 / 252  # 假设无风险利率3%
            volatility = np.std(returns)
            
            if volatility == 0:
                return 0
            
            sharpe = excess_return / volatility * np.sqrt(252)
            return float(sharpe)
        except:
            return 0
    
    def calculate_var(self, prices: np.ndarray, confidence: float) -> float:
        """计算VaR"""
        try:
            returns = np.diff(prices) / prices[:-1]
            var = np.percentile(returns, (1 - confidence) * 100)
            return float(var)
        except:
            return 0
    
    def calculate_risk_score(self, max_dd: float, sharpe: float, var: float) -> float:
        """计算风险评分"""
        try:
            # 归一化各项指标
            dd_score = min(max_dd * 2, 1)  # 最大回撤权重
            sharpe_score = max(0, min((2 - sharpe) / 4, 1))  # 夏普比率权重
            var_score = min(abs(var) * 10, 1)  # VaR权重
            
            # 综合评分
            risk_score = (dd_score * 0.4 + sharpe_score * 0.3 + var_score * 0.3)
            return float(risk_score)
        except:
            return 0.5
    
    def generate_trading_signals(self, nav_data: pd.DataFrame, technical_analysis: Dict) -> Dict:
        """生成买卖信号"""
        try:
            signals = {
                'current_signal': 'hold',
                'signal_strength': 0,
                'buy_reasons': [],
                'sell_reasons': [],
                'target_price': 0,
                'stop_loss': 0
            }
            
            if not technical_analysis:
                return signals
            
            current_price = nav_data['累计净值'].iloc[-1]
            buy_reasons = []
            sell_reasons = []
            signal_score = 0
            
            # MA信号
            ma_trend = technical_analysis.get('moving_averages', {}).get('ma_trend', 'neutral')
            if ma_trend == 'bullish':
                buy_reasons.append('均线呈多头排列')
                signal_score += 1
            elif ma_trend == 'bearish':
                sell_reasons.append('均线呈空头排列')
                signal_score -= 1
            
            # MACD信号
            macd_signal = technical_analysis.get('macd', {}).get('signal', 'neutral')
            if macd_signal == 'buy':
                buy_reasons.append('MACD金叉')
                signal_score += 1
            elif macd_signal == 'sell':
                sell_reasons.append('MACD死叉')
                signal_score -= 1
            
            # RSI信号
            rsi_signal = technical_analysis.get('rsi', {}).get('signal', 'neutral')
            if rsi_signal == 'oversold':
                buy_reasons.append('RSI超卖')
                signal_score += 1
            elif rsi_signal == 'overbought':
                sell_reasons.append('RSI超买')
                signal_score -= 1
            
            # KDJ信号
            kdj_signal = technical_analysis.get('kdj', {}).get('signal', 'neutral')
            if kdj_signal == 'buy':
                buy_reasons.append('KDJ金叉')
                signal_score += 1
            elif kdj_signal == 'sell':
                sell_reasons.append('KDJ死叉')
                signal_score -= 1
            
            # 布林带信号
            bb_position = technical_analysis.get('bollinger_bands', {}).get('position', 'middle')
            if bb_position == 'lower':
                buy_reasons.append('触及布林带下轨')
                signal_score += 0.5
            elif bb_position == 'upper':
                sell_reasons.append('触及布林带上轨')
                signal_score -= 0.5
            
            # 确定信号
            if signal_score >= 2:
                signals['current_signal'] = 'buy'
            elif signal_score <= -2:
                signals['current_signal'] = 'sell'
            else:
                signals['current_signal'] = 'hold'
            
            signals['signal_strength'] = abs(signal_score)
            signals['buy_reasons'] = buy_reasons
            signals['sell_reasons'] = sell_reasons
            
            # 计算目标价格和止损
            if signals['current_signal'] == 'buy':
                signals['target_price'] = current_price * 1.05  # 5%目标
                signals['stop_loss'] = current_price * 0.95    # 5%止损
            elif signals['current_signal'] == 'sell':
                signals['target_price'] = current_price * 0.95  # 5%目标
                signals['stop_loss'] = current_price * 1.05     # 5%止损
            
            return signals
            
        except Exception as e:
            self.logger.error(f"生成交易信号失败: {e}")
            return {'current_signal': 'hold', 'signal_strength': 0, 'buy_reasons': [], 'sell_reasons': []}
    
    def calculate_overall_score(self, technical_analysis: Dict, risk_assessment: Dict, trading_signals: Dict) -> float:
        """计算综合评分"""
        try:
            score = 0
            
            # 技术分析评分 (40%)
            if technical_analysis:
                # 趋势强度
                trend_strength = technical_analysis.get('trend_strength', 0)
                score += min(trend_strength * 10, 20)
                
                # 动量
                momentum = technical_analysis.get('momentum', 0)
                score += max(min(momentum / 2, 10), -10)
                
                # 技术指标一致性
                signal_count = 0
                if technical_analysis.get('macd', {}).get('signal') == 'buy':
                    signal_count += 1
                if technical_analysis.get('rsi', {}).get('signal') == 'oversold':
                    signal_count += 1
                if technical_analysis.get('kdj', {}).get('signal') == 'buy':
                    signal_count += 1
                
                score += signal_count * 3
            
            # 风险评估评分 (30%)
            risk_score = risk_assessment.get('risk_score', 0.5)
            score += (1 - risk_score) * 30
            
            # 交易信号评分 (30%)
            signal_strength = trading_signals.get('signal_strength', 0)
            if trading_signals.get('current_signal') == 'buy':
                score += signal_strength * 10
            elif trading_signals.get('current_signal') == 'sell':
                score -= signal_strength * 10
            
            return max(0, min(100, score))
            
        except Exception as e:
            self.logger.error(f"计算综合评分失败: {e}")
            return 50
    
    def generate_technical_report(self, analysis_results: List[Dict]) -> Dict:
        """生成技术分析报告"""
        try:
            if not analysis_results:
                return {}
            
            # 统计信号分布
            buy_count = 0
            sell_count = 0
            hold_count = 0
            
            for result in analysis_results:
                signal = result.get('trading_signals', {}).get('current_signal', 'hold')
                if signal == 'buy':
                    buy_count += 1
                elif signal == 'sell':
                    sell_count += 1
                else:
                    hold_count += 1
            
            total_funds = len(analysis_results)
            
            # 计算平均评分
            scores = [result.get('overall_score', 50) for result in analysis_results]
            avg_score = np.mean(scores) if scores else 50
            
            # 风险分布
            risk_levels = {}
            for result in analysis_results:
                risk_level = result.get('risk_assessment', {}).get('risk_level', 'unknown')
                risk_levels[risk_level] = risk_levels.get(risk_level, 0) + 1
            
            report = {
                'summary': {
                    'total_funds': total_funds,
                    'buy_signals': buy_count,
                    'sell_signals': sell_count,
                    'hold_signals': hold_count,
                    'buy_ratio': buy_count / total_funds if total_funds > 0 else 0,
                    'sell_ratio': sell_count / total_funds if total_funds > 0 else 0,
                    'avg_score': avg_score
                },
                'risk_distribution': risk_levels,
                'market_sentiment': self.analyze_market_sentiment(analysis_results),
                'top_funds': self.get_top_funds(analysis_results),
                'generation_time': datetime.now().isoformat()
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"生成技术报告失败: {e}")
            return {}
    
    def analyze_market_sentiment(self, analysis_results: List[Dict]) -> str:
        """分析市场情绪"""
        try:
            buy_ratio = sum(1 for r in analysis_results if r.get('trading_signals', {}).get('current_signal') == 'buy') / len(analysis_results)
            
            if buy_ratio > 0.6:
                return '乐观'
            elif buy_ratio < 0.4:
                return '悲观'
            else:
                return '中性'
        except:
            return '中性'
    
    def get_top_funds(self, analysis_results: List[Dict], top_n: int = 10) -> List[Dict]:
        """获取评分最高的基金"""
        try:
            sorted_results = sorted(analysis_results, key=lambda x: x.get('overall_score', 0), reverse=True)
            return sorted_results[:top_n]
        except:
            return []
    
    def generate_trading_signals(self, analysis_results: List[Dict]) -> Dict:
        """生成整体交易信号"""
        try:
            if not analysis_results:
                return {}
            
            # 统计信号
            signals = {'buy': [], 'sell': [], 'hold': []}
            
            for result in analysis_results:
                fund_code = result.get('fund_code', '')
                fund_name = result.get('fund_info', {}).get('fund_name', '')
                signal = result.get('trading_signals', {}).get('current_signal', 'hold')
                score = result.get('overall_score', 0)
                
                fund_info = {
                    'fund_code': fund_code,
                    'fund_name': fund_name,
                    'score': score,
                    'reasons': result.get('trading_signals', {}).get('buy_reasons' if signal == 'buy' else 'sell_reasons', [])
                }
                
                signals[signal].append(fund_info)
            
            # 按评分排序
            for signal_type in signals:
                signals[signal_type] = sorted(signals[signal_type], key=lambda x: x['score'], reverse=True)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"生成整体交易信号失败: {e}")
            return {}
    
    def generate_charts(self, analysis_results: List[Dict], output_dir: str):
        """生成分析图表"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # 1. 信号分布饼图
            self.plot_signal_distribution(analysis_results, output_dir)
            
            # 2. 评分分布直方图
            self.plot_score_distribution(analysis_results, output_dir)
            
            # 3. 风险分布图
            self.plot_risk_distribution(analysis_results, output_dir)
            
            # 4. 技术指标热力图
            self.plot_technical_heatmap(analysis_results, output_dir)
            
        except Exception as e:
            self.logger.error(f"生成图表失败: {e}")
    
    def plot_signal_distribution(self, analysis_results: List[Dict], output_dir: str):
        """绘制信号分布饼图"""
        try:
            buy_count = sum(1 for r in analysis_results if r.get('trading_signals', {}).get('current_signal') == 'buy')
            sell_count = sum(1 for r in analysis_results if r.get('trading_signals', {}).get('current_signal') == 'sell')
            hold_count = len(analysis_results) - buy_count - sell_count
            
            plt.figure(figsize=(10, 8))
            labels = ['买入信号', '卖出信号', '持有信号']
            sizes = [buy_count, sell_count, hold_count]
            colors = ['#ff9999', '#66b3ff', '#99ff99']
            
            plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            plt.title('基金交易信号分布', fontsize=16, fontweight='bold')
            plt.axis('equal')
            
            plt.savefig(f'{output_dir}/signal_distribution.png', dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            self.logger.error(f"绘制信号分布图失败: {e}")
    
    def plot_score_distribution(self, analysis_results: List[Dict], output_dir: str):
        """绘制评分分布直方图"""
        try:
            scores = [r.get('overall_score', 50) for r in analysis_results]
            
            plt.figure(figsize=(12, 8))
            plt.hist(scores, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
            plt.xlabel('综合评分')
            plt.ylabel('基金数量')
            plt.title('基金综合评分分布', fontsize=16, fontweight='bold')
            plt.grid(True, alpha=0.3)
            
            plt.savefig(f'{output_dir}/score_distribution.png', dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            self.logger.error(f"绘制评分分布图失败: {e}")
    
    def plot_risk_distribution(self, analysis_results: List[Dict], output_dir: str):
        """绘制风险分布图"""
        try:
            risk_levels = {}
            for result in analysis_results:
                risk_level = result.get('risk_assessment', {}).get('risk_level', '未知')
                risk_levels[risk_level] = risk_levels.get(risk_level, 0) + 1
            
            plt.figure(figsize=(10, 8))
            bars = plt.bar(risk_levels.keys(), risk_levels.values(), color=['green', 'orange', 'red', 'gray'])
            plt.xlabel('风险等级')
            plt.ylabel('基金数量')
            plt.title('基金风险等级分布', fontsize=16, fontweight='bold')
            
            # 添加数值标签
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{int(height)}', ha='center', va='bottom')
            
            plt.savefig(f'{output_dir}/risk_distribution.png', dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            self.logger.error(f"绘制风险分布图失败: {e}")
    
    def plot_technical_heatmap(self, analysis_results: List[Dict], output_dir: str):
        """绘制技术指标热力图"""
        try:
            # 提取技术指标数据
            data = []
            for result in analysis_results:
                tech = result.get('technical_analysis', {})
                row = [
                    tech.get('rsi', {}).get('value', 50),
                    tech.get('trend_strength', 0),
                    tech.get('volatility', 0),
                    tech.get('momentum', 0)
                ]
                data.append(row)
            
            if not data:
                return
            
            df = pd.DataFrame(data, columns=['RSI', '趋势强度', '波动率', '动量'])
            
            plt.figure(figsize=(12, 10))
            sns.heatmap(df.corr(), annot=True, cmap='coolwarm', center=0, 
                       square=True, linewidths=0.5)
            plt.title('技术指标相关性热力图', fontsize=16, fontweight='bold')
            
            plt.savefig(f'{output_dir}/technical_heatmap.png', dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            self.logger.error(f"绘制技术指标热力图失败: {e}")
