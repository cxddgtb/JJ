"""简化数据源 - 专门为GitHub Actions环境优化"""

import pandas as pd
import json
import random
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
from .base_source import BaseDataSource
from ..utils.logger import log_info, log_warning, log_error, log_debug

class SimpleDataSource(BaseDataSource):
    """简化数据源 - 专为CI/CD环境设计"""

    def __init__(self):
        super().__init__("Simple", priority=0)  # 最高优先级

        # 扩展的基金数据库
        self.fund_database = {
            '000001': {'name': '华夏成长混合', 'type': '混合型', 'company': '华夏基金', 'scale': '50.2亿', 'nav': 1.8234},
            '110022': {'name': '易方达消费行业股票', 'type': '股票型', 'company': '易方达基金', 'scale': '128.7亿', 'nav': 3.2156},
            '163402': {'name': '兴全趋势投资混合', 'type': '混合型', 'company': '兴全基金', 'scale': '85.3亿', 'nav': 2.1567},
            '519674': {'name': '银河创新成长混合', 'type': '混合型', 'company': '银河基金', 'scale': '42.8亿', 'nav': 1.9834},
            '000248': {'name': '汇添富消费行业混合', 'type': '混合型', 'company': '汇添富基金', 'scale': '76.5亿', 'nav': 2.4521},
            '110003': {'name': '易方达上证50指数A', 'type': '指数型', 'company': '易方达基金', 'scale': '95.1亿', 'nav': 1.7832},
            '000011': {'name': '华夏大盘精选混合', 'type': '混合型', 'company': '华夏基金', 'scale': '156.8亿', 'nav': 2.8945},
            '320007': {'name': '诺安成长混合', 'type': '混合型', 'company': '诺安基金', 'scale': '38.2亿', 'nav': 1.6745},
            '100032': {'name': '富国中证红利指数增强', 'type': '指数型', 'company': '富国基金', 'scale': '67.4亿', 'nav': 2.0123},
            '161725': {'name': '招商中证白酒指数分级', 'type': '指数型', 'company': '招商基金', 'scale': '45.6亿', 'nav': 1.4567},
            '050002': {'name': '博时沪深300指数A', 'type': '指数型', 'company': '博时基金', 'scale': '89.3亿', 'nav': 1.8765},
            '161903': {'name': '万家行业优选混合', 'type': '混合型', 'company': '万家基金', 'scale': '32.1亿', 'nav': 2.1234},
            '202001': {'name': '南方稳健成长混合', 'type': '混合型', 'company': '南方基金', 'scale': '78.9亿', 'nav': 1.9456},
            '040004': {'name': '华安宝利配置混合', 'type': '混合型', 'company': '华安基金', 'scale': '54.7亿', 'nav': 2.3567},
            '070002': {'name': '嘉实增长混合', 'type': '混合型', 'company': '嘉实基金', 'scale': '98.2亿', 'nav': 2.6789},
            '519068': {'name': '汇添富焦点成长混合A', 'type': '混合型', 'company': '汇添富基金', 'scale': '61.5亿', 'nav': 2.1098},
            '481006': {'name': '工银红利混合', 'type': '混合型', 'company': '工银瑞信基金', 'scale': '73.6亿', 'nav': 1.8543},
            '000596': {'name': '前海开源中证军工指数A', 'type': '指数型', 'company': '前海开源基金', 'scale': '29.8亿', 'nav': 1.5432},
            '001704': {'name': '国投瑞银进宝灵活配置混合', 'type': '混合型', 'company': '国投瑞银基金', 'scale': '41.2亿', 'nav': 1.7654},
            '008281': {'name': '华夏中证5G通信主题ETF联接A', 'type': 'ETF联接', 'company': '华夏基金', 'scale': '35.9亿', 'nav': 1.3456},
            '005827': {'name': '易方达蓝筹精选混合', 'type': '混合型', 'company': '易方达基金', 'scale': '102.4亿', 'nav': 2.7890},
            '260108': {'name': '景顺长城新兴成长混合', 'type': '混合型', 'company': '景顺长城基金', 'scale': '56.3亿', 'nav': 2.0987},
            '000913': {'name': '农银汇理主题轮动混合', 'type': '混合型', 'company': '农银汇理基金', 'scale': '43.7亿', 'nav': 1.8765},
            '110011': {'name': '易方达中小盘混合', 'type': '混合型', 'company': '易方达基金', 'scale': '87.1亿', 'nav': 2.4321},
            '000831': {'name': '工银医疗保健行业股票', 'type': '股票型', 'company': '工银瑞信基金', 'scale': '69.8亿', 'nav': 3.1234}
        }

        # 预计算的技术指标基础值
        self.tech_indicators = {}
        for code in self.fund_database.keys():
            self.tech_indicators[code] = {
                'rsi': random.uniform(30, 70),
                'macd': random.uniform(-0.05, 0.05),
                'ma5': random.uniform(0.95, 1.05),
                'ma20': random.uniform(0.90, 1.10)
            }

    def get_fund_list(self, limit: int = 100) -> List[Dict]:
        """返回基金列表"""
        funds = []
        codes = list(self.fund_database.keys())[:limit]

        for code in codes:
            fund_data = self.fund_database[code]
            funds.append({
                'code': code,
                'name': fund_data['name'],
                'type': fund_data['type'],
                'company': fund_data['company'],
                'nav': fund_data['nav'],
                'source': self.name
            })

        log_info(f"简化数据源返回 {len(funds)} 只基金")
        return funds

    def get_fund_info(self, fund_code: str) -> Dict:
        """获取基金基本信息"""
        if fund_code in self.fund_database:
            base_info = self.fund_database[fund_code].copy()

            # 添加动态计算的数据
            today = datetime.now()
            base_info.update({
                'code': fund_code,
                'nav_date': today.strftime('%Y-%m-%d'),
                'daily_return': round(random.uniform(-2.5, 2.5), 2),
                'week_return': round(random.uniform(-5, 5), 2),
                'month_return': round(random.uniform(-8, 8), 2),
                'year_return': round(random.uniform(-15, 25), 2),
                'establish_date': '2015-06-01',
                'management_fee': '1.50%',
                'custody_fee': '0.25%',
                'source': self.name,
                'last_updated': today.isoformat()
            })

            return base_info
        else:
            # 生成未知基金的基本信息
            return {
                'code': fund_code,
                'name': f'基金{fund_code}',
                'type': random.choice(['混合型', '股票型', '债券型', '指数型']),
                'company': f'基金公司{fund_code[:3]}',
                'nav': round(random.uniform(0.8, 3.0), 4),
                'nav_date': datetime.now().strftime('%Y-%m-%d'),
                'daily_return': round(random.uniform(-2.5, 2.5), 2),
                'scale': f'{random.randint(20, 150)}亿元',
                'establish_date': '2015-06-01',
                'source': self.name
            }

    def get_fund_nav_history(self, fund_code: str, days: int = 365) -> pd.DataFrame:
        """生成基金净值历史数据"""
        try:
            # 使用基金代码作为随机种子，确保数据一致性
            np.random.seed(int(fund_code[:6]) if fund_code.isdigit() else hash(fund_code) % 100000)

            # 生成交易日日期
            end_date = datetime.now()
            start_date = end_date - timedelta(days=int(days * 1.4))  # 多生成一些日期以确保有足够的交易日

            # 生成所有日期，然后筛选工作日
            all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
            business_dates = [d for d in all_dates if d.weekday() < 5][-days:]  # 只保留最近的交易日

            # 获取基金基础净值
            base_nav = self.fund_database.get(fund_code, {}).get('nav', 1.5)

            # 生成价格走势（使用几何布朗运动）
            dt = 1/252  # 一年252个交易日
            mu = 0.08   # 年化收益率
            sigma = 0.2 # 年化波动率

            prices = [base_nav * 0.95]  # 起始价格稍低于当前净值

            for i in range(1, len(business_dates)):
                drift = mu * dt
                shock = sigma * np.sqrt(dt) * np.random.normal()
                price = prices[-1] * np.exp(drift + shock)
                prices.append(max(price, 0.1))  # 确保价格不会太低

            # 调整最后一个价格接近当前净值
            if len(prices) > 0:
                adjustment_factor = base_nav / prices[-1]
                prices = [p * adjustment_factor for p in prices]

            # 计算日收益率
            returns = [0] + [((prices[i] / prices[i-1]) - 1) * 100 for i in range(1, len(prices))]

            # 创建DataFrame
            df = pd.DataFrame({
                'date': business_dates,
                'nav': prices,
                'accumulated_nav': prices,  # 简化处理
                'daily_return': returns
            })

            # 添加一些技术指标
            if len(df) >= 5:
                df['ma5'] = df['nav'].rolling(window=5).mean()
            if len(df) >= 20:
                df['ma20'] = df['nav'].rolling(window=20).mean()

            # 填充NaN值
            df = df.fillna(method='bfill').fillna(method='ffill')

            log_debug(f"为基金 {fund_code} 生成了 {len(df)} 条历史数据")
            return df

        except Exception as e:
            log_error(f"生成基金 {fund_code} 历史数据失败: {e}")
            return pd.DataFrame()

    def get_fund_holdings(self, fund_code: str) -> Dict:
        """生成持仓信息"""
        try:
            # 根据基金类型生成不同的持仓
            fund_info = self.fund_database.get(fund_code, {})
            fund_type = fund_info.get('type', '混合型')

            if '股票' in fund_type or '混合' in fund_type:
                stocks = [
                    ('000001', '平安银行', 7.23), ('000002', '万科A', 6.45),
                    ('000858', '五粮液', 5.89), ('000568', '泸州老窖', 4.67),
                    ('000596', '古井贡酒', 4.12), ('002415', '海康威视', 3.98),
                    ('002594', '比亚迪', 3.76), ('300750', '宁德时代', 3.54),
                    ('600036', '招商银行', 3.21), ('600519', '贵州茅台', 2.98)
                ]
            elif '债券' in fund_type:
                stocks = [
                    ('110035', '国债1035', 15.23), ('110023', '国债1023', 12.45),
                    ('120408', '企业债408', 8.89), ('136842', '公司债842', 7.67),
                    ('101801', '政府债801', 6.12), ('112205', '企业债205', 5.98)
                ]
            else:  # 指数型
                stocks = [
                    ('000001', '上证指数成分股1', 4.23), ('000002', '上证指数成分股2', 4.15),
                    ('000858', '上证指数成分股3', 3.89), ('000568', '上证指数成分股4', 3.67),
                    ('000596', '上证指数成分股5', 3.42), ('002415', '上证指数成分股6', 3.28),
                    ('002594', '上证指数成分股7', 3.16), ('300750', '上证指数成分股8', 3.04),
                    ('600036', '上证指数成分股9', 2.91), ('600519', '上证指数成分股10', 2.78)
                ]

            holdings = []
            for i, (code, name, ratio) in enumerate(stocks):
                holdings.append({
                    'stock_code': code,
                    'stock_name': name,
                    'hold_ratio': round(ratio + random.uniform(-0.5, 0.5), 2),
                    'hold_amount': random.randint(100, 2000) * 10000
                })

            return {
                'top_holdings': holdings,
                'total_holdings': len(holdings),
                'stock_position_ratio': sum(h['hold_ratio'] for h in holdings),
                'update_time': datetime.now().isoformat(),
                'source': self.name
            }

        except Exception as e:
            log_error(f"生成基金 {fund_code} 持仓失败: {e}")
            return {}

    def get_fund_manager(self, fund_code: str) -> Dict:
        """生成基金经理信息"""
        try:
            # 基金经理姓名库
            manager_names = [
                '张明华', '李建国', '王志强', '刘美玲', '陈思远',
                '杨晓东', '赵雪梅', '孙建军', '周春华', '吴国庆',
                '徐文博', '马丽娟', '朱永强', '胡晓敏', '郭建华'
            ]

            # 为每个基金分配固定的经理（基于基金代码）
            manager_index = int(fund_code[:3]) % len(manager_names) if fund_code.isdigit() else hash(fund_code) % len(manager_names)
            manager_name = manager_names[manager_index]

            start_date = datetime(2020, 1, 1) + timedelta(days=manager_index * 30)
            tenure_days = (datetime.now() - start_date).days

            return {
                'managers': [{
                    'name': manager_name,
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'tenure_days': tenure_days,
                    'tenure_return': round(random.uniform(5, 35), 2),
                    'experience_years': random.randint(5, 15),
                    'managed_funds': random.randint(2, 8)
                }],
                'current_manager': manager_name,
                'management_style': random.choice(['价值投资', '成长投资', '平衡投资', '指数跟踪']),
                'update_time': datetime.now().isoformat(),
                'source': self.name
            }

        except Exception as e:
            log_error(f"生成基金 {fund_code} 经理信息失败: {e}")
            return {}

    def health_check(self) -> bool:
        """简化数据源始终健康"""
        return True
