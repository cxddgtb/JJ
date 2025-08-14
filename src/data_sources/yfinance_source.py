"""yfinance数据源实现"""

import pandas as pd
import yfinance as yf
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from .base_source import BaseDataSource
from ..utils.logger import log_info, log_warning, log_error, log_debug

class YfinanceDataSource(BaseDataSource):
    """yfinance数据源"""

    def __init__(self):
        super().__init__("YFinance", priority=3)
        # 中国基金后缀映射
        self.fund_suffixes = ['.SZ', '.SS', '.HK']

    def _format_fund_code(self, fund_code: str) -> List[str]:
        """格式化基金代码，尝试不同后缀"""
        codes = [fund_code]

        # 如果没有后缀，尝试添加不同后缀
        if '.' not in fund_code:
            for suffix in self.fund_suffixes:
                codes.append(f"{fund_code}{suffix}")

        return codes

    def get_fund_list(self, limit: int = 100) -> List[Dict]:
        """yfinance不直接提供基金列表，返回一些知名基金"""
        # 返回一些知名的中国基金代码
        well_known_funds = [
            {'code': '000001', 'name': '华夏成长混合', 'source': self.name},
            {'code': '110022', 'name': '易方达消费行业股票', 'source': self.name},
            {'code': '163402', 'name': '兴全趋势投资混合', 'source': self.name},
            {'code': '519674', 'name': '银河创新成长混合', 'source': self.name},
            {'code': '000248', 'name': '汇添富消费行业混合', 'source': self.name},
            {'code': '110003', 'name': '易方达上证50指数A', 'source': self.name},
            {'code': '000011', 'name': '华夏大盘精选混合', 'source': self.name},
            {'code': '320007', 'name': '诺安成长混合', 'source': self.name},
            {'code': '100032', 'name': '富国中证红利指数增强', 'source': self.name},
            {'code': '161725', 'name': '招商中证白酒指数分级', 'source': self.name}
        ]

        return well_known_funds[:limit]

    def get_fund_info(self, fund_code: str) -> Dict:
        """获取基金基本信息"""
        try:
            fund_codes = self._format_fund_code(fund_code)

            for code in fund_codes:
                try:
                    ticker = yf.Ticker(code)
                    info = ticker.info

                    if info and len(info) > 1:  # 确保获取到了数据
                        return {
                            'code': fund_code,
                            'name': info.get('longName', info.get('shortName', '')),
                            'type': info.get('category', ''),
                            'company': info.get('fundFamily', ''),
                            'nav': info.get('navPrice', info.get('regularMarketPrice', 0)),
                            'currency': info.get('currency', ''),
                            'total_assets': info.get('totalAssets', 0),
                            'expense_ratio': info.get('annualReportExpenseRatio', 0),
                            'source': self.name
                        }
                except Exception as e:
                    log_debug(f"yfinance获取{code}信息失败: {e}")
                    continue

            return {}

        except Exception as e:
            log_error(f"yfinance获取基金{fund_code}信息失败: {e}")
            return {}

    def get_fund_nav_history(self, fund_code: str, days: int = 365) -> pd.DataFrame:
        """获取基金净值历史"""
        try:
            fund_codes = self._format_fund_code(fund_code)

            for code in fund_codes:
                try:
                    ticker = yf.Ticker(code)

                    # 计算时间范围
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=days)

                    # 获取历史数据
                    hist = ticker.history(
                        start=start_date.strftime('%Y-%m-%d'),
                        end=end_date.strftime('%Y-%m-%d'),
                        interval='1d'
                    )

                    if not hist.empty:
                        # 标准化数据格式
                        df = pd.DataFrame({
                            'date': hist.index,
                            'nav': hist['Close'],
                            'accumulated_nav': hist['Close'],  # yfinance没有累计净值，使用收盘价
                            'daily_return': hist['Close'].pct_change() * 100
                        })

                        df['daily_return'] = df['daily_return'].fillna(0)
                        df = df.reset_index(drop=True)

                        log_info(f"yfinance成功获取基金{fund_code}历史数据，共{len(df)}条记录")
                        return df

                except Exception as e:
                    log_debug(f"yfinance获取{code}历史数据失败: {e}")
                    continue

            return pd.DataFrame()

        except Exception as e:
            log_error(f"yfinance获取基金{fund_code}历史数据失败: {e}")
            return pd.DataFrame()

    def get_fund_holdings(self, fund_code: str) -> Dict:
        """获取基金持仓信息"""
        try:
            fund_codes = self._format_fund_code(fund_code)

            for code in fund_codes:
                try:
                    ticker = yf.Ticker(code)

                    # 尝试获取持仓信息
                    holdings = ticker.get_holdings()

                    if holdings is not None and not holdings.empty:
                        top_holdings = []

                        for _, row in holdings.head(10).iterrows():
                            holding = {
                                'stock_code': row.get('symbol', ''),
                                'stock_name': row.get('holdingName', ''),
                                'hold_ratio': float(row.get('holdingPercent', 0)) * 100,
                                'hold_amount': 0  # yfinance通常不提供持股数量
                            }
                            top_holdings.append(holding)

                        return {
                            'top_holdings': top_holdings,
                            'update_time': datetime.now().isoformat(),
                            'source': self.name
                        }

                except Exception as e:
                    log_debug(f"yfinance获取{code}持仓失败: {e}")
                    continue

            return {}

        except Exception as e:
            log_error(f"yfinance获取基金{fund_code}持仓失败: {e}")
            return {}

    def health_check(self) -> bool:
        """健康检查"""
        try:
            # 测试获取一个知名股票的信息
            ticker = yf.Ticker("AAPL")
            info = ticker.info
            return bool(info and len(info) > 1)
        except Exception as e:
            log_error(f"yfinance健康检查失败: {e}")
            return False
