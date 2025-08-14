"""
报告生成器 - 生成专业的基金分析报告
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import matplotlib.font_manager as fm
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os
from pathlib import Path
from jinja2 import Template, Environment, FileSystemLoader
import markdown
import base64
from io import BytesIO

from ..utils.logger import log_info, log_warning, log_error, log_debug
from ..analyzer.signal_generator import SignalType

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class ReportGenerator:
    """报告生成器"""

    def __init__(self, output_dir="reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # 创建子目录
        (self.output_dir / "images").mkdir(exist_ok=True)
        (self.output_dir / "data").mkdir(exist_ok=True)
        (self.output_dir / "html").mkdir(exist_ok=True)

        # 设置样式
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")

        # 报告模板
        self.template_env = Environment(
            loader=FileSystemLoader('templates') if os.path.exists('templates') else None
        )

    def generate_comprehensive_report(self, analysis_results: Dict, signal: Dict) -> Dict:
        """生成综合分析报告"""
        try:
            fund_code = analysis_results.get('fund_code', '')
            report_time = datetime.now()

            log_info(f"开始生成基金 {fund_code} 的综合分析报告")

            # 生成各种图表
            charts = self._generate_all_charts(analysis_results)

            # 生成报告内容
            report_content = {
                'metadata': {
                    'fund_code': fund_code,
                    'fund_name': analysis_results.get('fundamental_analysis', {}).get('basic_info', {}).get('fund_name', ''),
                    'report_time': report_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'analysis_period': self._get_analysis_period(analysis_results),
                    'report_type': '基金投资分析报告'
                },
                'executive_summary': self._generate_executive_summary(analysis_results, signal),
                'investment_recommendation': self._generate_investment_recommendation(signal),
                'technical_analysis': self._format_technical_analysis(analysis_results.get('technical_analysis', {})),
                'fundamental_analysis': self._format_fundamental_analysis(analysis_results.get('fundamental_analysis', {})),
                'sentiment_analysis': self._format_sentiment_analysis(analysis_results.get('sentiment_analysis', {})),
                'risk_analysis': self._generate_risk_analysis(analysis_results),
                'performance_analysis': self._generate_performance_analysis(analysis_results),
                'market_comparison': self._generate_market_comparison(analysis_results),
                'charts': charts,
                'appendix': self._generate_appendix(analysis_results)
            }

            # 生成不同格式的报告
            report_files = {
                'markdown': self._generate_markdown_report(report_content),
                'html': self._generate_html_report(report_content),
                'json': self._save_json_report(report_content)
            }

            log_info(f"基金 {fund_code} 分析报告生成完成")

            return {
                'success': True,
                'report_content': report_content,
                'report_files': report_files,
                'charts': charts
            }

        except Exception as e:
            log_error(f"生成综合报告失败: {e}")
            return {'success': False, 'error': str(e)}

    def _generate_executive_summary(self, analysis_results: Dict, signal: Dict) -> str:
        """生成执行摘要"""
        fund_info = analysis_results.get('fundamental_analysis', {}).get('basic_info', {})
        fund_name = fund_info.get('fund_name', '')
        fund_code = analysis_results.get('fund_code', '')

        # 获取关键指标
        performance = analysis_results.get('fundamental_analysis', {}).get('performance_metrics', {})
        technical = analysis_results.get('technical_analysis', {})

        annual_return = performance.get('annual_return', 0)
        max_drawdown = performance.get('max_drawdown', 0)
        sharpe_ratio = performance.get('sharpe_ratio', 0)
        technical_score = technical.get('technical_score', 50)

        signal_type = signal.get('signal_type', SignalType.HOLD)
        confidence = signal.get('confidence', 0)

        summary = f"""
## 执行摘要

**基金名称**: {fund_name} ({fund_code})  
**分析时间**: {datetime.now().strftime('%Y年%m月%d日')}  
**投资建议**: {signal_type.value}  
**信号强度**: {confidence:.1%}  

### 核心观点

基于我们的多维度分析模型，{fund_name}在当前市场环境下表现如下：

