#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import re
import json
import time
import random
from datetime import datetime, timedelta
import pytz

# 定义基金列表
FUND_CODES = [
    '000001', '000002', '000003', '000004', '000005', '000006', '000007', '000008', '000009', '000010',
    '000011', '000012', '000013', '000014', '000015', '000016', '000017', '000018', '000019', '000020',
    '000021', '000022', '000023', '000024', '000025', '000026', '000027', '000028', '000029', '000030'
]

# 定义通指标参数
def calculate_indicators(df):
    """计算通达信指标"""
    # 计算压力支撑指标
    N = 20
    M = 32
    P1 = 80
    P2 = 100

    # VAR1: (C+H+O+L)/4
    df['VAR1'] = (df['close'] + df['high'] + df['open'] + df['low']) / 4

    # 计算XMA（指数移动平均）
    def xma(series, n):
        return series.ewm(span=n, adjust=False).mean()

    # 卖出线
    df['卖出'] = xma(df['VAR1'], N) * (1 + P1/1000)
    # 买入线
    df['买入'] = xma(df['VAR1'], M) * (1 - P2/1000)

    # 计算筹码意愿指标
    # VAR2Q: REF(LOW,1)
    df['VAR2Q'] = df['low'].shift(1)
    # VAR3Q: SMA(ABS(LOW-VAR2Q),3,1)/SMA(MAX(LOW-VAR2Q,0),3,1)*100
    df['VAR3Q'] = (abs(df['low'] - df['VAR2Q']).ewm(span=3, adjust=False).mean()) / (np.maximum(df['low'] - df['VAR2Q'], 0).ewm(span=3, adjust=False).mean()) * 100
    # VAR4Q: EMA(IF(CLOSE*1.3,VAR3Q*10,VAR3Q/10),3)
    df['VAR4Q'] = np.where(df['close']*1.3, df['VAR3Q']*10, df['VAR3Q']/10).ewm(span=3, adjust=False).mean()
    # VAR5Q: LLV(LOW,30)
    df['VAR5Q'] = df['low'].rolling(window=30).min()
    # VAR6Q: HHV(VAR4Q,30)
    df['VAR6Q'] = df['VAR4Q'].rolling(window=30).max()
    # VAR7Q: IF(MA(CLOSE,58),1,0)
    df['VAR7Q'] = np.where(df['close'].rolling(window=58).mean(), 1, 0)
    # VAR8Q: EMA(IF(LOW<=VAR5Q,(VAR4Q+VAR6Q*2)/2,0),3)/618*VAR7Q
    df['VAR8Q'] = np.where(df['low'] <= df['VAR5Q'], (df['VAR4Q'] + df['VAR6Q']*2)/2, 0).ewm(span=3, adjust=False).mean() / 618 * df['VAR7Q']
    # VAR9Q: IF(VAR8Q>100,100,VAR8Q)
    df['VAR9Q'] = np.where(df['VAR8Q'] > 100, 100, df['VAR8Q'])

    # 计算主力进出指标
    # VAR1: REF((LOW+OPEN+CLOSE+HIGH)/4,1)
    df['VAR1'] = ((df['low'] + df['open'] + df['close'] + df['high']) / 4).shift(1)
    # VAR2: SMA(ABS(LOW-VAR1),13,1)/SMA(MAX(LOW-VAR1,0),10,1)
    df['VAR2'] = (abs(df['low'] - df['VAR1']).ewm(span=13, adjust=False).mean()) / (np.maximum(df['low'] - df['VAR1'], 0).ewm(span=10, adjust=False).mean())
    # VAR3: EMA(VAR2,10)
    df['VAR3'] = df['VAR2'].ewm(span=10, adjust=False).mean()
    # VAR4: LLV(LOW,33)
    df['VAR4'] = df['low'].rolling(window=33).min()
    # VAR5: EMA(IF(LOW<=VAR4,VAR3,0),3)
    df['VAR5'] = np.where(df['low'] <= df['VAR4'], df['VAR3'], 0).ewm(span=3, adjust=False).mean()

    # VAR12: SMA(ABS(HIGH-VAR1),13,1)/SMA(MAX(HIGH-VAR1,0),10,1)
    df['VAR12'] = (abs(df['high'] - df['VAR1']).ewm(span=13, adjust=False).mean()) / (np.maximum(df['high'] - df['VAR1'], 0).ewm(span=10, adjust=False).mean())
    # VAR13: EMA(VAR12,10)
    df['VAR13'] = df['VAR12'].ewm(span=10, adjust=False).mean()
    # VAR14: HHV(HIGH,33)
    df['VAR14'] = df['high'].rolling(window=33).max()
    # VAR15: EMA(IF(HIGH>=VAR14,VAR13,0),3)
    df['VAR15'] = np.where(df['high'] >= df['VAR14'], df['VAR13'], 0).ewm(span=3, adjust=False).mean()

    # A1: REF(CLOSE,2)
    df['A1'] = df['close'].shift(2)
    # A2: SMA(MAX(CLOSE-A1,0),7,1)/SMA(ABS(CLOSE-A1),7,1)*100
    df['A2'] = (np.maximum(df['close'] - df['A1'], 0).ewm(span=7, adjust=False).mean()) / (abs(df['close'] - df['A1']).ewm(span=7, adjust=False).mean()) * 100
    # VARC: SMA(ABS(L-REF(L,1)),3,1)/SMA(MAX(L-REF(L,1),0),3,1)
    df['VARC'] = (abs(df['low'] - df['low'].shift(1)).ewm(span=3, adjust=False).mean()) / (np.maximum(df['low'] - df['low'].shift(1), 0).ewm(span=3, adjust=False).mean())
    # 金山: EMA(IF(L<= LLV(L,30),VARC,0),3)
    df['金山'] = np.where(df['low'] <= df['low'].rolling(window=30).min(), df['VARC'], 0).ewm(span=3, adjust=False).mean()

    return df

