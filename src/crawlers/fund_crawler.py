#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
基金数据爬虫模块
"""

import os
import json
import time
import logging
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from ..utils.config import FUND_CATEGORIES, DATA_DIR, CRAWLER_CONFIG
from ..utils.thread_pool import run_with_thread_pool

logger = logging.getLogger(__name__)

class FundCrawler:
    """基金数据爬虫类"""

    def __init__(self):
        """初始化基金数据爬虫"""
        self.data_dir = os.path.join(DATA_DIR, 'funds')
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
            'Referer': 'https://fund.eastmoney.com/'
        }

        logger.info("基金数据爬虫初始化完成")

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

    def _get_fund_list_by_category(self, category: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        根据基金类别获取基金列表

        Args:
            category: 基金类别配置

        Returns:
            基金列表
        """
        category_name = category['name']
        category_code = category['code']
        limit = category['limit']

        logger.info(f"获取 {category_name} 基金列表...")

        # 东方财富网基金列表URL
        url = f"https://fund.eastmoney.com/data/fundranking.html#tall;c0;cna;o;pn=10000"

        response = self._make_request(url)
        if not response:
            return []

        # 使用正则表达式提取基金数据
        import re
        pattern = r'var db = ({.*?});'
        match = re.search(pattern, response.text)

        if not match:
            logger.warning(f"无法从 {url} 提取基金数据")
            return []

        try:
            data = json.loads(match.group(1))
            funds_data = data.get('datas', [])

            # 解析基金数据
            fund_list = []
            count = 0

            for fund_data in funds_data:
                if count >= limit:
                    break

                # 检查基金类型
                fund_type = fund_data[3]  # 基金类型在数据中的位置
                if category_code not in fund_type.lower():
                    continue

                # 解析基金信息
                fund_code = fund_data[0]
                fund_name = fund_data[1]

                fund_list.append({
                    'code': fund_code,
                    'name': fund_name,
                    'type': fund_type,
                    'category': category_name,
                    'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

                count += 1

            logger.info(f"成功获取 {len(fund_list)} 只 {category_name} 基金")
            return fund_list

        except Exception as e:
            logger.error(f"解析 {category_name} 基金列表失败: {str(e)}", exc_info=True)
            return []

    def _get_fund_detail(self, fund: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取基金详细信息

        Args:
            fund: 基金基本信息

        Returns:
            基金详细信息
        """
        fund_code = fund['code']
        fund_name = fund['name']

        logger.debug(f"获取基金 {fund_name}({fund_code}) 的详细信息...")

        # 基金详情页URL
        url = f"https://fund.eastmoney.com/{fund_code}.html"

        response = self._make_request(url)
        if not response:
            return fund

        soup = BeautifulSoup(response.text, 'lxml')

        try:
            # 提取基金基本信息
            info_items = soup.select('.infoOfFund td')

            # 基金净值
            net_asset_value = None
            if info_items and len(info_items) > 0:
                net_asset_value = info_items[0].get_text(strip=True)

            # 累计净值
            accumulated_net_value = None
            if info_items and len(info_items) > 1:
                accumulated_net_value = info_items[1].get_text(strip=True)

            # 日增长率
            daily_growth_rate = None
            daily_growth_rate_elem = soup.select_one('.dataOfFund .dataNum02')
            if daily_growth_rate_elem:
                daily_growth_rate = daily_growth_rate_elem.get_text(strip=True)

            # 近一年收益率
            one_year_return = None
            return_rate_elems = soup.select('.dataOfFund .dataNums span')
            if return_rate_elems and len(return_rate_elems) > 2:
                one_year_return = return_rate_elems[2].get_text(strip=True)

            # 基金规模
            fund_scale = None
            fund_scale_elem = soup.select_one('.fundDetail-tit:contains("基金规模") + .fundDetail-item')
            if fund_scale_elem:
                fund_scale = fund_scale_elem.get_text(strip=True)

            # 成立日期
            establishment_date = None
            est_date_elem = soup.select_one('.fundDetail-tit:contains("成立日期") + .fundDetail-item')
            if est_date_elem:
                establishment_date = est_date_elem.get_text(strip=True)

            # 更新基金信息
            fund.update({
                'net_asset_value': net_asset_value,
                'accumulated_net_value': accumulated_net_value,
                'daily_growth_rate': daily_growth_rate,
                'one_year_return': one_year_return,
                'fund_scale': fund_scale,
                'establishment_date': establishment_date
            })

            # 获取历史净值数据
            self._get_fund_nav_history(fund)

            return fund

        except Exception as e:
            logger.error(f"获取基金 {fund_name}({fund_code}) 详情失败: {str(e)}", exc_info=True)
            return fund

    def _get_fund_nav_history(self, fund: Dict[str, Any]) -> None:
        """
        获取基金历史净值数据

        Args:
            fund: 基金信息
        """
        fund_code = fund['code']

        # 计算日期范围（获取最近一年的数据）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        # 东方财富网历史净值API
        url = f"https://api.fund.eastmoney.com/f10/lsjz?callback=jQuery&fundCode={fund_code}&pageIndex=1&pageSize=1000&startDate={start_date_str}&endDate={end_date_str}"

        response = self._make_request(url)
        if not response:
            return

        try:
            # 提取JSON数据
            import re
            pattern = r'jQuery\((.*?)\)'
            match = re.search(pattern, response.text)

            if not match:
                logger.warning(f"无法从 {url} 提取历史净值数据")
                return

            data = json.loads(match.group(1))

            # 解析净值数据
            nav_data = data.get('data', {}).get('lsjzList', [])

            nav_history = []
            for item in nav_data:
                nav_history.append({
                    'date': item.get('FSRQ'),
                    'net_asset_value': item.get('NAV'),
                    'accumulated_net_value': item.get('NAVCHGRT'),
                    'growth_rate': item.get('JZZZL')
                })

            # 按日期排序
            nav_history.sort(key=lambda x: x['date'])

            # 添加到基金信息中
            fund['nav_history'] = nav_history

            logger.debug(f"成功获取基金 {fund_code} 的 {len(nav_history)} 条历史净值数据")

        except Exception as e:
            logger.error(f"解析基金 {fund_code} 历史净值数据失败: {str(e)}", exc_info=True)

    def crawl_funds_by_category(self, category: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        爬取指定类别的基金数据

        Args:
            category: 基金类别配置

        Returns:
            基金数据列表
        """
        logger.info(f"开始爬取 {category['name']} 基金数据...")

        # 获取基金列表
        fund_list = self._get_fund_list_by_category(category)

        if not fund_list:
            logger.warning(f"未找到 {category['name']} 基金列表")
            return []

        # 使用线程池获取基金详细信息
        logger.info(f"开始爬取 {len(fund_list)} 只 {category['name']} 基金的详细信息...")
        fund_list = run_with_thread_pool(self._get_fund_detail, fund_list)

        # 过滤掉没有详细信息的基金
        fund_list = [fund for fund in fund_list if fund.get('net_asset_value')]

        logger.info(f"成功爬取 {len(fund_list)} 只 {category['name']} 基金数据")
        return fund_list

    def crawl_all_funds(self) -> List[Dict[str, Any]]:
        """
        爬取所有类别的基金数据

        Returns:
            所有基金数据列表
        """
        logger.info("开始爬取所有类别的基金数据...")

        all_funds = []
        for category in FUND_CATEGORIES:
            try:
                funds_by_category = self.crawl_funds_by_category(category)
                all_funds.extend(funds_by_category)
            except Exception as e:
                logger.error(f"爬取 {category['name']} 基金数据失败: {str(e)}", exc_info=True)

        # 保存基金数据
        self.save_fund_data(all_funds)

        logger.info(f"成功爬取共 {len(all_funds)} 只基金数据")
        return all_funds

    def save_fund_data(self, fund_list: List[Dict[str, Any]]) -> None:
        """
        保存基金数据

        Args:
            fund_list: 基金数据列表
        """
        if not fund_list:
            logger.warning("基金数据列表为空，不保存数据")
            return

        # 按日期保存
        today = datetime.now().strftime('%Y%m%d')
        filename = os.path.join(self.data_dir, f'funds_{today}.json')

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(fund_list, f, ensure_ascii=False, indent=2)
            logger.info(f"基金数据已保存到 {filename}")
        except Exception as e:
            logger.error(f"保存基金数据失败: {str(e)}", exc_info=True)
