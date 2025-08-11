"""
读取 funds.json，计算常见技术指标并给出买/卖信号。

输出示例： data/signals.json
"""
import json
import argparse
from datetime import datetime
import pandas as pd
import numpy as np


def sma(series, window):
    return series.rolling(window).mean()


def ema(series, window):
    return series.ewm(span=window, adjust=False).mean()


def rsi(series, window=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.rolling(window).mean()
    ma_down = down.rolling(window).mean()
    rs = ma_up / (ma_down.replace(0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    return rsi


def macd(series, fast=12, slow=26, signal=9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def analyze_timeseries(history):
    # history: list of { 'date':'YYYY-MM-DD', 'value': float }
    df = pd.DataFrame(history)
    if 'date' not in df.columns or 'value' not in df.columns:
        return {'error': 'no timeseries'}
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    df.set_index('date', inplace=True)
    series = df['value'].astype(float)

    df['sma_short'] = sma(series, 10)
    df['sma_long'] = sma(series, 30)
    df['rsi'] = rsi(series, 14)
    macd_line, signal_line, hist = macd(series)
    df['macd'] = macd_line
    df['macd_signal'] = signal_line

    # 简单信号规则示例：
    # 买入：短期 SMA 上穿长期 SMA，且 RSI < 70
    # 卖出：短期 SMA 下穿长期 SMA，或 RSI > 80
    df['sma_cross'] = (df['sma_short'] - df['sma_long']).apply(np.sign)
    df['sma_cross_change'] = df['sma_cross'].diff()

    latest = df.dropna().iloc[-1]

    signals = []
    # 检查交叉
    if latest['sma_cross_change'] == 2:  # -1 -> +1
        signals.append('BUY: SMA cross up')
    if latest['sma_cross_change'] == -2:
        signals.append('SELL: SMA cross down')

    if latest['rsi'] > 80:
        signals.append('SELL: RSI overbought')
    if latest['rsi'] < 30:
        signals.append('BUY: RSI oversold')

    # MACD 线与信号线的关系
    if latest['macd'] > latest['macd_signal']:
        signals.append('MACD positive')
    else:
        signals.append('MACD negative')

    return {
        'last_date': str(latest.name.date()),
        'last_value': float(series.iloc[-1]),
        'signals': signals,
        'summary': df.tail(5).to_dict(orient='index')
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--in', dest='infile', default='data/funds.json')
    parser.add_argument('--out', dest='outfile', default='data/signals.json')
    args = parser.parse_args()

    with open(args.infile, 'r', encoding='utf-8') as f:
        funds = json.load(f)

    out = []
    for item in funds:
        try:
            hist = item.get('history')
            if not hist:
                out.append({'source': item.get('source'), 'error': 'no history'})
                continue
            analysis = analyze_timeseries(hist)
            out.append({'source': item.get('source'), 'name': item.get('name'), 'analysis': analysis})
        except Exception as e:
            out.append({'source': item.get('source'), 'error': str(e)})

    with open(args.outfile, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print('signals saved ->', args.outfile)


if __name__ == '__main__':
    main()
