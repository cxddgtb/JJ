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
    with open('config.json', 'r', encoding='utf-8') as f: config = json.load(f)
    config.setdefault('historical_days_to_display', 7)
    return config

def check_time_interval():
    github_event_name = os.getenv('GITHUB_EVENT_NAME')
    if github_event_name != 'repository_dispatch': return True
    if not os.path.exists(TIMESTAMP_FILE): return True
    with open(TIMESTAMP_FILE, "r") as f: last_run_timestamp = float(f.read())
    hours_diff = (time.time() - last_run_timestamp) / 3600
    if hours_diff < MIN_INTERVAL_HOURS: return False
    return True

def update_timestamp():
    with open(TIMESTAMP_FILE, "w") as f: f.write(str(time.time()))

# --- 数据获取模块 (“三层情报网络”) ---

# --- 第一层：常规部队 (API) ---
def get_from_eastmoney_api(fund_code, history_days):
    url = f"http://api.fund.eastmoney.com/f10/lsjz?fundCode={fund_code}&pageIndex=1&pageSize={history_days}"
    response = requests.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT)
    response.raise_for_status()
    data = response.json().get('Data')
    if not data or not data.get('LSJZList'): raise ValueError("API数据无效")
    return data

# --- 第二层：特种部队 (浏览器模拟) ---
def get_from_sina_web(fund_code, history_days):
    options = webdriver.ChromeOptions(); options.add_argument("--headless"); options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage"); options.add_argument("user-agent=" + HEADERS['User-Agent'])
    service = Service(ChromeDriverManager().install()); driver = webdriver.Chrome(service=service, options=options)
    try:
        url = f"http://money.finance.sina.com.cn/fund/hgsz/{fund_code}.html"
        driver.get(url)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "fund_history_table")))
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        rows = soup.find('table', id='fund_history_table').find('tbody').find_all('tr')
        lsjz_list = [{'FSRQ': c[0].text, 'DWJZ': c[1].text, 'JZZZL': c[3].text.replace('%','')} for r in rows[:history_days] if len(c:=r.find_all('td'))>3]
        fund_name = soup.find('h1', id='fund_name').text.split('(')[0].strip()
        lsjz_list.reverse()
        return {'FundBaseInfo': {'JJJC': fund_name}, 'LSJZList': lsjz_list}
    finally: driver.quit()

# --- 第三层：终极情报员 (搜索引擎) ---
def get_from_search_engine(fund_code):
    query = f"{fund_code} 基金净值"
    with DDGS() as ddgs:
        results = list(ddgs.text(query, region='cn-zh', max_results=3))
        if not results: raise ValueError("搜索引擎未返回结果")
        # 尝试从搜索结果摘要中用正则表达式解析
        for result in results:
            snippet = result.get('body', '')
            # 匹配 "净值" "日期" "涨幅" 等关键词
            match = re.search(r'(\d{4}-\d{2}-\d{2}).*?单位净值.*?(\d+\.\d+).*?日增长率.*?(-?\d+\.\d+)%', snippet)
            if match:
                fsrq, dwjz, jzzzl = match.groups()
                # 搜索引擎只能获取最新一天的数据
                return {'FundBaseInfo': {'JJJC': result.get('title', fund_code)}, 'LSJZList': [{'FSRQ': fsrq, 'DWJZ': dwjz, 'JZZZL': jzzzl}]}
    raise ValueError("无法从搜索结果中解析净值")

# --- “情报汇总官” ---
def get_fund_raw_data_final_robust(fund_code, history_days):
    print(f"\n开始对基金 {fund_code} 进行三层情报网络并行获取...")
    # 定义所有情报员和他们的任务
    sources = {
        "SINA_WEB": (get_from_sina_web, [fund_code, history_days]),
        "EASTMONEY_API": (get_from_eastmoney_api, [fund_code, history_days]),
        "SEARCH_ENGINE": (get_from_search_engine, [fund_code])
    }
    
    successful_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(sources)) as executor:
        future_to_source = {executor.submit(func, *args): name for name, (func, args) in sources.items()}
        for future in concurrent.futures.as_completed(future_to_source):
            source_name = future_to_source[future]
            try:
                data = future.result()
                if data and data.get('LSJZList'):
                    latest_date = data['LSJZList'][-1].get('FSRQ', '0000-00-00')
                    successful_results.append({'source': source_name, 'date': latest_date, 'data': data})
                    print(f"    ✅ {source_name}: 获取成功, 最新日期: {latest_date}")
            except Exception as e:
                print(f"    ❌ {source_name}: 获取失败: {e}")

    if not successful_results:
        print(f"所有情报来源均未能获取 {fund_code} 的数据。")
        return None

    # 情报融合：选择最新日期的数据，并进行融合
    latest_date = max(r['date'] for r in successful_results)
    best_sources = [r for r in successful_results if r['date'] == latest_date]
    print(f"  📊 找到最新数据日期为 {latest_date} 的来源: {[r['source'] for r in best_sources]}")
    
    # 数据融合：如果多个来源都有最新数据，取平均值
    final_data = best_sources[0]['data'] # 以第一个为基础
    if len(best_sources) > 1:
        latest_net_values = [float(r['data']['LSJZList'][-1]['DWJZ']) for r in best_sources]
        avg_net_value = np.mean(latest_net_values)
        final_data['LSJZList'][-1]['DWJZ'] = str(avg_net_value)
        print(f"  🏆 数据融合完成，采用平均净值: {avg_net_value:.4f}")

    return final_data
    
# --- 其他所有函数 (process_fund_data, report generation, etc.) ---
# 这一部分和上上版完全一样，只需确保 search_news 的引用已更新
def search_news(keyword):
    print(f"正在搜索新闻: {keyword}...")
    try:
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
