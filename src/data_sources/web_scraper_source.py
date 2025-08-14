"""网页爬虫数据源实现"""

import pandas as pd
import json
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from .base_source import BaseDataSource
from ..utils.logger import log_info, log_warning, log_error, log_debug

class WebScraperDataSource(BaseDataSource):
    """网页爬虫数据源"""

    def __init__(self):
        super().__init__("WebScraper", priority=2)
        self.base_urls = {
            'eastmoney': 'http://fund.eastmoney.com',
            'ttjj': 'http://fundgz.1234567.com.cn',
            'sina': 'http://vip.stock.finance.sina.com.cn',
            'tencent': 'http://qt.gtimg.cn'
        }

    def get_fund_list(self, limit: int = 100) -> List[Dict]:
        """从多个网站获取基金列表"""
        funds = []

        # 尝试从东方财富获取
        em_funds = self._get_eastmoney_fund_list(limit)
        funds.extend(em_funds)

        # 如果东方财富失败，尝试其他源
        if not funds:
            sina_funds = self._get_sina_fund_list(limit)
            funds.extend(sina_funds)

        return funds[:limit]

    def _get_eastmoney_fund_list(self, limit: int) -> List[Dict]:
        """从东方财富获取基金列表"""
        try:
            # 使用搜索接口
            search_url = "http://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx"
            params = {
                'm': 1,
                'key': '',
                'type': 'all'
            }

            response = self._make_request(search_url, params=params)
            if not response:
                return []

            # 解析响应
            text = response.text
            if 'var Datas=' in text:
                # 提取JSON数据
                json_match = re.search(r'var Datas=(\[.*?\]);', text)
                if json_match:
                    data = json.loads(json_match.group(1))
                    funds = []

                    for item in data[:limit]:
                        if len(item) >= 2:
                            funds.append({
                                'code': item[0],
                                'name': item[1],
                                'source': f"{self.name}-EastMoney"
                            })

                    return funds

            return []

        except Exception as e:
            log_error(f"东方财富基金列表获取失败: {e}")
            return []

    def _get_sina_fund_list(self, limit: int) -> List[Dict]:
        """从新浪获取基金列表"""
        try:
            # 新浪基金列表API
            url = "http://vip.stock.finance.sina.com.cn/fund_center/data/jsonp.php/IO.XSRV2.CallbackList['hLfu5s99aaIUp7D4']/NetValueReturn_Service.NetValueReturnOpen"
            params = {
                'page': 1,
                'num': limit,
                'sort': 'nav',
                'asc': 0,
                'ccode': '',
                'type2': '',
                'type3': ''
            }

            response = self._make_request(url, params=params)
            if not response:
                return []

            # 解析JSONP响应
            text = response.text
            json_match = re.search(r'\[(.*)\]', text)
            if json_match:
                data_str = '[' + json_match.group(1) + ']'
                data = json.loads(data_str)
                funds = []

                for item in data:
                    if isinstance(item, dict) and 'symbol' in item and 'name' in item:
                        funds.append({
                            'code': item['symbol'],
                            'name': item['name'],
                            'source': f"{self.name}-Sina"
                        })

                return funds

            return []

        except Exception as e:
            log_error(f"新浪基金列表获取失败: {e}")
            return []

    def get_fund_info(self, fund_code: str) -> Dict:
        """获取基金基本信息"""
        # 尝试多个数据源
        info = self._get_eastmoney_fund_info(fund_code)
        if not info:
            info = self._get_ttjj_fund_info(fund_code)

        return info

    def _get_eastmoney_fund_info(self, fund_code: str) -> Dict:
        """从东方财富获取基金信息"""
        try:
            url = f"http://fund.eastmoney.com/{fund_code}.html"
            response = self._make_request(url)
            if not response:
                return {}

            soup = BeautifulSoup(response.text, 'html.parser')
            info = {'code': fund_code, 'source': f"{self.name}-EastMoney"}

            # 提取基金名称
            title_elem = soup.find('title')
            if title_elem:
                title = title_elem.get_text()
                name_match = re.search(r'(.*?)\((\d+)\)', title)
                if name_match:
                    info['name'] = name_match.group(1)

            # 提取基金信息表格
            info_tables = soup.find_all('table', class_='info')
            for table in info_tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        key = cells[0].get_text().strip()
                        value = cells[1].get_text().strip()

                        if '基金类型' in key:
                            info['type'] = value
                        elif '成立日期' in key:
                            info['establish_date'] = value
                        elif '基金规模' in key:
                            info['scale'] = value
                        elif '基金公司' in key:
                            info['company'] = value

            return info

        except Exception as e:
            log_error(f"东方财富获取基金{fund_code}信息失败: {e}")
            return {}

    def _get_ttjj_fund_info(self, fund_code: str) -> Dict:
        """从天天基金获取基金信息"""
        try:
            # 天天基金实时数据接口
            url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"

            response = self._make_request(url)
            if not response:
                return {}

            # 解析JSONP响应
            text = response.text
            json_match = re.search(r'jsonpgz\((.*?)\);', text)
            if json_match:
                data = json.loads(json_match.group(1))

                return {
                    'code': data.get('fundcode', fund_code),
                    'name': data.get('name', ''),
                    'nav': float(data.get('dwjz', 0)),
                    'nav_date': data.get('jzrq', ''),
                    'estimated_nav': float(data.get('gsz', 0)),
                    'estimated_return': float(data.get('gszzl', 0)),
                    'source': f"{self.name}-TTJJ"
                }

            return {}

        except Exception as e:
            log_error(f"天天基金获取基金{fund_code}信息失败: {e}")
            return {}

    def get_fund_nav_history(self, fund_code: str, days: int = 365) -> pd.DataFrame:
        """获取基金净值历史"""
        # 尝试多个数据源
        hist_df = self._get_eastmoney_nav_history(fund_code, days)
        if hist_df.empty:
            hist_df = self._get_sina_nav_history(fund_code, days)

        return hist_df

    def _get_eastmoney_nav_history(self, fund_code: str, days: int) -> pd.DataFrame:
        """从东方财富获取净值历史"""
        try:
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            url = "http://api.fund.eastmoney.com/f10/lsjz"
            params = {
                'fundCode': fund_code,
                'pageIndex': 1,
                'pageSize': days,
                'startDate': start_date.strftime('%Y-%m-%d'),
                'endDate': end_date.strftime('%Y-%m-%d')
            }

            response = self._make_request(url, params=params)
            if not response:
                return pd.DataFrame()

            data = response.json()
            if data.get('Data') and data['Data'].get('LSJZList'):
                records = []
                for item in data['Data']['LSJZList']:
                    records.append({
                        'date': pd.to_datetime(item['FSRQ']),
                        'nav': float(item['DWJZ']) if item['DWJZ'] else 0,
                        'accumulated_nav': float(item['LJJZ']) if item['LJJZ'] else 0,
                        'daily_return': float(item['JZZZL']) if item['JZZZL'] else 0
                    })

                df = pd.DataFrame(records)
                return df.sort_values('date').reset_index(drop=True)

            return pd.DataFrame()

        except Exception as e:
            log_error(f"东方财富获取基金{fund_code}历史数据失败: {e}")
            return pd.DataFrame()

    def _get_sina_nav_history(self, fund_code: str, days: int) -> pd.DataFrame:
        """从新浪获取净值历史"""
        try:
            url = f"http://stock.finance.sina.com.cn/fundInfo/api/openapi.php/CaihuiFundInfoService.getNav"
            params = {
                'symbol': fund_code,
                'datefrom': (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'),
                'dateto': datetime.now().strftime('%Y-%m-%d')
            }

            response = self._make_request(url, params=params)
            if not response:
                return pd.DataFrame()

            data = response.json()
            if data.get('result') and data['result'].get('data'):
                records = []
                for item in data['result']['data']:
                    records.append({
                        'date': pd.to_datetime(item['fbrq']),
                        'nav': float(item['jjjz']) if item['jjjz'] else 0,
                        'accumulated_nav': float(item['ljjz']) if item['ljjz'] else 0,
                        'daily_return': 0  # 新浪数据可能不包含日收益率
                    })

                df = pd.DataFrame(records)
                # 计算日收益率
                if not df.empty:
                    df = df.sort_values('date')
                    df['daily_return'] = df['nav'].pct_change() * 100
                    df['daily_return'] = df['daily_return'].fillna(0)

                return df.reset_index(drop=True)

            return pd.DataFrame()

        except Exception as e:
            log_error(f"新浪获取基金{fund_code}历史数据失败: {e}")
            return pd.DataFrame()

    def get_fund_holdings(self, fund_code: str) -> Dict:
        """获取基金持仓信息"""
        return self._get_eastmoney_holdings(fund_code)

    def _get_eastmoney_holdings(self, fund_code: str) -> Dict:
        """从东方财富获取持仓信息"""
        try:
            url = f"http://fund.eastmoney.com/f10/ccmx_{fund_code}.html"
            response = self._make_request(url)
            if not response:
                return {}

            soup = BeautifulSoup(response.text, 'html.parser')
            holdings = []

            # 查找持仓表格
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) > 1:
                    # 检查是否是股票持仓表
                    header = rows[0].get_text()
                    if '股票名称' in header or '持仓占比' in header:
                        for row in rows[1:11]:  # 前10大持仓
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 3:
                                holding = {
                                    'stock_code': cells[0].get_text().strip(),
                                    'stock_name': cells[1].get_text().strip(),
                                    'hold_ratio': 0,
                                    'source': f"{self.name}-EastMoney"
                                }

                                # 提取持仓比例
                                ratio_text = cells[2].get_text().strip()
                                ratio_match = re.search(r'(\d+\.?\d*)%?', ratio_text)
                                if ratio_match:
                                    holding['hold_ratio'] = float(ratio_match.group(1))

                                if holding['stock_code'] and holding['stock_name']:
                                    holdings.append(holding)

            return {
                'top_holdings': holdings,
                'update_time': datetime.now().isoformat(),
                'source': f"{self.name}-EastMoney"
            }

        except Exception as e:
            log_error(f"东方财富获取基金{fund_code}持仓失败: {e}")
            return {}
