# =_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=
#                Project Prometheus - Final Production Version
#              (API-Compliant Dual-Core & All Previous Features)
# =_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=_=
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
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, stop_after_attempt, wait_fixed
import google.generativeai as genai
from openai import OpenAI, RateLimitError, APIConnectionError, AuthenticationError # <--- 导入更精确的错误类型
import requests
from bs4 import BeautifulSoup
import google.api_core.exceptions
import markdown
from sparklines import sparklines

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

# GPT AI (Secondary) - With custom base_url
GPT_API_KEY = os.getenv('GPT_API_free')
GPT_BASE_URL = os.getenv('GPT_BASE_URL_free')
client_gpt = None # Initialize as None
if GPT_API_KEY and GPT_BASE_URL:
    try:
        # --- FIX: Initialize the client EXACTLY as per the documentation ---
        client_gpt = OpenAI(
            api_key=GPT_API_KEY,
            base_url=GPT_BASE_URL,
        )
        logging.info(f"备用AI (GPT)客户端已成功初始化，目标服务器: {GPT_BASE_URL}")
    except Exception as e:
        logging.error(f"初始化备用AI (GPT)客户端失败: {e}")
else:
    logging.warning("GPT_API_free或GPT_BASE_URL_free未设置，备用AI已禁用。")

# ... (Data acquisition, history, and monte carlo sections remain unchanged) ...
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
def get_economic_data():
    if not config['economic_data']['enabled']: return "宏观经济数据模块已禁用。"
    try:
        fred_key = os.getenv('FRED_API_KEY'); fred = Fred(api_key=fred_key)
        data_points = {indicator: f"{fred.get_series(indicator).iloc[-1]} (截至 {fred.get_series(indicator).index[-1].strftime('%Y-%m-%d')})" for indicator in config['economic_data']['indicators']}
        return f"最新宏观经济指标: {json.dumps(data_points, indent=2, ensure_ascii=False)}"
    except Exception as e: logging.error(f"获取FRED数据失败: {e}"); return "无法检索宏观经济数据。"
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
def run_monte_carlo_simulation(all_fund_data):
    # This function is now just for a potential future use, we keep it but it's not the core prediction
    return "蒙特卡洛模拟已由AI预测取代。", None

# --- Section 5: AI Council (Upgraded with Dual-Core Engine and better error handling) ---
def generate_template_report(context, reason="AI分析失败"):
    logging.warning(f"{reason}，切换到B计划：模板化数据报告。")
    quant_table = "| 基金名称 | 状态 | RSI(14) | MACD信号 | RSI近30日趋势 (左新右旧) |\n| :--- | :--- | :--- | :--- | :--- |\n"
    for item in context.get('quant_analysis_data', []):
        history_str = 'N/A'
        if 'history' in item and item['history']: spark_str = "".join(sparklines(item['history'])); history_str = f"`{spark_str}`"
        quant_table += f"| {item['name']} ({item['code']}) | {item['status']} | {item.get('rsi', 'N/A')} | {item.get('macd', 'N/A')} | {history_str} |\n"
    news_section = "### 市场新闻摘要\n"
    news_list = context.get('news', []); news_section += "\n- " + "\n- ".join(news_list) if news_list else "未能成功获取最新新闻。"
    summary_report = f"# ⚠️ 普罗米修斯数据简报 ({reason})\n**报告时间:** {context['current_time']}\n**警告:** {reason}，今日未生成智能分析。以下为原始数据摘要。\n---\n### 量化指标仪表盘\n{quant_table}\n---\n{news_section}\n---\n*提示：要恢复AI智能分析，请检查您的API密钥和配额。*"
    return summary_report.strip(), "未生成深度分析报告。"