**业绩表现**: 年化收益率 {annual_return:.2f}%，最大回撤 {max_drawdown:.2f}%，夏普比率 {sharpe_ratio:.2f}

**技术分析**: 技术得分 {technical_score:.1f}/100，技术面{'偏强' if technical_score > 60 else '偏弱' if technical_score < 40 else '中性'}

**投资建议**: {self._get_recommendation_reason(signal)}

### 风险提示

{self._generate_risk_warning(analysis_results)}
        """

        return summary.strip()

    def _generate_investment_recommendation(self, signal: Dict) -> Dict:
        """生成投资建议"""
        signal_type = signal.get('signal_type', SignalType.HOLD)
        confidence = signal.get('confidence', 0)
        reasoning = signal.get('reasoning', [])

        # 投资建议等级
        recommendation_level = self._get_recommendation_level(signal_type)

        # 建议仓位
        position_size = signal.get('position_size', '适中')

        # 预期持有期
        holding_period = signal.get('holding_period', 30)

        # 风险等级
        risk_level = signal.get('risk_level', '中等')

        return {
            'signal_type': signal_type.value,
            'recommendation_level': recommendation_level,
            'confidence': f"{confidence:.1%}",
            'position_size': position_size,
            'expected_holding_period': f"{holding_period}天",
            'risk_level': risk_level,
            'entry_price': signal.get('entry_price', 0),
            'target_price': signal.get('target_price'),
            'stop_loss': signal.get('stop_loss'),
            'reasoning': reasoning,
            'investment_strategy': self._generate_investment_strategy(signal),
            'timing_advice': self._generate_timing_advice(signal)
        }

    def _format_technical_analysis(self, technical_analysis: Dict) -> Dict:
        """格式化技术分析结果"""
        if not technical_analysis:
            return {}

        return {
            '技术得分': f"{technical_analysis.get('technical_score', 50):.1f}/100",
            '投资建议': technical_analysis.get('recommendation', '持有'),
            '移动平均': {
                '均线排列': technical_analysis.get('moving_averages', {}).get('ma_alignment', ''),
                '金叉死叉': '金叉' if technical_analysis.get('moving_averages', {}).get('golden_cross') else '死叉' if technical_analysis.get('moving_averages', {}).get('death_cross') else '无',
                'MA5偏离': f"{technical_analysis.get('moving_averages', {}).get('MA5_deviation', 0):.2f}%"
            },
            'MACD指标': {
                'MACD值': technical_analysis.get('macd', {}).get('macd', 0),
                '信号线': technical_analysis.get('macd', {}).get('signal', 0),
                '柱状图': technical_analysis.get('macd', {}).get('histogram', 0),
                '信号': technical_analysis.get('macd', {}).get('signal_cross', '无')
            },
            'RSI指标': {
                'RSI值': technical_analysis.get('rsi', {}).get('rsi', 50),
                'RSI信号': technical_analysis.get('rsi', {}).get('rsi_signal', '中性'),
                'RSI趋势': technical_analysis.get('rsi', {}).get('rsi_trend', 'flat')
            },
            '布林带': {
                '布林信号': technical_analysis.get('bollinger_bands', {}).get('bb_signal', ''),
                '布林位置': f"{technical_analysis.get('bollinger_bands', {}).get('bb_position', 0.5):.2%}",
                '布林宽度': f"{technical_analysis.get('bollinger_bands', {}).get('bb_width', 0):.4f}"
            },
            '风险指标': technical_analysis.get('risk_metrics', {}),
            '支撑阻力': technical_analysis.get('support_resistance', {}),
            '形态识别': technical_analysis.get('pattern_recognition', {})
        }

    def _format_fundamental_analysis(self, fundamental_analysis: Dict) -> Dict:
        """格式化基本面分析结果"""
        if not fundamental_analysis:
            return {}

        basic_info = fundamental_analysis.get('basic_info', {})
        performance = fundamental_analysis.get('performance_metrics', {})
        risk_metrics = fundamental_analysis.get('risk_metrics', {})

        return {
            '基本信息': {
                '基金类型': basic_info.get('fund_type', ''),
                '基金规模': f"{basic_info.get('fund_size', 0):.2f}亿元",
                '成立时间': basic_info.get('establishment_date', ''),
                '运作年限': f"{basic_info.get('operation_years', 0):.1f}年",
                '基金经理': basic_info.get('fund_manager', ''),
                '管理公司': basic_info.get('management_company', '')
            },
            '业绩指标': {
                '年化收益': f"{performance.get('annual_return', 0):.2f}%",
                '总收益': f"{performance.get('total_return', 0):.2f}%",
                '波动率': f"{performance.get('volatility', 0):.2f}%",
                '夏普比率': f"{performance.get('sharpe_ratio', 0):.3f}",
                '最大回撤': f"{performance.get('max_drawdown', 0):.2f}%",
                '卡玛比率': f"{performance.get('calmar_ratio', 0):.3f}",
                '索提诺比率': f"{performance.get('sortino_ratio', 0):.3f}",
                '胜率': f"{performance.get('win_rate', 0):.1f}%"
            },
            '风险分析': {
                'Beta系数': f"{risk_metrics.get('beta', 0):.3f}",
                'Alpha系数': f"{risk_metrics.get('alpha', 0):.3f}",
                'VaR(95%)': f"{risk_metrics.get('var_95', 0):.2f}%",
                '跟踪误差': f"{risk_metrics.get('tracking_error', 0):.2f}%",
                '信息比率': f"{risk_metrics.get('information_ratio', 0):.3f}"
            },
            '费用分析': fundamental_analysis.get('fee_analysis', {}),
            '经理分析': fundamental_analysis.get('manager_analysis', {}),
            '持仓分析': fundamental_analysis.get('holdings_analysis', {}),
            '同类比较': fundamental_analysis.get('peer_comparison', {})
        }

    def _format_sentiment_analysis(self, sentiment_analysis: Dict) -> Dict:
        """格式化情绪分析结果"""
        if not sentiment_analysis:
            return {}

        news_sentiment = sentiment_analysis.get('news_sentiment', {})
        market_sentiment = sentiment_analysis.get('market_sentiment', {})

        return {
            '新闻情绪': {
                '整体情绪': f"{news_sentiment.get('overall_sentiment', 0):.3f}",
                '市场情绪': news_sentiment.get('market_mood', '中性'),
                '新闻数量': news_sentiment.get('news_count', 0),
                '情绪趋势': news_sentiment.get('sentiment_trend', '稳定'),
                '积极比例': f"{news_sentiment.get('sentiment_distribution', {}).get('positive', 0):.1f}%",
                '消极比例': f"{news_sentiment.get('sentiment_distribution', {}).get('negative', 0):.1f}%"
            },
            '市场情绪': {
                '恐慌贪婪指数': market_sentiment.get('fear_greed_index', 50),
                'VIX指数': market_sentiment.get('vix_index', 20),
                '资金流向': market_sentiment.get('fund_flow', '中性'),
                '机构观点': market_sentiment.get('institutional_view', '中性')
            },
            '关键词分析': news_sentiment.get('keywords', {}),
            '社交媒体': sentiment_analysis.get('social_sentiment', {}),
            '机构情绪': sentiment_analysis.get('institutional_sentiment', {})
        }

    def _generate_risk_analysis(self, analysis_results: Dict) -> Dict:
        """生成风险分析"""
        fundamental = analysis_results.get('fundamental_analysis', {})
        technical = analysis_results.get('technical_analysis', {})

        risk_metrics = fundamental.get('risk_metrics', {})
        volatility_indicators = technical.get('volatility_indicators', {})

        # 风险等级评估
        volatility = fundamental.get('performance_metrics', {}).get('volatility', 0)
        max_drawdown = fundamental.get('performance_metrics', {}).get('max_drawdown', 0)

        risk_level = self._assess_risk_level_detailed(volatility, max_drawdown)

        return {
            '风险等级': risk_level,
            '主要风险': self._identify_main_risks(analysis_results),
            '风险指标': {
                '波动率': f"{volatility:.2f}%",
                '最大回撤': f"{max_drawdown:.2f}%",
                'Beta系数': f"{risk_metrics.get('beta', 0):.3f}",
                'VaR(95%)': f"{risk_metrics.get('var_95', 0):.2f}%"
            },
            '风险控制建议': self._generate_risk_control_advice(risk_level, analysis_results),
            '止损建议': self._generate_stop_loss_advice(analysis_results),
            '仓位建议': self._generate_position_advice(risk_level)
        }

    def _generate_performance_analysis(self, analysis_results: Dict) -> Dict:
        """生成业绩分析"""
        performance = analysis_results.get('fundamental_analysis', {}).get('performance_metrics', {})

        return {
            '收益分析': {
                '绝对收益': performance.get('total_return', 0),
                '年化收益': performance.get('annual_return', 0),
                '期间收益': performance.get('period_returns', {})
            },
            '风险调整收益': {
                '夏普比率': performance.get('sharpe_ratio', 0),
                '卡玛比率': performance.get('calmar_ratio', 0),
                '索提诺比率': performance.get('sortino_ratio', 0)
            },
            '收益特征': {
                '胜率': performance.get('win_rate', 0),
                '收益分布': performance.get('return_distribution', {}),
                '业绩等级': performance.get('performance_grade', '中等')
            },
            '业绩归因': self._generate_performance_attribution(analysis_results),
            '同类排名': self._generate_peer_ranking(analysis_results)
        }

    def _generate_market_comparison(self, analysis_results: Dict) -> Dict:
        """生成市场对比分析"""
        return {
            '基准比较': self._compare_with_benchmark(analysis_results),
            '同类比较': self._compare_with_peers_detailed(analysis_results),
            '市场环境': self._analyze_market_environment(analysis_results),
            '相对表现': self._analyze_relative_performance(analysis_results)
        }

    def _generate_all_charts(self, analysis_results: Dict) -> Dict:
        """生成所有图表"""
        charts = {}

        try:
            # 净值走势图
            charts['nav_trend'] = self._create_nav_trend_chart(analysis_results)

            # 技术指标图
            charts['technical_indicators'] = self._create_technical_indicators_chart(analysis_results)

            # 收益分布图
            charts['return_distribution'] = self._create_return_distribution_chart(analysis_results)

            # 风险收益散点图
            charts['risk_return_scatter'] = self._create_risk_return_scatter(analysis_results)

            # 回撤分析图
            charts['drawdown_analysis'] = self._create_drawdown_analysis_chart(analysis_results)

            # 持仓分析图
            charts['holdings_analysis'] = self._create_holdings_pie_chart(analysis_results)

            # 业绩对比图
            charts['performance_comparison'] = self._create_performance_comparison_chart(analysis_results)

            # 情绪指标图
            charts['sentiment_indicators'] = self._create_sentiment_chart(analysis_results)

        except Exception as e:
            log_error(f"生成图表失败: {e}")

        return charts

    def _create_nav_trend_chart(self, analysis_results: Dict) -> str:
        """创建净值走势图"""
        try:
            history_data = analysis_results.get('history_data')
            if history_data is None or history_data.empty:
                return ""

            fig = go.Figure()

            # 净值曲线
            fig.add_trace(go.Scatter(
                x=history_data['date'],
                y=history_data['nav'] if 'nav' in history_data.columns else history_data['close'],
                mode='lines',
                name='基金净值',
                line=dict(color='blue', width=2)
            ))

            # 添加移动平均线
            if len(history_data) >= 20:
                ma20 = history_data['nav'].rolling(20).mean() if 'nav' in history_data.columns else history_data['close'].rolling(20).mean()
                fig.add_trace(go.Scatter(
                    x=history_data['date'],
                    y=ma20,
                    mode='lines',
                    name='20日均线',
                    line=dict(color='orange', width=1, dash='dash')
                ))

            fig.update_layout(
                title='基金净值走势图',
                xaxis_title='日期',
                yaxis_title='净值',
                template='plotly_white',
                height=400
            )

            # 保存图表
            chart_path = self.output_dir / "images" / "nav_trend.html"
            fig.write_html(str(chart_path))

            return str(chart_path)

        except Exception as e:
            log_error(f"创建净值走势图失败: {e}")
            return ""

    def _create_technical_indicators_chart(self, analysis_results: Dict) -> str:
        """创建技术指标图"""
        try:
            history_data = analysis_results.get('history_data')
            if history_data is None or history_data.empty:
                return ""

            # 创建子图
            fig = make_subplots(
                rows=3, cols=1,
                subplot_titles=('净值与移动平均线', 'MACD', 'RSI'),
                vertical_spacing=0.1,
                row_heights=[0.5, 0.25, 0.25]
            )

            # 价格和均线
            price_col = 'nav' if 'nav' in history_data.columns else 'close'
            fig.add_trace(go.Scatter(
                x=history_data['date'], y=history_data[price_col],
                mode='lines', name='净值', line=dict(color='blue')
            ), row=1, col=1)

            if len(history_data) >= 20:
                ma20 = history_data[price_col].rolling(20).mean()
                fig.add_trace(go.Scatter(
                    x=history_data['date'], y=ma20,
                    mode='lines', name='MA20', line=dict(color='orange', dash='dash')
                ), row=1, col=1)

            # MACD (简化计算)
            if len(history_data) >= 34:
                exp1 = history_data[price_col].ewm(span=12).mean()
                exp2 = history_data[price_col].ewm(span=26).mean()
                macd_line = exp1 - exp2
                signal_line = macd_line.ewm(span=9).mean()

                fig.add_trace(go.Scatter(
                    x=history_data['date'], y=macd_line,
                    mode='lines', name='MACD', line=dict(color='blue')
                ), row=2, col=1)

                fig.add_trace(go.Scatter(
                    x=history_data['date'], y=signal_line,
                    mode='lines', name='Signal', line=dict(color='red')
                ), row=2, col=1)

            # RSI (简化计算)
            if len(history_data) >= 15:
                delta = history_data[price_col].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))

                fig.add_trace(go.Scatter(
                    x=history_data['date'], y=rsi,
                    mode='lines', name='RSI', line=dict(color='purple')
                ), row=3, col=1)

                # RSI参考线
                fig.add_hline(y=70, row=3, col=1, line_dash="dash", line_color="red")
                fig.add_hline(y=30, row=3, col=1, line_dash="dash", line_color="green")

            fig.update_layout(
                title='技术指标分析',
                height=800,
                template='plotly_white'
            )

            # 保存图表
            chart_path = self.output_dir / "images" / "technical_indicators.html"
            fig.write_html(str(chart_path))

            return str(chart_path)

        except Exception as e:
            log_error(f"创建技术指标图失败: {e}")
            return ""

    def _create_return_distribution_chart(self, analysis_results: Dict) -> str:
        """创建收益分布图"""
        try:
            history_data = analysis_results.get('history_data')
            if history_data is None or history_data.empty:
                return ""

            # 计算日收益率
            price_col = 'nav' if 'nav' in history_data.columns else 'close'
            returns = history_data[price_col].pct_change().dropna() * 100

            fig = go.Figure()

            # 直方图
            fig.add_trace(go.Histogram(
                x=returns,
                nbinsx=50,
                name='收益率分布',
                opacity=0.7
            ))

            # 正态分布拟合曲线
            mean_return = returns.mean()
            std_return = returns.std()
            x_norm = np.linspace(returns.min(), returns.max(), 100)
            y_norm = np.exp(-0.5 * ((x_norm - mean_return) / std_return) ** 2) / (std_return * np.sqrt(2 * np.pi))
            y_norm = y_norm * len(returns) * (returns.max() - returns.min()) / 50  # 标准化

            fig.add_trace(go.Scatter(
                x=x_norm, y=y_norm,
                mode='lines',
                name='正态分布拟合',
                line=dict(color='red', width=2)
            ))

            fig.update_layout(
                title='日收益率分布',
                xaxis_title='收益率 (%)',
                yaxis_title='频次',
                template='plotly_white',
                height=400
            )

            # 保存图表
            chart_path = self.output_dir / "images" / "return_distribution.html"
            fig.write_html(str(chart_path))

            return str(chart_path)

        except Exception as e:
            log_error(f"创建收益分布图失败: {e}")
            return ""

    def _generate_markdown_report(self, report_content: Dict) -> str:
        """生成Markdown格式报告"""
        try:
            metadata = report_content['metadata']

            md_content = f"""# {metadata['fund_name']} 投资分析报告

