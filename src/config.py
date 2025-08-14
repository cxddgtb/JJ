"""
配置文件 - 基金数据爬取与分析系统
"""
import os
from datetime import datetime, timedelta

# GitHub配置
GITHUB_TOKEN = os.getenv('REPO_ACCESS_TOKEN', '')
GITHUB_REPO = os.getenv('GITHUB_REPOSITORY', '')

# 数据源配置
DATA_SOURCES = {
    'eastmoney': {
        'fund_list': 'http://fund.eastmoney.com/js/fundcode_search.js',
        'fund_detail': 'http://fundgz.1234567.com.cn/js/{}.js',
        'fund_net': 'https://api.fund.eastmoney.com/f10/lsjz',
        'fund_news': 'https://fund.eastmoney.com/news/1593,1594,1595.html',
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://fund.eastmoney.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
    },
    'tiantian': {
        'fund_ranking': 'https://fund.eastmoney.com/data/rankingdisplay.html',
        'fund_manager': 'https://fund.eastmoney.com/manager/',
    },
    'sina': {
        'fund_news': 'https://finance.sina.com.cn/fund/',
        'market_news': 'https://finance.sina.com.cn/stock/'
    },
    '163': {
        'fund_news': 'https://money.163.com/fund/',
        'economic_news': 'https://money.163.com/'
    },
    'snowball': {
        'fund_discuss': 'https://xueqiu.com/k?q=基金',
        'market_sentiment': 'https://xueqiu.com/today'
    }
}

# 爬虫配置
CRAWLER_CONFIG = {
    'max_workers': 20,  # 最大线程数
    'request_delay': (0.5, 2.0),  # 请求延迟范围(秒)
    'retry_times': 3,  # 重试次数
    'timeout': 30,  # 超时时间(秒)
    'enable_proxy': True,  # 是否启用代理
    'proxy_pool_size': 10,  # 代理池大小
}

# 分析配置
ANALYSIS_CONFIG = {
    'technical_indicators': [
        'SMA_5', 'SMA_10', 'SMA_20', 'SMA_60',  # 简单移动平均
        'EMA_12', 'EMA_26',  # 指数移动平均
        'MACD', 'MACD_signal', 'MACD_hist',  # MACD指标
        'RSI_14',  # 相对强弱指数
        'BOLL_upper', 'BOLL_middle', 'BOLL_lower',  # 布林带
        'KDJ_K', 'KDJ_D', 'KDJ_J',  # KDJ指标
        'CCI',  # 商品通道指数
        'WR',  # 威廉指标
    ],
    'fundamental_factors': [
        'pe_ratio', 'pb_ratio', 'dividend_yield',  # 基本面指标
        'fund_size', 'fund_age', 'manager_experience',  # 基金基本信息
        'turnover_rate', 'expense_ratio', 'management_fee',  # 费用相关
        'sharpe_ratio', 'max_drawdown', 'volatility',  # 风险指标
    ],
    'market_sentiment': [
        'news_sentiment', 'social_sentiment', 'institutional_sentiment',
        'market_fear_greed', 'vix_index', 'margin_trading'
    ],
    'economic_indicators': [
        'gdp_growth', 'cpi', 'ppi', 'pmi',
        'interest_rate', 'exchange_rate', 'commodity_price'
    ]
}

# 买卖信号配置
SIGNAL_CONFIG = {
    'buy_signals': {
        'strong_buy': {'score_threshold': 80, 'confidence': 0.9},
        'buy': {'score_threshold': 60, 'confidence': 0.7},
        'weak_buy': {'score_threshold': 40, 'confidence': 0.5}
    },
    'sell_signals': {
        'strong_sell': {'score_threshold': 20, 'confidence': 0.9},
        'sell': {'score_threshold': 40, 'confidence': 0.7},
        'weak_sell': {'score_threshold': 60, 'confidence': 0.5}
    },
    'hold_threshold': {'min_score': 35, 'max_score': 65}
}

# 文章生成配置
ARTICLE_CONFIG = {
    'template_path': 'templates/',
    'output_path': 'reports/',
    'include_charts': True,
    'chart_types': ['line', 'candlestick', 'volume', 'indicator'],
    'languages': ['zh-CN'],
    'formats': ['markdown', 'html', 'pdf'],
    'auto_translate': False
}

# 通知配置
NOTIFICATION_CONFIG = {
    'telegram': {
        'enabled': False,
        'bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
        'chat_id': os.getenv('TELEGRAM_CHAT_ID', '')
    },
    'email': {
        'enabled': False,
        'smtp_server': os.getenv('EMAIL_SMTP_SERVER', ''),
        'smtp_port': int(os.getenv('EMAIL_SMTP_PORT', 587)),
        'username': os.getenv('EMAIL_USERNAME', ''),
        'password': os.getenv('EMAIL_PASSWORD', ''),
        'recipients': os.getenv('EMAIL_RECIPIENTS', '').split(',')
    },
    'webhook': {
        'enabled': False,
        'url': os.getenv('WEBHOOK_URL', ''),
        'headers': {}
    }
}

