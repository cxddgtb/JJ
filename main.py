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
        print(f"❌ 行业板块数据爬取失败: {e}")
        return "行业板块数据爬取失败。"

# ⬇️⬇️⬇️ 核心改动 1: 增强了数据获取的健壮性 ⬇️⬇️⬇️
def get_fund_raw_data(fund_code, history_days):
    """获取单支基金的原始数据，增加了详细的错误处理"""
    print(f"正在获取基金 {fund_code} 的原始数据...")
    url = f"http://api.fund.eastmoney.com/f10/lsjz?fundCode={fund_code}&pageIndex=1&pageSize={history_days}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT)
        response.raise_for_status() # 如果状态码不是200，则引发异常
        data = response.json()
        # 检查返回的数据是否有效
        if not data.get('Data') or not data['Data'].get('LSJZList'):
            print(f"❌ 基金 {fund_code} 的API返回数据格式无效或为空。")
            return None
        return data['Data']
    except requests.exceptions.RequestException as e:
        print(f"❌ 基金 {fund_code} 网络请求失败: {e}")
        return None
    except json.JSONDecodeError:
        print(f"❌ 基金 {fund_code} 返回内容不是有效的JSON格式。")
        return None
    except Exception as e:
        print(f"❌ 获取基金 {fund_code} 数据时发生未知错误: {e}")
        return None

def process_fund_data(raw_data, fund_code, ma_days, days_to_display):
    """处理原始数据，同样增加错误处理"""
    try:
        print(f"正在处理基金 {fund_code} 的数据...")
        fund_name = raw_data['FundBaseInfo']['JJJC']
        df = pd.DataFrame(raw_data['LSJZList'])
        df['FSRQ'] = pd.to_datetime(df['FSRQ'])
        df['DWJZ'] = pd.to_numeric(df['DWJZ'])
        df['JZZZL'] = pd.to_numeric(df['JZZZL'], errors='coerce').fillna(0) # 容错处理
        df = df.sort_values('FSRQ')
        
        df[f'MA{ma_days}'] = df['DWJZ'].rolling(window=ma_days).mean()
        
        latest_data = df.iloc[-1]
        structured_data = {'name': fund_name, 'code': fund_code, 'latest_price': latest_data['DWJZ'], 'latest_ma': latest_data[f'MA{ma_days}'], 'daily_growth': latest_data['JZZZL'], 'ma_days': ma_days}
        
        recent_df = df.tail(days_to_display).sort_values('FSRQ', ascending=False)
        table_rows = []
        for _, row in recent_df.iterrows():
            ma_val = row[f'MA{ma_days}']
            ma_str = f"{ma_val:.4f}" if not pd.isna(ma_val) else "N/A"
            trend_emoji = "📈" if row['DWJZ'] > ma_val else "📉" if not pd.isna(ma_val) else "🤔"
            table_rows.append(f"| {row['FSRQ'].strftime('%Y-%m-%d')} | {row['DWJZ']:.4f}   | {ma_str}    | {trend_emoji}  |")
        
        formatted_string = f"""
### 基金: {fund_name} ({fund_code})
- **最新净值**: {latest_data['DWJZ']:.4f} (日期: {latest_data['FSRQ'].strftime('%Y-%m-%d')})
- **{ma_days}日均线**: {latest_data[f'MA{ma_days}']:.4f if not pd.isna(latest_data[f'MA{ma_days}']) else '数据不足'}
- **技术分析**: 当前净值在 {ma_days}日均线**{'之上' if latest_data['DWJZ'] > latest_data[f'MA{ma_days}'] else '之下'}**。
- **最近 {days_to_display} 日详细数据**:
| 日期       | 单位净值 | {ma_days}日均线 | 趋势 |
|:-----------|:---------|:------------|:-----|
""" + "\n".join(table_rows)
        return structured_data, formatted_string
    except Exception as e:
        print(f"❌ 处理基金 {fund_code} 数据时出错: {e}")
        return None, None

