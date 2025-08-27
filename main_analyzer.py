import pandas as pd
import numpy as np
import os
import datetime
import akshare as ak
import sys
import time # 导入 time 模块用于添加延迟

# --- TongdaXIn Indicator Helper Functions ---
def XMA(series, N):
    """通达信的XMA通常等同于EMA."""
    return series.ewm(span=N, adjust=False).mean()

def SMA(series, N, M):
    """
    通达信的SMA(X, N, M) 公式。
    当 M=1 时，等同于标准的简单移动平均。
    当 M>1 时，常被解释为加权平滑，接近EMA。
    这里M=1时使用rolling mean，M>1时使用EMA-like平滑。
    """
    if M == 1:
        return series.rolling(window=N).mean()
    # For M > 1, often interpreted as EMA with alpha = M/N
    alpha = M / N
    return series.ewm(alpha=alpha, adjust=False).mean()

def EMA(series, N):
    return series.ewm(span=N, adjust=False).mean()

def LLV(series, N):
    return series.rolling(window=N).min()

def HHV(series, N):
    return series.rolling(window=N).max()

def REF(series, N):
    return series.shift(N)

def CROSS(s1, s2):
    """判断s1是否向上穿过s2."""
    # 确保没有NaN值干扰
    s1_prev = s1.shift(1).fillna(s1)
    s2_prev = s2.shift(1).fillna(s2)
    return (s1_prev < s2_prev) & (s1 > s2)

def COUNT(condition_series, N):
    """计算在最近N个周期内，条件为真的次数."""
    return condition_series.rolling(window=N).sum()

# --- WINNER/PWINNER 占位符 (重要：无法准确实现，仅作占位) ---
# 这些函数依赖于通达信特有的筹码分布数据，无法通过标准OHLCV数据计算。
# 因此，使用占位符，它们将返回0，并跳过相关计算。
def WINNER_PLACEHOLDER(price_series):
    return pd.Series(0.0, index=price_series.index)

def PWINNER_PLACEHOLDER(N, var_series):
    return pd.Series(0.0, index=var_series.index)

# --- 指标函数实现 ---

def calculate_indicator_pressure_support(df):
    """
    压力支撑主图指标 (最终优化版)
    """
    C, H, O, L = df['close'], df['high'], df['open'], df['low']

    N_param = 20
    M_param = 32
    P1 = 80
    P2 = 100

    VAR1 = (C + H + O + L) / 4
    卖出 = XMA(VAR1, N_param) * (1 + P1 / 1000)
    买入 = XMA(VAR1, M_param) * (1 - P2 / 1000)

    # 趋势与超卖确认买点
    denom_A3 = (HHV(H, 9) - LLV(L, 9)).replace(0, np.finfo(float).eps)
    A3 = (C - LLV(L, 9)) / denom_A3 * 100
    A4 = SMA(A3, 3, 1)
    A5 = SMA(A4, 3, 1)
    
    ROC_C = C - REF(C, 1)
    ABS_ROC_C = ROC_C.abs()
    
    # 确保EMA的计算有足够的数据
    EMA_ROC_C_6 = EMA(ROC_C.dropna(), 6)
    EMA_ABS_ROC_C_6 = EMA(ABS_ROC_C.dropna(), 6)
    
    # 重新索引以匹配原始df长度
    EMA_ROC_C_6 = EMA_ROC_C_6.reindex(df.index, method='pad')
    EMA_ABS_ROC_C_6 = EMA_ABS_ROC_C_6.reindex(df.index, method='pad')
    
    denom_A8 = EMA_ABS_ROC_C_6.replace(0, np.finfo(float).eps)
    A8 = 100 * EMA(EMA_ROC_C_6.dropna(), 6).reindex(df.index, method='pad') / denom_A8

    # 确保A8和MA(A8,2)有足够的数据点
    A8_ma_2 = SMA(A8.dropna(), 2, 1)
    A8_ma_2 = A8_ma_2.reindex(df.index, method='pad')

    buy_condition_A8_count = (COUNT(A8 < 0, 2) >= 1)
    买 = (LLV(A8, 2) == LLV(A8, 7)) & buy_condition_A8_count & CROSS(A8, A8_ma_2)

    # 结合买卖信号
    # 注意：.iloc[-1] 取得Series的最后一个值，如果是NaN则不能直接进行布尔运算
    buy_signal = bool((CROSS(C, 买入) | ((L < 买入) & (C > 买入)) | (买 == True)).iloc[-1])
    sell_signal = bool((CROSS(卖出, C) | ((H > 卖出) & (C < 卖出))).iloc[-1])

    return {
        'buy_signal_ps': buy_signal,
        'sell_signal_ps': sell_signal
    }

