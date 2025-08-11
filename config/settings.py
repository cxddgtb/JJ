class Config:
    OUTPUT_DIR = "output"
    LOGS_DIR = "logs"
    
    # 股票数据源 - 新浪财经
    STOCK_API_URL = "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData"
    
    # 基金数据源 - 天天基金网
    FUND_BASE_URL = "http://fund.eastmoney.com"
    FUND_RANK_URL = "http://fund.eastmoney.com/data/rankhandler.aspx"
    
    # 报告格式
    REPORT_FORMAT = "pdf"
    
    # 分析参数
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30
    MACD_FAST_PERIOD = 12
    MACD_SLOW_PERIOD = 26
    MACD_SIGNAL_PERIOD = 9
    FUND_BUY_THRESHOLD = 0.5
    FUND_SELL_THRESHOLD = -0.5
    
    # 股票代码列表 (新浪格式)
    STOCK_CODES = {
        "sh000001": "上证指数",
        "sz399001": "深证成指",
        "sz399006": "创业板指",
        "sh000300": "沪深300",
        "sh000016": "上证50"
    }

settings = Config()