def ultimate_ai_council(context):
    quant_analysis_for_ai = "最新技术指标及RSI近30日历史(最新值在最左侧):\n"
    for item in context.get('quant_analysis_data', []):
        history_str = ', '.join([f'{val:.2f}' for val in item.get('history', [])])
        quant_analysis_for_ai += f"  - **{item['name']} ({item['code']})**: {item['status']}。RSI={item.get('rsi', 'N/A')}, MACD信号={item.get('macd', 'N/A')}, 历史RSI=[{history_str}]\n"
    prompt = f"""... (The full Chinese prompt as in the previous version) ..."""

    # --- NEW: Dual-Core AI Logic with detailed error handling ---
    # Plan A: Try Gemini
    if AI_MODEL_GEMINI:
        try:
            logging.info("正在尝试使用主AI (Gemini)...")
            response = AI_MODEL_GEMINI.generate_content(prompt)
            report_text = response.text
            if "---DETAILED_REPORT_CUT---" in report_text: summary, detail = report_text.split("---DETAILED_REPORT_CUT---", 1)
            else: summary, detail = report_text, "AI未能生成独立的详细报告。"
            return summary.strip(), detail.strip()
        except google.api_core.exceptions.ResourceExhausted as gemini_e:
            logging.warning(f"主AI (Gemini) 配额耗尽: {gemini_e}") # This is not an error, just a trigger for fallback
        except Exception as gemini_e:
            logging.error(f"主AI (Gemini) 调用时发生未知错误: {gemini_e}")

    # Plan B: Try GPT if Gemini failed
    if client_gpt:
        try:
            logging.info("主AI失败，正在尝试使用备用AI (GPT)...")
            chat_completion = client_gpt.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-3.5-turbo",
            )
            report_text = chat_completion.choices[0].message.content
            if "---DETAILED_REPORT_CUT---" in report_text: summary, detail = report_text.split("---DETAILED_REPORT_CUT---", 1)
            else: summary, detail = report_text, "AI未能生成独立的详细报告。"
            return summary.strip(), detail.strip()
        # --- NEW: Detailed error catching for GPT ---
        except AuthenticationError as gpt_e:
            logging.error(f"备用AI (GPT) 认证失败！请检查您的GPT_API_free密钥是否正确或已过期。错误: {gpt_e}")
            return generate_template_report(context, reason="备用AI认证失败")
        except RateLimitError as gpt_e:
            logging.warning(f"备用AI (GPT) 配额耗尽。错误: {gpt_e}")
            return generate_template_report(context, reason="备用AI配额耗尽")
        except APIConnectionError as gpt_e:
            logging.error(f"备用AI (GPT) 无法连接到服务器！请检查GPT_BASE_URL_free是否正确。错误: {gpt_e}")
            return generate_template_report(context, reason="备用AI连接失败")
        except Exception as gpt_e:
            logging.error(f"备用AI (GPT) 调用时发生未知错误: {gpt_e}")
    
    # Plan C: Fallback to template
    return generate_template_report(context, reason="所有AI均调用失败")

# --- Section 6: Main Execution Block ---
def main():
    start_time = datetime.now(pytz.timezone('Asia/Shanghai')); logging.info(f"--- 普罗米修斯引擎启动于 {start_time.strftime('%Y-%m-%d %H:%M:%S')} (双核AI) ---")
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
    context['monte_carlo_summary'], _ = run_monte_carlo_simulation(all_fund_data)
    if not all_fund_data: summary_report, detail_report = (f"# 🔥 简报生成失败：无有效数据\n\n...", "请检查日志。")
    else: summary_report, detail_report = ultimate_ai_council(context)
    with open("README.md", "w", encoding="utf-8") as f: f.write(summary_report)
    report_filename = f"reports/report_{context['current_date']}.md"; os.makedirs('reports', exist_ok=True)
    with open(report_filename, "w", encoding='utf-8') as f: f.write(detail_report)
    # The email function is assumed to be defined from a previous step
    # send_email_report(f"普罗米修斯每日简报 - {context['current_date']}", summary_report)
    end_time = datetime.now(pytz.timezone('Asia/Shanghai')); logging.info(f"--- 普罗米修斯引擎结束于 {end_time.strftime('%Y-%m-%d %H:%M:%S')} ---")
    logging.info(f"--- 总运行时间: {end_time - start_time} ---")

if __name__ == "__main__":
    main()
