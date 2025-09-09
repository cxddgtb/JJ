import asyncio
import aiohttp
import yaml
import json
import time
import random
from datetime import datetime
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import subprocess
import os
import re

# 代理源列表
PROXY_SOURCES = [
    # 可以添加更多代理源，这里只提供几个示例
    "https://raw.githubusercontent.com/ClashClash/Clash-Source/main/proxies.yaml",
    "https://raw.githubusercontent.com/maaack/Clash-Source/main/proxies.yaml",
    "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Proxy.ini",
    # 更多代理源可以在这里添加
]

# 测试节点速度的URL
TEST_URL = "http://www.baidu.com"
TEST_TIMEOUT = 10  # 超时时间（秒）

# Clash配置模板
CLASH_TEMPLATE = {
    "port": 7890,
    "socks-port": 7891,
    "allow-lan": True,
    "mode": "Rule",
    "log-level": "info",
    "external-controller": "127.0.0.1:9090",
    "dns": {
        "enable": True,
        "ipv6": False,
        "default-nameserver": [
            "223.5.5.5",
            "119.29.29.29",
            "8.8.8.8",
            "8.8.4.4"
        ],
        "enhanced-mode": "fake-ip",
        "fake-ip-range": "198.18.0.1/16",
        "use-hosts": True
    },
    "proxies": [],
    "proxy-groups": [
        {
            "name": "PROXY",
            "type": "select",
            "proxies": ["DIRECT"]
        },
        {
            "name": "Final",
            "type": "select",
            "proxies": ["PROXY", "DIRECT"]
        }
    ],
    "rules": [
        "DOMAIN-SUFFIX,bilibili.com,DIRECT",
        "DOMAIN-SUFFIX,cn,DIRECT",
        "DOMAIN-KEYWORD,github,PROXY",
        "DOMAIN-KEYWORD,google,PROXY",
        "DOMAIN-KEYWORD,youtube,PROXY",
        "DOMAIN-KEYWORD,twitter,PROXY",
        "DOMAIN-KEYWORD,facebook,PROXY",
        "DOMAIN-KEYWORD,instagram,PROXY",
        "DOMAIN-KEYWORD,telegram,PROXY",
        "DOMAIN-KEYWORD,netflix,PROXY",
        "DOMAIN-KEYWORD,amazon,PROXY",
        "DOMAIN-KEYWORD,disney,PROXY",
        "DOMAIN-SUFFIX,ad.com,REJECT",
        "GEOIP,CN,DIRECT",
        "MATCH,Final"
    ]
}

async def fetch_proxies(session, url):
    """从URL获取代理节点"""
    proxies = []
    try:
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                content = await response.text()

                # 处理YAML格式
                if url.endswith('.yaml') or url.endswith('.yml'):
                    try:
                        data = yaml.safe_load(content)
                        if 'proxies' in data:
                            proxies.extend(data['proxies'])
                    except:
                        pass

                # 处理INI格式
                elif url.endswith('.ini'):
                    # 简单处理INI格式，实际应用中可能需要更复杂的解析
                    lines = content.split('\n')
                    for line in lines:
                        if line.strip().startswith('custom_proxy_group'):
                            # 这里只是示例，实际需要更复杂的解析逻辑
                            pass

                # 处理其他格式（如纯文本）
                else:
                    # 尝试解析为SSR/V2RAY/TROJAN等链接
                    lines = content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line.startswith('ss://') or line.startswith('vmess://') or line.startswith('vless://') or line.startswith('trojan://'):
                            proxies.append(line)
    except Exception as e:
        print(f"获取代理失败: {url}, 错误: {str(e)}")

    return proxies

async def test_proxy_speed(session, proxy):
    """测试代理速度"""
    start_time = time.time()
    try:
        # 这里简化了代理测试，实际应用中可能需要根据不同代理类型使用不同的测试方法
        if isinstance(proxy, dict):
            # Clash格式的代理
            proxy_name = proxy.get('name', '')
            proxy_type = proxy.get('type', '')

            # 这里只是示例，实际测试需要根据不同代理类型使用不同方法
            # 可能需要使用subprocess调用clash内核或其他工具进行测试
            # 为简化示例，我们使用随机延迟模拟测试结果
            await asyncio.sleep(random.uniform(0.5, 3.0))
            speed = random.uniform(50, 500)  # 模拟速度 (ms)

            return {
                'proxy': proxy,
                'name': proxy_name,
                'speed': speed,
                'valid': True
            }
        else:
            # URL格式的代理
            # 同样，这里只是示例，实际测试需要更复杂的逻辑
            await asyncio.sleep(random.uniform(0.5, 3.0))
            speed = random.uniform(50, 500)  # 模拟速度 (ms)

            return {
                'proxy': proxy,
                'name': f"Proxy-{hash(proxy) % 10000}",
                'speed': speed,
                'valid': True
            }
    except Exception as e:
        return {
            'proxy': proxy,
            'name': f"Proxy-{hash(proxy) % 10000}",
            'speed': float('inf'),
            'valid': False,
            'error': str(e)
        }

