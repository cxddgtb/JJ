import os
import datetime
import time
import json
import re
import concurrent.futures
import traceback
import google.generativeai as genai
import requests
import pandas as pd
import yfinance as yf
from bs4 import BeautifulSoup
from ddgs import DDGS

# --- 全局配置 ---
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}
TIMESTAMP_FILE, MIN_INTERVAL_HOURS, REQUESTS_TIMEOUT = "last_run_timestamp.txt", 6, 30

# --- 基础辅助函数 ---
def load_config():
    with open('config.json', 'r', encoding='utf-8') as f: config = json.load(f)
    config.setdefault('historical_days_to_display', 7)
    return config

def check_time_interval():
    if os.getenv('GITHUB_EVENT_NAME') != 'repository_dispatch' or not os.path.exists(TIMESTAMP_FILE): return True
    with open(TIMESTAMP_FILE, "r") as f: last_run_timestamp = float(f.read())
    if (time.time() - last_run_timestamp) / 3600 < MIN_INTERVAL_HOURS: return False
    return True

def update_timestamp():
    with open(TIMESTAMP_FILE, "w") as f: f.write(str(time.time()))

# --- 数据获取模块 (yfinance核心) ---
def get_fund_data_from_yfinance(fund_code, history_days, ma_days):
    """
    终极方案: 使用yfinance获取基金历史数据。
    自动尝试 .SS (上海) 和 .SZ (深圳) 后缀。
    """
    print(f"    YFINANCE: 正在为 {fund_code} 启动雅虎财经数据核心...")
    
    tickers_to_try = [f"{fund_code}.SS", f"{fund_code}.SZ"]
    hist_df = None
    
    for ticker in tickers_to_try:
        try:
            fund = yf.Ticker(ticker)
            # 获取比计算均线所需天数更多的数据，以确保均线准确
            hist_df = fund.history(period=f"{history_days + ma_days}d")
            if not hist_df.empty:
                print(f"    YFINANCE: ✅ 成功使用代码 {ticker} 获取到数据。")
                break # 成功获取，跳出循环
        except Exception:
            # yfinance在找不到ticker时可能会打印错误，我们忽略它并继续
            continue
            
    if hist_df is None or hist_df.empty:
        raise ValueError(f"无法在雅虎财经找到代码为 {fund_code} 的基金数据(.SS/.SZ均尝试失败)。")
        
    # --- 数据处理 ---
    # yfinance返回的数据列名是大写的
    hist_df.rename(columns={'Open': '开盘', 'High': '最高', 'Low': '最低', 'Close': '收盘', 'Volume': '成交量'}, inplace=True)
    
    # 计算日增长率
    hist_df['日增长率'] = hist_df['收盘'].pct_change() * 100
    
    # 计算移动平均线
    hist_df[f'MA{ma_days}'] = hist_df['收盘'].rolling(window=ma_days).mean()
    
    # 获取基金名称
    try:
        fund_name = fund.info.get('longName', fund_code)
    except Exception:
        fund_name = fund_code # 如果获取名称失败，则使用代码

    return fund_name, hist_df.tail(history_days) # 只返回需要的历史天数

# --- 数据处理与报告生成 ---
def process_fund_data(fund_name, hist_df, fund_code, ma_days, days_to_display):
    try:
        print(f"正在处理基金 {fund_code} 的数据...")
        latest_data = hist_df.iloc[-1]
        
        structured_data = {
            'name': fund_name, 'code': fund_code,
            'latest_price': latest_data['收盘'],
            'latest_ma': latest_data[f'MA{ma_days}'],
            'daily_growth': latest_data['日增长率'],
            'ma_days': ma_days
        }
        
        recent_df = hist_df.tail(days_to_display).sort_index(ascending=False)
        table_rows = []
        for index, row in recent_df.iterrows():
            ma_val = row[f'MA{ma_days}']
            ma_str = f"{ma_val:.4f}" if not pd.isna(ma_val) else "N/A"
            trend_emoji = "📈" if row['收盘'] > ma_val else "📉" if not pd.isna(ma_val) else "🤔"
            table_rows.append(f"| {index.strftime('%Y-%m-%d')} | {row['收盘']:.4f}   | {ma_str}    | {trend_emoji}  |")

        formatted_string = f"""
### 基金: {fund_name} ({fund_code})
- **最新净值**: {latest_data['收盘']:.4f} (截至: {latest_data.name.strftime('%Y-%m-%d')})
- **{ma_days}日均线**: {latest_data[f'MA{ma_days}']:.4f if not pd.isna(latest_data[f'MA{ma_days}']) else '数据不足'}
- **技术分析**: 当前净值在 {ma_days}日均线**{'之上' if latest_data['收盘'] > latest_data[f'MA{ma_days}'] else '之下'}**。
- **最近 {days_to_display} 日详细数据**:
| 日期       | 单位净值 | {ma_days}日均线 | 趋势 |
|:-----------|:---------|:------------|:-----|
""" + "\n".join(table_rows)
        return structured_data, formatted_string
    except Exception as e:
        print(f"❌ 处理基金 {fund_code} 数据时出错: {e}"); traceback.print_exc()
        return None, None

# ... [search_news, get_sector_data, generate_rule_based_report, AI report, call_gemini_ai 等函数保持和之前版本一致] ...
def search_news(keyword):
    print(f"正在搜索新闻: {keyword}...")
    try:
        with DDGS() as ddgs:
            return "\n".join([f"- [标题] {r['title']}\n  [摘要] {r.get('body', '无')}\n" for r in ddgs.news(keyword, region='cn-zh', safesearch='off', max_results=5)])
    except Exception as e: return f"搜索关键词 '{keyword}' 失败: {e}"
