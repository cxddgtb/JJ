class Config:
    OUTPUT_DIR = "output"
    LOGS_DIR = "logs"
    
    # 基金数据源
    FUND_BASE_URL = "http://fund.eastmoney.com"
    FUND_RANK_URL = f"{FUND_BASE_URL}/data/rankhandler.aspx"
    FUND_DETAIL_URL = f"{FUND_BASE_URL}/f10/F10DataApi.aspx"
    
    # 报告格式
    REPORT_FORMAT = "html"  # 使用HTML表格更灵活
    
    # 分析参数
    FUND_BUY_THRESHOLD = 0.5    # 日涨幅>0.5%视为买入信号
    FUND_SELL_THRESHOLD = -0.5   # 日涨幅<-0.5%视为卖出信号
    HISTORICAL_DAYS = 15         # 保留15天历史数据
    
    # 要跟踪的基金列表（名称, 代码）
    FUNDS_TO_TRACK = [
        ("华夏成长", "000001"),
        ("易方达消费行业", "110022"),
        ("富国天惠精选成长", "161005"),
        ("景顺长城新兴成长", "260108"),
        ("中欧医疗健康", "003095"),
        ("汇添富价值精选", "519069"),
        ("嘉实新兴产业", "000751"),
        ("南方优选成长", "202023"),
        ("工银瑞信前沿医疗", "001717"),
        ("广发稳健增长", "270002"),
        ("兴全合润混合", "163406"),
        ("招商中证白酒", "161725"),
        ("诺安成长混合", "320007"),
        ("天弘沪深300", "000961"),
        ("华安媒体互联网", "001071")
    ]

settings = Config()
