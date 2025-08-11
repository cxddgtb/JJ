import os
import json
import logging
import pandas as pd
from datetime import datetime, timedelta

# 配置设置
try:
    from config.settings import settings
except ImportError:
    # 备用方案：直接定义必要设置
    class FallbackSettings:
        OUTPUT_DIR = "output"
    settings = FallbackSettings()

def setup_logging():
    """配置日志系统"""
    log_dir = os.path.join(settings.OUTPUT_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(
        log_dir, 
        f"trading_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def save_data(data, filename, subdir=None):
    """保存数据到文件"""
    output_dir = settings.OUTPUT_DIR
    if subdir:
        output_dir = os.path.join(output_dir, subdir)
        os.makedirs(output_dir, exist_ok=True)
    
    filepath = os.path.join(output_dir, filename)
    
    if isinstance(data, pd.DataFrame):
        data.to_csv(filepath, index=False)
    elif isinstance(data, dict) or isinstance(data, list):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(str(data))
    
    return filepath

def load_data(filename, subdir=None):
    """从文件加载数据"""
    output_dir = settings.OUTPUT_DIR
    if subdir:
        output_dir = os.path.join(output_dir, subdir)
    
    filepath = os.path.join(output_dir, filename)
    
    if not os.path.exists(filepath):
        return None
    
    if filename.endswith('.json'):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    elif filename.endswith('.csv'):
        return pd.read_csv(filepath)
    else:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

def get_trading_date():
    """获取最近的交易日"""
    today = datetime.now()
    # 如果是周末，则返回周五的日期
    if today.weekday() == 5:  # 周六
        return (today - timedelta(days=1)).strftime('%Y-%m-%d')
    elif today.weekday() == 6:  # 周日
        return (today - timedelta(days=2)).strftime('%Y-%m-%d')
    return today.strftime('%Y-%m-%d')
