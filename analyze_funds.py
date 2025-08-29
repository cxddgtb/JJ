import pandas as pd
import numpy as np
import ta
import akshare as ak
import datetime
import os
import re

# --- Configuration ---
FUND_CODES_FILE = "fund.txt"
README_FILE = "README.md"
HISTORY_DAYS = 120 # Need enough history for indicators like LLV(33), HHV(33), etc.
ANALYSIS_PERIOD_DAYS = 30 # Number of days to show in the README table

# --- Helper function for TDX-style SMA (Exponential Moving Average equivalent) ---
def tdx_sma(series, n, m):
    """
    Calculates TDX-style SMA (equivalent to EMA with specific alpha).
    SMA(X,N,M) is generally (M*X + (N-M)*Ref(SMA,1)) / N
    This is equivalent to EMA with alpha = M/N.
    The window for ta.trend.ema_indicator is related to alpha by alpha = 2/(window + 1).
    So, window = 2/alpha - 1 = 2/(M/N) - 1 = 2N/M - 1.
    """
    if series.empty or series.isnull().all():
        return pd.Series(np.nan, index=series.index)
    
    alpha = m / n
    if alpha <= 0 or alpha > 1: # Ensure alpha is valid, otherwise use default EMA logic
        # Fallback to standard EMA window if alpha is out of reasonable range
        # For TDX, M is usually small and positive, N >= M
        window = n
    else:
        # Ensure window is at least 1, and convert to int
        window = max(1, int(round(2 * n / m - 1)))
    
    return ta.trend.ema_indicator(series, window=window, fillna=False) # fillna=False to keep NaNs at start

# --- Data Fetching ---
def get_fund_codes():
    if not os.path.exists(FUND_CODES_FILE):
        print(f"Error: {FUND_CODES_FILE} not found. Please create it with fund codes, e.g., '161725' per line.")
        return []
    with open(FUND_CODES_FILE, 'r') as f:
        codes = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return codes

def fetch_fund_data(fund_code, start_date_str, end_date_str):
    print(f"Fetching data for fund: {fund_code} from {start_date_str} to {end_date_str}")
    try:
        # akshare's fund_nav_hist_em provides daily NAV (Net Asset Value)
        # For funds, we usually only have one 'close' price (NAV) per day.
        # OHLC for funds is generally not available in the same way as stocks.
        # We will use NAV as 'close' and approximate 'open', 'high', 'low' as 'close' for indicator calculations.
        df = ak.fund_nav_hist_em(symbol=fund_code, start_date=start_date_str, end_date=end_date_str)
        if df.empty:
            print(f"No data found for fund {fund_code} in the specified period.")
            return pd.DataFrame()

        df['日期'] = pd.to_datetime(df['日期'])
        df = df.set_index('日期')
        df = df.sort_index()

        # Rename columns to standard OHLC (Close is NAV)
        df.rename(columns={'单位净值': 'close'}, inplace=True)

        # Approximate OHLC for indicators that require it.
        # This is a significant simplification due to fund data nature.
        # open, high, low are approximated for indicators that expect them.
        df['open'] = df['close'].shift(1).fillna(df['close']) 
        df['high'] = df[['close', 'open']].max(axis=1) 
        df['low'] = df[['close', 'open']].min(axis=1)   
        df['volume'] = 0 # No volume data for fund NAV, set to 0

        # Drop columns not needed for TA, keep essential ones
        df = df[['open', 'high', 'low', 'close', 'volume']]

        # Fetch fund name
        fund_info = ak.fund_em_fund_name_dict()
        fund_name = fund_info.get(fund_code, fund_code)
        df['fund_name'] = fund_name

        return df
    except Exception as e:
        print(f"Error fetching data for {fund_code}: {e}")
        return pd.DataFrame()

