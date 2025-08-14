#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
线程池工具模块
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from typing import Callable, List, Any, Dict, Optional

from .config import CRAWLER_CONFIG

logger = logging.getLogger(__name__)

class ThreadPoolManager:
    """线程池管理器"""

    def __init__(self, max_workers: Optional[int] = None):
        """
        初始化线程池

        Args:
            max_workers: 最大工作线程数，如果为None则使用配置文件中的值
        """
        self.max_workers = max_workers or CRAWLER_CONFIG.get('max_threads', 10)
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        logger.info(f"线程池已初始化，最大工作线程数: {self.max_workers}")

    def submit_task(self, func: Callable, *args, **kwargs) -> Any:
        """
        提交任务到线程池

        Args:
            func: 要执行的函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数

        Returns:
            Future对象
        """
        return self.executor.submit(func, *args, **kwargs)

    def submit_tasks(self, func: Callable, tasks_list: List[Dict[str, Any]]) -> List[Any]:
        """
        批量提交任务到线程池

        Args:
            func: 要执行的函数
            tasks_list: 任务参数列表，每个元素是一个字典，包含函数的参数

        Returns:
            结果列表
        """
        futures = []
        results = []

        # 提交所有任务
        for task_params in tasks_list:
            future = self.submit_task(func, **task_params)
            futures.append(future)

        # 等待所有任务完成并收集结果
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"任务执行出错: {str(e)}", exc_info=True)
                results.append(None)

        return results

    def map_tasks(self, func: Callable, iterable: List[Any]) -> List[Any]:
        """
        使用线程池映射函数到可迭代对象

        Args:
            func: 要执行的函数
            iterable: 可迭代对象

        Returns:
            结果列表
        """
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_item = {executor.submit(func, item): item for item in iterable}

            # 等待所有任务完成并收集结果
            for future in as_completed(future_to_item):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    item = future_to_item[future]
                    logger.error(f"处理项目 {item} 时出错: {str(e)}", exc_info=True)
                    results.append(None)

        return results

    def shutdown(self, wait: bool = True):
        """
        关闭线程池

        Args:
            wait: 是否等待所有任务完成
        """
        self.executor.shutdown(wait=wait)
        logger.info("线程池已关闭")

def run_with_thread_pool(func: Callable, tasks_list: List[Dict[str, Any]], max_workers: Optional[int] = None) -> List[Any]:
    """
    使用线程池运行函数的便捷方法

    Args:
        func: 要执行的函数
        tasks_list: 任务参数列表
        max_workers: 最大工作线程数

    Returns:
        结果列表
    """
    pool_manager = ThreadPoolManager(max_workers)
    try:
        results = pool_manager.submit_tasks(func, tasks_list)
        return results
    finally:
        pool_manager.shutdown()
