# ================================================================
#                Project Prometheus - Main Engine
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

# Matplotlib setup for non-GUI environment
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
            logging.info(f"Scraping news from {source['name']}...")
            html = fetch_url_content(source['url'])
            soup = BeautifulSoup(html, 'html.parser')
            # Add specific scraping logic for each site if needed
            # Generic approach: find all links with meaningful text
            links = soup.find_all('a', href=True)
            for link in links[:10]:
                 if len(link.text.strip()) > 15: # Filter out short/irrelevant links
                    headlines.append(link.text.strip())
        except Exception as e:
            logging.error(f"Failed to scrape news from {source['name']}: {e}")
    return list(set(headlines))[:15] # Return unique headlines

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def fetch_historical_data(code, days):
    market_suffix = ".SS" if code.startswith(('5', '6')) else ".SZ"
    ticker = f"{code}{market_suffix}"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    data = yf.download(ticker, start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)
    if data.empty:
        raise ValueError(f"No data found for ticker {ticker}, it may be delisted or invalid.")
    data['code'] = code
    return data

def get_economic_data():
    if not config['economic_data']['enabled']:
        return "Macroeconomic data module disabled."
    try:
        fred_key = os.getenv(config['economic_data']['fred_api_key_env'])
        if not fred_key:
            return "FRED API Key not set in environment."
        fred = Fred(api_key=fred_key)
        data_points = {}
        for indicator in config['economic_data']['indicators']:
            series = fred.get_series(indicator)
            latest_value = series.iloc[-1]
            latest_date = series.index[-1].strftime('%Y-%m-%d')
            data_points[indicator] = f"{latest_value} (as of {latest_date})"
        return f"Latest Macroeconomic Indicators: {json.dumps(data_points, indent=2)}"
    except Exception as e:
        logging.error(f"Failed to get FRED data: {e}")
        return "Could not retrieve macroeconomic data."

# --- Section 3: Self-Learning & Performance Review ---
def load_recommendations():
    path = config['user_profile']['recommendations_log_path']
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_recommendations(log_data):
    path = config['user_profile']['recommendations_log_path']
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

def evaluate_past_recommendations():
    if not config['prometheus_module']['learning_enabled']:
        return "Self-learning module disabled."
    
    log = load_recommendations()
    lookback_days = config['prometheus_module']['performance_lookback_days']
    cutoff_date = datetime.now() - timedelta(days=lookback_days)
    
    relevant_logs = [r for r in log if datetime.fromisoformat(r['date']) > cutoff_date and r['action'] in ['买入', '卖出']]
    if not relevant_logs:
        return "No scorable recommendations in the last 30 days."

    success_count = 0
    total_count = len(relevant_logs)
    report_details = []

    for rec in relevant_logs:
        try:
            hist_data = fetch_historical_data(rec['code'], lookback_days + 15) # Fetch extra data
            rec_date = datetime.fromisoformat(rec['date']).strftime('%Y-%m-%d')
            
            # Find the price on the recommendation date and 5 trading days later
            start_price = hist_data.loc[rec_date]['Close']
            end_date_loc = hist_data.index.get_loc(rec_date) + 5
            if end_date_loc >= len(hist_data): continue
            end_price = hist_data.iloc[end_date_loc]['Close']
            
            actual_return = (end_price / start_price) - 1
            
            is_success = False
            if rec['action'] == '买入' and actual_return > 0.005: # Success if it rose > 0.5%
                is_success = True
            elif rec['action'] == '卖出' and actual_return < -0.005: # Success if it fell > 0.5%
                is_success = True
            
            if is_success:
                success_count += 1
            
            report_details.append(f"- On {rec_date}, recommended '{rec['action']}' for {rec['name']}. Actual 5-day return was {actual_return:.2%}. Result: {'Success' if is_success else 'Fail'}.")

        except Exception as e:
            logging.warning(f"Could not evaluate recommendation for {rec['name']}: {e}")
            total_count -= 1

    win_rate = (success_count / total_count) * 100 if total_count > 0 else 0
    summary = f"**Self-Learning Performance Review (Last {lookback_days} Days):**\n- **Win Rate:** {win_rate:.2f}%\n- **Detailed Breakdown:**\n" + "\n".join(report_details)
    return summary

