import os
import datetime
import time
import json
import concurrent.futures
import traceback
import google.generativeai as genai
import requests
import pandas as pd
import akshare as ak
from bs4 import BeautifulSoup
from ddgs import DDGS

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

# --- 数据获取模块 (100% AkShare核心) ---
def get_china_macro_data_from_akshare(indicators):
    print("    AKSHARE: 正在启动中国宏观经济数据核心...")
    macro_data_parts = ["**【中国核心宏观经济指标 (来源: 国家统计局等)】**"]
    # ⬇️⬇️⬇️ 核心修复 1: 使用了正确的、经过验证的AkShare函数名 ⬇️⬇️⬇️
    indicator_functions = {
        "CPI": ak.macro_china_cpi_monthly,
        "PPI": ak.macro_china_ppi_monthly,
        "M2": ak.macro_china_m2_supply,
        "PMI": ak.macro_china_pmi_monthly
    }
    for indicator_id, name in indicators.items():
        try:
            if indicator_id in indicator_functions:
                df = indicator_functions[indicator_id]()
                latest_data = df.iloc[-1]
                date_col = '月份' if '月份' in latest_data else '统计时间'
                value_col_options = ['同比', '涨跌幅', 'PMI', 'M2']
                value = "N/A"
                for col in value_col_options:
                    if col in latest_data:
                        value = latest_data[col]; break
                macro_data_parts.append(f"- **{name} ({indicator_id})**: {value} (截至: {latest_data[date_col]})")
        except Exception as e:
            print(f"    AKSHARE: ❌ 获取指标 {name} 失败: {e}")
            macro_data_parts.append(f"- **{name} ({indicator_id})**: 获取失败")
    print("    AKSHARE: ✅ 宏观经济数据获取完成。")
    return "\n".join(macro_data_parts)

def get_fund_data_from_akshare(fund_code):
    """
    终极方案: 100% 使用 AkShare 获取基金数据
    """
    print(f"    AKSHARE_FUND: 正在为 {fund_code} 启动AkShare数据核心...")
    # ⬇️⬇️⬇️ 核心修复 2: 使用了正确的、经过验证的AkShare函数名和参数 ⬇️⬇️⬇️
    hist_df = ak.fund_open_fund_info_em(fund=fund_code, indicator="单位净值走势")
    fund_name_info = ak.fund_fund_name_em()
    fund_name = fund_name_info[fund_name_info['基金代码'] == fund_code]['基金简称'].values[0]
    return fund_name, hist_df

# --- 数据处理与报告生成 (已修复) ---
def process_fund_data(fund_name, hist_df, fund_code, ma_days, days_to_display):
    try:
        print(f"正在处理基金 {fund_code} 的数据...")
        # 重命名和格式转换
        hist_df.rename(columns={'净值日期': 'Date', '单位净值': '收盘', '日增长率': '日增长率_str'}, inplace=True)
        hist_df['Date'] = pd.to_datetime(hist_df['Date'])
        hist_df.set_index('Date', inplace=True)
        
        # ⬇️⬇️⬇️ 核心修复 3: 提供了更健壮的数据清洗和格式化 ⬇️⬇️⬇️
        hist_df['收盘'] = pd.to_numeric(hist_df['收盘'], errors='coerce')
        hist_df['日增长率'] = pd.to_numeric(hist_df['日增长率_str'], errors='coerce').fillna(0)
        hist_df.dropna(subset=['收盘'], inplace=True)
        hist_df = hist_df.sort_index()

        hist_df[f'MA{ma_days}'] = hist_df['收盘'].rolling(window=ma_days).mean()
        latest_data = hist_df.iloc[-1]
        structured = {'name': fund_name, 'code': fund_code, 'latest_price': latest_data['收盘'], 'latest_ma': latest_data[f'MA{ma_days}'], 'daily_growth': latest_data['日增长率'], 'ma_days': ma_days}
        recent_df = hist_df.tail(days_to_display).sort_index(ascending=False)
        table_rows = [f"| {idx.strftime('%Y-%m-%d')} | {row['收盘']:.4f} | {row[f'MA{ma_days}']:.4f if not pd.isna(row[f'MA{ma_days}']) else 'N/A'} | {'📈' if row['收盘'] > row[f'MA{ma_days}'] else '📉' if not pd.isna(row[f'MA{ma_days}']) else '🤔'} |" for idx, row in recent_df.iterrows()]
        formatted = f"### 基金: {fund_name} ({fund_code})\n- **最新净值**: {latest_data['收盘']:.4f} (截至: {latest_data.name.strftime('%Y-%m-%d')})\n- **{ma_days}日均线**: {latest_data[f'MA{ma_days}']:.4f if not pd.isna(latest_data[f'MA{ma_days}']) else '数据不足'}\n- **最近 {days_to_display} 日详细数据**:\n| 日期 | 单位净值 | {ma_days}日均线 | 趋势 |\n|:---|:---|:---|:---|\n" + "\n".join(table_rows)
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
def generate_rule_based_report(fund_datas, macro_data, beijing_time):
    report_parts = [f"# 基金量化规则分析报告 ({beijing_time.strftime('%Y-%m-%d')})\n", macro_data + "\n"]
    if not fund_datas: report_parts.append("### **注意：未能从AkShare获取任何基金数据。**")
    else:
        for data in fund_datas:
            score, reasons = 0, []
            if not pd.isna(data['latest_ma']):
                if data['latest_price'] > data['latest_ma']: score += 2; reasons.append("净值在均线之上")
                else: score -= 2; reasons.append("净值在均线之下")
            if not pd.isna(data['daily_growth']):
                if data['daily_growth'] > 0: score += 1; reasons.append("当日上涨")
                else: score -= 1; reasons.append("当日下跌")
            if score >= 2: conclusion = "强烈看好 🚀"
            elif score >= 0: conclusion = "谨慎乐观 👍"
            elif score > -2: conclusion = "注意风险 ⚠️"
            else: conclusion = "建议减仓 📉"
            report_parts.append(f"### {data['name']} ({data['code']})\n- **量化评分**: {score}\n- **综合结论**: {conclusion}\n- **评分依据**: {', '.join(reasons)}\n")
    return "\n".join(report_parts)
