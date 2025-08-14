"""
主程序 - 基金数据爬取与分析系统
"""
import os
import sys
import asyncio
import time
import json
import traceback
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import Dict, List, Optional
import pandas as pd
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logger import log_info, log_warning, log_error, log_debug, create_task_logger
from src.utils.proxy_manager import proxy_manager
from src.crawler.enhanced_fund_crawler import EnhancedFundCrawler
from src.analyzer.technical_analyzer import TechnicalAnalyzer
from src.analyzer.fundamental_analyzer import FundamentalAnalyzer
from src.analyzer.enhanced_sentiment_analyzer import EnhancedSentimentAnalyzer
from src.analyzer.signal_generator import SignalGenerator
from src.report.report_generator import ReportGenerator
from src.config import (
    DEFAULT_FUNDS, CRAWLER_CONFIG, ANALYSIS_CONFIG, 
    STORAGE_CONFIG, PERFORMANCE_CONFIG
)

class FundAnalysisSystem:
    """基金分析系统主类"""

    def __init__(self):
        self.crawler = EnhancedFundCrawler()
        self.technical_analyzer = TechnicalAnalyzer()
        self.fundamental_analyzer = FundamentalAnalyzer()
        self.sentiment_analyzer = EnhancedSentimentAnalyzer()
        self.signal_generator = SignalGenerator()
        self.report_generator = ReportGenerator()

        # 创建必要的目录
        self._create_directories()

        # 系统状态
        self.system_status = {
            'start_time': datetime.now(),
            'total_funds_analyzed': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'reports_generated': 0
        }

    def _create_directories(self):
        """创建必要的目录结构"""
        directories = [
            'data', 'cache', 'logs', 'reports', 'backup',
            'reports/images', 'reports/html', 'reports/markdown',
            'data/raw', 'data/processed', 'data/funds', 'data/news'
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    async def run_full_analysis(self):
        """运行完整的基金分析流程"""
        main_logger = create_task_logger("基金分析系统")
        main_logger.start("开始执行完整分析流程")

        try:
            # 第一阶段：数据获取
            log_info("=" * 60)
            log_info("第一阶段：数据获取与爬取")
            log_info("=" * 60)

            # 启动代理管理器
            await self._initialize_proxy_manager()

            # 获取基金列表
            fund_list = await self._get_fund_list()
            if not fund_list:
                log_error("未能获取基金列表，程序终止")
                return

            log_info(f"获取到 {len(fund_list)} 只基金，开始详细分析")

            # 第二阶段：并发分析
            log_info("=" * 60)
            log_info("第二阶段：多线程基金分析")
            log_info("=" * 60)

            analysis_results = await self._parallel_fund_analysis(fund_list)

            # 第三阶段：生成报告
            log_info("=" * 60)
            log_info("第三阶段：生成综合分析报告")
            log_info("=" * 60)

            await self._generate_comprehensive_reports(analysis_results)

            # 第四阶段：市场总结
            log_info("=" * 60)
            log_info("第四阶段：生成市场总结报告")
            log_info("=" * 60)

            await self._generate_market_summary(analysis_results)

            # 系统统计
            self._print_system_statistics()

            main_logger.success(f"完整分析流程执行完成，共分析 {len(analysis_results)} 只基金")

        except Exception as e:
            main_logger.error(e, "完整分析流程执行失败")
            log_error(f"系统错误详情: {traceback.format_exc()}")

    async def _initialize_proxy_manager(self):
        """初始化代理管理器"""
        proxy_logger = create_task_logger("代理管理器初始化")
        proxy_logger.start()

        try:
            # 更新代理列表
            proxy_manager.update_proxy_list()

            # 启动自动更新
            proxy_manager.start_auto_update()

            stats = proxy_manager.get_stats()
            if stats['total'] > 0:
                proxy_logger.success(f"代理管理器初始化成功，可用代理: {stats['total']} 个")
            else:
                proxy_logger.warning("未获取到可用代理，将使用直连模式")

        except Exception as e:
            proxy_logger.error(e, "代理管理器初始化失败")

    async def _get_fund_list(self) -> List[Dict]:
        """获取基金列表"""
        fund_logger = create_task_logger("获取基金列表")
        fund_logger.start()

        try:
            # 获取热门基金列表
            fund_list = self.crawler.get_fund_list(top_n=1000)

            # 如果获取失败，使用默认基金列表
            if not fund_list:
                log_warning("使用默认基金列表")
                fund_list = [{'code': code, 'name': f'基金{code}', 'type': '混合型'} 
                           for code in DEFAULT_FUNDS]

            # 保存基金列表
            self._save_fund_list(fund_list)

            fund_logger.success(f"成功获取 {len(fund_list)} 只基金信息")
            return fund_list

        except Exception as e:
            fund_logger.error(e, "获取基金列表失败")
            return []

    async def _parallel_fund_analysis(self, fund_list: List[Dict]) -> List[Dict]:
        """并行分析基金"""
        analysis_logger = create_task_logger("并行基金分析")
        analysis_logger.start(f"开始分析 {len(fund_list)} 只基金")

        results = []

        # 限制并发数量以避免过载
        max_concurrent = min(PERFORMANCE_CONFIG['cpu_cores'] * 2, 20)
        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_single_fund(fund_info: Dict) -> Optional[Dict]:
            async with semaphore:
                return await self._analyze_single_fund(fund_info)

        # 创建任务
        tasks = [analyze_single_fund(fund) for fund in fund_list]

        # 执行任务并收集结果
        completed = 0
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                if result:
                    results.append(result)
                    self.system_status['successful_analyses'] += 1
                else:
                    self.system_status['failed_analyses'] += 1

                completed += 1

                # 显示进度
                if completed % 10 == 0 or completed == len(tasks):
                    analysis_logger.progress(
                        completed, len(tasks), 
                        f"成功: {self.system_status['successful_analyses']}, "
                        f"失败: {self.system_status['failed_analyses']}"
                    )

            except Exception as e:
                log_error(f"基金分析任务失败: {e}")
                self.system_status['failed_analyses'] += 1

        analysis_logger.success(f"并行分析完成，成功分析 {len(results)} 只基金")
        return results

    async def _analyze_single_fund(self, fund_info: Dict) -> Optional[Dict]:
        """分析单只基金"""
        fund_code = fund_info.get('code', '')
        fund_name = fund_info.get('name', '')

        if not fund_code:
            return None

        try:
            log_debug(f"开始分析基金: {fund_name} ({fund_code})")

            # 1. 获取基金详细信息
            fund_detail = self.crawler.get_fund_detail(fund_code)
            if not fund_detail:
                log_warning(f"无法获取基金详情: {fund_code}")
                return None

            # 2. 获取历史数据
            history_data = self.crawler.get_fund_history(fund_code, days=365)
            if history_data.empty:
                log_warning(f"无法获取历史数据: {fund_code}")
                return None

            # 3. 技术分析
            technical_analysis = self.technical_analyzer.analyze(history_data, fund_code)

            # 4. 基本面分析
            fundamental_analysis = self.fundamental_analyzer.analyze(
                fund_code, fund_detail, history_data
            )

            # 5. AI智能情感分析（包含新闻生成和分析）
            try:
                sentiment_analysis = self.sentiment_analyzer.get_comprehensive_sentiment_analysis(
                    fund_code, fund_detail
                )
                log_info(f"基金 {fund_code} AI情感分析完成，AI建议: {sentiment_analysis.get('final_recommendation', {}).get('recommendation', '未知')}")
            except Exception as e:
                log_warning(f"基金 {fund_code} AI情感分析失败，使用传统分析: {e}")
                # 备用传统情感分析
                sentiment_analysis = self.sentiment_analyzer.analyze_fund_sentiment(
                    fund_detail.get('name', ''),
                    fund_detail.get('company', ''),
                    f"基金{fund_code}相关分析"
                )

            # 6. 综合分析结果
            analysis_results = {
                'fund_code': fund_code,
                'fund_info': fund_detail,
                'history_data': history_data.to_dict('records') if not history_data.empty else [],
                'technical_analysis': technical_analysis,
                'fundamental_analysis': fundamental_analysis,
                'sentiment_analysis': sentiment_analysis,
                'analysis_time': datetime.now().isoformat()
            }

            # 7. 生成交易信号
            signal = self.signal_generator.generate_signal(analysis_results)
            analysis_results['trading_signal'] = signal.__dict__ if hasattr(signal, '__dict__') else signal

            # 8. 保存分析数据
            self._save_analysis_data(fund_code, analysis_results)

            self.system_status['total_funds_analyzed'] += 1
            log_debug(f"基金 {fund_code} 分析完成")

            return analysis_results

        except Exception as e:
            log_error(f"分析基金 {fund_code} 失败: {e}")
            return None

    async def _generate_comprehensive_reports(self, analysis_results: List[Dict]):
        """生成综合分析报告"""
        report_logger = create_task_logger("生成综合报告")
        report_logger.start(f"开始生成 {len(analysis_results)} 个基金报告")

        # 筛选出需要重点关注的基金
        featured_funds = self._select_featured_funds(analysis_results)

        # 为重点基金生成详细报告
        for i, analysis in enumerate(featured_funds):
            try:
                fund_code = analysis.get('fund_code', '')
                signal = analysis.get('trading_signal', {})

                # 生成详细报告
                report_result = self.report_generator.generate_comprehensive_report(
                    analysis, signal
                )

                if report_result.get('success'):
                    self.system_status['reports_generated'] += 1
                    log_info(f"基金 {fund_code} 报告生成成功")
                else:
                    log_warning(f"基金 {fund_code} 报告生成失败")

                report_logger.progress(i + 1, len(featured_funds))

            except Exception as e:
                log_error(f"生成报告失败: {e}")

        report_logger.success(f"成功生成 {self.system_status['reports_generated']} 个基金报告")

    def _select_featured_funds(self, analysis_results: List[Dict]) -> List[Dict]:
        """选择需要重点关注的基金"""
        if not analysis_results:
            return []

        featured = []

        for analysis in analysis_results:
            try:
                signal = analysis.get('trading_signal', {})
                technical = analysis.get('technical_analysis', {})
                fundamental = analysis.get('fundamental_analysis', {})

                # 选择标准
                signal_type = signal.get('signal_type', '')
                confidence = signal.get('confidence', 0)
                technical_score = technical.get('technical_score', 50)
                fundamental_score = fundamental.get('fundamental_score', 50)

                # 强烈买入/卖出信号
                if '强烈' in str(signal_type) and confidence > 0.7:
                    featured.append(analysis)
                    continue

                # 高分基金
                if technical_score > 75 or fundamental_score > 75:
                    featured.append(analysis)
                    continue

                # 高置信度信号
                if confidence > 0.8:
                    featured.append(analysis)
                    continue

            except Exception as e:
                log_debug(f"筛选基金时出错: {e}")
                continue

        # 限制数量，优先选择信号强度高的
        featured.sort(key=lambda x: x.get('trading_signal', {}).get('confidence', 0), reverse=True)

        # 最多选择20只基金进行详细报告
        return featured[:20]

    async def _generate_market_summary(self, analysis_results: List[Dict]):
        """生成市场总结报告"""
        summary_logger = create_task_logger("生成市场总结")
        summary_logger.start()

        try:
            # 生成市场总结报告
            market_summary = self._create_market_summary(analysis_results)

            # 生成投资建议文章
            investment_article = self._create_investment_article(analysis_results, market_summary)

            # 保存报告
            self._save_market_reports(market_summary, investment_article)

            summary_logger.success("市场总结报告生成完成")

        except Exception as e:
            summary_logger.error(e, "生成市场总结失败")

    def _create_market_summary(self, analysis_results: List[Dict]) -> Dict:
        """创建市场总结"""
        if not analysis_results:
            return {}

        # 统计各种信号
        signal_stats = {'强烈买入': 0, '买入': 0, '持有': 0, '卖出': 0, '强烈卖出': 0}
        technical_scores = []
        fundamental_scores = []
        confidence_scores = []

        for analysis in analysis_results:
            try:
                signal = analysis.get('trading_signal', {})
                technical = analysis.get('technical_analysis', {})
                fundamental = analysis.get('fundamental_analysis', {})

                signal_type = str(signal.get('signal_type', '持有'))
                if '强烈买入' in signal_type:
                    signal_stats['强烈买入'] += 1
                elif '买入' in signal_type:
                    signal_stats['买入'] += 1
                elif '卖出' in signal_type:
                    if '强烈' in signal_type:
                        signal_stats['强烈卖出'] += 1
                    else:
                        signal_stats['卖出'] += 1
                else:
                    signal_stats['持有'] += 1

                technical_scores.append(technical.get('technical_score', 50))
                fundamental_scores.append(fundamental.get('fundamental_score', 50))
                confidence_scores.append(signal.get('confidence', 0))

            except Exception as e:
                log_debug(f"处理统计数据时出错: {e}")
                continue

        # 计算平均分数
        avg_technical = np.mean(technical_scores) if technical_scores else 50
        avg_fundamental = np.mean(fundamental_scores) if fundamental_scores else 50
        avg_confidence = np.mean(confidence_scores) if confidence_scores else 0

        return {
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_funds': len(analysis_results),
            'signal_distribution': signal_stats,
            'average_scores': {
                'technical': round(avg_technical, 1),
                'fundamental': round(avg_fundamental, 1),
                'confidence': round(avg_confidence * 100, 1)
            },
            'market_sentiment': self._evaluate_market_sentiment(signal_stats),
            'top_recommendations': self._get_top_recommendations(analysis_results)
        }

    def _create_investment_article(self, analysis_results: List[Dict], market_summary: Dict) -> str:
        """创建投资建议文章"""
        current_time = datetime.now()

        article = f"""# 基金投资分析报告

**分析时间**: {current_time.strftime('%Y年%m月%d日 %H:%M')}  
**分析基金数量**: {market_summary.get('total_funds', 0)}只  
**市场情绪**: {market_summary.get('market_sentiment', '中性')}  

## 市场概况

经过对{market_summary.get('total_funds', 0)}只基金的全面分析，当前市场呈现以下特征：

### 信号分布
{self._format_signal_distribution(market_summary.get('signal_distribution', {}))}

### 技术面分析
- 平均技术得分: {market_summary.get('average_scores', {}).get('technical', 50)}/100
- 技术面整体{self._evaluate_technical_trend(market_summary.get('average_scores', {}).get('technical', 50))}

### 基本面分析  
- 平均基本面得分: {market_summary.get('average_scores', {}).get('fundamental', 50)}/100
- 基本面整体{self._evaluate_fundamental_trend(market_summary.get('average_scores', {}).get('fundamental', 50))}

## 重点推荐

{self._format_top_recommendations(market_summary.get('top_recommendations', []))}

## 投资策略建议

{self._generate_investment_strategy_advice(market_summary)}

## 风险提示

{self._generate_risk_warnings(analysis_results)}

## 操作建议

{self._generate_operation_advice(market_summary)}

---
*本报告由AI基金分析系统自动生成，仅供参考，投资有风险，入市需谨慎。*
"""
        return article

    def _save_fund_list(self, fund_list: List[Dict]):
        """保存基金列表"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = f"data/fund_list_{timestamp}.json"

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(fund_list, f, ensure_ascii=False, indent=2)

            log_debug(f"基金列表已保存: {file_path}")

        except Exception as e:
            log_error(f"保存基金列表失败: {e}")

    def _save_analysis_data(self, fund_code: str, analysis_data: Dict):
        """保存分析数据"""
        try:
            # 保存到JSON文件
            file_path = f"data/funds/{fund_code}_analysis.json"

            # 创建目录
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False, indent=2, default=str)

        except Exception as e:
            log_error(f"保存分析数据失败 {fund_code}: {e}")

    def _save_market_reports(self, market_summary: Dict, investment_article: str):
        """保存市场报告"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # 保存市场总结
            summary_file = f"reports/market_summary_{timestamp}.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(market_summary, f, ensure_ascii=False, indent=2, default=str)

            # 保存投资文章
            article_file = f"reports/investment_article_{timestamp}.md"
            with open(article_file, 'w', encoding='utf-8') as f:
                f.write(investment_article)

            # 同时保存为今日报告（覆盖）
            with open("reports/today_report.md", 'w', encoding='utf-8') as f:
                f.write(investment_article)

            log_info(f"市场报告已保存: {article_file}")

        except Exception as e:
            log_error(f"保存市场报告失败: {e}")

    def _format_signal_distribution(self, signal_dist: Dict) -> str:
        """格式化信号分布"""
        total = sum(signal_dist.values())
        if total == 0:
            return "暂无数据"

        lines = []
        for signal, count in signal_dist.items():
            percentage = count / total * 100
            lines.append(f"- {signal}: {count}只 ({percentage:.1f}%)")

        return "\n".join(lines)

    def _format_top_recommendations(self, recommendations: List[Dict]) -> str:
        """格式化重点推荐"""
        if not recommendations:
            return "暂无重点推荐"

        lines = []
        for i, rec in enumerate(recommendations[:5], 1):
            fund_name = rec.get('fund_name', '')
            fund_code = rec.get('fund_code', '')
            signal_type = rec.get('signal_type', '')
            confidence = rec.get('confidence', 0)

            lines.append(f"{i}. **{fund_name}({fund_code})** - {signal_type} (信心度: {confidence:.1%})")

        return "\n".join(lines)

    def _evaluate_market_sentiment(self, signal_stats: Dict) -> str:
        """评估市场情绪"""
        total = sum(signal_stats.values())
        if total == 0:
            return "中性"

        buy_signals = signal_stats.get('强烈买入', 0) + signal_stats.get('买入', 0)
        sell_signals = signal_stats.get('强烈卖出', 0) + signal_stats.get('卖出', 0)

        buy_ratio = buy_signals / total
        sell_ratio = sell_signals / total

        if buy_ratio > 0.6:
            return "乐观"
        elif sell_ratio > 0.6:
            return "悲观"
        elif buy_ratio > sell_ratio:
            return "偏乐观"
        elif sell_ratio > buy_ratio:
            return "偏悲观"
        else:
            return "中性"

    def _get_top_recommendations(self, analysis_results: List[Dict]) -> List[Dict]:
        """获取重点推荐"""
        recommendations = []

        for analysis in analysis_results:
            try:
                signal = analysis.get('trading_signal', {})
                fund_info = analysis.get('fund_info', {})

                signal_type = str(signal.get('signal_type', ''))
                confidence = signal.get('confidence', 0)

                if confidence > 0.7 and ('买入' in signal_type or '卖出' in signal_type):
                    recommendations.append({
                        'fund_code': analysis.get('fund_code', ''),
                        'fund_name': fund_info.get('name', ''),
                        'signal_type': signal_type,
                        'confidence': confidence,
                        'score': signal.get('score', 0)
                    })

            except Exception as e:
                log_debug(f"处理推荐数据时出错: {e}")
                continue

        # 按信心度排序
        recommendations.sort(key=lambda x: x['confidence'], reverse=True)
        return recommendations[:10]

    def _generate_investment_strategy_advice(self, market_summary: Dict) -> str:
        """生成投资策略建议"""
        sentiment = market_summary.get('market_sentiment', '中性')
        avg_technical = market_summary.get('average_scores', {}).get('technical', 50)
        avg_fundamental = market_summary.get('average_scores', {}).get('fundamental', 50)

        if sentiment == "乐观" and avg_technical > 60:
            return "当前市场情绪乐观，技术面较强，建议适度增加权益类基金配置，但需注意风险控制。"
        elif sentiment == "悲观" and avg_technical < 40:
            return "当前市场情绪悲观，技术面偏弱，建议降低风险敞口，增加债券型基金和货币基金配置。"
        elif avg_fundamental > 60:
            return "基本面较好，建议采用价值投资策略，选择基本面扎实的优质基金长期持有。"
        else:
            return "当前市场处于震荡阶段，建议均衡配置，分批建仓，密切关注市场变化。"

    def _generate_risk_warnings(self, analysis_results: List[Dict]) -> str:
        """生成风险提示"""
        return """1. 基金投资存在市场风险，基金净值可能出现波动
2. 过往业绩不代表未来表现，投资需谨慎
3. 本分析基于历史数据和模型预测，仅供参考
4. 建议根据个人风险承受能力和投资目标进行决策
5. 分散投资，避免过度集中于单一基金或板块"""

    def _generate_operation_advice(self, market_summary: Dict) -> str:
        """生成操作建议"""
        signal_dist = market_summary.get('signal_distribution', {})
        buy_count = signal_dist.get('强烈买入', 0) + signal_dist.get('买入', 0)
        sell_count = signal_dist.get('强烈卖出', 0) + signal_dist.get('卖出', 0)

        if buy_count > sell_count:
            return "当前买入信号较多，可考虑适当增加仓位，但建议分批操作，控制风险。"
        elif sell_count > buy_count:
            return "当前卖出信号较多，建议谨慎操作，必要时减少仓位。"
        else:
            return "当前市场信号相对均衡，建议保持现有配置，观察后续变化。"

    def _evaluate_technical_trend(self, score: float) -> str:
        """评估技术趋势"""
        if score > 70:
            return "表现强势"
        elif score > 55:
            return "表现良好"
        elif score < 30:
            return "表现较弱"
        elif score < 45:
            return "表现偏弱"
        else:
            return "表现中等"

    def _evaluate_fundamental_trend(self, score: float) -> str:
        """评估基本面趋势"""
        return self._evaluate_technical_trend(score)  # 使用相同的评估标准

    def _print_system_statistics(self):
        """打印系统统计信息"""
        runtime = datetime.now() - self.system_status['start_time']

        log_info("=" * 60)
        log_info("系统运行统计")
        log_info("=" * 60)
        log_info(f"运行时间: {runtime}")
        log_info(f"分析基金总数: {self.system_status['total_funds_analyzed']}")
        log_info(f"成功分析数量: {self.system_status['successful_analyses']}")
        log_info(f"失败分析数量: {self.system_status['failed_analyses']}")
        log_info(f"生成报告数量: {self.system_status['reports_generated']}")

        if self.system_status['total_funds_analyzed'] > 0:
            success_rate = self.system_status['successful_analyses'] / self.system_status['total_funds_analyzed']
            log_info(f"成功率: {success_rate:.1%}")

        log_info("=" * 60)

async def main():
    """主函数"""
    try:
        log_info("基金数据爬取与分析系统启动")
        log_info(f"系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 创建系统实例
        system = FundAnalysisSystem()

        # 运行完整分析
        await system.run_full_analysis()

        log_info("基金数据爬取与分析系统运行完成")

    except KeyboardInterrupt:
        log_warning("用户中断程序执行")
    except Exception as e:
        log_error(f"系统运行失败: {e}")
        log_error(f"错误详情: {traceback.format_exc()}")
    finally:
        log_info("系统退出")

if __name__ == "__main__":
    # 设置事件循环策略（Windows兼容）
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # 运行主程序
    asyncio.run(main())
