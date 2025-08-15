#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
工具函数模块
提供各种通用功能
"""

import os
import re
import json
import time
import random
import hashlib
import logging
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import LOG_CONFIG

# 设置日志
logging.basicConfig(
    level=LOG_CONFIG['level'],
    format=LOG_CONFIG['format'],
    handlers=[
        logging.FileHandler(LOG_CONFIG['file']),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Retry:
    """重试装饰器"""

    def __init__(self, max_retries: int = 3, delay: float = 1.0, 
                 exceptions: tuple = (Exception,), backoff: float = 2.0):
        """
        初始化重试装饰器

        Args:
            max_retries: 最大重试次数
            delay: 初始延迟时间
            exceptions: 需要重试的异常
            backoff: 延迟时间增长因子
        """
        self.max_retries = max_retries
        self.delay = delay
        self.exceptions = exceptions
        self.backoff = backoff

    def __call__(self, func: Callable) -> Callable:
        """
        装饰器调用

        Args:
            func: 被装饰的函数

        Returns:
            装饰后的函数
        """
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = self.delay

            while retries < self.max_retries:
                try:
                    return func(*args, **kwargs)
                except self.exceptions as e:
                    retries += 1
                    if retries >= self.max_retries:
                        raise

                    logger.warning(f"函数 {func.__name__} 执行失败，{retries}/{self.max_retries} 次重试: {e}")
                    time.sleep(current_delay)
                    current_delay *= self.backoff

        return wrapper


def get_free_apis() -> List[Dict[str, str]]:
    """
    获取免费API列表

    Returns:
        免费API列表
    """
    return get_free_fund_apis()

def get_free_fund_apis() -> List[Dict[str, str]]:
    """
    获取免费基金API列表

    Returns:
        免费API列表
    """
    free_apis = []

    try:
        # 尝试从文件读取
        file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'free_apis.txt')
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 2:
                            free_apis.append({
                                'name': parts[0].strip(),
                                'url': parts[1].strip(),
                                'key': parts[2].strip() if len(parts) > 2 else '',
                                'type': parts[3].strip() if len(parts) > 3 else 'json'
                            })
            return free_apis
    except Exception as e:
        logger.warning(f"读取免费API列表失败: {e}")

    # 如果文件不存在或读取失败，返回默认的API列表
    return [
        {
            'name': '示例API1',
            'url': 'https://api.example.com/fund_data',
            'key': '',
            'type': 'json'
        },
        {
            'name': '示例API2',
            'url': 'https://data.example.com/fund',
            'key': '',
            'type': 'json'
        }
    ]


def generate_file_hash(file_path: str) -> str:
    """
    生成文件哈希值

    Args:
        file_path: 文件路径

    Returns:
        文件哈希值
    """
    if not os.path.exists(file_path):
        return ''

    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def clean_text(text: str) -> str:
    """
    清洗文本

    Args:
        text: 原始文本

    Returns:
        清洗后的文本
    """
    if not text:
        return ''

    # 去除HTML标签
    text = re.sub(r'<[^>]+>', '', text)

    # 去除多余空白
    text = re.sub(r'\s+', ' ', text).strip()

    # 去除特殊字符
    text = re.sub(r'[^\w\s\u4e00-\u9fff，。！？、；：""''（）【】\-\+*/%=<>]', '', text)

    return text


def extract_dates(text: str) -> List[str]:
    """
    从文本中提取日期

    Args:
        text: 原始文本

    Returns:
        日期列表
    """
    if not text:
        return []

    # 匹配YYYY-MM-DD格式的日期
    pattern = r'\d{4}-\d{1,2}-\d{1,2}'
    dates = re.findall(pattern, text)

    # 过滤无效日期
    valid_dates = []
    for date in dates:
        try:
            datetime.strptime(date, '%Y-%m-%d')
            valid_dates.append(date)
        except ValueError:
            continue

    return valid_dates


def extract_numbers(text: str) -> List[float]:
    """
    从文本中提取数字

    Args:
        text: 原始文本

    Returns:
        数字列表
    """
    if not text:
        return []

    # 匹配数字，包括整数、小数、百分比
    pattern = r'[-+]?\d*\.?\d+%?'
    numbers = re.findall(pattern, text)

    # 转换为浮点数
    float_numbers = []
    for num in numbers:
        try:
            if num.endswith('%'):
                # 处理百分比
                float_num = float(num.rstrip('%')) / 100
            else:
                float_num = float(num)
            float_numbers.append(float_num)
        except ValueError:
            continue

    return float_numbers


def save_to_json(data: Any, file_path: str):
    """
    保存数据到JSON文件

    Args:
        data: 要保存的数据
        file_path: 文件路径
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.debug(f"数据已保存至: {file_path}")
    except Exception as e:
        logger.error(f"保存数据失败: {e}")


