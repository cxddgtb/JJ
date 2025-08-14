"""
基金数据爬虫 - 专门用于爬取基金相关数据
"""
import re
import json
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin
import akshare as ak
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

from .base_crawler import BaseCrawler, CrawlResult
from ..utils.logger import log_info, log_warning, log_error, log_debug, create_task_logger
from ..config import DATA_SOURCES, DEFAULT_FUNDS

class FundCrawler(BaseCrawler):
    """基金数据爬虫"""

    def __init__(self, **kwargs):
        super().__init__(name="FundCrawler", **kwargs)
        self.fund_data = {}
        self.news_data = []
        self.market_data = {}

    def get_fund_list(self, fund_type=None, top_n=1000) -> List[Dict]:
        """获取基金列表"""
        task_logger = create_task_logger("获取基金列表")
        task_logger.start()

        try:
            # 方法1: 从东方财富获取
            fund_list = self._get_eastmoney_fund_list(fund_type, top_n)

            # 方法2: 从akshare获取补充数据
            if len(fund_list) < top_n // 2:
                ak_funds = self._get_akshare_fund_list(fund_type, top_n)
                fund_list.extend(ak_funds)

            # 去重并排序
            unique_funds = {}
            for fund in fund_list:
                code = fund.get('code')
                if code and code not in unique_funds:
                    unique_funds[code] = fund

            result = list(unique_funds.values())[:top_n]
            task_logger.success(f"获取到 {len(result)} 只基金")
            return result

        except Exception as e:
            task_logger.error(e, "获取基金列表失败")
            return []

    def _get_eastmoney_fund_list(self, fund_type=None, top_n=1000) -> List[Dict]:
        """从东方财富获取基金列表"""
        funds = []

        try:
            # 获取基金代码列表
            url = DATA_SOURCES['eastmoney']['fund_list']
            result = self.get(url)

            if result.success:
                # 解析JavaScript数据
                content = result.content
                # 提取基金代码数据
                pattern = r'var r = (\[.*?\]);'
                match = re.search(pattern, content)

                if match:
                    fund_data = eval(match.group(1))  # 注意：生产环境应该用更安全的解析方法

                    for item in fund_data[:top_n]:
                        if len(item) >= 4:
                            funds.append({
                                'code': item[0],
                                'name': item[2],
                                'type': item[3] if len(item) > 3 else '混合型',
                                'source': 'eastmoney'
                            })

            # 获取更详细的基金排行数据
            ranking_url = DATA_SOURCES['tiantian']['fund_ranking']
            soup = self.get_soup(ranking_url)

            if soup:
                # 解析基金排行表格
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')[1:]  # 跳过表头

                    for row in rows[:top_n]:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 3:
                            try:
                                code_cell = cells[2]
                                code_link = code_cell.find('a')
                                if code_link and code_link.text:
                                    code = code_link.text.strip()
                                    name = cells[3].text.strip() if len(cells) > 3 else ''

                                    funds.append({
                                        'code': code,
                                        'name': name,
                                        'type': '未知',
                                        'source': 'tiantian'
                                    })
                            except Exception as e:
                                log_debug(f"解析基金行数据失败: {e}")
                                continue

        except Exception as e:
            log_error(f"获取东方财富基金列表失败: {e}")

        return funds

    def _get_akshare_fund_list(self, fund_type=None, top_n=1000) -> List[Dict]:
        """从akshare获取基金列表"""
        funds = []

        try:
            # 获取公募基金列表
            # 尝试多种akshare基金列表获取方法
            try:
                fund_df = ak.fund_name_em()
            except AttributeError:
                try:
                    fund_df = ak.fund_em_fund_name()
                except AttributeError:
                    try:
                        fund_df = ak.fund_basic_info_em()
                    except AttributeError:
                        log_warning("akshare基金列表API不可用，使用默认列表")
                        return []

            if not fund_df.empty:
                for _, row in fund_df.head(top_n).iterrows():
                    funds.append({
                        'code': str(row['基金代码']),
                        'name': str(row['基金简称']),
                        'type': str(row.get('基金类型', '未知')),
                        'source': 'akshare'
                    })

        except Exception as e:
            log_warning(f"akshare获取基金列表失败: {e}")

        return funds

    def get_fund_detail(self, fund_code: str) -> Dict:
        """获取基金详细信息"""
        fund_info = {}

        try:
            # 方法1: 从东方财富API获取实时数据
            detail_url = DATA_SOURCES['eastmoney']['fund_detail'].format(fund_code)
            result = self.get(detail_url)

            if result.success:
                # 解析JSONP数据
                content = result.content
                # 移除JSONP包装
                json_str = re.sub(r'^jsonpgz\((.*)\);?$', r'\1', content)

                try:
                    data = json.loads(json_str)
                    fund_info.update({
                        'code': fund_code,
                        'name': data.get('name', ''),
                        'current_price': float(data.get('dwjz', 0)),  # 当前净值
                        'price_change': float(data.get('jzzzl', 0)),  # 涨跌幅
                        'update_time': data.get('gztime', ''),
                        'estimate_price': float(data.get('gsz', 0)),  # 估算净值
                        'estimate_change': float(data.get('gszzl', 0)),  # 估算涨跌幅
                        'source': 'eastmoney_api'
                    })
                except json.JSONDecodeError:
                    log_warning(f"解析基金数据JSON失败: {fund_code}")

            # 方法2: 从akshare获取历史数据
            try:
                # 获取基金历史净值 - 尝试多种akshare历史数据获取方法
                try:
                    hist_df = ak.fund_open_fund_info_em(fund=fund_code, indicator="累计净值走势")
                except (AttributeError, Exception):
                    try:
                        hist_df = ak.fund_em_open_fund_info(fund=fund_code, indicator="累计净值走势")
                    except (AttributeError, Exception):
                        try:
                            hist_df = ak.fund_etf_hist_em(symbol=fund_code)
                        except (AttributeError, Exception):
                            log_warning(f"无法从akshare获取基金{fund_code}历史数据")
                            return pd.DataFrame()

                if not hist_df.empty:
                    latest = hist_df.iloc[-1]
                    fund_info.update({
                        'net_value': float(latest.get('净值', 0)),
                        'accumulated_value': float(latest.get('累计净值', 0)),
                        'date': latest.get('净值日期', ''),
                        'daily_change': float(latest.get('日增长率', 0))
                    })

                # 获取基金基本信息
                # 尝试获取基金规模信息
                try:
                    info_df = ak.fund_open_fund_info_em(fund=fund_code, indicator="基金规模走势")
                except (AttributeError, Exception):
                    try:
                        info_df = ak.fund_em_open_fund_info(fund=fund_code, indicator="基金规模走势")
                    except (AttributeError, Exception):
                        info_df = pd.DataFrame()
                if not info_df.empty:
                    latest_info = info_df.iloc[-1]
                    fund_info.update({
                        'fund_size': float(latest_info.get('基金规模', 0)),
                        'size_date': latest_info.get('统计日期', '')
                    })

            except Exception as e:
                log_debug(f"akshare获取基金{fund_code}详情失败: {e}")

            # 方法3: 获取基金经理信息
            manager_info = self._get_fund_manager_info(fund_code)
            if manager_info:
                fund_info.update(manager_info)

            # 方法4: 获取持仓信息
            holdings_info = self._get_fund_holdings(fund_code)
            if holdings_info:
                fund_info.update(holdings_info)

        except Exception as e:
            log_error(f"获取基金{fund_code}详情失败: {e}")

        return fund_info

    def _get_fund_manager_info(self, fund_code: str) -> Dict:
        """获取基金经理信息"""
        try:
            # 尝试获取基金经理信息
            try:
                manager_df = ak.fund_open_fund_info_em(fund=fund_code, indicator="基金经理")
            except (AttributeError, Exception):
                try:
                    manager_df = ak.fund_em_open_fund_info(fund=fund_code, indicator="基金经理")
                except (AttributeError, Exception):
                    manager_df = pd.DataFrame()

            if not manager_df.empty:
                managers = []
                for _, row in manager_df.iterrows():
                    managers.append({
                        'name': row.get('基金经理', ''),
                        'start_date': row.get('任职日期', ''),
                        'tenure_return': float(row.get('任职回报', 0))
                    })

                return {'managers': managers}

        except Exception as e:
            log_debug(f"获取基金{fund_code}经理信息失败: {e}")

        return {}

    def _get_fund_holdings(self, fund_code: str) -> Dict:
        """获取基金持仓信息"""
        try:
            # 获取股票持仓
            # 尝试获取股票持仓信息
            try:
                stock_holdings = ak.fund_open_fund_info_em(fund=fund_code, indicator="股票持仓")
            except (AttributeError, Exception):
                try:
                    stock_holdings = ak.fund_em_open_fund_info(fund=fund_code, indicator="股票持仓")
                except (AttributeError, Exception):
                    stock_holdings = pd.DataFrame()
            holdings_info = {}

            if not stock_holdings.empty:
                top_holdings = []
                for _, row in stock_holdings.head(10).iterrows():
                    top_holdings.append({
                        'stock_code': row.get('股票代码', ''),
                        'stock_name': row.get('股票名称', ''),
                        'hold_ratio': float(row.get('持仓占比', 0)),
                        'hold_amount': float(row.get('持股数', 0))
                    })

                holdings_info['top_stock_holdings'] = top_holdings
                holdings_info['stock_position_ratio'] = sum(h['hold_ratio'] for h in top_holdings[:5])

            return holdings_info

        except Exception as e:
            log_debug(f"获取基金{fund_code}持仓信息失败: {e}")
            return {}

    def get_fund_history(self, fund_code: str, days=365) -> pd.DataFrame:
        """获取基金历史数据"""
        try:
            # 计算开始日期
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 从akshare获取历史净值
            hist_df = ak.fund_em_open_fund_info(
                fund=fund_code, 
                indicator="累计净值走势"
            )

            if not hist_df.empty:
                # 数据清洗和格式化
                hist_df['净值日期'] = pd.to_datetime(hist_df['净值日期'])
                hist_df = hist_df.sort_values('净值日期')

                # 筛选时间范围
                mask = (hist_df['净值日期'] >= start_date) & (hist_df['净值日期'] <= end_date)
                hist_df = hist_df.loc[mask]

                # 重命名列
                hist_df = hist_df.rename(columns={
                    '净值日期': 'date',
                    '净值': 'nav',
                    '累计净值': 'accumulated_nav',
                    '日增长率': 'daily_return'
                })

                # 转换数据类型
                hist_df['nav'] = pd.to_numeric(hist_df['nav'], errors='coerce')
                hist_df['accumulated_nav'] = pd.to_numeric(hist_df['accumulated_nav'], errors='coerce')
                hist_df['daily_return'] = pd.to_numeric(hist_df['daily_return'], errors='coerce')

                return hist_df

        except Exception as e:
            log_error(f"获取基金{fund_code}历史数据失败: {e}")

        return pd.DataFrame()

    def get_fund_news(self, keywords=None, days=7) -> List[Dict]:
        """获取基金相关新闻"""
        task_logger = create_task_logger("获取基金新闻")
        task_logger.start()

        all_news = []
        keywords = keywords or ['基金', '投资', '理财', '净值', '基金经理']

        try:
            # 从多个新闻源获取
            news_sources = [
                self._get_eastmoney_news,
                self._get_sina_news,
                self._get_163_news,
                self._get_snowball_news
            ]

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [
                    executor.submit(source, keywords, days) 
                    for source in news_sources
                ]

                for future in as_completed(futures):
                    try:
                        news_list = future.result(timeout=60)
                        all_news.extend(news_list)
                    except Exception as e:
                        log_warning(f"获取新闻源失败: {e}")

            # 去重和排序
            unique_news = {}
            for news in all_news:
                title = news.get('title', '')
                if title and title not in unique_news:
                    unique_news[title] = news

            result = list(unique_news.values())
            result.sort(key=lambda x: x.get('publish_time', ''), reverse=True)

            task_logger.success(f"获取到 {len(result)} 条新闻")
            return result

        except Exception as e:
            task_logger.error(e, "获取基金新闻失败")
            return []

    def _get_eastmoney_news(self, keywords: List[str], days: int) -> List[Dict]:
        """从东方财富获取新闻"""
        news_list = []

        try:
            news_url = DATA_SOURCES['eastmoney']['fund_news']
            soup = self.get_soup(news_url)

            if soup:
                # 查找新闻列表
                news_items = soup.find_all(['div', 'li'], class_=re.compile(r'news|item|list'))

                for item in news_items[:50]:
                    try:
                        title_elem = item.find(['a', 'h3', 'h4'])
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            link = title_elem.get('href', '')

                            if link and not link.startswith('http'):
                                link = urljoin(news_url, link)

                            # 检查关键词
                            if any(keyword in title for keyword in keywords):
                                time_elem = item.find(['span', 'time'], class_=re.compile(r'time|date'))
                                publish_time = time_elem.get_text(strip=True) if time_elem else ''

                                news_list.append({
                                    'title': title,
                                    'link': link,
                                    'publish_time': publish_time,
                                    'source': '东方财富',
                                    'keywords': [kw for kw in keywords if kw in title]
                                })
                    except Exception as e:
                        log_debug(f"解析东方财富新闻项失败: {e}")
                        continue

        except Exception as e:
            log_warning(f"获取东方财富新闻失败: {e}")

        return news_list

    def _get_sina_news(self, keywords: List[str], days: int) -> List[Dict]:
        """从新浪财经获取新闻"""
        news_list = []

        try:
            news_url = DATA_SOURCES['sina']['fund_news']
            soup = self.get_soup(news_url)

            if soup:
                # 查找新闻链接
                links = soup.find_all('a', href=True)

                for link in links[:100]:
                    try:
                        title = link.get_text(strip=True)
                        href = link['href']

                        if title and any(keyword in title for keyword in keywords):
                            if not href.startswith('http'):
                                href = urljoin(news_url, href)

                            news_list.append({
                                'title': title,
                                'link': href,
                                'publish_time': '',
                                'source': '新浪财经',
                                'keywords': [kw for kw in keywords if kw in title]
                            })
                    except Exception as e:
                        log_debug(f"解析新浪新闻项失败: {e}")
                        continue

        except Exception as e:
            log_warning(f"获取新浪新闻失败: {e}")

        return news_list

    def _get_163_news(self, keywords: List[str], days: int) -> List[Dict]:
        """从网易财经获取新闻"""
        news_list = []

        try:
            news_url = DATA_SOURCES['163']['fund_news']
            soup = self.get_soup(news_url)

            if soup:
                # 查找新闻项
                news_items = soup.find_all(['div', 'li'], class_=re.compile(r'news|item'))

                for item in news_items[:50]:
                    try:
                        title_elem = item.find('a')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            link = title_elem.get('href', '')

                            if title and any(keyword in title for keyword in keywords):
                                if not link.startswith('http'):
                                    link = urljoin(news_url, link)

                                news_list.append({
                                    'title': title,
                                    'link': link,
                                    'publish_time': '',
                                    'source': '网易财经',
                                    'keywords': [kw for kw in keywords if kw in title]
                                })
                    except Exception as e:
                        log_debug(f"解析网易新闻项失败: {e}")
                        continue

        except Exception as e:
            log_warning(f"获取网易新闻失败: {e}")

        return news_list

    def _get_snowball_news(self, keywords: List[str], days: int) -> List[Dict]:
        """从雪球获取讨论"""
        news_list = []

        try:
            # 雪球需要特殊处理，可能需要模拟浏览器
            discuss_url = DATA_SOURCES['snowball']['fund_discuss']

            # 这里可以添加雪球API调用或爬取逻辑
            # 由于雪球有反爬机制，这里简化处理
            log_debug("雪球数据获取需要特殊处理，暂时跳过")

        except Exception as e:
            log_warning(f"获取雪球讨论失败: {e}")

        return news_list

    def get_market_sentiment(self) -> Dict:
        """获取市场情绪指标"""
        sentiment_data = {}

        try:
            # 获取A股指数数据
            indices = ['000001', '399001', '399006']  # 上证、深证、创业板

            for index_code in indices:
                try:
                    index_df = ak.stock_zh_index_daily_em(symbol=index_code)
                    if not index_df.empty:
                        latest = index_df.iloc[-1]
                        sentiment_data[f'index_{index_code}'] = {
                            'close': float(latest['close']),
                            'change_pct': float(latest['close'] / latest['open'] - 1) * 100,
                            'volume': float(latest['volume']),
                            'date': str(latest['date'])
                        }
                except Exception as e:
                    log_debug(f"获取指数{index_code}数据失败: {e}")

            # 获取恐慌贪婪指数（如果有API）
            try:
                # 这里可以添加恐慌贪婪指数的获取逻辑
                pass
            except Exception as e:
                log_debug(f"获取恐慌贪婪指数失败: {e}")

            # 获取资金流向
            try:
                money_flow = ak.stock_market_fund_flow()
                if not money_flow.empty:
                    latest_flow = money_flow.iloc[-1]
                    sentiment_data['money_flow'] = {
                        'main_net_inflow': float(latest_flow.get('主力净流入', 0)),
                        'retail_net_inflow': float(latest_flow.get('散户净流入', 0)),
                        'date': str(latest_flow.get('日期', ''))
                    }
            except Exception as e:
                log_debug(f"获取资金流向失败: {e}")

        except Exception as e:
            log_error(f"获取市场情绪失败: {e}")

        return sentiment_data

    def crawl_all_fund_data(self, fund_codes=None, include_history=True) -> Dict:
        """爬取所有基金数据"""
        task_logger = create_task_logger("爬取所有基金数据")
        task_logger.start()

        fund_codes = fund_codes or DEFAULT_FUNDS
        all_data = {
            'funds': {},
            'news': [],
            'market_sentiment': {},
            'crawl_time': datetime.now().isoformat()
        }

        try:
            # 并发获取基金数据
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交基金详情任务
                fund_futures = {
                    executor.submit(self.get_fund_detail, code): code 
                    for code in fund_codes
                }

                # 提交历史数据任务（如果需要）
                history_futures = {}
                if include_history:
                    history_futures = {
                        executor.submit(self.get_fund_history, code): code 
                        for code in fund_codes
                    }

                # 收集基金详情
                for future in as_completed(fund_futures):
                    code = fund_futures[future]
                    try:
                        fund_detail = future.result(timeout=60)
                        all_data['funds'][code] = fund_detail
                        task_logger.progress(len(all_data['funds']), len(fund_codes), f"已完成基金 {code}")
                    except Exception as e:
                        log_error(f"获取基金{code}数据失败: {e}")

                # 收集历史数据
                if history_futures:
                    for future in as_completed(history_futures):
                        code = history_futures[future]
                        try:
                            history_data = future.result(timeout=120)
                            if code in all_data['funds'] and not history_data.empty:
                                all_data['funds'][code]['history'] = history_data.to_dict('records')
                        except Exception as e:
                            log_warning(f"获取基金{code}历史数据失败: {e}")

            # 获取新闻数据
            try:
                all_data['news'] = self.get_fund_news()
            except Exception as e:
                log_warning(f"获取新闻数据失败: {e}")

            # 获取市场情绪
            try:
                all_data['market_sentiment'] = self.get_market_sentiment()
            except Exception as e:
                log_warning(f"获取市场情绪失败: {e}")

            task_logger.success(f"完成 {len(all_data['funds'])} 只基金数据爬取")
            return all_data

        except Exception as e:
            task_logger.error(e, "爬取基金数据失败")
            return all_data

# 创建全局实例
fund_crawler = FundCrawler(max_workers=10, use_proxy=True, use_cache=True)

if __name__ == "__main__":
    # 测试基金爬虫
    crawler = FundCrawler()

    # 测试获取基金列表
    funds = crawler.get_fund_list(top_n=20)
    print(f"获取到 {len(funds)} 只基金")

    # 测试获取基金详情
    if funds:
        detail = crawler.get_fund_detail(funds[0]['code'])
        print(f"基金详情: {detail}")

    # 测试获取新闻
    news = crawler.get_fund_news()
    print(f"获取到 {len(news)} 条新闻")