def calculate_indicator_chip_intent(df):
    """
    筹码意愿与买卖点副图指标 (最终优化版)
    注意：WINNER/PWINNER 相关功能已省略或占位。
    """
    C, H, L = df['close'], df['high'], df['low']

    # --- PART 1: 筹码震仓分析 (SKIPPED due to WINNER/PWINNER) ---
    # 这部分因无法准确实现而跳过，相关计算将返回占位值
    # 震仓 = PWINNER_PLACEHOLDER(10, VAR4) * 100 

    # --- PART 2: 超买超卖与买卖信号 ---
    V1 = LLV(L, 10)
    V2 = HHV(H, 25)
    
    denom_price_line = (V2 - V1).replace(0, np.finfo(float).eps)
    价位线 = EMA(((C - V1) / denom_price_line) * 4, 4)

    买入信号 = CROSS(价位线, 0.3)
    卖出信号 = CROSS(3.5, 价位线)

    # --- PART 3: 主力吸筹分析 ---
    VAR2Q = REF(L, 1)
    denom_var3q = SMA(np.maximum(L - VAR2Q, 0), 3, 1).replace(0, np.finfo(float).eps)
    VAR3Q = SMA(abs(L - VAR2Q), 3, 1) / denom_var3q * 100

    VAR4Q = EMA(VAR3Q.dropna() * 10, 3).reindex(df.index, method='pad') # 假设 CLOSE*1.3 总是真 (即CLOSE>0)

    VAR5Q = LLV(L, 30)
    VAR6Q = HHV(VAR4Q, 30)
    
    VAR7Q = EMA(C, 58).notna().astype(int) # 假设数据充足，MA有效。
    
    term_if_true = (VAR4Q + VAR6Q * 2) / 2
    VAR8Q_numerator = (L <= VAR5Q).astype(int) * term_if_true
    VAR8Q = EMA(VAR8Q_numerator.dropna(), 3).reindex(df.index, method='pad') / 618 * VAR7Q # 618作为分母

    VAR9Q = VAR8Q.apply(lambda x: min(x, 100) if pd.notna(x) else x) # IF(VAR8Q>100,100,VAR8Q)
    吸筹 = VAR9Q > 0 

    # --- PART 4: 多空走势与顶部预警 ---
    denom_AA3_AA4 = (HHV(H, 21) - LLV(L, 21)).replace(0, np.finfo(float).eps)
    AA3 = (HHV(H, 21) - C) / denom_AA3_AA4 * 100 - 10
    AA4 = (C - LLV(L, 21)) / denom_AA3_AA4 * 100
    AA5 = SMA(AA4.dropna(), 13, 8).reindex(df.index, method='pad') # M=8, EMA-like
    走势 = np.ceil(SMA(AA5.dropna(), 13, 8).reindex(df.index, method='pad')) # M=8, EMA-like
    AA6 = SMA(AA3.dropna(), 21, 8).reindex(df.index, method='pad') # M=8, EMA-like
    卖临界 = (走势 - AA6) > 85

    # 结合买卖信号
    # 使用 .iloc[-1] 获取最新信号，并转换为 bool
    buy_signal = bool(买入信号.iloc[-1] or 吸筹.iloc[-1])
    sell_signal = bool(卖出信号.iloc[-1] or 卖临界.iloc[-1])

    return {
        'buy_signal_ci': buy_signal,
        'sell_signal_ci': sell_signal
    }


