"""数据源管理器"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from .base_source import BaseDataSource
from .simple_data_source import SimpleDataSource
from .akshare_source import AkshareDataSource
from .web_scraper_source import WebScraperDataSource
from .yfinance_source import YfinanceDataSource
from .fallback_source import FallbackDataSource
from ..utils.logger import log_info, log_warning, log_error, log_debug

class DataSourceManager:
    """数据源管理器 - 统一管理多个数据源"""

    def __init__(self):
        self.sources: List[BaseDataSource] = []
        self.source_status: Dict[str, bool] = {}
        self.last_health_check = 0
        self.health_check_interval = 300  # 5分钟检查一次

        # 初始化数据源
        self._init_sources()

        # 启动健康检查线程
        self._start_health_monitor()

    def _init_sources(self):
        """初始化所有数据源"""
        try:
            # 按优先级顺序添加数据源
            sources_to_add = [
                SimpleDataSource(),      # 简化数据源，专为CI/CD环境设计
                AkshareDataSource(),
                WebScraperDataSource(),
                YfinanceDataSource(),
                FallbackDataSource()     # 备用数据源，确保始终有数据
            ]

            for source in sources_to_add:
                try:
                    self.sources.append(source)
                    self.source_status[source.name] = False  # 初始状态为未知
                    log_info(f"数据源 {source.name} 初始化成功")
                except Exception as e:
                    log_error(f"数据源 {source.name} 初始化失败: {e}")

            # 按优先级排序
            self.sources.sort(key=lambda x: x.priority)
            log_info(f"数据源管理器初始化完成，共 {len(self.sources)} 个数据源")

        except Exception as e:
            log_error(f"数据源管理器初始化失败: {e}")

    def _start_health_monitor(self):
        """启动健康监控线程"""
        def health_monitor():
            while True:
                try:
                    self._check_all_sources_health()
                    time.sleep(self.health_check_interval)
                except Exception as e:
                    log_error(f"健康监控线程异常: {e}")
                    time.sleep(60)  # 出错时等待1分钟再重试

        monitor_thread = threading.Thread(target=health_monitor, daemon=True)
        monitor_thread.start()
        log_info("数据源健康监控线程已启动")

    def _check_all_sources_health(self):
        """检查所有数据源健康状态"""
        current_time = time.time()
        if current_time - self.last_health_check < self.health_check_interval:
            return

        log_debug("开始检查数据源健康状态")

        with ThreadPoolExecutor(max_workers=len(self.sources)) as executor:
            future_to_source = {
                executor.submit(source.health_check): source 
                for source in self.sources
            }

            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    is_healthy = future.result(timeout=30)
                    old_status = self.source_status.get(source.name, False)
                    self.source_status[source.name] = is_healthy

                    if old_status != is_healthy:
                        status_str = "可用" if is_healthy else "不可用"
                        log_info(f"数据源 {source.name} 状态变更: {status_str}")

                except Exception as e:
                    self.source_status[source.name] = False
                    log_warning(f"数据源 {source.name} 健康检查失败: {e}")

        self.last_health_check = current_time

        # 记录可用数据源
        available_sources = [name for name, status in self.source_status.items() if status]
        log_debug(f"当前可用数据源: {available_sources}")

    def get_available_sources(self) -> List[BaseDataSource]:
        """获取当前可用的数据源"""
        available = []
        fallback_source = None
        
        for source in self.sources:
            if source.name in ["Fallback", "Simple"]:
                # 备用数据源和简化数据源始终标记为可用
                self.source_status[source.name] = True
                if source.name == "Fallback":
                    fallback_source = source
                else:
                    available.append(source)
            elif self.source_status.get(source.name, False):
                available.append(source)
        
        # 确保备用数据源总是可用
        if fallback_source:
            available.append(fallback_source)
        
        # 如果除了备用数据源外没有其他可用源，记录警告
        if len(available) == 1 and fallback_source in available:
            log_warning("仅备用数据源可用，外部数据源均不可用")
        
        return available if available else self.sources

    def get_fund_list(self, limit: int = 100) -> List[Dict]:
        """获取基金列表 - 从多个数据源聚合"""
        all_funds = []
        fund_codes_seen = set()

        available_sources = self.get_available_sources()

        for source in available_sources:
            try:
                log_debug(f"尝试从 {source.name} 获取基金列表")
                funds = source.get_fund_list(limit)

                for fund in funds:
                    code = fund.get('code', '')
                    if code and code not in fund_codes_seen:
                        fund_codes_seen.add(code)
                        all_funds.append(fund)

                        if len(all_funds) >= limit:
                            break

                if len(all_funds) >= limit:
                    break

                log_info(f"从 {source.name} 获取到 {len(funds)} 只基金")

            except Exception as e:
                log_error(f"从 {source.name} 获取基金列表失败: {e}")
                continue

        log_info(f"基金列表聚合完成，共获取 {len(all_funds)} 只基金")
        return all_funds[:limit]

    def get_fund_info(self, fund_code: str) -> Dict:
        """获取基金信息 - 多数据源融合"""
        merged_info = {'code': fund_code}

        available_sources = self.get_available_sources()

        for source in available_sources:
            try:
                log_debug(f"尝试从 {source.name} 获取基金 {fund_code} 信息")
                info = source.get_fund_info(fund_code)

                if info:
                    # 合并信息，保留所有有价值的数据
                    for key, value in info.items():
                        if value and (key not in merged_info or not merged_info[key]):
                            merged_info[key] = value

                    # 记录数据来源
                    sources_used = merged_info.get('sources_used', [])
                    if source.name not in sources_used:
                        sources_used.append(source.name)
                    merged_info['sources_used'] = sources_used

                    log_debug(f"从 {source.name} 成功获取基金 {fund_code} 信息")

            except Exception as e:
                log_error(f"从 {source.name} 获取基金 {fund_code} 信息失败: {e}")
                continue

        # 添加获取时间
        merged_info['last_updated'] = datetime.now().isoformat()

        return merged_info

    def get_fund_nav_history(self, fund_code: str, days: int = 365) -> pd.DataFrame:
        """获取基金净值历史 - 优先使用最佳数据源"""
        available_sources = self.get_available_sources()

        for source in available_sources:
            try:
                log_debug(f"尝试从 {source.name} 获取基金 {fund_code} 历史数据")
                hist_df = source.get_fund_nav_history(fund_code, days)

                if not hist_df.empty:
                    # 添加数据源标识
                    hist_df['data_source'] = source.name

                    log_info(f"从 {source.name} 成功获取基金 {fund_code} 历史数据，共 {len(hist_df)} 条记录")
                    return hist_df

            except Exception as e:
                log_error(f"从 {source.name} 获取基金 {fund_code} 历史数据失败: {e}")
                continue

        log_warning(f"所有数据源都无法获取基金 {fund_code} 历史数据")
        return pd.DataFrame()

    def get_fund_holdings(self, fund_code: str) -> Dict:
        """获取基金持仓信息"""
        available_sources = self.get_available_sources()

        for source in available_sources:
            try:
                log_debug(f"尝试从 {source.name} 获取基金 {fund_code} 持仓信息")
                holdings = source.get_fund_holdings(fund_code)

                if holdings and holdings.get('top_holdings'):
                    log_info(f"从 {source.name} 成功获取基金 {fund_code} 持仓信息")
                    return holdings

            except Exception as e:
                log_error(f"从 {source.name} 获取基金 {fund_code} 持仓信息失败: {e}")
                continue

        log_warning(f"所有数据源都无法获取基金 {fund_code} 持仓信息")
        return {}

    def get_fund_manager(self, fund_code: str) -> Dict:
        """获取基金经理信息"""
        available_sources = self.get_available_sources()

        for source in available_sources:
            try:
                log_debug(f"尝试从 {source.name} 获取基金 {fund_code} 经理信息")
                manager_info = source.get_fund_manager(fund_code)

                if manager_info and manager_info.get('managers'):
                    log_info(f"从 {source.name} 成功获取基金 {fund_code} 经理信息")
                    return manager_info

            except Exception as e:
                log_error(f"从 {source.name} 获取基金 {fund_code} 经理信息失败: {e}")
                continue

        log_warning(f"所有数据源都无法获取基金 {fund_code} 经理信息")
        return {}

    def get_comprehensive_fund_data(self, fund_code: str, days: int = 365) -> Dict:
        """获取基金的全面数据"""
        log_info(f"开始获取基金 {fund_code} 的全面数据")

        # 并行获取不同类型的数据
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_info = executor.submit(self.get_fund_info, fund_code)
            future_history = executor.submit(self.get_fund_nav_history, fund_code, days)
            future_holdings = executor.submit(self.get_fund_holdings, fund_code)
            future_manager = executor.submit(self.get_fund_manager, fund_code)

            # 收集结果
            comprehensive_data = {
                'fund_code': fund_code,
                'basic_info': {},
                'nav_history': pd.DataFrame(),
                'holdings': {},
                'manager': {},
                'last_updated': datetime.now().isoformat()
            }

            try:
                comprehensive_data['basic_info'] = future_info.result(timeout=60)
            except Exception as e:
                log_error(f"获取基金 {fund_code} 基本信息超时: {e}")

            try:
                comprehensive_data['nav_history'] = future_history.result(timeout=60)
            except Exception as e:
                log_error(f"获取基金 {fund_code} 历史数据超时: {e}")

            try:
                comprehensive_data['holdings'] = future_holdings.result(timeout=60)
            except Exception as e:
                log_error(f"获取基金 {fund_code} 持仓信息超时: {e}")

            try:
                comprehensive_data['manager'] = future_manager.result(timeout=60)
            except Exception as e:
                log_error(f"获取基金 {fund_code} 经理信息超时: {e}")

        log_info(f"基金 {fund_code} 全面数据获取完成")
        return comprehensive_data

    def get_status_report(self) -> Dict:
        """获取数据源状态报告"""
        return {
            'total_sources': len(self.sources),
            'available_sources': len(self.get_available_sources()),
            'source_status': self.source_status.copy(),
            'last_health_check': datetime.fromtimestamp(self.last_health_check).isoformat() if self.last_health_check else None,
            'sources_info': [
                {
                    'name': source.name,
                    'priority': source.priority,
                    'status': self.source_status.get(source.name, False)
                }
                for source in self.sources
            ]
        }

# 全局数据源管理器实例
data_source_manager = DataSourceManager()