**基金代码**: {metadata['fund_code']}  
**报告时间**: {metadata['report_time']}  
**分析周期**: {metadata['analysis_period']}  

---

{report_content['executive_summary']}

## 投资建议

**投资评级**: {report_content['investment_recommendation']['recommendation_level']}  
**信号类型**: {report_content['investment_recommendation']['signal_type']}  
**信心水平**: {report_content['investment_recommendation']['confidence']}  
**建议仓位**: {report_content['investment_recommendation']['position_size']}  
**预期持有期**: {report_content['investment_recommendation']['expected_holding_period']}  

### 投资理由

{chr(10).join(f"- {reason}" for reason in report_content['investment_recommendation']['reasoning'])}

## 技术分析

{self._format_technical_section_md(report_content['technical_analysis'])}

## 基本面分析

{self._format_fundamental_section_md(report_content['fundamental_analysis'])}

## 情绪分析

{self._format_sentiment_section_md(report_content['sentiment_analysis'])}

## 风险分析

**风险等级**: {report_content['risk_analysis']['风险等级']}

### 主要风险点

{chr(10).join(f"- {risk}" for risk in report_content['risk_analysis']['主要风险'])}

### 风险控制建议

{chr(10).join(f"- {advice}" for advice in report_content['risk_analysis']['风险控制建议'])}

