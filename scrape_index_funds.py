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

    # 计算日期范围（近5年）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5*365)

    # 定义要爬取的主要指数基金代码和名称
    index_funds = {
        # 主要指数
        '000300.SH': '沪深300',
        '000905.SH': '中证500',
        '000016.SH': '上证50',
        '399006.SZ': '创业板指',
        '399812.SZ': '中证1000',
        'HSI': '恒生指数',

        # 主要ETF
        '510300.SH': '华泰柏瑞沪深300ETF',
        '510500.SH': '南方中证500ETF',
        '159915.SZ': '易方达恒生H股ETF',
        '513100.SH': '国泰纳斯达克100ETF',
        '513050.SH': '华夏上证50ETF',
        '588000.SH': '华夏上证科创板50ETF',
        '159949.SZ': '华安创业板50ETF',

        # 行业ETF
        '512170.SH': '华宝中证医疗ETF',
        '512880.SH': '国泰中证全指证券公司ETF',
        '515030.SH': '华夏中证新能源汽车ETF',
        '159992.SZ': '嘉实中证新能源ETF',
        '512710.SH': '富国中证军工龙头ETF',
        '515180.SH': '易方达中证红利ETF',
        '515230.SH': '鹏华中证酒ETF',
        '515660.SH': '招商中证银行ETF',
        '515880.SH': '招商中证沪港深科技龙头ETF',
        '515900.SH': '华夏中证5G通信主题ETF',
        '515930.SH': '华夏中证半导体ETF',

        # 海外ETF
        'SPY': '标普500指数ETF',
        'QQQ': '纳斯达克100指数ETF',
        'IWM': '罗素2000指数ETF',
        'VTI': '美国全市场ETF',
        'GLD': '黄金ETF',
        'USO': '原油ETF',
        'TLT': '20年以上美国国债ETF',
        'AGG': '美国综合债券ETF',
    }

    # 创建一个空的DataFrame来存储所有数据
    all_data = pd.DataFrame()

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
                        # 确保日期格式为YYYY-MM-DD
                        df['日期'] = pd.to_datetime(df['日期']).dt.strftime('%Y-%m-%d')
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
                            # 重置索引，使日期成为列
                            data.reset_index(inplace=True)
                            # 确保日期格式为YYYY-MM-DD
                            data['Date'] = pd.to_datetime(data['Date']).dt.strftime('%Y-%m-%d')
                            # 重命名列以保持一致性
                            data.rename(columns={
                                'Date': '日期',
                                'Open': '开盘',
                                'High': '最高',
                                'Low': '最低',
                                'Close': '收盘',
                                'Adj Close': '复权收盘',
                                'Volume': '成交量'
                            }, inplace=True)
                            # 添加基金代码和名称
                            data['代码'] = code
                            data['名称'] = name
                            # 添加缺失的列
                            for col in ['成交额', '振幅', '涨跌幅', '涨跌额', '换手率']:
                                if col not in data.columns:
                                    data[col] = None
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
                        # 重置索引，使日期成为列
                        data.reset_index(inplace=True)
                        # 确保日期格式为YYYY-MM-DD
                        data['Date'] = pd.to_datetime(data['Date']).dt.strftime('%Y-%m-%d')
                        # 重命名列以保持一致性
                        data.rename(columns={
                            'Date': '日期',
                            'Open': '开盘',
                            'High': '最高',
                            'Low': '最低',
                            'Close': '收盘',
                            'Adj Close': '复权收盘',
                            'Volume': '成交量'
                        }, inplace=True)
                        # 添加基金代码和名称
                        data['代码'] = code
                        data['名称'] = name
                        # 添加缺失的列
                        for col in ['成交额', '振幅', '涨跌幅', '涨跌额', '换手率']:
                            if col not in data.columns:
                                data[col] = None
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
        # 按日期和代码排序
        all_data.sort_values(by=['日期', '代码'], inplace=True)

        # 创建一个更整洁的数据结构
        # 1. 创建一个包含所有指数基金最新数据的DataFrame
        latest_data = pd.DataFrame()

        # 2. 获取每个指数基金最新的数据
        for code in all_data['代码'].unique():
            fund_data = all_data[all_data['代码'] == code].copy()
            if not fund_data.empty:
                # 获取最新日期的数据
                latest_date = fund_data['日期'].max()
                latest_row = fund_data[fund_data['日期'] == latest_date].iloc[0:1].copy()
                latest_data = pd.concat([latest_data, latest_row])

        # 3. 按代码排序最新数据
        latest_data.sort_values(by=['代码'], inplace=True)

        # 4. 保存完整数据到CSV文件
        all_data.to_csv('index_fund_data.csv', encoding='utf-8-sig', index=False)
        print(f"完整数据已保存到 index_fund_data.csv，共 {len(all_data)} 条记录")

        # 5. 保存最新数据到CSV文件
        latest_data.to_csv('index_fund_latest.csv', encoding='utf-8-sig', index=False)
        print(f"最新数据已保存到 index_fund_latest.csv，共 {len(latest_data)} 条记录")

        # 6. 创建一个汇总数据文件，包含每个指数基金的基本信息和最新价格
        summary_data = latest_data[['代码', '名称', '日期', '收盘']].copy()
        summary_data.rename(columns={'收盘': '最新价格'}, inplace=True)

        # 计算每个指数基金的涨跌幅
        for code in summary_data['代码'].unique():
            fund_all_data = all_data[all_data['代码'] == code].copy()
            if len(fund_all_data) >= 2:
                # 获取最新和前一天的数据
                sorted_data = fund_all_data.sort_values(by=['日期'])
                latest = sorted_data.iloc[-1]
                previous = sorted_data.iloc[-2]

                # 计算涨跌幅
                if previous['收盘'] != 0:
                    change_pct = (latest['收盘'] - previous['收盘']) / previous['收盘'] * 100
                    summary_data.loc[summary_data['代码'] == code, '涨跌幅'] = round(change_pct, 2)
                else:
                    summary_data.loc[summary_data['代码'] == code, '涨跌幅'] = 0

        # 保存汇总数据
        summary_data.to_csv('index_fund_summary.csv', encoding='utf-8-sig', index=False)
        print(f"汇总数据已保存到 index_fund_summary.csv，共 {len(summary_data)} 条记录")

        return {
            'all_data': all_data,
            'latest_data': latest_data,
            'summary_data': summary_data
        }
    else:
        print("未获取到任何数据")
        return None

if __name__ == "__main__":
    get_index_fund_data()
