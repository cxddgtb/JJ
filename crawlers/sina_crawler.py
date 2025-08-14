import re
import json
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from .base_crawler import BaseCrawler
from config import FUND_TYPES

class SinaCrawler(BaseCrawler):
    """新浪财经爬虫"""

    def __init__(self):
        super().__init__("SinaFinance", "https://finance.sina.com.cn/fund/")
        self.fund_list_url = "https://finance.sina.com.cn/fund/fundcode/index.shtml"
        self.fund_detail_url_template = "https://finance.sina.com.cn/fund/quotes/{code}/bc.shtml"
        self.fund_nav_url_template = "https://finance.sina.com.cn/fund/quotes/{code}/hist.shtml"
        self.fund_news_url = "https://finance.sina.com.cn/fund/"
        self.fund_rank_url = "https://finance.sina.com.cn/fund/rank/index.shtml"

    def crawl_fund_list(self):
        """爬取基金列表"""
        self.logger.info("开始爬取基金列表...")
        response = self.get_page(self.fund_list_url)
        soup = self.parse_html(response.text)

        try:
            funds = []
            # 查找基金列表表格
            table = soup.find('table', class_='table_fund')
            if not table:
                self.logger.error("无法找到基金列表表格")
                return []

            rows = table.find_all('tr')[1:]  # 跳过表头
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    code = cols[0].text.strip()
                    name = cols[1].text.strip()
                    type_name = cols[2].text.strip()

                    fund = {
                        'code': code,
                        'name': name,
                        'type': self._get_fund_type_code(type_name),
                        'type_name': type_name,
                        'source': self.name
                    }
                    funds.append(fund)

            self.logger.info(f"成功爬取 {len(funds)} 只基金信息")
            return funds
        except Exception as e:
            self.logger.error(f"爬取基金列表出错: {str(e)}")
            return []

    def _get_fund_type_code(self, type_name):
        """根据类型名称获取类型代码"""
        for name, code in FUND_TYPES.items():
            if name in type_name:
                return code
        return "other"

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
        fund_name_element = soup.find('h1', class_='fund_name')
        if fund_name_element:
            fund_info['name'] = fund_name_element.text.strip()
        else:
            fund_info['name'] = fund_code

        # 基金类型
        type_element = soup.find('td', text=re.compile(r'基金类型'))
        if type_element and type_element.find_next_sibling('td'):
            fund_info['type'] = type_element.find_next_sibling('td').text.strip()

        # 基金规模
        scale_element = soup.find('td', text=re.compile(r'基金规模'))
        if scale_element and scale_element.find_next_sibling('td'):
            fund_info['scale'] = scale_element.find_next_sibling('td').text.strip()

        # 基金经理
        manager_element = soup.find('td', text=re.compile(r'基金经理'))
        if manager_element and manager_element.find_next_sibling('td'):
            fund_info['manager'] = manager_element.find_next_sibling('td').text.strip()

        # 成立日期
        date_element = soup.find('td', text=re.compile(r'成立日期'))
        if date_element and date_element.find_next_sibling('td'):
            fund_info['establish_date'] = date_element.find_next_sibling('td').text.strip()

        # 最新净值和日期
        nav_element = soup.find('div', class_='fund_data_num')
        if nav_element:
            fund_info['latest_nav'] = nav_element.text.strip()

        nav_date_element = soup.find('div', class_='fund_data_date')
        if nav_date_element:
            fund_info['nav_date'] = nav_date_element.text.strip()

        # 累计净值
        total_nav_element = soup.find('div', class_='fund_total_num')
        if total_nav_element:
            fund_info['total_nav'] = total_nav_element.text.strip()

        # 日增长率
        growth_element = soup.find('div', class_='fund_data_rate')
        if growth_element:
            fund_info['daily_growth'] = growth_element.text.strip()

        # 近一年收益率
        year_return_element = soup.find('div', class_='fund_year_rate')
        if year_return_element:
            fund_info['year_return'] = year_return_element.text.strip()

        return fund_info

    def _parse_fund_nav(self, fund_code, pages=1):
        """解析基金净值数据"""
        nav_data = []

        for page in range(1, pages + 1):
            url = self.fund_nav_url_template.format(code=fund_code)
            response = self.get_page(url)
            soup = self.parse_html(response.text)

            try:
                # 获取净值表格
                table = soup.find('table', class_='fund_hist_data')
                if not table:
                    continue

                rows = table.find_all('tr')[1:]  # 跳过表头
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 5:
                        nav_record = {
                            'date': cols[0].text.strip(),
                            'nav': cols[1].text.strip(),
                            'accum_nav': cols[2].text.strip(),
                            'growth_rate': cols[3].text.strip(),
                            'status': cols[4].text.strip()
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
            stock_table = soup.find('table', class_='stock_position')
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
            bond_table = soup.find('table', class_='bond_position')
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
            industry_table = soup.find('table', class_='industry_position')
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
            news_items = soup.find_all('div', class_='news-item')[:limit]

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
            content_element = soup.find('div', class_='article')
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
            table = soup.find('table', class_='fund_rank_table')
            if not table:
                self.logger.error("无法找到基金排名表格")
                return []

            rows = table.find_all('tr')[1:limit+1]  # 跳过表头，限制数量
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 6:
                    rank = {
                        'rank': cols[0].text.strip(),
                        'code': cols[1].text.strip(),
                        'name': cols[2].text.strip(),
                        'type': cols[3].text.strip(),
                        'recent_nav': cols[4].text.strip(),
                        'year_return': cols[5].text.strip()
                    }
                    rank_list.append(rank)

            self.logger.info(f"成功爬取 {len(rank_list)} 条基金排名数据")
            return rank_list

        except Exception as e:
            self.logger.error(f"爬取基金排名出错: {str(e)}")
            return []
