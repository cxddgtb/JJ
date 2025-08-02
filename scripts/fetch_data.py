import os
import json
import requests
from datetime import datetime, timedelta

# 设置基金代码和API密钥
FUND_CODES = ['000001', '110011', '161725']  # 示例基金代码
API_KEY = os.getenv('FUND_API_KEY')  # 从环境变量获取API密钥

# API配置 (使用腾讯财经免费接口)
API_URL = 'http://fund.10jqka.com.cn/interface/fundcode_query.php'
DATA_DIR = '../data'

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

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
    for fund_code in FUND_CODES:
        fetch_fund_data(fund_code)
    print('基金数据获取完成!')

if __name__ == '__main__':
    main()