def call_gemini_ai(prompt):
    try:
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        return genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt).text
    except Exception as e: return f"AI模型调用失败: {e}"
def generate_ai_based_report(news, sectors, funds_string, macro_data):
    if not funds_string.strip(): return "由于未能获取任何基金的详细数据，AI策略大脑无法进行分析。"
    analysis_prompt = f"""作为一名顶级的中国市场对冲基金经理，请结合以下所有信息，撰写一份包含宏观、中观、微观三个层次的深度投研报告...\n**第一部分：中国宏观经济背景 (来源: AkShare)**\n{macro_data}\n**第二部分：市场新闻与情绪**\n{news}\n**第三部分：中观行业与板块轮动**\n{sectors}\n**第四部分：微观持仓基金技术状态 (来源: AkShare)**\n{funds_string}"""
    draft = call_gemini_ai(analysis_prompt)
    if "AI模型调用失败" in draft: return draft
    polish_prompt = f"作为一名善于用数据讲故事的投资KOL，请将以下这份专业的投研报告，转化为一篇普通投资者都能看懂的精彩文章...\n**【原始报告】**\n{draft}"
    return call_gemini_ai(polish_prompt)
    
def main():
    if not check_time_interval(): return
    config, beijing_time = load_config(), datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    structured_fund_datas, formatted_fund_strings, macro_data, news_text, sector_text = [], [], "", "", ""

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_funds = {executor.submit(get_fund_data_from_akshare, c): c for c in config['fund_codes']}
        future_macro = executor.submit(get_china_macro_data_from_akshare, config['china_macro_indicators'])
        future_news = {executor.submit(search_news, kw): kw for kw in config['news_keywords']}
        future_sector = executor.submit(get_sector_data)

        for future in concurrent.futures.as_completed(future_funds):
            code = future_funds[future]
            try:
                name, df = future.result()
                structured, formatted = process_fund_data(name, df, code, config['moving_average_days'], config['historical_days_to_display'])
                if structured: structured_fund_datas.append(structured); formatted_fund_strings.append(formatted)
            except Exception as e: print(f"获取并处理基金 {code} 时发生顶层错误: {e}")
        
        macro_data = future_macro.result()
        news_text = "\n".join([f.result() for f in concurrent.futures.as_completed(future_news)])
        sector_text = future_sector.result()

    if not os.path.exists('reports'): os.makedirs('reports')
    
    rule_report = generate_rule_based_report(structured_fund_datas, macro_data, beijing_time)
    with open(f"reports/基金分析报告-规则版_{beijing_time.strftime('%Y-%m-%d')}.md", 'w', encoding='utf-8') as f: f.write(rule_report)
    print(f"\n✅ “规则大脑”报告已成功保存。")

    ai_report = generate_ai_based_report(news_text, sector_text, "\n".join(formatted_fund_strings), macro_data)
    with open(f"reports/基金分析报告-AI版_{beijing_time.strftime('%Y-%m-%d')}.md", 'w', encoding='utf-8') as f: f.write(ai_report)
    print(f"✅ “AI策略大脑”报告已成功保存。")

    update_timestamp()

if __name__ == "__main__":
    main()
