#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金分析系统测试脚本
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime

def test_imports():
    """测试模块导入"""
    print("测试模块导入...")
    
    try:
        from fund_crawler import FundCrawler
        from fund_analyzer import FundAnalyzer
        from article_generator import ArticleGenerator
        from data_processor import DataProcessor
        from utils.logger import setup_logger
        from utils.config import Config
        print("✓ 所有模块导入成功")
        return True
    except ImportError as e:
        print(f"✗ 模块导入失败: {e}")
        return False

def test_config():
    """测试配置管理"""
    print("测试配置管理...")
    
    try:
        from utils.config import Config
        config = Config()
        
        # 测试基本配置
        max_workers = config.get('max_workers', 10)
        timeout = config.get('timeout', 300)
        
        print(f"✓ 配置加载成功 - 最大工作线程: {max_workers}, 超时时间: {timeout}秒")
        return True
    except Exception as e:
        print(f"✗ 配置测试失败: {e}")
        return False

def test_logger():
    """测试日志系统"""
    print("测试日志系统...")
    
    try:
        from utils.logger import setup_logger
        logger = setup_logger('test_logger')
        logger.info("测试日志消息")
        print("✓ 日志系统测试成功")
        return True
    except Exception as e:
        print(f"✗ 日志系统测试失败: {e}")
        return False

def test_crawler():
    """测试爬虫模块"""
    print("测试爬虫模块...")
    
    try:
        from fund_crawler import FundCrawler
        crawler = FundCrawler()
        
        # 测试获取基金列表
        fund_list = crawler.get_fund_list()
        if fund_list and len(fund_list) > 0:
            print(f"✓ 爬虫测试成功 - 获取到 {len(fund_list)} 只基金")
            return True
        else:
            print("✗ 爬虫测试失败 - 未获取到基金列表")
            return False
    except Exception as e:
        print(f"✗ 爬虫测试失败: {e}")
        return False

def test_analyzer():
    """测试分析器模块"""
    print("测试分析器模块...")
    
    try:
        from fund_analyzer import FundAnalyzer
        analyzer = FundAnalyzer()
        
        # 创建测试数据
        test_data = {
            'fund_code': '000001',
            'fund_info': {'fund_name': '测试基金'},
            'nav_data': [
                {'净值日期': '2024-01-01', '累计净值': 1.0},
                {'净值日期': '2024-01-02', '累计净值': 1.01},
                {'净值日期': '2024-01-03', '累计净值': 1.02}
            ]
        }
        
        # 测试分析功能
        result = analyzer.analyze_single_fund(test_data)
        if result:
            print("✓ 分析器测试成功")
            return True
        else:
            print("✗ 分析器测试失败 - 分析结果为空")
            return False
    except Exception as e:
        print(f"✗ 分析器测试失败: {e}")
        return False

def test_article_generator():
    """测试文章生成器"""
    print("测试文章生成器...")
    
    try:
        from article_generator import ArticleGenerator
        generator = ArticleGenerator()
        
        # 创建测试数据
        test_report = {
            'summary': {
                'total_funds': 10,
                'buy_signals': 3,
                'sell_signals': 2,
                'buy_ratio': 0.3,
                'sell_ratio': 0.2,
                'avg_score': 75.5
            },
            'market_sentiment': '乐观'
        }
        
        test_signals = {
            'buy': [
                {
                    'fund_code': '000001',
                    'fund_name': '测试基金1',
                    'score': 85.0,
                    'reasons': ['技术指标良好', '趋势向上']
                }
            ],
            'sell': []
        }
        
        # 测试文章生成
        article = generator.generate_article(test_report, test_signals)
        if article and len(article) > 100:
            print("✓ 文章生成器测试成功")
            return True
        else:
            print("✗ 文章生成器测试失败 - 生成的文章过短")
            return False
    except Exception as e:
        print(f"✗ 文章生成器测试失败: {e}")
        return False

def test_data_processor():
    """测试数据处理器"""
    print("测试数据处理器...")
    
    try:
        from data_processor import DataProcessor
        processor = DataProcessor()
        
        # 创建测试数据
        test_fund_data = [
            {
                'fund_code': '000001',
                'fund_info': {'fund_name': '测试基金1'},
                'nav_data': [{'净值日期': '2024-01-01', '累计净值': 1.0}]
            }
        ]
        
        test_analysis_results = [
            {
                'fund_code': '000001',
                'fund_info': {'fund_name': '测试基金1'},
                'overall_score': 85.0,
                'trading_signals': {'current_signal': 'buy', 'signal_strength': 2.5}
            }
        ]
        
        # 测试数据格式化
        fund_df = processor.format_fund_data_for_excel(test_fund_data)
        analysis_df = processor.format_analysis_results_for_excel(test_analysis_results)
        
        if not fund_df.empty and not analysis_df.empty:
            print("✓ 数据处理器测试成功")
            return True
        else:
            print("✗ 数据处理器测试失败 - 格式化结果为空")
            return False
    except Exception as e:
        print(f"✗ 数据处理器测试失败: {e}")
        return False

def test_directories():
    """测试目录创建"""
    print("测试目录创建...")
    
    try:
        directories = ['output', 'logs', 'data', 'reports', 'charts', 'config']
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        # 检查目录是否存在
        for directory in directories:
            if not os.path.exists(directory):
                print(f"✗ 目录创建失败: {directory}")
                return False
        
        print("✓ 目录创建测试成功")
        return True
    except Exception as e:
        print(f"✗ 目录创建测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("="*50)
    print("基金分析系统测试")
    print("="*50)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    tests = [
        ("模块导入", test_imports),
        ("配置管理", test_config),
        ("日志系统", test_logger),
        ("爬虫模块", test_crawler),
        ("分析器模块", test_analyzer),
        ("文章生成器", test_article_generator),
        ("数据处理器", test_data_processor),
        ("目录创建", test_directories)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"  {test_name} 测试失败")
    
    print("\n" + "="*50)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("✓ 所有测试通过！系统可以正常运行。")
        return True
    else:
        print("✗ 部分测试失败，请检查相关模块。")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
