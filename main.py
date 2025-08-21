import os
import datetime
import time
import json
import concurrent.futures
import traceback
import google.generativeai as genai
import requests
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

# --- 全局设置 ---
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36', 'Referer': 'http://fund.eastmoney.com/'}
TIMESTAMP_FILE = "last_run_timestamp.txt"
MIN_INTERVAL_HOURS = 6
REQUESTS_TIMEOUT = 20

# --- 功能函数 ---
def load_config():
    """从config.json加载配置"""
    print("正在加载配置文件 config.json...")
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    config.setdefault('historical_days_to_display', 7)
    return config

def check_time_interval():
    github_event_name = os.getenv('GITHUB_EVENT_NAME')
    if github_event_name != 'repository_dispatch': return True
    if not os.path.exists(TIMESTAMP_FILE): return True
    with open(TIMESTAMP_FILE, "r") as f: last_run_timestamp = float(f.read())
    current_timestamp = time.time()
    hours_diff = (current_timestamp - last_run_timestamp) / 3600
    if hours_diff < MIN_INTERVAL_HOURS:
        print(f"距离上次执行（{hours_diff:.2f}小时）未超过{MIN_INTERVAL_HOURS}小时，本次跳过。")
        return False
    return True

def update_timestamp():
    with open(TIMESTAMP_FILE, "w") as f: f.write(str(time.time()))

def search_news(keyword):
    print(f"正在搜索新闻: {keyword}...")
    try:
        with DDGS() as ddgs:
            return "\n".join([f"- [标题] {r['title']}\n  [摘要] {r.get('body', '无')}\n" for r in ddgs.news(keyword, region='cn-zh', safesearch='off', max_results=5)])
    except Exception as e: return f"搜索关键词 '{keyword}' 失败: {e}"

def get_sector_data():
    print("正在爬取行业板块数据...")
    url = "http://quote.eastmoney.com/center/boardlist.html#industry_board"
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT)
        soup = BeautifulSoup(response.text, 'html.parser')
        sectors = [{'name': cols[1].find('a').text.strip(), 'change': float(cols[4].text.strip().replace('%', ''))} for row in soup.select('table#table_wrapper-table tbody tr') if len(cols := row.find_all('td')) > 5]
        sectors.sort(key=lambda x: x['change'], reverse=True)
        rising_str = "\n".join([f"  - {s['name']}: {s['change']:.2f}%" for s in sectors[:10]])
        falling_str = "\n".join([f"  - {s['name']}: {s['change']:.2f}%" for s in sectors[-10:]])
        return f"**【热门上涨板块】**\n{rising_str}\n\n**【热门下跌板块】**\n{falling_str}"
    except Exception as e: return f"行业板块数据爬取失败: {e}"

def get_fund_raw_data(fund_code, history_days):
    print(f"正在获取基金 {fund_code} 的原始数据...")
    url = f"http://api.fund.eastmoney.com/f10/lsjz?fundCode={fund_code}&pageIndex=1&pageSize={history_days}"
    response = requests.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT).json()
    return response['Data']

def process_fund_data(raw_data, fund_code, ma_days, days_to_display):
    """处理原始数据，返回结构化数据和格式化字符串"""
    print(f"正在处理基金 {fund_code} 的数据...")
    fund_name = raw_data['FundBaseInfo']['JJJC']
    df = pd.DataFrame(raw_data['LSJZList'])
    df['FSRQ'] = pd.to_datetime(df['FSRQ'])
    df['DWJZ'] = pd.to_numeric(df['DWJZ'])
    df['JZZZL'] = pd.to_numeric(df['JZZZL'])
    df = df.sort_values('FSRQ')
    
    df[f'MA{ma_days}'] = df['DWJZ'].rolling(window=ma_days).mean()
    
    latest_data = df.iloc[-1]
    latest_price = latest_data['DWJZ']
    latest_ma = latest_data[f'MA{ma_days}']
    
    # 准备结构化数据
    structured_data = {
        'name': fund_name, 'code': fund_code,
        'latest_price': latest_price, 'latest_ma': latest_ma,
        'daily_growth': latest_data['JZZZL'], 'ma_days': ma_days
    }
    
    # 准备格式化字符串
    recent_df = df.tail(days_to_display).sort_values('FSRQ', ascending=False)
    table_rows = []
    for _, row in recent_df.iterrows():
        ma_val = row[f'MA{ma_days}']
        ma_str = f"{ma_val:.4f}" if not pd.isna(ma_val) else "N/A"
        trend_emoji = "📈" if row['DWJZ'] > ma_val else "📉" if not pd.isna(ma_val) else "🤔"
        table_rows.append(f"| {row['FSRQ'].strftime('%Y-%m-%d')} | {row['DWJZ']:.4f}   | {ma_str}    | {trend_emoji}  |")
    
    formatted_string = f"""
### 基金: {fund_name} ({fund_code})
- **最新净值**: {latest_price:.4f} (日期: {latest_data['FSRQ'].strftime('%Y-%m-%d')})
- **{ma_days}日均线**: {latest_ma:.4f if not pd.isna(latest_ma) else '数据不足'}
- **技术分析**: 当前净值在 {ma_days}日均线**{'之上' if latest_price > latest_ma else '之下'}**，短期趋势可能**{'偏强' if latest_price > latest_ma else '偏弱'}**。
- **最近 {days_to_display} 日详细数据**:
| 日期       | 单位净值 | {ma_days}日均线 | 趋势 |
|:-----------|:---------|:------------|:-----|
""" + "\n".join(table_rows)

    return structured_data, formatted_string