# --- Indicator Implementations ---
# Indicator 1: 压力支撑主图指标 (Pressure Support Main Chart Indicator)
def calculate_indicator1(df_original):
    df = df_original.copy()
    if df.empty or len(df) < max(20, 32, 9, 7): # N=20, M=32, LLV/HHV 9, A8 lookback 7
        return df_original # Return original if not enough data

    N = 20
    M = 32
    P1 = 80
    P2 = 100

    # VAR1 (C+H+O+L)/4 approximated as C for fund NAV
    VAR1 = df['close']

    df['卖出'] = tdx_sma(VAR1, N, 1) * (1 + P1 / 1000)
    df['买入'] = tdx_sma(VAR1, M, 1) * (1 - P2 / 1000)

    # B signal: CROSS(C,买入) OR (L<买入 AND C>买入)
    cross_buy = (df['close'].shift(1) < df['买入'].shift(1)) & (df['close'] > df['买入'])
    # L<买入 AND C>买入 is simplified to C>买入 (as L ~ C)
    df['SIGNAL_B'] = (cross_buy | (df['close'] > df['买入'].shift(1))).astype(int)

    # S signal: CROSS(卖出,C) OR (H>卖出 AND C<卖出)
    cross_sell = (df['卖出'].shift(1) > df['close'].shift(1)) & (df['卖出'] < df['close'])
    # H>卖出 AND C<卖出 is simplified to C<卖出 (as H ~ C)
    df['SIGNAL_S'] = (cross_sell | (df['close'] < df['卖出'].shift(1))).astype(int)


    # 买进 signal
    # A3:=(C-LLV(L,9))/(HHV(H,9)-LLV(L,9))*100;
    llv_l_9 = df['low'].rolling(9).min()
    hhv_h_9 = df['high'].rolling(9).max()
    denominator_a3 = hhv_h_9 - llv_l_9
    A3 = pd.Series(np.nan, index=df.index)
    valid_indices_a3 = denominator_a3 != 0
    A3[valid_indices_a3] = (df['close'][valid_indices_a3] - llv_l_9[valid_indices_a3]) / denominator_a3[valid_indices_a3] * 100
    
    A4 = tdx_sma(A3, 3, 1)
    A5 = tdx_sma(A4, 3, 1)

    # A8:=100*EMA(EMA(C-REF(C,1),6),6)/EMA(EMA(ABS(C-REF(C,1)),6),6);
    change = df['close'].diff()
    abs_change = abs(change)
    ema_change = tdx_sma(change, 6, 1)
    ema_abs_change = tdx_sma(abs_change, 6, 1)
    double_ema_change = tdx_sma(ema_change, 6, 1)
    double_ema_abs_change = tdx_sma(ema_abs_change, 6, 1)
    
    A8 = pd.Series(np.nan, index=df.index)
    valid_indices_a8 = double_ema_abs_change != 0
    A8[valid_indices_a8] = 100 * double_ema_change[valid_indices_a8] / double_ema_abs_change[valid_indices_a8]

    # 买:=LLV(A8,2)=LLV(A8,7) AND COUNT(A8<0,2) AND CROSS(A8,MA(A8,2));
    buy_cond1 = (A8.rolling(2).min() == A8.rolling(7).min())
    buy_cond2 = (A8 < 0).rolling(2).sum() == 2 # COUNT(A8<0,2)
    ma_a8_2 = tdx_sma(A8, 2, 1)
    buy_cond3 = (A8.shift(1) < ma_a8_2.shift(1)) & (A8 > ma_a8_2) # CROSS(A8,MA(A8,2))
    df['SIGNAL_买进'] = (buy_cond1 & buy_cond2 & buy_cond3).astype(int)

    return df

