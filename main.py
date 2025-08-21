import os
import datetime
import time
import json
import concurrent.futures
import google.generativeai as genai
import requests
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

# --- 全局设置 ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'http://fund.eastmoney.com/'
}
TIMESTAMP_FILE = "last_run_timestamp.txt"
MIN_INTERVAL_HOURS = 6
REQUESTS_TIMEOUT = 20

# --- 功能函数 ---

def load_config():
    """从config.json加载配置"""
    print("正在加载配置文件 config.json...")
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    # 为配置文件增加默认值，防止用户忘记填写
    config.setdefault('historical_days_to_display', 7)
    return config

def check_time_interval():
    """检查突发事件触发间隔"""
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
    """更新时间戳文件"""
    with open(TIMESTAMP_FILE, "w") as f: f.write(str(time.time()))

def search_news(keyword):
    """搜索新闻"""
    print(f"正在搜索新闻: {keyword}...")
    try:
        with DDGS() as ddgs:
            results = [f"- [标题] {r['title']}\n  [摘要] {r.get('body', '无')}\n" for r in ddgs.news(keyword, region='cn-zh', safesearch='off', max_results=5)]
            return "\n".join(results)
    except Exception as e: return f"搜索关键词 '{keyword}' 失败: {e}"

def get_sector_data():
    """爬取行业板块数据"""
    print("正在爬取行业板块数据...")
    url = "http://quote.eastmoney.com/center/boardlist.html#industry_board"
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT)
        soup = BeautifulSoup(response.text, 'html.parser')
        sectors = []
        for row in soup.select('table#table_wrapper-table tbody tr'):
            cols = row.find_all('td')
            if len(cols) > 5:
                try:
                    name = cols[1].find('a').text.strip()
                    change = float(cols[4].text.strip().replace('%', ''))
                    sectors.append({'name': name, 'change': change})
                except (ValueError, AttributeError): continue
        
        sectors.sort(key=lambda x: x['change'], reverse=True)
        top_rising = sectors[:10]; top_falling = sectors[-10:]
        rising_str = "\n".join([f"  - {s['name']}: {s['change']:.2f}%" for s in top_rising])
        falling_str = "\n".join([f"  - {s['name']}: {s['change']:.2f}%" for s in top_falling])
        return f"**【热门上涨板块】**\n{rising_str}\n\n**【热门下跌板块】**\n{falling_str}"
    except Exception as e: return f"行业板块数据爬取失败: {e}"

def get_fund_data_with_details(fund_code, history_days, ma_days, days_to_display):
    """获取基金详细数据，包括历史数据表和技术分析"""
    print(f"正在获取基金 {fund_code} 的详细数据...")
    try:
        url = f"http://api.fund.eastmoney.com/f10/lsjz?fundCode={fund_code}&pageIndex=1&pageSize={history_days}"
        response = requests.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT).json()
        
        fund_name = response['Data']['FundBaseInfo']['JJJC']
        data = response['Data']['LSJZList']
        
        df = pd.DataFrame(data)
        df['FSRQ'] = pd.to_datetime(df['FSRQ'])
        df['DWJZ'] = pd.to_numeric(df['DWJZ'])
        df = df.sort_values('FSRQ')
        
        df[f'MA{ma_days}'] = df['DWJZ'].rolling(window=ma_days).mean()
        
        latest_data = df.iloc[-1]
        latest_price = latest_data['DWJZ']
        latest_ma = latest_data[f'MA{ma_days}']
        
        recent_df = df.tail(days_to_display).sort_values('FSRQ', ascending=False)
        table_header = f"| 日期       | 单位净值 | {ma_days}日均线 | 趋势 |"
        table_divider = "|:-----------|:---------|:------------|:-----|"
        table_rows = []
        for _, row in recent_df.iterrows():
            ma_val = row[f'MA{ma_days}']
            ma_str = f"{ma_val:.4f}" if not pd.isna(ma_val) else "N/A"
            trend_emoji = "📈" if row['DWJZ'] > ma_val else "📉" if not pd.isna(ma_val) else "🤔"
            table_rows.append(f"| {row['FSRQ'].strftime('%Y-%m-%d')} | {row['DWJZ']:.4f}   | {ma_str}    | {trend_emoji}  |")
        historical_table = "\n".join([table_header, table_divider] + table_rows)
        
        return f"""
### 基金: {fund_name} ({fund_code})
- **最新净值**: {latest_price:.4f} (日期: {latest_data['FSRQ'].strftime('%Y-%m-%d')})
- **{ma_days}日均线**: {latest_ma:.4f if not pd.isna(latest_ma) else '数据不足'}
- **技术分析**: 当前净值在 {ma_days}日均线**{'之上' if latest_price > latest_ma else '之下'}**，表明短期趋势可能**{'偏强' if latest_price > latest_ma else '偏弱'}**。
- **最近 {days_to_display} 日详细数据**:
{historical_table}
"""
    except Exception as e:
        return f"\n### 基金: {fund_code}\n- 详细数据获取失败: {e}\n"