def get_sector_data():
    print("正在爬取行业板块数据...")
    try:
        response = requests.get("http://quote.eastmoney.com/center/boardlist.html#industry_board", headers=HEADERS, timeout=REQUESTS_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        sectors = [{'name': cols[1].find('a').text.strip(), 'change': float(cols[4].text.strip().replace('%', ''))} for row in soup.select('table#table_wrapper-table tbody tr') if len(cols := row.find_all('td')) > 5]
        sectors.sort(key=lambda x: x['change'], reverse=True)
        rising_str = "\n".join([f"  - {s['name']}: {s['change']:.2f}%" for s in sectors[:10]])
        falling_str = "\n".join([f"  - {s['name']}: {s['change']:.2f}%" for s in sectors[-10:]])
        return f"**【热门上涨板块】**\n{rising_str}\n\n**【热门下跌板块】**\n{falling_str}"
    except Exception as e:
        print(f"❌ 行业板块数据爬取失败: {e}"); return "行业板块数据爬取失败。"
def generate_rule_based_report(fund_datas, beijing_time):
    print("正在生成“规则大脑”分析报告...")
    report_parts = [f"# 基金量化规则分析报告 ({beijing_time.strftime('%Y-%m-%d')})\n", "本报告由预设量化规则生成，仅供参考。\n"]
    if not fund_datas:
        report_parts.append("### **注意：未能从雅虎财经获取任何基金数据，无法生成分析。**")
    else:
        for data in fund_datas:
            score, reasons = 0, []
            if not pd.isna(data['latest_ma']):
                if data['latest_price'] > data['latest_ma']: score += 2; reasons.append(f"净值({data['latest_price']:.4f})在{data['ma_days']}日均线({data['latest_ma']:.4f})之上")
                else: score -= 2; reasons.append(f"净值({data['latest_price']:.4f})在{data['ma_days']}日均线({data['latest_ma']:.4f})之下")
            if data['daily_growth'] > 0: score += 1; reasons.append(f"当日上涨({data['daily_growth']:.2f}%)")
            else: score -= 1; reasons.append(f"当日下跌({data['daily_growth']:.2f}%)")
            if score == 3: conclusion = "强烈看好 🚀"
            elif score == 1: conclusion = "谨慎乐观 👍"
            elif score == -1: conclusion = "注意风险 ⚠️"
            else: conclusion = "建议减仓 📉"
            report_parts.append(f"### {data['name']} ({data['code']})\n- **量化评分**: {score}\n- **综合结论**: {conclusion}\n- **评分依据**: {', '.join(reasons)}\n")
    report_parts.append("\n---\n**免责声明**: 本报告由自动化规则生成，不构成任何投资建议。")
    return "\n".join(report_parts)
def call_gemini_ai(prompt):
    try:
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt, request_options={'timeout': 180})
        return response.text
    except Exception as e:
        print(f"❌ 调用 Gemini AI 失败: {e}"); traceback.print_exc()
        return "AI模型调用失败，请检查API密钥或网络连接。"
def generate_ai_based_report(news, sectors, funds_string):
    print("正在请求“AI策略大脑”生成分析报告...")
    if not funds_string.strip():
        return "由于未能获取任何基金的详细数据，AI策略大脑无法进行分析。"
    analysis_prompt = f"作为一名数据驱动的量化投资策略师...[省略详细指令]...\n**第一部分：宏观新闻**\n{news}\n**第二部分：板块轮动**\n{sectors}\n**第三部分：持仓基金详细数据**\n{funds_string}"
    draft_article = call_gemini_ai(analysis_prompt)
    if "AI模型调用失败" in draft_article: return draft_article
    polish_prompt = f"作为一名善于用数据说话的投资社区KOL...[省略详细指令]...\n**【原始报告】**\n{draft_article}"
    return call_gemini_ai(polish_prompt)
    
def main():
    if not check_time_interval(): return
    config = load_config()
    beijing_time = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    
    structured_fund_datas, formatted_fund_strings = [], []
    print("开始并行获取所有基金数据...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(config['fund_codes'])) as executor:
        future_to_code = {executor.submit(get_fund_data_from_yfinance, code, config['historical_days_to_fetch'], config['moving_average_days']): code for code in config['fund_codes']}
        for future in concurrent.futures.as_completed(future_to_code):
            code = future_to_code[future]
            try:
                fund_name, hist_df = future.result()
                structured, formatted = process_fund_data(fund_name, hist_df, code, config['moving_average_days'], config['historical_days_to_display'])
                if structured and formatted:
                    structured_fund_datas.append(structured)
                    formatted_fund_strings.append(formatted)
            except Exception as e:
                print(f"获取并处理基金 {code} 数据时发生顶层错误: {e}")

    all_news_text = "\n".join([search_news(kw) for kw in config['news_keywords']])
    sector_data_text = get_sector_data()

    if not os.path.exists('reports'): os.makedirs('reports')
    
    rule_report = generate_rule_based_report(structured_fund_datas, beijing_time)
    rule_filename = f"reports/基金分析报告-规则版_{beijing_time.strftime('%Y-%m-%d_%H-%M')}.md"
    with open(rule_filename, 'w', encoding='utf-8') as f: f.write(rule_report)
    print(f"\n✅ “规则大脑”报告已成功保存为: {rule_filename}")

    ai_report = generate_ai_based_report(all_news_text, sector_data_text, "\n".join(formatted_fund_strings))
    ai_filename = f"reports/基金分析报告-AI版_{beijing_time.strftime('%Y-%m-%d_%H-%M')}.md"
    with open(ai_filename, 'w', encoding='utf-8') as f: f.write(ai_report)
    print(f"✅ “AI策略大脑”报告已成功保存为: {ai_filename}")

    update_timestamp()

if __name__ == "__main__":
    main()
