import requests
import pandas as pd
import json
import time
import random
from datetime import datetime
from config import settings
from .utils import save_data, get_trading_date, setup_logging

logger = setup_logging()

class FundDataScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Referer': 'https://fund.eastmoney.com/',
            'Cookie': f'FundAPIKey={settings.FUND_API_KEY}'
        })
        self.base_url = "https://api.fund.eastmoney.com"
        
    def fetch_fund_list(self, page=1, page_size=100):
        """获取基金列表"""
        url = f"{self.base_url}/fund/fundmainlist"
        params = {
            'op': 'ph',
            'dt': 'kf',
            'ft': 'all',
            'rs': '',
            'gs': '0',
            'sc': 'jnzf',
            'st': 'desc',
            'sd': datetime.now().strftime('%Y-%m-%d'),
            'ed': datetime.now().strftime('%Y-%m-%d'),
            'qdii': '',
            'pi': page,
            'pn': page_size,
            'dx': '1'
        }
        
        try:
            response = self.session.get(url, params=params)
            if response.status_code != 200:
                logger.error(f"获取基金列表失败: {response.status_code}")
                return None
                
            data = response.json()
            if data['errno'] != 0:
                logger.error(f"API返回错误: {data['errmsg']}")
                return None
                
            return data['data']
        except Exception as e:
            logger.exception("获取基金列表异常")
            return None
            
    def fetch_fund_detail(self, fund_code):
        """获取基金详情"""
        url = f"{self.base_url}/fund/fundnetvalue"
        params = {
            'fundCode': fund_code,
            'pageIndex': 1,
            'pageSize': 30,
            'startDate': '',
            'endDate': datetime.now().strftime('%Y-%m-%d'),
            'sort': 'date',
            'order': 'desc'
        }
        
        try:
            response = self.session.get(url, params=params)
            if response.status_code != 200:
                logger.error(f"获取基金详情失败: {fund_code}, {response.status_code}")
                return None
                
            data = response.json()
            if data['errno'] != 0:
                logger.error(f"API返回错误: {data['errmsg']}")
                return None
                
            return data['data']
        except Exception as e:
            logger.exception(f"获取基金详情异常: {fund_code}")
            return None
            
    def analyze_fund_signals(self, fund_data):
        """分析基金买卖信号"""
        signals = []
        
        if not fund_data or 'netValueList' not in fund_data or not fund_data['netValueList']:
            return signals
            
        df = pd.DataFrame(fund_data['netValueList'])
        
        # 转换数据类型
        df['date'] = pd.to_datetime(df['date'])
        df['netValue'] = pd.to_numeric(df['netValue'], errors='coerce')
        df['dailyReturn'] = pd.to_numeric(df['dailyReturn'], errors='coerce')
        
        # 计算短期和长期均值
        df['short_ma'] = df['netValue'].rolling(window=5).mean()
        df['long_ma'] = df['netValue'].rolling(window=20).mean()
        
        # 生成信号
        latest = df.iloc[0]
        prev = df.iloc[1] if len(df) > 1 else latest
        
        signal = {
            'code': fund_data['fundCode'],
            'name': fund_data['fundName'],
            'date': latest['date'].strftime('%Y-%m-%d'),
            'net_value': latest['netValue'],
            'daily_return': latest['dailyReturn'],
            'short_ma': latest['short_ma'],
            'long_ma': latest['long_ma'],
            'signal': 0,  # 0: 观望, 1: 买入, -1: 卖出
            'signal_reason': []
        }
        
        # 基于涨跌幅的信号
        if latest['dailyReturn'] > settings.FUND_BUY_THRESHOLD:
            signal['signal'] = 1
            signal['signal_reason'].append(f"单日涨幅{latest['dailyReturn']:.2f}%")
            
        elif latest['dailyReturn'] < settings.FUND_SELL_THRESHOLD:
            signal['signal'] = -1
            signal['signal_reason'].append(f"单日跌幅{abs(latest['dailyReturn']):.2f}%")
            
        # 基于均线的信号
        if signal['signal'] == 0:
            if latest['short_ma'] > latest['long_ma'] and prev['short_ma'] <= prev['long_ma']:
                signal['signal'] = 1
                signal['signal_reason'].append("短期均线上穿长期均线")
                
            elif latest['short_ma'] < latest['long_ma'] and prev['short_ma'] >= prev['long_ma']:
                signal['signal'] = -1
                signal['signal_reason'].append("短期均线下穿长期均线")
                
        signals.append(signal)
        return signals
        
    def run(self, max_funds=50):
        """执行基金数据爬取和分析"""
        logger.info("开始爬取基金数据")
        fund_list = self.fetch_fund_list(page_size=max_funds)
        if not fund_list:
            return None
            
        all_signals = []
        trading_date = get_trading_date()
        
        for fund in fund_list['datas']:
            fund_code = fund[0]
            fund_name = fund[1]
            logger.info(f"处理基金: {fund_name}({fund_code})")
            
            # 获取基金详情
            fund_data = self.fetch_fund_detail(fund_code)
            if not fund_data:
                continue
                
            # 分析买卖信号
            signals = self.analyze_fund_signals(fund_data)
            all_signals.extend(signals)
            
            # 保存原始数据
            save_data(fund_data, f"{fund_code}_data.json", "fund_data")
            
            time.sleep(random.uniform(0.5, 2))  # 随机延迟避免被封
            
        # 保存信号数据
        save_data(all_signals, "fund_signals.json")
        logger.info(f"完成基金信号分析，共处理 {len(all_signals)} 只基金")
        return all_signals
