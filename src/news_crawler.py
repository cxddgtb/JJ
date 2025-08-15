#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
新闻爬取模块
使用多线程和多搜索引擎爬取基金相关新闻
"""

import os
import re
import time
import json
import asyncio
import aiohttp
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from fake_useragent import UserAgent
import logging
from datetime import datetime
import argparse
from typing import List, Dict, Any, Optional

from config import (
    NEWS_CONFIG, OUTPUT_DIR, RAW_DATA_DIR, LOG_CONFIG,
    BROWSER_CONFIG
)
from utils import get_free_apis

# 设置日志
logging.basicConfig(
    level=LOG_CONFIG['level'],
    format=LOG_CONFIG['format'],
    handlers=[
        logging.FileHandler(LOG_CONFIG['file']),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NewsCrawler:
    """新闻爬取类"""

    def __init__(self, fund_type: str = 'mixed', threads: int = 5):
        """
        初始化新闻爬取器

        Args:
            fund_type: 基金类型
            threads: 线程数
        """
        self.fund_type = fund_type
        self.threads = threads
        self.ua = UserAgent()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        })

        # 创建输出目录
        self.news_output_dir = os.path.join(RAW_DATA_DIR, 'news')
        os.makedirs(self.news_output_dir, exist_ok=True)

    def _get_search_engines(self) -> List[str]:
        """获取可用的搜索引擎"""
        return list(NEWS_CONFIG['engines'].keys())

    def _build_search_url(self, engine: str, keyword: str, page: int = 1) -> str:
        """
        构建搜索引擎的URL

        Args:
            engine: 搜索引擎名称
            keyword: 搜索关键词
            page: 页码

        Returns:
            构建好的URL
        """
        engine_config = NEWS_CONFIG['engines'][engine]
        url = engine_config['url']

        params = engine_config['params'].copy()
        params.update({
            '{keyword}': keyword,
            '{page}': str((page - 1) * 10 + 1) if engine == 'baidu' else str(page)
        })

        # 替换参数
        for k, v in params.items():
            url = url.replace(k, v)

        return url

    def _parse_news_from_baidu(self, html: str, keyword: str) -> List[Dict[str, Any]]:
        """
        解析百度搜索结果

        Args:
            html: HTML内容
            keyword: 搜索关键词

        Returns:
            解析后的新闻列表
        """
        news_list = []
        soup = BeautifulSoup(html, 'html.parser')

        # 查找新闻条目
        items = soup.find_all('div', class_='result-op')
        if not items:
            items = soup.find_all('div', class_='result')

        for item in items:
            try:
                title_tag = item.find('h3')
                if not title_tag:
                    continue

                title = title_tag.get_text().strip()
                link = title_tag.find('a')
                if not link:
                    continue

                url = link.get('href')
                if not url:
                    continue

                # 获取摘要
                abstract_tag = item.find('div', class_='c-abstract')
                abstract = abstract_tag.get_text().strip() if abstract_tag else ''

                # 获取来源和时间
                source_tag = item.find('p', class_='c-author')
                source = ''
                publish_time = ''

                if source_tag:
                    source_text = source_tag.get_text().strip()
                    # 尝试提取来源和时间
                    source_match = re.search(r'来源：(.+?)\s', source_text)
                    time_match = re.search(r'(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}:\d{1,2})', source_text)

                    if source_match:
                        source = source_match.group(1)
                    if time_match:
                        publish_time = time_match.group(1)

                if not publish_time:
                    publish_time = datetime.now().strftime('%Y-%m-%d')

                news_list.append({
                    'title': title,
                    'url': url,
                    'abstract': abstract,
                    'source': source,
                    'publish_time': publish_time,
                    'keyword': keyword,
                    'engine': 'baidu'
                })
            except Exception as e:
                logger.warning(f"解析百度新闻条目失败: {e}")
                continue

        return news_list

    def _parse_news_from_google(self, html: str, keyword: str) -> List[Dict[str, Any]]:
        """
        解析Google搜索结果

        Args:
            html: HTML内容
            keyword: 搜索关键词

        Returns:
            解析后的新闻列表
        """
        news_list = []
        soup = BeautifulSoup(html, 'html.parser')

        # 查找新闻条目
        items = soup.find_all('div', class_='g')
        if not items:
            items = soup.find_all('div', class_='SoC6k')

        for item in items:
            try:
                # 尝试获取标题和链接
                title_tag = item.find('h3')
                if not title_tag:
                    title_tag = item.find('h2')

                if not title_tag:
                    continue

                title = title_tag.get_text().strip()
                link = title_tag.find('a')
                if not link:
                    continue

                url = link.get('href')
                if not url:
                    continue

                # 获取摘要
                abstract_tag = item.find('div', class_='VwiC3b')
                if not abstract_tag:
                    abstract_tag = item.find('div', class_='yDYNvb')

                abstract = abstract_tag.get_text().strip() if abstract_tag else ''

                # 获取来源和时间
                source_tag = item.find('div', class_='BNeawe UPmit')
                if not source_tag:
                    source_tag = item.find('div', class_='s3vajd')

                source = ''
                publish_time = ''

                if source_tag:
                    source_text = source_tag.get_text().strip()
                    # 尝试提取来源和时间
                    source_match = re.search(r'(.+?)\s*·\s*(.+)', source_text)

                    if source_match:
                        source = source_match.group(1)
                        publish_time = source_match.group(2)

                if not publish_time:
                    publish_time = datetime.now().strftime('%Y-%m-%d')

                news_list.append({
                    'title': title,
                    'url': url,
                    'abstract': abstract,
                    'source': source,
                    'publish_time': publish_time,
                    'keyword': keyword,
                    'engine': 'google'
                })
            except Exception as e:
                logger.warning(f"解析Google新闻条目失败: {e}")
                continue

        return news_list

    def _parse_news_from_bing(self, html: str, keyword: str) -> List[Dict[str, Any]]:
        """
        解析Bing搜索结果

        Args:
            html: HTML内容
            keyword: 搜索关键词

        Returns:
            解析后的新闻列表
        """
        news_list = []
        soup = BeautifulSoup(html, 'html.parser')

        # 查找新闻条目
        items = soup.find_all('li', class_='b_algo')
        if not items:
            items = soup.find_all('div', class_='b_algo')

        for item in items:
            try:
                # 尝试获取标题和链接
                title_tag = item.find('h2')
                if not title_tag:
                    continue

                title = title_tag.get_text().strip()
                link = title_tag.find('a')
                if not link:
                    continue

                url = link.get('href')
                if not url:
                    continue

                # 获取摘要
                abstract_tag = item.find('p')
                abstract = abstract_tag.get_text().strip() if abstract_tag else ''

                # 获取来源和时间
                source_tag = item.find('div', class_='b_attribution')
                source = ''
                publish_time = ''

                if source_tag:
                    source_text = source_tag.get_text().strip()
                    # 尝试提取来源和时间
                    source_match = re.search(r'(.+?)\s*·\s*(.+)', source_text)

                    if source_match:
                        source = source_match.group(1)
                        publish_time = source_match.group(2)

                if not publish_time:
                    publish_time = datetime.now().strftime('%Y-%m-%d')

                news_list.append({
                    'title': title,
                    'url': url,
                    'abstract': abstract,
                    'source': source,
                    'publish_time': publish_time,
                    'keyword': keyword,
                    'engine': 'bing'
                })
            except Exception as e:
                logger.warning(f"解析Bing新闻条目失败: {e}")
                continue

        return news_list

    def _parse_news_from_sogou(self, html: str, keyword: str) -> List[Dict[str, Any]]:
        """
        解析搜狗搜索结果

        Args:
            html: HTML内容
            keyword: 搜索关键词

        Returns:
            解析后的新闻列表
        """
        news_list = []
        soup = BeautifulSoup(html, 'html.parser')

        # 查找新闻条目
        items = soup.find_all('div', class_='results')
        if not items:
            items = soup.find_all('div', class_='vrwrap')

        for item in items:
            try:
                # 尝试获取标题和链接
                title_tag = item.find('h3')
                if not title_tag:
                    continue

                title = title_tag.get_text().strip()
                link = title_tag.find('a')
                if not link:
                    continue

                url = link.get('href')
                if not url:
                    continue

                # 获取摘要
                abstract_tag = item.find('p', class='ft')
                abstract = abstract_tag.get_text().strip() if abstract_tag else ''

                # 获取来源和时间
                source_tag = item.find('div', class_='news-info')
                source = ''
                publish_time = ''

                if source_tag:
                    source_text = source_tag.get_text().strip()
                    # 尝试提取来源和时间
                    source_match = re.search(r'来源：(.+?)\s', source_text)
                    time_match = re.search(r'(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}:\d{1,2})', source_text)

                    if source_match:
                        source = source_match.group(1)
                    if time_match:
                        publish_time = time_match.group(1)

                if not publish_time:
                    publish_time = datetime.now().strftime('%Y-%m-%d')

                news_list.append({
                    'title': title,
                    'url': url,
                    'abstract': abstract,
                    'source': source,
                    'publish_time': publish_time,
                    'keyword': keyword,
                    'engine': 'sogou'
                })
            except Exception as e:
                logger.warning(f"解析搜狗新闻条目失败: {e}")
                continue

        return news_list

    def _parse_news_from_360(self, html: str, keyword: str) -> List[Dict[str, Any]]:
        """
        解析360搜索结果

        Args:
            html: HTML内容
            keyword: 搜索关键词

        Returns:
            解析后的新闻列表
        """
        news_list = []
        soup = BeautifulSoup(html, 'html.parser')

        # 查找新闻条目
        items = soup.find_all('div', class_='result')
        if not items:
            items = soup.find_all('div', class_='sc-body')

        for item in items:
            try:
                # 尝试获取标题和链接
                title_tag = item.find('h3')
                if not title_tag:
                    continue

                title = title_tag.get_text().strip()
                link = title_tag.find('a')
                if not link:
                    continue

                url = link.get('href')
                if not url:
                    continue

                # 获取摘要
                abstract_tag = item.find('div', class_='c-abstract')
                abstract = abstract_tag.get_text().strip() if abstract_tag else ''

                # 获取来源和时间
                source_tag = item.find('div', class_='c-gap-top-small')
                source = ''
                publish_time = ''

                if source_tag:
                    source_text = source_tag.get_text().strip()
                    # 尝试提取来源和时间
                    source_match = re.search(r'来源：(.+?)\s', source_text)
                    time_match = re.search(r'(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}:\d{1,2})', source_text)

                    if source_match:
                        source = source_match.group(1)
                    if time_match:
                        publish_time = time_match.group(1)

                if not publish_time:
                    publish_time = datetime.now().strftime('%Y-%m-%d')

                news_list.append({
                    'title': title,
                    'url': url,
                    'abstract': abstract,
                    'source': source,
                    'publish_time': publish_time,
                    'keyword': keyword,
                    'engine': '360'
                })
            except Exception as e:
                logger.warning(f"解析360新闻条目失败: {e}")
                continue

        return news_list

    def _parse_news_html(self, html: str, engine: str, keyword: str) -> List[Dict[str, Any]]:
        """
        根据搜索引擎类型解析HTML

        Args:
            html: HTML内容
            engine: 搜索引擎名称
            keyword: 搜索关键词

        Returns:
            解析后的新闻列表
        """
        try:
            if engine == 'baidu':
                return self._parse_news_from_baidu(html, keyword)
            elif engine == 'google':
                return self._parse_news_from_google(html, keyword)
            elif engine == 'bing':
                return self._parse_news_from_bing(html, keyword)
            elif engine == 'sogou':
                return self._parse_news_from_sogou(html, keyword)
            elif engine == '360':
                return self._parse_news_from_360(html, keyword)
            else:
                logger.warning(f"不支持的搜索引擎: {engine}")
                return []
        except Exception as e:
            logger.error(f"解析{engine}搜索结果失败: {e}")
            return []

    def _fetch_news_from_engine(self, engine: str, keyword: str, max_pages: int) -> List[Dict[str, Any]]:
        """
        从单个搜索引擎获取新闻

        Args:
            engine: 搜索引擎名称
            keyword: 搜索关键词
            max_pages: 最大页数

        Returns:
            获取到的新闻列表
        """
        logger.info(f"从{engine}搜索关键词: {keyword}")
        news_list = []

        for page in range(1, max_pages + 1):
            try:
                # 构建URL
                url = self._build_search_url(engine, keyword, page)

                # 添加随机User-Agent
                headers = self.session.headers.copy()
                headers['User-Agent'] = self.ua.random

                # 发送请求
                response = self.session.get(url, headers=headers, timeout=10)
                response.raise_for_status()

                # 解析HTML
                engine_news = self._parse_news_html(response.text, engine, keyword)

                if not engine_news:
                    logger.info(f"{engine}没有找到更多新闻，停止搜索")
                    break

                news_list.extend(engine_news)
                logger.info(f"{engine}第{page}页，找到{len(engine_news)}条新闻")

                # 添加延迟，避免被封
                time.sleep(2)

            except Exception as e:
                logger.error(f"从{engine}获取第{page}页失败: {e}")
                time.sleep(5)
                continue

        return news_list

    def _fetch_news_single_thread(self, engines: List[str], keywords: List[str], max_pages: int) -> List[Dict[str, Any]]:
        """
        单线程获取新闻

        Args:
            engines: 搜索引擎列表
            keywords: 关键词列表
            max_pages: 最大页数

        Returns:
            获取到的新闻列表
        """
        all_news = []

        for keyword in keywords:
            logger.info(f"开始搜索关键词: {keyword}")
            keyword_news = []

            for engine in engines:
                engine_news = self._fetch_news_from_engine(engine, keyword, max_pages)
                keyword_news.extend(engine_news)

            all_news.extend(keyword_news)
            logger.info(f"关键词{keyword}共找到{len(keyword_news)}条新闻")

        return all_news

    def _fetch_news_multi_thread(self, engines: List[str], keywords: List[str], max_pages: int) -> List[Dict[str, Any]]:
        """
        多线程获取新闻

        Args:
            engines: 搜索引擎列表
            keywords: 关键词列表
            max_pages: 最大页数

        Returns:
            获取到的新闻列表
        """
        all_news = []

        # 创建线程池
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            # 为每个关键词和引擎创建任务
            futures = []
            for keyword in keywords:
                for engine in engines:
                    futures.append(executor.submit(
                        self._fetch_news_from_engine, 
                        engine, keyword, max_pages
                    ))

            # 收集结果
            for future in as_completed(futures):
                try:
                    news_list = future.result()
                    all_news.extend(news_list)
                    logger.info(f"线程完成，获取到{len(news_list)}条新闻")
                except Exception as e:
                    logger.error(f"线程执行失败: {e}")

        return all_news

    def _save_news(self, news_list: List[Dict[str, Any]]) -> None:
        """
        保存新闻到文件

        Args:
            news_list: 新闻列表
        """
        if not news_list:
            logger.warning("没有新闻需要保存")
            return

        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"news_{self.fund_type}_{timestamp}.json"
        filepath = os.path.join(self.news_output_dir, filename)

        # 保存到JSON文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(news_list, f, ensure_ascii=False, indent=2)

        logger.info(f"新闻已保存到: {filepath}，共{len(news_list)}条")

    def _deduplicate_news(self, news_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        去重新闻

        Args:
            news_list: 新闻列表

        Returns:
            去重后的新闻列表
        """
        seen_urls = set()
        unique_news = []

        for news in news_list:
            url = news.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_news.append(news)

        logger.info(f"去重前: {len(news_list)}条，去重后: {len(unique_news)}条")
        return unique_news

    def crawl(self, use_multi_thread: bool = True) -> None:
        """
        爬取新闻

        Args:
            use_multi_thread: 是否使用多线程
        """
        logger.info("开始爬取基金新闻")

        # 获取搜索引擎和关键词
        engines = self._get_search_engines()
        keywords = NEWS_CONFIG['keywords']
        max_pages = NEWS_CONFIG['max_news_per_engine']

        logger.info(f"使用搜索引擎: {', '.join(engines)}")
        logger.info(f"使用关键词: {', '.join(keywords)}")
        logger.info(f"最大页数: {max_pages}")

        # 根据配置选择单线程或多线程
        if use_multi_thread:
            news_list = self._fetch_news_multi_thread(engines, keywords, max_pages)
        else:
            news_list = self._fetch_news_single_thread(engines, keywords, max_pages)

        # 尝试从免费API获取更多新闻
        try:
            from utils import get_free_apis
            free_apis = get_free_apis()
            if free_apis:
                logger.info(f"从{len(free_apis)}个免费API获取新闻")
                for api in free_apis:
                    try:
                        # 构建请求URL
                        url = api['url'].replace('{keyword}', keywords[0])
                        
                        # 发送请求
                        response = self.session.get(url, timeout=10)
                        if response.status_code == 200:
                            if api['type'] == 'json':
                                data = response.json()
                            else:
                                data = response.text
                            
                            # 解析数据
                            if isinstance(data, dict) and 'news' in data:
                                for item in data['news']:
                                    news_list.append({
                                        'title': item.get('title', ''),
                                        'url': item.get('url', ''),
                                        'abstract': item.get('summary', ''),
                                        'source': api['name'],
                                        'publish_time': item.get('date', ''),
                                        'keyword': keywords[0],
                                        'engine': 'free_api'
                                    })
                    except Exception as e:
                        logger.debug(f"从免费API获取新闻失败: {e}")
                        continue
        except Exception as e:
            logger.warning(f"使用免费API获取新闻失败: {e}")

        # 去重
        news_list = self._deduplicate_news(news_list)

        # 保存新闻
        self._save_news(news_list)

        logger.info("新闻爬取完成")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='基金新闻爬取工具')
    parser.add_argument('--fund-type', type=str, default='mixed', help='基金类型')
    parser.add_argument('--threads', type=int, default=5, help='线程数')
    parser.add_argument('--single-thread', action='store_true', help='使用单线程模式')

    args = parser.parse_args()

    # 创建新闻爬取器
    crawler = NewsCrawler(fund_type=args.fund_type, threads=args.threads)

    # 爬取新闻
    crawler.crawl(use_multi_thread=not args.single_thread)


if __name__ == '__main__':
    main()
