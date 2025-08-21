import os
import datetime
import time
import concurrent.futures
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

# --- 用户配置区 ---
# 请在这里输入您关心的基金代码列表
FUND_CODES = ["001186", "161725", "005827"] 
# 新闻搜索的关键词
NEWS_KEYWORDS = ["中国股市", "A股", "美联储利率", "重要经济会议"]
# --- 配置区结束 ---

# --- 全局设置 ---
# 突发事件触发的最小时间间隔（小时）
MIN_INTERVAL_HOURS = 6
TIMESTAMP_FILE = "last_run_timestamp.txt"
MAX_NEWS_RESULTS = 5 # 每个关键词搜索的新闻数量
REQUESTS_TIMEOUT = 15 # 请求超时时间（秒）
SECTOR_COUNT = 10 # 抓取涨跌幅前10的板块
# 模拟浏览器请求头，防止被网站屏蔽
HEADERS = {
    'User-Agent': 'Mozilla.5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def check_time_interval():
    """检查距离上次突发事件执行是否超过指定间隔"""
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
    """使用DuckDuckGo搜索新闻"""
    print(f"正在搜索新闻关键词: {keyword}...")
    results = []
    try:
        with DDGS() as ddgs:
            ddgs_results = ddgs.news(keyword, region='cn-zh', safesearch='off', max_results=MAX_NEWS_RESULTS)
            if ddgs_results:
                for r in ddgs_results:
                    results.append(f"- [标题] {r['title']}\n  [链接] {r['url']}\n  [摘要] {r.get('body', '无')}\n")
    except Exception as e:
        print(f"搜索关键词 '{keyword}' 失败: {e}")
    return "\n".join(results)

def get_fund_data(fund_code):
    """爬取单支基金的数据"""
    print(f"正在爬取基金数据: {fund_code}...")
    url = f"http://fund.eastmoney.com/{fund_code}.html"
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        fund_name = soup.select_one('div.fundDetail-tit > div').get_text(strip=True).replace('(前端)', '')
        data_item = soup.select_one('dl.dataItem02')
        net_value = data_item.select_one('dd.dataNums > span.ui-font-large').text
        daily_growth = data_item.select_one('dd.dataNums > span:nth-of-type(2)').text
        data_info = soup.select_one('div.dataOfFund')
        fund_scale = data_info.select_one('td:nth-of-type(2)').text.split('：')[-1].strip()
        return f"""
### 基金: {fund_name} ({fund_code})
- **最新净值**: {net_value}
- **日增长率**: {daily_growth}
- **基金规模**: {fund_scale}
"""
    except Exception as e:
        print(f"爬取基金 {fund_code} 数据失败: {e}")
        return f"\n### 基金: {fund_code}\n- 数据爬取失败。\n"

def get_sector_data():
    """爬取行业板块数据，包括涨幅前10和跌幅前10"""
    print("正在爬取行业板块数据...")
    url = "http://quote.eastmoney.com/center/boardlist.html#industry_board"
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        table = soup.find('table', {'id': 'table_wrapper-table'})
        if not table:
            return "未能找到板块数据表格，网站结构可能已更新。"
        
        rows = table.select('tbody tr')
        
        sectors = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 5:
                try:
                    name = cols[1].find('a').text.strip()
                    change = float(cols[4].text.strip().replace('%', ''))
                    leading_stock = cols[8].find('a').text.strip()
                    sectors.append({'name': name, 'change': change, 'stock': leading_stock})
                except (ValueError, AttributeError):
                    continue

        # 按涨跌幅排序
        sectors.sort(key=lambda x: x['change'], reverse=True)
        
        # 提取涨幅前10和跌幅前10
        top_rising = sectors[:SECTOR_COUNT]
        top_falling = sectors[-SECTOR_COUNT:]
        top_falling.reverse() # 让跌幅最大的在最前面

        result = ["**【今日热门上涨板块】**"]
        for i, s in enumerate(top_rising):
            result.append(f"{i+1}. **{s['name']}**: {s['change']:.2f}% (领涨股: {s['stock']})")
        
        result.append("\n**【今日热门下跌板块】**")
        for i, s in enumerate(top_falling):
            result.append(f"{i+1}. **{s['name']}**: {s['change']:.2f}% (领跌股: {s['stock']})")
            
        return "\n".join(result)

    except Exception as e:
        print(f"爬取行业板块数据失败: {e}")
        return "行业板块数据爬取失败，请检查网站结构或网络连接。"

def call_gemini_ai(prompt, model_name="gemini-1.5-flash"):
    """调用Gemini AI"""
    print(f"正在调用 Gemini AI ({model_name})...")
    try:
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"调用 Gemini AI 失败: {e}")
        return "AI模型调用失败，无法生成内容。"

