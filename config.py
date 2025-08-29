# config.py
import os

# API配置
GUGUDATA_APPKEY = os.getenv('GUGUDATA_APPKEY', 'YOUR_APPKEY_HERE')
JQDATA_USER = os.getenv('JQDATA_USER', 'YOUR_JQDATA_USER')
JQDATA_PWD = os.getenv('JQDATA_PWD', 'YOUR_JQDATA_PASSWORD')

# 基金列表（可根据需要添加更多基金代码）
FUND_CODES = {
    '161725': '招商中证白酒指数',
    '110022': '易方达消费行业',
    '519674': '银河创新成长',
    '003096': '中欧医疗健康C',
    '005827': '易方达蓝筹精选',
    '260108': '景顺长城新兴成长',
    '001875': '前海开源沪港深优势',
    '110011': '易方达中小盘',
    '163406': '兴全合润分级',
    '001704': '国投瑞银锐意改革'
}

# 数据分析参数
N = 20  # 压力支撑指标参数
M = 32  # 压力支撑指标参数
P1 = 80  # 压力支撑指标参数
P2 = 100  # 压力支撑指标参数
