# report_generator.py
import pandas as pd
from datetime import datetime

class ReportGenerator:
    @staticmethod
    def generate_report(analysis_results):
        """生成报告表格"""
        # 按信号优先级排序：买 > 卖 > 观望 > 误差
        signal_priority = {'买': 0, '卖': 1, '观望': 2, '误差': 3}
        sorted_results = sorted(analysis_results, key=lambda x: signal_priority[x['signal']])
        
        # 创建表格内容
        table_content = "# 基金买卖点分析报告\n\n"
        table_content += f"最后更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # 创建历史信号表头（最近15个交易日）
        history_header = "| 基金名称 | 当前价格 | 操作建议 | "
        history_header += " | ".join([f"T-{14-i}" for i in range(15)])
        history_header += " |\n"
        
        # 创建分隔线
        separator = "| :--- | :---: | :---: |"
        separator += " | ".join([":---:" for _ in range(15)]) + " |\n"
        
        table_content += history_header
        table_content += separator
        
        # 填充表格数据
        for result in sorted_results:
            # 基金名称和代码
            fund_col = f"{result['fund_name']}({result['fund_code']})"
            
            # 当前价格
            price_col = f"{result['current_price']:.4f}"
            
            # 操作建议（带颜色）
            signal_col = result['signal']
            if signal_col == "买":
                signal_col = "🟢 买"
            elif signal_col == "卖":
                signal_col = "🔴 卖"
            elif signal_col == "观望":
                signal_col = "🟡 观望"
            else:
                signal_col = "⚫ 误差"
            
            # 历史信号
            history_cols = ""
            for signal in result['history_signals']:
                if signal == "买":
                    history_cols += "| 🟢 "
                elif signal == "卖":
                    history_cols += "| 🔴 "
                elif signal == "观望":
                    history_cols += "| 🟡 "
                else:
                    history_cols += "| ⚫ "
            
            # 添加一行
            table_content += f"| {fund_col} | {price_col} | {signal_col} {history_cols} |\n"
        
        # 添加说明
        table_content += "\n## 说明\n"
        table_content += "- 🟢 买: 建议买入\n"
        table_content += "- 🔴 卖: 建议卖出\n"
        table_content += "- 🟡 观望: 建议观望\n"
        table_content += "- ⚫ 误差: 分析出错\n"
        table_content += "- 历史信号从右向左排序，最右边为最新信号\n"
        table_content += "- 表格按操作建议优先级排序（买 > 卖 > 观望 > 误差）\n"
        
        return table_content
    
    @staticmethod
    def save_report(report_content, filename="README.md"):
        """保存报告到文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report_content)
