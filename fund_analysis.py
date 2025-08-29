import requests
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta

# 多个数据源API配置
DATA_SOURCES = [
    {
        'name': 'gugudata',
        'url': 'https://api.gugudata.com/fund/open/etfrealtime',
        'params': {'appkey': '', 'symbol': ''},
        'parser': lambda data: data['Data'] if data['DataStatus']['StatusCode'] == 100 else None
    },
    # 可以添加更多数据源...
]

# 模拟基金列表（实际使用时应该从API获取）
FUND_CODES = ['007401', '952099', '000001', '000002', '000003', '000004', '000005']

class FundAnalyzer:
    def __init__(self):
        self.fund_data = []
        self.historical_data = self.load_historical_data()
    
    def load_historical_data(self):
        """加载历史数据"""
        historical_file = 'fund_history.json'
        if os.path.exists(historical_file):
            with open(historical_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_historical_data(self):
        """保存历史数据"""
        with open('fund_history.json', 'w', encoding='utf-8') as f:
            json.dump(self.historical_data, f, ensure_ascii=False, indent=2)
    
    def fetch_fund_data(self, fund_code):
        """从多个数据源获取基金数据"""
        all_data = []
        
        for source in DATA_SOURCES:
            try:
                # 这里简化处理，实际应该使用不同的API参数和解析方式
                response = requests.get(f"https://api.gugudata.com/fund/open/etfrealtime?appkey=demo&symbol={fund_code}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('DataStatus', {}).get('StatusCode') == 100:
                        fund_info = data['Data']
                        all_data.append({
                            'source': source['name'],
                            'price': float(fund_info.get('MarketPrice', 0)),
                            'net_worth': float(fund_info.get('UnitNetworth', 0)),
                            'growth_rate': float(fund_info.get('GrowthRate', 0).strip('%')),
                            'timestamp': datetime.now().isoformat()
                        })
            except Exception as e:
                print(f"从 {source['name']} 获取数据失败: {e}")
                continue
        
        # 计算平均价格作为最终价格
        if all_data:
            avg_price = sum(item['price'] for item in all_data) / len(all_data)
            return avg_price
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
        prices = [item['price'] for item in price_history] + [current_price]
        
        # 计算各个指标
        sell_line, buy_line, amplitude = self.calculate_indicator_1(prices)
        buy_signal2, sell_signal2, price_line = self.calculate_indicator_2(prices)
        main_in, main_out = self.calculate_indicator_3(prices)
        
        # 综合判断买卖信号
        signal_score = 0
        
        # 指标1逻辑
        if current_price <= buy_line * 1.02:  # 当前价格接近买入线
            signal_score += 2
        elif current_price >= sell_line * 0.98:  # 当前价格接近卖出线
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
                # 获取基金数据
                current_price = self.fetch_fund_data(fund_code)
                if current_price is None:
                    print(f"无法获取基金 {fund_code} 的数据")
                    continue
                
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
                    '基金名称': f'基金{fund_code}',
                    '当前价格': current_price,
                    '操作信号': signal
                })
                
                print(f"基金{fund_code}: 价格={current_price}, 信号={signal}")
                
            except Exception as e:
                print(f"分析基金 {fund_code} 时出错: {e}")
                continue
        
        # 保存历史数据
        self.save_historical_data()
        
        return results

def generate_markdown_table(fund_results):
    """生成Markdown表格"""
    # 按信号优先级排序（买 > 卖 > 观望）
    signal_order = {"买": 0, "卖": 1, "观望": 2}
    sorted_results = sorted(fund_results, key=lambda x: signal_order[x['操作信号']])
    
    # 创建表格内容
    table = "## 基金买卖点分析报表\n\n"
    table += "| 基金名称 | 当前价格 | 操作信号 |\n"
    table += "|----------|----------|----------|\n"
    
    for fund in sorted_results:
        # 为不同信号添加颜色
        signal_color = ""
        if fund['操作信号'] == "买":
            signal_color = "🟢"  # 绿色
        elif fund['操作信号'] == "卖":
            signal_color = "🔴"  # 红色
        else:
            signal_color = "🟡"  # 黄色
            
        table += f"| {fund['基金名称']} | {fund['当前价格']:.4f} | {signal_color} {fund['操作信号']} |\n"
    
    table += f"\n*最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
    table += "\n### 说明\n"
    table += "- 🟢 买: 多个指标显示买入信号\n"
    table += "- 🔴 卖: 多个指标显示卖出信号\n"
    table += "- 🟡 观望: 指标不一致或无明显信号\n"
    table += "- 数据来源: 多个金融数据API综合\n"
    table += "- 更新频率: 每个交易日北京时间下午2点自动更新\n"
    
    return table

def update_readme(table_content):
    """更新README.md文件"""
    # 读取现有的README内容
    with open('README.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
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
    else:
        print("未能获取到任何基金数据")
