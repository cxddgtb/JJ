# analyzer.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_fetcher import FundDataFetcher
from indicators import TongdaxinIndicators

class FundAnalyzer:
    def __init__(self, appkey):
        self.fetcher = FundDataFetcher(appkey)
        self.indicators = TongdaxinIndicators()
    
    def analyze_fund(self, fund_code, fund_name):
        """分析单个基金的买卖点"""
        try:
            # 获取当前数据
            current_data = self.fetcher.fetch_fund_data(fund_code)
            current_price = current_data['price']
            
            # 获取历史数据（30个交易日）
            historical_data = self.fetcher.fetch_historical_data(fund_code, 30)
            
            # 准备指标计算所需的数据
            prices = {
                'open': np.array([data['price'] * (1 - random.uniform(0, 0.02)) for data in historical_data]),
                'high': np.array([data['price'] * (1 + random.uniform(0, 0.03)) for data in historical_data]),
                'low': np.array([data['price'] * (1 - random.uniform(0, 0.03)) for data in historical_data]),
                'close': np.array([data['price'] for data in historical_data])
            }
            
            # 模拟成交量数据
            volumes = np.array([random.randint(10000, 100000) for _ in range(30)])
            
            # 计算综合指标
            signal = self.indicators.calculate_all_indicators(prices, volumes)
            
            # 生成历史信号
            history_signals = []
            for i in range(15, 30):  # 最近15个交易日
                window_prices = {key: value[:i+1] for key, value in prices.items()}
                window_volumes = volumes[:i+1]
                hist_signal = self.indicators.calculate_all_indicators(window_prices, window_volumes)
                history_signals.append(hist_signal)
            
            return {
                'fund_code': fund_code,
                'fund_name': fund_name,
                'current_price': current_price,
                'signal': signal,
                'history_signals': history_signals,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            print(f"分析基金{fund_code}时出错: {str(e)}")
            return {
                'fund_code': fund_code,
                'fund_name': fund_name,
                'current_price': 0,
                'signal': "误差",
                'history_signals': [],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def analyze_all_funds(self, fund_codes):
        """分析所有基金"""
        results = []
        for code, name in fund_codes.items():
            print(f"正在分析 {name}({code})...")
            result = self.analyze_fund(code, name)
            results.append(result)
            # 避免请求过于频繁
            import time
            time.sleep(1)
        
        return results