# Indicator 2: 筹码意愿与买卖点副图指标 (Chips Intention and Buy/Sell Point Sub-Chart Indicator)
def calculate_indicator2(df_original):
    df = df_original.copy()
    if df.empty or len(df) < max(30, 25, 21, 10, 60): # HHV/LLV periods, approx_winner_range window
        return df_original

    # PART 1: 筹码震仓分析 (Chip Shakeout Analysis)
    # WINNER approximation: percentage of historical close prices within +/- 10% of current close.
    # This is a very rough approximation.
    def approx_winner_range(current_price, hist_prices, window=60):
        if len(hist_prices) < window:
            return 0 # Not enough history to calculate
        relevant_hist = hist_prices.iloc[-window:]
        lower_bound = 0.9 * current_price
        upper_bound = 1.1 * current_price
        # Ensure that relevant_hist is not empty for calculation
        if not relevant_hist.empty:
            return ((relevant_hist >= lower_bound) & (relevant_hist <= upper_bound)).sum() / len(relevant_hist) * 100
        return 0

    VAR2_list = []
    for i in range(len(df)):
        current_close = df['close'].iloc[i]
        hist_closes = df['close'].iloc[:i+1] # All data up to current point
        VAR2_list.append(approx_winner_range(current_close, hist_closes))
    VAR2_approx = pd.Series(VAR2_list, index=df.index)

    VAR4 = np.where(VAR2_approx < 0, 0, VAR2_approx) # VAR4:=IF(VAR2<0,0,VAR2)
    df['震仓'] = tdx_sma(pd.Series(VAR4, index=df.index), 10, 1) * 100 

    # PART 2: 超买超卖与买卖信号 (Overbought/Oversold and Buy/Sell Signals)
    V1 = df['low'].rolling(10).min() # LLV(LOW,10)
    V2 = df['high'].rolling(25).max() # HHV(HIGH,25)
    
    price_line_raw = pd.Series(np.nan, index=df.index)
    valid_indices_pl = (V2 - V1) != 0
    price_line_raw[valid_indices_pl] = (df['close'][valid_indices_pl] - V1[valid_indices_pl]) / (V2[valid_indices_pl] - V1[valid_indices_pl]) * 4
    
    df['价位线'] = tdx_sma(price_line_raw, 4, 1)

    df['SIGNAL_买入信号'] = ((df['价位线'].shift(1) < 0.3) & (df['价位线'] >= 0.3)).astype(int) # CROSS(价位线,0.3)
    df['SIGNAL_卖出信号'] = ((df['价位线'].shift(1) > 3.5) & (df['价位线'] <= 3.5)).astype(int) # CROSS(3.5,价位线)

    # PART 3: 主力吸筹分析 (Main Force Accumulation Analysis)
    VAR2Q = df['low'].shift(1) # REF(LOW,1)
    abs_diff_l = abs(df['low'] - VAR2Q)
    max_diff_l = (df['low'] - VAR2Q).apply(lambda x: max(x, 0)) # MAX(LOW-VAR2Q,0)
    
    # SMA(ABS(LOW-VAR2Q),3,1) / SMA(MAX(LOW-VAR2Q,0),3,1) * 100
    sma_abs_diff_l = tdx_sma(abs_diff_l, 3, 1)
    sma_max_diff_l = tdx_sma(max_diff_l, 3, 1)
    
    VAR3Q = pd.Series(np.nan, index=df.index)
    valid_indices_v3q = sma_max_diff_l != 0
    VAR3Q[valid_indices_v3q] = (sma_abs_diff_l[valid_indices_v3q] / sma_max_diff_l[valid_indices_v3q]) * 100
    VAR3Q = VAR3Q.fillna(0) # Replace inf/nan with 0 for safety

    if_cond_var4q = (df['close'] > 1.3 * df['close'].shift(1))
    var3q_adjusted = np.where(if_cond_var4q, VAR3Q * 10, VAR3Q / 10)
    df['VAR4Q'] = tdx_sma(pd.Series(var3q_adjusted, index=df.index), 3, 1)

    VAR5Q = df['low'].rolling(30).min() # LLV(LOW,30)
    VAR6Q = df['VAR4Q'].rolling(30).max() # HHV(VAR4Q,30)
    
    VAR7Q = 1 # VAR7Q:=IF(MA(CLOSE,58),1,0) - assuming MA(C,58) is calculable and positive, so it's 1

    if_cond_var8q = (df['low'] <= VAR5Q)
    var8q_raw = np.where(if_cond_var8q, (df['VAR4Q'] + VAR6Q * 2) / 2, 0) # Adjusted (VAR4Q+VAR6Q*2)/2
    VAR8Q = tdx_sma(pd.Series(var8q_raw, index=df.index), 3, 1) / 618 * VAR7Q

    df['VAR9Q'] = np.where(VAR8Q > 100, 100, VAR8Q)
    df['SIGNAL_吸筹'] = (df['VAR9Q'] > 0).astype(int) # Accumulation signal when > 0

    # PART 4: 多空走势与顶部预警 (Bull/Bear Trend and Top Warning)
    HHV_H_21 = df['high'].rolling(21).max()
    LLV_L_21 = df['low'].rolling(21).min()
    
    denominator_aa3_aa4 = HHV_H_21 - LLV_L_21
    AA3 = pd.Series(np.nan, index=df.index)
    AA4 = pd.Series(np.nan, index=df.index)
    
    valid_indices_aa = denominator_aa3_aa4 != 0
    AA3[valid_indices_aa] = (HHV_H_21[valid_indices_aa] - df['close'][valid_indices_aa]) / denominator_aa3_aa4[valid_indices_aa] * 100 - 10
    AA4[valid_indices_aa] = (df['close'][valid_indices_aa] - LLV_L_21[valid_indices_aa]) / denominator_aa3_aa4[valid_indices_aa] * 100

    AA3 = AA3.fillna(0)
    AA4 = AA4.fillna(0)

    AA5 = tdx_sma(AA4, 13, 8) 
    df['走势'] = np.ceil(tdx_sma(AA5, 13, 8)) 

    AA6 = tdx_sma(AA3, 21, 8) 
    df['SIGNAL_卖临界'] = (df['走势'] - AA6 > 85).astype(int)

    return df

