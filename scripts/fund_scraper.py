import requests
import pandas as pd
import json
import re
import time
import random
from datetime import datetime
from bs4 import BeautifulSoup
from scripts.utils import save_data, get_trading_date, setup_logging
from config.settings import settings

logger = setup_logging()

class FundDataScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Referer': settings.FUND_BASE_URL
        })
        
    def fetch_fund_list(self, page=1, page_size=100):
        """获取基金列表"""
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
            'pi': str(page),
            'pn': str(page_size),
            'dx': '1'
        }
        
        try:
            response = self.session.get(settings.FUND_RANK_URL, params=params)
            if response.status_code != 200:
                logger.error(f"获取基金列表失败: {response.status_code}")
                return None
                
            # 解析特殊格式
            content = response.text
            match = re.search(r'var rankData = (.*);', content)
            if not match:
                logger.error("基金列表数据格式异常")
                return None
                
            json_str = match.group(1)
            data = json.loads(json_str)
            
            return {
                'datas': data['datas'],
                'allCount': data['allCount']
            }
        except Exception as e:
            logger.exception("获取基金列表异常")
            return None
            
    def fetch_fund_detail(self, fund_code):
        """获取基金详情"""
        url = f"{settings.FUND_BASE_URL}/f10/F10DataApi.aspx"
        params = {
            'type': 'lsjz',
            'code': fund_code,
            'page': 1,
            'per': 30,
            'sdate': '',
            'edate': datetime.now().strftime('%Y-%m-%d')
        }
        
        try:
            response = self.session.get(url, params=params)
            if response.status_code != 200:
                logger.error(f"获取基金详情失败: {fund_code}, {response.status_code}")
                return None
                
            # 解析HTML表格
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'class': 'w782 comm lsjz'})
            if not table:
                logger.error(f"基金详情表格未找到: {fund_code}")
                return None
                
            # 解析表头
            headers = [th.get_text().strip() for th in table.find('thead').find_all('th')]
            
            # 解析数据行
            rows = []
            for tr in table.find('tbody').find_all('tr'):
                row = [td.get_text().strip() for td in tr.find_all('td')]
                rows.append(row)
                
            df = pd.DataFrame(rows, columns=headers)
            return df
        except Exception as e:
            logger.exception(f"获取基金详情异常: {fund_code}")
            return None
            
    def analyze_fund_signals(self, fund_code, fund_name, df):
        """分析基金买卖信号"""
        signals = []
        
        if df is None or df.empty:
            return signals
            
        try:
            # 转换数据类型
            df['净值日期'] = pd.to_datetime(df['净值日期'])
            df['单位净值'] = pd.to_numeric(df['单位净值'], errors='coerce')
            df['日增长率'] = pd.to_numeric(df['日增长率'].str.rstrip('%'), errors='coerce')
            
            # 排序
            df.sort_values('净值日期', ascending=False, inplace=True)
            
            # 计算短期和长期均值
            df['short_ma'] = df['单位净值'].rolling(window=5).mean()
            df['long_ma'] = df['单位净值'].rolling(window=20).mean()
            
            # 获取最新数据
            latest = df.iloc[0]
            
            signal = {
                'code': fund_code,
                'name': fund_name,
                'date': latest['净值日期'].strftime('%Y-%m-%d'),
                'net_value': latest['单位净值'],
                'daily_return': latest['日增长率'],
                'short_ma': latest['short_ma'],
                'long_ma': latest['long_ma'],
                'signal': 0,  # 0: 观望, 1: 买入, -1: 卖出
                'signal_reason': []
            }
            
            # 基于涨跌幅的信号
            if signal['daily_return'] > settings.FUND_BUY_THRESHOLD:
                signal['signal'] = 1
                signal['signal_reason'].append(f"单日涨幅{signal['daily_return']:.2f}%")
                
            elif signal['daily_return'] < settings.FUND_SELL_THRESHOLD:
                signal['signal'] = -1
                signal['signal_reason'].append(f"单日跌幅{abs(signal['daily_return']):.2f}%")
                
            # 基于均线的信号
            if signal['signal'] == 0:
                if signal['short_ma'] > signal['long_ma'] and df.iloc[1]['short_ma'] <= df.iloc[1]['long_ma']:
                    signal['signal'] = 1
                    signal['signal_reason'].append("短期均线上穿长期均线")
                    
                elif signal['short_ma'] < signal['long_ma'] and df.iloc[1]['short_ma'] >= df.iloc[1]['long_ma']:
                    signal['signal'] = -1
                    signal['signal_reason'].append("短期均线下穿长期均线")
                    
            signals.append(signal)
            return signals
        except Exception as e:
            logger.exception(f"分析基金信号异常: {fund_code}")
            return []
            
    def run(self, max_funds=50):
        """执行基金数据爬取和分析"""
        logger.info("开始爬取基金数据")
        fund_list = self.fetch_fund_list(page_size=max_funds)
        if not fund_list:
            return None
            
        all_signals = []
        trading_date = get_trading_date()
        
        for fund_data in fund_list['datas']:
            fund_info = fund_data.split(',')
            if len(fund_info) < 2:
                continue
                
            fund_code = fund_info[0]
            fund_name = fund_info[1]
            logger.info(f"处理基金: {fund_name}({fund_code})")
            
            # 获取基金详情
            df = self.fetch_fund_detail(fund_code)
            if df is None:
                continue
                
            # 分析买卖信号
            signals = self.analyze_fund_signals(fund_code, fund_name, df)
            all_signals.extend(signals)
            
            # 保存原始数据
            save_data(df, f"{fund_code}_data.csv", "fund_data")
            
            time.sleep(random.uniform(0.5, 2))  # 随机延迟避免被封
            
        # 保存信号数据
        save_data(all_signals, "fund_signals.json")
        logger.info(f"完成基金信号分析，共处理 {len(all_signals)} 只基金")
        return all_signals
