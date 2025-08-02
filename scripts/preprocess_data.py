import os
import json
import pandas as pd

# 配置
DATA_DIR = '../data'
PROCESSED_DIR = '../data/processed'

# 确保处理后的数据目录存在
os.makedirs(PROCESSED_DIR, exist_ok=True)

# 预处理基金数据的函数
def preprocess_fund_data(fund_code):
    try:
        # 读取原始数据
        raw_file = os.path.join(DATA_DIR, f'{fund_code}_data.json')
        with open(raw_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 转换为DataFrame
        df = pd.DataFrame(data['net_values'])

        # 数据清洗
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        df = df.dropna()

        # 计算技术指标
        # 1. 移动平均线
        df['ma5'] = df['net_value'].rolling(window=5).mean()
        df['ma10'] = df['net_value'].rolling(window=10).mean()
        df['ma20'] = df['net_value'].rolling(window=20).mean()

        # 2. 相对强弱指数(RSI)
        delta = df['net_value'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # 3. 成交量变化
        df['volume_change'] = df['volume'].pct_change()

        # 保存处理后的数据
        processed_file = os.path.join(PROCESSED_DIR, f'{fund_code}_processed.csv')
        df.to_csv(processed_file, index=False, encoding='utf-8')

        print(f'成功预处理基金 {fund_code} 的数据并保存到 {processed_file}')
        return True
    except Exception as e:
        print(f'预处理基金 {fund_code} 数据时出错: {str(e)}')
        return False

# 主函数
def main():
    print('开始预处理基金数据...')
    # 获取所有基金数据文件
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('_data.json'):
            fund_code = filename.split('_')[0]
            preprocess_fund_data(fund_code)
    print('基金数据预处理完成!')

if __name__ == '__main__':
    main()