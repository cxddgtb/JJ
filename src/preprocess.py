# src/preprocess.py
import pandas as pd
import argparse
import os
import sys

def preprocess_data(input_file, output_file):
    """
    预处理基金数据
    """
    try:
        # 确保输入文件存在
        if not os.path.exists(input_file):
            print(f"Error: Input file {input_file} does not exist!")
            return False
        
        # 读取数据
        df = pd.read_csv(input_file)
        
        # 基本预处理
        df = df.dropna()
        df = df.drop_duplicates()
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 保存为Parquet格式
        df.to_parquet(output_file)
        print(f"Successfully preprocessed data and saved to {output_file}")
        return True
    except Exception as e:
        print(f"Error during preprocessing: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Preprocess fund data')
    parser.add_argument('--input', required=True, help='Input CSV file path')
    parser.add_argument('--output', required=True, help='Output Parquet file path')
    
    args = parser.parse_args()
    
    success = preprocess_data(args.input, args.output)
    
    if not success:
        sys.exit(1)  # 退出状态码1表示错误
