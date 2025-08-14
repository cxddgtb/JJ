import re
import json
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from .base_crawler import BaseCrawler
from config import FUND_TYPES

class EastMoneyCrawler(BaseCrawler):
    """天天基金网爬虫"""

    def __init__(self):
        super().__init__("EastMoney", "https://fund.eastmoney.com/")
        self.fund_list_url = "https://fund.eastmoney.com/js/fundcode_search.js"
        self.fund_detail_url_template = "https://fund.eastmoney.com/{code}.html"
        self.fund_nav_url_template = "https://fund.eastmoney.com/f10/F10DataApi.aspx?type=lsjz&code={code}&page={page}&per={per}"
        self.fund_position_url_template = "https://fund.eastmoney.com/{code}.html"
        self.fund_news_url = "https://fund.eastmoney.com/news/default.aspx"
        self.fund_rank_url = "https://fund.eastmoney.com/data/fundranking.html"

    def crawl_fund_list(self):
        """爬取基金列表"""
        self.logger.info("开始爬取基金列表...")
        response = self.get_page(self.fund_list_url)
        text = response.text

        # 解析基金列表数据
        pattern = r'var r = (.*);'
        match = re.search(pattern, text)
        if not match:
            self.logger.error("无法解析基金列表数据")
            return []

        try:
            fund_data = json.loads(match.group(1))
            funds = []
            for item in fund_data:
                fund = {
                    'code': item[0],
                    'name': item[2],
                    'type': item[3],
                    'type_name': self._get_fund_type_name(item[3]),
                    'source': self.name
                }
                funds.append(fund)

            self.logger.info(f"成功爬取 {len(funds)} 只基金信息")
            return funds
        except Exception as e:
            self.logger.error(f"解析基金列表数据出错: {str(e)}")
            return []

    def _get_fund_type_name(self, type_code):
        """根据类型代码获取类型名称"""
        for type_name, code in FUND_TYPES.items():
            if code in type_code:
                return type_name
        return "其他"

    def crawl_fund_detail(self, fund_code):
        """爬取基金详情"""
        self.logger.info(f"开始爬取基金 {fund_code} 的详情...")
        detail_url = self.fund_detail_url_template.format(code=fund_code)
        response = self.get_page(detail_url)
        soup = self.parse_html(response.text)

        try:
            # 基金基本信息
            fund_info = self._parse_fund_info(soup, fund_code)

            # 基金净值数据
            nav_data = self._parse_fund_nav(fund_code)

            # 基金持仓数据
            position_data = self._parse_fund_position(soup, fund_code)

            # 合并所有数据
            fund_detail = {
                'code': fund_code,
                'info': fund_info,
                'nav': nav_data,
                'position': position_data,
                'source': self.name,
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            self.logger.info(f"成功爬取基金 {fund_code} 的详情")
            return fund_detail
        except Exception as e:
            self.logger.error(f"爬取基金 {fund_code} 详情出错: {str(e)}")
            return None

    def _parse_fund_info(self, soup, fund_code):
        """解析基金基本信息"""
        fund_info = {}

        # 基金名称和代码
        fund_name_element = soup.find('h1', class_='fundDetail-title')
        if fund_name_element:
            fund_info['name'] = fund_name_element.text.strip()
        else:
            fund_info['name'] = fund_code

        # 基金类型
        type_element = soup.find('div', class_='fundInfoItem').find('td', text=re.compile(r'基金类型'))
        if type_element and type_element.find_next_sibling('td'):
            fund_info['type'] = type_element.find_next_sibling('td').text.strip()

        # 基金规模
        scale_element = soup.find('div', class_='fundInfoItem').find('td', text=re.compile(r'资产规模'))
        if scale_element and scale_element.find_next_sibling('td'):
            fund_info['scale'] = scale_element.find_next_sibling('td').text.strip()

        # 基金经理
        manager_element = soup.find('div', class_='fundInfoItem').find('td', text=re.compile(r'基金经理'))
        if manager_element and manager_element.find_next_sibling('td'):
            fund_info['manager'] = manager_element.find_next_sibling('td').text.strip()

        # 成立日期
        date_element = soup.find('div', class_='fundInfoItem').find('td', text=re.compile(r'成立日期'))
        if date_element and date_element.find_next_sibling('td'):
            fund_info['establish_date'] = date_element.find_next_sibling('td').text.strip()

        # 最新净值和日期
        nav_element = soup.find('dd', class_='dataNums')
        if nav_element:
            fund_info['latest_nav'] = nav_element.text.strip()

        nav_date_element = soup.find('p', class_='data-tips')
        if nav_date_element:
            fund_info['nav_date'] = nav_date_element.text.strip()

        # 累计净值
        total_nav_element = soup.find('dd', class_='dataNums2')
        if total_nav_element:
            fund_info['total_nav'] = total_nav_element.text.strip()

        # 日增长率
        growth_element = soup.find('span', class_='ui-font-middle')
        if growth_element:
            fund_info['daily_growth'] = growth_element.text.strip()

        # 近一年收益率
        year_return_element = soup.find('span', class_='ui-font-middle', id='year')
        if year_return_element:
            fund_info['year_return'] = year_return_element.text.strip()

        return fund_info

    def _parse_fund_nav(self, fund_code, pages=1):
        """解析基金净值数据"""
        nav_data = []

        for page in range(1, pages + 1):
            url = self.fund_nav_url_template.format(code=fund_code, page=page, per=20)
            response = self.get_page(url)

            try:
                # 解析JSON数据
                data = json.loads(response.text)
                content = data['content']

                # 解析每一行净值数据
                for item in content.split(','):
                    parts = item.split('|')
                    if len(parts) >= 6:
                        nav_record = {
                            'date': parts[0],
                            'nav': parts[1],
                            'accum_nav': parts[2],
                            'growth_rate': parts[3],
                            'subscription_status': parts[4],
                            'redemption_status': parts[5]
                        }
                        nav_data.append(nav_record)
            except Exception as e:
                self.logger.error(f"解析基金 {fund_code} 净值数据出错: {str(e)}")

        return nav_data

    def _parse_fund_position(self, soup, fund_code):
        """解析基金持仓数据"""
        position_data = {
            'stock_positions': [],
            'bond_positions': [],
            'industry_positions': []
        }

        try:
            # 股票持仓
            stock_table = soup.find('table', id='stockposition')
            if stock_table:
                rows = stock_table.find_all('tr')[1:]  # 跳过表头
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        position = {
                            'code': cols[0].text.strip(),
                            'name': cols[1].text.strip(),
                            'proportion': cols[2].text.strip(),
                            'shares': cols[3].text.strip()
                        }
                        position_data['stock_positions'].append(position)

            # 债券持仓
            bond_table = soup.find('table', id='bondposition')
            if bond_table:
                rows = bond_table.find_all('tr')[1:]  # 跳过表头
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        position = {
                            'code': cols[0].text.strip(),
                            'name': cols[1].text.strip(),
                            'proportion': cols[2].text.strip(),
                            'value': cols[3].text.strip()
                        }
                        position_data['bond_positions'].append(position)

            # 行业配置
            industry_table = soup.find('table', id='industryAllocate')
            if industry_table:
                rows = industry_table.find_all('tr')[1:]  # 跳过表头
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        position = {
                            'industry': cols[0].text.strip(),
                            'proportion': cols[1].text.strip(),
                            'value': cols[2].text.strip()
                        }
                        position_data['industry_positions'].append(position)

        except Exception as e:
            self.logger.error(f"解析基金 {fund_code} 持仓数据出错: {str(e)}")

        return position_data

    def crawl_fund_news(self, limit=50):
        """爬取基金新闻"""
        self.logger.info("开始爬取基金新闻...")
        news_list = []

        try:
            response = self.get_page(self.fund_news_url)
            soup = self.parse_html(response.text)

            # 获取新闻列表
            news_items = soup.find_all('div', class_='newsItem')[:limit]

            for item in news_items:
                title_element = item.find('a')
                if not title_element:
                    continue

                title = title_element.text.strip()
                url = title_element.get('href')

                if not url.startswith('http'):
                    url = self.base_url + url

                # 获取新闻详情
                news_detail = self._crawl_news_detail(url)

                news = {
                    'title': title,
                    'url': url,
                    'detail': news_detail,
                    'source': self.name,
                    'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                news_list.append(news)

            self.logger.info(f"成功爬取 {len(news_list)} 条基金新闻")
            return news_list

        except Exception as e:
            self.logger.error(f"爬取基金新闻出错: {str(e)}")
            return []

    def _crawl_news_detail(self, url):
        """爬取新闻详情"""
        try:
            response = self.get_page(url)
            soup = self.parse_html(response.text)

            # 获取新闻内容
            content_element = soup.find('div', class_='Body')
            if content_element:
                # 移除不需要的元素
                for element in content_element.find_all(['script', 'style']):
                    element.decompose()

                # 提取文本
                content = content_element.get_text().strip()
                return content

            return ""

        except Exception as e:
            self.logger.error(f"爬取新闻详情出错: {str(e)}")
            return ""

    def crawl_fund_rank(self, fund_type=None, limit=100):
        """爬取基金排名"""
        self.logger.info("开始爬取基金排名...")
        rank_list = []

        try:
            response = self.get_page(self.fund_rank_url)
            soup = self.parse_html(response.text)

            # 获取排名表格
            table = soup.find('table', class_='table')
            if not table:
                self.logger.error("未找到基金排名表格")
                return []

            rows = table.find_all('tr')[1:limit+1]  # 跳过表头

            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 10:
                    rank_item = {
                        'rank': cols[0].text.strip(),
                        'code': cols[1].text.strip(),
                        'name': cols[2].text.strip(),
                        'date': cols[3].text.strip(),
                        'unit_nav': cols[4].text.strip(),
                        'accum_nav': cols[5].text.strip(),
                        'daily_growth': cols[6].text.strip(),
                        'week_return': cols[7].text.strip(),
                        'month_return': cols[8].text.strip(),
                        'year_return': cols[9].text.strip(),
                        'source': self.name,
                        'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }

                    # 如果指定了基金类型，则进行过滤
                    if fund_type is None or fund_type in rank_item['name']:
                        rank_list.append(rank_item)

            self.logger.info(f"成功爬取 {len(rank_list)} 条基金排名数据")
            return rank_list

        except Exception as e:
            self.logger.error(f"爬取基金排名出错: {str(e)}")
            return []
