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
    'Referer': 'http://fund.eastmoney.com/' # 增加Referer，更像真实浏览器
}
TIMESTAMP_FILE = "last_run_timestamp.txt"
MIN_INTERVAL_HOURS = 6
REQUESTS_TIMEOUT = 20

# --- 功能函数 ---

def load_config():
    """从config.json加载配置"""
    print("正在加载配置文件 config.json...")
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def check_time_interval():
    """检查突发事件触发间隔"""
    github_event_name = os.getenv('GITHUB_EVENT_NAME')
    if github_event_name != 'repository_dispatch':
        return True
    if not os.path.exists(TIMESTAMP_FILE):
        return True
    with open(TIMESTAMP_FILE, "r") as f:
        last_run_timestamp = float(f.read())
    current_timestamp = time.time()
    hours_diff = (current_timestamp - last_run_timestamp) / 3600
    if hours_diff < MIN_INTERVAL_HOURS:
        print(f"距离上次执行（{hours_diff:.2f}小时）未超过{MIN_INTERVAL_HOURS}小时，本次跳过。")
        return False
    return True

def update_timestamp():
    """更新时间戳文件"""
    with open(TIMESTAMP_FILE, "w") as f:
        f.write(str(time.time()))

def search_news(keyword):
    """搜索新闻"""
    print(f"正在搜索新闻: {keyword}...")
    try:
        with DDGS() as ddgs:
            results = [f"- [标题] {r['title']}\n  [摘要] {r.get('body', '无')}\n" for r in ddgs.news(keyword, region='cn-zh', safesearch='off', max_results=5)]
            return "\n".join(results)
    except Exception as e:
        return f"搜索关键词 '{keyword}' 失败: {e}"

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
        top_rising = sectors[:10]
        top_falling = sectors[-10:]
        
        rising_str = "\n".join([f"  - {s['name']}: {s['change']:.2f}%" for s in top_rising])
        falling_str = "\n".join([f"  - {s['name']}: {s['change']:.2f}%" for s in top_falling])
        return f"**【热门上涨板块】**\n{rising_str}\n\n**【热门下跌板块】**\n{falling_str}"
    except Exception as e:
        return f"行业板块数据爬取失败: {e}"

def get_fund_historical_data_and_ma(fund_code, history_days, ma_days):
    """获取基金历史净值并计算移动平均线"""
    print(f"正在获取基金 {fund_code} 的历史数据并计算MA{ma_days}...")
    try:
        url = f"http://api.fund.eastmoney.com/f10/lsjz?fundCode={fund_code}&pageIndex=1&pageSize={history_days}"
        response = requests.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT)
        data = response.json()['Data']['LSJZList']
        
        df = pd.DataFrame(data)
        df['FSRQ'] = pd.to_datetime(df['FSRQ'])
        df['DWJZ'] = pd.to_numeric(df['DWJZ'])
        df = df.sort_values('FSRQ')
        
        # 计算移动平均线
        df[f'MA{ma_days}'] = df['DWJZ'].rolling(window=ma_days).mean()
        
        latest_data = df.iloc[-1]
        fund_name = response.json()['Data']['FundBaseInfo']['JJJC']
        latest_price = latest_data['DWJZ']
        latest_ma = latest_data[f'MA{ma_days}']
        
        # 生成ASCII图表
        chart = generate_ascii_chart(latest_price, latest_ma, df['DWJZ'].min(), df['DWJZ'].max())
        
        return f"""
### 基金: {fund_name} ({fund_code})
- **最新净值**: {latest_price:.4f}
- **{ma_days}日均线**: {latest_ma:.4f}
- **趋势分析**: 当前价格在 {ma_days}日均线 **{'之上' if latest_price > latest_ma else '之下'}**，可能处于短期**{'上升' if latest_price > latest_ma else '下降'}**趋势。
- **价格位置图**:
{chart}
"""
    except Exception as e:
        return f"\n### 基金: {fund_code}\n- 历史数据和均线计算失败: {e}\n"

def generate_ascii_chart(price, ma, min_val, max_val, width=25):
    """生成一个简单的文本图表来显示价格和均线的位置"""
    if price is None or ma is None or pd.isna(ma):
        return "  (数据不足，无法生成图表)"
    
    val_range = max_val - min_val
    if val_range == 0: return "  (数据波动为0)"

    price_pos = int(((price - min_val) / val_range) * (width - 1))
    ma_pos = int(((ma - min_val) / val_range) * (width - 1))
    
    chart_list = ['-'] * width
    min_str = f"[{min_val:.3f}]"
    max_str = f"[{max_val:.3f}]"

    if price_pos == ma_pos:
        chart_list[price_pos] = 'P/M' # Price and MA are at the same spot
    else:
        chart_list[price_pos] = 'P' # Price
        chart_list[ma_pos] = 'M' # Moving Average
        
    return f"  {min_str} {''.join(chart_list)} {max_str}"

