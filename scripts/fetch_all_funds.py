import json
import requests
import pandas as pd
import time
import random
from datetime import datetime, timedelta
import os

# 配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
ALL_FUNDS_FILE = os.path.join(DATA_DIR, 'all_fund_codes.json')
API_URL = 'http://fund.10jqka.com.cn/interface/fundcode_query.php'
FUND_LIST_API = 'http://fund.10jqka.com.cn/interface/fundlist.php'

# 确保目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# 获取所有基金代码
def get_all_fund_codes():
    try:
        print('获取所有基金代码...')
        # 检查是否已经有基金代码文件
        if os.path.exists(ALL_FUNDS_FILE):
            with open(ALL_FUNDS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)

        # 获取基金总数
        params = {
            'page': 1,
            'pagesize': 1,
            'sort': 'zsz',
            'order': 'desc'
        }
        response = requests.get(FUND_LIST_API, params=params)
        response.raise_for_status()
        data = response.json()
        total_count = int(data['total'])
        print(f'发现 {total_count} 只基金')

        # 分批获取所有基金代码
        page_size = 100
        total_pages = (total_count + page_size - 1) // page_size
        all_funds = []

        for page in range(1, total_pages + 1):
            print(f'获取第 {page}/{total_pages} 页基金代码...')
            params = {
                'page': page,
                'pagesize': page_size,
                'sort': 'zsz',
                'order': 'desc'
            }
            response = requests.get(FUND_LIST_API, params=params)
            response.raise_for_status()
            data = response.json()
            if 'data' in data and data['data']:
                all_funds.extend(data['data'])

            # 添加随机延迟，避免被封IP
            time.sleep(random.uniform(1, 3))

        # 保存基金代码
        with open(ALL_FUNDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_funds, f, ensure_ascii=False, indent=2)

        print(f'成功获取并保存 {len(all_funds)} 只基金代码到 {ALL_FUNDS_FILE}')
        return all_funds
    except Exception as e:
        print(f'获取基金代码时出错: {str(e)}')
        return []

# 获取基金历史数据
def get_fund_history_data(fund_code, fund_name, start_date, end_date):
    try:
        print(f'获取基金 {fund_code}({fund_name}) 历史数据...')
        # 这里简化处理，实际应用中可能需要使用更详细的API或数据来源
        # 创建模拟数据（实际应用中应替换为真实API调用）
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
            'name': fund_name,
            'net_values': net_values,
            'volume': volume
        }

        data_file = os.path.join(DATA_DIR, f'{fund_code}_data.json')
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(fund_data, f, ensure_ascii=False, indent=2)

        print(f'成功保存基金 {fund_code}({fund_name}) 历史数据到 {data_file}')
        return True
    except Exception as e:
        print(f'获取基金 {fund_code}({fund_name}) 历史数据时出错: {str(e)}')
        return False

# 主函数
def main():
    print('开始批量获取全网基金数据...')
    # 设置日期范围（过去1年）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)

    # 获取所有基金代码
    all_funds = get_all_fund_codes()
    if not all_funds:
        print('没有获取到基金代码，程序退出')
        return

    # 为每个基金代码获取数据（这里限制只获取前100只，避免过多请求）
    max_funds = 100  # 可以根据需要调整
    success_count = 0
    fail_count = 0

    for i, fund in enumerate(all_funds[:max_funds]):
        fund_code = fund.get('code', '')
        fund_name = fund.get('name', f'未知基金{fund_code}')
        print(f'处理基金 {i+1}/{max_funds}: {fund_code}({fund_name})')

        if get_fund_history_data(fund_code, fund_name, start_date, end_date):
            success_count += 1
        else:
            fail_count += 1

        # 添加随机延迟，避免被封IP
        time.sleep(random.uniform(2, 5))

    print(f'基金数据获取完成! 成功: {success_count}, 失败: {fail_count}')

if __name__ == '__main__':
    main()