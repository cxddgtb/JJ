"""akshare数据源实现"""

import pandas as pd
import akshare as ak
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from .base_source import BaseDataSource
from ..utils.logger import log_info, log_warning, log_error, log_debug

class AkshareDataSource(BaseDataSource):
    """akshare数据源"""

    def __init__(self):
        super().__init__("AkShare", priority=1)
        self.api_methods = self._init_api_methods()

    def _init_api_methods(self) -> Dict:
        """初始化API方法映射"""
        return {
            'fund_list': [
                'fund_name_em',
                'fund_em_fund_name', 
                'fund_basic_info_em',
                'fund_etf_list_sina'
            ],
            'fund_info': [
                'fund_open_fund_info_em',
                'fund_em_open_fund_info',
                'fund_individual_basic_info_xq'
            ],
            'fund_history': [
                'fund_open_fund_info_em',
                'fund_em_open_fund_info',
                'fund_etf_hist_em',
                'fund_etf_hist_sina'
            ]
        }

    def _try_akshare_methods(self, method_type: str, *args, **kwargs):
        """尝试多种akshare方法"""
        methods = self.api_methods.get(method_type, [])

        for method_name in methods:
            try:
                if hasattr(ak, method_name):
                    method = getattr(ak, method_name)
                    result = method(*args, **kwargs)
                    if result is not None and not (isinstance(result, pd.DataFrame) and result.empty):
                        log_debug(f"akshare方法 {method_name} 成功获取数据")
                        return result
                else:
                    log_debug(f"akshare方法 {method_name} 不存在")
            except Exception as e:
                log_debug(f"akshare方法 {method_name} 失败: {e}")
                continue

        log_warning(f"所有akshare {method_type} 方法都失败")
        return None

    def get_fund_list(self, limit: int = 100) -> List[Dict]:
        """获取基金列表"""
        try:
            # 尝试获取公募基金列表
            fund_df = self._try_akshare_methods('fund_list')

            if fund_df is not None and not fund_df.empty:
                funds = []

                # 处理不同API返回的列名
                code_cols = ['基金代码', 'fund_code', 'code', '代码']
                name_cols = ['基金简称', 'fund_name', 'name', '名称', '简称']

                code_col = None
                name_col = None

                for col in code_cols:
                    if col in fund_df.columns:
                        code_col = col
                        break

                for col in name_cols:
                    if col in fund_df.columns:
                        name_col = col
                        break

                if code_col and name_col:
                    for _, row in fund_df.head(limit).iterrows():
                        funds.append({
                            'code': str(row[code_col]).strip(),
                            'name': str(row[name_col]).strip(),
                            'source': self.name
                        })

                    log_info(f"akshare获取到 {len(funds)} 只基金")
                    return funds

            return []

        except Exception as e:
            log_error(f"akshare获取基金列表失败: {e}")
            return []

    def get_fund_info(self, fund_code: str) -> Dict:
        """获取基金基本信息"""
        try:
            # 尝试获取基金基本信息
            info_df = self._try_akshare_methods('fund_info', fund=fund_code, indicator="基金信息")

            if info_df is not None and not info_df.empty:
                info = {}
                if len(info_df) > 0:
                    row = info_df.iloc[0]

                    # 标准化字段名
                    field_mapping = {
                        '基金简称': 'name',
                        '基金代码': 'code', 
                        '基金类型': 'type',
                        '成立日期': 'establish_date',
                        '基金规模': 'scale',
                        '基金公司': 'company',
                        '基金经理': 'manager',
                        '管理费率': 'management_fee',
                        '托管费率': 'custody_fee'
                    }

                    for ak_field, std_field in field_mapping.items():
                        if ak_field in row.index:
                            info[std_field] = row[ak_field]

                    info['source'] = self.name
                    return info

            return {}

        except Exception as e:
            log_error(f"akshare获取基金{fund_code}信息失败: {e}")
            return {}

    def get_fund_nav_history(self, fund_code: str, days: int = 365) -> pd.DataFrame:
        """获取基金净值历史"""
        try:
            # 尝试获取历史净值数据
            hist_df = self._try_akshare_methods('fund_history', fund=fund_code, indicator="累计净值走势")

            if hist_df is not None and not hist_df.empty:
                # 标准化列名
                column_mapping = {
                    '净值日期': 'date',
                    '日期': 'date',
                    '净值': 'nav',
                    '单位净值': 'nav',
                    '累计净值': 'accumulated_nav',
                    '日增长率': 'daily_return',
                    '增长率': 'daily_return'
                }

                # 重命名列
                for old_col, new_col in column_mapping.items():
                    if old_col in hist_df.columns:
                        hist_df = hist_df.rename(columns={old_col: new_col})

                # 确保日期列存在并转换格式
                if 'date' in hist_df.columns:
                    hist_df['date'] = pd.to_datetime(hist_df['date'])
                    hist_df = hist_df.sort_values('date')

                    # 筛选最近days天的数据
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=days)
                    mask = hist_df['date'] >= start_date
                    hist_df = hist_df.loc[mask]

                    # 确保数值列为数值类型
                    numeric_cols = ['nav', 'accumulated_nav', 'daily_return']
                    for col in numeric_cols:
                        if col in hist_df.columns:
                            hist_df[col] = pd.to_numeric(hist_df[col], errors='coerce')

                    return hist_df.reset_index(drop=True)

            return pd.DataFrame()

        except Exception as e:
            log_error(f"akshare获取基金{fund_code}历史数据失败: {e}")
            return pd.DataFrame()

    def get_fund_holdings(self, fund_code: str) -> Dict:
        """获取基金持仓信息"""
        try:
            holdings_df = self._try_akshare_methods('fund_info', fund=fund_code, indicator="股票持仓")

            if holdings_df is not None and not holdings_df.empty:
                holdings = []

                # 处理持仓数据
                for _, row in holdings_df.head(10).iterrows():  # 只取前10大持仓
                    holding = {}

                    # 标准化字段
                    field_mapping = {
                        '股票代码': 'stock_code',
                        '股票名称': 'stock_name', 
                        '持仓占比': 'hold_ratio',
                        '持股数': 'hold_amount'
                    }

                    for ak_field, std_field in field_mapping.items():
                        if ak_field in row.index:
                            value = row[ak_field]
                            if std_field in ['hold_ratio', 'hold_amount'] and value:
                                try:
                                    # 处理百分比和数值
                                    if isinstance(value, str):
                                        value = float(value.replace('%', '').replace(',', ''))
                                    holding[std_field] = float(value)
                                except:
                                    holding[std_field] = 0.0
                            else:
                                holding[std_field] = str(value) if value else ''

                    if holding.get('stock_code'):
                        holdings.append(holding)

                return {
                    'top_holdings': holdings,
                    'update_time': datetime.now().isoformat(),
                    'source': self.name
                }

            return {}

        except Exception as e:
            log_error(f"akshare获取基金{fund_code}持仓失败: {e}")
            return {}

    def get_fund_manager(self, fund_code: str) -> Dict:
        """获取基金经理信息"""
        try:
            manager_df = self._try_akshare_methods('fund_info', fund=fund_code, indicator="基金经理")

            if manager_df is not None and not manager_df.empty:
                managers = []

                for _, row in manager_df.iterrows():
                    manager = {}

                    # 标准化字段
                    field_mapping = {
                        '基金经理': 'name',
                        '任职日期': 'start_date', 
                        '任职天数': 'tenure_days',
                        '任职回报': 'tenure_return'
                    }

                    for ak_field, std_field in field_mapping.items():
                        if ak_field in row.index:
                            manager[std_field] = row[ak_field]

                    if manager.get('name'):
                        managers.append(manager)

                return {
                    'managers': managers,
                    'update_time': datetime.now().isoformat(),
                    'source': self.name
                }

            return {}

        except Exception as e:
            log_error(f"akshare获取基金{fund_code}经理信息失败: {e}")
            return {}
