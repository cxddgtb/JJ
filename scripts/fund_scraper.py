import requests
import pandas as pd
import json
import re
import time
import random
from datetime import datetime, timedelta
from scripts.utils import save_data, setup_logging
from config.settings import settings

logger = setup_logging()

class FundDataScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Referer': settings.FUND_BASE_URL,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0'
        })
        
    def fetch_fund_history(self, fund_code, fund_name, days=settings.HISTORICAL_DAYS):
        """获取基金历史数据"""
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days+10)).strftime('%Y-%m-%d')
        
        params = {
            'type': 'lsjz',
            'code': fund_code,
            'page': 1,
            'per': days + 5,  # 多取几天确保有足够数据
            'sdate': start_date,
            'edate': end_date
        }
        
        try:
            response = self.session.get(settings.FUND_DETAIL_URL, params=params)
            if response.status_code != 200:
                logger.warning(f"获取基金历史失败: {fund_code}, HTTP {response.status_code}")
                return []
                
            # 解析HTML表格
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'class': 'w782 comm lsjz'})
            if not table:
                logger.warning(f"基金历史表格未找到: {fund_code}")
                return []
                
            # 解析表头
            headers = [th.get_text().strip() for th in table.find('thead').find_all('th')]
            
            # 解析数据行
            rows = []
            for tr in table.find('tbody').find_all('tr'):
                row = [td.get_text().strip() for td in tr.find_all('td')]
                rows.append(row)
                
            # 转换为DataFrame并按日期排序
            df = pd.DataFrame(rows, columns=headers)
            if df.empty:
                return []
                
            # 转换数据类型
            df['净值日期'] = pd.to_datetime(df['净值日期'])
            df.sort_values('净值日期', ascending=False, inplace=True)
            
            # 处理单位净值
            df['单位净值'] = pd.to_numeric(
                df['单位净值'].str.replace('[^0-9.]', '', regex=True), 
                errors='coerce'
            )
            
            # 处理日增长率
            df['日增长率'] = pd.to_numeric(
                df['日增长率'].str.replace('%', '').str.replace('--', '0'), 
                errors='coerce'
            )
            
            # 仅保留最近15天数据
            df = df.head(settings.HISTORICAL_DAYS)
            
            # 转换为历史记录列表
            history = []
            for _, row in df.iterrows():
                history.append({
                    '日期': row['净值日期'].strftime('%Y-%m-%d'),
                    '净值': row['单位净值'],
                    '日涨幅': row['日增长率']
                })
                
            return history
        except Exception as e:
            logger.warning(f"获取基金历史异常: {fund_code} - {str(e)}")
            return []
            
    def analyze_fund_signals(self, history):
        """分析基金历史信号"""
        signals = []
        
        for day_data in history:
            signal = "观望"
            daily_return = day_data.get('日涨幅', 0)
            
            if not pd.isna(daily_return):
                if daily_return > settings.FUND_BUY_THRESHOLD:
                    signal = "买入"
                elif daily_return < settings.FUND_SELL_THRESHOLD:
                    signal = "卖出"
            
            day_data['信号'] = signal
            signals.append(day_data)
            
        return signals
            
    def run(self):
        """执行基金数据爬取和分析"""
        logger.info("开始爬取基金历史数据")
        all_fund_signals = []
        
        for fund_name, fund_code in settings.FUNDS_TO_TRACK:
            logger.info(f"处理基金: {fund_name}({fund_code})")
            
            try:
                # 获取历史数据
                history = self.fetch_fund_history(fund_code, fund_name)
                if not history:
                    logger.warning(f"基金 {fund_name}({fund_code}) 无历史数据")
                    continue
                    
                # 分析信号
                signals = self.analyze_fund_signals(history)
                
                # 保存基金数据
                fund_data = {
                    '基金名称': fund_name,
                    '基金代码': fund_code,
                    '历史信号': signals
                }
                
                all_fund_signals.append(fund_data)
                
                # 保存原始数据
                save_data(fund_data, f"{fund_code}_history.json", "fund_data")
                
                time.sleep(random.uniform(1, 3))  # 随机延迟避免被封
                
            except Exception as e:
                logger.error(f"处理基金 {fund_name}({fund_code}) 失败: {str(e)}")
        
        # 保存所有信号数据
        save_data(all_fund_signals, "fund_signals.json")
        logger.info(f"完成基金信号分析，共处理 {len(all_fund_signals)} 只基金")
        return all_fund_signals
