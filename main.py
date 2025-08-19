# ================================================================
#                Project Prometheus - Final Prophet Version
#              (Future Prediction Chart & All Previous Features)
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
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, stop_after_attempt, wait_fixed
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import google.api_core.exceptions
import markdown
import ffn # <--- 导入新库
import bt  # <--- 导入新库

# --- Section 1: Setup & Configuration ---
try:
    with open('config.yaml', 'r', encoding='utf-8') as f: config = yaml.safe_load(f)
except FileNotFoundError: print("FATAL: config.yaml not found. Exiting."); sys.exit(1)
LOG_DIR = 'logs'; CHART_DIR = 'charts'
os.makedirs(LOG_DIR, exist_ok=True); os.makedirs(CHART_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s',
                    handlers=[logging.FileHandler(os.path.join(LOG_DIR, 'workflow.log'), mode='w'), logging.StreamHandler()])
matplotlib.use('Agg'); matplotlib.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei']; matplotlib.rcParams['axes.unicode_minus'] = False
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY: logging.error("FATAL: GEMINI_API_KEY environment variable not set."); sys.exit(1)
genai.configure(api_key=GEMINI_API_KEY); AI_MODEL = genai.GenerativeModel('gemini-1.5-pro-latest')

# --- Section 2: Data Acquisition & Future Prediction Module ---
# ... (scrape_news, fetch_historical_data_akshare, get_economic_data remain the same) ...
@retry(stop=stop_after_attempt(3), wait=wait_fixed(3))
def fetch_url_content_raw(url):
    headers = {'User-Agent': 'Mozilla/5.0 ...'}; response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status(); return response.content
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

# --- NEW: Function to generate future prediction chart for a SINGLE fund ---
def generate_future_trend_chart(fund_code, data):
    """
    Generates a mini prediction chart for the next 30 days based on historical volatility.
    """
    try:
        # 1. Calculate historical daily returns and volatility
        returns = data['Close'].pct_change().dropna()
        if len(returns) < 30: # Need at least some data
            return None
        
        # 2. Setup simulation parameters
        last_price = data['Close'].iloc[-1]
        num_simulations = 100
        num_days = 30
        
        # 3. Run Monte Carlo simulation
        simulation_df = pd.DataFrame()
        for x in range(num_simulations):
            daily_vol = returns.std()
            price_series = [last_price]
            
            # Generate random returns for 30 days
            price = last_price * (1 + np.random.normal(0, daily_vol))
            price_series.append(price)
            for _ in range(num_days -1):
                price = price_series[-1] * (1 + np.random.normal(0, daily_vol))
                price_series.append(price)
            
            simulation_df[x] = price_series
        
        # 4. Create the mini chart
        plt.figure(figsize=(3, 1)) # Small size for embedding in table
        # Plot all simulations with high transparency
        for i in range(num_simulations):
            plt.plot(simulation_df.iloc[:, i], color='grey', alpha=0.1)
        
        # Plot the median path (50th percentile) more prominently
        median_path = simulation_df.quantile(0.5, axis=1)
        plt.plot(median_path, color='blue', linewidth=2)
        
        # Clean up the chart for a "K-line" feel
        plt.axis('off')
        plt.margins(0)
        plt.tick_params(axis='both', left=False, top=False, right=False, bottom=False, labelleft=False, labeltop=False, labelright=False, labelbottom=False)
        
        chart_path = os.path.join(CHART_DIR, f"{fund_code}_future_trend.png")
        plt.savefig(chart_path, bbox_inches='tight', pad_inches=0, dpi=50)
        plt.close()
        
        return chart_path
    except Exception as e:
        logging.error(f"为基金 {fund_code} 生成未来趋势图失败: {e}")
        return None

# --- Section 5A: Template-Based Fallback Report (Upgraded with Future Chart) ---
def generate_template_report(context):
    logging.warning("AI API配额耗尽，切换到B计划：模板化数据报告。")
    
    # --- NEW: Upgraded table with future prediction chart ---
    quant_table = "| 基金名称 | 状态 | RSI(14) | MACD信号 | 未来30日趋势预测 |\n| :--- | :--- | :--- | :--- | :--- |\n"
    for item in context.get('quant_analysis_data', []):
        chart_md = 'N/A'
        if 'future_chart_path' in item and item['future_chart_path']:
             # Use a relative path for Markdown
            chart_md = f"![趋势图]({item['future_chart_path']})"
        quant_table += f"| {item['name']} ({item['code']}) | {item['status']} | {item.get('rsi', 'N/A')} | {item.get('macd', 'N/A')} | {chart_md} |\n"
    
    news_section = "### 市场新闻摘要\n"
    news_list = context.get('news', []); news_section += "\n- " + "\n- ".join(news_list) if news_list else "未能成功获取最新新闻。"
    summary_report = f"# ⚠️ 普罗米修斯数据简报 (AI分析失败)\n**报告时间:** {context['current_time']}\n**警告:** 因Gemini API配额耗尽，今日未生成智能分析。以下为原始数据摘要。\n---\n### 量化指标与趋势预测\n{quant_table}\n---\n{news_section}\n---\n*提示：要恢复AI智能分析，请为您的Google Cloud项目启用结算。*"
    return summary_report.strip(), "因AI API配额耗尽，未生成深度分析报告。"

