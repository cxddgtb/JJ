import requests
import pandas as pd
import re
from datetime import datetime

def get_fund_net_value(fund_code):
    """
    获取基金的单位净值、累计净值和日增长率
    """
    url = f"http://fundgz.1234567.com.cn/js/{fund_code}.js"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # 如果请求失败则抛出异常

    # 解析返回的JSONP数据
    match = re.search(r'jsonpgz\((.*)\);', response.text)
    if not match:
        raise ValueError("无法从返回的数据中解析出基金信息")

    fund_data = eval(match.group(1))

    return {
        "基金代码": fund_data["fundcode"],
        "基金名称": fund_data["name"],
        "单位净值": float(fund_data["dwjz"]),
        "估算净值": float(fund_data["gsz"]),
        "估算增长率": float(fund_data["gszzl"]),
        "净值日期": datetime.strptime(fund_data["jzrq"], "%Y-%m-%d").date(),
    }

def get_fund_historical_net_value(fund_code, start_date, end_date):
    """
    获取基金的历史净值数据
    """
    url = f"http://fund.eastmoney.com/f10/F10DataApi.aspx?type=lsjz&code={fund_code}&page=1&sdate={start_date}&edate={end_date}&per=2000"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    # 解析返回的HTML表格
    match = re.search(r'content:"(.*)"', response.text)
    if not match:
        raise ValueError("无法从返回的数据中解析出历史净值")

    html_content = match.group(1)
    df = pd.read_html(html_content, header=0)[0]
    df.rename(columns={"净值日期": "date", "单位净值": "net_value", "累计净值": "accumulated_net_value", "日增长率": "daily_growth_rate"}, inplace=True)
    df["date"] = pd.to_datetime(df["date"])
    df["net_value"] = pd.to_numeric(df["net_value"], errors='coerce')
    df["accumulated_net_value"] = pd.to_numeric(df["accumulated_net_value"], errors='coerce')
    df['daily_growth_rate'] = df['daily_growth_rate'].str.strip('%').astype(float) / 100
    return df

if __name__ == '__main__':
    # 示例：获取一只基金的实时估值和历史净值
    fund_code = "005918"  # 招商中证白酒指数(LOF)A
    
    # 获取实时估值
    try:
        real_time_value = get_fund_net_value(fund_code)
        print("基金实时估值：")
        print(real_time_value)
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"获取基金实时估值失败：{e}")

    # 获取历史净值
    try:
        today = datetime.now()
        start_date = (today - pd.Timedelta(days=365)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        historical_data = get_fund_historical_net_value(fund_code, start_date, end_date)
        print("\n基金历史净值：")
        print(historical_data.head())
        
        # 将历史数据保存到CSV文件
        output_path = f"data/{fund_code}_historical_data.csv"
        historical_data.to_csv(output_path, index=False)
        print(f"\n历史数据已保存到 {output_path}")

    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"获取基金历史净值失败：{e}")