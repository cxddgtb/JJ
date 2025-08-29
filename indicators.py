# indicators.py
import numpy as np
import pandas as pd

class TongdaxinIndicators:
    @staticmethod
    def pressure_support_indicator(prices, N=20, M=32, P1=80, P2=100):
        """
        压力支撑主图指标
        参数:
          prices: 价格序列
          N, M, P1, P2: 指标参数
        """
        if len(prices) < max(N, M):
            return "观望", 0, 0
        
        # 计算VAR1
        VAR1 = (prices['close'] + prices['high'] + prices['open'] + prices['low']) / 4
        
        # 计算卖出线(压力)
       卖出 = np.mean(VAR1[-N:]) * (1 + P1/1000)
        
        # 计算买入线(支撑)
        买入 = np.mean(VAR1[-M:]) * (1 - P2/1000)
        
        # 计算当前价格
        current_price = prices['close'][-1]
        
        # 生成信号
        if current_price >= 卖出 * 0.99:
            signal = "卖"
        elif current_price <= 买入 * 1.01:
            signal = "买"
        else:
            signal = "观望"
        
        return signal, 卖出, 买入
    
    @staticmethod
    def chip_will_indicator(prices, volumes):
        """
        筹码意愿与买卖点副图指标
        """
        if len(prices) < 30:
            return "观望", 0, 0
        
        # 计算价位线
        low_10 = np.min(prices['low'][-10:])
        high_25 = np.max(prices['high'][-25:])
        
        价位线 = np.mean((prices['close'][-4:] - low_10) / (high_25 - low_10) * 4)
        
        # 生成信号
        if 价位线 < 0.3:
            signal = "买"
        elif 价位线 > 3.5:
            signal = "卖"
        else:
            signal = "观望"
        
        return signal, 价位线, 0
    
    @staticmethod
    def main_force_indicator(prices, volumes):
        """
        主力进出副图指标
        """
        if len(prices) < 33:
            return "观望", 0, 0
        
        # 计算VAR1
        VAR1 = (prices['low'][-2] + prices['open'][-2] + prices['close'][-2] + prices['high'][-2]) / 4
        
        # 计算VAR3
        abs_diff = np.abs(prices['low'][-13:] - VAR1)
        max_diff = np.maximum(prices['low'][-13:] - VAR1, 0)
        VAR2 = np.sum(abs_diff) / np.sum(max_diff) if np.sum(max_diff) > 0 else 0
        VAR3 = np.mean(VAR2) if isinstance(VAR2, np.ndarray) else VAR2
        
        # 计算VAR5
        low_33 = np.min(prices['low'][-33:])
        if prices['low'][-1] <= low_33:
            VAR5 = VAR3
        else:
            VAR5 = 0
        
        # 生成信号
        if VAR5 > 0:
            signal = "买"
        else:
            signal = "观望"
        
        return signal, VAR5, 0
    
    @staticmethod
    def calculate_all_indicators(prices, volumes):
        """计算所有指标并生成综合信号"""
        # 获取三个指标信号
        signal1, _, _ = TongdaxinIndicators.pressure_support_indicator(prices)
        signal2, _, _ = TongdaxinIndicators.chip_will_indicator(prices, volumes)
        signal3, _, _ = TongdaxinIndicators.main_force_indicator(prices, volumes)
        
        # 综合判断
        signals = [signal1, signal2, signal3]
        buy_count = signals.count("买")
        sell_count = signals.count("卖")
        
        if buy_count >= 2:
            return "买"
        elif sell_count >= 2:
            return "卖"
        else:
            return "观望"
