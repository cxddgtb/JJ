import pandas as pd
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import akshare as ak
import time
from datetime import datetime, timedelta
import os

def get_index_fund_data():
    """获取指数基金数据"""
    print(f"开始爬取指数基金数据 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 创建一个空的DataFrame来存储所有数据
    all_data = pd.DataFrame()

    # 定义要爬取的主要指数基金代码和名称
    index_funds = {
        '000300.SH': '沪深300',
        '000905.SH': '中证500',
        '000016.SH': '上证50',
        '399006.SZ': '创业板指',
        '399812.SZ': '中证1000',
        'HSI': '恒生指数',
        '510300.SH': '华泰柏瑞沪深300ETF',
        '510500.SH': '南方中证500ETF',
        '159915.SZ': '易方达恒生H股ETF',
        '513100.SH': '国泰纳斯达克100ETF',
        '513050.SH': '华夏上证50ETF',
        '588000.SH': '华夏上证科创板50ETF',
        '159949.SZ': '华安创业板50ETF',
        '512170.SH': '华宝中证医疗ETF',
        '512880.SH': '国泰中证全指证券公司ETF',
        '515030.SH': '华夏中证新能源汽车ETF',
        '159992.SZ': '嘉实中证新能源ETF',
        '512710.SH': '富国中证军工龙头ETF',
        '515180.SH': '易方达中证红利ETF',
        '515210.SH': '富国中证细分机械设备产业主题ETF',
        '515220.SH': '国泰中证煤炭ETF',
        '515230.SH': '鹏华中证酒ETF',
        '515260.SH': '景顺长城中证科技传媒通信150ETF',
        '515290.SH': '南方中证新能源ETF',
        '515300.SH': '广发中证全指可选消费ETF',
        '515330.SH': '华夏中证细分食品饮料产业主题ETF',
        '515450.SH': '南方中证申万有色金属ETF',
        '515600.SH': '汇添富中证主要消费ETF',
        '515650.SH': '华夏中证人工智能主题ETF',
        '515660.SH': '招商中证银行ETF',
        '515670.SH': '富国中证智能汽车主题ETF',
        '515680.SH': '汇添富中证互联网医疗主题ETF',
        '515690.SH': '华夏中证云计算与大数据主题ETF',
        '515700.SH': '平安中证新能源汽车产业ETF',
        '515790.SH': '招商中证物联网主题ETF',
        '515800.SH': '汇添富中证国企一带一路ETF',
        '515810.SH': '富国中证消费电子主题ETF',
        '515820.SH': '嘉实中证软件服务ETF',
        '515830.SH': '华夏中证新能源汽车ETF',
        '515850.SH': '富国中证农业主题ETF',
        '515860.SH': '广发中证全指能源ETF',
        '515870.SH': '鹏华中证高股息龙头ETF',
        '515880.SH': '招商中证沪港深科技龙头ETF',
        '515890.SH': '嘉实中证医药健康100策略ETF',
        '515900.SH': '华夏中证5G通信主题ETF',
        '515910.SH': '南方中证申万有色金属ETF',
        '515920.SH': '富国中证科技50策略ETF',
        '515930.SH': '华夏中证半导体ETF',
        '515940.SH': '广发中证全指家用电器ETF',
        '515950.SH': '富国中证银行ETF',
        '515960.SH': '华夏中证新能源汽车ETF',
        '515970.SH': '招商中证银行ETF',
        '515980.SH': '南方中证全指房地产ETF',
        '515990.SH': '嘉实中证央企创新驱动ETF',
        'SPY': '标普500指数ETF',
        'QQQ': '纳斯达克100指数ETF',
        'IWM': '罗素2000指数ETF',
        'VTI': '美国全市场ETF',
        'GLD': '黄金ETF',
        'USO': '原油ETF',
        'TLT': '20年以上美国国债ETF',
        'AGG': '美国综合债券ETF',
    }

    # 计算日期范围（近5年）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5*365)

    # 遍历所有指数基金
    for code, name in index_funds.items():
        try:
            print(f"正在获取 {name} ({code}) 的数据...")

            # 尝试使用yfinance获取数据
            if code.endswith('.SH') or code.endswith('.SZ'):
                # 中国ETF，使用akshare获取数据
                try:
                    # 格式化代码
                    ak_code = code.split('.')[0]
                    if code.endswith('.SH'):
                        ak_code = f"sh{ak_code}"
                    else:
                        ak_code = f"sz{ak_code}"

                    # 获取ETF数据
                    df = ak.fund_etf_hist_em(symbol=ak_code, start_date=start_date.strftime('%Y%m%d'), end_date=end_date.strftime('%Y%m%d'))

                    if not df.empty:
                        # 重命名列
                        df.columns = ['日期', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率']
                        # 添加基金代码和名称
                        df['代码'] = code
                        df['名称'] = name
                        # 重置索引，使日期成为列而不是索引
                        df.reset_index(inplace=True)
                        # 添加到总数据
                        all_data = pd.concat([all_data, df])
                        print(f"成功获取 {name} ({code}) 的数据，共 {len(df)} 条记录")
                    else:
                        print(f"未获取到 {name} ({code}) 的数据")
                except Exception as e:
                    print(f"使用akshare获取 {name} ({code}) 数据失败: {str(e)}")
                    # 尝试使用yfinance
                    try:
                        yf_code = code.split('.')[0] + '.SS' if code.endswith('.SH') else code.split('.')[0] + '.SZ'
                        data = yf.download(yf_code, start=start_date, end=end_date, auto_adjust=False)
                        if not data.empty:
                            data['代码'] = code
                            data['名称'] = name
                            # 重置索引，使日期成为列而不是索引
                            data.reset_index(inplace=True)
                            # 添加到总数据
                            all_data = pd.concat([all_data, data])
                            print(f"使用yfinance成功获取 {name} ({code}) 的数据，共 {len(data)} 条记录")
                        else:
                            print(f"使用yfinance也未获取到 {name} ({code}) 的数据")
                    except Exception as e2:
                        print(f"使用yfinance获取 {name} ({code}) 数据也失败: {str(e2)}")
            else:
                # 海外ETF，使用yfinance获取数据
                try:
                    data = yf.download(code, start=start_date, end=end_date, auto_adjust=False)
                    if not data.empty:
                        data['代码'] = code
                        data['名称'] = name
                        # 重置索引，使日期成为列而不是索引
                        data.reset_index(inplace=True)
                        # 添加到总数据
                        all_data = pd.concat([all_data, data])
                        print(f"成功获取 {name} ({code}) 的数据，共 {len(data)} 条记录")
                    else:
                        print(f"未获取到 {name} ({code}) 的数据")
                except Exception as e:
                    print(f"获取 {name} ({code}) 数据失败: {str(e)}")

            # 添加延迟，避免请求过于频繁
            time.sleep(1)

        except Exception as e:
            print(f"处理 {name} ({code}) 时发生错误: {str(e)}")

    # 保存数据到CSV文件
    if not all_data.empty:
        # 确定日期列的名称
        date_column = 'Date' if 'Date' in all_data.columns else '日期'
        code_column = '代码' if '代码' in all_data.columns else 'Code'

        # 按日期和代码排序
        all_data.sort_values(by=[date_column, code_column], inplace=True)
        # 保存到CSV文件
        all_data.to_csv('index_fund_data.csv', encoding='utf-8-sig', index=False)
        print(f"数据已保存到 index_fund_data.csv，共 {len(all_data)} 条记录")
    else:
        print("未获取到任何数据")

    return all_data

if __name__ == "__main__":
    get_index_fund_data()