def main():
    """主函数"""
    if not check_time_interval():
        return
        
    print("开始执行基金分析工作流...")
    
    all_news_text = ""
    all_fund_data = ""
    sector_data_text = ""

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        news_futures = {executor.submit(search_news, kw): kw for kw in NEWS_KEYWORDS}
        fund_futures = {executor.submit(get_fund_data, code): code for code in FUND_CODES}
        sector_future = executor.submit(get_sector_data)
        
        # 收集结果
        all_news_text = "\n".join([f.result() for f in concurrent.futures.as_completed(news_futures)])
        all_fund_data = "\n".join([f.result() for f in concurrent.futures.as_completed(fund_futures)])
        sector_data_text = sector_future.result()

    print("\n--- 新闻数据汇总 ---")
    print(all_news_text)
    print("\n--- 基金数据汇总 ---")
    print(all_fund_data)
    print("\n--- 行业板块数据 ---")
    print(sector_data_text)
    
    # --- 第一步：AI分析并生成初稿 ---
    analysis_prompt = f"""
作为一名顶级的基金投资策略师，请根据以下所有信息，为我撰写一份深入的投资操作分析报告。

**【宏观市场新闻摘要】**
{all_news_text}

**【今日行业板块数据概览】**
{sector_data_text}

**【我关注的基金核心数据】**
{all_fund_data}

**【报告撰写要求】**
1.  **市场大势研判**: 结合【宏观新闻】和【行业板块数据】，分析当前市场的整体情绪（乐观/悲观/中性）和主要特征（例如，是普涨普跌，还是结构性行情）。
2.  **板块轮动分析**: 根据板块的涨跌情况，分析当前市场的热点在哪里，资金可能正在从哪些板块流出，又流向了哪些板块。
3.  **持仓基金诊断**: 逐一分析我关注的每一支基金。请务必将基金的表现与【行业板块数据】关联起来。例如，如果基金重仓了某个热门板块，要指出其受益情况；如果重仓了下跌板块，要分析其受挫原因。
4.  **综合操作建议**: 基于以上所有信息的综合分析，给出明确、可执行的总体操作建议（例如：建议加仓XX基金，减仓YY基金，或整体持仓观望）。操作理由必须充分，要同时引用新闻、板块和基金数据作为论据。
5.  **风险揭示**: 明确指出当前市场和操作建议中潜在的主要风险点。
6.  要求逻辑严密，分析深入，语言专业。
"""
    
    draft_article = call_gemini_ai(analysis_prompt)
    print("\n--- AI 生成的分析报告初稿 ---")
    print(draft_article)
    
    # --- 第二步：AI润色文章，用于社区发表 ---
    polish_prompt = f"""
作为一名资深的投资社区内容创作者，请将以下这份专业的分析报告润色成一篇适合在网络社区（如雪球、知乎）发表的文章。

**【原始报告】**
{draft_article}

**【润色要求】**
1.  **标题**: 起一个吸引人但不过于夸张的标题，最好能体现出市场的核心动态。
2.  **引言**: 写一段引人入胜的开场白，用通俗的话概括一下今天的市场（比如“今天又是喝酒吃药行情”，或者“科技股上演大撤退”），并点出本文的看点。
3.  **正文**: 保持原文的核心逻辑和数据不变。将专业的术语转化为普通投资者能懂的大白话。可以适当使用emoji来增加文章的生动性。例如，📈表示上涨，📉表示下跌。
4.  **结尾**: 进行要点总结，并加上一些鼓励读者互动、讨论的话语。
5.  **免责声明**: 在文章末尾必须加上免责声明，提示“本文仅为个人观点分享，不构成任何投资建议，市场有风险，投资需谨慎”。
"""
    
    final_article = call_gemini_ai(polish_prompt)
    print("\n--- 经AI润色后的最终文章 ---")
    print(final_article)
    
    # --- 保存文章到文件 ---
    if not os.path.exists('reports'):
        os.makedirs('reports')
    beijing_time = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    file_name = f"reports/基金分析报告_{beijing_time.strftime('%Y-%m-%d_%H-%M')}.md"
    with open(file_name, 'w', encoding='utf-8') as f:
        f.write(final_article)
    print(f"\n报告已成功保存为: {file_name}")

    update_timestamp()

if __name__ == "__main__":
    main()