# Indicator 3: 通达信主力进出副图指标 (TDX Main Force In/Out Sub-Chart Indicator)
def calculate_indicator3(df_original):
    df = df_original.copy()
    if df.empty or len(df) < max(33, 13, 7): # LLV/HHV 33, SMA 13, A2 lookback 7
        return df_original

    VAR1 = df['close'].shift(1) # REF((LOW+OPEN+CLOSE+HIGH)/4,1) approximated with close

    # 主力进场与洗盘 (Main Force Entry & Shakeout)
    abs_diff_low = abs(df['low'] - VAR1) # ABS(LOW-VAR1)
    max_diff_low = (df['low'] - VAR1).apply(lambda x: max(x, 0)) # MAX(LOW-VAR1,0)
    
    sma_abs_diff_low = tdx_sma(abs_diff_low, 13, 1)
    sma_max_diff_low = tdx_sma(max_diff_low, 10, 1)
    VAR2 = pd.Series(np.nan, index=df.index)
    valid_indices_v2 = sma_max_diff_low != 0
    VAR2[valid_indices_v2] = sma_abs_diff_low[valid_indices_v2] / sma_max_diff_low[valid_indices_v2]
    VAR2 = VAR2.fillna(0) 

    VAR3 = tdx_sma(VAR2, 10, 1)
    VAR4 = df['low'].rolling(33).min() # LLV(LOW,33)
    if_cond_var5 = (df['low'] <= VAR4) # IF(LOW<=VAR4
    var5_raw = np.where(if_cond_var5, VAR3, 0)
    VAR5 = tdx_sma(pd.Series(var5_raw, index=df.index), 3, 1)

    df['SIGNAL_主进'] = (VAR5 > VAR5.shift(1)).astype(int)
    df['SIGNAL_洗盘'] = (VAR5 < VAR5.shift(1)).astype(int)

    # 主力出场与冲顶 (Main Force Exit & Top Rush)
    abs_diff_high = abs(df['high'] - VAR1) # ABS(HIGH-VAR1)
    # MAX(HIGH-VAR1,0) for upward pressure, or MAX(VAR1-HIGH,0) for downward pressure
    # Interpreting as `MAX(df['high'] - VAR1, 0)` for upward momentum, and for VAR12 as for exhaustion.
    max_diff_high = (df['high'] - VAR1).apply(lambda x: max(x, 0)) 
    
    sma_abs_diff_high = tdx_sma(abs_diff_high, 13, 1)
    sma_max_diff_high = tdx_sma(max_diff_high, 10, 1)
    VAR12 = pd.Series(np.nan, index=df.index)
    valid_indices_v12 = sma_max_diff_high != 0
    VAR12[valid_indices_v12] = sma_abs_diff_high[valid_indices_v12] / sma_max_diff_high[valid_indices_v12]
    VAR12 = VAR12.fillna(0) 

    VAR13 = tdx_sma(VAR12, 10, 1)
    VAR14 = df['high'].rolling(33).max() # HHV(HIGH,33)
    if_cond_var15 = (df['high'] >= VAR14) # IF(HIGH>=VAR14
    var15_raw = np.where(if_cond_var15, VAR13, 0)
    VAR15 = tdx_sma(pd.Series(var15_raw, index=df.index), 3, 1)

    df['SIGNAL_主出'] = (VAR15 < VAR15.shift(1)).astype(int)
    df['SIGNAL_冲顶'] = (VAR15 > VAR15.shift(1)).astype(int)

    # 超卖与底部确认信号 (Oversold & Bottom Confirmation)
    A1 = df['close'].shift(2) # REF(CLOSE,2)
    max_c_diff = (df['close'] - A1).apply(lambda x: max(x, 0)) # MAX(CLOSE-A1,0)
    abs_c_diff = abs(df['close'] - A1) # ABS(CLOSE-A1)
    
    sma_max_c_diff = tdx_sma(max_c_diff, 7, 1)
    sma_abs_c_diff = tdx_sma(abs_c_diff, 7, 1)
    A2 = pd.Series(np.nan, index=df.index)
    valid_indices_a2 = sma_abs_c_diff != 0
    A2[valid_indices_a2] = (sma_max_c_diff[valid_indices_a2] / sma_abs_c_diff[valid_indices_a2]) * 100
    A2 = A2.fillna(0) 

    df['SIGNAL_波段介入点'] = (A2 < 19).astype(int)

    # 金山 (Golden Mountain)
    abs_l_diff = abs(df['low'] - df['low'].shift(1)) # ABS(L-REF(L,1))
    max_l_diff = (df['low'] - df['low'].shift(1)).apply(lambda x: max(x, 0)) # MAX(L-REF(L,1),0)
    
    sma_abs_l_diff = tdx_sma(abs_l_diff, 3, 1)
    sma_max_l_diff = tdx_sma(max_l_diff, 3, 1)
    VARC = pd.Series(np.nan, index=df.index)
    valid_indices_varc = sma_max_l_diff != 0
    VARC[valid_indices_varc] = sma_abs_l_diff[valid_indices_varc] / sma_max_l_diff[valid_indices_varc]
    VARC = VARC.fillna(0)

    if_cond_gold = (df['low'] <= df['low'].rolling(30).min()) # IF(L<=LLV(L,30)
    golden_mountain_raw = np.where(if_cond_gold, VARC, 0)
    df['SIGNAL_金山'] = (tdx_sma(pd.Series(golden_mountain_raw, index=df.index), 3, 1) > 0).astype(int) # Check if positive

    return df

