from scripts.fund_scraper import FundDataScraper
from scripts.report_generator import TradingReportGenerator
from scripts.utils import setup_logging

logger = setup_logging()

def main():
    logger.info("=" * 50)
    logger.info("开始执行基金信号分析任务")
    logger.info("=" * 50)
    
    # 步骤1: 爬取基金历史数据
    fund_scraper = FundDataScraper()
    fund_signals = fund_scraper.run()
    
    if not fund_signals:
        logger.error("基金数据爬取失败")
        return
        
    # 步骤2: 生成报告
    report_generator = TradingReportGenerator(fund_signals)
    if report_generator.run():
        logger.info("基金信号报告生成完成")
    else:
        logger.error("报告生成失败")
        
    logger.info("=" * 50)
    logger.info("基金信号分析任务完成")
    logger.info("=" * 50)

if __name__ == "__main__":
    main()
