import os
import pickle
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

# 配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed')
MODELS_DIR = os.path.join(BASE_DIR, 'models')

# 确保数据处理目录和模型目录存在
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

# 训练模型的函数
def train_model(fund_code):
    try:
        # 加载预处理后的数据
        processed_file = os.path.join(PROCESSED_DIR, f'{fund_code}_processed.csv')
        df = pd.read_csv(processed_file)

        # 定义特征和目标变量
        # 我们将使用前一天的指标来预测第二天的净值变化
        features = ['ma5', 'ma10', 'ma20', 'rsi', 'volume_change']
        target = 'next_day_change'

        # 计算次日净值变化
        df['next_day_change'] = df['net_value'].pct_change(periods=-1).shift(-1)

        # 移除包含NaN的行
        df = df.dropna()

        # 分割训练集和测试集
        X = df[features]
        y = df[target]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # 创建并训练模型
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        # 预测和评估
        y_pred = model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        print(f'基金 {fund_code} 模型评估结果:')
        print(f'均方误差 (MSE): {mse:.6f}')
        print(f'决定系数 (R²): {r2:.6f}')

        # 保存模型
        model_file = os.path.join(MODELS_DIR, f'{fund_code}_model.pkl')
        with open(model_file, 'wb') as f:
            pickle.dump(model, f)

        print(f'成功训练基金 {fund_code} 的模型并保存到 {model_file}')
        return model, mse, r2
    except Exception as e:
        print(f'训练基金 {fund_code} 模型时出错: {str(e)}')
        return None, None, None

# 主函数
def main():
    print('开始训练基金模型...')
    # 获取所有预处理后的数据文件
    for filename in os.listdir(PROCESSED_DIR):
        if filename.endswith('_processed.csv'):
            fund_code = filename.split('_')[0]
            train_model(fund_code)
    print('基金模型训练完成!')

if __name__ == '__main__':
    main()