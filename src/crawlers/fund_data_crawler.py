#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import random
import argparse
import logging
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.logger import setup_logger
from utils.config import Config
from utils.helpers import retry, get_fund_categories, parse_fund_code

class FundDataCrawler:
    def __init__(self, category='stock', max_workers=10, delay=1):
        """
        初始化基金数据爬虫

        Args:
            category (str): 基金类别，如'stock'(股票型), 'mixed'(混合型), 'bond'(债券型), 'money'(货币型), 'qdii'(QDII)
            max_workers (int): 最大线程数
            delay (float): 请求延迟(秒)
        """
        self.category = category
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
        self.logger = setup_logger(f'FundDataCrawler-{category}')

        # 基金类别URL映射
        self.category_urls = {
            'stock': 'http://fund.eastmoney.com/js/fundcode_search.js',  # 股票型基金
            'mixed': 'http://fund.eastmoney.com/js/fundcode_search.js',  # 混合型基金
            'bond': 'http://fund.eastmoney.com/js/fundcode_search.js',  # 债券型基金
            'money': 'http://fund.eastmoney.com/js/fundcode_search.js',  # 货币型基金
            'qdii': 'http://fund.eastmoney.com/js/fundcode_search.js',  # QDII基金
        }

        # 东方财富基金数据URL模板
        self.fund_detail_url = 'http://fund.eastmoney.com/{code}.html'
        self.fund_history_url = 'http://fund.eastmoney.com/f10/jz_{code}.html'

    @retry(max_retries=3, delay=2)
    def get_fund_codes(self):
        """
        获取指定类别的基金代码列表

        Returns:
            list: 基金代码列表
        """
        try:
            url = self.category_urls[self.category]
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            # 解析JS文件中的基金代码
            js_content = response.text
            fund_codes = []

            # 提取基金代码
            start_marker = 'var r = "'
            end_marker = '";'
            if start_marker in js_content and end_marker in js_content:
                start_index = js_content.find(start_marker) + len(start_marker)
                end_index = js_content.find(end_marker, start_index)
                codes_str = js_content[start_index:end_index]
                fund_codes = codes_str.split(';')

                # 过滤无效代码
                fund_codes = [code.strip() for code in fund_codes if code.strip() and len(code.strip()) == 6]

            self.logger.info(f"获取到{len(fund_codes)}个{self.category}类基金代码")
            return fund_codes

        except Exception as e:
            self.logger.error(f"获取基金代码失败: {str(e)}")
            return []

    @retry(max_retries=3, delay=2)
    def get_fund_info(self, fund_code):
        """
        获取单个基金的详细信息

        Args:
            fund_code (str): 基金代码

        Returns:
            dict: 基金详细信息
        """
        try:
            # 构建基金详情页URL
            url = self.fund_detail_url.format(code=fund_code)

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

            # 基金基本信息
            fund_info = {
                'code': fund_code,
                'category': self.category,
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # 基金名称
            name_element = soup.find('h1', class_='fundDetail-tit')
            if name_element:
                fund_info['name'] = name_element.text.strip()
            else:
                fund_info['name'] = f'未知基金_{fund_code}'

            # 基金规模
            scale_element = soup.find('td', text='基金规模')
            if scale_element and scale_element.find_next_sibling('td'):
                fund_info['scale'] = scale_element.find_next_sibling('td').text.strip()
            else:
                fund_info['scale'] = '未知'

            # 基金公司
            company_element = soup.find('td', text='基金公司')
            if company_element and company_element.find_next_sibling('td'):
                fund_info['company'] = company_element.find_next_sibling('td').text.strip()
            else:
                fund_info['company'] = '未知'

            # 基金经理
            manager_element = soup.find('td', text='基金经理')
            if manager_element and manager_element.find_next_sibling('td'):
                fund_info['manager'] = manager_element.find_next_sibling('td').text.strip()
            else:
                fund_info['manager'] = '未知'

            # 成立日期
            establish_date_element = soup.find('td', text='成立日期')
            if establish_date_element and establish_date_element.find_next_sibling('td'):
                fund_info['establish_date'] = establish_date_element.find_next_sibling('td').text.strip()
            else:
                fund_info['establish_date'] = '未知'

            # 基金类型
            type_element = soup.find('td', text='基金类型')
            if type_element and type_element.find_next_sibling('td'):
                fund_info['type'] = type_element.find_next_sibling('td').text.strip()
            else:
                fund_info['type'] = '未知'

            # 基金状态
            status_element = soup.find('td', text='基金状态')
            if status_element and status_element.find_next_sibling('td'):
                fund_info['status'] = status_element.find_next_sibling('td').text.strip()
            else:
                fund_info['status'] = '未知'

            # 获取净值数据
            nav_data = self.get_fund_nav(fund_code)
            fund_info.update(nav_data)

            return fund_info

        except Exception as e:
            self.logger.error(f"获取基金{fund_code}信息失败: {str(e)}")
            return {
                'code': fund_code,
                'category': self.category,
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            }

    @retry(max_retries=3, delay=2)
    def get_fund_nav(self, fund_code, days=30):
        """
        获取基金净值数据

        Args:
            fund_code (str): 基金代码
            days (int): 获取最近多少天的数据

        Returns:
            dict: 净值数据
        """
        try:
            # 构建基金净值历史URL
            url = self.fund_history_url.format(code=fund_code)

            # 随机User-Agent
            headers = {
                'User-Agent': self.ua.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Connection': 'keep-alive',
                'Referer': self.fund_detail_url.format(code=fund_code)
            }

            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            # 使用BeautifulSoup解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # 查找表格
            table = soup.find('table', class_='w782')
            if not table:
                return {}

            # 解析表格行
            rows = table.find_all('tr')[1:]  # 跳过表头

            # 存储净值数据
            nav_data = {
                'nav_history': [],
                'latest_nav': None,
                'latest_nav_date': None,
                'latest_accum_nav': None,
                'nav_change': None,
                'nav_change_percent': None,
                'latest_week_return': None,
                'latest_month_return': None,
                'latest_three_month_return': None,
                'latest_year_return': None,
                'latest_three_year_return': None,
                'latest_since_inception_return': None
            }

            # 提取净值数据
            for row in rows[:days]:
                cols = row.find_all('td')
                if len(cols) >= 7:
                    date = cols[0].text.strip()
                    nav = cols[1].text.strip()
                    accum_nav = cols[2].text.strip()
                    daily_change = cols[3].text.strip()
                    daily_change_percent = cols[4].text.strip()

                    nav_data['nav_history'].append({
                        'date': date,
                        'nav': nav,
                        'accum_nav': accum_nav,
                        'daily_change': daily_change,
                        'daily_change_percent': daily_change_percent
                    })

            if nav_data['nav_history']:
                # 最新净值
                nav_data['latest_nav'] = nav_data['nav_history'][0]['nav']
                nav_data['latest_nav_date'] = nav_data['nav_history'][0]['date']
                nav_data['latest_accum_nav'] = nav_data['nav_history'][0]['accum_nav']

                # 净值变化
                if len(nav_data['nav_history']) > 1:
                    nav_data['nav_change'] = float(nav_data['nav_history'][0]['nav']) - float(nav_data['nav_history'][1]['nav'])
                    nav_data['nav_change_percent'] = nav_data['nav_history'][0]['daily_change_percent']

                # 计算收益率
                returns = self.calculate_returns(nav_data['nav_history'])
                nav_data.update(returns)

            return nav_data

        except Exception as e:
            self.logger.error(f"获取基金{fund_code}净值数据失败: {str(e)}")
            return {'error': str(e)}

    def calculate_returns(self, nav_history):
        """
        根据净值历史数据计算各种期限的收益率

        Args:
            nav_history (list): 净值历史数据

        Returns:
            dict: 各种期限的收益率
        """
        if not nav_history or len(nav_history) < 2:
            return {}

        returns = {}
        latest_nav = float(nav_history[0]['nav'])

        # 计算最近一周收益率
        week_ago_nav = None
        for i, nav in enumerate(nav_history):
            if i > 4:  # 跳过最近5个交易日（一周约5个交易日）
                week_ago_nav = float(nav['nav'])
                break

        if week_ago_nav:
            returns['latest_week_return'] = (latest_nav - week_ago_nav) / week_ago_nav * 100

        # 计算最近一月收益率
        month_ago_nav = None
        for i, nav in enumerate(nav_history):
            if i > 19:  # 跳过最近20个交易日（一月约20个交易日）
                month_ago_nav = float(nav['nav'])
                break

        if month_ago_nav:
            returns['latest_month_return'] = (latest_nav - month_ago_nav) / month_ago_nav * 100

        # 计算最近三月收益率
        three_month_ago_nav = None
        for i, nav in enumerate(nav_history):
            if i > 59:  # 跳过最近60个交易日（三月约60个交易日）
                three_month_ago_nav = float(nav['nav'])
                break

        if three_month_ago_nav:
            returns['latest_three_month_return'] = (latest_nav - three_month_ago_nav) / three_month_ago_nav * 100

        # 计算最近一年收益率
        year_ago_nav = None
        for i, nav in enumerate(nav_history):
            if i > 240:  # 跳过最近240个交易日（一年约240个交易日）
                year_ago_nav = float(nav['nav'])
                break

        if year_ago_nav:
            returns['latest_year_return'] = (latest_nav - year_ago_nav) / year_ago_nav * 100

        # 计算最近三年收益率
        three_year_ago_nav = None
        for i, nav in enumerate(nav_history):
            if i > 720:  # 跳过最近720个交易日（三年约720个交易日）
                three_year_ago_nav = float(nav['nav'])
                break

        if three_year_ago_nav:
            returns['latest_three_year_return'] = (latest_nav - three_year_ago_nav) / three_year_ago_nav * 100

        # 计算成立以来收益率
        if len(nav_history) > 1:
            inception_nav = float(nav_history[-1]['nav'])
            returns['latest_since_inception_return'] = (latest_nav - inception_nav) / inception_nav * 100

        return returns

    def crawl_all_funds(self, output_file=None, max_funds=None):
        """
        爬取所有指定类别的基金数据

        Args:
            output_file (str): 输出文件路径
            max_funds (int): 最大爬取基金数量，None表示全部

        Returns:
            list: 基金数据列表
        """
        try:
            # 获取基金代码列表
            fund_codes = self.get_fund_codes()

            # 限制爬取数量
            if max_funds and max_funds > 0:
                fund_codes = fund_codes[:max_funds]

            self.logger.info(f"开始爬取{len(fund_codes)}个{self.category}类基金数据")

            # 使用线程池并行爬取
            fund_data = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交任务
                futures = {executor.submit(self.get_fund_info, code): code for code in fund_codes}

                # 使用tqdm显示进度条
                with tqdm(total=len(futures), desc=f"爬取{self.category}类基金") as pbar:
                    for future in as_completed(futures):
                        fund_info = future.result()
                        fund_data.append(fund_info)
                        pbar.update(1)

                        # 随机延迟，防止请求过于频繁
                        time.sleep(self.delay)

            # 转换为DataFrame
            df = pd.DataFrame(fund_data)

            # 保存到文件
            if output_file:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                df.to_csv(output_file, index=False, encoding='utf-8-sig')
                self.logger.info(f"基金数据已保存到: {output_file}")

            return fund_data

        except Exception as e:
            self.logger.error(f"爬取{self.category}类基金数据失败: {str(e)}")
            return []


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='爬取基金数据')
    parser.add_argument('--category', type=str, default='stock', 
                        help='基金类别: stock(股票型), mixed(混合型), bond(债券型), money(货币型), qdii(QDII)')
    parser.add_argument('--output', type=str, required=True, 
                        help='输出文件路径')
    parser.add_argument('--max-funds', type=int, default=None,
                        help='最大爬取基金数量')
    parser.add_argument('--workers', type=int, default=10,
                        help='最大线程数')
    parser.add_argument('--delay', type=float, default=1.0,
                        help='请求延迟(秒)')

    args = parser.parse_args()

    # 创建爬虫实例
    crawler = FundDataCrawler(
        category=args.category,
        max_workers=args.workers,
        delay=args.delay
    )

    # 爬取基金数据
    crawler.crawl_all_funds(
        output_file=args.output,
        max_funds=args.max_funds
    )


