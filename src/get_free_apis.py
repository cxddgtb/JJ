#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
获取免费API模块
用于获取可用的免费API列表
"""

import os
import json
import requests
import logging
from datetime import datetime
from typing import List, Dict, Any

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

def get_free_apis() -> List[Dict[str, str]]:
    """
    获取免费API列表

    Returns:
        免费API列表
    """
    return get_free_fund_apis()

def get_free_fund_apis() -> List[Dict[str, str]]:
    """
    获取免费的基金API列表

    Returns:
        免费API列表
    """
    free_apis = []

    # 从GitHub获取免费API列表
    github_url = "https://raw.githubusercontent.com/xxx/fund-free-apis/main/free_apis.txt"
    try:
        response = requests.get(github_url, timeout=10)
        response.raise_for_status()  # 如果状态码不是2xx，则抛出异常
        if response.status_code == 200:
            content = response.text
            for line in content.split('\n'):
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
            logger.info(f"从GitHub获取到{len(free_apis)}个免费API")
    except Exception as e:
        logger.warning(f"从GitHub获取免费API失败: {e}")

    # 从其他源获取API列表
    other_sources = [
        "https://gist.githubusercontent.com/xxx/xxxxx/raw/fund_apis.txt",
        "https://raw.githubusercontent.com/xxx/xxxxx/main/fund_apis.txt"
    ]

    for url in other_sources:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # 如果状态码不是2xx，则抛出异常
            if response.status_code == 200:
                content = response.text
                for line in content.split('\n'):
                    line = line.strip()
                    if line and '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 2:
                            api = {
                                'name': parts[0].strip(),
                                'url': parts[1].strip(),
                                'key': parts[2].strip() if len(parts) > 2 else '',
                                'type': parts[3].strip() if len(parts) > 3 else 'json'
                            }
                            # 检查是否已存在
                            if not any(a['url'] == api['url'] for a in free_apis):
                                free_apis.append(api)
                logger.info(f"从{url}获取到{len([a for a in free_apis if a['url'] == url])}个免费API")
        except Exception as e:
            logger.warning(f"从{url}获取免费API失败: {e}")

    return free_apis

def save_free_apis(apis: List[Dict[str, str]]):
    """
    保存免费API列表到文件

    Args:
        apis: API列表
    """
    if not apis:
        logger.warning("没有API需要保存")
        return
        
    # 确保目录存在
    os.makedirs(os.path.dirname(os.path.dirname(__file__)), exist_ok=True)

    # 保存到文件
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'free_apis.txt')
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for api in apis:
                f.write(f"{api['name']}|{api['url']}|{api['key']}|{api['type']}\n")
        logger.info(f"免费API列表已保存至: {file_path}")
    except Exception as e:
        logger.error(f"保存免费API列表失败: {e}")

def test_api(api: Dict[str, str]) -> bool:
    """
    测试API是否可用

    Args:
        api: API信息

    Returns:
        是否可用
    """
    try:
        # 构建测试URL
        test_url = api['url'].replace('{fund_code}', '000001')
        if api['key']:
            test_url = test_url.replace('{api_key}', api['key'])

        # 发送请求
        response = requests.get(test_url, timeout=10)
        response.raise_for_status()  # 如果状态码不是2xx，则抛出异常

        # 检查响应
        if response.status_code == 200:
            if api['type'] == 'json':
                try:
                    data = response.json()
                    return bool(data)
                except:
                    return False
            else:
                return bool(response.text)
        return False
    except Exception as e:
        logger.debug(f"测试API失败: {api['name']} - {e}")
        return False

def main():
    """主函数"""
    logger.info("开始获取免费API列表")

    # 获取免费API列表
    free_apis = get_free_fund_apis()
    
    if not free_apis:
        logger.warning("未获取到任何免费API")
        return

    # 测试API
    logger.info("开始测试API可用性")
    available_apis = []
    for api in free_apis:
        if test_api(api):
            available_apis.append(api)
            logger.info(f"API可用: {api['name']}")
        else:
            logger.warning(f"API不可用: {api['name']}")

    # 保存可用API
    if available_apis:
        save_free_apis(available_apis)
        logger.info(f"完成，共获取到{len(available_apis)}个可用免费API")
    else:
        logger.warning("没有可用的API")

if __name__ == '__main__':
    main()
