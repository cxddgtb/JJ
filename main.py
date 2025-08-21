# ================================================================
#                Project Prometheus - Final Replicate AI Core
# ================================================================
import os
import sys
import json
import yaml
import logging
from datetime import datetime, timedelta
import pytz
import pandas as pd
import akshare as ak
import pandas_ta as ta
from fredapi import Fred
import matplotlib.pyplot as plt
import matplotlib
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, stop_after_attempt, wait_fixed
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import google.api_core.exceptions
import markdown
from sparklines import sparklines
import replicate # <--- 导入新的Replicate库

# --- Section 1: Setup & Configuration ---
try:
    with open('config.yaml', 'r', encoding='utf-8') as f: config = yaml.safe_load(f)
except FileNotFoundError: print("FATAL: config.yaml not found. Exiting."); sys.exit(1)
LOG_DIR = 'logs'; CHART_DIR = 'charts'
os.makedirs(LOG_DIR, exist_ok=True); os.makedirs(CHART_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s',
                    handlers=[logging.FileHandler(os.path.join(LOG_DIR, 'workflow.log'), mode='w'), logging.StreamHandler()])
matplotlib.use('Agg'); matplotlib.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']; matplotlib.rcParams['axes.unicode_minus'] = False
HISTORICAL_INDICATORS_PATH = 'portfolio/historical_indicators.json'

# --- API Configuration ---
# Gemini AI (Primary)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    AI_MODEL_GEMINI = genai.GenerativeModel('gemini-1.5-pro-latest')
else:
    logging.warning("GEMINI_API_KEY not found, primary AI is disabled.")
    AI_MODEL_GEMINI = None

# Replicate AI (Secondary)
REPLICATE_API_TOKEN = os.getenv('REPLICATE_API_TOKEN')
if not REPLICATE_API_TOKEN:
    logging.warning("REPLICATE_API_TOKEN not found, secondary AI is disabled.")

# --- The rest of the code is mostly the same ---
@retry(stop=stop_after_attempt(3), wait=wait_fixed(3))
def fetch_url_content_raw(url):
    headers = {'User-Agent': 'Mozilla/5.0 ...'}; response = requests.get(url, headers=headers, timeout=20); response.raise_for_status(); return response.content
def scrape_news():
    headlines = []
    for source in config['data_sources']['news_urls']:
        try:
            raw_html = fetch_url_content_raw(source['url']); soup = BeautifulSoup(raw_html, 'html.parser')
            for link in soup.find_all('a', href=True):
                if len(link.text.strip()) > 20 and '...' not in link.text: headlines.append(link.text.strip())
        except Exception as e: logging.error(f"从 {source['name']} 爬取新闻失败: {e}")
    return list(set(headlines))[:15]
@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def fetch_historical_data_akshare(code, days):
    df = ak.fund_etf_hist_em(symbol=code, period="daily", adjust="qfq")
    if df.empty: raise ValueError(f"AKShare未能获取到代码 {code} 的数据。")
    df = df.rename(columns={'日期': 'Date', '开盘': 'Open', '收盘': 'Close', '最高': 'High', '最低': 'Low', '成交量': 'Volume'})
    df['Date'] = pd.to_datetime(df['Date']); df = df.set_index('Date')
    cols_to_numeric = ['Open', 'Close', 'High', 'Low', 'Volume']
    df[cols_to_numeric] = df[cols_to_numeric].apply(pd.to_numeric, errors='coerce'); df.dropna(subset=cols_to_numeric, inplace=True)
    df = df[df.index >= (datetime.now() - timedelta(days=days))]; df = df.sort_index(); df['code'] = code; return df
def load_historical_indicators():
    try:
        with open(HISTORICAL_INDICATORS_PATH, 'r', encoding='utf-8') as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): return {}
def save_historical_indicators(data):
    with open(HISTORICAL_INDICATORS_PATH, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2, ensure_ascii=False)
def update_and_get_history(fund_code, new_rsi):
    history = load_historical_indicators()
    if fund_code not in history: history[fund_code] = []
    history[fund_code].insert(0, new_rsi); history[fund_code] = history[fund_code][:30]
    save_historical_indicators(history); return history[fund_code]

# --- Section 5: AI Council (Upgraded with Replicate AI Core) ---
def generate_template_report(context, reason="AI分析失败"):
    # ... (This function remains the same) ...
    return "...", "..."

