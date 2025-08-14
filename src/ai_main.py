"""AI驱动的基金分析主程序 - 完全智能化解决方案"""

import asyncio
import sys
import os
from datetime import datetime
import json
from pathlib import Path
import traceback

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logger import log_info, log_warning, log_error, log_debug
from src.core.smart_system import SmartFundSystem

class AIFundAnalysisSystem:
    """AI基金分析系统 - 完全智能化"""

    def __init__(self):
        self.smart_system = SmartFundSystem()
        self.output_dir = Path("reports")
        self.data_dir = Path("data")

        # 创建目录
        self.output_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)

        log_info("AI基金分析系统初始化完成")

    async def run_ai_analysis(self):
        """运行AI分析"""
        try:
            log_info("🚀 启动AI驱动的基金分析系统")
            log_info(f"⏰ 系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            log_info("🤖 使用完全AI生成的数据，无需外部API")

            # 运行智能分析
            results = await self.smart_system.run_complete_analysis(max_funds=25)

            # 保存结果
            await self._save_analysis_results(results)

            # 生成总结报告
            await self._generate_summary_report(results)

            # 显示统计信息
            self._display_statistics(results['stats'])

            log_info("✅ AI基金分析系统运行完成")

        except Exception as e:
            log_error(f"❌ AI系统运行失败: {e}")
            log_error(f"详细错误: {traceback.format_exc()}")

    async def _save_analysis_results(self, results: dict):
        """保存分析结果"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # 保存基金分析结果
            analysis_file = self.data_dir / f"ai_fund_analysis_{timestamp}.json"
            with open(analysis_file, 'w', encoding='utf-8') as f:
                # 将DataFrame转换为可序列化的格式
                serializable_results = self._make_serializable(results)
                json.dump(serializable_results, f, ensure_ascii=False, indent=2, default=str)

            log_info(f"📁 分析结果已保存到: {analysis_file}")

        except Exception as e:
            log_error(f"保存分析结果失败: {e}")

    def _make_serializable(self, obj):
        """将对象转换为可序列化格式"""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif hasattr(obj, '__dict__'):
            return self._make_serializable(obj.__dict__)
        else:
            return obj

    async def _generate_summary_report(self, results: dict):
        """生成总结报告"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

            # 获取系统总结
            system_summary = results.get('system_summary', {})
            analysis_results = results.get('analysis_results', [])

            # 生成Markdown报告
            report_content = self._create_markdown_report(system_summary, analysis_results)

            # 保存今日报告
            today_report = self.output_dir / "today_report.md"
            with open(today_report, 'w', encoding='utf-8') as f:
                f.write(report_content)

            # 保存历史报告
            history_report = self.output_dir / f"ai_analysis_report_{timestamp}.md"
            with open(history_report, 'w', encoding='utf-8') as f:
                f.write(report_content)

            log_info(f"📊 AI分析报告已生成: {today_report}")

        except Exception as e:
            log_error(f"生成总结报告失败: {e}")

    def _create_markdown_report(self, system_summary: dict, analysis_results: list) -> str:
        """创建Markdown报告"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        report = f"""# 🤖 AI基金分析报告

## 📅 报告信息
- **生成时间**: {timestamp}
- **分析方法**: AI智能分析
- **数据来源**: AI生成 + 智能模拟

## 📊 市场概况

{system_summary.get('market_overview', 'AI正在分析市场情况...')}

## 🎯 基金分析总结

### 📈 整体表现
{system_summary.get('fund_analysis', 'AI基金分析进行中...')}

### 🧠 AI智能洞察
{system_summary.get('ai_insights', {}).get('market_trend_prediction', 'AI市场预测分析中...')}

## 💡 投资建议

{system_summary.get('investment_advice', 'AI正在生成个性化投资建议...')}

## 🏆 优秀基金推荐

"""

        # 添加基金分析结果
        if analysis_results:
            report += "| 基金代码 | 基金名称 | AI评级 | 推荐度 | 风险等级 |\n"
            report += "|---------|---------|--------|--------|----------|\n"

            for result in analysis_results[:10]:  # 显示前10只基金
                fund_info = result.get('fund_info', {})
                investment_advice = fund_info.get('investment_advice', {})

                report += f"| {fund_info.get('code', 'N/A')} "
                report += f"| {fund_info.get('name', 'N/A')} "
                report += f"| {investment_advice.get('ai_rating', 'N/A')} "
                report += f"| {investment_advice.get('recommendation', 'N/A')} "
                report += f"| {fund_info.get('risk_metrics', {}).get('risk_level', 'N/A')} |
"

        report += f"""

## 📋 板块分析

{self._format_sector_analysis(system_summary.get('sector_analysis', {}))}

## ⚠️ 风险提示

{system_summary.get('risk_analysis', {}).get('risk_warning', 'AI风险分析进行中...')}

## 🔍 详细统计

- **分析基金总数**: {len(analysis_results)}
- **AI评级AAA基金**: {sum(1 for r in analysis_results if r.get('fund_info', {}).get('investment_advice', {}).get('ai_rating') == 'AAA')}
- **推荐买入基金**: {sum(1 for r in analysis_results if '推荐' in r.get('fund_info', {}).get('investment_advice', {}).get('recommendation', ''))}

## 🤖 AI分析说明

本报告完全由AI智能生成，采用以下先进技术：

1. **🧠 多因子分析模型**: 综合考虑宏观经济、政策环境、市场流动性等因素
2. **📊 智能数据生成**: 基于金融数学模型生成真实可信的历史数据
3. **🎯 机器学习评级**: AI驱动的基金评级和推荐系统
4. **📈 趋势预测算法**: 智能预测市场趋势和投资机会

---

*📝 本报告由AI智能生成，仅供参考，不构成投资建议*  
*⚡ 系统版本: AI-Enhanced v2.0*  
*🔄 下次更新: 每日自动更新*
"""

        return report

    def _format_sector_analysis(self, sector_analysis: dict) -> str:
        """格式化板块分析"""
        if not sector_analysis:
            return "AI板块分析进行中..."

        formatted = ""
        for sector, analysis in sector_analysis.items():
            performance = analysis.get('performance', '平稳')
            recommendation = analysis.get('recommendation', '观望')
            formatted += f"- **{sector}**: {performance} - {recommendation}
"

        return formatted if formatted else "AI板块分析进行中..."

    def _display_statistics(self, stats: dict):
        """显示统计信息"""
        log_info("=" * 60)
        log_info("🎯 AI分析统计")
        log_info("=" * 60)

        runtime = datetime.now() - stats['start_time']

        log_info(f"⏱️  运行时间: {runtime}")
        log_info(f"📊 分析基金总数: {stats['total_funds_analyzed']}")
        log_info(f"✅ 成功分析数量: {stats['successful_analyses']}")
        log_info(f"❌ 失败分析数量: {stats['failed_analyses']}")
        log_info(f"📋 生成报告数量: {stats['reports_generated']}")

        if stats['total_funds_analyzed'] > 0:
            success_rate = stats['successful_analyses'] / stats['total_funds_analyzed']
            log_info(f"🎯 成功率: {success_rate:.1%}")

        log_info("=" * 60)

async def main():
    """AI主函数"""
    try:
        # 创建AI系统实例
        ai_system = AIFundAnalysisSystem()

        # 运行AI分析
        await ai_system.run_ai_analysis()

    except KeyboardInterrupt:
        log_warning("⚠️ 用户中断程序执行")
    except Exception as e:
        log_error(f"❌ AI系统运行失败: {e}")
        log_error(f"详细错误: {traceback.format_exc()}")
    finally:
        log_info("🔚 AI基金分析系统退出")

if __name__ == "__main__":
    # 运行AI系统
    asyncio.run(main())
