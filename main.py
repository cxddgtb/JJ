import os
import datetime
import time
import json
import re
import concurrent.futures
import traceback
import google.generativeai as genai
import requests
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
# ⬇️⬇️⬇️ 核心升级 1: 更新了库的引用 ⬇️⬇️⬇️
from ddgs import DDGS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- 全局配置 ---
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}
TIMESTAMP_FILE, MIN_INTERVAL_HOURS, REQUESTS_TIMEOUT = "last_run_timestamp.txt", 6, 30

# --- 基础辅助函数 (无改动) ---
def load_config():
    print("正在加载配置文件 config.json...")
    with open('config.json', 'r', encoding='utf-8') as f: config = json.load(f)
    config.setdefault('historical_days_to_display', 7)
    return config

def check_time_interval():
    # ... (代码不变) ...
    github_event_name = os.getenv('GITHUB_EVENT_NAME')
    if github_event_name != 'repository_dispatch': return True
    if not os.path.exists(TIMESTAMP_FILE): return True
    with open(TIMESTAMP_FILE, "r") as f: last_run_timestamp = float(f.read())
    hours_diff = (time.time() - last_run_timestamp) / 3600
    if hours_diff < MIN_INTERVAL_HOURS:
        print(f"距离上次执行（{hours_diff:.2f}小时）未超过{MIN_INTERVAL_HOURS}小时，本次跳过。")
        return False
    return True

def update_timestamp():
    with open(TIMESTAMP_FILE, "w") as f: f.write(str(time.time()))

# --- 数据获取模块 (完全重构) ---

# ⬇️⬇️⬇️ 核心升级 2: 全新的主攻方案 - 浏览器模拟“新浪财经” ⬇️⬇️⬇️
def get_fund_raw_data_from_sina_web(fund_code, history_days):
    """主方案：使用Selenium模拟浏览器，访问新浪财经网页"""
    print(f"    SINA_WEB: 正在启动浏览器核心获取 {fund_code}...")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=" + HEADERS['User-Agent'])
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        url = f"http://money.finance.sina.com.cn/fund/hgsz/{fund_code}.html"
        driver.get(url)
        
        # 等待数据表格出现
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "fund_history_table")))
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        table = soup.find('table', id='fund_history_table')
        rows = table.find('tbody').find_all('tr')
        
        lsjz_list = []
        for row in rows[:history_days]:
            cols = row.find_all('td')
            fsrq = cols[0].text.strip()
            dwjz = cols[1].text.strip()
            # 新浪的日增长率在第四列
            jzzzl_text = cols[3].text.strip().replace('%', '')
            jzzzl = float(jzzzl_text) if jzzzl_text != '' else 0.0
            lsjz_list.append({'FSRQ': fsrq, 'DWJZ': dwjz, 'JZZZL': str(jzzzl)})
        
        fund_name = soup.find('h1', id='fund_name').text.split('(')[0].strip()
        print(f"    SINA_WEB: ✅ 成功从网页获取 {fund_code} 数据。")
        lsjz_list.reverse()
        return {'FundBaseInfo': {'JJJC': fund_name}, 'LSJZList': lsjz_list}

    finally:
        driver.quit()

def get_fund_raw_data_from_eastmoney_api(fund_code, history_days):
    """备用方案: 尝试天天基金API (成功率较低)"""
    print(f"    EASTMONEY_API: 正在尝试获取 {fund_code}...")
    url = f"http://api.fund.eastmoney.com/f10/lsjz?fundCode={fund_code}&pageIndex=1&pageSize={history_days}"
    response = requests.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if not data.get('Data') or not data['Data'].get('LSJZList'):
        raise ValueError("天天基金API返回数据格式无效或为空")
    return data['Data']

def get_fund_raw_data_final_robust(fund_code, history_days):
    """终极健壮的数据获取函数，主攻新浪网页，API为备用"""
    print(f"\n开始获取基金 {fund_code} 的数据...")
    try:
        return get_fund_raw_data_from_sina_web(fund_code, history_days)
    except Exception as e_selenium:
        print(f"    SINA_WEB: ❌ 主攻方案(新浪网页)获取失败: {e_selenium}")
        print("    --> 自动切换至API备用方案...")
        try:
            return get_fund_raw_data_from_eastmoney_api(fund_code, history_days)
        except Exception as e_api:
            print(f"    EASTMONEY_API: ❌ 所有备用方案均失败: {e_api}")
            return None

# --- 其他所有函数 (process_fund_data, report generation, etc.) ---
# 这一部分和上一版完全一样，只需确保 search_news 的引用已更新
def search_news(keyword):
    print(f"正在搜索新闻: {keyword}...")
    try:
        # 核心升级 3: 使用新的 ddgs 库
        with DDGS() as ddgs:
            return "\n".join([f"- [标题] {r['title']}\n  [摘要] {r.get('body', '无')}\n" for r in ddgs.news(keyword, region='cn-zh', safesearch='off', max_results=5)])
    except Exception as e: return f"搜索关键词 '{keyword}' 失败: {e}"