# 数据存储配置
STORAGE_CONFIG = {
    'local': {
        'data_dir': 'data/',
        'cache_dir': 'cache/',
        'log_dir': 'logs/',
        'backup_dir': 'backup/'
    },
    'database': {
        'enabled': False,
        'type': 'sqlite',  # sqlite, mysql, postgresql
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'fund_analysis'),
        'username': os.getenv('DB_USERNAME', ''),
        'password': os.getenv('DB_PASSWORD', '')
    },
    'redis': {
        'enabled': False,
        'host': os.getenv('REDIS_HOST', 'localhost'),
        'port': int(os.getenv('REDIS_PORT', 6379)),
        'password': os.getenv('REDIS_PASSWORD', ''),
        'db': int(os.getenv('REDIS_DB', 0))
    }
}

# 日志配置
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_handler': {
        'enabled': True,
        'filename': 'logs/fund_analysis.log',
        'max_bytes': 10 * 1024 * 1024,  # 10MB
        'backup_count': 5
    },
    'console_handler': {
        'enabled': True
    }
}

# 性能配置
PERFORMANCE_CONFIG = {
    'memory_limit': 2048,  # MB
    'cpu_cores': os.cpu_count() or 4,
    'cache_size': 1024,  # MB
    'batch_size': 100,
    'chunk_size': 1000
}

# 安全配置
SECURITY_CONFIG = {
    'rate_limiting': {
        'enabled': True,
        'requests_per_minute': 60,
        'requests_per_hour': 1000
    },
    'user_agents': [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
    ],
    'proxy_sources': [
        'https://www.proxy-list.download/api/v1/get?type=http',
        'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
        'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt'
    ]
}

# 基金类型配置
FUND_TYPES = {
    'equity': {
        'name': '股票型基金',
        'codes': ['001', '002', '003', '004', '005', '006'],
        'risk_level': 'high',
        'analysis_weight': {
            'technical': 0.4,
            'fundamental': 0.3,
            'market_sentiment': 0.2,
            'economic': 0.1
        }
    },
    'bond': {
        'name': '债券型基金',
        'codes': ['051', '052', '053'],
        'risk_level': 'low',
        'analysis_weight': {
            'technical': 0.2,
            'fundamental': 0.4,
            'market_sentiment': 0.1,
            'economic': 0.3
        }
    },
    'hybrid': {
        'name': '混合型基金',
        'codes': ['161', '162', '163', '164', '165', '166', '167', '168', '169'],
        'risk_level': 'medium',
        'analysis_weight': {
            'technical': 0.35,
            'fundamental': 0.35,
            'market_sentiment': 0.2,
            'economic': 0.1
        }
    },
    'index': {
        'name': '指数型基金',
        'codes': ['510', '511', '512', '513', '515', '516', '518', '159'],
        'risk_level': 'medium',
        'analysis_weight': {
            'technical': 0.5,
            'fundamental': 0.2,
            'market_sentiment': 0.2,
            'economic': 0.1
        }
    },
    'money_market': {
        'name': '货币市场基金',
        'codes': ['511', '519'],
        'risk_level': 'very_low',
        'analysis_weight': {
            'technical': 0.1,
            'fundamental': 0.3,
            'market_sentiment': 0.1,
            'economic': 0.5
        }
    }
}

# 时间配置
TIME_CONFIG = {
    'trading_hours': {
        'start': '09:30',
        'end': '15:00',
        'lunch_break': ('11:30', '13:00')
    },
    'analysis_frequency': {
        'realtime': 300,  # 5分钟
        'daily': 3600,  # 1小时
        'weekly': 86400,  # 1天
        'monthly': 604800  # 1周
    },
    'data_retention': {
        'raw_data': 90,  # 天
        'processed_data': 365,  # 天
        'reports': 1095,  # 天
        'logs': 30  # 天
    }
}

# 默认基金列表（热门基金）
DEFAULT_FUNDS = [
    '000001',  # 华夏成长
    '110022',  # 易方达消费行业
    '161725',  # 招商中证白酒指数
    '320007',  # 诺安成长
    '519674',  # 银河创新成长
    '000248',  # 汇添富消费行业
    '163402',  # 兴全趋势投资
    '110003',  # 易方达上证50指数
    '100032',  # 富国中证红利指数增强
    '000011',  # 华夏大盘精选
]

# API配置
API_CONFIG = {
    'timeout': 30,
    'max_retries': 3,
    'backoff_factor': 2,
    'status_forcelist': [500, 502, 503, 504],
    'session_pool_connections': 10,
    'session_pool_maxsize': 10
}