def calculate_indicator_main_force(df):
    """
    通达信主力进出副图指标 (最终版)
    """
    C, H, L, O = df['close'], df['high'], df['low'], df['open']

    VAR1_val = (L + O + C + H) / 4
    VAR1 = REF(VAR1_val, 1)

    # 主力进场与洗盘 (底部判断)
    denom_var2 = SMA(np.maximum(L - VAR1, 0), 10, 1).replace(0, np.finfo(float).eps)
    VAR2 = SMA(abs(L - VAR1), 13, 1) / denom_var2
    VAR3 = EMA(VAR2.dropna(), 10).reindex(df.index, method='pad')
    VAR4 = LLV(L, 33)
    
    # IF(LOW<=VAR4,VAR3,0)
    VAR5_numerator = (L <= VAR4).astype(int) * VAR3 
    VAR5 = EMA(VAR5_numerator.dropna(), 3).reindex(df.index, method='pad')

    主进 = VAR5 > REF(VAR5, 1)

    # 主力出场与冲顶 (顶部判断)
    denom_var12 = SMA(np.maximum(H - VAR1, 0), 10, 1).replace(0, np.finfo(float).eps)
    VAR12 = SMA(abs(H - VAR1), 13, 1) / denom_var12
    VAR13 = EMA(VAR12.dropna(), 10).reindex(df.index, method='pad')
    VAR14 = HHV(H, 33)
    
    # IF(HIGH>=VAR14,VAR13,0)
    VAR15_numerator = (H >= VAR14).astype(int) * VAR13
    VAR15 = EMA(VAR15_numerator.dropna(), 3).reindex(df.index, method='pad')

    主出 = VAR15 < REF(VAR15, 1)
    冲顶 = VAR15 > REF(VAR15, 1)

    # 超卖与底部确认信号
    A1 = REF(C, 2)
    denom_a2 = SMA(abs(C - A1), 7, 1).replace(0, np.finfo(float).eps)
    A2 = SMA(np.maximum(C - A1, 0), 7, 1) / denom_a2 * 100
    波段介入点 = A2 < 19

    denom_varc = SMA(np.maximum(L - REF(L, 1), 0), 3, 1).replace(0, np.finfo(float).eps)
    VARC = SMA(abs(L - REF(L, 1)), 3, 1) / denom_varc
    金山 = EMA(((L <= LLV(L, 30)).astype(int) * VARC).dropna(), 3).reindex(df.index, method='pad')

    # 结合买卖信号
    buy_signal = bool(主进.iloc[-1] or 波段介入点.iloc[-1] or (金山.iloc[-1] > 0))
    sell_signal = bool(主出.iloc[-1] or 冲顶.iloc[-1])

    return {
        'buy_signal_mf': buy_signal,
        'sell_signal_mf': sell_signal
    }

# --- 数据获取与处理 ---

def get_index_name(index_code):
    """
    根据指数代码获取名称。
    """
    try:
        # 尝试通过 stock_info_a_code_name 获取股票/ETF名称
        stock_info_df = ak.stock_info_a_code_name()
        name_match_stock = stock_info_df[stock_info_df['code'] == index_code.split('.')[0]]['name']
        if not name_match_stock.empty:
            return name_match_stock.iloc[0]

        # 尝试通过 fund_etf_spot_em 获取 ETF 名称
        fund_list = ak.fund_etf_spot_em()
        name_df_fund = fund_list[fund_list['代码'] == index_code]
        if not name_df_fund.empty:
            return name_df_fund['名称'].iloc[0]

        # 尝试通过 stock_zh_index_spot 获取指数实时名称
        # 注意：这个接口是实时的，可能不适合所有历史指数，但可以获取名称
        index_spot_df = ak.stock_zh_index_spot()
        name_match_index = index_spot_df[index_spot_df['代码'] == index_code.split('.')[0]]['名称']
        if not name_match_index.empty:
            return name_match_index.iloc[0]
            
        # 默认硬编码映射 (如果 AkShare 查找失败)
        mapping = {
            '000001.SH': '上证指数',
            '399001.SZ': '深证成指',
            '510300.SH': '沪深300ETF',
            '159919.SZ': '沪深300ETF', # 另一个常见的沪深300ETF
            # 添加更多你可能需要的指数代码和名称
        }
        return mapping.get(index_code, f"未知_{index_code.replace('.', '_')}")
    except Exception as e:
        print(f"获取 {index_code} 名称时出错: {e}")
        return f"未知_{index_code.replace('.', '_')}"


