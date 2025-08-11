from scripts.stock_scraper import StockDataScraper  # 使用新的股票爬取类
from scripts.fund_scraper import FundDataScraper
from scripts.data_analyzer import TradingSignalAnalyzer
from scripts.report_generator import TradingReportGenerator
from scripts.utils import setup_logging

logger = setup_logging()

def main():
    logger.info("=" * 50)
    logger.info("开始执行交易信号分析任务")
    logger.info("=" * 50)
    
    # 步骤1: 爬取股票数据（使用新的StockDataScraper）
    stock_scraper = StockDataScraper()
    stock_signals = stock_scraper.run()
    if not stock_signals:
        logger.error("股票数据爬取失败，终止任务")
        return
        
    # 步骤2: 爬取基金数据
    fund_scraper = FundDataScraper()
    fund_signals = fund_scraper.run(max_funds=100)
    if not fund_signals:
        logger.error("基金数据爬取失败，终止任务")
        return
        
    # 步骤3: 分析数据并生成信号
    analyzer = TradingSignalAnalyzer(stock_signals, fund_signals)
    combined_signals = analyzer.run()
    if not combined_signals:
        logger.error("数据分析失败，终止任务")
        return
        
    # 步骤4: 生成报告
    report_generator = TradingReportGenerator(combined_signals)
    if report_generator.run():
        logger.info("交易报告处理完成")
    else:
        logger.error("报告生成失败")
        
    logger.info("=" * 50)
    logger.info("交易信号分析任务完成")
    logger.info("=" * 50)

if __name__ == "__main__":
    main()
