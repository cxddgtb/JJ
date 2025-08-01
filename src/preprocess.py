import pandas as pd
import argparse
import os
import sys

def preprocess_data(input_file, output_file):
    """
    预处理基金数据
    """
    try:
        # 确保输入文件存在且非空
        if not os.path.exists(input_file) or os.path.getsize(input_file) == 0:
            print(f"错误: 输入文件 {input_file} 不存在或为空!")
            return False
        
        # 读取数据
        df = pd.read_csv(input_file)
        
        # 检查数据是否为空
        if df.empty:
            print(f"错误: 输入文件 {input_file} 没有有效数据!")
            return False
            
        # 基本预处理
        df = df.dropna()
        df = df.drop_duplicates()
        
        # 添加技术指标计算 (示例)
        df['MA10'] = df['Close'].rolling(window=10).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['RSI'] = calculate_rsi(df['Close'])
        
        # 添加目标变量 (示例)
        df['signal'] = (df['Close'].shift(-5) > df['Close']).astype(int)
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 保存为Parquet格式
        df.to_parquet(output_file)
        print(f"成功预处理数据并保存到 {output_file}")
        return True
    except Exception as e:
        print(f"预处理过程中出错: {e}")
        return False

def calculate_rsi(prices, window=14):
    """
    计算相对强弱指数 (RSI)
    """
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Preprocess fund data')
    parser.add_argument('--input', required=True, help='Input CSV file path')
    parser.add_argument('--output', required=True, help='Output Parquet file path')
    
    args = parser.parse_args()
    
    success = preprocess_data(args.input, args.output)
    
    if not success:
        sys.exit(1)  # 退出状态码1表示错误