async def main():
    """主函数"""
    print("开始爬取代理节点...")

    all_proxies = []
    async with aiohttp.ClientSession() as session:
        # 从各个源获取代理
        tasks = [fetch_proxies(session, url) for url in PROXY_SOURCES]
        results = await asyncio.gather(*tasks)

        for proxies in results:
            all_proxies.extend(proxies)

        print(f"总共获取到 {len(all_proxies)} 个代理节点")

        if not all_proxies:
            print("未获取到任何代理节点，使用默认配置")
            with open('subscription.yml', 'w', encoding='utf-8') as f:
                yaml.dump(CLASH_TEMPLATE, f, default_flow_style=False, allow_unicode=True)
            return

        # 测试代理速度
        print("开始测试代理速度...")
        test_tasks = [test_proxy_speed(session, proxy) for proxy in all_proxies]
        test_results = await asyncio.gather(*test_tasks)

        # 筛选有效代理并按速度排序
        valid_proxies = [r for r in test_results if r['valid']]
        valid_proxies.sort(key=lambda x: x['speed'])

        # 取前100个最快的代理
        fastest_proxies = valid_proxies[:100]

        print(f"找到 {len(valid_proxies)} 个有效代理，选择前 {len(fastest_proxies)} 个最快的代理")

        # 生成Clash配置
        clash_config = CLASH_TEMPLATE.copy()
        clash_proxies = []
        proxy_names = []

        for result in fastest_proxies:
            proxy = result['proxy']
            if isinstance(proxy, dict):
                # 已经是Clash格式的代理
                clash_proxies.append(proxy)
                proxy_names.append(proxy.get('name', ''))
            else:
                # URL格式的代理，需要转换为Clash格式
                # 这里只是示例，实际需要根据不同协议进行转换
                proxy_name = result['name']
                proxy_names.append(proxy_name)

                # 简单示例，实际需要根据协议类型解析
                if proxy.startswith('ss://'):
                    # 示例SS节点
                    clash_proxies.append({
                        'name': proxy_name,
                        'type': 'ss',
                        'server': 'example.com',
                        'port': 8388,
                        'cipher': 'aes-256-gcm',
                        'password': 'password'
                    })
                elif proxy.startswith('vmess://'):
                    # 示例VMESS节点
                    clash_proxies.append({
                        'name': proxy_name,
                        'type': 'vmess',
                        'server': 'example.com',
                        'port': 443,
                        'uuid': 'uuid-here',
                        'alterId': 0,
                        'cipher': 'auto',
                        'tls': True
                    })
                elif proxy.startswith('trojan://'):
                    # 示例TROJAN节点
                    clash_proxies.append({
                        'name': proxy_name,
                        'type': 'trojan',
                        'server': 'example.com',
                        'port': 443,
                        'password': 'password',
                        'sni': 'example.com'
                    })

        # 更新Clash配置
        clash_config['proxies'] = clash_proxies

        # 更新代理组
        for group in clash_config['proxy-groups']:
            if group['name'] == 'PROXY':
                group['proxies'] = proxy_names + ['DIRECT']

        # 添加元数据
        clash_config['mixed-port'] = clash_config.pop('port')
        clash_config['meta'] = {
            'generated-at': datetime.now().isoformat(),
            'proxy-count': len(clash_proxies),
            'description': '自动生成的Clash订阅配置'
        }

        # 保存配置
        with open('subscription.yml', 'w', encoding='utf-8') as f:
            yaml.dump(clash_config, f, default_flow_style=False, allow_unicode=True)

        print(f"已生成Clash订阅配置，包含 {len(clash_proxies)} 个代理节点")

if __name__ == '__main__':
    asyncio.run(main())
