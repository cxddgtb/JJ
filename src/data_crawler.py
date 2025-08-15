#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据爬取模块
从多个来源获取基金数据和指标
"""

import os
import re
import json
import time
import asyncio
import aiohttp
import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from fake_useragent import UserAgent
import logging
from datetime import datetime, timedelta
import argparse
from typing import List, Dict, Any, Optional, Union

from config import (
    API_CONFIG, OUTPUT_DIR, RAW_DATA_DIR, LOG_CONFIG,
    INDICATORS_CONFIG, FUND_TYPES
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

class DataCrawler:
    """数据爬取类"""

    def __init__(self, fund_type: str = 'mixed', threads: int = 8):
        """
        初始化数据爬取器

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
        self.data_output_dir = os.path.join(RAW_DATA_DIR, 'funds')
        os.makedirs(self.data_output_dir, exist_ok=True)

        # 初始化各数据源的客户端
        self._init_clients()

    def _init_clients(self):
        """初始化各数据源的客户端"""
        self.clients = {}

        # Tushare客户端
        try:
            import tushare as ts
            ts.set_token(API_CONFIG['tushare']['token'])
            self.clients['tushare'] = ts.pro_api()
            logger.info("Tushare客户端初始化成功")
        except Exception as e:
            logger.warning(f"Tushare客户端初始化失败: {e}")

        # Akshare客户端
        try:
            import akshare as ak
            self.clients['akshare'] = ak
            logger.info("Akshare客户端初始化成功")
        except Exception as e:
            logger.warning(f"Akshare客户端初始化失败: {e}")

        # Baostock客户端
        try:
            import baostock as bs
            bs.login()
            self.clients['baostock'] = bs
            logger.info("Baostock客户端初始化成功")
        except Exception as e:
            logger.warning(f"Baostock客户端初始化失败: {e}")

        # JQData客户端
        try:
            import jqdatasdk as jq
            jq.auth(API_CONFIG['jqdata']['username'], API_CONFIG['jqdata']['password'])
            self.clients['jqdata'] = jq
            logger.info("JQData客户端初始化成功")
        except Exception as e:
            logger.warning(f"JQData客户端初始化失败: {e}")

    def _get_free_apis(self) -> List[Dict[str, str]]:
        """获取免费API列表"""
        free_apis = []

        try:
            with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'free_apis.txt'), 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 2:
                            free_apis.append({
                                'name': parts[0].strip(),
                                'url': parts[1].strip(),
                                'key': parts[2].strip() if len(parts) > 2 else '',
                                'type': parts[3].strip() if len(parts) > 3 else 'json'
                            })
        except Exception as e:
            logger.warning(f"读取免费API列表失败: {e}")

        return free_apis

    def crawl_fund_list(self) -> pd.DataFrame:
        """
        爬取基金列表

        Returns:
            基金列表DataFrame
        """
        logger.info(f"开始爬取{self.fund_type}基金列表")

        all_funds = []

        # 尝试从不同数据源获取基金列表
        for source, client in self.clients.items():
            try:
                if source == 'tushare':
                    # 获取基金基本信息
                    df = client.fund_basic(exchange='', list_status='L', 
                                          fields='fund_code,fund_name,fund_management,fund_scale')
                    # 过滤基金类型
                    if self.fund_type != 'mixed':
                        df = df[df['fund_type'] == self.fund_type]

                    all_funds.append(df)
                    logger.info(f"从{Tushare}获取到{len(df)}只基金")

                elif source == 'akshare':
                    # 获取基金基本信息
                    df = ak.fund_em_fund_info()
                    # 过滤基金类型
                    if self.fund_type != 'mixed':
                        df = df[df['基金类型'] == self.fund_type]

                    all_funds.append(df)
                    logger.info(f"从{Akshare}获取到{len(df)}只基金")

                elif source == 'baostock':
                    # 获取基金基本信息
                    rs = client.query_all_fund_data()
                    if rs.error_code == '0':
                        funds = []
                        while (rs.error_code == '0') & rs.next():
                            funds.append(rs.get_row_data())

                        df = pd.DataFrame(funds, columns=rs.fields)
                        # 过滤基金类型
                        if self.fund_type != 'mixed':
                            df = df[df['fund_type'] == self.fund_type]

                        all_funds.append(df)
                        logger.info(f"从{Baostock}获取到{len(df)}只基金")

                elif source == 'jqdata':
                    # 获取基金基本信息
                    df = jq.get_fundamentals(jq.all_instruments('Fund'))
                    # 过滤基金类型
                    if self.fund_type != 'mixed':
                        df = df[df['type'] == self.fund_type]

                    all_funds.append(df)
                    logger.info(f"从{JQData}获取到{len(df)}只基金")

            except Exception as e:
                logger.warning(f"从{source}获取基金列表失败: {e}")
                continue

        # 合并所有基金列表
        if all_funds:
            funds_df = pd.concat(all_funds, ignore_index=True)
            # 去重
            funds_df = funds_df.drop_duplicates(subset=['fund_code'] if 'fund_code' in funds_df.columns else ['code'])

            # 保存基金列表
            output_file = os.path.join(self.data_output_dir, f'fund_list_{self.fund_type}.csv')
            funds_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            logger.info(f"基金列表已保存至: {output_file}")

            return funds_df
        else:
            logger.error("未能从任何数据源获取基金列表")
            return pd.DataFrame()

    def crawl_fund_nav(self, fund_codes: List[str]) -> Dict[str, pd.DataFrame]:
        """
        爬取基金净值数据

        Args:
            fund_codes: 基金代码列表

        Returns:
            基金净值数据字典
        """
        logger.info(f"开始爬取{len(fund_codes)}只基金的净值数据")

        nav_data = {}

        # 多线程爬取
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = []

            for fund_code in fund_codes:
                future = executor.submit(self._crawl_single_fund_nav, fund_code)
                futures.append(future)

            for i, future in enumerate(as_completed(futures)):
                try:
                    fund_code, nav_df = future.result()
                    if nav_df is not None and not nav_df.empty:
                        nav_data[fund_code] = nav_df
                        logger.info(f"已完成{i+1}/{len(fund_codes)}只基金的净值爬取: {fund_code}")
                except Exception as e:
                    logger.warning(f"爬取基金净值失败: {e}")

        # 保存净值数据
        if nav_data:
            os.makedirs(os.path.join(self.data_output_dir, 'nav'), exist_ok=True)
            for fund_code, nav_df in nav_data.items():
                output_file = os.path.join(self.data_output_dir, 'nav', f'{fund_code}_nav.csv')
                nav_df.to_csv(output_file, index=False, encoding='utf-8-sig')

        return nav_data

    def _crawl_single_fund_nav(self, fund_code: str) -> tuple:
        """
        爬取单只基金的净值数据

        Args:
            fund_code: 基金代码

        Returns:
            (基金代码, 净值DataFrame)
        """
        nav_df = None

        # 尝试从不同数据源获取净值数据
        for source, client in self.clients.items():
            try:
                if source == 'tushare':
                    # 获取基金净值
                    df = client.fund_nav(fund_code=fund_code, 
                                       start_date='20200101', 
                                       end_date=datetime.now().strftime('%Y%m%d'))
                    if not df.empty:
                        nav_df = df
                        break

                elif source == 'akshare':
                    # 获取基金净值
                    df = ak.fund_nav_em(fund=fund_code)
                    if not df.empty:
                        nav_df = df
                        break

                elif source == 'baostock':
                    # 获取基金净值
                    rs = client.query_history_k_data_plus(fund_code, "date,open,high,low,close,volume,amount", 
                                                         start_date='2020-01-01', 
                                                         end_date=datetime.now().strftime('%Y-%m-%d'))
                    if rs.error_code == '0':
                        data = []
                        while (rs.error_code == '0') & rs.next():
                            data.append(rs.get_row_data())

                        df = pd.DataFrame(data, columns=rs.fields)
                        if not df.empty:
                            nav_df = df
                            break

                elif source == 'jqdata':
                    # 获取基金净值
                    df = jq.get_price(fund_code, 
                                     start_date='2020-01-01', 
                                     end_date=datetime.now(),
                                     frequency='daily')
                    if not df.empty:
                        nav_df = df
                        break

            except Exception as e:
                logger.debug(f"从{source}获取{fund_code}净值数据失败: {e}")
                continue

        # 尝试使用免费API
        if nav_df is None:
            try:
                from utils import get_free_apis
                free_apis = get_free_apis()
                for api in free_apis:
                    try:
                        # 构建请求URL
                        url = api['url'].replace('{fund_code}', fund_code)

                        # 发送请求
                        response = self.session.get(url, timeout=API_CONFIG['free_apis']['timeout'])
                        if response.status_code == 200:
                            if api['type'] == 'json':
                                data = response.json()
                            else:
                                data = response.text

                            # 解析数据
                            # 根据API类型解析数据
                            if isinstance(data, str) and ',' in data:
                                # CSV格式数据
                                try:
                                    df = pd.read_csv(pd.StringIO(data))
                                    if not df.empty:
                                        nav_df = df
                                        break
                                except Exception as e:
                                    logger.debug(f"解析CSV数据失败: {e}")
                            elif isinstance(data, dict):
                                # JSON格式数据
                                if 'data' in data:
                                    df = pd.DataFrame(data['data'])
                                elif 'nav' in data:
                                    df = pd.DataFrame(data['nav'])
                                elif 'list' in data:
                                    df = pd.DataFrame(data['list'])
                                else:
                                    df = pd.DataFrame([data])
                                
                                if not df.empty:
                                    nav_df = df
                                    break
                    except Exception as e:
                        logger.debug(f"从免费API获取{fund_code}净值数据失败: {e}")
                        continue
            except Exception as e:
                logger.warning(f"使用免费API获取净值数据失败: {e}")

                except Exception as e:
                    logger.debug(f"从免费API获取{fund_code}净值数据失败: {e}")
                    continue

        return fund_code, nav_df

    def crawl_fund_indicators(self, fund_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        爬取基金指标数据

        Args:
            fund_codes: 基金代码列表

        Returns:
            基金指标数据字典
        """
        logger.info(f"开始爬取{len(fund_codes)}只基金的指标数据")

        indicators_data = {}

        # 多线程爬取
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = []

            for fund_code in fund_codes:
                future = executor.submit(self._crawl_single_fund_indicators, fund_code)
                futures.append(future)

            for i, future in enumerate(as_completed(futures)):
                try:
                    fund_code, indicators = future.result()
                    if indicators:
                        indicators_data[fund_code] = indicators
                        logger.info(f"已完成{i+1}/{len(fund_codes)}只基金的指标爬取: {fund_code}")
                except Exception as e:
                    logger.warning(f"爬取基金指标失败: {e}")

        # 保存指标数据
        if indicators_data:
            os.makedirs(os.path.join(self.data_output_dir, 'indicators'), exist_ok=True)
            output_file = os.path.join(self.data_output_dir, 'indicators', f'indicators_{self.fund_type}.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(indicators_data, f, ensure_ascii=False, indent=2)

        return indicators_data

    def _crawl_single_fund_indicators(self, fund_code: str) -> tuple:
        """
        爬取单只基金的指标数据

        Args:
            fund_code: 基金代码

        Returns:
            (基金代码, 指标字典)
        """
        indicators = {}

        # 尝试从不同数据源获取指标数据
        for source, client in self.clients.items():
            try:
                if source == 'tushare':
                    # 获取基金指标
                    df = client.fund_portfolio(fund_code=fund_code, 
                                             start_date='20200101', 
                                             end_date=datetime.now().strftime('%Y%m%d'))
                    if not df.empty:
                        indicators['portfolio'] = df.to_dict('records')

                    df = client.fund_performance(fund_code=fund_code, 
                                              start_date='20200101', 
                                              end_date=datetime.now().strftime('%Y%m%d'))
                    if not df.empty:
                        indicators['performance'] = df.to_dict('records')

                    if indicators:
                        break

                elif source == 'akshare':
                    # 获取基金指标
                    df = ak.fund_em_fund_info_detail(fund=fund_code)
                    if not df.empty:
                        indicators['detail'] = df.to_dict('records')

                    df = ak.fund_em_fund_info_holder(fund=fund_code)
                    if not df.empty:
                        indicators['holder'] = df.to_dict('records')

                    if indicators:
                        break

                elif source == 'baostock':
                    # 获取基金指标
                    rs = client.query_history_k_data_plus(fund_code, "date,pe,pb", 
                                                         start_date='2020-01-01', 
                                                         end_date=datetime.now().strftime('%Y-%m-%d'))
                    if rs.error_code == '0':
                        data = []
                        while (rs.error_code == '0') & rs.next():
                            data.append(rs.get_row_data())

                        df = pd.DataFrame(data, columns=rs.fields)
                        if not df.empty:
                            indicators['pe_pb'] = df.to_dict('records')
                            break

                elif source == 'jqdata':
                    # 获取基金指标
                    df = jq.get_fundamentals(jq.Fund(fund_code))
                    if not df.empty:
                        indicators['fundamentals'] = df.to_dict('records')

                    df = jq.get_fundamentals(jq.FundHolder(fund_code))
                    if not df.empty:
                        indicators['holders'] = df.to_dict('records')

                    if indicators:
                        break

            except Exception as e:
                logger.debug(f"从{source}获取{fund_code}指标数据失败: {e}")
                continue

        # 尝试使用免费API
        if not indicators:
            free_apis = self._get_free_apis()
            for api in free_apis:
                try:
                    # 构建请求URL
                    url = api['url'].replace('{fund_code}', fund_code)

                    # 发送请求
                    response = self.session.get(url, timeout=API_CONFIG['free_apis']['timeout'])
                    if response.status_code == 200:
                        if api['type'] == 'json':
                            data = response.json()
                        else:
                            data = response.text

                        # 解析数据
                        # 这里需要根据具体API的响应格式进行解析
                        if isinstance(data, dict) and 'indicators' in data:
                            indicators = data['indicators']
                            break

                except Exception as e:
                    logger.debug(f"从免费API获取{fund_code}指标数据失败: {e}")
                    continue

        return fund_code, indicators

    def crawl_fund_news(self, fund_codes: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        爬取基金相关新闻

        Args:
            fund_codes: 基金代码列表

        Returns:
            基金新闻字典
        """
        logger.info(f"开始爬取{len(fund_codes)}只基金的新闻")

        fund_news = {}

        # 多线程爬取
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = []

            for fund_code in fund_codes:
                future = executor.submit(self._crawl_single_fund_news, fund_code)
                futures.append(future)

            for i, future in enumerate(as_completed(futures)):
                try:
                    fund_code, news = future.result()
                    if news:
                        fund_news[fund_code] = news
                        logger.info(f"已完成{i+1}/{len(fund_codes)}只基金的新闻爬取: {fund_code}")
                except Exception as e:
                    logger.warning(f"爬取基金新闻失败: {e}")

        # 尝试从免费API获取更多新闻
        try:
            from utils import get_free_apis
            free_apis = get_free_apis()
            if free_apis:
                logger.info(f"从{len(free_apis)}个免费API获取基金新闻")
                for api in free_apis:
                    try:
                        # 构建请求URL
                        url = api['url'].replace('{fund_code}', fund_codes[0])
                        
                        # 发送请求
                        response = self.session.get(url, timeout=10)
                        if response.status_code == 200:
                            if api['type'] == 'json':
                                data = response.json()
                            else:
                                data = response.text
                            
                            # 解析数据
                            if isinstance(data, dict) and 'news' in data:
                                for fund_code in fund_codes:
                                    if fund_code not in fund_news:
                                        fund_news[fund_code] = []
                                    
                                    for item in data['news']:
                                        fund_news[fund_code].append({
                                            'title': item.get('title', ''),
                                            'content': item.get('content', ''),
                                            'publish_time': item.get('date', ''),
                                            'source': api['name'],
                                            'type': 'news'
                                        })
                    except Exception as e:
                        logger.debug(f"从免费API获取基金新闻失败: {e}")
                        continue
        except Exception as e:
            logger.warning(f"使用免费API获取基金新闻失败: {e}")

        # 保存新闻数据
        if fund_news:
            os.makedirs(os.path.join(self.data_output_dir, 'news'), exist_ok=True)
            output_file = os.path.join(self.data_output_dir, 'news', f'fund_news_{self.fund_type}.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(fund_news, f, ensure_ascii=False, indent=2)

        return fund_news

    def _crawl_single_fund_news(self, fund_code: str) -> tuple:
        """
        爬取单只基金的新闻

        Args:
            fund_code: 基金代码

        Returns:
            (基金代码, 新闻列表)
        """
        news = []

        # 尝试从不同数据源获取新闻
        for source, client in self.clients.items():
            try:
                if source == 'tushare':
                    # 获取基金公告
                    df = client.fund_announcement(fund_code=fund_code, 
                                                 start_date='20200101', 
                                                 end_date=datetime.now().strftime('%Y%m%d'))
                    if not df.empty:
                        for _, row in df.iterrows():
                            news.append({
                                'title': row['title'],
                                'content': row['content'],
                                'publish_time': row['announcement_date'],
                                'source': 'Tushare',
                                'type': 'announcement'
                            })
                        break

                elif source == 'akshare':
                    # 获取基金新闻
                    df = ak.fund_em_news_info(symbol=fund_code)
                    if not df.empty:
                        for _, row in df.iterrows():
                            news.append({
                                'title': row['title'],
                                'content': row['content'],
                                'publish_time': row['date'],
                                'source': 'Akshare',
                                'type': 'news'
                            })
                        break

                elif source == 'baostock':
                    # 获取基金新闻
                    rs = client.query_history_k_data_plus(fund_code, "date,news", 
                                                         start_date='2020-01-01', 
                                                         end_date=datetime.now().strftime('%Y-%m-%d'))
                    if rs.error_code == '0':
                        while (rs.error_code == '0') & rs.next():
                            news.append({
                                'title': f'{fund_code}相关新闻',
                                'content': rs.get_data_field('news'),
                                'publish_time': rs.get_data_field('date'),
                                'source': 'Baostock',
                                'type': 'news'
                            })
                        break

                elif source == 'jqdata':
                    # 获取基金新闻
                    df = jq.run_query(jq.query(jq.News).filter(
                        jq.News.code == fund_code
                    ).limit(100))
                    if not df.empty:
                        for _, row in df.iterrows():
                            news.append({
                                'title': row['title'],
                                'content': row['content'],
                                'publish_time': row['display_time'],
                                'source': 'JQData',
                                'type': 'news'
                            })
                        break

            except Exception as e:
                logger.debug(f"从{source}获取{fund_code}新闻失败: {e}")
                continue

        # 尝试使用免费API
        if not news:
            free_apis = self._get_free_apis()
            for api in free_apis:
                try:
                    # 构建请求URL
                    url = api['url'].replace('{fund_code}', fund_code)

                    # 发送请求
                    response = self.session.get(url, timeout=API_CONFIG['free_apis']['timeout'])
                    if response.status_code == 200:
                        if api['type'] == 'json':
                            data = response.json()
                        else:
                            data = response.text

                        # 解析数据
                        if isinstance(data, dict) and 'news' in data:
                            for item in data['news']:
                                news.append({
                                    'title': item.get('title', ''),
                                    'content': item.get('content', ''),
                                    'publish_time': item.get('date', ''),
                                    'source': api['name'],
                                    'type': 'news'
                                })
                            break

                except Exception as e:
                    logger.debug(f"从免费API获取{fund_code}新闻失败: {e}")
                    continue

        return fund_code, news

    def run(self):
        """运行数据爬取流程"""
        logger.info(f"开始爬取{self.fund_type}基金数据")

        # 爬取基金列表
        funds_df = self.crawl_fund_list()
        if funds_df.empty:
            logger.error("未能获取基金列表，终止爬取")
            return

        # 获取基金代码列表
        fund_codes = funds_df['fund_code'].tolist() if 'fund_code' in funds_df.columns else funds_df['code'].tolist()

        # 爬取基金净值数据
        nav_data = self.crawl_fund_nav(fund_codes)

        # 爬取基金指标数据
        indicators_data = self.crawl_fund_indicators(fund_codes)

        # 爬取基金新闻
        fund_news = self.crawl_fund_news(fund_codes)

        logger.info(f"{self.fund_type}基金数据爬取完成")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='基金数据爬取工具')
    parser.add_argument('--fund-type', type=str, default='mixed', 
                       help='基金类型 (mixed, stock, bond, money_market, qdii)')
    parser.add_argument('--threads', type=int, default=8, 
                       help='线程数')

    args = parser.parse_args()

    crawler = DataCrawler(fund_type=args.fund_type, threads=args.threads)
    crawler.run()