def ultimate_ai_council(context):
    quant_analysis_for_ai = "最新技术指标及RSI近30日历史(最新值在最左侧):\n"
    for item in context.get('quant_analysis_data', []):
        history_str = ', '.join([f'{val:.2f}' for val in item.get('history', [])])
        quant_analysis_for_ai += f"  - **{item['name']} ({item['code']})**: {item['status']}。RSI={item.get('rsi', 'N/A')}, MACD信号={item.get('macd', 'N/A')}, 历史RSI=[{history_str}]\n"
    prompt = f"""... (The full Chinese prompt as in the previous version) ..."""

    # --- NEW: Dual-Core AI Logic with Replicate ---
    # Plan A: Try Gemini
    if AI_MODEL_GEMINI:
        try:
            logging.info("正在尝试使用主AI (Gemini)...")
            response = AI_MODEL_GEMINI.generate_content(prompt)
            report_text = response.text
            if "---DETAILED_REPORT_CUT---" in report_text: summary, detail = report_text.split("---DETAILED_REPORT_CUT---", 1)
            else: summary, detail = report_text, "AI未能生成独立的详细报告。"
            return summary.strip(), detail.strip()
        except Exception as gemini_e:
            logging.warning(f"主AI (Gemini) 调用失败: {gemini_e}")

    # Plan B: Try Replicate if Gemini failed
    if REPLICATE_API_TOKEN:
        try:
            logging.info("主AI失败，正在尝试使用备用AI (Replicate)...")
            # We use the official Qwen 1.5 4B Chat model on Replicate
            output = replicate.run(
                "replicate/qwen1.5-4b-chat:bce9629b13182a2b7274b7e8712a8a379c131434313fcfb836453663a8a92849",
                input={
                    "prompt": prompt,
                    "max_new_tokens": 4096 # Allow for long, detailed reports
                }
            )
            # The output is a generator, we piece it together
            report_text = "".join(output)
            
            if "---DETAILED_REPORT_CUT---" in report_text: summary, detail = report_text.split("---DETAILED_REPORT_CUT---", 1)
            else: summary, detail = report_text, "AI未能生成独立的详细报告。"
            return summary.strip(), detail.strip()
        except Exception as replicate_e:
            logging.error(f"备用AI (Replicate) 调用也失败了: {replicate_e}")
    
    # Plan C: Fallback to template
    return generate_template_report(context, reason="所有AI均调用失败")

# --- Section 6: Main Execution Block ---
def main():
    start_time = datetime.now(pytz.timezone('Asia/Shanghai')); logging.info(f"--- 普罗米修斯引擎启动于 {start_time.strftime('%Y-%m-%d %H:%M:%S')} (Replicate核心) ---")
    context = {'current_time': start_time.strftime('%Y-%m-%d %H:%M:%S %Z'), 'current_date': start_time.strftime('%Y-%m-%d')}
    with ThreadPoolExecutor(max_workers=10) as executor:
        news_future, eco_future = executor.submit(scrape_news), executor.submit(get_economic_data)
        fund_codes = [f['code'] for f in config['index_funds']]
        hist_data_futures = {code: executor.submit(fetch_historical_data_akshare, code, 365) for code in fund_codes}
        context['news'], context['economic_data'] = news_future.result(), eco_future.result()
        all_fund_data, quant_data_structured = {}, []
        for code in fund_codes:
            future = hist_data_futures[code]; fund_name = next((f['name'] for f in config['index_funds'] if f['code'] == code), code)
            item = {'name': fund_name, 'code': code}
            try:
                data = future.result(); all_fund_data[code] = data; data.ta.rsi(append=True); data.ta.macd(append=True)
                latest = data.iloc[-1]; current_rsi = round(latest['RSI_14'], 2)
                rsi_history = update_and_get_history(code, current_rsi)
                macd_signal = '金叉' if latest['MACD_12_26_9'] > latest['MACDs_12_26_9'] else '死叉'
                item.update({'status': '数据正常', 'rsi': current_rsi, 'macd': macd_signal, 'history': rsi_history})
            except Exception as e:
                logging.error(f"处理基金 {fund_name} ({code}) 的数据失败: {e}"); item.update({'status': '数据获取失败'})
            quant_data_structured.append(item)
        context['quant_analysis_data'] = quant_data_structured
    try:
        with open(config['user_profile']['portfolio_path'], 'r', encoding='utf-8') as f: context['portfolio'] = json.load(f)
    except Exception as e: logging.error(f"无法加载持仓文件: {e}"); context['portfolio'] = [{"错误": "无法加载持仓文件。"}]
    
    if not all_fund_data: summary_report, detail_report = (f"# 🔥 简报生成失败：无有效数据\n\n...", "请检查日志。")
    else: summary_report, detail_report = ultimate_ai_council(context)
    with open("README.md", "w", encoding="utf-8") as f: f.write(summary_report)
    report_filename = f"reports/report_{context['current_date']}.md"; os.makedirs('reports', exist_ok=True)
    with open(report_filename, "w", encoding='utf-8') as f: f.write(detail_report)
    # The email function is assumed to exist
    # send_email_report(...)
    end_time = datetime.now(pytz.timezone('Asia/Shanghai')); logging.info(f"--- 引擎结束于 {end_time.strftime('%Y-%m-%d %H:%M:%S')} ---")
    logging.info(f"--- 总运行时间: {end_time - start_time} ---")

if __name__ == "__main__":
    main()