# --- Signal Consolidation ---
def consolidate_signals(df):
    """
    Consolidates signals from multiple indicators into a single '买入', '卖出', or '观望' decision.
    Uses a scoring system and priority.
    """
    if df.empty:
        return '观望' 

    buy_score = 0
    sell_score = 0

    latest_signals = df.iloc[-1]

    # Indicator 1: 压力支撑主图指标
    if latest_signals.get('SIGNAL_S', 0) == 1: sell_score += 2 # Strong sell
    if latest_signals.get('SIGNAL_B', 0) == 1: buy_score += 2 # Strong buy
    if latest_signals.get('SIGNAL_买进', 0) == 1: buy_score += 1 # Moderate buy

    # Indicator 2: 筹码意愿与买卖点副图指标
    if latest_signals.get('SIGNAL_卖出信号', 0) == 1: sell_score += 2 # Strong sell
    if latest_signals.get('SIGNAL_买入信号', 0) == 1: buy_score += 2 # Strong buy
    if latest_signals.get('SIGNAL_吸筹', 0) == 1 and latest_signals.get('VAR9Q', 0) > 50: buy_score += 1.5 # Strong accumulation
    if latest_signals.get('SIGNAL_卖临界', 0) == 1: sell_score += 2 # Strong sell, top warning

    # Indicator 3: 主力进出副图指标
    if latest_signals.get('SIGNAL_主出', 0) == 1: sell_score += 2 # Strong sell
    if latest_signals.get('SIGNAL_冲顶', 0) == 1: sell_score += 2 # Strong sell
    if latest_signals.get('SIGNAL_主进', 0) == 1: buy_score += 2 # Strong buy
    if latest_signals.get('SIGNAL_波段介入点', 0) == 1: buy_score += 2 # Strong buy, oversold
    if latest_signals.get('SIGNAL_金山', 0) == 1: buy_score += 1 # Moderate buy, bottom confirmation
    if latest_signals.get('SIGNAL_洗盘', 0) == 1 and buy_score < 1: sell_score += 0.5 # Weak sell / uncertainty, only if no strong buy

    # Consolidation Logic
    if sell_score >= 3 and buy_score < 2: 
        return '卖出'
    elif buy_score >= 3 and sell_score < 2: 
        return '买入'
    elif buy_score >= 1.5 and sell_score < 1.5: # Moderate buy preference
        return '买入'
    elif sell_score >= 1.5 and buy_score < 1.5: # Moderate sell preference (e.g. if only one strong sell signal)
        return '卖出'
    else: # Default or balanced signals
        return '观望'