# --- Section 5B: Ultimate AI Council ---
def ultimate_ai_council(context):
    logging.info("正在召开A计划：终极AI委员会...")
    # The AI doesn't need to see the chart, just the raw data. The prompt remains the same.
    quant_analysis_for_ai = "最新技术指标分析:\n"
    for item in context.get('quant_analysis_data', []):
        quant_analysis_for_ai += f"  - **{item['name']} ({item['code']})**: {item['status']}。RSI={item.get('rsi', 'N/A')}, MACD信号={item.get('macd', 'N/A')}\n"
    
    prompt = f"""
    您是“普罗米修斯”AI，... (rest of the prompt is the same as the last version) ...
    **3. 量化分析 (数据、指标):**
    {quant_analysis_for_ai}
    ...
    ### 投资组合仪表盘
    | 基金名称 | 类型 | **操作建议** | **信心指数** | 核心理由 |
    | :--- | :--- | :--- | :--- | :--- |
    ...
    """
    try:
        logging.info("正在使用 Gemini 1.5 Pro 生成中文报告...")
        response = AI_MODEL.generate_content(prompt)
        report_text = response.text
        if "---DETAILED_REPORT_CUT---" in report_text: summary, detail = report_text.split("---DETAILED_REPORT_CUT---", 1)
        else: summary, detail = report_text, "AI未能生成独立的详细报告。"
        return summary.strip(), detail.strip()
    except google.api_core.exceptions.ResourceExhausted as e:
        logging.error(f"AI报告失败，API配额耗尽: {e}"); return generate_template_report(context)
    except Exception as e:
        logging.error(f"AI报告未知错误: {e}"); summary, detail = generate_template_report(context)
        return f"# 🔥 AI分析遭遇未知错误\n\n{summary}", detail

# --- Section 6: Main Execution Block (Upgraded with Future Chart) ---
def main():
    start_time = datetime.now(pytz.timezone('Asia/Shanghai')); logging.info(f"--- 普罗米修斯引擎启动于 {start_time.strftime('%Y-%m-%d %H:%M:%S')} (AKShare核心) ---")
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
                data = future.result(); all_fund_data[code] = data
                data.ta.rsi(append=True); data.ta.macd(append=True)
                latest = data.iloc[-1]
                macd_signal = '金叉' if latest['MACD_12_26_9'] > latest['MACDs_12_26_9'] else '死叉'
                
                # --- NEW: Generate future trend chart for each fund ---
                future_chart_path = generate_future_trend_chart(code, data)
                
                item.update({'status': '数据正常', 'rsi': f"{latest['RSI_14']:.2f}", 'macd': macd_signal, 'future_chart_path': future_chart_path})
            except Exception as e:
                logging.error(f"处理基金 {fund_name} ({code}) 的数据失败: {e}"); item.update({'status': '数据获取失败'})
            quant_data_structured.append(item)
        context['quant_analysis_data'] = quant_data_structured
    
    try:
        with open(config['user_profile']['portfolio_path'], 'r', encoding='utf-8') as f: context['portfolio'] = json.load(f)
    except Exception as e: logging.error(f"无法加载持仓文件: {e}"); context['portfolio'] = [{"错误": "无法加载持仓文件。"}]

    if not all_fund_data: summary_report, detail_report = (f"# 🔥 简报生成失败：无有效数据\n\n所有目标基金的数据获取均失败。", "请检查日志。")
    else: summary_report, detail_report = ultimate_ai_council(context)
    
    with open("README.md", "w", encoding="utf-8") as f: f.write(summary_report)
    report_filename = f"reports/report_{context['current_date']}.md"; os.makedirs('reports', exist_ok=True)
    with open(report_filename, "w", encoding='utf-8') as f: f.write(detail_report)
    
    end_time = datetime.now(pytz.timezone('Asia/Shanghai')); logging.info(f"--- 普罗米修斯引擎结束于 {end_time.strftime('%Y-%m-%d %H:%M:%S')} ---")
    logging.info(f"--- 总运行时间: {end_time - start_time} ---")

if __name__ == "__main__":
    main()
