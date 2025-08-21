import os
import datetime
import time
import json
import concurrent.futures
import traceback
import google.generativeai as genai
import requests
import pandas as pd
import yfinance as yf
from bs4 import BeautifulSoup
from ddgs import DDGS
import re

# --- 全局配置 ---
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}
TIMESTAMP_FILE, MIN_INTERVAL_HOURS = "last_run_timestamp.txt", 6

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

# --- 数据获取模块 (“双保险”核心) ---
def get_fund_data_from_yfinance(fund_code, history_days):
    """第一保险: 尝试从yfinance获取深度历史数据"""
    print(f"    YFINANCE: 正在为 {fund_code} 启动雅虎财经数据核心...")
    tickers_to_try = [f"{fund_code}.SS", f"{fund_code}.SZ"]
    for ticker in tickers_to_try:
        try:
            hist_df = yf.Ticker(ticker).history(period=f"{history_days}d", auto_adjust=True)
            if not hist_df.empty:
                print(f"    YFINANCE: ✅ 成功使用代码 {ticker} 获取到数据。")
                fund_name = yf.Ticker(ticker).info.get('longName', fund_code)
                return {'type': 'history', 'name': fund_name, 'data': hist_df}
        except Exception: continue
    return None

def get_fund_data_from_search(fund_code):
    """第二保险: 如果yfinance失败，从搜索引擎获取当日快照"""
    print(f"    SEARCH_ENGINE: yfinance失败, 为 {fund_code} 启动搜索引擎备用方案...")
    queries = [f"{fund_code} 基金净值", f"基金 {fund_code} 最新净值"]
    with DDGS(timeout=20) as ddgs:
        for query in queries:
            try:
                results = list(ddgs.text(query, region='cn-zh', max_results=2))
                for result in results:
                    snippet, title = result.get('body', ''), result.get('title', '')
                    match = re.search(r'(\d{4}[年-]\d{2}[月-]\d{2}日?).*?单位净值.*?(\d+\.\d+).*?(?:日增长率|涨跌幅).*?(-?\d+\.\d+)%', snippet)
                    if match:
                        fsrq, dwjz, jzzzl = match.groups()
                        fsrq_formatted = re.sub(r'[年月日]', '-', fsrq).strip('-')
                        fund_name = re.search(r'(.*?)\(', title).group(1).strip() if re.search(r'(.*?)\(', title) else fund_code
                        print(f"    SEARCH_ENGINE: ✅ 成功从搜索结果解析 {fund_code} 数据。")
                        return {'type': 'snapshot', 'name': fund_name, 'date': fsrq_formatted, 'price': dwjz, 'growth': jzzzl}
            except Exception as e: print(f"      -> 查询 '{query}' 时出现临时错误: {e}")
    raise ValueError("所有搜索引擎查询均未能成功解析净值。")

def get_fund_data_robust(fund_code, history_days):
    """“双保险”调度器"""
    result = get_fund_data_from_yfinance(fund_code, history_days)
    if result:
        return result
    return get_fund_data_from_search(fund_code)