# --- Main Analysis Function ---
def perform_analysis_and_update_readme():
    print("Starting fund analysis and README update...")

    fund_codes = get_fund_codes()
    if not fund_codes:
        print("No fund codes found. Exiting.")
        return

    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=HISTORY_DAYS) 
    
    all_results = [] # Store all results for sorting and filtering

    for code in fund_codes:
        df_fund = fetch_fund_data(code, start_date.strftime('%Y%m%d'), end_date.strftime('%Y%m%d'))
        
        if df_fund.empty:
            fund_name = df_fund['fund_name'].iloc[0] if 'fund_name' in df_fund and not df_fund.empty else code
            all_results.append({'基金名称': fund_name, '日期': end_date.strftime('%Y-%m-%d'), '当前价格': 'N/A', '信号': '观望'})
            continue

        fund_name = df_fund['fund_name'].iloc[0] if 'fund_name' in df_fund else code

        # Calculate all indicators
        df_fund = calculate_indicator1(df_fund)
        df_fund = calculate_indicator2(df_fund)
        df_fund = calculate_indicator3(df_fund)
        
        # Get signals for the last ANALYSIS_PERIOD_DAYS
        # Iterate over the last `ANALYSIS_PERIOD_DAYS` to get signals for each day
        for i in range(1, min(ANALYSIS_PERIOD_DAYS + 1, len(df_fund) + 1)):
            current_day_df = df_fund.iloc[:- (min(ANALYSIS_PERIOD_DAYS, len(df_fund)) - i)] # Slice to include enough history for indicators
            
            if current_day_df.empty:
                continue

            signal = consolidate_signals(current_day_df)
            price = current_day_df['close'].iloc[-1]
            date = current_day_df.index[-1].strftime('%Y-%m-%d')
            all_results.append({'基金名称': fund_name, '日期': date, '当前价格': f'{price:.2f}', '信号': signal})
            
    # Sort results
    # Priority: Buy (1) > Sell (2) > Watch (3)
    signal_order = {'买入': 1, '卖出': 2, '观望': 3}
    
    # Sort first by fund name, then by date descending to prepare for unique filter
    # This helps ensure that for each fund-date, we get the desired latest signal if consolidate_signals was run multiple times.
    all_results_sorted_temp = sorted(all_results, key=lambda x: (x['基金名称'], x['日期']), reverse=True)

    # Filter to get only the latest signal for each fund-date pair if there were duplicates
    unique_results = {}
    for res in all_results_sorted_temp:
        key = (res['基金名称'], res['日期'])
        # Keep only the first occurrence for each fund-date (which is the latest run's signal)
        if key not in unique_results:
            unique_results[key] = res
    
    # Convert back to list and sort by signal priority for today's data, then by fund name, then by date descending
    final_sorted_results_list = list(unique_results.values())
    
    # Get today's signal for each fund for sorting
    today_date_str = end_date.strftime('%Y-%m-%d')
    today_signals_by_fund = {res['基金名称']: res['信号'] for res in final_sorted_results_list if res['日期'] == today_date_str}

    def custom_sort_key(res):
        fund_name = res['基金名称']
        signal_today = today_signals_by_fund.get(fund_name, '观望')
        return (signal_order.get(signal_today, 99), fund_name, res['日期']) # Sort by today's signal, then fund name, then date DESC

    final_sorted_results = sorted(final_sorted_results_list, key=custom_sort_key, reverse=True)
    
    # Group results by fund name for display in markdown
    fund_grouped_data = {}
    for res in final_sorted_results:
        fund_name = res['基金名称']
        if fund_name not in fund_grouped_data:
            fund_grouped_data[fund_name] = []
        fund_grouped_data[fund_name].append(res)
    
    # --- Generate Markdown Table ---
    markdown_table = "## 每日基金买卖点分析\n\n"
    markdown_table += "⚠️ **重要提示:** 以下分析基于通达信指标的Python近似实现，并假设基金净值（NAV）可近似为K线数据（开盘价、最高价、最低价均基于当日净值或前一日净值）。这与股票的真实K线数据有显著差异，部分复杂指标（如筹码分布）也进行了简化近似。因此**指标的准确性受到限制，仅供参考，不构成任何投资建议。**\n\n"
    markdown_table += f"更新时间: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} (UTC)\n\n"
    markdown_table += "| 基金名称 | 日期 | 当前价格 | 信号 |\n"
    markdown_table += "|----------|----------|----------|------|\n"

    # Iterate through funds ordered by today's signal
    for fund_name in sorted(fund_grouped_data.keys(), key=lambda f: signal_order.get(today_signals_by_fund.get(f, '观望'), 99)):
        # Take the last ANALYSIS_PERIOD_DAYS entries for each fund, sorted by date descending
        fund_entries = sorted([e for e in fund_grouped_data[fund_name] if e['基金名称'] == fund_name], 
                              key=lambda x: x['日期'], reverse=True)[:ANALYSIS_PERIOD_DAYS]
        
        for entry in fund_entries:
            markdown_table += f"| {entry['基金名称']} | {entry['日期']} | {entry['当前价格']} | {entry['信号']} |\n"

    # Update README.md
    if os.path.exists(README_FILE):
        with open(README_FILE, 'r', encoding='utf-8') as f:
            readme_content = f.read()
        
        start_marker = "## 每日基金买卖点分析"
        end_marker_pattern = r"^(##\s.+)" # Regex for finding the next H2 heading
        
        match = re.search(end_marker_pattern, readme_content[len(start_marker):], re.MULTILINE)
        
        if start_marker in readme_content:
            before_table = readme_content.split(start_marker)[0]
            if match:
                end_pos = readme_content.find(match.group(1), len(start_marker))
                after_table = readme_content[end_pos:]
                readme_content = before_table + markdown_table + "\n" + after_table
            else:
                readme_content = before_table + markdown_table
        else:
            readme_content += "\n" + markdown_table # Append if no section found

    else:
        readme_content = markdown_table # Create if README doesn't exist

    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(readme_content)

    print("Fund analysis completed and README.md updated.")

