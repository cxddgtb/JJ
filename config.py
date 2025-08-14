import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# GitHub配置
GITHUB_TOKEN = os.getenv("REPO_ACCESS_TOKEN")
REPO_OWNER = os.getenv("REPO_OWNER", "your_username")
REPO_NAME = os.getenv("REPO_NAME", "fund_analysis")

# 数据库配置（如果需要）
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "fund_data")

# 爬虫配置
CRAWL_DELAY = 1  # 爬取延迟，单位秒
MAX_RETRIES = 3  # 最大重试次数
TIMEOUT = 30  # 请求超时时间，单位秒
CONCURRENT_REQUESTS = 10  # 并发请求数
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:96.0) Gecko/20100101 Firefox/96.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Safari/605.1.15",
]

# 目标网站配置
TARGET_SITES = {
    "天天基金": "https://fund.eastmoney.com/",
    "新浪财经": "https://finance.sina.com.cn/fund/",
    "腾讯财经": "https://finance.qq.com/fund/",
    "网易财经": "https://money.163.com/fund/",
    "和讯基金": "https://funds.hexun.com/",
    "金融界基金": "https://fund.jrj.com.cn/",
    "中证网": "https://www.cs.com.cn/fund/",
    "证券时报": "https://fund.stcn.com/",
    "中国基金网": "https://www.cnfund.cn/",
    "晨星网": "https://www.morningstar.cn/",
}

# 基金类型配置
FUND_TYPES = {
    "股票型": "stock",
    "债券型": "bond",
    "混合型": "hybrid",
    "货币型": "money",
    "指数型": "index",
    "QDII": "qdii",
    "FOF": "fof",
}

# 分析参数配置
ANALYSIS_PARAMS = {
    "SHORT_TERM_MA": 5,  # 短期移动平均线天数
    "MID_TERM_MA": 20,  # 中期移动平均线天数
    "LONG_TERM_MA": 60,  # 长期移动平均线天数
    "RSI_PERIOD": 14,  # RSI计算周期
    "RSI_OVERBOUGHT": 70,  # RSI超买线
    "RSI_OVERSOLD": 30,  # RSI超卖线
    "MACD_FAST": 12,  # MACD快线周期
    "MACD_SLOW": 26,  # MACD慢线周期
    "MACD_SIGNAL": 9,  # MACD信号线周期
    "BOLLINGER_PERIOD": 20,  # 布林带周期
    "BOLLINGER_STD_DEV": 2,  # 布林带标准差倍数
}

# 报告生成配置
REPORT_CONFIG = {
    "OUTPUT_DIR": "reports",  # 报告输出目录
    "TEMPLATE_DIR": "templates",  # 模板目录
    "STATIC_DIR": "static",  # 静态资源目录
    "REPORT_FORMAT": "markdown",  # 报告格式，可选：markdown, html, pdf
    "INCLUDE_CHARTS": True,  # 是否包含图表
    "CHART_FORMAT": "png",  # 图表格式
    "MAX_FUNDS_IN_REPORT": 20,  # 报告中包含的最大基金数量
}

# 日志配置
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
        },
        "file": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.FileHandler",
            "filename": "fund_analysis.log",
            "mode": "a",
        },
    },
    "loggers": {
        "": {
            "handlers": ["default", "file"],
            "level": "INFO",
            "propagate": True
        }
    }
}
