"""备用数据源 - 使用静态数据和模拟数据"""

import pandas as pd
import random
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
from .base_source import BaseDataSource
from ..utils.logger import log_info, log_warning, log_error, log_debug

class FallbackDataSource(BaseDataSource):
    """备用数据源 - 当所有外部数据源都失败时使用"""

    def __init__(self):
        super().__init__("Fallback", priority=99)  # 最低优先级

        # 预设基金数据
        self.fund_data = {
            '000001': {'name': '华夏成长混合', 'type': '混合型', 'company': '华夏基金'},
            '110022': {'name': '易方达消费行业股票', 'type': '股票型', 'company': '易方达基金'},
            '163402': {'name': '兴全趋势投资混合', 'type': '混合型', 'company': '兴全基金'},
            '519674': {'name': '银河创新成长混合', 'type': '混合型', 'company': '银河基金'},
            '000248': {'name': '汇添富消费行业混合', 'type': '混合型', 'company': '汇添富基金'},
            '110003': {'name': '易方达上证50指数A', 'type': '指数型', 'company': '易方达基金'},
            '000011': {'name': '华夏大盘精选混合', 'type': '混合型', 'company': '华夏基金'},
            '320007': {'name': '诺安成长混合', 'type': '混合型', 'company': '诺安基金'},
            '100032': {'name': '富国中证红利指数增强', 'type': '指数型', 'company': '富国基金'},
            '161725': {'name': '招商中证白酒指数分级', 'type': '指数型', 'company': '招商基金'},
            '050002': {'name': '博时沪深300指数A', 'type': '指数型', 'company': '博时基金'},
            '161903': {'name': '万家行业优选混合', 'type': '混合型', 'company': '万家基金'},
            '202001': {'name': '南方稳健成长混合', 'type': '混合型', 'company': '南方基金'},
            '040004': {'name': '华安宝利配置混合', 'type': '混合型', 'company': '华安基金'},
            '070002': {'name': '嘉实增长混合', 'type': '混合型', 'company': '嘉实基金'},
            '519068': {'name': '汇添富焦点成长混合A', 'type': '混合型', 'company': '汇添富基金'},
            '481006': {'name': '工银红利混合', 'type': '混合型', 'company': '工银瑞信基金'},
            '000596': {'name': '前海开源中证军工指数A', 'type': '指数型', 'company': '前海开源基金'},
            '001704': {'name': '国投瑞银进宝灵活配置混合', 'type': '混合型', 'company': '国投瑞银基金'},
            '008281': {'name': '华夏中证5G通信主题ETF联接A', 'type': 'ETF联接', 'company': '华夏基金'}
        }

    def get_fund_list(self, limit: int = 100) -> List[Dict]:
        """返回预设的基金列表"""
        funds = []
        for code, info in list(self.fund_data.items())[:limit]:
            funds.append({
                'code': code,
                'name': info['name'],
                'type': info['type'],
                'company': info['company'],
                'source': self.name
            })

        log_info(f"备用数据源返回 {len(funds)} 只基金")
        return funds

    def get_fund_info(self, fund_code: str) -> Dict:
        """返回基金基本信息"""
        if fund_code in self.fund_data:
            base_info = self.fund_data[fund_code].copy()
            base_info.update({
                'code': fund_code,
                'nav': round(random.uniform(0.8, 2.5), 4),  # 模拟净值
                'nav_date': datetime.now().strftime('%Y-%m-%d'),
                'daily_return': round(random.uniform(-3, 3), 2),  # 模拟日收益率
                'establish_date': '2010-01-01',
                'scale': f'{random.randint(5, 100)}亿元',
                'source': self.name
            })
            return base_info
        else:
            # 为未知代码生成基本信息
            return {
                'code': fund_code,
                'name': f'基金{fund_code}',
                'type': '混合型',
                'company': '未知基金公司',
                'nav': round(random.uniform(0.8, 2.5), 4),
                'nav_date': datetime.now().strftime('%Y-%m-%d'),
                'daily_return': round(random.uniform(-3, 3), 2),
                'establish_date': '2010-01-01',
                'scale': f'{random.randint(5, 100)}亿元',
                'source': self.name
            }

    def get_fund_nav_history(self, fund_code: str, days: int = 365) -> pd.DataFrame:
        """生成模拟的净值历史数据"""
        try:
            # 生成日期序列
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')

            # 只保留工作日
            business_days = [d for d in date_range if d.weekday() < 5]

            # 生成模拟净值数据
            np.random.seed(hash(fund_code) % 1000)  # 使用基金代码作为种子，确保数据一致性

            initial_nav = random.uniform(0.8, 2.5)
            returns = np.random.normal(0.0005, 0.02, len(business_days))  # 日收益率正态分布

            navs = [initial_nav]
            for i in range(1, len(business_days)):
                new_nav = navs[-1] * (1 + returns[i])
                navs.append(max(new_nav, 0.1))  # 确保净值不为负

            # 创建DataFrame
            df = pd.DataFrame({
                'date': business_days,
                'nav': navs,
                'accumulated_nav': navs,  # 简化处理，累计净值等于净值
                'daily_return': np.concatenate([[0], np.diff(navs) / navs[:-1] * 100])
            })

            log_debug(f"为基金 {fund_code} 生成了 {len(df)} 条模拟历史数据")
            return df

        except Exception as e:
            log_error(f"生成基金 {fund_code} 模拟历史数据失败: {e}")
            return pd.DataFrame()

    def get_fund_holdings(self, fund_code: str) -> Dict:
        """生成模拟的持仓信息"""
        try:
            # 模拟前10大持仓
            stock_names = [
                '贵州茅台', '五粮液', '中国平安', '招商银行', '美的集团',
                '格力电器', '中国中免', '宁德时代', '比亚迪', '立讯精密'
            ]

            holdings = []
            for i, stock_name in enumerate(stock_names):
                holdings.append({
                    'stock_code': f'00000{i+1}',
                    'stock_name': stock_name,
                    'hold_ratio': round(random.uniform(1, 8), 2),
                    'hold_amount': random.randint(100, 1000) * 10000
                })

            return {
                'top_holdings': holdings,
                'update_time': datetime.now().isoformat(),
                'source': self.name
            }

        except Exception as e:
            log_error(f"生成基金 {fund_code} 模拟持仓失败: {e}")
            return {}

    def get_fund_manager(self, fund_code: str) -> Dict:
        """生成模拟的基金经理信息"""
        managers_pool = [
            '张伟', '王强', '李娜', '刘洋', '陈静',
            '杨磊', '赵敏', '孙涛', '周杰', '吴雪'
        ]

        manager_name = random.choice(managers_pool)

        return {
            'managers': [{
                'name': manager_name,
                'start_date': '2020-01-01',
                'tenure_days': (datetime.now() - datetime(2020, 1, 1)).days,
                'tenure_return': round(random.uniform(-10, 50), 2)
            }],
            'update_time': datetime.now().isoformat(),
            'source': self.name
        }

    def health_check(self) -> bool:
        """备用数据源始终可用"""
        return True
