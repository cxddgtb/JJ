# ================================================================
#                Project Prometheus - Final Production Version
#              (AKShare Core, Chinese Edition & Template Fallback)
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

# --- Section 1: Setup & Configuration ---
try:
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    print("FATAL: config.yaml not found. Exiting.")
    sys.exit(1)

LOG_DIR = 'logs'
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s',
                    handlers=[logging.FileHandler(os.path.join(LOG_DIR, 'workflow.log'), mode='w'),
                              logging.StreamHandler()])

# --- FIX: Use the font that is actually installed in the GitHub runner ---
matplotlib.use('Agg')
matplotlib.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei'] # Use WenQuanYi Zen Hei
matplotlib.rcParams['axes.unicode_minus'] = False

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logging.error("FATAL: GEMINI_API_KEY environment variable not set.")
    sys.exit(1)
genai.configure(api_key=GEMINI_API_KEY)
AI_MODEL = genai.GenerativeModel('gemini-1.5-pro-latest')

# --- Section 2: Data Acquisition Layer (AKShare) ---
@retry(stop_after_attempt=3, wait=wait_fixed(3))
def fetch_url_content(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    return response.text

def scrape_news():
    headlines = []
    for source in config['data_sources']['news_urls']:
        try:
            logging.info(f"正在从 {source['name']} 爬取新闻...")
            html = fetch_url_content(source['url'])
            soup = BeautifulSoup(html, 'html.parser')
            links = soup.find_all('a', href=True)
            for link in links:
                if len(link.text.strip()) > 20 and '...' not in link.text:
                    headlines.append(link.text.strip())
            if not headlines:
                logging.warning(f"未能从 {source['name']} 找到有效新闻标题。")
        except Exception as e:
            logging.error(f"从 {source['name']} 爬取新闻失败: {e}")
    return list(set(headlines))[:15]

@retry(stop_after_attempt=3, wait=wait_fixed(5))
def fetch_historical_data_akshare(code, days):
    logging.info(f"正在使用AKShare获取基金 {code} 的历史数据...")
    df = ak.fund_etf_hist_em(symbol=code, period="daily", adjust="qfq")
    if df.empty:
        raise ValueError(f"AKShare未能获取到代码 {code} 的数据。请检查代码是否为有效的场内ETF代码。")
    df = df.rename(columns={'日期': 'Date', '开盘': 'Open', '收盘': 'Close', '最高': 'High', '最低': 'Low', '成交量': 'Volume'})
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.set_index('Date')
    cols_to_numeric = ['Open', 'Close', 'High', 'Low', 'Volume']
    df[cols_to_numeric] = df[cols_to_numeric].apply(pd.to_numeric, errors='coerce')
    df.dropna(subset=cols_to_numeric, inplace=True)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    df = df[df.index >= start_date]
    df = df.sort_index()
    df['code'] = code
    return df

def get_economic_data():
    if not config['economic_data']['enabled']: return "宏观经济数据模块已禁用。"
    try:
        fred_key = os.getenv('FRED_API_KEY')
        if not fred_key: return "未能找到FRED API密钥环境变量。"
        fred = Fred(api_key=fred_key)
        data_points = {}
        for indicator in config['economic_data']['indicators']:
            series = fred.get_series(indicator)
            if not series.empty:
                data_points[indicator] = f"{series.iloc[-1]} (截至 {series.index[-1].strftime('%Y-%m-%d')})"
        return f"最新宏观经济指标: {json.dumps(data_points, indent=2, ensure_ascii=False)}"
    except Exception as e:
        logging.error(f"获取FRED数据失败: {e}")
        return "无法检索宏观经济数据。"

def evaluate_past_recommendations():
    return "绩效评估模块等待历史数据积累。"

def run_monte_carlo_simulation(all_fund_data):
    if not config['prometheus_module']['monte_carlo']['enabled']: return "蒙特卡洛模拟已禁用。", None
    if not all_fund_data or len(all_fund_data) < 2:
        logging.warning("历史数据不足，无法运行蒙特卡洛模拟。已跳过。")
        return "蒙特卡洛模拟已跳过：有效的基金数据不足。", None
    try:
        logging.info("开始进行蒙特卡洛模拟...")
        combined_data = pd.concat([df['Close'] for df in all_fund_data.values()], axis=1)
        combined_data.columns = list(all_fund_data.keys())
        daily_returns = combined_data.pct_change().dropna()
        if daily_returns.empty or len(daily_returns) < 2: return "蒙特卡洛模拟已跳过：基金数据无重叠部分。", None
        mean_returns = daily_returns.mean()
        cov_matrix = daily_returns.cov()
        num_simulations, num_days = config['prometheus_module']['monte_carlo']['simulations'], config['prometheus_module']['monte_carlo']['projection_days']
        results = np.zeros((num_days, num_simulations))
        initial_portfolio_value = 100
        for i in range(num_simulations):
            daily_vol = np.random.multivariate_normal(mean_returns, cov_matrix, num_days)
            portfolio_daily_returns = daily_vol.mean(axis=1)
            path = np.zeros(num_days)
            path[0] = initial_portfolio_value * (1 + portfolio_daily_returns[0])
            for t in range(1, num_days): path[t] = path[t-1] * (1 + portfolio_daily_returns[t])
            results[:, i] = path
        plt.figure(figsize=(12, 7))
        plt.plot(results, alpha=0.1)
        plt.title(f'投资组合价值预测 ({num_simulations}次模拟, 未来{num_days}天)', fontsize=16)
        plt.xlabel('从今天起的交易日', fontsize=12); plt.ylabel('标准化的投资组合价值', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.6)
        final_values = pd.Series(results[-1, :])
        percentiles = final_values.quantile([0.05, 0.50, 0.95])
        plt.axhline(y=percentiles[0.95], color='g', linestyle='--', label=f'95%乐观情况 ({percentiles[0.95]:.2f})')
        plt.axhline(y=percentiles[0.50], color='b', linestyle='-', label=f'50%中性情况 ({percentiles[0.50]:.2f})')
        plt.axhline(y=percentiles[0.05], color='r', linestyle='--', label=f'5%悲观情况 ({percentiles[0.05]:.2f})')
        plt.legend()
        chart_path = 'charts/monte_carlo_projection.png'
        plt.savefig(chart_path)
        plt.close()
        summary = (f"**蒙特卡洛模拟结果 ({num_simulations}次路径, {num_days}天):**\n"
                   f"- **乐观情况 (95分位):** 投资组合价值可能增长至 {percentiles[0.95]:.2f}。\n"
                   f"- **中性预期 (50分位):** 投资组合价值预期在 {percentiles[0.50]:.2f} 附近。\n"
                   f"- **悲观情况 (5分位):** 投资组合价值可能下跌至 {percentiles[0.05]:.2f}。")
        return summary, chart_path
    except Exception as e:
        logging.error(f"蒙特卡洛模拟发生严重错误: {e}")
        return "蒙特卡洛模拟因意外错误未能运行。", None

# --- NEW: Section 5A: Template-Based Fallback Report ---
def generate_template_report(context):
    logging.warning("AI API配额耗尽，切换到模板化数据报告方案 (B计划)。")
    
    # Build the quantitative analysis table
    quant_table = "| 基金名称 | 状态 | RSI(14) | MACD信号 |\n| :--- | :--- | :--- | :--- |\n"
    quant_data = context.get('quant_analysis_data', [])
    for item in quant_data:
        quant_table += f"| {item['name']} ({item['code']}) | {item['status']} | {item.get('rsi', 'N/A')} | {item.get('macd', 'N/A')} |\n"

    # Build the news section
    news_section = "### 市场新闻摘要\n"
    news_list = context.get('news', [])
    if news_list:
        news_section += "\n- ".join(news_list)
    else:
        news_section += "未能成功获取最新新闻。"

    # Assemble the final report
    summary_report = f"""
# ⚠️ 普罗米修斯数据简报 (AI分析失败)

**报告时间:** {context['current_time']}

**警告:** 由于Gemini AI API的免费配额已用尽，今日未能生成智能分析报告。以下为已成功获取的原始数据摘要，仅供参考。

---

### 量化指标一览

{quant_table}

---

{news_section}

---
*提示：要恢复完整的AI智能分析，请为您的Google Cloud项目启用结算功能，升级API配额。*
"""
    detail_report = "由于AI API配额耗尽，未生成深度分析报告。"
    return summary_report.strip(), detail_report

# --- Section 5B: Ultimate AI Council (The A Plan) ---
def ultimate_ai_council(context):
    # ... (The prompt remains the same)
    logging.info("正在召开终极AI委员会 (A计划)...")
    prompt = f"""... (The full Chinese prompt as in the previous version) ..."""
    try:
        logging.info("正在使用 Gemini 1.5 Pro 生成中文报告...")
        response = AI_MODEL.generate_content(prompt)
        # ... (response parsing remains the same)
    except google.api_core.exceptions.ResourceExhausted as e:
        logging.error(f"AI报告生成失败，API配额耗尽: {e}")
        # --- THIS IS THE KEY CHANGE: Call the fallback function ---
        return generate_template_report(context)
    except Exception as e:
        logging.error(f"AI报告生成时发生未知错误: {e}")
        summary, detail = generate_template_report(context) # Also fallback on other errors
        summary = f"# 🔥 AI分析遭遇未知错误\n\n{summary}" # Add an extra error header
        return summary, detail

# --- Section 6: Main Execution Block ---
def main():
    start_time = datetime.now(pytz.timezone('Asia/Shanghai'))
    logging.info(f"--- 普罗米修斯引擎启动于 {start_time.strftime('%Y-%m-%d %H:%M:%S')} (AKShare核心) ---")
    
    context = {'current_time': start_time.strftime('%Y-%m-%d %H:%M:%S %Z'), 'current_date': start_time.strftime('%Y-%m-%d')}
    context['performance_review'] = evaluate_past_recommendations()

    with ThreadPoolExecutor(max_workers=10) as executor:
        news_future = executor.submit(scrape_news)
        eco_future = executor.submit(get_economic_data)
        fund_codes = [f['code'] for f in config['index_funds']]
        hist_data_futures = {code: executor.submit(fetch_historical_data_akshare, code, 365) for code in fund_codes}

        context['news'] = news_future.result()
        context['economic_data'] = eco_future.result()
        
        all_fund_data = {}
        quant_reports_text = [] # For AI prompt
        quant_data_structured = [] # For template fallback

        for code in fund_codes:
            future = hist_data_futures[code]
            fund_name = next((f['name'] for f in config['index_funds'] if f['code'] == code), code)
            item = {'name': fund_name, 'code': code}
            try:
                data = future.result()
                all_fund_data[code] = data
                data.ta.rsi(append=True)
                data.ta.macd(append=True)
                latest = data.iloc[-1]
                macd_signal = '金叉' if latest['MACD_12_26_9'] > latest['MACDs_12_26_9'] else '死叉'
                
                item.update({'status': '数据正常', 'rsi': f"{latest['RSI_14']:.2f}", 'macd': macd_signal})
                quant_reports_text.append(f"  - **{fund_name} ({code})**: {item['status']}。RSI={item['rsi']}, MACD信号={item['macd']}")
            except Exception as e:
                logging.error(f"处理基金 {fund_name} ({code}) 的数据失败: {e}")
                item.update({'status': '数据获取失败'})
                quant_reports_text.append(f"  - **{fund_name} ({code})**: {item['status']}。请检查基金代码是否正确。")
            quant_data_structured.append(item)
        
        context['quant_analysis'] = "最新技术指标分析:\n" + "\n".join(quant_reports_text)
        context['quant_analysis_data'] = quant_data_structured # Store structured data for template

    try:
        with open(config['user_profile']['portfolio_path'], 'r', encoding='utf-8') as f:
            context['portfolio'] = json.load(f)
    except Exception as e:
        logging.error(f"无法加载持仓文件: {e}")
        context['portfolio'] = [{"错误": "无法加载持仓文件。"}]

    context['monte_carlo_summary'], _ = run_monte_carlo_simulation(all_fund_data)
    
    if not all_fund_data:
        logging.warning("跳过AI委员会：未能获取到任何有效的基金数据。")
        summary_report, detail_report = (f"# 🔥 简报生成失败：无有效数据\n\n所有目标基金的数据获取均失败。请检查基金代码是否为有效的场内ETF。系统将在下个计划时间自动重试。", 
                                         "所有数据获取任务均失败。请检查日志中关于AKShare的详细错误信息。")
    else:
        summary_report, detail_report = ultimate_ai_council(context)

    with open("README.md", "w", encoding="utf-8") as f: f.write(summary_report)
    report_filename = f"reports/report_{context['current_date']}.md"
    os.makedirs('reports', exist_ok=True)
    with open(report_filename, "w", encoding="utf-8") as f: f.write(detail_report)

    end_time = datetime.now(pytz.timezone('Asia/Shanghai'))
    logging.info(f"--- 普罗米修斯引擎结束于 {end_time.strftime('%Y-%m-%d %H:%M:%S')} ---")
    logging.info(f"--- 总运行时间: {end_time - start_time} ---")

if __name__ == "__main__":
    main()
