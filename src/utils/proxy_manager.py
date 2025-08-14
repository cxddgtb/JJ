"""
代理管理器 - 自动获取和管理代理IP
"""
import requests
import random
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from .logger import log_info, log_warning, log_error, log_debug

@dataclass
class ProxyInfo:
    """代理信息"""
    ip: str
    port: int
    protocol: str = 'http'
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    speed: float = 0.0
    last_check: float = 0.0
    success_count: int = 0
    fail_count: int = 0

    @property
    def url(self) -> str:
        """获取代理URL"""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.ip}:{self.port}"
        return f"{self.protocol}://{self.ip}:{self.port}"

    @property
    def success_rate(self) -> float:
        """成功率"""
        total = self.success_count + self.fail_count
        return self.success_count / total if total > 0 else 0.0

    def __str__(self):
        return f"{self.ip}:{self.port} (成功率: {self.success_rate:.2%})"

class ProxyManager:
    """代理管理器"""

    def __init__(self, max_proxies=50, check_timeout=10):
        self.max_proxies = max_proxies
        self.check_timeout = check_timeout
        self.proxies = []
        self.lock = threading.Lock()
        self.last_update = 0
        self.update_interval = 3600  # 1小时更新一次

        # 代理源列表
        self.proxy_sources = [
            'https://www.proxy-list.download/api/v1/get?type=http',
            'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
            'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt',
            'https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt',
            'https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all',
            'https://www.proxynova.com/proxy-server-list/',
            'https://free-proxy-list.net/',
        ]

        # 测试URL列表
        self.test_urls = [
            'http://httpbin.org/ip',
            'http://icanhazip.com',
            'http://ident.me',
            'http://ipinfo.io/ip'
        ]

    def fetch_proxies_from_api(self, url: str) -> List[str]:
        """从API获取代理列表"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            # 提取IP:PORT格式的代理
            proxy_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]{1,5}\b'
            proxies = re.findall(proxy_pattern, response.text)

            log_debug(f"从 {url} 获取到 {len(proxies)} 个代理")
            return proxies[:100]  # 限制数量

        except Exception as e:
            log_warning(f"获取代理失败 {url}: {e}")
            return []

    def fetch_proxies_from_webpage(self, url: str) -> List[str]:
        """从网页爬取代理"""
        try:
            from bs4 import BeautifulSoup

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            proxies = []

            # 不同网站的解析规则
            if 'proxynova.com' in url:
                rows = soup.find_all('tr')
                for row in rows[1:]:  # 跳过表头
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        ip = cells[0].text.strip()
                        port = cells[1].text.strip()
                        if ip and port:
                            proxies.append(f"{ip}:{port}")

            elif 'free-proxy-list.net' in url:
                rows = soup.find('tbody').find_all('tr') if soup.find('tbody') else []
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        ip = cells[0].text.strip()
                        port = cells[1].text.strip()
                        if ip and port:
                            proxies.append(f"{ip}:{port}")

            log_debug(f"从 {url} 爬取到 {len(proxies)} 个代理")
            return proxies[:50]  # 限制数量

        except Exception as e:
            log_warning(f"爬取代理失败 {url}: {e}")
            return []

    def check_proxy(self, proxy_str: str) -> Optional[ProxyInfo]:
        """检测代理可用性"""
        try:
            ip, port = proxy_str.split(':')
            port = int(port)

            proxy_info = ProxyInfo(ip=ip, port=port)
            proxy_dict = {
                'http': proxy_info.url,
                'https': proxy_info.url
            }

            # 随机选择测试URL
            test_url = random.choice(self.test_urls)

            start_time = time.time()
            response = requests.get(
                test_url,
                proxies=proxy_dict,
                timeout=self.check_timeout,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )

            if response.status_code == 200:
                proxy_info.speed = time.time() - start_time
                proxy_info.last_check = time.time()
                proxy_info.success_count = 1
                log_debug(f"代理可用: {proxy_info}")
                return proxy_info

        except Exception as e:
            log_debug(f"代理检测失败 {proxy_str}: {e}")

        return None

    def update_proxy_list(self):
        """更新代理列表"""
        if time.time() - self.last_update < self.update_interval:
            return

        log_info("开始更新代理列表...")
        all_proxy_strings = []

        # 从所有源获取代理
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []

            for source in self.proxy_sources:
                if 'api' in source or 'raw.githubusercontent.com' in source:
                    future = executor.submit(self.fetch_proxies_from_api, source)
                else:
                    future = executor.submit(self.fetch_proxies_from_webpage, source)
                futures.append(future)

            for future in as_completed(futures):
                try:
                    proxies = future.result(timeout=60)
                    all_proxy_strings.extend(proxies)
                except Exception as e:
                    log_warning(f"获取代理源失败: {e}")

        # 去重
        unique_proxies = list(set(all_proxy_strings))
        log_info(f"获取到 {len(unique_proxies)} 个唯一代理，开始检测...")

        # 并发检测代理可用性
        valid_proxies = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(self.check_proxy, proxy) for proxy in unique_proxies[:200]]

            for i, future in enumerate(as_completed(futures)):
                try:
                    proxy_info = future.result(timeout=30)
                    if proxy_info:
                        valid_proxies.append(proxy_info)

                        # 限制代理数量
                        if len(valid_proxies) >= self.max_proxies:
                            break

                    # 显示进度
                    if (i + 1) % 20 == 0:
                        log_info(f"已检测 {i + 1} 个代理，发现 {len(valid_proxies)} 个可用")

                except Exception as e:
                    log_debug(f"代理检测异常: {e}")

        # 按速度排序
        valid_proxies.sort(key=lambda x: x.speed)

        with self.lock:
            self.proxies = valid_proxies
            self.last_update = time.time()

        log_info(f"代理列表更新完成，共 {len(valid_proxies)} 个可用代理")

    def get_proxy(self) -> Optional[ProxyInfo]:
        """获取一个可用代理"""
        with self.lock:
            if not self.proxies:
                return None

            # 优先选择成功率高的代理
            good_proxies = [p for p in self.proxies if p.success_rate > 0.5 or p.fail_count == 0]
            if good_proxies:
                return random.choice(good_proxies)
            else:
                return random.choice(self.proxies) if self.proxies else None

    def get_proxy_dict(self) -> Optional[Dict[str, str]]:
        """获取代理字典格式"""
        proxy = self.get_proxy()
        if proxy:
            return {
                'http': proxy.url,
                'https': proxy.url
            }
        return None

    def mark_proxy_success(self, proxy_url: str):
        """标记代理成功"""
        with self.lock:
            for proxy in self.proxies:
                if proxy.url == proxy_url:
                    proxy.success_count += 1
                    break

    def mark_proxy_failed(self, proxy_url: str):
        """标记代理失败"""
        with self.lock:
            for proxy in self.proxies:
                if proxy.url == proxy_url:
                    proxy.fail_count += 1
                    # 如果失败太多次，移除代理
                    if proxy.fail_count > 10 and proxy.success_rate < 0.1:
                        self.proxies.remove(proxy)
                        log_debug(f"移除失败代理: {proxy}")
                    break

    def get_stats(self) -> Dict:
        """获取代理统计信息"""
        with self.lock:
            if not self.proxies:
                return {'total': 0, 'avg_speed': 0, 'avg_success_rate': 0}

            total = len(self.proxies)
            avg_speed = sum(p.speed for p in self.proxies) / total
            avg_success_rate = sum(p.success_rate for p in self.proxies) / total

            return {
                'total': total,
                'avg_speed': avg_speed,
                'avg_success_rate': avg_success_rate,
                'best_proxy': min(self.proxies, key=lambda x: x.speed) if self.proxies else None
            }

    def start_auto_update(self):
        """启动自动更新线程"""
        def update_loop():
            while True:
                try:
                    self.update_proxy_list()
                    time.sleep(self.update_interval)
                except Exception as e:
                    log_error(f"代理自动更新失败: {e}")
                    time.sleep(300)  # 出错后5分钟重试

        thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()
        log_info("代理自动更新线程已启动")

# 全局代理管理器实例
proxy_manager = ProxyManager()

def get_random_proxy():
    """获取随机代理"""
    return proxy_manager.get_proxy_dict()

def update_proxies():
    """更新代理列表"""
    proxy_manager.update_proxy_list()

def get_proxy_stats():
    """获取代理统计"""
    return proxy_manager.get_stats()

if __name__ == "__main__":
    # 测试代理管理器
    pm = ProxyManager(max_proxies=10)
    pm.update_proxy_list()

    stats = pm.get_stats()
    print(f"代理统计: {stats}")

    # 测试获取代理
    for i in range(5):
        proxy = pm.get_proxy_dict()
        if proxy:
            print(f"代理 {i+1}: {proxy}")
        else:
            print(f"代理 {i+1}: 无可用代理")
