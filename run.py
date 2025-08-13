#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金分析系统快速启动脚本
"""

import os
import sys
import subprocess
import time
from datetime import datetime

def check_dependencies():
    """检查依赖是否安装"""
    print("检查依赖包...")
    try:
        import pandas
        import numpy
        import matplotlib
        import seaborn
        import akshare
        import tushare
        import talib
        print("✓ 所有依赖包已安装")
        return True
    except ImportError as e:
        print(f"✗ 缺少依赖包: {e}")
        return False

def install_dependencies():
    """安装依赖包"""
    print("安装依赖包...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ 依赖包安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 依赖包安装失败: {e}")
        return False

def create_directories():
    """创建必要的目录"""
    directories = ['output', 'logs', 'data', 'reports', 'charts', 'config']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    print("✓ 目录创建完成")

def create_config():
    """创建配置文件"""
    config_content = '''{
  "tushare_token": "",
  "max_workers": 10,
  "timeout": 300,
  "output_dir": "output",
  "log_level": "INFO",
  "fund_categories": ["股票型", "混合型", "债券型"],
  "analysis_periods": [7, 30, 90, 180, 365],
  "technical_indicators": ["MA", "MACD", "RSI", "KDJ", "BOLL"],
  "risk_levels": ["低风险", "中风险", "高风险"],
  "market_sources": [
    "东方财富",
    "新浪财经",
    "证券时报",
    "中国证券报",
    "上海证券报"
  ]
}'''
    
    config_file = 'config/config.json'
    if not os.path.exists(config_file):
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
        print("✓ 配置文件创建完成")
    else:
        print("✓ 配置文件已存在")

def run_system():
    """运行基金分析系统"""
    print("\n" + "="*50)
    print("基金数据分析与买卖点生成系统")
    print("="*50)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)
    
    try:
        # 导入并运行主程序
        from main import main
        main()
        print("\n✓ 系统运行完成")
    except Exception as e:
        print(f"\n✗ 系统运行失败: {e}")
        return False
    
    return True

def main():
    """主函数"""
    print("基金分析系统启动器")
    print("="*30)
    
    # 1. 检查依赖
    if not check_dependencies():
        print("\n尝试安装依赖包...")
        if not install_dependencies():
            print("依赖包安装失败，请手动安装: pip install -r requirements.txt")
            return
    
    # 2. 创建目录
    create_directories()
    
    # 3. 创建配置
    create_config()
    
    # 4. 运行系统
    print("\n开始运行基金分析系统...")
    success = run_system()
    
    if success:
        print("\n" + "="*50)
        print("系统运行成功！")
        print("请查看以下目录获取结果：")
        print("- output/: 分析文章和Excel文件")
        print("- charts/: 分析图表")
        print("- reports/: 详细报告")
        print("- logs/: 运行日志")
        print("="*50)
    else:
        print("\n系统运行失败，请检查日志文件获取详细信息。")

if __name__ == "__main__":
    main()
