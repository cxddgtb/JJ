"""增强版基金爬虫 - 使用新的数据源管理器"""

import pandas as pd
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from ..data_sources.data_source_manager import data_source_manager
from ..utils.logger import log_info, log_warning, log_error, log_debug
from ..utils.cache_manager import cache_manager
from ..config import DEFAULT_FUNDS, CRAWLER_CONFIG

class EnhancedFundCrawler:
    """增强版基金爬虫"""

    def __init__(self):
        self.data_manager = data_source_manager
        self.cache_manager = cache_manager
        self.config = CRAWLER_CONFIG

        # 统计信息
        self.stats = {
            'total_requested': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'start_time': datetime.now()
        }

    def get_fund_list(self, top_n: int = 50, use_cache: bool = True) -> List[Dict]:
        """获取基金列表"""
        cache_key = f"fund_list_{top_n}"

        # 尝试从缓存获取
        if use_cache:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                self.stats['cache_hits'] += 1
                log_info(f"从缓存获取基金列表，共 {len(cached_data)} 只基金")
                return cached_data

        log_info(f"开始获取前 {top_n} 只基金列表")

        try:
            # 使用数据源管理器获取基金列表
            funds = self.data_manager.get_fund_list(limit=top_n)

            # 如果数据源管理器返回空列表，使用默认基金列表
            if not funds:
                log_warning("数据源管理器未能获取基金列表，使用默认基金列表")
                funds = []
                for code, name in DEFAULT_FUNDS.items():
                    funds.append({
                        'code': code,
                        'name': name,
                        'source': 'Default'
                    })

            # 缓存结果
            if use_cache and funds:
                self.cache_manager.set(cache_key, funds, expire_hours=6)  # 6小时过期

            self.stats['successful_requests'] += 1
            log_info(f"成功获取 {len(funds)} 只基金")
            return funds

        except Exception as e:
            self.stats['failed_requests'] += 1
            log_error(f"获取基金列表失败: {e}")

            # 返回默认基金列表作为备选
            funds = []
            for code, name in DEFAULT_FUNDS.items():
                funds.append({
                    'code': code,
                    'name': name,
                    'source': 'Default'
                })
            return funds[:top_n]

    def get_fund_detail(self, fund_code: str, use_cache: bool = True) -> Dict:
        """获取基金详细信息"""
        cache_key = f"fund_detail_{fund_code}"

        # 尝试从缓存获取
        if use_cache:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                self.stats['cache_hits'] += 1
                log_debug(f"从缓存获取基金 {fund_code} 详情")
                return cached_data

        log_info(f"开始获取基金 {fund_code} 详细信息")
        self.stats['total_requested'] += 1

        try:
            # 使用数据源管理器获取全面数据
            comprehensive_data = self.data_manager.get_comprehensive_fund_data(fund_code)

            # 整理数据格式
            fund_detail = self._format_fund_detail(comprehensive_data)

            # 缓存结果
            if use_cache and fund_detail:
                self.cache_manager.set(cache_key, fund_detail, expire_hours=2)  # 2小时过期

            self.stats['successful_requests'] += 1
            return fund_detail

        except Exception as e:
            self.stats['failed_requests'] += 1
            log_error(f"获取基金 {fund_code} 详情失败: {e}")
            return {}

    def _format_fund_detail(self, comprehensive_data: Dict) -> Dict:
        """格式化基金详情数据"""
        fund_code = comprehensive_data.get('fund_code', '')
        basic_info = comprehensive_data.get('basic_info', {})
        nav_history = comprehensive_data.get('nav_history', pd.DataFrame())
        holdings = comprehensive_data.get('holdings', {})
        manager = comprehensive_data.get('manager', {})

        # 基础信息
        fund_detail = {
            'code': fund_code,
            'name': basic_info.get('name', ''),
            'type': basic_info.get('type', ''),
            'company': basic_info.get('company', ''),
            'establish_date': basic_info.get('establish_date', ''),
            'scale': basic_info.get('scale', ''),
            'sources_used': basic_info.get('sources_used', []),
            'last_updated': comprehensive_data.get('last_updated', '')
        }

        # 净值信息
        if not nav_history.empty:
            latest_nav = nav_history.iloc[-1]
            fund_detail.update({
                'nav': float(latest_nav.get('nav', 0)),
                'nav_date': latest_nav.get('date', '').strftime('%Y-%m-%d') if pd.notna(latest_nav.get('date')) else '',
                'daily_return': float(latest_nav.get('daily_return', 0)),
                'data_points': len(nav_history)
            })

            # 计算近期收益率
            if len(nav_history) >= 7:
                week_return = ((nav_history.iloc[-1]['nav'] / nav_history.iloc[-7]['nav']) - 1) * 100
                fund_detail['week_return'] = round(week_return, 2)

            if len(nav_history) >= 30:
                month_return = ((nav_history.iloc[-1]['nav'] / nav_history.iloc[-30]['nav']) - 1) * 100
                fund_detail['month_return'] = round(month_return, 2)

            if len(nav_history) >= 252:  # 一年约252个交易日
                year_return = ((nav_history.iloc[-1]['nav'] / nav_history.iloc[-252]['nav']) - 1) * 100
                fund_detail['year_return'] = round(year_return, 2)

        # 持仓信息
        if holdings.get('top_holdings'):
            fund_detail['holdings'] = holdings['top_holdings'][:10]  # 前10大持仓
            fund_detail['holdings_count'] = len(holdings['top_holdings'])

        # 基金经理信息
        if manager.get('managers'):
            fund_detail['managers'] = manager['managers']
            fund_detail['current_manager'] = manager['managers'][0] if manager['managers'] else {}

        return fund_detail

    def get_fund_history(self, fund_code: str, days: int = 365, use_cache: bool = True) -> pd.DataFrame:
        """获取基金历史数据"""
        cache_key = f"fund_history_{fund_code}_{days}"

        # 尝试从缓存获取
        if use_cache:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data is not None:
                self.stats['cache_hits'] += 1
                log_debug(f"从缓存获取基金 {fund_code} 历史数据")
                return cached_data

        log_info(f"开始获取基金 {fund_code} 最近 {days} 天历史数据")

        try:
            # 使用数据源管理器获取历史数据
            hist_df = self.data_manager.get_fund_nav_history(fund_code, days)

            # 缓存结果
            if use_cache and not hist_df.empty:
                self.cache_manager.set(cache_key, hist_df, expire_hours=1)  # 1小时过期

            return hist_df

        except Exception as e:
            log_error(f"获取基金 {fund_code} 历史数据失败: {e}")
            return pd.DataFrame()

    def batch_get_fund_details(self, fund_codes: List[str], max_workers: int = 5) -> Dict[str, Dict]:
        """批量获取基金详情"""
        log_info(f"开始批量获取 {len(fund_codes)} 只基金的详情")

        results = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_code = {
                executor.submit(self.get_fund_detail, code): code 
                for code in fund_codes
            }

            # 收集结果
            for future in as_completed(future_to_code):
                fund_code = future_to_code[future]
                try:
                    result = future.result(timeout=60)  # 60秒超时
                    if result:
                        results[fund_code] = result
                        log_debug(f"成功获取基金 {fund_code} 详情")
                    else:
                        log_warning(f"基金 {fund_code} 详情为空")

                except Exception as e:
                    log_error(f"获取基金 {fund_code} 详情异常: {e}")

        log_info(f"批量获取完成，成功获取 {len(results)} 只基金详情")
        return results

    def get_fund_news(self, keywords: List[str] = None, limit: int = 20) -> List[Dict]:
        """获取基金相关新闻（简化版）"""
        # 这里可以集成新闻API或爬虫
        log_info("获取基金新闻功能暂未实现")
        return []

    def get_market_overview(self) -> Dict:
        """获取市场概览"""
        log_info("开始获取市场概览")

        try:
            # 获取一些代表性基金的数据来分析市场
            representative_funds = ['000001', '110022', '163402', '519674', '000248']
            market_data = {}

            for fund_code in representative_funds:
                try:
                    hist_df = self.get_fund_history(fund_code, days=30)
                    if not hist_df.empty:
                        latest_return = hist_df.iloc[-1]['daily_return']
                        market_data[fund_code] = latest_return
                except:
                    continue

            if market_data:
                avg_return = sum(market_data.values()) / len(market_data)
                return {
                    'average_daily_return': round(avg_return, 2),
                    'sample_funds': len(market_data),
                    'market_sentiment': 'positive' if avg_return > 0 else 'negative',
                    'last_updated': datetime.now().isoformat()
                }

            return {}

        except Exception as e:
            log_error(f"获取市场概览失败: {e}")
            return {}

    def get_stats(self) -> Dict:
        """获取爬虫统计信息"""
        runtime = datetime.now() - self.stats['start_time']

        return {
            **self.stats,
            'runtime_seconds': runtime.total_seconds(),
            'success_rate': round(
                (self.stats['successful_requests'] / max(self.stats['total_requested'], 1)) * 100, 2
            ),
            'cache_hit_rate': round(
                (self.stats['cache_hits'] / max(self.stats['total_requested'], 1)) * 100, 2
            ),
            'data_sources_status': self.data_manager.get_status_report()
        }

    def clear_cache(self):
        """清理缓存"""
        self.cache_manager.clear()
        log_info("基金爬虫缓存已清理")

    def health_check(self) -> Dict:
        """健康检查"""
        return {
            'crawler_status': 'healthy',
            'data_sources': self.data_manager.get_status_report(),
            'cache_status': 'available',
            'last_check': datetime.now().isoformat()
        }