def call_gemini_ai(prompt):
    """调用Gemini AI"""
    print("正在调用 Gemini AI 进行深度分析...")
    try:
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI模型调用失败: {e}"

def main():
    if not check_time_interval():
        return
    
    config = load_config()
    
    print("开始执行增强版基金分析工作流...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        news_futures = {executor.submit(search_news, kw): kw for kw in config['news_keywords']}
        fund_futures = {executor.submit(get_fund_historical_data_and_ma, code, config['historical_days_to_fetch'], config['moving_average_days']): code for code in config['fund_codes']}
        sector_future = executor.submit(get_sector_data)

        all_news_text = "\n".join([f.result() for f in concurrent.futures.as_completed(news_futures)])
        all_fund_data = "\n".join([f.result() for f in concurrent.futures.as_completed(fund_futures)])
        sector_data_text = sector_future.result()

    # --- 打印汇总信息 ---
    print("\n" + "="*50 + "\n--- 数据汇总 ---\n" + "="*50)
    print(f"\n--- 宏观新闻 ---\n{all_news_text}")
    print(f"\n--- 行业板块 ---\n{sector_data_text}")
    print(f"\n--- 基金技术分析 ---\n{all_fund_data}")
    print("\n" + "="*50)

    # --- AI分析 ---
    analysis_prompt = f"""
作为一名拥有定量分析（Quant）和宏观经济分析双重背景的顶级投资组合经理，请根据以下三方面信息，撰写一份专业、深入且可执行的投资策略报告。

**第一部分：宏观新闻与市场情绪 (定性分析)**
{all_news_text}

**第二部分：市场结构与板块轮动 (中观分析)**
{sector_data_text}

**第三部分：核心持仓技术状态 (微观量化分析)**
{all_fund_data}

**【策略报告撰写指令】**
1.  **顶层判断 (Top-Down Analysis)**: 首先，结合【宏观新闻】和【板块数据】，判断当前市场的整体环境。是风险偏好提升的进攻期，还是风险厌恶主导的防守期？市场资金的主线在哪里？
2.  **量化验证 (Quantitative Check)**: 检视【核心持仓技术状态】。基金的短期趋势（价格与均线关系）是否与你的宏观判断相符？是否存在背离？（例如，宏观一片向好，但你的持仓却跌破了均线）。
3.  **具体策略制定 (Actionable Strategy)**:
    *   **进攻策略**: 如果判断市场向好，应优先加仓哪些“宏观顺风”且“技术形态良好”（价格在均线之上）的基金？
    *   **防守策略**: 如果判断市场有风险，应考虑减仓或卖出哪些“宏观逆风”或“技术形态走坏”（价格跌破均线）的基金？
    *   **观望策略**: 对于那些宏观和技术指标表现矛盾的基金，给出观望或轻仓操作的建议。
4.  **总结与风险**: 用简洁的语言总结核心操作建议，并明确指出该策略面临的最大风险是什么。
"""
    draft_article = call_gemini_ai(analysis_prompt)
    
    # --- AI润色 ---
    polish_prompt = f"""
作为一名顶级的投资社区意见领袖（KOL），请将以下这份硬核的专业投研报告，转化为一篇普通投资者都能看懂、且愿意看下去的精彩文章。

**【原始报告】**
{draft_article}

**【润色要求】**
1.  **标题**: 起一个“抓眼球”的标题，例如：“市场大变天！我的基金该跑还是该抄底？技术指标给出答案！”
2.  **开场**: 用一个热门事件或者生动的比喻开场，直接切入今天市场的核心矛盾。
3.  **“翻译”成人话**: 将“宏观”、“量化”、“技术形态”等专业术语，用大白话解释清楚。例如，把“价格在20日均线之上”解释为“它踩稳了短期生命线，势头不错”。
4.  **图文并茂**: 在文章中恰当使用 Emoji（例如 ✅, ❌, 📈, 📉, 🤔），增加阅读趣味。
5.  **结构清晰**: 使用清晰的小标题，如“今天市场发生了啥？”、“我的基金怎么样了？”、“所以，到底该咋办？”。
6.  **结尾**: 强势总结观点，并加上互动性的话语，最后附上免责声明。
"""
    final_article = call_gemini_ai(polish_prompt)

    # --- 保存文件 ---
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
