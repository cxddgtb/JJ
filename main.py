# ================================================================
#                Project Prometheus - Main Engine (Hardened & Chinese Edition)
# ================================================================
import os
import sys
import json
import yaml
import logging
from datetime import datetime, timedelta
import pytz
import pandas as pd
import yfinance as yf
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

# Logging Configuration
LOG_DIR = 'logs'
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'workflow.log'), mode='w'),
        logging.StreamHandler()
    ]
)

# Matplotlib setup for non-GUI environment and Chinese characters
matplotlib.use('Agg')
matplotlib.rcParams['font.sans-serif'] = ['SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False

# API Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logging.error("FATAL: GEMINI_API_KEY environment variable not set.")
    sys.exit(1)
genai.configure(api_key=GEMINI_API_KEY)
AI_MODEL = genai.GenerativeModel('gemini-1.5-pro-latest')

# --- Section 2: Data Acquisition Layer ---
@retry(stop=stop_after_attempt(3), wait=wait_fixed(3))
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

@retry(stop=stop_after_attempt(2), wait=wait_fixed(5))
def fetch_historical_data(code, days):
    market_suffix = ".SS" if code.startswith(('5', '6')) else ".SZ"
    ticker = f"{code}{market_suffix}"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    data = yf.download(ticker, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False, auto_adjust=True)
    if data.empty:
        raise ValueError(f"未能找到代码 {ticker} 的数据。它可能已退市、代码无效或遭遇临时API问题。")
    data['code'] = code
    return data

def get_economic_data():
    if not config['economic_data']['enabled']:
        return "宏观经济数据模块已禁用。"
    try:
        fred_key = os.getenv(config['economic_data']['fred_api_key_env'])
        if not fred_key:
            return "未能找到FRED API密钥环境变量。"
        fred = Fred(api_key=fred_key)
        data_points = {}
        for indicator in config['economic_data']['indicators']:
            series = fred.get_series(indicator)
            if not series.empty:
                latest_value = series.iloc[-1]
                latest_date = series.index[-1].strftime('%Y-%m-%d')
                data_points[indicator] = f"{latest_value} (截至 {latest_date})"
        return f"最新宏观经济指标: {json.dumps(data_points, indent=2, ensure_ascii=False)}"
    except Exception as e:
        logging.error(f"获取FRED数据失败: {e}")
        return "无法检索宏观经济数据。"

# --- Section 3: Performance Review (Placeholder) ---
def evaluate_past_recommendations():
    # This function is a placeholder for future self-learning implementation.
    return "绩效评估模块等待历史数据积累。"

# --- Section 4: Monte Carlo Future Prediction ---
def run_monte_carlo_simulation(all_fund_data):
    if not config['prometheus_module']['monte_carlo']['enabled']:
        return "蒙特卡洛模拟已禁用。", None
    
    if not all_fund_data or len(all_fund_data) < 2:
        logging.warning("历史数据不足，无法运行蒙特卡洛模拟。已跳过。")
        return "蒙特卡洛模拟已跳过：有效的基金数据不足。", None

    try:
        logging.info("开始进行蒙特卡洛模拟...")
        combined_data = pd.concat([df['Close'] for df in all_fund_data.values()], axis=1)
        combined_data.columns = list(all_fund_data.keys())
        
        daily_returns = combined_data.pct_change().dropna()
        if daily_returns.empty or len(daily_returns) < 2:
            logging.warning("基金数据无重叠，无法计算协方差矩阵。已跳过模拟。")
            return "蒙特卡洛模拟已跳过：基金数据无重叠部分。", None

        mean_returns = daily_returns.mean()
        cov_matrix = daily_returns.cov()
        
        num_simulations = config['prometheus_module']['monte_carlo']['simulations']
        num_days = config['prometheus_module']['monte_carlo']['projection_days']
        
        results = np.zeros((num_days, num_simulations))
        initial_portfolio_value = 100

        for i in range(num_simulations):
            daily_vol = np.random.multivariate_normal(mean_returns, cov_matrix, num_days)
            portfolio_daily_returns = daily_vol.mean(axis=1)
            path = np.zeros(num_days)
            path[0] = initial_portfolio_value * (1 + portfolio_daily_returns[0])
            for t in range(1, num_days):
                path[t] = path[t-1] * (1 + portfolio_daily_returns[t])
            results[:, i] = path

        plt.figure(figsize=(12, 7))
        plt.plot(results, alpha=0.1)
        plt.title(f'投资组合价值预测 ({num_simulations}次模拟, 未来{num_days}天)', fontsize=16)
        plt.xlabel('从今天起的交易日', fontsize=12)
        plt.ylabel('标准化的投资组合价值', fontsize=12)
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

# --- Section 5: Ultimate AI Council (Chinese Prompt) ---
def ultimate_ai_council(context):
    logging.info("正在召开终极AI委员会...")

    prompt = f"""
    您是“普罗米修斯”AI，一个由顶级金融专家组成的AI委员会。您的使命是根据提供的所有数据，为用户生成一份机构级的、完整的中文投资报告。

    **核心目标:** 为用户提供一份清晰、可执行、理由充分的午后交易投资策略。

    **用户画像:**
    - 风险偏好: {config['user_profile']['risk_profile']}
    - 投资哲学: "{config['user_profile']['investment_philosophy']}"

    **当前持仓:**
    {json.dumps(context['portfolio'], indent=2, ensure_ascii=False)}

    **--- 输入数据 ---**

    **1. 自我学习绩效评估 (我过去的建议表现如何？):**
    {context.get('performance_review', '暂无')}

    **2. 市场新闻与情绪 (市场情绪如何？):**
    {context['news'] if context.get('news') else '未能获取到市场新闻。'}

    **3. 宏观经济数据 (宏观大局是怎样的？):**
    {context.get('economic_data', '暂无')}
    
    **4. 量化分析 (数据和指标说明了什么？):**
    {context.get('quant_analysis', '未能获取到任何基金的量化数据。')}

    **5. 未来风险评估 (概率模型预测了什么？):**
    {context.get('monte_carlo_summary', '暂无')}

    **--- 输出格式要求 ---**

    您必须严格按照以下格式生成两部分内容，并用 "---DETAILED_REPORT_CUT---" 这行文字精确地分隔开。

    **第一部分: 执行摘要 (用于README.md)**
    这部分内容必须简洁、直观。

    # 🔥 普罗米修斯每日投资简报

    **报告时间:** {context['current_time']}

    **今日核心观点:** (用一句话高度概括您对今日市场的核心判断)

    ---

    ### 投资组合仪表盘

    | 基金名称 | 类型 | **操作建议** | **信心指数** | 核心理由 |
    | :--- | :--- | :--- | :--- | :--- |
    (请为用户的基金池中的**每一只基金**填充此表格，提供明确的'持有', '买入', '减仓', '卖出', '观望'等建议，并给出'高', '中', '低'的信心指数)

    ---

    ### 未来90天财富预测 (蒙特卡洛模拟)

    ![投资组合预测图](charts/monte_carlo_projection.png)

    **首席风险官(CRO)的最终裁决:** (解读蒙特卡洛模拟结果。给出一个明确的风险等级：低、中、高、或极高，并解释原因。)

    ---

    *免责声明: 本AI报告由公开数据自动生成，仅供参考，不构成任何投资建议。所有金融决策均包含风险。*

    ---DETAILED_REPORT_CUT---

    **第二部分: 深度分析报告 (用于 reports/report_YYYY-MM-DD.md)**
    这是AI委员会详细的“会议纪要”。

    # 普罗米修斯深度分析报告 - {context['current_date']}

    ## 1. 首席投资官(CIO)开篇陈词
    (提供一个全面的市场宏观概述，解释“今日核心观点”是如何形成的。)

    ## 2. 自我学习与策略调整
    (讨论绩效评估报告。明确说明过去的成功或失败如何影响今天的建议。例如：“鉴于我们近期对科技板块的预测表现不佳，尽管指标看涨，我们今天仍采取更为谨慎的‘持有’立场。”)

    ## 3. 逐只基金深度剖析
    (为每一只基金提供数段分析，涵盖:)
    - **宏观视角:** 当前经济环境对此板块有何影响？
    - **量化视角:** 技术指标（RSI, MACD等）揭示了什么信号？
    - **情绪视角:** 近期新闻面对此板块是利好还是利空？
    - **最终决策逻辑:** 综合以上所有信息，详细解释仪表盘中最终建议的完整思考过程。

    ## 4. 风险评估与应急预案
    (详细阐述CRO的裁决。投资组合面临的主要风险是什么？哪些突发事件可能让今天的判断失效？)
    """

    try:
        logging.info("正在使用 Gemini 1.5 Pro 生成中文报告...")
        response = AI_MODEL.generate_content(prompt)
        report_text = response.text
        if "---DETAILED_REPORT_CUT---" in report_text:
            summary, detail = report_text.split("---DETAILED_REPORT_CUT---", 1)
        else:
            summary = report_text
            detail = "AI未能生成独立的详细报告部分。"
        return summary.strip(), detail.strip()
    except google.api_core.exceptions.ResourceExhausted as e:
        logging.error(f"AI报告生成失败，API配额耗尽: {e}")
        error_summary = ("# 🔥 普罗米修斯简报生成失败：API配额超限\n\n"
                         "对Gemini AI的请求已被拒绝，因为免费套餐的API配额已用完。"
                         "要解决此问题，请为您的Google Cloud项目启用结算功能。工作流将在明天重试。")
        return error_summary, str(e)
    except Exception as e:
        logging.error(f"AI报告生成时发生未知错误: {e}")
        error_summary = "# 🔥 普罗米修斯简报生成失败\n\n生成AI报告时发生未知错误，请检查日志。"
        return error_summary, str(e)


# --- Section 6: Main Execution Block ---
def main():
    start_time = datetime.now(pytz.timezone('Asia/Shanghai'))
    logging.info(f"--- 普罗米修斯引擎启动于 {start_time.strftime('%Y-%m-%d %H:%M:%S')} ---")
    
    context = {
        'current_time': start_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
        'current_date': start_time.strftime('%Y-%m-%d')
    }
    
    context['performance_review'] = evaluate_past_recommendations()

    # Data Acquisition (Parallel)
    with ThreadPoolExecutor(max_workers=10) as executor:
        news_future = executor.submit(scrape_news)
        eco_future = executor.submit(get_economic_data)
        
        fund_codes = [f['code'] for f in config['index_funds']]
        hist_data_futures = {code: executor.submit(fetch_historical_data, code, 365) for code in fund_codes}

        context['news'] = "\n- ".join(news_future.result())
        context['economic_data'] = eco_future.result()
        
        all_fund_data = {}
        quant_reports = []
        for code in fund_codes:
            future = hist_data_futures[code]
            fund_name = next((f['name'] for f in config['index_funds'] if f['code'] == code), code)
            try:
                data = future.result()
                all_fund_data[code] = data
                data.ta.rsi(append=True)
                data.ta.macd(append=True)
                latest = data.iloc[-1]
                macd_signal = '金叉' if latest['MACD_12_26_9'] > latest['MACDs_12_26_9'] else '死叉'
                quant_reports.append(f"  - **{fund_name} ({code})**: 数据正常。RSI={latest['RSI_14']:.2f}, MACD信号={macd_signal}")
            except Exception as e:
                logging.error(f"处理基金 {fund_name} ({code}) 的数据失败: {e}")
                quant_reports.append(f"  - **{fund_name} ({code})**: 数据获取失败。无法检索或处理历史数据。")
        
        context['quant_analysis'] = "最新技术指标分析:\n" + "\n".join(quant_reports)

    try:
        with open(config['user_profile']['portfolio_path'], 'r', encoding='utf-8') as f:
            context['portfolio'] = json.load(f)
    except Exception as e:
        logging.error(f"无法加载持仓文件: {e}")
        context['portfolio'] = [{"错误": "无法加载持仓文件。"}]

    context['monte_carlo_summary'], _ = run_monte_carlo_simulation(all_fund_data)
    
    if not all_fund_data:
        logging.warning("跳过AI委员会：未能获取到任何有效的基金数据。")
        summary_report = (f"# 🔥 普罗米修斯简报生成失败：无有效数据\n\n"
                          f"所有目标基金的数据获取均失败。最常见的原因是`yfinance`数据源不稳定。"
                          f"系统将在下个计划时间自动重试。本次未执行AI分析。")
        detail_report = "所有数据获取任务均失败。请检查日志中关于yfinance和新闻爬取的详细错误信息。"
    else:
        summary_report, detail_report = ultimate_ai_council(context)

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(summary_report)
    
    report_filename = f"reports/report_{context['current_date']}.md"
    os.makedirs('reports', exist_ok=True)
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(detail_report)

    end_time = datetime.now(pytz.timezone('Asia/Shanghai'))
    logging.info(f"--- 普罗米修斯引擎结束于 {end_time.strftime('%Y-%m-%d %H:%M:%S')} ---")
    logging.info(f"--- 总运行时间: {end_time - start_time} ---")


if __name__ == "__main__":
    main()