def get_signal(row):
    """根据指标计算买卖信号"""
    # 买入信号条件
    buy_signal = (
        (row['close'] > row['买入']) and  # 价格上穿买入线
        (row['VAR9Q'] > 0) and  # 有吸筹迹象
        (row['VAR5'] > row['VAR5'].shift(1)) and  # 主力进场
        (row['A2'] < 19)  # 波段介入点
    )

    # 卖出信号条件
    sell_signal = (
        (row['close'] < row['卖出']) and  # 价格下穿卖出线
        (row['VAR15'] < row['VAR15'].shift(1)) and  # 主力出场
        (row['金山'] > 0)  # 金山指标
    )

    if buy_signal:
        return "买"
    elif sell_signal:
        return "卖"
    else:
        return "观望"

def get_fund_data_from_tiantian(fund_code):
    """从天天基金网获取基金数据"""
    url = f"http://fund.eastmoney.com/f10/F10DataApi.aspx?type=lsjz&code={fund_code}&page=1&per=100"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 解析数据
        content = soup.find('div', class_='box')
        if content:
            # 查找表格
            table = content.find('table')
            if table:
                rows = table.find_all('tr')[1:]  # 跳过表头
                data = []
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 7:
                        date = cols[0].text.strip()
                        net_asset_value = float(cols[1].text.strip())
                        cumulative_net_asset_value = float(cols[2].text.strip())
                        daily_growth_rate = cols[3].text.strip()
                        subscription_status = cols[4].text.strip()
                        redemption_status = cols[5].text.strip()
                        dividend_distribution = cols[6].text.strip()

                        # 转换日增长率
                        daily_growth_rate = daily_growth_rate.replace('%', '')
                        try:
                            daily_growth_rate = float(daily_growth_rate) / 100
                        except:
                            daily_growth_rate = 0

                        data.append({
                            'date': date,
                            'open': net_asset_value,
                            'high': net_asset_value * (1 + abs(daily_growth_rate) * 0.5),
                            'low': net_asset_value * (1 - abs(daily_growth_rate) * 0.5),
                            'close': net_asset_value,
                            'volume': 1000000,  # 基金没有成交量，设一个固定值
                            'fund_code': fund_code,
                            'fund_name': get_fund_name(fund_code)
                        })

                return pd.DataFrame(data)
    except Exception as e:
        print(f"获取基金 {fund_code} 数据失败: {e}")

    return None

def get_fund_name(fund_code):
    """获取基金名称"""
    url = f"http://fund.eastmoney.com/{fund_code}.html"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 获取基金名称
        fund_name_tag = soup.find('h1', class_='fundDetail-tit')
        if fund_name_tag:
            return fund_name_tag.text.strip()
    except Exception as e:
        print(f"获取基金 {fund_code} 名称失败: {e}")

    return f"基金{fund_code}"

