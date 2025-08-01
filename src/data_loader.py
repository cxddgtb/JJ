import yfinance as yf
import pandas as pd
import os
import argparse
import sys
import datetime

def load_fund_data(fund_code, start_date):
    """
    获取基金历史数据
    fund_code: 基金代码 (如 '510300.SS')
    start_date: '2020-01-01'
    """
    print(f"尝试加载基金数据: {fund_code} 从 {start_date}")
    
    try:
        # 尝试直接下载
        data = yf.download(fund_code, start=start_date)
        
        # 如果数据为空，尝试不同的后缀
        if data.empty:
            print(f"尝试不同的交易所后缀...")
            # 尝试A股后缀
            for suffix in ['.SS', '.SZ', '.CF']:
                new_code = fund_code.split('.')[0] + suffix
                print(f"尝试代码: {new_code}")
                data = yf.download(new_code, start=start_date)
                if not data.empty:
                    print(f"使用 {new_code} 获取数据成功")
                    return data[['Open', 'High', 'Low', 'Close', 'Volume']]
            
            # 尝试美股后缀
            for suffix in ['.AX', '.TO', '.L', '.F']:
                new_code = fund_code.split('.')[0] + suffix
                print(f"尝试国际代码: {new_code}")
                data = yf.download(new_code, start=start_date)
                if not data.empty:
                    print(f"使用 {new_code} 获取数据成功")
                    return data[['Open', 'High', 'Low', 'Close', 'Volume']]
        
        # 如果仍然为空
        if data.empty:
            print(f"警告: 未找到基金 {fund_code} 从 {start_date} 的数据")
            return pd.DataFrame()
            
        print(f"成功获取 {fund_code} 的数据")
        return data[['Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception as e:
        print(f"数据下载错误: {str(e)}")
        return pd.DataFrame()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='加载基金数据')
    parser.add_argument('--fund', required=True, help='基金代码')
    parser.add_argument('--start_date', required=True, help='开始日期 (YYYY-MM-DD格式)')
    parser.add_argument('--output', required=True, help='输出CSV文件路径')
    
    args = parser.parse_args()
    
    print("="*50)
    print(f"接收参数: --fund={args.fund} --start_date={args.start_date} --output={args.output}")
    print("="*50)
    
    # 确保目录存在
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    df = load_fund_data(args.fund, args.start_date)
    
    if df.empty:
        # 尝试使用备选基金代码
        print("尝试备选基金代码...")
        alternative_codes = ['510300.SS', '510310.SS', '510330.SS', '159919.SZ']
        for code in alternative_codes:
            df = load_fund_data(code, args.start_date)
            if not df.empty:
                break
        
        if df.empty:
            print("错误: 无法加载任何基金数据!")
            sys.exit(1)
    
    df.to_csv(args.output)
    print(f"成功保存数据到 {args.output}")
    print(f"数据大小: {len(df)} 行")
    print("前5行数据:")
    print(df.head())
    sys.exit(0)
