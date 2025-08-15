#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import logging.handlers
from datetime import datetime

def setup_logger(name, level=logging.INFO, log_file=None):
    """
    设置日志记录器

    Args:
        name (str): 日志记录器名称
        level (int): 日志级别
        log_file (str): 日志文件路径

    Returns:
        logging.Logger: 日志记录器
    """
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 避免重复添加处理器
    if logger.handlers:
        return logger

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 使用RotatingFileHandler，限制日志文件大小
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

if __name__ == '__main__':
    # 测试日志功能
    logger = setup_logger('test', log_file='logs/test.log')
    logger.info('这是一条测试日志')
    logger.warning('这是一条警告日志')
    logger.error('这是一条错误日志')
