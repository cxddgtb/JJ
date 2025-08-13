#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金数据分析主程序
自动爬取基金数据，分析买卖点，生成操作建议文章
"""

import os
import sys
import logging
import traceback
from datetime import datetime, timedelta
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import threading
import time

# 导入自定义模块
from fund_crawler import FundCrawler
from fund_analyzer import FundAnalyzer
from article_generator import ArticleGenerator
from data_processor import DataProcessor
from utils.logger import setup_logger
from utils.config import Config

class FundAnalysisSystem:
    """基金分析系统主类"""
    
    def __init__(self):
        self.config = Config()
        self.logger = setup_logger('fund_analysis_system')
        self.crawler = FundCrawler()
        self.analyzer = FundAnalyzer()
        self.generator = ArticleGenerator()
        self.processor = DataProcessor()
        
        # 创建输出目录
        self.create_output_dirs()
        
    def create_output_dirs(self):
        """创建输出目录"""
        dirs = ['output', 'logs', 'data', 'reports', 'charts']
        for dir_name in dirs:
            os.makedirs(dir_name, exist_ok=True)
            
    def run_parallel_crawling(self):
        """并行爬取基金数据"""
        self.logger.info("开始并行爬取基金数据...")
        
        # 获取基金列表
        fund_list = self.crawler.get_fund_list()
        
        # 使用线程池并行爬取
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for fund_code in fund_list[:50]:  # 限制数量避免超时
                future = executor.submit(self.crawler.crawl_fund_data, fund_code)
                futures.append(future)
            
            # 收集结果
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=30)
                    if result:
                        results.append(result)
                except Exception as e:
                    self.logger.error(f"爬取失败: {e}")
                    
        self.logger.info(f"成功爬取 {len(results)} 只基金数据")
        return results
        
    def analyze_fund_data(self, fund_data_list):
        """分析基金数据"""
        self.logger.info("开始分析基金数据...")
        
        analysis_results = []
        
        # 使用进程池进行并行分析
        with ProcessPoolExecutor(max_workers=4) as executor:
            futures = []
            for fund_data in fund_data_list:
                future = executor.submit(self.analyzer.analyze_single_fund, fund_data)
                futures.append(future)
            
            # 收集分析结果
            for future in futures:
                try:
                    result = future.result(timeout=60)
                    if result:
                        analysis_results.append(result)
                except Exception as e:
                    self.logger.error(f"分析失败: {e}")
                    
        self.logger.info(f"完成 {len(analysis_results)} 只基金分析")
        return analysis_results
        
    def generate_market_report(self, analysis_results):
        """生成市场报告"""
        self.logger.info("生成市场分析报告...")
        
        # 生成技术分析报告
        tech_report = self.analyzer.generate_technical_report(analysis_results)
        
        # 生成买卖点建议
        trading_signals = self.analyzer.generate_trading_signals(analysis_results)
        
        # 生成操作文章
        article = self.generator.generate_article(tech_report, trading_signals)
        
        return {
            'technical_report': tech_report,
            'trading_signals': trading_signals,
            'article': article
        }
        
    def save_results(self, results, analysis_results, report):
        """保存所有结果"""
        self.logger.info("保存分析结果...")
        
        # 保存原始数据
        self.processor.save_fund_data(results, 'data/fund_data.json')
        
        # 保存分析结果
        self.processor.save_analysis_results(analysis_results, 'output/analysis_results.json')
        
        # 保存报告
        self.processor.save_report(report, 'reports/market_report.json')
        
        # 保存文章
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        article_file = f'output/fund_analysis_article_{timestamp}.md'
        with open(article_file, 'w', encoding='utf-8') as f:
            f.write(report['article'])
            
        # 生成图表
        self.analyzer.generate_charts(analysis_results, 'charts/')
        
        self.logger.info(f"结果已保存到 output/ 目录")
        
    def run(self):
        """运行完整的分析流程"""
        try:
            self.logger.info("=== 基金分析系统启动 ===")
            start_time = time.time()
            
            # 1. 并行爬取数据
            fund_data = self.run_parallel_crawling()
            if not fund_data:
                self.logger.error("未获取到基金数据，程序退出")
                return
                
            # 2. 分析数据
            analysis_results = self.analyze_fund_data(fund_data)
            if not analysis_results:
                self.logger.error("分析失败，程序退出")
                return
                
            # 3. 生成报告
            report = self.generate_market_report(analysis_results)
            
            # 4. 保存结果
            self.save_results(fund_data, analysis_results, report)
            
            # 5. 输出摘要
            end_time = time.time()
            duration = end_time - start_time
            
            self.logger.info(f"=== 分析完成 ===")
            self.logger.info(f"处理基金数量: {len(fund_data)}")
            self.logger.info(f"分析完成数量: {len(analysis_results)}")
            self.logger.info(f"总耗时: {duration:.2f} 秒")
            self.logger.info(f"文章已生成: output/fund_analysis_article_*.md")
            
        except Exception as e:
            self.logger.error(f"系统运行失败: {e}")
            self.logger.error(traceback.format_exc())
            sys.exit(1)

def main():
    """主函数"""
    system = FundAnalysisSystem()
    system.run()

if __name__ == "__main__":
    main()