# --- Section 4: Monte Carlo Future Prediction ---
def run_monte_carlo_simulation(all_fund_data):
    if not config['prometheus_module']['monte_carlo']['enabled']:
        return "Monte Carlo simulation disabled.", None

    try:
        logging.info("Starting Monte Carlo simulation...")
        # Combine historical data for all funds in the portfolio
        combined_data = pd.concat([df['Close'] for df in all_fund_data.values()], axis=1)
        combined_data.columns = list(all_fund_data.keys())
        
        daily_returns = combined_data.pct_change().dropna()
        mean_returns = daily_returns.mean()
        cov_matrix = daily_returns.cov()
        
        num_simulations = config['prometheus_module']['monte_carlo']['simulations']
        num_days = config['prometheus_module']['monte_carlo']['projection_days']
        
        results = np.zeros((num_days, num_simulations))
        initial_portfolio_value = 100 # Start with a normalized value

        for i in range(num_simulations):
            # For simplicity, assume equal weighting. A real version would use portfolio weights.
            daily_vol = np.random.multivariate_normal(mean_returns, cov_matrix, num_days)
            portfolio_daily_returns = daily_vol.mean(axis=1)
            path = np.zeros(num_days)
            path[0] = initial_portfolio_value * (1 + portfolio_daily_returns[0])
            for t in range(1, num_days):
                path[t] = path[t-1] * (1 + portfolio_daily_returns[t])
            results[:, i] = path

        plt.figure(figsize=(12, 7))
        plt.plot(results)
        plt.title(f'Portfolio Value Projection ({num_simulations} Simulations over {num_days} Days)', fontsize=16)
        plt.xlabel('Trading Days from Today', fontsize=12)
        plt.ylabel('Normalized Portfolio Value', fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.6)
        
        final_values = pd.Series(results[-1, :])
        percentiles = final_values.quantile([0.05, 0.50, 0.95])
        
        chart_path = 'charts/monte_carlo_projection.png'
        plt.savefig(chart_path)
        plt.close()

        summary = f"**Monte Carlo Simulation Results ({num_simulations} paths, {num_days} days):**\n" \
                  f"- **Best Case (95th percentile):** Value might increase to {percentiles[0.95]:.2f}.\n" \
                  f"- **Median Outcome (50th percentile):** Value is expected to be around {percentiles[0.50]:.2f}.\n" \
                  f"- **Worst Case (5th percentile):** Value might decrease to {percentiles[0.05]:.2f}."
        
        return summary, chart_path
    except Exception as e:
        logging.error(f"Monte Carlo simulation failed: {e}")
        return "Monte Carlo simulation failed to run.", None

# --- Section 5: Ultimate AI Council ---
def ultimate_ai_council(context):
    logging.info("Convening the Ultimate AI Council...")

    # The single, comprehensive prompt for the most advanced model
    prompt = f"""
    You are the "Prometheus" AI, a council of financial experts embodied in a single large language model. Your task is to generate a complete, institutional-grade investment report based on the provided data.

    **Objective:** Provide a clear, actionable, and well-reasoned investment strategy for the user for the afternoon session.

    **User Profile:**
    - Risk Profile: {config['user_profile']['risk_profile']}
    - Investment Philosophy: "{config['user_profile']['investment_philosophy']}"

    **Current Portfolio Holdings:**
    {json.dumps(context['portfolio'], indent=2)}

    **--- INPUT DATA ---**

    **1. Self-Learning Performance Review (How well did my past advice perform?):**
    {context['performance_review']}

    **2. Market News & Sentiment (What is the market mood?):**
    {context['news']}

    **3. Macroeconomic Data (What is the big picture?):**
    {context['economic_data']}
    
    **4. Quantitative Analysis (What do the numbers and charts say?):**
    {context['quant_analysis']}

    **5. Future Risk Assessment (What do probabilistic models predict?):**
    {context['monte_carlo_summary']}

    **--- REQUIRED OUTPUT FORMAT ---**

    You MUST generate two parts, separated by the exact string "---DETAILED_REPORT_CUT---".

    **Part 1: The Executive Summary (for README.md)**
    This part should be concise and visual.

    # 🔥 Prometheus Daily Investment Briefing

    **Report Time:** {context['current_time']}

    **Today's Core Thesis:** (A single, powerful sentence summarizing the market outlook)

    ---

    ### Portfolio Dashboard

    | Fund Name | Type | **Action** | **Confidence** | Justification |
    | :--- | :--- | :--- | :--- | :--- |
    (Fill this table for EACH fund in the user's fund pool, providing an action like 'Hold', 'Buy', 'Trim', 'Sell', 'Avoid' and a confidence level: High, Medium, Low)

    ---

    ### Future 90-Day Wealth Projection (Monte Carlo Simulation)

    ![Portfolio Projection](charts/monte_carlo_projection.png)

    **Chief Risk Officer's Verdict:** (Interpret the Monte Carlo results. Provide a clear risk level: Low, Medium, High, or Critical. Explain why.)

    ---

    *Disclaimer: This AI-generated report is for informational purposes only and does not constitute investment advice. All financial decisions carry risk.*

    ---DETAILED_REPORT_CUT---

    **Part 2: The In-Depth Analysis (for reports/report_YYYY-MM-DD.md)**
    This is the detailed "meeting minutes" of the AI council.

    #  Prometheus In-Depth Analysis - {context['current_date']}

    ## 1. CIO's Opening Statement
    (Provide a comprehensive market overview, explaining how today's thesis was formed.)

    ## 2. Self-Learning & Strategy Adjustment
    (Discuss the performance review. Explicitly state how past successes or failures are influencing today's recommendations. For example: "Given our recent poor performance in predicting tech sector movements, we are adopting a more cautious 'Hold' stance today despite bullish indicators.")

    ## 3. Detailed Fund-by-Fund Breakdown
    (For each fund, provide a multi-paragraph analysis covering:)
    - **Macro View:** How does the economic environment affect this sector?
    - **Quant View:** What do the technical indicators (RSI, MACD, etc.) suggest?
    - **Sentiment View:** Is the news flow positive or negative for this sector?
    - **Final Decision Rationale:** Synthesize the above to justify the final recommendation in the dashboard.

    ## 4. Risk Assessment & Contingency
    (Elaborate on the CRO's verdict. What are the key risks to the portfolio? What events could invalidate today's thesis?)

    """

    try:
        logging.info("Generating report with Gemini 1.5 Pro...")
        response = AI_MODEL.generate_content(prompt)
        report_text = response.text
        summary, detail = report_text.split("---DETAILED_REPORT_CUT---", 1)
        return summary.strip(), detail.strip()
    except Exception as e:
        logging.error(f"AI report generation failed: {e}")
        error_summary = "# 🔥 Prometheus Briefing Failed\n\nAI model failed to generate a report. Please check the logs."
        error_detail = f"# Report Generation Error\n\n{e}"
        return error_summary, error_detail