# --- 数据处理与报告生成 (终极修复) ---
def process_fund_data(result, fund_code, ma_days, days_to_display):
    try:
        if result['type'] == 'history':
            print(f"正在处理基金 {fund_code} 的历史数据...")
            fund_name, hist_df = result['name'], result['data']
            hist_df.rename(columns={'Close': '收盘'}, inplace=True)
            hist_df['收盘'] = pd.to_numeric(hist_df['收盘'], errors='coerce')
            hist_df.dropna(subset=['收盘'], inplace=True)
            hist_df['日增长率'] = hist_df['收盘'].pct_change() * 100
            hist_df[f'MA{ma_days}'] = hist_df['收盘'].rolling(window=ma_days).mean()
            latest_data = hist_df.iloc[-1]
            structured = {'name': fund_name, 'code': fund_code, 'latest_price': latest_data['收盘'], 'latest_ma': latest_data[f'MA{ma_days}'], 'daily_growth': latest_data['日增长率'], 'ma_days': ma_days}
            recent_df = hist_df.tail(days_to_display).sort_index(ascending=False)
            table_rows = [f"| {idx.strftime('%Y-%m-%d')} | {row['收盘']:.4f} | {row[f'MA{ma_days}']:.4f if not pd.isna(row[f'MA{ma_days}']) else 'N/A'} | {'📈' if row['收盘'] > row[f'MA{ma_days}'] else '📉' if not pd.isna(row[f'MA{ma_days}']) else '🤔'} |" for idx, row in recent_df.iterrows()]
            formatted = f"### 基金: {fund_name} ({fund_code})\n- **数据来源**: 雅虎财经 (深度历史)\n- **最新净值**: {latest_data['收盘']:.4f} (截至: {latest_data.name.strftime('%Y-%m-%d')})\n- **{ma_days}日均线**: {latest_data[f'MA{ma_days}']:.4f if not pd.isna(latest_data[f'MA{ma_days}']) else '数据不足'}\n- **最近 {days_to_display} 日详细数据**:\n| 日期 | 单位净值 | {ma_days}日均线 | 趋势 |\n|:---|:---|:---|:---|\n" + "\n".join(table_rows)
            return structured, formatted
        
        elif result['type'] == 'snapshot':
            print(f"正在处理基金 {fund_code} 的当日快照...")
            fund_name = result['name']
            structured = {'name': fund_name, 'code': fund_code, 'latest_price': float(result['price']), 'latest_ma': float('nan'), 'daily_growth': float(result['growth']), 'ma_days': ma_days}
            formatted = f"### 基金: {fund_name} ({fund_code})\n- **数据来源**: 搜索引擎 (当日快照)\n- **最新净值**: {result['price']} (截至: {result['date']})\n- **日涨跌幅**: {result['growth']}%\n- **备注**: 未能获取完整的历史数据，无法计算移动均线。"
            return structured, formatted
            
    except Exception as e:
        print(f"❌ 处理基金 {fund_code} 数据时出错: {e}"); traceback.print_exc()
        return None, None

# ... [其他辅助函数 search_news, get_sector_data, reports, call_gemini_ai 等保持不变] ...
def search_news(keyword):
    print(f"正在搜索新闻: {keyword}...")
    with DDGS() as ddgs: return "\n".join([f"- [标题] {r['title']}\n  [摘要] {r.get('body', '无')}\n" for r in ddgs.news(keyword, region='cn-zh', max_results=5)])
def get_sector_data():
    print("正在爬取行业板块数据...")
    try:
        response = requests.get("http://quote.eastmoney.com/center/boardlist.html#industry_board", headers=HEADERS, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        sectors = [{'name': c[1].find('a').text.strip(), 'change': float(c[4].text.replace('%',''))} for r in soup.select('table#table_wrapper-table tbody tr') if len(c:=r.find_all('td'))>5]
        sectors.sort(key=lambda x: x['change'], reverse=True)
        rising = "\n".join([f"  - {s['name']}: {s['change']:.2f}%" for s in sectors[:10]])
        falling = "\n".join([f"  - {s['name']}: {s['change']:.2f}%" for s in sectors[-10:]])
        return f"**【热门上涨板块】**\n{rising}\n\n**【热门下跌板块】**\n{falling}"
    except Exception as e: return f"行业板块数据爬取失败: {e}"
def generate_rule_based_report(fund_datas, beijing_time):
    report_parts = [f"# 基金量化规则分析报告 ({beijing_time.strftime('%Y-%m-%d')})\n"]
    if not fund_datas: report_parts.append("### **注意：所有数据源均未能获取任何基金数据。**")
    else:
        for data in fund_datas:
            score, reasons = 0, []
            if not pd.isna(data['latest_ma']):
                if data['latest_price'] > data['latest_ma']: score += 2; reasons.append("净值在均线之上")
                else: score -= 2; reasons.append("净值在均线之下")
            if not pd.isna(data['daily_growth']):
                if data['daily_growth'] > 0: score += 1; reasons.append("当日上涨")
                else: score -= 1; reasons.append("当日下跌")
            
            if pd.isna(data['latest_ma']): # 快照数据的特殊判断
                conclusion = "谨慎乐观 👍" if data['daily_growth'] > 0 else "注意风险 ⚠️"
            elif score >= 2: conclusion = "强烈看好 🚀"
            elif score >= 0: conclusion = "谨慎乐观 👍"
            elif score > -2: conclusion = "注意风险 ⚠️"
            else: conclusion = "建议减仓 📉"
            report_parts.append(f"### {data['name']} ({data['code']})\n- **量化评分**: {score if not pd.isna(data['latest_ma']) else 'N/A'}\n- **综合结论**: {conclusion}\n- **评分依据**: {', '.join(reasons)}\n")
    return "\n".join(report_parts)
def call_gemini_ai(prompt):
    try:
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        return genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt).text
    except Exception as e: return f"AI模型调用失败: {e}"
