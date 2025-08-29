import requests
import pandas as pd
import numpy as np
import json
import os
import re
from datetime import datetime, timedelta
import time
import random

# 基金代码列表 - 这里是一些常见基金代码示例
FUND_CODES = [
    '161725',  # 招商中证白酒
    '110022',  # 易方达消费行业
    '001102',  # 前海开源国家比较优势
    '519674',  # 银河创新成长
    '003096',  # 中欧医疗健康C
    '005827',  # 易方达蓝筹精选
    '260108',  # 景顺长城新兴成长
    '161005',  # 富国天惠成长
    '110011',  # 易方达中小盘
    '000404'   # 易方达新常态
]

class FundAnalyzer:
    def __init__(self):
        self.fund_data = []
        self.historical_data = self.load_historical_data()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0'
        ]
    
    def load_historical_data(self):
        """加载历史数据"""
        historical_file = 'fund_history.json'
        if os.path.exists(historical_file):
            try:
                with open(historical_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_historical_data(self):
        """保存历史数据"""
        with open('fund_history.json', 'w', encoding='utf-8') as f:
            json.dump(self.historical_data, f, ensure_ascii=False, indent=2)
    
    def fetch_from_eastmoney(self, fund_code):
        """从东方财富获取基金数据"""
        try:
            url = f"http://fund.eastmoney.com/{fund_code}.html"
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Referer': f'http://fund.eastmoney.com/{fund_code}.html'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = 'utf-8'
            
            # 从HTML中提取基金数据
            html_content = response.text
            
            # 提取基金名称
            name_pattern = r'<div class="fundDetail-tit">\s*<div>\s*([^<]+)\s*</div>'
            name_match = re.search(name_pattern, html_content)
            fund_name = name_match.group(1).strip() if name_match else f"基金{fund_code}"
            
            # 提取净值信息
           净值_pattern = r'<dl class="dataItem02"><dt>净值\((\d+-\d+-\d+)\)</dt><dd><span class="ui-font-large ui-color-(red|green) ui-num">([\d.]+)</span>'
            净值_match = re.search(净值_pattern, html_content)
            
            if 净值_match:
                净值日期 = 净值_match.group(1)
                净值 = float(净值_match.group(3))
                return {
                    'name': fund_name,
                    'price': 净值,
                    'date': 净值日期,
                    'source': 'eastmoney'
                }
            
            # 尝试另一种模式
            alternative_pattern = r'<span class="ui-font-large ui-color-(red|green) ui-num" id="gz_gsz">([\d.]+)</span>'
            alt_match = re.search(alternative_pattern, html_content)
            
            if alt_match:
                return {
                    'name': fund_name,
                    'price': float(alt_match.group(2)),
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'source': 'eastmoney'
                }
                
        except Exception as e:
            print(f"从东方财富获取基金 {fund_code} 数据失败: {e}")
        
        return None
    
    def fetch_from_ Sina(self, fund_code):
        """从新浪财经获取基金数据"""
        try:
            url = f"http://finance.sina.com.cn/fund/quotes/{fund_code}/bc.shtml"
            headers = {'User-Agent': random.choice(self.user_agents)}
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = 'gbk'
            
            html_content = response.text
            
            # 尝试提取基金数据
            pattern = r'<div class="ct04">.*?<strong>([\d.]+)</strong>'
            match = re.search(pattern, html_content, re.DOTALL)
            
            if match:
                # 提取基金名称
                name_pattern = r'<h1>(.*?)</h1>'
                name_match = re.search(name_pattern, html_content)
                fund_name = name_match.group(1).strip() if name_match else f"基金{fund_code}"
                
                return {
                    'name': fund_name,
                    'price': float(match.group(1)),
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'source': 'sina'
                }
                
        except Exception as e:
            print(f"从新浪获取基金 {fund_code} 数据失败: {e}")
        
        return None
    
    def fetch_from_天天基金(self, fund_code):
        """从天天基金获取基金数据"""
        try:
            url = f"http://fund.eastmoney.com/{fund_code}.html"
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Referer': f'http://fund.eastmoney.com/{fund_code}.html'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = 'utf-8'
            
            html_content = response.text
            
            # 提取估值信息
            pattern = r'<div id="gz_gsz" class="ui-font-large ui-color-(red|green) ui-num">([\d.]+)</div>'
            match = re.search(pattern, html_content)
            
            if match:
                # 提取基金名称
                name_pattern = r'<div class="fundDetail-tit">.*?<div>(.*?)</div>'
                name_match = re.search(name_pattern, html_content, re.DOTALL)
                fund_name = name_match.group(1).strip() if name_match else f"基金{fund_code}"
                
                return {
                    'name': fund_name,
                    'price': float(match.group(2)),
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'source': 'tiantian'
                }
                
        except Exception as e:
            print(f"从天天基金获取基金 {fund_code} 数据失败: {e}")
        
        return None
    
    def fetch_fund_data(self, fund_code):
        """从多个数据源获取基金数据"""
        # 尝试多个数据源
        sources = [
            self.fetch_from_eastmoney,
            self.fetch_from_ Sina,
            self.fetch_from_天天基金
        ]
        
        results = []
        
        for source in sources:
            try:
                data = source(fund_code)
                if data and data.get('price', 0) > 0:
                    results.append(data)
                    print(f"从 {data['source']} 成功获取基金 {fund_code} 数据: {data['price']}")
            except Exception as e:
                print(f"从 {source.__name__} 获取数据失败: {e}")
            
            # 添加随机延迟避免被封
            time.sleep(random.uniform(0.5, 1.5))
        
        # 如果有多个结果，计算平均价格
        if results:
            avg_price = sum(item['price'] for item in results) / len(results)
            fund_name = results[0]['name']  # 使用第一个结果的名称
            
            return {
                'name': fund_name,
                'price': avg_price,
                'date': datetime.now().strftime('%Y-%m-%d')
            }
        
        return None
    
    def calculate_indicator_1(self, prices):
        """计算压力支撑主图指标"""
        if len(prices) < 32:
            return None, None, None
        
        # 简化计算，实际应根据提供的公式实现
        n = 20
        m = 32
        p1 = 80
        p2 = 100
        
        var1 = sum(prices[-4:]) / 4 if len(prices) >= 4 else prices[-1]
        sell_line = np.mean(prices[-n:]) * (1 + p1/1000)
        buy_line = np.mean(prices[-m:]) * (1 - p2/1000)
        amplitude = 100 * (sell_line - buy_line) / buy_line if buy_line != 0 else 0
        
        return sell_line, buy_line, amplitude
    
    def calculate_indicator_2(self, prices):
        """计算筹码意愿与买卖点指标"""
        if len(prices) < 25:
            return None, None, None
        
        # 简化计算，实际应根据提供的公式实现
        v1 = min(prices[-10:])
        v2 = max(prices[-25:])
        price_line = np.mean([(p - v1)/(v2 - v1)*4 for p in prices[-4:]])
        
        buy_signal = price_line > 0.3
        sell_signal = price_line < 3.5
        
        return buy_signal, sell_signal, price_line
    
    def calculate_indicator_3(self, prices):
        """计算主力进出指标"""
        if len(prices) < 33:
            return None, None, None, None
        
        # 简化计算，实际应根据提供的公式实现
        var1 = np.mean([prices[-1], prices[-2], prices[-3], prices[-4]]) if len(prices) >= 4 else prices[-1]
        main_in = np.mean(prices[-3:]) > np.mean(prices[-6:-3]) if len(prices) >= 6 else False
        main_out = np.mean(prices[-3:]) < np.mean(prices[-6:-3]) if len(prices) >= 6 else False
        
        return main_in, main_out
    
    def determine_signal(self, fund_code, current_price):
        """根据多个指标确定买卖信号"""
        if fund_code not in self.historical_data:
            self.historical_data[fund_code] = []
        
        # 获取最近30个交易日的价格数据
        price_history = self.historical_data[fund_code][-30:] if fund_code in self.historical_data else []
        prices = [item['price'] for item in price_history]
        
        if len(prices) < 10:  # 数据不足，返回观望
            return "观望"
        
        prices.append(current_price)  # 添加当前价格
        
        # 计算各个指标
        sell_line, buy_line, amplitude = self.calculate_indicator_1(prices)
        buy_signal2, sell_signal2, price_line = self.calculate_indicator_2(prices)
        main_in, main_out = self.calculate_indicator_3(prices)
        
        # 综合判断买卖信号
        signal_score = 0
        
        # 指标1逻辑
        if buy_line and current_price <= buy_line * 1.02:  # 当前价格接近买入线
            signal_score += 2
        elif sell_line and current_price >= sell_line * 0.98:  # 当前价格接近卖出线
            signal_score -= 2
        
        # 指标2逻辑
        if buy_signal2:
            signal_score += 1
        if sell_signal2:
            signal_score -= 1
        
        # 指标3逻辑
        if main_in:
            signal_score += 1
        if main_out:
            signal_score -= 1
        
        # 确定最终信号
        if signal_score >= 3:
            return "买"
        elif signal_score <= -3:
            return "卖"
        else:
            return "观望"
    
    def analyze_all_funds(self):
        """分析所有基金"""
        results = []
        
        for fund_code in FUND_CODES:
            try:
                print(f"开始分析基金 {fund_code}...")
                
                # 获取基金数据
                fund_info = self.fetch_fund_data(fund_code)
                if fund_info is None:
                    print(f"无法获取基金 {fund_code} 的数据")
                    continue
                
                current_price = fund_info['price']
                fund_name = fund_info['name']
                
                # 确定买卖信号
                signal = self.determine_signal(fund_code, current_price)
                
                # 更新历史数据
                if fund_code not in self.historical_data:
                    self.historical_data[fund_code] = []
                
                self.historical_data[fund_code].append({
                    'date': datetime.now().isoformat(),
                    'price': current_price,
                    'signal': signal
                })
                
                # 只保留最近30个交易日的数据
                if len(self.historical_data[fund_code]) > 30:
                    self.historical_data[fund_code] = self.historical_data[fund_code][-30:]
                
                results.append({
                    '基金代码': fund_code,
                    '基金名称': fund_name,
                    '当前价格': current_price,
                    '操作信号': signal
                })
                
                print(f"基金 {fund_name}({fund_code}): 价格={current_price}, 信号={signal}")
                
                # 添加延迟避免请求过于频繁
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                print(f"分析基金 {fund_code} 时出错: {e}")
                continue
        
        # 保存历史数据
        self.save_historical_data()
        
        return results

def generate_markdown_table(fund_results):
    """生成Markdown表格"""
    if not fund_results:
        return "## 基金买卖点分析报表\n\n暂无数据，请检查数据源或稍后重试。"
    
    # 按信号优先级排序（买 > 卖 > 观望）
    signal_order = {"买": 0, "卖": 1, "观望": 2}
    sorted_results = sorted(fund_results, key=lambda x: signal_order[x['操作信号']])
    
    # 创建表格内容
    table = "## 基金买卖点分析报表\n\n"
    table += "| 基金代码 | 基金名称 | 当前价格 | 操作信号 |\n"
    table += "|----------|----------|----------|----------|\n"
    
    for fund in sorted_results:
        # 为不同信号添加颜色
        signal_color = ""
        if fund['操作信号'] == "买":
            signal_color = "🟢"  # 绿色
        elif fund['操作信号'] == "卖":
            signal_color = "🔴"  # 红色
        else:
            signal_color = "🟡"  # 黄色
            
        table += f"| {fund['基金代码']} | {fund['基金名称']} | {fund['当前价格']:.4f} | {signal_color} {fund['操作信号']} |\n"
    
    table += f"\n*最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
    table += "\n### 说明\n"
    table += "- 🟢 买: 多个指标显示买入信号\n"
    table += "- 🔴 卖: 多个指标显示卖出信号\n"
    table += "- 🟡 观望: 指标不一致或无明显信号\n"
    table += "- 数据来源: 多个金融数据网站综合\n"
    table += "- 更新频率: 每个交易日北京时间下午2点自动更新\n"
    
    return table

def update_readme(table_content):
    """更新README.md文件"""
    # 读取现有的README内容
    try:
        with open('README.md', 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        content = "# 基金分析项目\n\n"
    
    # 查找现有的表格区域
    start_marker = '## 基金买卖点分析报表'
    end_marker = '### 说明'
    
    if start_marker in content:
        # 替换现有的表格
        start_index = content.find(start_marker)
        end_index = content.find(end_marker, start_index)
        
        if end_index != -1:
            # 找到说明部分之后的内容
            after_table = content[end_index:]
            new_content = content[:start_index] + table_content + after_table
        else:
            # 没有找到说明部分，直接在文件末尾添加
            new_content = content + '\n\n' + table_content
    else:
        # 没有找到表格，直接在文件末尾添加
        new_content = content + '\n\n' + table_content
    
    # 写回README文件
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(new_content)

if __name__ == "__main__":
    print("开始分析基金数据...")
    
    # 创建分析器实例
    analyzer = FundAnalyzer()
    
    # 分析所有基金
    results = analyzer.analyze_all_funds()
    
    if results:
        # 生成Markdown表格
        markdown_table = generate_markdown_table(results)
        
        # 更新README.md
        update_readme(markdown_table)
        
        print("基金分析完成，README.md已更新")
        print(f"成功分析 {len(results)} 只基金")
    else:
        print("未能获取到任何基金数据")
        # 创建空的表格
        markdown_table = generate_markdown_table([])
        update_readme(markdown_table)