## 免责声明

本报告基于公开信息和量化分析模型生成，仅供参考，不构成投资建议。投资有风险，入市需谨慎。

---

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

            # 保存Markdown文件
            md_path = self.output_dir / f"fund_analysis_{metadata['fund_code']}_{datetime.now().strftime('%Y%m%d')}.md"
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(md_content)

            return str(md_path)

        except Exception as e:
            log_error(f"生成Markdown报告失败: {e}")
            return ""

    def _generate_html_report(self, report_content: Dict) -> str:
        """生成HTML格式报告"""
        try:
            # 先生成Markdown
            md_path = self._generate_markdown_report(report_content)

            if md_path:
                # 读取Markdown内容
                with open(md_path, 'r', encoding='utf-8') as f:
                    md_content = f.read()

                # 转换为HTML
                html_content = markdown.markdown(md_content, extensions=['tables', 'toc'])

                # 添加CSS样式
                html_with_style = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_content['metadata']['fund_name']} 投资分析报告</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; border-left: 4px solid #3498db; padding-left: 10px; }}
        h3 {{ color: #7f8c8d; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f8f9fa; font-weight: bold; }}
        .highlight {{ background-color: #fff3cd; padding: 10px; border-radius: 5px; margin: 10px 0; }}
        .risk-warning {{ background-color: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .recommendation {{ background-color: #d4edda; color: #155724; padding: 15px; border-radius: 5px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        {html_content}
    </div>
</body>
</html>
                """

                # 保存HTML文件
                html_path = self.output_dir / "html" / f"fund_analysis_{report_content['metadata']['fund_code']}_{datetime.now().strftime('%Y%m%d')}.html"
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_with_style)

                return str(html_path)

        except Exception as e:
            log_error(f"生成HTML报告失败: {e}")
            return ""

    def _save_json_report(self, report_content: Dict) -> str:
        """保存JSON格式报告"""
        try:
            json_path = self.output_dir / "data" / f"fund_analysis_{report_content['metadata']['fund_code']}_{datetime.now().strftime('%Y%m%d')}.json"

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(report_content, f, ensure_ascii=False, indent=2, default=str)

            return str(json_path)

        except Exception as e:
            log_error(f"保存JSON报告失败: {e}")
            return ""

    # 辅助方法
    def _get_analysis_period(self, analysis_results: Dict) -> str:
        """获取分析周期"""
        history_data = analysis_results.get('history_data')
        if history_data is not None and not history_data.empty and 'date' in history_data.columns:
            start_date = history_data['date'].min()
            end_date = history_data['date'].max()
            return f"{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}"
        return "近一年"

    def _get_recommendation_reason(self, signal: Dict) -> str:
        """获取投资建议原因"""
        reasoning = signal.get('reasoning', [])
        if reasoning:
            return f"主要基于：{', '.join(reasoning[:3])}"
        return "基于综合分析模型判断"

    def _generate_risk_warning(self, analysis_results: Dict) -> str:
        """生成风险提示"""
        risk_level = self._assess_risk_level_simple(analysis_results)

        warnings = {
            '低风险': "该基金风险相对较低，但仍需关注市场波动风险。",
            '中等风险': "该基金具有中等风险水平，投资者应充分了解产品特性。",
            '高风险': "该基金风险较高，适合风险承受能力强的投资者。",
            '极高风险': "该基金风险极高，投资者需谨慎考虑，做好风险控制。"
        }

        return warnings.get(risk_level, "投资需谨慎，充分评估风险承受能力。")

    def _assess_risk_level_simple(self, analysis_results: Dict) -> str:
        """简单风险等级评估"""
        performance = analysis_results.get('fundamental_analysis', {}).get('performance_metrics', {})
        volatility = performance.get('volatility', 0)
        max_drawdown = abs(performance.get('max_drawdown', 0))

        if volatility < 5 and max_drawdown < 5:
            return '低风险'
        elif volatility < 15 and max_drawdown < 15:
            return '中等风险'
        elif volatility < 25 and max_drawdown < 25:
            return '高风险'
        else:
            return '极高风险'

    def _get_recommendation_level(self, signal_type) -> str:
        """获取投资建议等级"""
        level_mapping = {
            SignalType.STRONG_BUY: "强烈推荐",
            SignalType.BUY: "推荐",
            SignalType.WEAK_BUY: "谨慎推荐",
            SignalType.HOLD: "中性",
            SignalType.WEAK_SELL: "谨慎回避",
            SignalType.SELL: "不推荐",
            SignalType.STRONG_SELL: "强烈不推荐"
        }
        return level_mapping.get(signal_type, "中性")

    # 其他格式化方法...
    def _format_technical_section_md(self, technical_analysis: Dict) -> str:
        """格式化技术分析部分"""
        if not technical_analysis:
            return "技术分析数据不足。"

        return f"""
**技术得分**: {technical_analysis.get('技术得分', 'N/A')}

### 移动平均分析
- 均线排列: {technical_analysis.get('移动平均', {}).get('均线排列', 'N/A')}
- 金叉死叉: {technical_analysis.get('移动平均', {}).get('金叉死叉', 'N/A')}
- MA5偏离: {technical_analysis.get('移动平均', {}).get('MA5偏离', 'N/A')}

### MACD指标
- MACD值: {technical_analysis.get('MACD指标', {}).get('MACD值', 'N/A')}
- 信号: {technical_analysis.get('MACD指标', {}).get('信号', 'N/A')}

### RSI指标
- RSI值: {technical_analysis.get('RSI指标', {}).get('RSI值', 'N/A')}
- RSI信号: {technical_analysis.get('RSI指标', {}).get('RSI信号', 'N/A')}
        """

    def _format_fundamental_section_md(self, fundamental_analysis: Dict) -> str:
        """格式化基本面分析部分"""
        if not fundamental_analysis:
            return "基本面分析数据不足。"

        basic_info = fundamental_analysis.get('基本信息', {})
        performance = fundamental_analysis.get('业绩指标', {})

        return f"""
### 基本信息
- 基金类型: {basic_info.get('基金类型', 'N/A')}
- 基金规模: {basic_info.get('基金规模', 'N/A')}
- 运作年限: {basic_info.get('运作年限', 'N/A')}
- 基金经理: {basic_info.get('基金经理', 'N/A')}

### 业绩指标
- 年化收益: {performance.get('年化收益', 'N/A')}
- 最大回撤: {performance.get('最大回撤', 'N/A')}
- 夏普比率: {performance.get('夏普比率', 'N/A')}
- 胜率: {performance.get('胜率', 'N/A')}
        """

    def _format_sentiment_section_md(self, sentiment_analysis: Dict) -> str:
        """格式化情绪分析部分"""
        if not sentiment_analysis:
            return "情绪分析数据不足。"

        news_sentiment = sentiment_analysis.get('新闻情绪', {})

        return f"""
### 新闻情绪分析
- 整体情绪: {news_sentiment.get('整体情绪', 'N/A')}
- 市场情绪: {news_sentiment.get('市场情绪', 'N/A')}
- 情绪趋势: {news_sentiment.get('情绪趋势', 'N/A')}
- 积极比例: {news_sentiment.get('积极比例', 'N/A')}
- 消极比例: {news_sentiment.get('消极比例', 'N/A')}
        """

    # 占位符方法 - 需要根据实际需求实现
    def _generate_investment_strategy(self, signal: Dict) -> str:
        return "建议采用分批建仓策略，控制单次投资比例。"

    def _generate_timing_advice(self, signal: Dict) -> str:
        return "建议在技术指标确认后进行操作。"

    def _assess_risk_level_detailed(self, volatility: float, max_drawdown: float) -> str:
        return self._assess_risk_level_simple({'fundamental_analysis': {'performance_metrics': {'volatility': volatility, 'max_drawdown': max_drawdown}}})

    def _identify_main_risks(self, analysis_results: Dict) -> List[str]:
        return ["市场风险", "流动性风险", "管理风险"]

    def _generate_risk_control_advice(self, risk_level: str, analysis_results: Dict) -> List[str]:
        return ["设置止损位", "控制仓位比例", "定期审视投资组合"]

    def _generate_stop_loss_advice(self, analysis_results: Dict) -> str:
        return "建议设置5-10%的止损位"

    def _generate_position_advice(self, risk_level: str) -> str:
        advice_map = {
            '低风险': '可适当增加仓位',
            '中等风险': '控制在合理仓位',
            '高风险': '降低仓位比例',
            '极高风险': '谨慎参与或观望'
        }
        return advice_map.get(risk_level, '控制在合理仓位')

    def _generate_performance_attribution(self, analysis_results: Dict) -> Dict:
        return {"资产配置贡献": "N/A", "行业配置贡献": "N/A", "个股选择贡献": "N/A"}

    def _generate_peer_ranking(self, analysis_results: Dict) -> str:
        return "同类排名数据待完善"

    def _compare_with_benchmark(self, analysis_results: Dict) -> Dict:
        return {"相对收益": "N/A", "跟踪误差": "N/A", "信息比率": "N/A"}

    def _compare_with_peers_detailed(self, analysis_results: Dict) -> Dict:
        return {"同类平均收益": "N/A", "排名百分位": "N/A"}

    def _analyze_market_environment(self, analysis_results: Dict) -> Dict:
        return {"市场趋势": "N/A", "风格偏好": "N/A", "流动性环境": "N/A"}

    def _analyze_relative_performance(self, analysis_results: Dict) -> Dict:
        return {"相对强度": "N/A", "Beta系数": "N/A", "Alpha系数": "N/A"}

    def _create_risk_return_scatter(self, analysis_results: Dict) -> str:
        return ""

    def _create_drawdown_analysis_chart(self, analysis_results: Dict) -> str:
        return ""

    def _create_holdings_pie_chart(self, analysis_results: Dict) -> str:
        return ""

    def _create_performance_comparison_chart(self, analysis_results: Dict) -> str:
        return ""

    def _create_sentiment_chart(self, analysis_results: Dict) -> str:
        return ""

    def _generate_appendix(self, analysis_results: Dict) -> Dict:
        return {
            "数据来源": ["东方财富", "新浪财经", "雪球", "akshare"],
            "分析方法": ["技术分析", "基本面分析", "情绪分析"],
            "模型说明": "基于多因子模型的量化分析"
        }
