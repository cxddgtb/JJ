#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基金数据分析与买卖点预测系统
主程序入口
"""

import os
import sys
import logging
from datetime import datetime

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from crawlers.news_crawler import NewsCrawler
from crawlers.fund_crawler import FundCrawler
from indicators.long_term_indicators import LongTermIndicators
from indicators.mid_term_indicators import MidTermIndicators
from indicators.short_term_indicators import ShortTermIndicators
from analysis.buy_sell_analysis import BuySellAnalysis
from analysis.ai_analysis import AIAnalysis
from report.generate_table import GenerateTable
from report.generate_article import GenerateArticle
from utils.config import Config

def setup_logging():
    """设置日志"""
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f'fund_analysis_{current_time}.log')

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def main():
    """主函数"""
    logger = setup_logging()
    logger.info("基金数据分析与买卖点预测系统启动")

    try:
        # 1. 爬取基金新闻
        logger.info("开始爬取基金新闻...")
        news_crawler = NewsCrawler()
        news_data = news_crawler.crawl_all_news()
        logger.info(f"成功爬取{len(news_data)}条基金新闻")

        # 2. 爬取基金数据
        logger.info("开始爬取基金数据...")
        fund_crawler = FundCrawler()
        fund_data = fund_crawler.crawl_all_funds()
        logger.info(f"成功爬取{len(fund_data)}只基金数据")

        # 3. 计算长期指标
        logger.info("计算长期指标...")
        long_term_indicators = LongTermIndicators(fund_data)
        long_term_data = long_term_indicators.calculate()

        # 4. 计算中期指标
        logger.info("计算中期指标...")
        mid_term_indicators = MidTermIndicators(fund_data)
        mid_term_data = mid_term_indicators.calculate()

        # 5. 计算短期指标
        logger.info("计算短期指标...")
        short_term_indicators = ShortTermIndicators(fund_data)
        short_term_data = short_term_indicators.calculate()

        # 6. 分析买卖点
        logger.info("分析买卖点...")
        buy_sell_analysis = BuySellAnalysis(
            fund_data, 
            long_term_data, 
            mid_term_data, 
            short_term_data,
            news_data
        )
        buy_sell_points = buy_sell_analysis.analyze()

        # 7. AI分析
        logger.info("进行AI分析...")
        ai_analysis = AIAnalysis(
            fund_data,
            buy_sell_points,
            news_data
        )
        ai_insights = ai_analysis.analyze()

        # 8. 生成买卖点表格
        logger.info("生成买卖点表格...")
        table_generator = GenerateTable(buy_sell_points, ai_insights)
        table_generator.generate()

        # 9. 生成操作文章
        logger.info("生成操作文章...")
        article_generator = GenerateArticle(
            buy_sell_points, 
            ai_insights, 
            news_data,
            fund_data
        )
        article_generator.generate()

        logger.info("基金数据分析与买卖点预测系统运行完成")

    except Exception as e:
        logger.error(f"系统运行出错: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