def get_fund_data_from_sina(fund_code):
    """从新浪财经获取基金数据作为备用数据源"""
    url = f"https://finance.sina.com.cn/fund/quotes/{fund_code}/bc.shtml"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 解析数据
        # 这里需要根据新浪财经的实际HTML结构进行解析
        # 由于网站结构可能变化，这里只提供示例代码
        data = []
        # 示例解析代码，实际需要根据网站结构调整
        # table = soup.find('table', {'id': 'fund_hold_table'})
        # if table:
        #     rows = table.find_all('tr')[1:]  # 跳过表头
        #     for row in rows:
        #         cols = row.find_all('td')
        #         if len(cols) >= 5:
        #             date = cols[0].text.strip()
        #             net_asset_value = float(cols[1].text.strip())
        #             daily_growth_rate = cols[2].text.strip().replace('%', '')
        #             try:
        #                 daily_growth_rate = float(daily_growth_rate) / 100
        #             except:
        #                 daily_growth_rate = 0
        #             
        #             data.append({
        #                 'date': date,
        #                 'open': net_asset_value,
        #                 'high': net_asset_value * (1 + abs(daily_growth_rate) * 0.5),
        #                 'low': net_asset_value * (1 - abs(daily_growth_rate) * 0.5),
        #                 'close': net_asset_value,
        #                 'volume': 1000000,
        #                 'fund_code': fund_code,
        #                 'fund_name': get_fund_name(fund_code)
        #             })
        # 
        # if data:
        #     return pd.DataFrame(data)
    except Exception as e:
        print(f"从新浪财经获取基金 {fund_code} 数据失败: {e}")

    return None

def get_fund_data(fund_code):
    """获取基金数据，尝试多个数据源"""
    # 首先尝试从天天基金网获取
    df = get_fund_data_from_tiantian(fund_code)

    # 如果天天基金网获取失败，尝试从新浪财经获取
    if df is None or len(df) == 0:
        df = get_fund_data_from_sina(fund_code)

    return df

def update_readme(fund_signals):
    """更新README.md文件"""
    # 读取README.md文件
    with open('README.md', 'r', encoding='utf-8') as f:
        readme_content = f.read()

    # 分割README内容
    parts = readme_content.split('<!-- 数据将通过GitHub Actions自动更新 -->')

    # 生成表格内容
    table_header = "| 基金名称 | 当前价格 | 买卖信号 | 分析日期 |\n|---------|---------|---------|---------|\n"
    table_rows = []

    # 按照买卖信号排序（买 > 卖 > 观望）
    sorted_signals = sorted(fund_signals, key=lambda x: (
        0 if x['signal'] == '买' else (1 if x['signal'] == '卖' else 2)
    ))

    for signal in sorted_signals:
        table_rows.append(f"| {signal['fund_name']} | {signal['price']:.4f} | {signal['signal']} | {signal['date']} |\n")

    # 组合新的README内容
    new_readme_content = parts[0] + '<!-- 数据将通过GitHub Actions自动更新 -->\n' + table_header + ''.join(table_rows)

    # 写入README.md文件
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(new_readme_content)

def main():
    """主函数"""
    # 获取当前日期（北京时间）
    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(tz)
    current_date = now.strftime('%Y-%m-%d')

    fund_signals = []

    # 遍历基金代码列表
    for fund_code in FUND_CODES:
        print(f"正在分析基金 {fund_code}...")

        # 获取基金数据
        df = get_fund_data(fund_code)

        if df is not None and len(df) > 0:
            # 计算指标
            df = calculate_indicators(df)

            # 获取最新数据
            latest_data = df.iloc[-1]

            # 计算买卖信号
            signal = get_signal(latest_data)

            # 添加到信号列表
            fund_signals.append({
                'fund_code': fund_code,
                'fund_name': latest_data['fund_name'],
                'price': latest_data['close'],
                'signal': signal,
                'date': current_date
            })

            # 随机延迟，避免请求过于频繁
            time.sleep(random.uniform(0.5, 1.5))
        else:
            print(f"无法获取基金 {fund_code} 的数据")

    # 更新README.md文件
    if fund_signals:
        update_readme(fund_signals)
        print("README.md文件已更新")
    else:
        print("没有获取到任何基金数据，不更新README.md文件")

if __name__ == "__main__":
    main()