def process_fund_data(raw_data, fund_code, ma_days, days_to_display):
    try:
        print(f"正在处理基金 {fund_code} 的数据...")
        fund_name = raw_data.get('FundBaseInfo', {}).get('JJJC', fund_code)
        df = pd.DataFrame(raw_data['LSJZList'])
        df['FSRQ'] = pd.to_datetime(df['FSRQ'])
        df['DWJZ'] = pd.to_numeric(df['DWJZ'])
        df['JZZZL'] = pd.to_numeric(df.get('JZZZL', '0'), errors='coerce').fillna(0)
        df = df.sort_values('FSRQ')
        df[f'MA{ma_days}'] = df['DWJZ'].rolling(window=ma_days).mean()
        latest_data = df.iloc[-1]
        structured_data = {'name': fund_name, 'code': fund_code, 'latest_price': latest_data['DWJZ'], 'latest_ma': latest_data[f'MA{ma_days}'], 'daily_growth': latest_data['JZZZL'], 'ma_days': ma_days}
        recent_df = df.tail(days_to_display).sort_values('FSRQ', ascending=False)
        table_rows = [f"| {row['FSRQ'].strftime('%Y-%m-%d')} | {row['DWJZ']:.4f}   | {row[f'MA{ma_days}']:.4f if not pd.isna(row[f'MA{ma_days}']) else 'N/A'}    | {'📈' if row['DWJZ'] > row[f'MA{ma_days}'] else '📉' if not pd.isna(row[f'MA{ma_days}']) else '🤔'}  |" for _, row in recent_df.iterrows()]
        formatted_string = f"### 基金: {fund_name} ({fund_code})\n- **最新净值**: {latest_data['DWJZ']:.4f} (日期: {latest_data['FSRQ'].strftime('%Y-%m-%d')})\n- **{ma_days}日均线**: {latest_data[f'MA{ma_days}']:.4f if not pd.isna(latest_data[f'MA{ma_days}']) else '数据不足'}\n- **技术分析**: 当前净值在 {ma_days}日均线**{'之上' if latest_data['DWJZ'] > latest_data[f'MA{ma_days}'] else '之下'}**。\n- **最近 {days_to_display} 日详细数据**:\n| 日期       | 单位净值 | {ma_days}日均线 | 趋势 |\n|:-----------|:---------|:------------|:-----|\n" + "\n".join(table_rows)
        return structured_data, formatted_string
    except Exception as e:
        print(f"❌ 处理基金 {fund_code} 数据时出错: {e}"); traceback.print_exc()
        return None, None

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
    # ... (代码不变) ...
    print("正在生成“规则大脑”分析报告...")
    report_parts = [f"# 基金量化规则分析报告 ({beijing_time.strftime('%Y-%m-%d')})\n", "本报告由预设量化规则生成，仅供参考。\n"]
    if not fund_datas:
        report_parts.append("### **注意：所有数据源均未能成功获取任何基金数据，无法生成分析。**\n请检查网络连接或稍后再试。")
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
    # ... (代码不变) ...
    try:
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt, request_options={'timeout': 180})
        return response.text
    except Exception as e:
        print(f"❌ 调用 Gemini AI 失败: {e}"); traceback.print_exc()
        return "AI模型调用失败，请检查API密钥或网络连接。"

def generate_ai_based_report(news, sectors, funds_string):
    # ... (代码不变) ...
    print("正在请求“AI策略大脑”生成分析报告...")
    if not funds_string.strip():
        return "由于所有数据源均未能获取任何基金的详细数据，AI策略大脑无法进行分析。"
    analysis_prompt = f"作为一名数据驱动的量化投资策略师...[省略详细指令]...\n**第一部分：宏观新闻**\n{news}\n**第二部分：板块轮动**\n{sectors}\n**第三部分：持仓基金详细数据**\n{funds_string}"
    draft_article = call_gemini_ai(analysis_prompt)
    if "AI模型调用失败" in draft_article: return draft_article
    polish_prompt = f"作为一名善于用数据说话的投资社区KOL...[省略详细指令]...\n**【原始报告】**\n{draft_article}"
    return call_gemini_ai(polish_prompt)
    
def main():
    if not check_time_interval(): return
    config = load_config()
    beijing_time = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    
    raw_fund_datas = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(config['fund_codes'])) as executor:
        future_to_code = {executor.submit(get_fund_raw_data_final_robust, code, config['historical_days_to_fetch']): code for code in config['fund_codes']}
        for future in concurrent.futures.as_completed(future_to_code):
            code, raw_data = future_to_code[future], future.result()
            if raw_data: raw_fund_datas[code] = raw_data

    structured_fund_datas, formatted_fund_strings = [], []
    for code, raw_data in raw_fund_datas.items():
        structured, formatted = process_fund_data(raw_data, code, config['moving_average_days'], config['historical_days_to_display'])
        if structured and formatted:
            structured_fund_datas.append(structured)
            formatted_fund_strings.append(formatted)

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