# --- GitHub Actions Workflow ---
def create_github_workflow():
    workflow_content = """
name: Update Fund Analysis

on:
  workflow_dispatch: # Allows manual triggering
  schedule:
    # Run every trading day at 14:00 Beijing time (6 AM UTC)
    # The market is usually closed by 15:00 in China. Fetching data at 14:00 gives latest official NAV.
    - cron: '0 6 * * 1-5'

jobs:
  analyze-funds:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout repository
      uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.x'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Run fund analysis
      run: python analyze_funds.py
      env:
        TZ: Asia/Shanghai # Set timezone for cron job context so that `datetime.date.today()` aligns

    - name: Commit and push changes
      run: |
        git config user.name 'github-actions[bot]'
        git config user.email 'github-actions[bot]@users.noreply.github.com'
        git add README.md
        git commit -m "Update fund analysis table" || echo "No changes to commit"
        git push
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
"""
    os.makedirs(".github/workflows", exist_ok=True)
    with open(".github/workflows/fund_analysis.yml", "w", encoding='utf-8') as f:
        f.write(workflow_content)
    print("GitHub Actions workflow 'fund_analysis.yml' created.")

# --- Update requirements.txt ---
def update_requirements_txt():
    required_packages = ["pandas", "numpy", "ta", "akshare"]
    existing_packages = set()
    if os.path.exists("requirements.txt"):
        with open("requirements.txt", 'r') as f:
            for line in f:
                stripped_line = line.strip()
                if stripped_line and not stripped_line.startswith('#'):
                    pkg_name = stripped_line.split('==')[0].split('<')[0].split('>')[0].split('~')[0].strip()
                    existing_packages.add(pkg_name)
    
    with open("requirements.txt", 'a+', encoding='utf-8') as f: 
        f.seek(0)
        content = f.read()
        f.seek(0, 2)
        for pkg in required_packages:
            if pkg not in existing_packages and pkg not in content: # Check if package or its variant is already there
                f.write(f"\n{pkg}")
    print("requirements.txt updated.")

# --- Create dummy fund.txt if not exists for testing ---
def create_dummy_fund_txt():
    if not os.path.exists(FUND_CODES_FILE):
        with open(FUND_CODES_FILE, 'w', encoding='utf-8') as f:
            f.write("# 基金代码列表，每行一个\n")
            f.write("000001 # 华夏成长混合\n") # Example fund code (E Fund Blue Chip Mixed)
            f.write("001475 # 嘉实沪深300ETF联接A\n") # Another example (ChinaAMC China Securities 500 ETF Link)
        print(f"Dummy {FUND_CODES_FILE} created with example fund codes for initial setup.")

# --- Main execution flow for local testing/setup ---
if __name__ == "__main__":
    create_dummy_fund_txt() # Ensure fund.txt exists for initial setup
    update_requirements_txt()
    create_github_workflow()
    
    # Run the analysis locally (for testing the script logic)
    print("\n--- Running initial fund analysis locally ---")
    perform_analysis_and_update_readme()
    print("--- Local analysis complete. Check README.md ---")