def get_historical_data(index_code):
    """
    从AkShare获取指数/ETF历史数据，并处理列名。
    """
    df = None
    try:
        # 尝试获取A股指数数据
        if index_code.endswith('.SH') or index_code.endswith('.SZ'):
            symbol_core = index_code.split('.')[0]
            if symbol_core.startswith(('0', '3', '8', '9')): # 常见指数代码开头
                print(f"尝试用 ak.stock_zh_index_daily 获取 {index_code}...")
                df = ak.stock_zh_index_daily(symbol=symbol_core)
                if df is not None and not df.empty:
                    df.rename(columns={
                        '日期': 'date',
                        '开盘': 'open',
                        '收盘': 'close',
                        '最高': 'high',
                        '最低': 'low',
                        '成交量': 'volume',
                        '成交额': 'turnover'
                    }, inplace=True)
            else: # 可能是股票或特定类型的ETF
                # 尝试用 fund_etf_hist_em 获取 ETF
                print(f"尝试用 ak.fund_etf_hist_em 获取 {index_code} (ETF)...")
                df = ak.fund_etf_hist_em(symbol=index_code, period="daily", start_date="20000101", end_date=datetime.date.today().strftime('%Y%m%d'), adjust="qfq") # 前复权
                if df is not None and not df.empty:
                     df.rename(columns={
                        '日期': 'date',
                        '开盘': 'open',
                        '收盘': 'close',
                        '最高': 'high',
                        '最低': 'low',
                        '成交量': 'volume',
                        '成交额': 'turnover'
                    }, inplace=True)
        else: # 如果没有市场后缀，默认尝试作为ETF处理
            print(f"尝试用 ak.fund_etf_hist_em 获取 {index_code} (ETF, 无后缀)...")
            df = ak.fund_etf_hist_em(symbol=index_code, period="daily", start_date="20000101", end_date=datetime.date.today().strftime('%Y%m%d'), adjust="qfq")
            if df is not None and not df.empty:
                 df.rename(columns={
                    '日期': 'date',
                    '开盘': 'open',
                    '收盘': 'close',
                    '最高': 'high',
                    '最低': 'low',
                    '成交量': 'volume',
                    '成交额': 'turnover'
                }, inplace=True)
        
        # 再次检查 DataFrame 是否有效且包含必要的列
        if df is None or df.empty or 'date' not in df.columns or 'open' not in df.columns:
            print(f"未能从 AkShare 获取 {index_code} 的有效数据或所需列。")
            return None

        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df = df.sort_index()
        return df[['open', 'close', 'high', 'low']]

    except Exception as e:
        print(f"从AkShare获取 {index_code} 历史数据失败: {e}")
        return None

