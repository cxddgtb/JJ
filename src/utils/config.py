#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置文件
"""

import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent.parent

# 数据目录
DATA_DIR = os.path.join(BASE_DIR, 'data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 输出目录
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# 日志目录
LOG_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 爬虫配置
CRAWLER_CONFIG = {
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
    'timeout': 30,
    'retry_times': 3,
    'delay': 1,  # 请求延迟(秒)
    'max_threads': 10,  # 最大线程数
}

# 新闻爬取配置
NEWS_SOURCES = [
    {
        'name': '东方财富网',
        'url': 'https://fund.eastmoney.com/news/',
        'list_selector': '.newsList li',
        'title_selector': '.title a',
        'link_selector': '.title a',
        'date_selector': '.time',
        'content_selector': '.Body'
    },
    {
        'name': '天天基金网',
        'url': 'https://fund.1234567.com.cn/news/',
        'list_selector': '.news-list li',
        'title_selector': 'a',
        'link_selector': 'a',
        'date_selector': '.date',
        'content_selector': '.article-content'
    },
    {
        'name': '新浪财经',
        'url': 'https://finance.sina.com.cn/fund/',
        'list_selector': '.ConsList li',
        'title_selector': 'a',
        'link_selector': 'a',
        'date_selector': '.time',
        'content_selector': '.article-content'
    }
]

# 基金板块配置
FUND_CATEGORIES = [
    {'name': '股票型', 'code': 'gp', 'limit': 50},
    {'name': '混合型', 'code': 'hh', 'limit': 50},
    {'name': '债券型', 'code': 'zq', 'limit': 50},
    {'name': '指数型', 'code': 'zs', 'limit': 50},
    {'name': 'QDII', 'code': 'qdii', 'limit': 30},
    {'name': '货币型', 'code': 'hb', 'limit': 20}
]

# 指标配置
INDICATORS_CONFIG = {
    'long_term': {
        'ma_periods': [30, 60, 120],  # 移动平均线周期
        'rsi_period': 14,  # RSI周期
        'macd_params': {'fast': 12, 'slow': 26, 'signal': 9}  # MACD参数
    },
    'mid_term': {
        'ma_periods': [5, 10, 20],
        'rsi_period': 9,
        'macd_params': {'fast': 6, 'slow': 13, 'signal': 5}
    },
    'short_term': {
        'ma_periods': [3, 5, 10],
        'rsi_period': 6,
        'macd_params': {'fast': 3, 'slow': 8, 'signal': 3}
    }
}

# AI分析配置
AI_CONFIG = {
    'model_name': 'bert-base-chinese',  # 使用的预训练模型
    'max_length': 512,  # 最大文本长度
    'batch_size': 16,  # 批处理大小
    'threshold': 0.7,  # 置信度阈值
}

# 买卖点分析配置
BUY_SELL_CONFIG = {
    'buy_threshold': 0.7,  # 买入信号阈值
    'sell_threshold': 0.3,  # 卖出信号阈值
    'weight': {  # 各指标权重
        'long_term': 0.4,
        'mid_term': 0.3,
        'short_term': 0.2,
        'news_sentiment': 0.1
    }
}

# 报告配置
REPORT_CONFIG = {
    'table_format': 'markdown',  # 表格格式: markdown, html, excel
    'article_template': 'default',  # 文章模板
    'include_charts': True,  # 是否包含图表
    'chart_format': 'png',  # 图表格式: png, svg, pdf
}
