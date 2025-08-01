import yfinance as yf
import pandas as pd
import os
import argparse
import sys

def load_fund_data(fund_code, start_date):
    """
    获取基金历史数据
    fund_code: 基金代码 (如 '000311.SZ' 或 '000311.SS')
    start_date: '2020-01-01'
    """
    try:
        # 尝试直接下载
        data = yf.download(fund_code, start=start_date)
        
        # 如果数据为空，尝试添加交易所后缀
        if data.empty:
            print(f"尝试添加交易所后缀...")
            for exchange in ['.SZ', '.SS']:
                full_code = fund_code.split('.')[0] + exchange
                print(f"尝试代码: {full_code}")
                data = yf.download(full_code, start=start_date)
                if not data.empty:
                    print(f"使用 {full_code} 获取数据成功")
                    return data[['Open', 'High', 'Low', 'Close', 'Volume']]
        
        # 如果仍然为空
        if data.empty:
            print(f"警告: 未找到基金 {fund_code} 从 {start_date} 的数据")
            return pd.DataFrame()
            
        return data[['Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception as e:
        print(f"数据下载错误: {e}")
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
        print("错误: 无法加载数据!")
        sys.exit(1)  # 退出状态码1表示错误
    else:
        df.to_csv(args.output)
        print(f"成功保存数据到 {args.output}")