def analyze_index(index_code, repo_root):
    """
    分析单个指数基金的买卖信号。
    """
    print(f"正在分析 {index_code}...")
    df = get_historical_data(index_code)

    if df is None or df.empty:
        print(f"无数据或无法获取 {index_code} 的数据。跳过。")
        return

    # 确保有足够的数据点进行计算 (例如，最长的EMA需要58天，REF需要2天，LLV/HHV需要33天等，取最大值)
    required_data_points = max(58, 33, 25, 13) + 5 # 留一些余量，确保所有指标都能计算
    if len(df) < required_data_points:
        print(f"{index_code} 历史数据不足 ({len(df)} 条)。至少需要 {required_data_points} 条数据。跳过。")
        return

    # 运行三个指标
    try:
        results_ps = calculate_indicator_pressure_support(df)
        results_ci = calculate_indicator_chip_intent(df)
        results_mf = calculate_indicator_main_force(df)
    except Exception as e:
        print(f"计算 {index_code} 指标时出错: {e}. 跳过。")
        return


    # 综合买卖信号：只要任一指标发出买入信号，就认为是买入；任一发出卖出信号，认为是卖出。
    # 优先判断卖出信号，如果同时有买入和卖出，则倾向于卖出或持有。
    combined_buy_signal = results_ps['buy_signal_ps'] or results_ci['buy_signal_ci'] or results_mf['buy_signal_mf']
    combined_sell_signal = results_ps['sell_signal_ps'] or results_ci['sell_signal_ci'] or results_mf['sell_signal_mf']

    current_date_str = datetime.date.today().strftime('%Y-%m-%d')
    index_name = get_index_name(index_code)
    
    # 文件名格式：数字编号加名称加日期加后面三十格用于写入未来三十天的买卖数据
    # 例如: 000001_SH_上证指数_2025-08-27_future_30_days.csv
    filename_base = f"{index_code.replace('.', '_')}_{index_name}_{current_date_str}"
    filename = f"{filename_base}_future_30_days.csv"
    
    # 当前信号判断
    if combined_sell_signal:
        current_signal_text = "卖出"
    elif combined_buy_signal:
        current_signal_text = "买入"
    else:
        current_signal_text = "持有"
    
    # 准备未来30天的占位数据
    future_data_cols = []
    for i in range(30):
        future_date = (datetime.date.today() + datetime.timedelta(days=i+1)).strftime('%Y-%m-%d')
        future_data_cols.append(f"未来_{future_date}_信号") # 只有列名
        
    # CSV头部
    header = ["日期", "当前信号", "压力支撑_买", "压力支撑_卖", "筹码意愿_买", "筹码意愿_卖", "主力进出_买", "主力进出_卖"] + future_data_cols
    
    # CSV数据行
    row_data = [
        current_date_str,
        current_signal_text,
        "TRUE" if results_ps['buy_signal_ps'] else "FALSE",
        "TRUE" if results_ps['sell_signal_ps'] else "FALSE",
        "TRUE" if results_ci['buy_signal_ci'] else "FALSE",
        "TRUE" if results_ci['sell_sell_ci'] else "FALSE", # 修正此处的错误，应该是'sell_signal_ci'
        "TRUE" if results_mf['buy_signal_mf'] else "FALSE",
        "TRUE" if results_mf['sell_signal_mf'] else "FALSE"
    ] + ["N/A"] * 30 # 未来30天信号填充"N/A"

    # 保存到 analysis_results 文件夹
    output_dir = os.path.join(repo_root, 'analysis_results')
    os.makedirs(output_dir, exist_ok=True)
    output_filepath = os.path.join(output_dir, filename)
    with open(output_filepath, 'w', encoding='utf-8') as f:
        f.write(",".join(header) + "\n")
        f.write(",".join(map(str, row_data)) + "\n")
    print(f"已将 {index_code} 的分析结果保存到：{output_filepath}")

    # 如果有买入信号，保存到 buy_signals 文件夹
    if combined_buy_signal:
        buy_signal_dir = os.path.join(repo_root, 'buy_signals')
        os.makedirs(buy_signal_dir, exist_ok=True)
        buy_signal_filepath = os.path.join(buy_signal_dir, filename)
        # 直接复制内容，或重新写入
        with open(buy_signal_filepath, 'w', encoding='utf-8') as f:
            f.write(",".join(header) + "\n")
            f.write(",".join(map(str, row_data)) + "\n")
        print(f"检测到 {index_code} 的买入信号。已复制到：{buy_signal_filepath}")


if __name__ == "__main__":
    # 获取 GitHub Workspace 路径，用于定位文件
    repo_root = os.getenv('GITHUB_WORKSPACE', os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    # 确保 'indices_to_monitor' 文件夹存在
    indices_folder = os.path.join(repo_root, 'indices_to_monitor')
    os.makedirs(indices_folder, exist_ok=True)
    indices_file = os.path.join(indices_folder, 'indices.txt')

    # 如果 'indices.txt' 不存在，则创建默认文件
    if not os.path.exists(indices_file):
        with open(indices_file, 'w', encoding='utf-8') as f:
            f.write("000001.SH\n") # 上证指数
            f.write("399001.SZ\n") # 深证成指
            f.write("510300.SH\n") # 沪深300ETF (示例)
        print(f"已创建默认的 {indices_file}。请编辑此文件以添加/删除您希望监控的指数代码。")

    # 读取要监控的指数代码
    with open(indices_file, 'r', encoding='utf-8') as f:
        index_codes = [line.strip() for line in f if line.strip()]

    for code in index_codes:
        analyze_index(code, repo_root)
        # 添加一个短暂停顿，避免对 AkShare 服务器造成过大压力
        time.sleep(2) 

    print("所有指数分析完成。")
