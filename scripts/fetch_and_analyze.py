#!/usr/bin/env python3
import os
import sys
import json
import argparse
import datetime
import time

import numpy as np
import pandas as pd
import yfinance as yf
import openai

# ---------- 技术指标（简单实现） ----------
def sma(series, period):
    return series.rolling(period).mean()

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.rolling(period).mean()
    ma_down = down.rolling(period).mean()
    rs = ma_up / (ma_down + 1e-9)
    return 100 - (100 / (1 + rs))

def macd(series, fast=12, slow=26, signal=9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

# ---------- 获取历史价格 ----------
def fetch_history_by_ticker(ticker, period="1y", interval="1d"):
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval)
        if df.empty:
            return None
        df = df[['Close', 'Volume']]
        df = df.rename(columns={'Close':'close', 'Volume':'volume'})
        df.index = pd.to_datetime(df.index)
        return df
    except Exception as e:
        print(f"yfinance fetch error for {ticker}: {e}", file=sys.stderr)
        return None

# ---------- 分析单只基金/ETF ----------
def analyze_series(df):
    close = df['close']
    res = {}
    res['sma_5'] = sma(close, 5).iloc[-1]
    res['sma_20'] = sma(close, 20).iloc[-1]
    res['ema_12'] = ema(close, 12).iloc[-1]
    res['ema_26'] = ema(close, 26).iloc[-1]
    res['rsi_14'] = rsi(close, 14).iloc[-1]
    macd_line, signal_line, hist = macd(close)
    res['macd'] = macd_line.iloc[-1]
    res['macd_signal'] = signal_line.iloc[-1]
    res['macd_hist'] = hist.iloc[-1]
    res['last_close'] = close.iloc[-1]
    res['pct_change_5d'] = close.pct_change(5).iloc[-1]
    return res

# ---------- 调用 OpenAI（请在 Secrets 中放 OPENAI_API_KEY） ----------
def ask_ai_for_signal(ticker, metrics, recent_notes=""):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY not set in environment")
    openai.api_key = key

    # 简单 prompt，实际可按需改进（或把模型换成更专业的 finance model）
    prompt = f"""
You are a financial analysis assistant. Given the following numeric indicators for a fund/ETF ticker {ticker}, provide:
1) concise recommendation: BUY / HOLD / SELL
2) a short rationale (1-2 sentences)
3) risk level (low/medium/high)
4) any technical triggers to watch (e.g., "if price crosses SMA20 with volume > x")

Indicators (most recent):
{json.dumps(metrics, indent=2)}

Recent note: {recent_notes}

Please respond in JSON with keys: recommendation, rationale, risk, triggers.
    """

    # 使用 ChatCompletion 或 Completions（取决于 openai 版本）：
    try:
        resp = openai.ChatCompletion.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role":"user","content":prompt}],
            temperature=0.2,
            max_tokens=350
        )
        text = resp['choices'][0]['message']['content'].strip()
        # 尝试解析为 JSON（若模型已经返回 JSON）
        try:
            parsed = json.loads(text)
            return parsed, text
        except Exception:
            # 如果不是严格 JSON，返回原始文本并包一下
            return {"raw": text}, text
    except Exception as e:
        return {"error": str(e)}, ""

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

# ---------- 主流程 ----------
def main(args):
    ensure_dir("results")
    fund_list = []
    # 读取基金列表：每行一个 ticker 或 URL（这里示例以 ticker 为主）
    if args.fund_list and os.path.exists(args.fund_list):
        with open(args.fund_list, 'r', encoding='utf-8') as f:
            for line in f:
                s = line.strip()
                if s and not s.startswith('#'):
                    fund_list.append(s)
    else:
        # 默认示例：几个常见 ETF（你可以替换成基金 ticker）
        fund_list = ["VOO", "VTI", "SPY"]

    results = {}
    for t in fund_list:
        print(f"[{datetime.datetime.now()}] Processing {t}")
        df = fetch_history_by_ticker(t, period=args.period)
        if df is None or df.empty:
            print(f"  No data for {t}, skipping.")
            results[t] = {"error": "no data"}
            continue

        metrics = analyze_series(df)
        # optional: add a tiny textual summary
        recent_notes = f"Last close {metrics['last_close']:.2f}, 5d change {metrics['pct_change_5d']:.3f}"
        ai_res, ai_raw = ask_ai_for_signal(t, metrics, recent_notes=recent_notes)

        results[t] = {
            "metrics": metrics,
            "ai": ai_res,
            "ai_raw": ai_raw,
            "last_updated": datetime.datetime.utcnow().isoformat() + "Z"
        }
        # 避免请求过快
        time.sleep(1.5)

    # 保存结果
    out_file = args.output or f"results/analysis_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print("Saved ->", out_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fund-list", default="funds.txt", help="每行一个 ticker")
    parser.add_argument("--period", default="1y", help="yfinance period")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    main(args)
