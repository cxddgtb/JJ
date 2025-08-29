# main.py
from config import GUGUDATA_APPKEY, FUND_CODES
from analyzer import FundAnalyzer
from report_generator import ReportGenerator

def main():
    """主函数"""
    # 初始化分析器
    analyzer = FundAnalyzer(GUGUDATA_APPKEY)
    
    # 分析所有基金
    results = analyzer.analyze_all_funds(FUND_CODES)
    
    # 生成报告
    report_content = ReportGenerator.generate_report(results)
    
    # 保存报告
    ReportGenerator.save_report(report_content)
    
    print("基金分析报告已生成并保存到 README.md")

if __name__ == "__main__":
    main()
