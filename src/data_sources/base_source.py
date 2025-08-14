"""基础数据源抽象类"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union
import pandas as pd
from datetime import datetime, timedelta
import requests
import time
import random
from ..utils.logger import log_info, log_warning, log_error, log_debug

class BaseDataSource(ABC):
    """数据源基类"""

    def __init__(self, name: str, priority: int = 1):
        self.name = name
        self.priority = priority  # 优先级，数字越小优先级越高
        self.last_request_time = 0
        self.request_interval = 1  # 请求间隔秒数
        self.max_retries = 3
        self.timeout = 30

        # 请求头轮换
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15'
        ]

    def _get_headers(self) -> Dict[str, str]:
        """获取随机请求头"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }

    def _rate_limit(self):
        """请求频率限制"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.request_interval:
            sleep_time = self.request_interval - elapsed
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def _make_request(self, url: str, params: Dict = None, **kwargs) -> Optional[requests.Response]:
        """发起HTTP请求"""
        self._rate_limit()

        headers = kwargs.pop('headers', self._get_headers())
        timeout = kwargs.pop('timeout', self.timeout)

        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=timeout,
                    **kwargs
                )

                if response.status_code == 200:
                    return response
                elif response.status_code in [403, 429, 530]:
                    log_warning(f"{self.name} 访问受限 (状态码: {response.status_code})，尝试延长等待时间")
                    time.sleep(random.uniform(5, 10))
                else:
                    log_warning(f"{self.name} 请求失败，状态码: {response.status_code}")

            except requests.exceptions.RequestException as e:
                log_warning(f"{self.name} 请求异常 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(random.uniform(2, 5))

        log_error(f"{self.name} 所有请求尝试失败")
        return None

    @abstractmethod
    def get_fund_list(self, limit: int = 100) -> List[Dict]:
        """获取基金列表"""
        pass

    @abstractmethod
    def get_fund_info(self, fund_code: str) -> Dict:
        """获取基金基本信息"""
        pass

    @abstractmethod
    def get_fund_nav_history(self, fund_code: str, days: int = 365) -> pd.DataFrame:
        """获取基金净值历史"""
        pass

    def get_fund_holdings(self, fund_code: str) -> Dict:
        """获取基金持仓信息（可选实现）"""
        log_debug(f"{self.name} 不支持持仓信息获取")
        return {}

    def get_fund_manager(self, fund_code: str) -> Dict:
        """获取基金经理信息（可选实现）"""
        log_debug(f"{self.name} 不支持基金经理信息获取")
        return {}

    def health_check(self) -> bool:
        """健康检查"""
        try:
            # 尝试获取少量数据测试连接
            test_funds = self.get_fund_list(limit=1)
            return len(test_funds) > 0
        except Exception as e:
            log_error(f"{self.name} 健康检查失败: {e}")
            return False
