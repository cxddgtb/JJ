# ================================================================
#                Project Prometheus - Final Prophet Version
#              (AI-Driven Prediction Chart & All Features)
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
import re

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

# --- Section 2: Data Acquisition & AI-Powered Charting ---
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
    return list(set(headlines))[:20] # 增加新闻数量以提供更丰富的上下文
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

# --- NEW: AI-Driven Future Prediction Chart Generator ---
def generate_ai_prediction_chart(fund_code, last_price, predictions):
    """
    Generates a K-line-like prediction chart based on AI's price targets.
    """
    try:
        bullish_target = predictions.get('bullish', last_price * 1.1)
        bearish_target = predictions.get('bearish', last_price * 0.9)
        likely_target = predictions.get('likely', last_price)
        
        plt.figure(figsize=(3, 1))
        
        # Create x-axis for 30 days
        days = np.arange(0, 31)
        
        # Create the "cone of probability"
        # Upper bound: from last_price to bullish_target
        upper_bound = np.linspace(last_price, bullish_target, 31)
        # Lower bound: from last_price to bearish_target
        lower_bound = np.linspace(last_price, bearish_target, 31)
        # Most likely path
        likely_path = np.linspace(last_price, likely_target, 31)
        
        # Fill the area between bullish and bearish to create the cone
        plt.fill_between(days, lower_bound, upper_bound, color='grey', alpha=0.2, label='概率通道')
        
        # Plot the most likely path
        plt.plot(days, likely_path, color='blue', linewidth=2, label='最可能路径')
        
        # Clean up the chart
        plt.axis('off'); plt.margins(0)
        plt.tick_params(axis='both', length=0)
        
        chart_path = os.path.join(CHART_DIR, f"{fund_code}_ai_prediction.png")
        plt.savefig(chart_path, bbox_inches='tight', pad_inches=0, dpi=50)
        plt.close()
        
        return chart_path
    except Exception as e:
        logging.error(f"为基金 {fund_code} 生成AI预测图失败: {e}")
        return None

# --- Section 5: AI Council & Fallback Report ---
def generate_template_report(context):
    logging.warning("AI API配额耗尽，切换到B计划：模板化数据报告。")
    quant_table = "| 基金名称 | 状态 | RSI(14) | MACD信号 |\n| :--- | :--- | :--- | :--- |\n"
    for item in context.get('quant_analysis_data', []):
        quant_table += f"| {item['name']} ({item['code']}) | {item['status']} | {item.get('rsi', 'N/A')} | {item.get('macd', 'N/A')} |\n"
    news_section = "### 市场新闻摘要\n"
    news_list = context.get('news', []); news_section += "\n- " + "\n- ".join(news_list) if news_list else "未能成功获取最新新闻。"
    summary_report = f"# ⚠️ 普罗米修斯数据简报 (AI分析失败)\n**报告时间:** {context['current_time']}\n**警告:** 因Gemini API配额耗尽，今日未生成智能分析。以下为原始数据摘要。\n---\n### 量化指标一览\n{quant_table}\n---\n{news_section}\n---\n*提示：要恢复AI智能分析，请为您的Google Cloud项目启用结算。*"
    return summary_report.strip(), "因AI API配额耗尽，未生成深度分析报告。"

def ultimate_ai_council(context):
    logging.info("正在召开A计划：终极AI委员会...")
    
    quant_analysis_for_ai = "最新技术指标分析:\n"
    for item in context.get('quant_analysis_data', []):
        quant_analysis_for_ai += f"  - **{item['name']} ({item['code']})**: {item['status']}。最新收盘价={item.get('last_price', 'N/A')}, RSI={item.get('rsi', 'N/A')}, MACD信号={item.get('macd', 'N/A')}\n"
    
    prompt = f"""
    您是“普罗米修斯”AI，一个由顶级金融专家组成的AI委员会。您的使命是根据提供的所有数据，为用户生成一份机构级的、完整的中文投资报告，并对未来进行量化预测。

    **核心目标:** 
    1. 提供清晰、可执行、理由充分的午后交易策略。
    2. 基于所有信息，对每只基金未来30天的价格走势进行预测。

    **用户画像:**
    - 风险偏好: {config['user_profile']['risk_profile']}
    - 投资哲学: "{config['user_profile']['investment_philosophy']}"

    **--- 输入数据 ---**
    1. **市场新闻与情绪:** {context['news'] if context.get('news') else '未能获取到市场新闻。'}
    2. **宏观经济数据:** {context.get('economic_data', '暂无')}
    3. **量化分析:** {quant_analysis_for_ai}

    **--- 输出格式要求 ---**
    您必须严格按照以下格式生成两部分内容，并用 "---DETAILED_REPORT_CUT---" 这行文字精确地分隔开。

    **第一部分: 执行摘要 (README.md)**
    # 🔥 普罗米修斯每日投资简报
    **报告时间:** {context['current_time']}
    **今日核心观点:** (用一句话概括市场核心判断)
    ---
    ### 投资组合仪表盘与未来30日预测
    | 基金名称 | 类型 | **操作建议** | **信心指数** | 核心理由 | 未来30日趋势预测 |
    | :--- | :--- | :--- | :--- | :--- | :--- |
    (为基金池中**每一只基金**填充此表格。**核心理由**要简短精炼。**未来30日趋势预测**列暂时留空，由程序后续填充。)
    ---
    *免责声明: 本报告由AI自动生成，仅供参考，不构成投资建议。*

    ---DETAILED_REPORT_CUT---

    **第二部分: 深度分析与量化预测 (JSON格式)**
    这是AI委员会的详细分析和预测数据。**此部分必须是严格的JSON格式。**

    {{
        "detailed_analysis": [
            {{
                "code": "基金代码",
                "name": "基金名称",
                "analysis": "这里是详细的多段分析，涵盖宏观、量化、情绪视角和最终决策逻辑。"
            }}
            // ... 为每一只基金重复此结构
        ],
        "predictions": [
            {{
                "code": "基金代码",
                "bullish": 乐观价格目标,
                "bearish": 悲观价格目标,
                "likely": 最可能价格目标
            }}
            // ... 为每一只基金重复此结构
        ]
    }}
    """
    try:
        logging.info("正在使用 Gemini 1.5 Pro 生成中文报告和预测...")
        response = AI_MODEL.generate_content(prompt)
        report_text = response.text
        
        if "---DETAILED_REPORT_CUT---" in report_text:
            summary_md, detail_json_str = report_text.split("---DETAILED_REPORT_CUT---", 1)
            return summary_md.strip(), json.loads(detail_json_str.strip())
        else: # 如果AI未能按要求分割，则整个作为摘要，并返回空预测
            return report_text.strip(), {}
    except (google.api_core.exceptions.ResourceExhausted, Exception) as e:
        logging.error(f"AI报告生成失败: {e}")
        is_quota_error = isinstance(e, google.api_core.exceptions.ResourceExhausted)
        summary, detail = generate_template_report(context)
        if not is_quota_error:
             summary = f"# 🔥 AI分析遭遇未知错误\n\n{summary}"
        return summary, {} # 返回空字典表示没有预测数据

