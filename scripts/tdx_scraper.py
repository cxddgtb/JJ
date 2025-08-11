import requests
import pandas as pd
import numpy as np
import talib
import time
import random
from datetime import datetime
from bs4 import BeautifulSoup
from config import settings
from .utils import save_data, get_trading_date, setup_logging

logger = setup_logging()

class TDXDataScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Referer': 'https://www.tdx.com.cn/'
        })
        self.base_url = "https://www.tdx.com.cn"
        self.login_url = f"{self.base_url}/login"
        self.data_url = f"{self.base_url}/data"
        
    def login(self):
        """登录通达信平台（模拟登录）"""
        try:
            login_data = {
                'username': settings.TDX_USER,
                'password': settings.TDX_PASS,
                'remember': 'on'
            }
            response = self.session.post(self.login_url, data=login_data)
            if response.status_code == 200 and "登录成功" in response.text:
                logger.info("通达信登录成功")
                return True
            logger.error(f"通达信登录失败: {response.status_code}, {response.text[:200]}")
            return False
        except Exception as e:
            logger.exception("通达信登录异常")
            return False
            
    def fetch_stock_data(self, stock_code, period="daily", limit=100):
        """获取股票数据"""
        try:
            params = {
                'code': stock_code,
                'period': period,
                'limit': limit
            }
            response = self.session.get(settings.TDX_API_URL, params=params)
            
            if response.status_code != 200:
                logger.error(f"获取股票数据失败: {stock_code}, 状态码: {response.status_code}")
                return None
                
            data = response.json()
            if data['code'] != 0:
                logger.error(f"API返回错误: {data['msg']}")
                return None
                
            df = pd.DataFrame(data['data']['items'], columns=data['data']['fields'])
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # 转换数据类型
            numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'amount']
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
            
            # 计算买卖信号
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
        # 登录
        if not self.login():
            return None
            
        all_signals = {}
        trading_date = get_trading_date()
        
        for stock_code in settings.STOCK_CODES:
            logger.info(f"处理股票: {stock_code}")
            
            # 获取数据
            df = self.fetch_stock_data(stock_code)
            if df is None or df.empty:
                continue
                
            # 计算技术指标
            df = self.calculate_technical_indicators(df)
            
            # 保存原始数据
            save_data(df, f"{stock_code}_data.csv", "stock_data")
            
            # 提取最新信号
            latest = df.iloc[-1]
            signal = {
                'code': stock_code,
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
