# src/data_loader.py
import yfinance as yf
import pandas as pd
import os
import argparse

def load_fund_data(fund_code, start_date):
    """
    获取基金历史数据
    fund_code: 基金代码 (如 '000311.OF')
    start_date: '2020-01-01'
    """
    try:
        data = yf.download(fund_code, start=start_date)
        if data.empty:
            print(f"Warning: No data found for {fund_code} from {start_date}")
        return data[['Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception as e:
        print(f"Error downloading data: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Load fund data')
    parser.add_argument('--fund', required=True, help='Fund code')
    parser.add_argument('--start_date', required=True, help='Start date in YYYY-MM-DD format')
    parser.add_argument('--output', required=True, help='Output CSV file path')
    
    args = parser.parse_args()
    
    # 确保目录存在
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    df = load_fund_data(args.fund, args.start_date)
    
    if df.empty:
        print("Failed to load data. Creating empty file for debugging.")
        open(args.output, 'a').close()  # 创建空文件
    else:
        df.to_csv(args.output)
        print(f"Successfully saved data to {args.output}")
