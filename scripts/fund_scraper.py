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
            'Referer': settings.FUND_BASE_URL,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0'
        })
        
    def fetch_fund_list(self, page=1, page_size=100):
        """获取基金列表 - 更健壮的实现"""
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
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.session.get(settings.FUND_RANK_URL, params=params)
                if response.status_code != 200:
                    logger.warning(f"获取基金列表失败 (HTTP {response.status_code})，尝试 {attempt+1}/{max_retries}")
                    time.sleep(2)
                    continue
                    
                content = response.text
                
                # 尝试多种可能的格式
                if 'var rankData = ' in content:
                    # 处理 JSONP 格式
                    start_index = content.index('var rankData = ') + len('var rankData = ')
                    end_index = content.find(';', start_index)
                    if end_index == -1:
                        end_index = len(content)
                    json_str = content[start_index:end_index]
                elif content.startswith('{') or content.startswith('['):
                    # 可能是纯 JSON
                    json_str = content
                else:
                    # 尝试正则匹配
                    match = re.search(r'\{.*\}', content, re.DOTALL)
                    if match:
                        json_str = match.group(0)
                    else:
                        logger.warning(f"无法识别的基金列表格式，尝试 {attempt+1}/{max_retries}")
                        time.sleep(2)
                        continue
                
                try:
                    data = json.loads(json_str)
                    if 'datas' in data and 'allCount' in data:
                        logger.info(f"成功获取基金列表，共 {data['allCount']} 只基金")
                        return {
                            'datas': data['datas'],
                            'allCount': data['allCount']
                        }
                    else:
                        logger.warning(f"基金列表数据缺少必要字段，尝试 {attempt+1}/{max_retries}")
                except json.JSONDecodeError as e:
                    logger.warning(f"解析基金列表JSON失败: {e}，尝试 {attempt+1}/{max_retries}")
                    logger.debug(f"JSON字符串: {json_str[:200]}...")
            except Exception as e:
                logger.warning(f"获取基金列表异常: {e}，尝试 {attempt+1}/{max_retries}")
            
            time.sleep(3)
        
        logger.error(f"获取基金列表失败，已尝试 {max_retries} 次")
        return None
            
    def fetch_fund_detail(self, fund_code):
        """获取基金详情 - 使用更可靠的API"""
        url = f"{settings.FUND_BASE_URL}/api/FundJijin/GetJijin"
        params = {
            'fundcode': fund_code,
            'pageindex': 0,
            'pagesize': 30,
            'type': 'lsjz'
        }
        
        try:
            response = self.session.get(url, params=params)
            if response.status_code != 200:
                logger.warning(f"获取基金详情失败: {fund_code}, HTTP {response.status_code}")
                return pd.DataFrame()
                
            try:
                data = response.json()
                if 'Data' not in data or 'LSJZList' not in data['Data']:
                    logger.warning(f"基金详情数据格式异常: {fund_code}")
                    return pd.DataFrame()
                    
                # 转换为DataFrame
                df = pd.DataFrame(data['Data']['LSJZList'])
                if df.empty:
                    logger.warning(f"基金 {fund_code} 无净值数据")
                    return df
                
                # 重命名列
                df.rename(columns={
                    'FSRQ': '净值日期',
                    'DWJZ': '单位净值',
                    'LJJZ': '累计净值',
                    'JZZZL': '日增长率'
                }, inplace=True)
                
                # 保留必要列
                df = df[['净值日期', '单位净值', '日增长率']]
                
                return df
            except json.JSONDecodeError:
                logger.warning(f"解析基金详情JSON失败: {fund_code}")
                return pd.DataFrame()
        except Exception as e:
            logger.warning(f"获取基金详情异常: {fund_code} - {str(e)}")
            return pd.DataFrame()
            
    def analyze_fund_signals(self, fund_code, fund_name, df):
        """分析基金买卖信号 - 简化但更健壮"""
        signals = []
        
        if df.empty:
            logger.info(f"基金 {fund_name}({fund_code}) 无数据，跳过分析")
            return signals
            
        try:
            # 转换数据类型
            df['净值日期'] = pd.to_datetime(df['净值日期'])
            df['单位净值'] = pd.to_numeric(df['单位净值'], errors='coerce')
            
            # 处理日增长率（可能为空或特殊值）
            df['日增长率'] = pd.to_numeric(
                df['日增长率'].replace('', '0').str.rstrip('%'),
                errors='coerce'
            )
            
            # 过滤无效数据
            df = df.dropna(subset=['单位净值'])
            
            if df.empty:
                logger.info(f"基金 {fund_name}({fund_code}) 无有效数据，跳过分析")
                return signals
                
            # 排序
            df.sort_values('净值日期', ascending=False, inplace=True)
            latest = df.iloc[0]
            
            signal = {
                'code': fund_code,
                'name': fund_name,
                'date': latest['净值日期'].strftime('%Y-%m-%d'),
                'net_value': latest['单位净值'],
                'daily_return': latest.get('日增长率', 0),
                'signal': 0,  # 0: 观望, 1: 买入, -1: 卖出
                'signal_reason': []
            }
            
            # 基于涨跌幅的信号
            daily_return = signal['daily_return']
            if not pd.isna(daily_return):
                if daily_return > settings.FUND_BUY_THRESHOLD:
                    signal['signal'] = 1
                    signal['signal_reason'].append(f"单日涨幅{daily_return:.2f}%")
                elif daily_return < settings.FUND_SELL_THRESHOLD:
                    signal['signal'] = -1
                    signal['signal_reason'].append(f"单日跌幅{abs(daily_return):.2f}%")
                    
            signals.append(signal)
            return signals
        except Exception as e:
            logger.warning(f"分析基金信号异常: {fund_code} - {str(e)}")
            return []
            
    def run(self, max_funds=20):
        """执行基金数据爬取和分析"""
        logger.info("开始爬取基金数据")
        fund_list = self.fetch_fund_list(page_size=max_funds)
        if not fund_list or 'datas' not in fund_list:
            logger.error("无法获取基金列表数据，使用备用基金列表")
            # 备用基金列表
            fund_list = {
                'datas': [
                    '000001,华夏成长',
                    '000003,中海可转债A',
                    '000011,华夏大盘精选',
                    '000021,华夏优势增长',
                    '000031,华夏复兴',
                    '000041,华夏全球精选',
                    '000051,华夏沪深300ETF联接A',
                    '000061,华夏盛世精选',
                    '000071,华夏恒生ETF联接A',
                    '000127,农银行业成长'
                ]
            }
            
        all_signals = []
        
        for fund_data in fund_list['datas'][:max_funds]:  # 确保不超过最大数量
            fund_info = fund_data.split(',')
            if len(fund_info) < 2:
                continue
                
            fund_code = fund_info[0]
            fund_name = fund_info[1]
            logger.info(f"处理基金: {fund_name}({fund_code})")
            
            # 获取基金详情
            df = self.fetch_fund_detail(fund_code)
            
            # 分析买卖信号
            signals = self.analyze_fund_signals(fund_code, fund_name, df)
            all_signals.extend(signals)
            
            # 保存原始数据
            if not df.empty:
                save_data(df, f"{fund_code}_data.csv", "fund_data")
            
            time.sleep(random.uniform(1, 3))  # 增加延迟避免被封
            
        # 保存信号数据
        save_data(all_signals, "fund_signals.json")
        logger.info(f"完成基金信号分析，共处理 {len(all_signals)} 只基金")
        return all_signals
