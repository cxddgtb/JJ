import os
import json
import asyncio
import aiohttp
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from concurrent.futures import ThreadPoolExecutor

# --- 配置区 ---
# 搜索关键词
KEYWORDS = ["中国基金新闻", "A股市场分析", "宏观经济政策", "热门基金板块"]
# 目标搜索引擎 (使用多引擎确保信息全面)
SEARCH_ENGINES = {
    "google": "https://www.google.com/search?q=",
    "bing": "https://www.bing.com/search?q=",
}
# 目标财经网站 (使用Selenium模拟浏览器访问)
FINANCIAL_WEBSITES = {
    "eastmoney": "http://fund.eastmoney.com/",
    # 您可以添加更多需要爬取的网站
}

# --- 爬虫函数 ---
def fetch_search_results(session, engine, keyword):
    """使用aiohttp异步获取搜索引擎结果"""
    url = f"{SEARCH_ENGINES[engine]}{keyword}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
    try:
        async with session.get(url, headers=headers, timeout=10) as response:
            return await response.text()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_news(html_content):
    """解析HTML内容，提取新闻标题和链接"""
    soup = BeautifulSoup(html_content, 'html.parser')
    news_items = []
    # (这里的选择器需要根据实际搜索结果页进行适配)
    for item in soup.find_all('h3'):
        title = item.get_text()
        link = item.find('a')['href'] if item.find('a') else 'No link'
        news_items.append({"title": title, "link": link})
    return news_items

def scrape_dynamic_website(site_name, url):
    """使用Selenium爬取动态加载的网站内容"""
    print(f"Scraping {site_name} with Selenium...")
    options = Options()
    options.add_argument("--headless") # 无头模式，在服务器上运行
    driver = webdriver.Firefox(options=options)
    try:
        driver.get(url)
        # 等待页面加载
        await asyncio.sleep(5) 
        # (这里可以加入更复杂的逻辑，比如点击按钮、滚动页面等)
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        # (根据网站结构提取需要的数据)
        # 示例：提取一些关键指标或文章标题
        data = {"source": site_name, "content": "一些从动态网站提取的数据"}
        return data
    except Exception as e:
        print(f"Error scraping {url} with Selenium: {e}")
        return None
    finally:
        driver.quit()

async def main():
    all_news = []
    financial_data = []

    # 1. 多线程执行搜索引擎爬取
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_search_results(session, engine, keyword) for engine in SEARCH_ENGINES for keyword in KEYWORDS]
        html_contents = await asyncio.gather(*tasks)
        for html in html_contents:
            if html:
                all_news.extend(parse_news(html))

    # 2. 多线程执行动态网站爬取
    with ThreadPoolExecutor(max_workers=4) as executor:
        loop = asyncio.get_event_loop()
        futures = [loop.run_in_executor(executor, scrape_dynamic_website, name, url) for name, url in FINANCIAL_WEBSITES.items()]
        for response in await asyncio.gather(*futures):
            if response:
                financial_data.append(response)

    # 整合所有数据并保存
    final_data = {
        "news": all_news[:50], # 取前50条新闻，防止数据过大
        "indicators": financial_data
    }
    with open("collected_data.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    print("Data collection finished. Data saved to collected_data.json")

if __name__ == "__main__":
    asyncio.run(main())
