<<<<<<< HEAD
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import random
import argparse
import logging
import json
import pandas as pd
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import re

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.logger import setup_logger
from utils.config import Config
from utils.helpers import retry

class NewsCrawler:
    def __init__(self, max_workers=10, delay=1):
        """
        初始化新闻爬虫

        Args:
            max_workers (int): 最大线程数
            delay (float): 请求延迟(秒)
        """
        self.max_workers = max_workers
        self.delay = delay
        self.ua = UserAgent()
        self.session = requests.Session()
        self.session.headers.update({
=======
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
新闻爬虫模块
"""

import os
import json
import time
import logging
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from datetime import datetime
from typing import List, Dict, Any, Optional

from ..utils.config import NEWS_SOURCES, DATA_DIR, CRAWLER_CONFIG
from ..utils.thread_pool import run_with_thread_pool

logger = logging.getLogger(__name__)

class NewsCrawler:
    """新闻爬虫类"""

    def __init__(self):
        """初始化新闻爬虫"""
        self.data_dir = os.path.join(DATA_DIR, 'news')
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        self.session = requests.Session()
        self.ua = UserAgent()
        self.timeout = CRAWLER_CONFIG.get('timeout', 30)
        self.retry_times = CRAWLER_CONFIG.get('retry_times', 3)
        self.delay = CRAWLER_CONFIG.get('delay', 1)

        # 设置请求头
        self.headers = {
>>>>>>> b18564d6e095109b4e15afc2fd8319e3704d4f68
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
<<<<<<< HEAD
        })

        # 设置日志
        self.logger = setup_logger('NewsCrawler')

        # 新闻来源URL
        self.news_sources = {
            'eastmoney': {
                'name': '东方财富网',
                'base_url': 'https://fund.eastmoney.com/',
                'news_list_url': 'https://fund.eastmoney.com/news/{page}.html',
                'news_detail_url': 'https://fund.eastmoney.com/{news_id}.html',
                'pages': 5  # 爬取前5页新闻
            },
            'hexun': {
                'name': '和讯网',
                'base_url': 'https://funds.hexun.com/',
                'news_list_url': 'https://funds.hexun.com/list/{page}.html',
                'pages': 5
            },
            'cnstock': {
                'name': '上海证券报',
                'base_url': 'https://www.cnstock.com/',
                'news_list_url': 'https://www.cnstock.com/roll/',
                'pages': 5
            },
            'chinafund': {
                'name': '中国基金网',
                'base_url': 'https://www.chinafund.cn/',
                'news_list_url': 'https://www.chinafund.cn/news/',
                'pages': 5
            }
        }

    @retry(max_retries=3, delay=2)
    def crawl_eastmoney_news(self, pages=5):
        """
        爬取东方财富网基金新闻

        Args:
            pages (int): 爬取页数

        Returns:
            list: 新闻列表
        """
        news_list = []

        try:
            for page in range(1, pages + 1):
                try:
                    # 构建新闻列表页URL
                    url = self.news_sources['eastmoney']['news_list_url'].format(page=page)

                    # 随机User-Agent
                    headers = {
                        'User-Agent': self.ua.random,
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                        'Connection': 'keep-alive',
                    }

                    response = self.session.get(url, headers=headers, timeout=10)
                    response.raise_for_status()

                    # 使用BeautifulSoup解析HTML
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # 查找新闻列表
                    news_items = soup.find_all('div', class_='news-item')

                    for item in news_items:
                        # 提取新闻信息
                        news_info = {
                            'source': '东方财富网',
                            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'title': '',
                            'summary': '',
                            'url': '',
                            'publish_time': '',
                            'content': ''
                        }

                        # 新闻标题
                        title_element = item.find('a', class_='title')
                        if title_element:
                            news_info['title'] = title_element.text.strip()
                            news_info['url'] = 'https:' + title_element['href'] if title_element['href'].startswith('//') else title_element['href']

                        # 新闻摘要
                        summary_element = item.find('p', class_='summary')
                        if summary_element:
                            news_info['summary'] = summary_element.text.strip()

                        # 发布时间
                        time_element = item.find('span', class_='time')
                        if time_element:
                            news_info['publish_time'] = time_element.text.strip()

                        # 如果有URL，爬取新闻详情
                        if news_info['url']:
                            try:
                                news_detail = self.crawl_news_detail(news_info['url'])
                                news_info.update(news_detail)
                            except Exception as e:
                                self.logger.error(f"爬取新闻详情失败: {news_info['url']}, 错误: {str(e)}")

                        news_list.append(news_info)

                        # 随机延迟
                        time.sleep(self.delay)

                    self.logger.info(f"东方财富网第{page}页新闻爬取完成，共获取{len(news_list)}条新闻")

                except Exception as e:
                    self.logger.error(f"爬取东方财富网第{page}页新闻失败: {str(e)}")
                    continue

        except Exception as e:
            self.logger.error(f"爬取东方财富网新闻失败: {str(e)}")

        return news_list

    @retry(max_retries=3, delay=2)
    def crawl_hexun_news(self, pages=5):
        """
        爬取和讯网基金新闻

        Args:
            pages (int): 爬取页数

        Returns:
            list: 新闻列表
        """
        news_list = []

        try:
            for page in range(1, pages + 1):
                try:
                    # 构建新闻列表页URL
                    url = self.news_sources['hexun']['news_list_url'].format(page=page)

                    # 随机User-Agent
                    headers = {
                        'User-Agent': self.ua.random,
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                        'Connection': 'keep-alive',
                    }

                    response = self.session.get(url, headers=headers, timeout=10)
                    response.raise_for_status()

                    # 使用BeautifulSoup解析HTML
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # 查找新闻列表
                    news_items = soup.find_all('div', class_='news-list')

                    if not news_items:
                        # 尝试其他可能的类名
                        news_items = soup.find_all('div', class_='newslist')

                    if news_items:
                        for item in news_items:
                            # 提取新闻信息
                            news_info = {
                                'source': '和讯网',
                                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'title': '',
                                'summary': '',
                                'url': '',
                                'publish_time': '',
                                'content': ''
                            }

                            # 新闻标题和URL
                            title_element = item.find('a')
                            if title_element:
                                news_info['title'] = title_element.text.strip()
                                news_info['url'] = title_element['href'] if title_element['href'].startswith('http') else 'https:' + title_element['href']

                            # 发布时间
                            time_element = item.find('span')
                            if time_element:
                                news_info['publish_time'] = time_element.text.strip()

                            # 如果有URL，爬取新闻详情
                            if news_info['url']:
                                try:
                                    news_detail = self.crawl_news_detail(news_info['url'])
                                    news_info.update(news_detail)
                                except Exception as e:
                                    self.logger.error(f"爬取新闻详情失败: {news_info['url']}, 错误: {str(e)}")

                            news_list.append(news_info)

                            # 随机延迟
                            time.sleep(self.delay)

                    self.logger.info(f"和讯网第{page}页新闻爬取完成，共获取{len(news_list)}条新闻")

                except Exception as e:
                    self.logger.error(f"爬取和讯网第{page}页新闻失败: {str(e)}")
                    continue

        except Exception as e:
            self.logger.error(f"爬取和讯网新闻失败: {str(e)}")

        return news_list

    @retry(max_retries=3, delay=2)
    def crawl_cnstock_news(self, pages=5):
        """
        爬取上海证券报基金新闻

        Args:
            pages (int): 爬取页数

        Returns:
            list: 新闻列表
        """
        news_list = []

        try:
            # 上海证券报新闻列表页
            url = self.news_sources['cnstock']['news_list_url']

            # 随机User-Agent
            headers = {
                'User-Agent': self.ua.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Connection': 'keep-alive',
            }

            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # 查找新闻列表
            news_items = soup.find_all('li', class_='news-li')

            for item in news_items:
                # 提取新闻信息
                news_info = {
                    'source': '上海证券报',
                    'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'title': '',
                    'summary': '',
                    'url': '',
                    'publish_time': '',
                    'content': ''
                }

                # 新闻标题和URL
                title_element = item.find('h3')
                if title_element:
                    title_a = title_element.find('a')
                    if title_a:
                        news_info['title'] = title_a.text.strip()
                        news_info['url'] = title_a['href'] if title_a['href'].startswith('http') else 'https://www.cnstock.com' + title_a['href']

                # 发布时间
                time_element = item.find('span', class_='time')
                if time_element:
                    news_info['publish_time'] = time_element.text.strip()

                # 如果有URL，爬取新闻详情
                if news_info['url']:
                    try:
                        news_detail = self.crawl_news_detail(news_info['url'])
                        news_info.update(news_detail)
                    except Exception as e:
                        self.logger.error(f"爬取新闻详情失败: {news_info['url']}, 错误: {str(e)}")

                news_list.append(news_info)

                # 随机延迟
                time.sleep(self.delay)

            self.logger.info(f"上海证券报新闻爬取完成，共获取{len(news_list)}条新闻")

        except Exception as e:
            self.logger.error(f"爬取上海证券报新闻失败: {str(e)}")

        return news_list

    @retry(max_retries=3, delay=2)
    def crawl_chinafund_news(self, pages=5):
        """
        爬取中国基金网新闻

        Args:
            pages (int): 爬取页数

        Returns:
            list: 新闻列表
        """
        news_list = []

        try:
            # 中国基金网新闻列表页
            url = self.news_sources['chinafund']['news_list_url']

            # 随机User-Agent
            headers = {
                'User-Agent': self.ua.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Connection': 'keep-alive',
            }

            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # 查找新闻列表
            news_items = soup.find_all('div', class_='news-item')

            for item in news_items:
                # 提取新闻信息
                news_info = {
                    'source': '中国基金网',
                    'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'title': '',
                    'summary': '',
                    'url': '',
                    'publish_time': '',
                    'content': ''
                }

                # 新闻标题和URL
                title_element = item.find('h3')
                if title_element:
                    title_a = title_element.find('a')
                    if title_a:
                        news_info['title'] = title_a.text.strip()
                        news_info['url'] = title_a['href'] if title_a['href'].startswith('http') else 'https://www.chinafund.cn' + title_a['href']

                # 发布时间
                time_element = item.find('span', class_='date')
                if time_element:
                    news_info['publish_time'] = time_element.text.strip()

                # 如果有URL，爬取新闻详情
                if news_info['url']:
                    try:
                        news_detail = self.crawl_news_detail(news_info['url'])
                        news_info.update(news_detail)
                    except Exception as e:
                        self.logger.error(f"爬取新闻详情失败: {news_info['url']}, 错误: {str(e)}")

                news_list.append(news_info)

                # 随机延迟
                time.sleep(self.delay)

            self.logger.info(f"中国基金网新闻爬取完成，共获取{len(news_list)}条新闻")

        except Exception as e:
            self.logger.error(f"爬取中国基金网新闻失败: {str(e)}")

        return news_list

    @retry(max_retries=3, delay=2)
    def crawl_news_detail(self, url):
        """
        爬取新闻详情

        Args:
            url (str): 新闻URL

        Returns:
            dict: 新闻详情
        """
        try:
            # 随机User-Agent
            headers = {
                'User-Agent': self.ua.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Connection': 'keep-alive',
                'Referer': url
            }

            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # 提取新闻内容
            content = ''
            content_elements = soup.find_all('div', class_='article-content')

            if not content_elements:
                # 尝试其他可能的类名
                content_elements = soup.find_all('div', class_='article')
                if not content_elements:
                    content_elements = soup.find_all('div', class_='content')

            if content_elements:
                for element in content_elements:
                    # 提取段落
                    paragraphs = element.find_all('p')
                    for p in paragraphs:
                        text = p.text.strip()
                        if text:
                            content += text + '\n\n'

            # 提取发布时间
            publish_time = ''
            time_elements = soup.find_all('span', class_='time')

            if not time_elements:
                time_elements = soup.find_all('div', class='article-info')

            if time_elements:
                for element in time_elements:
                    time_text = element.text.strip()
                    if '发布' in time_text or '时间' in time_text or '来源' in time_text:
                        publish_time = time_text
                        break

            return {
                'content': content.strip(),
                'publish_time': publish_time
            }

        except Exception as e:
            self.logger.error(f"爬取新闻详情失败: {url}, 错误: {str(e)}")
            return {
                'content': '',
                'publish_time': ''
            }

    def crawl_all_news(self, output_file=None):
        """
        爬取所有来源的基金新闻

        Args:
            output_file (str): 输出文件路径

        Returns:
            list: 新闻列表
        """
        all_news = []

        try:
            # 使用线程池并行爬取不同来源的新闻
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交任务
                futures = {
                    executor.submit(self.crawl_eastmoney_news): '东方财富网',
                    executor.submit(self.crawl_hexun_news): '和讯网',
                    executor.submit(self.crawl_cnstock_news): '上海证券报',
                    executor.submit(self.crawl_chinafund_news): '中国基金网'
                }

                # 使用tqdm显示进度条
                with tqdm(total=len(futures), desc="爬取基金新闻") as pbar:
                    for future in as_completed(futures):
                        source_name = futures[future]
                        try:
                            news_list = future.result()
                            all_news.extend(news_list)
                            self.logger.info(f"{source_name}新闻爬取完成，获取{len(news_list)}条新闻")
                        except Exception as e:
                            self.logger.error(f"{source_name}新闻爬取失败: {str(e)}")
                        pbar.update(1)

            # 去重
            unique_news = []
            seen_urls = set()

            for news in all_news:
                if news['url'] and news['url'] not in seen_urls:
                    unique_news.append(news)
                    seen_urls.add(news['url'])

            # 按爬取时间排序
            unique_news.sort(key=lambda x: x['crawl_time'], reverse=True)

            # 保存到文件
            if output_file:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)

                # 保存为JSON
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(unique_news, f, ensure_ascii=False, indent=2)

                # 保存为CSV
                df = pd.DataFrame(unique_news)
                csv_file = os.path.splitext(output_file)[0] + '.csv'
                df.to_csv(csv_file, index=False, encoding='utf-8-sig')

                self.logger.info(f"新闻数据已保存到: {output_file} 和 {csv_file}")

            return unique_news

        except Exception as e:
            self.logger.error(f"爬取所有新闻失败: {str(e)}")
            return []


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='爬取基金新闻')
    parser.add_argument('--output', type=str, required=True,
                        help='输出文件路径')
    parser.add_argument('--workers', type=int, default=10,
                        help='最大线程数')
    parser.add_argument('--delay', type=float, default=1.0,
                        help='请求延迟(秒)')

    args = parser.parse_args()

    # 创建爬虫实例
    crawler = NewsCrawler(
        max_workers=args.workers,
        delay=args.delay
    )

    # 爬取新闻
    crawler.crawl_all_news(
        output_file=args.output
    )


if __name__ == '__main__':
    main()
=======
        }

        logger.info("新闻爬虫初始化完成")

    def _make_request(self, url: str) -> Optional[requests.Response]:
        """
        发送HTTP请求

        Args:
            url: 请求URL

        Returns:
            Response对象或None
        """
        for attempt in range(self.retry_times):
            try:
                # 随机User-Agent
                self.headers['User-Agent'] = self.ua.random

                # 发送请求
                response = self.session.get(url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
                response.encoding = response.apparent_encoding

                # 延迟，避免请求过于频繁
                time.sleep(self.delay)

                return response
            except Exception as e:
                logger.warning(f"请求 {url} 失败 (尝试 {attempt + 1}/{self.retry_times}): {str(e)}")
                if attempt < self.retry_times - 1:
                    time.sleep(2 ** attempt)  # 指数退避

        logger.error(f"请求 {url} 失败，已达到最大重试次数")
        return None

    def _parse_news_list(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析新闻列表页

        Args:
            source: 新闻源配置

        Returns:
            新闻列表
        """
        url = source['url']
        list_selector = source['list_selector']
        title_selector = source['title_selector']
        link_selector = source['link_selector']
        date_selector = source['date_selector']

        response = self._make_request(url)
        if not response:
            return []

        soup = BeautifulSoup(response.text, 'lxml')
        news_items = soup.select(list_selector)

        news_list = []
        for item in news_items:
            try:
                title_elem = item.select_one(title_selector)
                link_elem = item.select_one(link_selector)
                date_elem = item.select_one(date_selector)

                if not title_elem or not link_elem:
                    continue

                title = title_elem.get_text(strip=True)
                link = link_elem.get('href', '')

                # 处理相对链接
                if link.startswith('/'):
                    from urllib.parse import urljoin
                    link = urljoin(url, link)

                publish_date = ''
                if date_elem:
                    publish_date = date_elem.get_text(strip=True)

                news_list.append({
                    'title': title,
                    'link': link,
                    'publish_date': publish_date,
                    'source': source['name'],
                    'content': '',
                    'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            except Exception as e:
                logger.warning(f"解析新闻项失败: {str(e)}")
                continue

        return news_list

    def _parse_news_content(self, news_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析新闻内容页

        Args:
            news_item: 新闻项

        Returns:
            包含内容的新闻项
        """
        link = news_item['link']
        source_config = next((s for s in NEWS_SOURCES if s['name'] == news_item['source']), None)

        if not source_config:
            logger.warning(f"找不到新闻源 {news_item['source']} 的配置")
            return news_item

        content_selector = source_config['content_selector']

        response = self._make_request(link)
        if not response:
            return news_item

        soup = BeautifulSoup(response.text, 'lxml')
        content_elem = soup.select_one(content_selector)

        if content_elem:
            # 提取纯文本内容
            content = content_elem.get_text(strip=True)
            news_item['content'] = content
        else:
            logger.warning(f"在 {link} 中找不到内容元素")

        return news_item

    def crawl_news_from_source(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从指定新闻源爬取新闻

        Args:
            source: 新闻源配置

        Returns:
            新闻列表
        """
        logger.info(f"开始从 {source['name']} 爬取新闻...")

        # 解析新闻列表
        news_list = self._parse_news_list(source)
        logger.info(f"从 {source['name']} 解析到 {len(news_list)} 条新闻")

        # 使用线程池爬取新闻内容
        logger.info(f"开始爬取 {source['name']} 的新闻内容...")
        news_list = run_with_thread_pool(self._parse_news_content, news_list)

        # 过滤掉没有内容的新闻
        news_list = [news for news in news_list if news.get('content')]

        logger.info(f"从 {source['name']} 成功爬取 {len(news_list)} 条有内容的新闻")
        return news_list

    def crawl_all_news(self) -> List[Dict[str, Any]]:
        """
        爬取所有新闻源的新闻

        Returns:
            所有新闻列表
        """
        logger.info("开始爬取所有新闻源的新闻...")

        all_news = []
        for source in NEWS_SOURCES:
            try:
                news_from_source = self.crawl_news_from_source(source)
                all_news.extend(news_from_source)
            except Exception as e:
                logger.error(f"爬取 {source['name']} 新闻失败: {str(e)}", exc_info=True)

        # 保存新闻数据
        self.save_news_data(all_news)

        logger.info(f"成功爬取共 {len(all_news)} 条新闻")
        return all_news

    def save_news_data(self, news_list: List[Dict[str, Any]]) -> None:
        """
        保存新闻数据

        Args:
            news_list: 新闻列表
        """
        if not news_list:
            logger.warning("新闻列表为空，不保存数据")
            return

        # 按日期保存
        today = datetime.now().strftime('%Y%m%d')
        filename = os.path.join(self.data_dir, f'news_{today}.json')

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(news_list, f, ensure_ascii=False, indent=2)
            logger.info(f"新闻数据已保存到 {filename}")
        except Exception as e:
            logger.error(f"保存新闻数据失败: {str(e)}", exc_info=True)
>>>>>>> b18564d6e095109b4e15afc2fd8319e3704d4f68
