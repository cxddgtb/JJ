"""
基础爬虫类 - 提供统一的爬虫接口和功能
"""
import requests
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Union, Callable
from urllib.parse import urljoin, urlparse
from fake_useragent import UserAgent
from retrying import retry
import json
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
import pickle
import hashlib
from pathlib import Path

from ..utils.logger import log_info, log_warning, log_error, log_debug, CrawlerLogger
from ..utils.proxy_manager import proxy_manager
from ..config import CRAWLER_CONFIG, SECURITY_CONFIG

@dataclass
class CrawlResult:
    """爬取结果"""
    url: str
    status_code: int
    content: str
    headers: Dict
    cookies: Dict
    response_time: float
    timestamp: float
    success: bool = True
    error: Optional[str] = None

    def to_dict(self):
        return asdict(self)

class RateLimiter:
    """请求限速器"""

    def __init__(self, requests_per_minute=60):
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute
        self.last_request_time = 0
        self.lock = threading.Lock()

    def wait(self):
        """等待到允许的请求时间"""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time

            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)

            self.last_request_time = time.time()

class CacheManager:
    """缓存管理器"""

    def __init__(self, cache_dir='cache', expire_hours=24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.expire_seconds = expire_hours * 3600

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def get(self, key: str) -> Optional[Dict]:
        """获取缓存"""
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            # 检查是否过期
            if time.time() - cache_path.stat().st_mtime > self.expire_seconds:
                cache_path.unlink()
                return None

            with open(cache_path, 'rb') as f:
                return pickle.load(f)

        except Exception as e:
            log_warning(f"读取缓存失败 {key}: {e}")
            return None

    def set(self, key: str, data: Dict):
        """设置缓存"""
        cache_path = self._get_cache_path(key)

        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            log_warning(f"写入缓存失败 {key}: {e}")

    def clear_expired(self):
        """清理过期缓存"""
        for cache_file in self.cache_dir.glob("*.cache"):
            if time.time() - cache_file.stat().st_mtime > self.expire_seconds:
                try:
                    cache_file.unlink()
                    log_debug(f"删除过期缓存: {cache_file.name}")
                except Exception as e:
                    log_warning(f"删除缓存失败: {e}")

class BaseCrawler:
    """基础爬虫类"""

    def __init__(self, name="BaseCrawler", use_proxy=True, use_cache=True, max_workers=10):
        self.name = name
        self.use_proxy = use_proxy
        self.use_cache = use_cache
        self.max_workers = max_workers

        # 初始化组件
        self.session = requests.Session()
        self.ua = UserAgent()
        self.logger = CrawlerLogger()
        self.rate_limiter = RateLimiter(SECURITY_CONFIG['rate_limiting']['requests_per_minute'])
        self.cache_manager = CacheManager() if use_cache else None

        # 配置session
        self._setup_session()

        # 统计信息
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'start_time': time.time()
        }

    def _setup_session(self):
        """配置请求会话"""
        # 设置适配器
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        retry_strategy = Retry(
            total=CRAWLER_CONFIG['retry_times'],
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504]
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # 设置默认超时
        self.session.timeout = CRAWLER_CONFIG['timeout']

    def _get_headers(self, custom_headers=None) -> Dict:
        """获取请求头"""
        headers = {
            'User-Agent': random.choice(SECURITY_CONFIG['user_agents']),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        if custom_headers:
            headers.update(custom_headers)

        return headers

    def _get_cache_key(self, url: str, params: Dict = None) -> str:
        """生成缓存键"""
        key_data = {'url': url}
        if params:
            key_data['params'] = params
        return json.dumps(key_data, sort_keys=True)

    @retry(stop_max_attempt_number=3, wait_exponential_multiplier=1000)
    def _make_request(self, url: str, method='GET', **kwargs) -> CrawlResult:
        """执行HTTP请求"""
        start_time = time.time()
        self.stats['total_requests'] += 1

        try:
            # 限速
            if SECURITY_CONFIG['rate_limiting']['enabled']:
                self.rate_limiter.wait()

            # 设置代理
            if self.use_proxy and proxy_manager:
                proxy_dict = proxy_manager.get_proxy_dict()
                if proxy_dict:
                    kwargs['proxies'] = proxy_dict

            # 设置请求头
            headers = self._get_headers(kwargs.get('headers'))
            kwargs['headers'] = headers

            # 记录请求开始
            self.logger.request_start(url, method)

            # 执行请求
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()

            # 计算响应时间
            response_time = time.time() - start_time

            # 记录成功
            self.logger.request_success(url, response.status_code, response_time)
            self.stats['successful_requests'] += 1

            # 标记代理成功
            if self.use_proxy and 'proxies' in kwargs:
                proxy_manager.mark_proxy_success(kwargs['proxies']['http'])

            # 创建结果对象
            result = CrawlResult(
                url=url,
                status_code=response.status_code,
                content=response.text,
                headers=dict(response.headers),
                cookies=dict(response.cookies),
                response_time=response_time,
                timestamp=time.time(),
                success=True
            )

            return result

        except Exception as e:
            # 记录失败
            self.logger.request_error(url, e)
            self.stats['failed_requests'] += 1

            # 标记代理失败
            if self.use_proxy and 'proxies' in kwargs:
                proxy_manager.mark_proxy_failed(kwargs['proxies']['http'])

            # 创建失败结果
            result = CrawlResult(
                url=url,
                status_code=0,
                content='',
                headers={},
                cookies={},
                response_time=time.time() - start_time,
                timestamp=time.time(),
                success=False,
                error=str(e)
            )

            raise e

    def get(self, url: str, params=None, use_cache=None, **kwargs) -> CrawlResult:
        """GET请求"""
        use_cache = use_cache if use_cache is not None else self.use_cache

        # 检查缓存
        if use_cache and self.cache_manager:
            cache_key = self._get_cache_key(url, params)
            cached_result = self.cache_manager.get(cache_key)

            if cached_result:
                self.stats['cache_hits'] += 1
                log_debug(f"使用缓存: {url}")
                return CrawlResult(**cached_result)

        # 执行请求
        if params:
            kwargs['params'] = params

        result = self._make_request(url, 'GET', **kwargs)

        # 保存缓存
        if use_cache and self.cache_manager and result.success:
            cache_key = self._get_cache_key(url, params)
            self.cache_manager.set(cache_key, result.to_dict())

        return result

    def post(self, url: str, data=None, json=None, **kwargs) -> CrawlResult:
        """POST请求"""
        if data:
            kwargs['data'] = data
        if json:
            kwargs['json'] = json

        return self._make_request(url, 'POST', **kwargs)

    def get_soup(self, url: str, parser='html.parser', **kwargs) -> Optional[BeautifulSoup]:
        """获取BeautifulSoup对象"""
        result = self.get(url, **kwargs)

        if result.success:
            try:
                return BeautifulSoup(result.content, parser)
            except Exception as e:
                log_error(f"解析HTML失败 {url}: {e}")
                return None
        else:
            log_error(f"请求失败 {url}: {result.error}")
            return None

    def get_json(self, url: str, **kwargs) -> Optional[Dict]:
        """获取JSON数据"""
        result = self.get(url, **kwargs)

        if result.success:
            try:
                return json.loads(result.content)
            except Exception as e:
                log_error(f"解析JSON失败 {url}: {e}")
                return None
        else:
            log_error(f"请求失败 {url}: {result.error}")
            return None

    def crawl_urls(self, urls: List[str], callback: Callable = None, **kwargs) -> List[CrawlResult]:
        """并发爬取多个URL"""
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交任务
            future_to_url = {
                executor.submit(self.get, url, **kwargs): url 
                for url in urls
            }

            # 收集结果
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)

                    # 执行回调
                    if callback and result.success:
                        callback(result)

                except Exception as e:
                    log_error(f"爬取URL失败 {url}: {e}")
                    # 创建失败结果
                    failed_result = CrawlResult(
                        url=url,
                        status_code=0,
                        content='',
                        headers={},
                        cookies={},
                        response_time=0,
                        timestamp=time.time(),
                        success=False,
                        error=str(e)
                    )
                    results.append(failed_result)

        return results

    def extract_links(self, soup: BeautifulSoup, base_url: str = None) -> List[str]:
        """提取页面中的链接"""
        links = []

        for link in soup.find_all('a', href=True):
            href = link['href']

            # 处理相对链接
            if base_url and not href.startswith(('http://', 'https://')):
                href = urljoin(base_url, href)

            if href.startswith(('http://', 'https://')):
                links.append(href)

        return list(set(links))  # 去重

    def delay(self, min_delay=None, max_delay=None):
        """随机延迟"""
        if min_delay is None:
            min_delay = CRAWLER_CONFIG['request_delay'][0]
        if max_delay is None:
            max_delay = CRAWLER_CONFIG['request_delay'][1]

        delay_time = random.uniform(min_delay, max_delay)
        time.sleep(delay_time)

    def get_stats(self) -> Dict:
        """获取爬虫统计信息"""
        runtime = time.time() - self.stats['start_time']

        return {
            **self.stats,
            'runtime': runtime,
            'requests_per_second': self.stats['total_requests'] / runtime if runtime > 0 else 0,
            'success_rate': (
                self.stats['successful_requests'] / self.stats['total_requests'] 
                if self.stats['total_requests'] > 0 else 0
            ),
            'cache_hit_rate': (
                self.stats['cache_hits'] / self.stats['total_requests']
                if self.stats['total_requests'] > 0 else 0
            )
        }

    def cleanup(self):
        """清理资源"""
        self.session.close()

        if self.cache_manager:
            self.cache_manager.clear_expired()

        # 输出统计信息
        stats = self.get_stats()
        log_info(f"爬虫 [{self.name}] 统计信息:")
        log_info(f"  总请求: {stats['total_requests']}")
        log_info(f"  成功率: {stats['success_rate']:.2%}")
        log_info(f"  缓存命中率: {stats['cache_hit_rate']:.2%}")
        log_info(f"  平均QPS: {stats['requests_per_second']:.2f}")
        log_info(f"  运行时间: {stats['runtime']:.2f}秒")

if __name__ == "__main__":
    # 测试基础爬虫
    crawler = BaseCrawler("测试爬虫")

    # 测试单个URL
    result = crawler.get("http://httpbin.org/get")
    print(f"请求结果: {result.success}, 状态码: {result.status_code}")

    # 测试多个URL
    urls = [
        "http://httpbin.org/get",
        "http://httpbin.org/user-agent",
        "http://httpbin.org/headers"
    ]

    results = crawler.crawl_urls(urls)
    print(f"批量爬取完成，成功: {sum(1 for r in results if r.success)}/{len(results)}")

    # 显示统计信息
    stats = crawler.get_stats()
    print(f"爬虫统计: {stats}")

    # 清理
    crawler.cleanup()