def generate_rule_based_report(fund_datas, sector_data, beijing_time):
    print("正在生成“规则大脑”分析报告...")
    report_parts = [f"# 基金量化规则分析报告 ({beijing_time.strftime('%Y-%m-%d')})\n"]
    report_parts.append("本报告由预设量化规则生成，仅供参考。\n")
    
    for data in fund_datas:
        score = 0
        reasons = []
        if not pd.isna(data['latest_ma']):
            if data['latest_price'] > data['latest_ma']:
                score += 2
                reasons.append(f"净值({data['latest_price']:.4f})在{data['ma_days']}日均线({data['latest_ma']:.4f})之上")
            else:
                score -= 2
                reasons.append(f"净值({data['latest_price']:.4f})在{data['ma_days']}日均线({data['latest_ma']:.4f})之下")
        
        if data['daily_growth'] > 0:
            score += 1
            reasons.append(f"当日上涨({data['daily_growth']:.2f}%)")
        else:
            score -= 1
            reasons.append(f"当日下跌({data['daily_growth']:.2f}%)")
            
        if score == 3: conclusion = "强烈看好 🚀"
        elif score == 1: conclusion = "谨慎乐观 👍"
        elif score == -1: conclusion = "注意风险 ⚠️"
        else: conclusion = "建议减仓 📉"
        
        report_parts.append(f"### {data['name']} ({data['code']})\n- **量化评分**: {score}\n- **综合结论**: {conclusion}\n- **评分依据**: {', '.join(reasons)}\n")
        
    report_parts.append("\n--- \n**免责声明**: 本报告由自动化规则生成，不构成任何投资建议。")
    return "\n".join(report_parts)

def generate_ai_based_report(news, sectors, funds_string):
    print("正在请求“AI策略大脑”生成分析报告...")
    analysis_prompt = f"作为一名数据驱动的量化投资策略师，请严格根据以下三方面信息，撰写一份逻辑严密、有数据支撑的投资策略报告...\n[...这里省略了之前的详细Prompt...]\n**第一部分：宏观新闻**\n{news}\n**第二部分：板块轮动**\n{sectors}\n**第三部分：持仓基金详细数据**\n{funds_string}"
    draft_article = call_gemini_ai(analysis_prompt)
    
    if "AI模型调用失败" in draft_article:
        return draft_article # 直接返回错误信息
        
    polish_prompt = f"作为一名善于用数据说话的投资社区KOL，请将以下这份专业的投研报告，转化为一篇对普通投资者极具吸引力和说服力的文章...\n[...这里省略了之前的详细Prompt...]\n**【原始报告】**\n{draft_article}"
    return call_gemini_ai(polish_prompt)
    
def call_gemini_ai(prompt):
    try:
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt, request_options={'timeout': 180}) # 增加超时
        return response.text
    except Exception as e:
        print(f"调用 Gemini AI 失败: {e}")
        traceback.print_exc()
        return "AI模型调用失败，请检查API密钥或网络连接。"

def main():
    if not check_time_interval(): return
    config = load_config()
    beijing_time = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    
    # --- 并行获取所有原始数据 ---
    raw_fund_datas = {}
    all_news_text = ""
    sector_data_text = ""

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        news_futures = {executor.submit(search_news, kw): kw for kw in config['news_keywords']}
        fund_futures = {executor.submit(get_fund_raw_data, code, config['historical_days_to_fetch']): code for code in config['fund_codes']}
        sector_future = executor.submit(get_sector_data)

        for future in concurrent.futures.as_completed(fund_futures):
            code = fund_futures[future]
            raw_fund_datas[code] = future.result()
        
        all_news_text = "\n".join([f.result() for f in concurrent.futures.as_completed(news_futures)])
        sector_data_text = sector_future.result()

    # --- 数据处理 ---
    structured_fund_datas = []
    formatted_fund_strings = []
    for code in config['fund_codes']:
        if code in raw_fund_datas:
            try:
                structured, formatted = process_fund_data(raw_fund_datas[code], code, config['moving_average_days'], config['historical_days_to_display'])
                structured_fund_datas.append(structured)
                formatted_fund_strings.append(formatted)
            except Exception as e:
                print(f"处理基金 {code} 数据时出错: {e}")

    # --- 生成并保存报告 ---
    if not os.path.exists('reports'): os.makedirs('reports')

    # 1. 生成规则报告 (永远执行)
    try:
        rule_report = generate_rule_based_report(structured_fund_datas, sector_data_text, beijing_time)
        rule_filename = f"reports/基金分析报告-规则版_{beijing_time.strftime('%Y-%m-%d_%H-%M')}.md"
        with open(rule_filename, 'w', encoding='utf-8') as f: f.write(rule_report)
        print(f"\n✅ “规则大脑”报告已成功保存为: {rule_filename}")
    except Exception as e:
        print(f"\n❌ 生成“规则大脑”报告失败: {e}")

    # 2. 生成AI报告 (如果失败不影响程序)
    try:
        ai_report = generate_ai_based_report(all_news_text, sector_data_text, "\n".join(formatted_fund_strings))
        ai_filename = f"reports/基金分析报告-AI版_{beijing_time.strftime('%Y-%m-%d_%H-%M')}.md"
        with open(ai_filename, 'w', encoding='utf-8') as f: f.write(ai_report)
        print(f"✅ “AI策略大脑”报告已成功保存为: {ai_filename}")
    except Exception as e:
        print(f"\n❌ 生成“AI策略大脑”报告失败: {e}")

    update_timestamp()

if __name__ == "__main__":
    main()