# --- Section 6: Main Execution Block (Final Version) ---
def main():
    start_time = datetime.now(pytz.timezone('Asia/Shanghai')); logging.info(f"--- 普罗米修斯引擎启动于 {start_time.strftime('%Y-%m-%d %H:%M:%S')} ---")
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
                item.update({'status': '数据正常', 'rsi': f"{latest['RSI_14']:.2f}", 'macd': macd_signal, 'last_price': latest['Close']})
            except Exception as e:
                logging.error(f"处理基金 {fund_name} ({code}) 的数据失败: {e}"); item.update({'status': '数据获取失败'})
            quant_data_structured.append(item)
        context['quant_analysis_data'] = quant_data_structured
    
    try:
        with open(config['user_profile']['portfolio_path'], 'r', encoding='utf-8') as f: context['portfolio'] = json.load(f)
    except Exception as e: logging.error(f"无法加载持仓文件: {e}"); context['portfolio'] = [{"错误": "无法加载持仓文件。"}]
    
    if not all_fund_data:
        summary_report, detail_data = (f"# 🔥 简报生成失败：无有效数据\n\n...", {})
    else:
        summary_report, detail_data = ultimate_ai_council(context)
    
    # --- NEW: Post-processing step to add charts to the summary report ---
    final_summary_report = summary_report
    if detail_data and 'predictions' in detail_data:
        predictions = {p['code']: p for p in detail_data['predictions']}
        updated_rows = []
        for row in summary_report.split('\n'):
            # Find table rows, which start with '|'
            if row.strip().startswith('|') and not row.strip().startswith('| :---'):
                # Extract fund code from the row, e.g., | 沪深300基石 (510300) | ...
                match = re.search(r'\((\d{6})\)', row)
                if match:
                    code = match.group(1)
                    if code in predictions and code in all_fund_data:
                        last_price = all_fund_data[code]['Close'].iloc[-1]
                        chart_path = generate_ai_prediction_chart(code, last_price, predictions[code])
                        if chart_path:
                            # Replace the last empty cell with the chart markdown
                            row = row.rsplit('|', 1)[0] + f"| ![趋势图]({chart_path}) |"
            updated_rows.append(row)
        final_summary_report = "\n".join(updated_rows)

    with open("README.md", "w", encoding="utf-8") as f: f.write(final_summary_report)
    
    # Create the detailed report from the JSON data
    detail_report_md = f"# 普罗米修斯深度分析报告 - {context['current_date']}\n\n"
    if detail_data and 'detailed_analysis' in detail_data:
        for analysis_item in detail_data['detailed_analysis']:
            detail_report_md += f"## {analysis_item['name']} ({analysis_item['code']})\n\n{analysis_item['analysis']}\n\n---\n\n"
    else:
        detail_report_md += "未能生成深度分析内容。"

    report_filename = f"reports/report_{context['current_date']}.md"; os.makedirs('reports', exist_ok=True)
    with open(report_filename, "w", encoding='utf-8') as f: f.write(detail_report_md)
    
    end_time = datetime.now(pytz.timezone('Asia/Shanghai')); logging.info(f"--- 普罗米修斯引擎结束于 {end_time.strftime('%Y-%m-%d %H:%M:%S')} ---")
    logging.info(f"--- 总运行时间: {end_time - start_time} ---")

if __name__ == "__main__":
    main()
