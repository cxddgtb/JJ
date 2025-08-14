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
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
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
