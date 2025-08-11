import pandas as pd

def calculate_moving_average(df, window):
    """
    计算移动平均线
    """
    return df['net_value'].rolling(window=window).mean()

def calculate_rsi(df, window=14):
    """
    计算相对强弱指数 (RSI)
    """
    delta = df['net_value'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(df, fast_period=12, slow_period=26, signal_period=9):
    """
    计算移动平均收敛散度 (MACD)
    """
    fast_ema = df['net_value'].ewm(span=fast_period, adjust=False).mean()
    slow_ema = df['net_value'].ewm(span=slow_period, adjust=False).mean()
    macd = fast_ema - slow_ema
    signal_line = macd.ewm(span=signal_period, adjust=False).mean()
    return macd, signal_line

def generate_signals(df):
    """
    根据技术指标生成买卖信号
    """
    df['ma5'] = calculate_moving_average(df, 5)
    df['ma10'] = calculate_moving_average(df, 10)
    df['rsi'] = calculate_rsi(df)
    df['macd'], df['macd_signal'] = calculate_macd(df)

    # 买入信号：5日均线上穿10日均线，且RSI < 70
    df['buy_signal'] = ((df['ma5'] > df['ma10']) & (df['ma5'].shift(1) < df['ma10'].shift(1)) & (df['rsi'] < 70))

    # 卖出信号：5日均线下穿10日均线，或RSI > 70
    df['sell_signal'] = ((df['ma5'] < df['ma10']) & (df['ma5'].shift(1) > df['ma10'].shift(1))) | (df['rsi'] > 70)

    return df

if __name__ == '__main__':
    fund_code = "005918"
    input_path = f"data/{fund_code}_historical_data.csv"
    output_path = f"data/{fund_code}_analysis.csv"

    try:
        # 读取历史数据
        df = pd.read_csv(input_path, parse_dates=['date'])

        # 生成交易信号
        df_with_signals = generate_signals(df)

        # 保存分析结果
        df_with_signals.to_csv(output_path, index=False)
        print(f"分析结果已保存到 {output_path}")

        print("\n最近的交易信号：")
        print(df_with_signals.tail(10))

    except FileNotFoundError:
        print(f"错误：找不到输入文件 {input_path}。请先运行 get_fund_data.py 来获取数据。")
    except Exception as e:
        print(f"处理数据时发生错误：{e}")