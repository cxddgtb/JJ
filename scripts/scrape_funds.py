"""
从自定义来源抓取基金历史净值/价格数据，并输出统一 JSON。

使用方法：
  python scripts/scrape_funds.py --out data/funds.json

注意：调用前在仓库 Secrets 中配置 TARGET_SOURCES，或在本地环境变量中设置。
TARGET_SOURCES 示例（逗号分隔）:
  https://example.com/fundA|jsonapi,https://example2.com/fundB|html|.price-selector
格式为：URL|type（json/api/html）|可选CSS选择器
"""

import os
import json
import time
import argparse
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

RATE_LIMIT = float(os.getenv('RATE_LIMIT_SECONDS', '1'))


def parse_target_spec(spec: str):
    parts = spec.split('|')
    url = parts[0].strip()
    typ = parts[1].strip() if len(parts) > 1 else 'auto'
    selector = parts[2].strip() if len(parts) > 2 else None
    return url, typ, selector


def fetch_json_api(url):
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.json()


def fetch_html_and_extract(url, selector=None):
    resp = requests.get(url, timeout=20, headers={"User-Agent": "github-actions-bot/1.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    if selector:
        elems = soup.select(selector)
        # 根据页面结构自定义解析
        return [e.get_text(strip=True) for e in elems]
    return soup.get_text()


def normalize_to_timeseries(raw, source_url):
    # 这里给出一个示例的归一化结构，实际需要根据 data source 自行实现
    # 返回 dict: { 'id': ..., 'name': ..., 'history': [ { 'date': 'YYYY-MM-DD', 'value': float }, ... ] }
    if isinstance(raw, dict) and 'history' in raw:
        return {
            'source': source_url,
            'name': raw.get('name') or raw.get('fundName') or source_url,
            'history': raw['history']
        }
    # fallback
    return {
        'source': source_url,
        'name': source_url,
        'history_text': str(raw)[:1000]
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='data/funds.json')
    args = parser.parse_args()

    raw_targets = os.getenv('TARGET_SOURCES', '')
    if not raw_targets:
        print('WARNING: no TARGET_SOURCES provided. 请在仓库 Secrets 中添加 TARGET_SOURCES。')
        return

    targets = [t.strip() for t in raw_targets.split(',') if t.strip()]
    results = []

    for spec in tqdm(targets, desc='targets'):
        url, typ, selector = parse_target_spec(spec)
        try:
            if typ == 'json' or url.lower().endswith('.json'):
                raw = fetch_json_api(url)
            else:
                raw = fetch_html_and_extract(url, selector)
            normalized = normalize_to_timeseries(raw, url)
            results.append(normalized)
        except Exception as e:
            print(f'failed to fetch {url}: {e}')
        time.sleep(RATE_LIMIT)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print('saved ->', args.out)


if __name__ == '__main__':
    main()
