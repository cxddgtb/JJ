import os
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from .eastmoney_crawler import EastMoneyCrawler
from .sina_crawler import SinaCrawler
from config import CONCURRENT_REQUESTS, TARGET_SITES

class CrawlerManager:
    """爬虫管理器，用于统一管理所有爬虫"""

    def __init__(self):
        self.logger = logging.getLogger("CrawlerManager")
        self.crawlers = {
            "EastMoney": EastMoneyCrawler(),
            "SinaFinance": SinaCrawler(),
        }
        self.data_dir = "data"
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """确保数据目录存在"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, "funds"), exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, "news"), exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, "ranks"), exist_ok=True)

    def crawl_all_fund_lists(self):
        """爬取所有网站的基金列表"""
        self.logger.info("开始爬取所有网站的基金列表...")
        all_funds = []

        with ThreadPoolExecutor(max_workers=len(self.crawlers)) as executor:
            future_to_name = {
                executor.submit(crawler.crawl_fund_list): name 
                for name, crawler in self.crawlers.items()
            }

            for future in as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    funds = future.result()
                    all_funds.extend(funds)
                    self.logger.info(f"{name} 爬取了 {len(funds)} 只基金")
                except Exception as e:
                    self.logger.error(f"{name} 爬取基金列表出错: {str(e)}")

        # 去重
        unique_funds = {}
        for fund in all_funds:
            code = fund['code']
            if code not in unique_funds:
                unique_funds[code] = fund

        unique_funds = list(unique_funds.values())
        self.logger.info(f"总共爬取到 {len(unique_funds)} 只不重复的基金")

        # 保存基金列表
        self._save_fund_list(unique_funds)

        return unique_funds

    def _save_fund_list(self, fund_list):
        """保存基金列表到文件"""
        import json

        file_path = os.path.join(self.data_dir, "fund_list.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({
                'data': fund_list,
                'count': len(fund_list),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, f, ensure_ascii=False, indent=2)

        self.logger.info(f"基金列表已保存到 {file_path}")

    def crawl_fund_details(self, fund_codes, sites=None):
        """爬取指定基金的详情"""
        if sites is None:
            sites = list(self.crawlers.keys())

        self.logger.info(f"开始爬取 {len(fund_codes)} 只基金的详情...")

        all_details = {}

        for code in fund_codes:
            fund_details = {}

            with ThreadPoolExecutor(max_workers=len(sites)) as executor:
                future_to_site = {
                    executor.submit(self.crawlers[site].crawl_fund_detail, code): site 
                    for site in sites if site in self.crawlers
                }

                for future in as_completed(future_to_site):
                    site = future_to_site[future]
                    try:
                        detail = future.result()
                        if detail:
                            fund_details[site] = detail
                            self.logger.debug(f"{site} 爬取基金 {code} 详情成功")
                    except Exception as e:
                        self.logger.error(f"{site} 爬取基金 {code} 详情出错: {str(e)}")

            if fund_details:
                all_details[code] = fund_details
                # 保存单个基金详情
                self._save_fund_detail(code, fund_details)

        self.logger.info(f"成功爬取 {len(all_details)} 只基金的详情")
        return all_details

    def _save_fund_detail(self, fund_code, fund_detail):
        """保存单个基金详情到文件"""
        import json

        file_path = os.path.join(self.data_dir, "funds", f"{fund_code}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(fund_detail, f, ensure_ascii=False, indent=2)

    def crawl_all_fund_news(self, limit_per_site=50):
        """爬取所有网站的基金新闻"""
        self.logger.info("开始爬取所有网站的基金新闻...")
        all_news = []

        with ThreadPoolExecutor(max_workers=len(self.crawlers)) as executor:
            future_to_name = {
                executor.submit(crawler.crawl_fund_news, limit_per_site): name 
                for name, crawler in self.crawlers.items()
            }

            for future in as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    news = future.result()
                    all_news.extend(news)
                    self.logger.info(f"{name} 爬取了 {len(news)} 条新闻")
                except Exception as e:
                    self.logger.error(f"{name} 爬取基金新闻出错: {str(e)}")

        # 保存新闻
        self._save_news(all_news)

        self.logger.info(f"总共爬取到 {len(all_news)} 条基金新闻")
        return all_news

    def _save_news(self, news_list):
        """保存新闻到文件"""
        import json

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_path = os.path.join(self.data_dir, "news", f"news_{timestamp}.json")

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({
                'data': news_list,
                'count': len(news_list),
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, f, ensure_ascii=False, indent=2)

        self.logger.info(f"基金新闻已保存到 {file_path}")

    def crawl_fund_ranks(self, fund_type=None, limit_per_site=100):
        """爬取所有网站的基金排名"""
        self.logger.info("开始爬取所有网站的基金排名...")
        all_ranks = {}

        with ThreadPoolExecutor(max_workers=len(self.crawlers)) as executor:
            future_to_name = {
                executor.submit(crawler.crawl_fund_rank, fund_type, limit_per_site): name 
                for name, crawler in self.crawlers.items()
            }

            for future in as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    rank = future.result()
                    if rank:
                        all_ranks[name] = rank
                        self.logger.info(f"{name} 爬取了 {len(rank)} 条排名数据")
                except Exception as e:
                    self.logger.error(f"{name} 爬取基金排名出错: {str(e)}")

        # 保存排名
        self._save_ranks(all_ranks)

        return all_ranks

    def _save_ranks(self, ranks):
        """保存排名到文件"""
        import json

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_path = os.path.join(self.data_dir, "ranks", f"ranks_{timestamp}.json")

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({
                'data': ranks,
                'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, f, ensure_ascii=False, indent=2)

        self.logger.info(f"基金排名已保存到 {file_path}")

    def crawl_all_data(self, fund_codes=None, news_limit=50, rank_limit=100):
        """爬取所有数据"""
        # 爬取基金列表
        fund_list = self.crawl_all_fund_lists()

        # 如果没有指定基金代码，则使用所有基金代码
        if fund_codes is None:
            fund_codes = [fund['code'] for fund in fund_list]

        # 爬取基金详情
        fund_details = self.crawl_fund_details(fund_codes)

        # 爬取基金新闻
        fund_news = self.crawl_all_fund_news(news_limit)

        # 爬取基金排名
        fund_ranks = self.crawl_fund_ranks(limit_per_site=rank_limit)

        return {
            'fund_list': fund_list,
            'fund_details': fund_details,
            'fund_news': fund_news,
            'fund_ranks': fund_ranks
        }
