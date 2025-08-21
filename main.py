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
# 模拟浏览器请求头，防止被网站屏蔽
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def check_time_interval():
    """检查距离上次突发事件执行是否超过指定间隔"""
    # 这个函数只在事件触发时检查，定时任务不受影响
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
            # 使用DDGS的news方法
            ddgs_results = ddgs.news(keyword, region='cn-zh', safesearch='off', max_results=MAX_NEWS_RESULTS)
            if ddgs_results:
                for r in ddgs_results:
                    results.append(f"- [标题] {r['title']}\n  [链接] {r['url']}\n  [摘要] {r.get('body', '无')}\n")
    except Exception as e:
        print(f"搜索关键词 '{keyword}' 失败: {e}")
    return "\n".join(results)

def get_fund_data(fund_code):
    """
    爬取基金数据。
    注意：这里以天天基金网为例，网站结构可能变化导致爬虫失效，这是最需要维护的部分。
    """
    print(f"正在爬取基金数据: {fund_code}...")
    url = f"http://fund.eastmoney.com/{fund_code}.html"
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUESTS_TIMEOUT)
        response.raise_for_status() # 如果请求失败则抛出异常
        soup = BeautifulSoup(response.text, 'html.parser')
        
        fund_name = soup.select_one('div.fundDetail-tit > div').get_text(strip=True).replace('(前端)', '')
        # 获取净值、日增长率等信息
        data_item = soup.select_one('dl.dataItem02')
        net_value = data_item.select_one('dd.dataNums > span.ui-font-large').text
        daily_growth = data_item.select_one('dd.dataNums > span:nth-of-type(2)').text
        
        # 获取各类指标
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
        return f"\n### 基金: {fund_code}\n- 数据爬取失败，请检查网站结构或网络连接。\n"

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
    
    # 使用多线程并行处理数据获取
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # 并行搜索新闻
        news_futures = {executor.submit(search_news, kw): kw for kw in NEWS_KEYWORDS}
        # 并行爬取基金数据
        fund_futures = {executor.submit(get_fund_data, code): code for code in FUND_CODES}
        
        # 等待所有任务完成并收集结果
        all_news_text = "\n".join([future.result() for future in concurrent.futures.as_completed(news_futures)])
        all_fund_data = "\n".join([future.result() for future in concurrent.futures.as_completed(fund_futures)])

    print("\n--- 新闻数据汇总 ---")
    print(all_news_text)
    print("\n--- 基金数据汇总 ---")
    print(all_fund_data)
    
    # --- 第一步：AI分析并生成初稿 ---
    analysis_prompt = f"""
作为一名专业的基金投资分析师，请根据以下最新的市场新闻和基金数据，为我提供一份详细的投资操作分析报告。

**【市场新闻摘要】**
{all_news_text}

**【我关注的基金数据】**
{all_fund_data}

**【报告要求】**
1.  **市场情绪判断**: 结合新闻，判断当前市场的宏观情绪是乐观、悲观还是中性。
2.  **具体基金分析**: 逐一分析我关注的每支基金，并结合新闻判断它们可能受到的影响。
3.  **操作建议**: 给出明确的总体操作建议（如：加仓、减仓、持仓观望或调仓），并说明核心理由，理由必须结合给出的新闻和数据。
4.  **风险提示**: 指出当前操作可能面临的主要风险。
5.  语言风格要求专业、客观、逻辑清晰。
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
1.  **标题**: 起一个吸引人但不过于夸张的标题。
2.  **引言**: 写一段引人入胜的开场白，概括一下当前的市场情况和本文的核心看点。
3.  **正文**: 保持原文的核心观点和数据逻辑不变，但用更通俗易懂、更有感染力的语言来表达。可以适当使用emoji来增加文章的活力。
4.  **结尾**: 进行总结，并加上一些鼓励读者交流讨论的话语。
5.  **免责声明**: 在文章末尾必须加上免责声明，提示“本文仅为个人观点分享，不构成任何投资建议”。
"""
    
    final_article = call_gemini_ai(polish_prompt)
    print("\n--- 经AI润色后的最终文章 ---")
    print(final_article)
    
    # --- 保存文章到文件 ---
    # 创建reports目录（如果不存在）
    if not os.path.exists('reports'):
        os.makedirs('reports')
        
    beijing_time = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    file_name = f"reports/基金分析报告_{beijing_time.strftime('%Y-%m-%d_%H-%M')}.md"
    with open(file_name, 'w', encoding='utf-8') as f:
        f.write(final_article)
        
    print(f"\n报告已成功保存为: {file_name}")

    # 总是更新时间戳，确保文件存在以便于git提交。
    # 脚本开头的间隔检查逻辑不受影响，因为它只在 'repository_dispatch' 事件中生效。
    update_timestamp()

if __name__ == "__main__":
    main()
