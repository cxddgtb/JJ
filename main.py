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
from duckduckgo_search import DDGS

# --- 全局配置 ---
HEADERS_EASTMONEY = {'Referer': 'http://fund.eastmoney.com/', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}
HEADERS_SINA = {'Referer': 'http://finance.sina.com.cn/', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}
HEADERS_TENCENT = {'Referer': 'https://fund.qq.com/', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'}
TIMESTAMP_FILE, MIN_INTERVAL_HOURS, REQUESTS_TIMEOUT = "last_run_timestamp.txt", 6, 25

# --- 基础辅助函数 ---
def load_config():
    print("正在加载配置文件 config.json...")
    with open('config.json', 'r', encoding='utf-8') as f: config = json.load(f)
    config.setdefault('historical_days_to_display', 7)
    return config

def check_time_interval():
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
    
# --- 数据获取模块 (已修复) ---

def get_fund_raw_data_from_tencent(fund_code, history_days):
    print(f"    TENCENT: 正在尝试获取 {fund_code}...")
    url = f"https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newkline/newkline?_var=kline_dayq&param={fund_code},day,,,{history_days},qfq"
    response = requests.get(url, headers=HEADERS_TENCENT, timeout=REQUESTS_TIMEOUT)
    response.raise_for_status()
    json_str = re.search(r'\{.*\}', response.text).group(0)
    data = json.loads(json_str)
    
    # 修复：更安全地访问数据
    fund_data_root = data.get('data', {})
    if not fund_data_root or fund_code not in fund_data_root:
        raise ValueError("Tencent API返回数据中不包含该基金代码")
        
    fund_data = fund_data_root[fund_code]
    fund_name = fund_data.get('name', fund_code)
    history_list = fund_data.get('qfqday', fund_data.get('day', []))
    
    lsjz_list = []
    for i in range(len(history_list)):
        current_day, net_value = history_list[i], float(history_list[i][2])
        growth = 0.0
        if i > 0 and (prev_val := float(history_list[i-1][2])) > 0:
            growth = (net_value / prev_val - 1) * 100
        lsjz_list.append({'FSRQ': current_day[0], 'DWJZ': str(net_value), 'JZZZL': str(growth)})

    return {'FundBaseInfo': {'JJJC': fund_name}, 'LSJZList': lsjz_list}

def get_fund_raw_data_from_sina(fund_code, history_days):
    print(f"    SINA: 正在尝试获取 {fund_code}...")
    url = f"http://stock.finance.sina.com.cn/fundInfo/api/openapi.php/CaihuiFundInfoService.getNav?symbol={fund_code}&page=1&num={history_days}"
    response = requests.get(url, headers=HEADERS_SINA, timeout=REQUESTS_TIMEOUT)
    response.raise_for_status()
    data = response.json()['result']['data']
    fund_name = data.get('fund_name', fund_code)
    # 修复：安全地获取增长率字段
    lsjz_list = [{'FSRQ': item['fbrq'], 'DWJZ': item['jjjz'], 'JZZZL': item.get('jzzzl', '0')} for item in data['data']]
    return {'FundBaseInfo': {'JJJC': fund_name}, 'LSJZList': lsjz_list}

def get_fund_raw_data_from_eastmoney(fund_code, history_days):
    print(f"    EASTMONEY: 正在尝试获取 {fund_code}...")
    url = f"http://api.fund.eastmoney.com/f10/lsjz?fundCode={fund_code}&pageIndex=1&pageSize={history_days}"
    response = requests.get(url, headers=HEADERS_EASTMONEY, timeout=REQUESTS_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if not data.get('Data') or not data['Data'].get('LSJZList'):
        raise ValueError("天天基金API返回数据格式无效或为空")
    return data['Data']

def get_fund_raw_data_final_robust(fund_code, history_days):
    print(f"\n开始并行获取基金 {fund_code} 的数据...")
    sources = {"EastMoney": get_fund_raw_data_from_eastmoney, "Sina": get_fund_raw_data_from_sina, "Tencent": get_fund_raw_data_from_tencent}
    successful_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(sources)) as executor:
        future_to_source = {executor.submit(func, fund_code, history_days): name for name, func in sources.items()}
        for future in concurrent.futures.as_completed(future_to_source):
            source_name = future_to_source[future]
            try:
                data = future.result()
                if data and data.get('LSJZList'):
                    # 修复：更安全地获取最新日期
                    latest_date = data['LSJZList'][-1].get('FSRQ', '0000-00-00')
                    successful_results.append({'source': source_name, 'date': latest_date, 'data': data})
                    print(f"    ✅ {source_name}: 获取成功, 最新数据日期: {latest_date}")
            except Exception as e:
                print(f"    ❌ {source_name}: 获取失败: {e}")

    if not successful_results:
        print(f"所有数据源均未能获取 {fund_code} 的数据。")
        return None

    best_result = sorted(successful_results, key=lambda x: x['date'], reverse=True)[0]
    print(f"  🏆 为基金 {fund_code} 选择的最佳数据源是: {best_result['source']} (最新日期: {best_result['date']})")
    return best_result['data']

# --- 数据处理与报告生成 (已修复与恢复) ---
def process_fund_data(raw_data, fund_code, ma_days, days_to_display):
    try:
        print(f"正在处理基金 {fund_code} 的数据...")
        # 修复：使用.get()安全地访问字典
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

# ⬇️⬇️⬇️ 恢复：被遗忘的函数都在这里 ⬇️⬇️⬇️
def search_news(keyword):
    print(f"正在搜索新闻: {keyword}...")
    try:
        with DDGS() as ddgs:
            return "\n".join([f"- [标题] {r['title']}\n  [摘要] {r.get('body', '无')}\n" for r in ddgs.news(keyword, region='cn-zh', safesearch='off', max_results=5)])
    except Exception as e: return f"搜索关键词 '{keyword}' 失败: {e}"

def get_sector_data():
    print("正在爬取行业板块数据...")
    try:
        response = requests.get("http://quote.eastmoney.com/center/boardlist.html#industry_board", headers=HEADERS_EASTMONEY, timeout=REQUESTS_TIMEOUT)
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
    
# --- 主流程 ---
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

    # 现在可以安全地调用这些函数了
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
