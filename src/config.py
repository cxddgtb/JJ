import os
import yaml
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 基础配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, 'outputs')
RAW_DATA_DIR = os.path.join(OUTPUT_DIR, 'raw_data')
PROCESSED_DATA_DIR = os.path.join(OUTPUT_DIR, 'processed_data')
ANALYSIS_RESULTS_DIR = os.path.join(OUTPUT_DIR, 'analysis_results')
ARTICLES_DIR = os.path.join(OUTPUT_DIR, 'articles')

# 确保目录存在
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
os.makedirs(ANALYSIS_RESULTS_DIR, exist_ok=True)
os.makedirs(ARTICLES_DIR, exist_ok=True)

# API配置
API_CONFIG = {
    'tushare': {
        'token': os.getenv('TUSHARE_TOKEN', ''),
        'timeout': 30
    },
    'akshare': {
        'timeout': 30
    },
    'jqdata': {
        'username': os.getenv('JQDATA_USERNAME', ''),
        'password': os.getenv('JQDATA_PASSWORD', ''),
        'timeout': 30
    },
    'baostock': {
        'timeout': 30
    },
    'free_apis': {
        'timeout': 30
    }
}

# 新闻搜索配置
NEWS_CONFIG = {
    'engines': {
        'baidu': {
            'url': 'https://www.baidu.com/s',
            'params': {
                'wd': '{keyword}',
                'tn': 'news',
                'ch': 'ten',
                'bsst': '1',
                'cl': '2',
                'fr=search',
                'pn': '{page}',
                'rn': '10'
            },
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        },
        'google': {
            'url': 'https://www.google.com/search',
            'params': {
                'q': '{keyword}',
                'tbm': 'nws',
                'start': '{page}'
            },
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        },
        'bing': {
            'url': 'https://www.bing.com/news/search',
            'params': {
                'q': '{keyword}',
                'first': '{page}'
            },
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        },
        'sogou': {
            'url': 'https://www.sogou.com/news',
            'params': {
                'query': '{keyword}',
                'page': '{page}',
                'p': '{page}'
            },
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        },
        '360': {
            'url': 'https://news.so.com/news',
            'params': {
                'q': '{keyword}',
                'pn': '{page}'
            },
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        }
    },
    'keywords': [
        '基金', '股票型基金', '债券型基金', '货币基金', '混合型基金', 'QDII基金',
        '基金净值', '基金分红', '基金定投', '基金投资', '基金分析', '基金评级',
        '基金买入', '基金卖出', '基金持仓', '基金经理', '基金公司'
    ],
    'max_pages': 10,
    'max_news_per_engine': 20
}

# 浏览器配置
BROWSER_CONFIG = {
    'chrome': {
        'executable_path': os.path.join(BASE_DIR, 'drivers', 'chromedriver.exe'),
        'options': [
            '--headless',
            '--disable-gpu',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-images',
            '--disable-javascript'
        ]
    },
    'firefox': {
        'executable_path': os.path.join(BASE_DIR, 'drivers', 'geckodriver.exe'),
        'options': [
            '--headless'
        ]
    }
}

# AI配置
AI_CONFIG = {
    'openai': {
        'api_key': os.getenv('OPENAI_API_KEY', ''),
        'model': 'text-davinci-003',
        'temperature': 0.7,
        'max_tokens': 2000
    },
    'baidu': {
        'api_key': os.getenv('BAIDU_API_KEY', ''),
        'secret_key': os.getenv('BAIDU_SECRET_KEY', ''),
        'model': 'ERNIE-Bot'
    },
    'default_model': 'openai'
}

# 基金类型配置
FUND_TYPES = {
    'mixed': {
        'name': '混合型基金',
        'description': '同时投资于股票、债券等多种资产，风险和收益介于股票型和债券型基金之间'
    },
    'stock': {
        'name': '股票型基金',
        'description': '主要投资于股票市场，高风险高收益'
    },
    'bond': {
        'name': '债券型基金',
        'description': '主要投资于债券市场，风险较低，收益相对稳定'
    },
    'money_market': {
        'name': '货币市场基金',
        'description': '投资于短期货币市场工具，风险极低，流动性好'
    },
    'qdii': {
        'name': 'QDII基金',
        'description': '投资于海外市场，分散地域风险'
    }
}

# 分析指标配置
INDICATORS_CONFIG = {
    'technical': [
        'MA', 'EMA', 'MACD', 'RSI', 'KDJ', 'BOLL', 'WR', 'CCI', 'DMI', 'OBV'
    ],
    'fundamental': [
        'NAV', 'YTD', '1Y', '3Y', '5Y', 'Sharpe', 'Sortino', 'Alpha', 'Beta', 'Information_Ratio'
    ],
    'volume': [
        'Volume', 'Turnover_Rate', 'Amount_Change', 'Volume_Change'
    ]
}

# 文章生成配置
ARTICLE_CONFIG = {
    'template_file': os.path.join(BASE_DIR, 'templates', 'article_template.txt'),
    'analysis_prompt_file': os.path.join(BASE_DIR, 'templates', 'analysis_prompt.txt'),
    'max_length': 3000,
    'sections': [
        '市场概况',
        '基金表现',
        '技术分析',
        '基本面分析',
        '新闻影响',
        '买入/卖出建议',
        '风险提示'
    ]
}

# 日志配置
LOG_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s | %(levelname)s | %(module)s | %(message)s',
    'file': os.path.join(BASE_DIR, 'logs', 'fund_analysis.log')
}

# 确保日志目录存在
log_dir = os.path.dirname(LOG_CONFIG['file'])
os.makedirs(log_dir, exist_ok=True)