def generate_rule_based_report(fund_datas, beijing_time):
    print("正在生成“规则大脑”分析报告...")
    report_parts = [f"# 基金量化规则分析报告 ({beijing_time.strftime('%Y-%m-%d')})\n", "本报告由预设量化规则生成，仅供参考。\n"]
    
    if not fund_datas:
        report_parts.append("### **注意：未能成功获取并处理任何基金数据，无法生成分析。**\n请检查运行日志以了解详细错误信息。")
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

# ... [generate_ai_based_report 和 call_gemini_ai 函数保持不变] ...
def generate_ai_based_report(news, sectors, funds_string):
    print("正在请求“AI策略大脑”生成分析报告...")
    if not funds_string.strip():
        return "由于未能获取任何基金的详细数据，AI策略大脑无法进行分析。"
    # 省略了详细的Prompt字符串，保持和之前一致
    analysis_prompt = f"作为一名数据驱动的量化投资策略师...\n**第一部分：宏观新闻**\n{news}\n**第二部分：板块轮动**\n{sectors}\n**第三部分：持仓基金详细数据**\n{funds_string}"
    draft_article = call_gemini_ai(analysis_prompt)
    if "AI模型调用失败" in draft_article: return draft_article
    polish_prompt = f"作为一名善于用数据说话的投资社区KOL...\n**【原始报告】**\n{draft_article}"
    return call_gemini_ai(polish_prompt)
def call_gemini_ai(prompt):
    try:
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt, request_options={'timeout': 180})
        return response.text
    except Exception as e:
        print(f"❌ 调用 Gemini AI 失败: {e}"); traceback.print_exc()
        return "AI模型调用失败，请检查API密钥或网络连接。"

def main():
    if not check_time_interval(): return
    config = load_config()
    beijing_time = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    
    # --- 并行获取所有原始数据 ---
    raw_fund_datas = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        fund_futures = {executor.submit(get_fund_raw_data, code, config['historical_days_to_fetch']): code for code in config['fund_codes']}
        for future in concurrent.futures.as_completed(fund_futures):
            code, raw_data = fund_futures[future], future.result()
            # ⬇️⬇️⬇️ 核心改动 2: 只将成功获取的数据加入待处理列表 ⬇️⬇️⬇️
            if raw_data:
                raw_fund_datas[code] = raw_data

    # --- 串行处理数据（更易于调试）并收集其他信息 ---
    structured_fund_datas, formatted_fund_strings = [], []
    for code, raw_data in raw_fund_datas.items():
        structured, formatted = process_fund_data(raw_data, code, config['moving_average_days'], config['historical_days_to_display'])
        if structured and formatted:
            structured_fund_datas.append(structured)
            formatted_fund_strings.append(formatted)

    # --- 获取新闻和板块数据 ---
    all_news_text = "\n".join([search_news(kw) for kw in config['news_keywords']])
    sector_data_text = get_sector_data()

    # --- 生成并保存报告 ---
    if not os.path.exists('reports'): os.makedirs('reports')
    
    # 1. 生成规则报告 (永远执行)
    rule_report = generate_rule_based_report(structured_fund_datas, beijing_time)
    rule_filename = f"reports/基金分析报告-规则版_{beijing_time.strftime('%Y-%m-%d_%H-%M')}.md"
    with open(rule_filename, 'w', encoding='utf-8') as f: f.write(rule_report)
    print(f"\n✅ “规则大脑”报告已成功保存为: {rule_filename}")

    # 2. 生成AI报告 (如果失败不影响程序)
    ai_report = generate_ai_based_report(all_news_text, sector_data_text, "\n".join(formatted_fund_strings))
    ai_filename = f"reports/基金分析报告-AI版_{beijing_time.strftime('%Y-%m-%d_%H-%M')}.md"
    with open(ai_filename, 'w', encoding='utf-8') as f: f.write(ai_report)
    print(f"✅ “AI策略大脑”报告已成功保存为: {ai_filename}")

    update_timestamp()

if __name__ == "__main__":
    main()