def generate_ai_based_report(news, sectors, funds_string):
    if not funds_string.strip(): return "由于未能获取任何基金的详细数据，AI策略大脑无法进行分析。"
    analysis_prompt = f"""作为一名顶级的中国市场对冲基金经理，请结合以下所有信息，撰写一份包含宏观、中观、微观三个层次的深度投研报告。
**注意：部分基金可能只有当日快照数据，缺乏历史均线，请在分析时明确指出这一点，并做出更谨慎的判断。**
**第一部分：市场新闻与情绪**\n{news}\n**第二部分：中观行业与板块轮动**\n{sectors}\n**第三部分：微观持仓基金技术状态**\n{funds_string}"""
    draft = call_gemini_ai(analysis_prompt)
    if "AI模型调用失败" in draft: return draft
    polish_prompt = f"作为一名善于用数据讲故事的投资KOL...[省略详细指令]...\n**【原始报告】**\n{draft}"
    return call_gemini_ai(polish_prompt)
    
def main():
    if not check_time_interval(): return
    config, beijing_time = load_config(), datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    structured_fund_datas, formatted_fund_strings, news_text, sector_text = [], [], "", ""

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_funds = {executor.submit(get_fund_data_robust, c, config['historical_days_to_fetch']): c for c in config['fund_codes']}
        future_news = {executor.submit(search_news, kw): kw for kw in config['news_keywords']}
        future_sector = executor.submit(get_sector_data)

        for future in concurrent.futures.as_completed(future_funds):
            code = future_funds[future]
            try:
                result = future.result()
                if result:
                    structured, formatted = process_fund_data(result, code, config['moving_average_days'], config['historical_days_to_display'])
                    if structured: structured_fund_datas.append(structured); formatted_fund_strings.append(formatted)
            except Exception as e: print(f"获取并处理基金 {code} 时发生顶层错误: {e}")
        
        news_text = "\n".join([f.result() for f in concurrent.futures.as_completed(future_news)])
        sector_text = future_sector.result()

    if not os.path.exists('reports'): os.makedirs('reports')
    
    rule_report = generate_rule_based_report(structured_fund_datas, beijing_time)
    with open(f"reports/基金分析报告-规则版_{beijing_time.strftime('%Y-%m-%d')}.md", 'w', encoding='utf-8') as f: f.write(rule_report)
    print(f"\n✅ “规则大脑”报告已成功保存。")

    ai_report = generate_ai_based_report(news_text, sector_text, "\n".join(formatted_fund_strings))
    with open(f"reports/基金分析报告-AI版_{beijing_time.strftime('%Y-%m-%d')}.md", 'w', encoding='utf-8') as f: f.write(ai_report)
    print(f"✅ “AI策略大脑”报告已成功保存。")

    update_timestamp()

if __name__ == "__main__":
    main()
