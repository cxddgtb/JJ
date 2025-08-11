import requests
import pandas as pd
import numpy as np
import talib
import time
import random
import json
from datetime import datetime, timedelta
from scripts.utils import save_data, get_trading_date, setup_logging
from config.settings import settings

logger = setup_logging()

class StockDataScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Referer': 'https://finance.sina.com.cn/'
        })
    
    def fetch_stock_data(self, stock_code, period=240, count=100):
        """从新浪财经获取股票数据"""
        try:
            params = {
                'symbol': stock_code,
                'scale': period,  # 240表示日线
                'datalen': count,
                'ma': 'no'
            }
            
            response = self.session.get(settings.STOCK_API_URL, params=params)
            if response.status_code != 200:
                logger.error(f"获取股票数据失败: {stock_code}, 状态码: {response.status_code}")
                return None
                
            # 新浪返回的是JSONP格式，需要清理
            data_str = response.text.strip()
            if data_str.startswith('(') and data_str.endswith(')'):
                data_str = data_str[1:-1]
                
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                logger.error(f"解析股票数据失败: {stock_code}")
                return None
                
            # 转换为DataFrame
            df = pd.DataFrame(data)
            if df.empty:
                return None
                
            # 重命名列
            df.rename(columns={
                'day': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            }, inplace=True)
            
            # 转换数据类型
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
            return df
        except Exception as e:
            logger.exception(f"获取股票数据异常: {stock_code}")
            return None
            
    def calculate_technical_indicators(self, df):
        """计算技术指标"""
        try:
            # 计算RSI
            df['RSI'] = talib.RSI(df['close'], timeperiod=14)
            
            # 计算MACD
            df['MACD'], df['MACD_signal'], df['MACD_hist'] = talib.MACD(
                df['close'], 
                fastperiod=settings.MACD_FAST_PERIOD,
                slowperiod=settings.MACD_SLOW_PERIOD,
                signalperiod=settings.MACD_SIGNAL_PERIOD
            )
            
            # 计算布林带
            df['BB_upper'], df['BB_middle'], df['BB_lower'] = talib.BBANDS(
                df['close'], timeperiod=20
            )
            
            # 计算KDJ
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            
            slowk, slowd = talib.STOCH(high, low, close, 
                                      fastk_period=9, 
                                      slowk_period=3, 
                                      slowk_matype=0, 
                                      slowd_period=3, 
                                      slowd_matype=0)
            df['K'] = slowk
            df['D'] = slowd
            df['J'] = 3 * df['K'] - 2 * df['D']
            
            # 生成买卖信号
            df['signal'] = 0  # 0: 观望, 1: 买入, -1: 卖出
            
            # RSI超卖 + MACD金叉
            rsi_buy_condition = (df['RSI'] < settings.RSI_OVERSOLD) & (df['MACD'] > df['MACD_signal'])
            df.loc[rsi_buy_condition, 'signal'] = 1
            
            # RSI超买 + MACD死叉
            rsi_sell_condition = (df['RSI'] > settings.RSI_OVERBOUGHT) & (df['MACD'] < df['MACD_signal'])
            df.loc[rsi_sell_condition, 'signal'] = -1
            
            # KDJ金叉
            kdj_buy_condition = (df['K'] > df['D']) & (df['K'].shift(1) <= df['D'].shift(1))
            df.loc[kdj_buy_condition, 'signal'] = 1
            
            # KDJ死叉
            kdj_sell_condition = (df['K'] < df['D']) & (df['K'].shift(1) >= df['D'].shift(1))
            df.loc[kdj_sell_condition, 'signal'] = -1
            
            return df
        except Exception as e:
            logger.exception("计算技术指标异常")
            return df
            
    def run(self):
        """执行数据爬取和分析"""
        all_signals = {}
        trading_date = get_trading_date()
        
        for stock_code, stock_name in settings.STOCK_CODES.items():
            logger.info(f"处理股票: {stock_name}({stock_code})")
            
            # 获取数据
            df = self.fetch_stock_data(stock_code)
            if df is None or df.empty:
                logger.warning(f"未获取到股票数据: {stock_code}")
                continue
                
            # 计算技术指标
            df = self.calculate_technical_indicators(df)
            
            # 保存原始数据
            save_data(df, f"{stock_code}_data.csv", "stock_data")
            
            # 提取最新信号
            latest = df.iloc[-1]
            signal = {
                'code': stock_code,
                'name': stock_name,
                'date': trading_date,
                'close': latest['close'],
                'rsi': latest['RSI'],
                'macd': latest['MACD'],
                'macd_signal': latest['MACD_signal'],
                'macd_hist': latest['MACD_hist'],
                'k': latest['K'],
                'd': latest['D'],
                'j': latest['J'],
                'signal': latest['signal'],
                'signal_reason': []
            }
            
            # 解释信号原因
            if signal['signal'] == 1:
                if signal['rsi'] < settings.RSI_OVERSOLD:
                    signal['signal_reason'].append("RSI超卖")
                if signal['macd_hist'] > 0 and latest['MACD_hist'] > df['MACD_hist'].shift(1).iloc[-1]:
                    signal['signal_reason'].append("MACD柱状线上升")
                if signal['k'] > signal['d']:
                    signal['signal_reason'].append("KDJ金叉")
                    
            elif signal['signal'] == -1:
                if signal['rsi'] > settings.RSI_OVERBOUGHT:
                    signal['signal_reason'].append("RSI超买")
                if signal['macd_hist'] < 0 and latest['MACD_hist'] < df['MACD_hist'].shift(1).iloc[-1]:
                    signal['signal_reason'].append("MACD柱状线下降")
                if signal['k'] < signal['d']:
                    signal['signal_reason'].append("KDJ死叉")
            
            all_signals[stock_code] = signal
            time.sleep(random.uniform(1, 3))  # 随机延迟避免被封
            
        # 保存信号数据
        save_data(all_signals, "stock_signals.json")
        logger.info(f"完成股票信号分析，共处理 {len(all_signals)} 只股票")
        return all_signals