def load_from_json(file_path: str) -> Any:
    """
    从JSON文件加载数据

    Args:
        file_path: 文件路径

    Returns:
        加载的数据
    """
    try:
        if not os.path.exists(file_path):
            return None

        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载数据失败: {e}")
        return None


def save_to_csv(data: pd.DataFrame, file_path: str):
    """
    保存数据到CSV文件

    Args:
        data: 要保存的数据
        file_path: 文件路径
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        data.to_csv(file_path, index=False, encoding='utf-8-sig')
        logger.debug(f"数据已保存至: {file_path}")
    except Exception as e:
        logger.error(f"保存数据失败: {e}")


def load_from_csv(file_path: str) -> pd.DataFrame:
    """
    从CSV文件加载数据

    Args:
        file_path: 文件路径

    Returns:
        加载的数据
    """
    try:
        if not os.path.exists(file_path):
            return pd.DataFrame()

        return pd.read_csv(file_path, encoding='utf-8-sig')
    except Exception as e:
        logger.error(f"加载数据失败: {e}")
        return pd.DataFrame()


def download_file(url: str, file_path: str, headers: Optional[Dict] = None, 
                 timeout: int = 30, max_retries: int = 3) -> bool:
    """
    下载文件

    Args:
        url: 文件URL
        file_path: 保存路径
        headers: 请求头
        timeout: 超时时间
        max_retries: 最大重试次数

    Returns:
        是否下载成功
    """
    if headers is None:
        headers = {}

    # 添加默认User-Agent
    if 'User-Agent' not in headers:
        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

    # 确保目录存在
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # 重试下载
    for retry in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout, stream=True)
            response.raise_for_status()

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.debug(f"文件已下载至: {file_path}")
            return True

        except Exception as e:
            logger.warning(f"下载文件失败 (重试 {retry + 1}/{max_retries}): {e}")
            if retry < max_retries - 1:
                time.sleep(2 ** retry)  # 指数退避

    return False


def batch_download(urls: List[str], save_dir: str, file_names: Optional[List[str]] = None,
                  headers: Optional[Dict] = None, timeout: int = 30, 
                  max_workers: int = 5) -> Dict[str, bool]:
    """
    批量下载文件

    Args:
        urls: URL列表
        save_dir: 保存目录
        file_names: 文件名列表，如果为None则使用URL的最后一部分
        headers: 请求头
        timeout: 超时时间
        max_workers: 最大线程数

    Returns:
        下载结果字典
    """
    if file_names is None:
        file_names = [os.path.basename(url) for url in urls]

    if len(urls) != len(file_names):
        logger.error("URL列表和文件名列表长度不一致")
        return {}

    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []

        for url, file_name in zip(urls, file_names):
            file_path = os.path.join(save_dir, file_name)
            future = executor.submit(download_file, url, file_path, headers, timeout)
            futures.append((url, file_name, future))

        for url, file_name, future in futures:
            try:
                success = future.result()
                results[file_name] = success
                logger.debug(f"下载完成: {file_name} - {'成功' if success else '失败'}")
            except Exception as e:
                logger.error(f"下载失败: {file_name} - {e}")
                results[file_name] = False

    return results


def format_number(number: Union[int, float], precision: int = 2) -> str:
    """
    格式化数字

    Args:
        number: 数字
        precision: 小数位数

    Returns:
        格式化后的字符串
    """
    if isinstance(number, str):
        try:
            number = float(number)
        except ValueError:
            return number

    if np.isnan(number):
        return 'N/A'

    if number == 0:
        return '0'

    # 处理百分比
    if abs(number) > 100 or abs(number) < 0.01:
        return f"{number:.{precision}e}"
    else:
        return f"{number:.{precision}f}"


def format_percentage(number: Union[int, float], precision: int = 2) -> str:
    """
    格式化百分比

    Args:
        number: 百分比值 (0-100)
        precision: 小数位数

    Returns:
        格式化后的百分比字符串
    """
    if isinstance(number, str):
        try:
            number = float(number)
        except ValueError:
            return number

    if np.isnan(number):
        return 'N/A'

    return f"{number:.{precision}%}"


def get_time_intervals(start_date: str, end_date: str, interval: str = '1D') -> List[str]:
    """
    获取时间间隔

    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
        interval: 间隔 ('1D'=1天, '1W'=1周, '1M'=1月)

    Returns:
        时间间隔列表
    """
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError as e:
        logger.error(f"日期格式错误: {e}")
        return []

    intervals = []
    current = start

    while current <= end:
        if interval == '1D':
            intervals.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)
        elif interval == '1W':
            intervals.append(current.strftime('%Y-%m-%d'))
            current += timedelta(weeks=1)
        elif interval == '1M':
            intervals.append(current.strftime('%Y-%m-%d'))
            # 下个月的同一天
            year = current.year
            month = current.month + 1
            if month > 12:
                year += 1
                month = 1
            try:
                current = datetime(year, month, current.day)
            except ValueError:
                # 如果下个月没有对应的日期（如1月31日），则使用该月的最后一天
                import calendar
                _, last_day = calendar.monthrange(year, month)
                current = datetime(year, month, last_day)

    return intervals


def validate_fund_code(code: str) -> bool:
    """
    验证基金代码格式

    Args:
        code: 基金代码

    Returns:
        是否为有效的基金代码
    """
    if not code:
        return False

    # 基金代码通常是6位数字
    return re.match(r'^\d{6}$', code) is not None


def calculate_nav_return(nav_series: pd.Series) -> Dict[str, float]:
    """
    计算净值收益率

    Args:
        nav_series: 净值序列

    Returns:
        收益率字典
    """
    if len(nav_series) < 2:
        return {}

    # 计算日收益率
    daily_returns = nav_series.pct_change().dropna()

    # 计算各种收益率
    result = {
        'daily_mean': daily_returns.mean(),
        'daily_std': daily_returns.std(),
        'total_return': (nav_series.iloc[-1] / nav_series.iloc[0]) - 1,
        'annualized_return': (1 + result['total_return']) ** (252 / len(nav_series)) - 1,
        'sharpe_ratio': np.sqrt(252) * daily_returns.mean() / daily_returns.std(),
        'max_drawdown': (nav_series / nav_series.cummax() - 1).min(),
        'volatility': daily_returns.std() * np.sqrt(252)
    }

    return result


def get_market_status() -> Dict[str, str]:
    """
    获取市场状态

    Returns:
        市场状态字典
    """
    now = datetime.now()

    # 判断是否为交易时间
    is_trading_time = (
        now.weekday() < 5 and  # 周一至周五
        9 <= now.hour < 15    # 9:00-15:00
    )

    return {
        'current_time': now.strftime('%Y-%m-%d %H:%M:%S'),
        'is_trading_day': now.weekday() < 5,
        'is_trading_time': is_trading_time,
        'market_status': '交易中' if is_trading_time else '休市'
    }


def init_directories():
    """
    初始化必要的目录
    """
    directories = [
        'outputs',
        'outputs/raw_data',
        'outputs/raw_data/news',
        'outputs/raw_data/funds',
        'outputs/raw_data/funds/nav',
        'outputs/processed_data',
        'outputs/analysis_results',
        'outputs/articles',
        'logs',
        'drivers',
        'templates'
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)

    logger.info("目录初始化完成")


if __name__ == '__main__':
    init_directories()
