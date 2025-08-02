import os
import pickle
import json
import pandas as pd
import requests
from datetime import datetime

# 配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, 'models')
DATA_DIR = os.path.join(BASE_DIR, 'data')
PREDICTION_DIR = os.path.join(BASE_DIR, 'data', 'predictions')
FUND_CODES = ['000001', '110011', '161725']  # 示例基金代码
# 腾讯财经API不需要API密钥
API_URL = 'http://fund.10jqka.com.cn/interface/fundcode_query.php'

# 确保预测目录存在
os.makedirs(PREDICTION_DIR, exist_ok=True)

# 获取最新基金数据
def get_latest_fund_data(fund_code):
    try:
        # 腾讯财经API参数
        params = {
            'code': fund_code,
            'fields': 'f002v,f003v,f004v,f005v,f006v,f007v,f010v,f012v,f013v,f014v,f015v,f016v,f017v,f018v,f019v,f020v,f021v,f022v,f023v,f024v,f025v,f026v,f027v,f028v,f029v'
        }
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        # 解析腾讯财经API返回的结果
        data = response.text.strip()
        # 腾讯财经API返回的是类似jsonp的格式，需要处理
        if data.startswith('jsonpgz(') and data.endswith(')'):
            data = data[7:-1]  # 去掉jsonpgz(和)
        # 解析JSON
        result = json.loads(data)
        if result and isinstance(result, list) and len(result) > 0:
            # 提取需要的数据
            fund_data = {
                'code': fund_code,
                'net_value': float(result[0]['f002v']),  # 单位净值
                'volume': float(result[0]['f006v']) if result[0]['f006v'] else 0.0  # 成交量
            }
            return fund_data
        return None
    except Exception as e:
        print(f'获取基金 {fund_code} 最新数据时出错: {str(e)}')
        return None

# 预处理最新数据
def preprocess_latest_data(data):
    try:
        # 提取需要的字段
        latest_data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'net_value': data['net_value'],
            'volume': data['volume']
        }

        # 读取历史数据计算指标
        fund_code = data['code']
        history_file = os.path.join(DATA_DIR, f'{fund_code}_data.json')
        with open(history_file, 'r', encoding='utf-8') as f:
            history_data = json.load(f)

        # 转换为DataFrame
        df = pd.DataFrame(history_data['net_values'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        # 添加最新数据
        latest_df = pd.DataFrame([latest_data])
        latest_df['date'] = pd.to_datetime(latest_df['date'])
        df = pd.concat([df, latest_df], ignore_index=True)

        # 重新计算技术指标
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

        # 获取最新一条记录的特征
        latest_features = df.iloc[-1][['ma5', 'ma10', 'ma20', 'rsi', 'volume_change']].values.reshape(1, -1)
        return latest_features
    except Exception as e:
        print(f'预处理最新数据时出错: {str(e)}')
        return None

# 预测函数
def predict(fund_code):
    try:
        # 加载模型
        model_file = os.path.join(MODEL_DIR, f'{fund_code}_model.pkl')
        with open(model_file, 'rb') as f:
            model = pickle.load(f)

        # 获取并预处理最新数据
        latest_data = get_latest_fund_data(fund_code)
        if not latest_data:
            return None

        features = preprocess_latest_data(latest_data)
        if features is None:
            return None

        # 预测
        prediction = model.predict(features)[0]

        # 生成买卖信号
        signal = '买入' if prediction > 0.01 else ('卖出' if prediction < -0.01 else '持有')

        # 保存预测结果
        prediction_result = {
            'fund_code': fund_code,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'predicted_change': float(prediction),
            'signal': signal
        }

        prediction_file = os.path.join(PREDICTION_DIR, f'{fund_code}_prediction.json')
        with open(prediction_file, 'w', encoding='utf-8') as f:
            json.dump(prediction_result, f, ensure_ascii=False, indent=2)

        print(f'成功预测基金 {fund_code}: 信号={signal}, 预测变化={prediction:.6f}')
        return prediction_result
    except Exception as e:
        print(f'预测基金 {fund_code} 时出错: {str(e)}')
        return None

# 主函数
def main():
    print('开始预测基金走势...')
    results = []
    for fund_code in FUND_CODES:
        result = predict(fund_code)
        if result:
            results.append(result)

    # 保存所有预测结果
    all_predictions_file = os.path.join(PREDICTION_DIR, 'all_predictions.json')
    with open(all_predictions_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f'基金预测完成，共预测 {len(results)} 只基金，结果保存到 {all_predictions_file}')

if __name__ == '__main__':
    main()