if __name__ == '__main__':
    main()
atest_month_return'] = (latest_nav - month_ago_nav) / month_ago_nav * 100

        # 计算最近三月收益率
        three_month_ago_nav = None
        for i, nav in enumerate(nav_history):
            if i > 59:  # 跳过最近60个交易日（三月约60个交易日）
                three_month_ago_nav = float(nav['nav'])
                break

        if three_month_ago_nav:
            returns['latest_three_month_return'] = (latest_nav - three_month_ago_nav) / three_month_ago_nav * 100

        # 计算最近一年收益率
        year_ago_nav = None
        for i, nav in enumerate(nav_history):
            if i > 240:  # 跳过最近240个交易日（一年约240个交易日）
                year_ago_nav = float(nav['nav'])
                break

        if year_ago_nav:
            returns['latest_year_return'] = (latest_nav - year_ago_nav) / year_ago_nav * 100

        # 计算最近三年收益率
        three_year_ago_nav = None
        for i, nav in enumerate(nav_history):
            if i > 720:  # 跳过最近720个交易日（三年约720个交易日）
                three_year_ago_nav = float(nav['nav'])
                break

        if three_year_ago_nav:
            returns['latest_three_year_return'] = (latest_nav - three_year_ago_nav) / three_year_ago_nav * 100

        # 计算成立以来收益率
        if len(nav_history) > 1:
            inception_nav = float(nav_history[-1]['nav'])
            if inception_nav != 0:
                returns['latest_since_inception_return'] = (latest_nav - inception_nav) / inception_nav * 100

        return returns

    def crawl_all_funds(self, output_file, max_funds=100):
        """
        爬取指定类别的所有基金数据

        Args:
            output_file (str): 输出文件路径
            max_funds (int): 最大爬取基金数量
        """
        try:
            # 获取基金代码列表
            fund_codes = self.get_fund_codes()
            if not fund_codes:
                self.logger.error("未获取到基金代码")
                return

            # 限制爬取数量
            fund_codes = fund_codes[:max_funds]
            self.logger.info(f"开始爬取{len(fund_codes)}个{self.category}类基金数据")

            # 创建输出目录
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            # 使用线程池爬取基金数据
            fund_data = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交任务
                futures = {executor.submit(self.get_fund_info, code): code for code in fund_codes}

                # 处理结果
                for future in tqdm(as_completed(futures), total=len(futures), desc="爬取基金数据"):
                    code = futures[future]
                    try:
                        result = future.result()
                        fund_data.append(result)

                        # 随机延迟
                        time.sleep(random.uniform(self.delay * 0.5, self.delay * 1.5))
                    except Exception as e:
                        self.logger.error(f"处理基金{code}时出错: {str(e)}")

            # 转换为DataFrame并保存
            if fund_data:
                df = pd.DataFrame(fund_data)
                df.to_csv(output_file, index=False, encoding='utf-8-sig')
                self.logger.info(f"基金数据已保存到 {output_file}")
            else:
                self.logger.error("未获取到任何基金数据")

        except Exception as e:
            self.logger.error(f"爬取基金数据失败: {str(e)}")


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='爬取基金数据')
    parser.add_argument('--category', type=str, default='stock', 
                        choices=['stock', 'mixed', 'bond', 'money', 'qdii'],
                        help='基金类别')
    parser.add_argument('--output', type=str, default='data/raw/funds.csv',
                        help='输出文件路径')
    parser.add_argument('--max-funds', type=int, default=100,
                        help='最大爬取基金数量')
    parser.add_argument('--max-workers', type=int, default=10,
                        help='最大线程数')
    parser.add_argument('--delay', type=float, default=1,
                        help='请求延迟(秒)')

    args = parser.parse_args()

    # 创建爬虫实例
    crawler = FundDataCrawler(
        category=args.category,
        max_workers=args.max_workers,
        delay=args.delay
    )

    # 爬取基金数据
    crawler.crawl_all_funds(
        output_file=args.output,
        max_funds=args.max_funds
    )


if __name__ == '__main__':
    main()
