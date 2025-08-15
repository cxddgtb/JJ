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
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
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
