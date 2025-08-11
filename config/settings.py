# config/settings.py
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    # 确保 OUTPUT_DIR 定义存在
    OUTPUT_DIR = "output"
    
    # 通达信配置
    TDX_USER = os.getenv('TDX_USER', 'default_user')
    TDX_PASS = os.getenv('TDX_PASS', 'default_pass')
    TDX_API_URL = "https://api.tdx.com.cn/api/v1/market/indicator"
    
    # 基金配置
    FUND_API_KEY = os.getenv('FUND_API_KEY', 'default_api_key')
    FUND_API_URL = "https://api.fund.eastmoney.com/fund/lisifund"
    
    # 邮件配置
    EMAIL_HOST = "smtp.gmail.com"
    EMAIL_PORT = 587
    EMAIL_USER = os.getenv('EMAIL_USER', 'your_email@gmail.com')
    EMAIL_PASS = os.getenv('EMAIL_PASS', 'your_email_password')
    EMAIL_RECEIVER = os.getenv('EMAIL_RECEIVER', 'receiver@example.com')
    
    # 报告格式
    REPORT_FORMAT = "pdf"  # 可选 pdf 或 html
    
    # 分析参数
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30
    MACD_FAST_PERIOD = 12
    MACD_SLOW_PERIOD = 26
    MACD_SIGNAL_PERIOD = 9
    FUND_BUY_THRESHOLD = 0.5  # 基金涨幅超过0.5%视为买入信号
    FUND_SELL_THRESHOLD = -0.5  # 基金跌幅超过0.5%视为卖出信号
    
    # 股票代码列表
    STOCK_CODES = [
        "000001",  # 上证指数
        "399001",  # 深证成指
        "399006",  # 创业板指
        "000300",  # 沪深300
        "000016",  # 上证50
    ]

# 创建配置实例
settings = Config()
