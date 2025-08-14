import requests
import time
import random
import logging
from abc import ABC, abstractmethod
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import CRAWL_DELAY, MAX_RETRIES, TIMEOUT, USER_AGENTS, CONCURRENT_REQUESTS

class BaseCrawler(ABC):
    """爬虫基类，定义了爬虫的基本功能和接口"""

    def __init__(self, name, base_url):
        self.name = name
        self.base_url = base_url
        self.session = requests.Session()
        self.ua = UserAgent()
        self.logger = logging.getLogger(self.name)
        self.setup_session()

    def setup_session(self):
        """设置请求会话"""
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })

    def get_random_user_agent(self):
        """获取随机User-Agent"""
        return random.choice(USER_AGENTS)

    def get_page(self, url, params=None, headers=None, use_selenium=False, timeout=TIMEOUT):
        """获取网页内容"""
        if headers:
            self.session.headers.update(headers)
        else:
            self.session.headers.update({'User-Agent': self.get_random_user_agent()})

        for attempt in range(MAX_RETRIES):
            try:
                if use_selenium:
                    return self._get_page_with_selenium(url, timeout)
                else:
                    response = self.session.get(url, params=params, timeout=timeout)
                    response.raise_for_status()
                    time.sleep(CRAWL_DELAY)
                    return response
            except Exception as e:
                self.logger.error(f"Attempt {attempt + 1} failed for URL {url}: {str(e)}")
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(CRAWL_DELAY * (attempt + 1))

    def _get_page_with_selenium(self, url, timeout):
        """使用Selenium获取动态加载的网页内容"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(f'--user-agent={self.get_random_user_agent()}')

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

        try:
            driver.get(url)
            time.sleep(3)  # 等待页面加载
            page_source = driver.page_source
            return type('MockResponse', (), {'text': page_source, 'status_code': 200})()
        finally:
            driver.quit()

    def parse_html(self, html_content):
        """解析HTML内容"""
        return BeautifulSoup(html_content, 'lxml')

    @abstractmethod
    def crawl_fund_list(self):
        """爬取基金列表，子类必须实现此方法"""
        pass

    @abstractmethod
    def crawl_fund_detail(self, fund_code):
        """爬取基金详情，子类必须实现此方法"""
        pass

    @abstractmethod
    def crawl_fund_news(self):
        """爬取基金新闻，子类必须实现此方法"""
        pass

    def crawl_multiple_funds(self, fund_codes, max_workers=CONCURRENT_REQUESTS):
        """并发爬取多个基金数据"""
        results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_code = {executor.submit(self.crawl_fund_detail, code): code for code in fund_codes}
            for future in as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    results[code] = future.result()
                except Exception as e:
                    self.logger.error(f"Error crawling fund {code}: {str(e)}")
                    results[code] = None
        return results

    def save_data(self, data, file_path):
        """保存数据到文件"""
        import json
        import os
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.logger.info(f"Data saved to {file_path}")
