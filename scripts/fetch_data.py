import os
import json
import requests
import pandas as pd
from datetime import datetime, timedelta

# 配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed')
FUND_CODES = ['000001', '110011', '161725']  # 示例基金代码
API_URL = 'http://fund.10jqka.com.cn/interface/fundcode_query.php'

# 确保目录存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# 获取基金历史数据
def get_fund_history_data(fund_code, start_date, end_date):
    try:
        print(f'获取基金 {fund_code} 历史数据...')
        # 这里简化处理，实际应用中可能需要使用更详细的API或数据来源
        # 创建模拟数据
        dates = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
        net_values = []
        volume = []
        base_value = 1.0
        for date in dates:
            # 模拟净值波动
            base_value = base_value * (1 + (pd.np.random.randn() * 0.01))
            net_values.append({
                'date': date.strftime('%Y-%m-%d'),
                'net_value': round(base_value, 4)
            })
            # 模拟成交量
            volume.append({
                'date': date.strftime('%Y-%m-%d'),
                'volume': round(pd.np.random.rand() * 1000000, 2)
            })

        # 保存历史数据
        fund_data = {
            'code': fund_code,
            'name': f'示例基金{fund_code}',
            'net_values': net_values,
            'volume': volume
        }

        data_file = os.path.join(DATA_DIR, f'{fund_code}_data.json')
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(fund_data, f, ensure_ascii=False, indent=2)

        print(f'成功保存基金 {fund_code} 历史数据到 {data_file}')

        # 预处理数据
        process_data(fund_code)

    except Exception as e:
        print(f'获取基金 {fund_code} 历史数据时出错: {str(e)}')

# 预处理数据
def process_data(fund_code):
    try:
        # 加载历史数据
        data_file = os.path.join(DATA_DIR, f'{fund_code}_data.json')
        with open(data_file, 'r', encoding='utf-8') as f:
            fund_data = json.load(f)

        # 转换为DataFrame
        df = pd.DataFrame(fund_data['net_values'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        # 添加成交量数据
        volume_df = pd.DataFrame(fund_data['volume'])
        volume_df['date'] = pd.to_datetime(volume_df['date'])
        df = df.merge(volume_df, on='date', how='left')

        # 计算技术指标
        df['ma5'] = df['net_value'].rolling(window=5).mean()
        df['ma10'] = df['net_value'].rolling(window=10).mean()
        df['ma20'] = df['net_value'].rolling(window=20).mean()

        delta = df['net_value'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))

        df['volume_change'] = df['volume'].pct_change()

        # 删除包含NaN的行
        df = df.dropna()

        # 保存预处理后的数据
        processed_file = os.path.join(PROCESSED_DIR, f'{fund_code}_processed.csv')
        df.to_csv(processed_file, index=False)

        print(f'成功预处理基金 {fund_code} 数据并保存到 {processed_file}')

    except Exception as e:
        print(f'预处理基金 {fund_code} 数据时出错: {str(e)}')

# 获取基金数据的函数
def fetch_fund_data(fund_code):
    try:
        # 腾讯财经API参数
        params = {
            'code': fund_code,
            'fields': 'f002v,f003v,f004v,f005v,f006v,f007v,f010v,f012v,f013v,f014v,f015v,f016v,f017v,f018v,f019v,f020v,f021v,f022v,f023v,f024v,f025v,f026v,f027v,f028v,f029v'
        }

        # 发送请求
        response = requests.get(API_URL, params=params)
        response.raise_for_status()

        # 解析腾讯财经API返回的结果
        data = response.text.strip()
        # 腾讯财经API返回的是类似jsonp的格式，需要处理
        if data.startswith('jsonpgz(') and data.endswith(')'):
            data = data[7:-1]  # 去掉jsonpgz(和)
        # 解析JSON
        result = json.loads(data)

        # 构造我们需要的数据格式
        fund_data = {
            'code': fund_code,
            'name': result[0]['f003v'] if result and len(result) > 0 else '',
            'net_values': []
        }

        # 注意：腾讯财经API可能不直接提供历史净值数据
        # 这里我们仅获取最新数据作为示例
        if result and len(result) > 0:
            latest_data = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'net_value': float(result[0]['f002v']),  # 单位净值
                'volume': float(result[0]['f006v']) if result[0]['f006v'] else 0.0  # 成交量
            }
            fund_data['net_values'].append(latest_data)

        # 保存数据
        filename = os.path.join(DATA_DIR, f'{fund_code}_data.json')
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(fund_data, f, ensure_ascii=False, indent=2)

        print(f'成功获取基金 {fund_code} 的数据并保存到 {filename}')
        return True
    except Exception as e:
        print(f'获取基金 {fund_code} 数据时出错: {str(e)}')
        return False

# 主函数
def main():
    print('开始获取基金数据...')
    # 设置日期范围（过去1年）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    # 为每个基金代码获取数据
    for fund_code in FUND_CODES:
        get_fund_history_data(fund_code, start_date, end_date)

    print('基金数据获取和预处理完成!')

if __name__ == '__main__':
    main()