# --- Section 6: Main Execution Block ---
def main():
    start_time = datetime.now(pytz.timezone('Asia/Shanghai'))
    logging.info(f"--- Project Prometheus Engine START at {start_time.strftime('%Y-%m-%d %H:%M:%S')} ---")
    
    context = {
        'current_time': start_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
        'current_date': start_time.strftime('%Y-%m-%d')
    }

    # 1. Self-Learning
    context['performance_review'] = evaluate_past_recommendations()

    # 2. Data Acquisition (Parallel)
    with ThreadPoolExecutor(max_workers=10) as executor:
        news_future = executor.submit(scrape_news)
        eco_future = executor.submit(get_economic_data)
        
        fund_codes = [f['code'] for f in config['index_funds']]
        hist_data_futures = {code: executor.submit(fetch_historical_data, code, 365) for code in fund_codes}

        context['news'] = "\n- ".join(news_future.result())
        context['economic_data'] = eco_future.result()
        
        all_fund_data = {}
        quant_reports = []
        for code, future in hist_data_futures.items():
            try:
                data = future.result()
                all_fund_data[code] = data
                # Technical Analysis
                data.ta.rsi(append=True)
                data.ta.macd(append=True)
                latest = data.iloc[-1]
                quant_reports.append(f"  - {config['index_funds'][fund_codes.index(code)]['name']} ({code}): RSI={latest['RSI_14']:.2f}, MACD Signal={'Golden Cross' if latest['MACD_12_26_9'] > latest['MACDs_12_26_9'] else 'Dead Cross'}")
            except Exception as e:
                logging.error(f"Failed to process data for {code}: {e}")
        context['quant_analysis'] = "Latest Technical Indicators:\n" + "\n".join(quant_reports)

    # 3. Load Portfolio
    try:
        with open(config['user_profile']['portfolio_path'], 'r', encoding='utf-8') as f:
            context['portfolio'] = json.load(f)
    except Exception as e:
        logging.error(f"Could not load portfolio: {e}")
        context['portfolio'] = []

    # 4. Future Prediction
    context['monte_carlo_summary'], _ = run_monte_carlo_simulation(all_fund_data)

    # 5. AI Council Decision
    summary_report, detail_report = ultimate_ai_council(context)

    # 6. Save Outputs
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(summary_report)
    
    report_filename = f"reports/report_{context['current_date']}.md"
    os.makedirs('reports', exist_ok=True)
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(detail_report)

    # (Future enhancement: Parse recommendations from AI output and save to log)
    # This part is complex as it requires reliable NLP from the AI output.
    # For now, the log remains a manual or semi-manual process until AI output is 100% structured.

    end_time = datetime.now(pytz.timezone('Asia/Shanghai'))
    logging.info(f"--- Project Prometheus Engine END at {end_time.strftime('%Y-%m-%d %H:%M:%S')} ---")
    logging.info(f"--- Total execution time: {end_time - start_time} ---")


if __name__ == "__main__":
    main()