def call_gemini_ai(prompt):
    """调用Gemini AI"""
    print("正在调用 Gemini AI 进行深度分析...")
    try:
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e: return f"AI模型调用失败: {e}"

def main():
    if not check_time_interval(): return
    config = load_config()
    
    print("开始执行“数据驱动版”基金分析工作流...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        news_futures = {executor.submit(search_news, kw): kw for kw in config['news_keywords']}
        fund_futures = {executor.submit(get_fund_data_with_details, code, config['historical_days_to_fetch'], config['moving_average_days'], config['historical_days_to_display']): code for code in config['fund_codes']}
        sector_future = executor.submit(get_sector_data)

        all_news_text = "\n".join([f.result() for f in concurrent.futures.as_completed(news_futures)])
        all_fund_data = "\n".join([f.result() for f in concurrent.futures.as_completed(fund_futures)])
        sector_data_text = sector_future.result()

    print("\n" + "="*50 + "\n--- 原始数据汇总 ---\n" + "="*50)
    print(f"\n--- 宏观新闻 ---\n{all_news_text}")
    print(f"\n--- 行业板块 ---\n{sector_data_text}")
    print(f"\n--- 基金详细数据与分析 ---\n{all_fund_data}")
    print("\n" + "="*50)

    analysis_prompt = f"""
作为一名数据驱动的量化投资策略师，请严格根据以下三方面信息，撰写一份逻辑严密、有数据支撑的投资策略报告。

**第一部分：宏观新闻 (市场情绪)**
{all_news_text}

**第二部分：板块轮动 (市场结构)**
{sector_data_text}

**第三部分：持仓基金的详细数据 (量化事实)**
{all_fund_data}

**【策略报告撰写指令】**
1.  **市场定调**: 结合【宏观新闻】和【板块数据】，对当前市场环境（进攻/防守）和主线热点做出判断。
2.  **数据解读**: 逐一分析【持仓基金】。**你的分析必须基于“最近几日详细数据”表格**。
    *   明确指出净值的**连续变化趋势**。例如：“从数据表可以看出，该基金净值已连续三日下跌，从X日的A元跌至Y日的B元。”
    *   将净值与均线进行**动态比较**。例如：“在Z日，该基金净值跌破了20日均线，这是一个明确的短期走弱信号。”
3.  **策略制定 (必须引用数据)**:
    *   **加仓建议**: 必须说明理由，例如：“建议加仓XX基金，因为其重仓的YY板块处于上涨趋势，并且其净值已连续N日站在均线上方，表现强势。”
    *   **减仓建议**: 必须说明理由，例如：“建议减仓XX基金，数据显示其净值在[日期]已跌破关键均线，且至今未能收复，下行风险较大。”
4.  **总结与风险**: 总结核心操作，并提示风险。
"""
    draft_article = call_gemini_ai(analysis_prompt)
    
    polish_prompt = f"""
作为一名善于用数据说话的投资社区KOL，请将以下这份专业的投研报告，转化为一篇对普通投资者极具吸引力和说服力的文章。

**【原始报告】**
{draft_article}

**【润色要求】**
1.  **标题**: 要有冲击力，突出“数据”和“真相”，例如：“别光听消息！真金白银的数据告诉你，基金是该走是该留？”
2.  **核心亮点**: 在文章开头，就告诉读者，本文最大的不同是“用数据说话”，会展示每支基金最近一周的“成绩单”。
3.  **数据表格可视化**: 将报告中的数据表格美化。在表格上方加上类似“话不多说，直接上数据”的引导语，让表格成为文章的核心证据。
4.  **解读要通俗**: 把“跌破均线”解释为“短期势头不对，要小心了”，把“站上均线”解释为“状态回暖，可以多看两眼”。
5.  **结论要清晰**: 在文章结尾，用1、2、3点清晰地列出操作建议总结。
6.  **结尾**: 强势总结观点，并附上免责声明。
"""
    final_article = call_gemini_ai(polish_prompt)

    print("\n--- 最终生成的社区文章 ---")
    print(final_article)
    if not os.path.exists('reports'): os.makedirs('reports')
    beijing_time = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    file_name = f"reports/基金分析报告_{beijing_time.strftime('%Y-%m-%d_%H-%M')}.md"
    with open(file_name, 'w', encoding='utf-8') as f: f.write(final_article)
    print(f"\n报告已成功保存为: {file_name}")
    
    update_timestamp()

if __name__ == "__main__":
    main()
