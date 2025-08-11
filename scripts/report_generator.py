from datetime import datetime
import pandas as pd
from config.settings import settings
from scripts.utils import save_data, setup_logging
import os

logger = setup_logging()

class TradingReportGenerator:
    def __init__(self, fund_signals):
        self.fund_signals = fund_signals
        self.trading_date = datetime.now().strftime('%Y-%m-%d')
        
    def generate_html_report(self):
        """生成HTML格式的报告"""
        try:
            # 创建数据框
            columns = ['基金名称', '基金代码']
            
            # 添加日期列（最近15天）
            dates = []
            if self.fund_signals:
                # 从第一个基金获取日期
                dates = [signal['日期'] for signal in self.fund_signals[0]['历史信号']]
                columns.extend(dates)
            
            # 创建空数据框
            df = pd.DataFrame(columns=columns)
            
            # 填充数据
            for fund in self.fund_signals:
                row = {
                    '基金名称': fund['基金名称'],
                    '基金代码': fund['基金代码']
                }
                
                # 添加每日信号
                for signal in fund['历史信号']:
                    date = signal['日期']
                    row[date] = signal['信号']
                
                df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            
            # 生成HTML表格
            html_report = f"""
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>基金交易信号历史记录 - {self.trading_date}</title>
                <style>
                    body {{ font-family: 'Microsoft YaHei', sans-serif; margin: 20px; }}
                    h1 {{ color: #2c3e50; text-align: center; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 12px; text-align: center; }}
                    th {{ background-color: #3498db; color: white; }}
                    tr:nth-child(even) {{ background-color: #f2f2f2; }}
                    .buy {{ background-color: #d4edda; color: #155724; font-weight: bold; }}
                    .sell {{ background-color: #f8d7da; color: #721c24; font-weight: bold; }}
                    .watch {{ background-color: #fff3cd; color: #856404; }}
                </style>
            </head>
            <body>
                <h1>基金交易信号历史记录</h1>
                <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                {df.to_html(classes='fund-table', index=False, escape=False)}
                
                <script>
                    // 为信号单元格添加样式
                    document.querySelectorAll('td').forEach(td => {{
                        if (td.textContent === '买入') {{
                            td.classList.add('buy');
                        }} else if (td.textContent === '卖出') {{
                            td.classList.add('sell');
                        }} else if (td.textContent === '观望') {{
                            td.classList.add('watch');
                        }}
                    }});
                </script>
            </body>
            </html>
            """
            
            # 保存报告
            report_path = os.path.join(settings.OUTPUT_DIR, "fund_signals_report.html")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_report)
                
            return report_path
        except Exception as e:
            logger.exception("生成HTML报告失败")
            return None
            
    def run(self):
        """生成报告"""
        logger.info("开始生成基金信号报告")
        
        report_path = self.generate_html_report()
        if report_path:
            logger.info(f"报告已保存至: {report_path}")
            return True
        return False
