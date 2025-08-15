#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文章润色模块
使用AI对生成的文章进行润色，使其更适合社区发布
"""

import os
import re
import json
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union

from config import (
    AI_CONFIG, OUTPUT_DIR, ARTICLES_DIR, LOG_CONFIG
)

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

class ArticlePolisher:
    """文章润色器类"""

    def __init__(self, fund_type: str = 'mixed'):
        """
        初始化文章润色器

        Args:
            fund_type: 基金类型
        """
        self.fund_type = fund_type

        # 初始化AI客户端
        self._init_ai_client()

        # 加载润色提示词
        self.polish_prompt = self._load_polish_prompt()

    def _init_ai_client(self):
        """初始化AI客户端"""
        if AI_CONFIG['default_model'] == 'openai':
            try:
                import openai
                self.ai_client = openai
                self.ai_client.api_key = AI_CONFIG['openai']['api_key']
                logger.info("OpenAI客户端初始化成功")
            except Exception as e:
                logger.error(f"OpenAI客户端初始化失败: {e}")
                raise
        elif AI_CONFIG['default_model'] == 'baidu':
            try:
                from aip import AipNlp
                self.ai_client = AipNlp(
                    AI_CONFIG['baidu']['api_key'],
                    AI_CONFIG['baidu']['secret_key']
                )
                logger.info("百度AI客户端初始化成功")
            except Exception as e:
                logger.error(f"百度AI客户端初始化失败: {e}")
                raise
        else:
            logger.warning(f"不支持的AI模型: {AI_CONFIG['default_model']}")
            raise ValueError(f"不支持的AI模型: {AI_CONFIG['default_model']}")

    def _load_polish_prompt(self) -> str:
        """加载润色提示词"""
        return """
        请对以下基金分析文章进行润色，使其更加生动、专业且适合社区发布。

        要求：
        1. 保持原文的核心内容和观点不变
        2. 使语言更加生动、专业、有说服力
        3. 增加一些投资相关的专业术语和表达
        4. 优化段落结构，使文章更加易读
        5. 增加一些实用的投资建议和风险提示
        6. 使文章更加吸引人，适合在投资社区发布
        7. 保留原文中的数据和分析结果

        文章：
        {article}

        润色后的文章：
        """

    def polish_article(self, article: str, article_file: str) -> str:
        """
        润色文章

        Args:
            article: 原始文章
            article_file: 文章文件路径

        Returns:
            润色后的文章
        """
        logger.info(f"开始润色文章: {article_file}")

        # 构建润色提示
        polish_prompt = self.polish_prompt.format(article=article)

        # 调用AI进行润色
        try:
            if AI_CONFIG['default_model'] == 'openai':
                polished_article = self._call_openai(polish_prompt)
            elif AI_CONFIG['default_model'] == 'baidu':
                polished_article = self._call_baidu(polish_prompt)
            else:
                raise ValueError(f"不支持的AI模型: {AI_CONFIG['default_model']}")

            # 保存润色后的文章
            polished_file = article_file.replace('.md', '_polished.md')
            self._save_polished_article(polished_article, polished_file)

            return polished_article

        except Exception as e:
            logger.error(f"文章润色失败: {e}")
            return article

    def _call_openai(self, prompt: str) -> str:
        """
        调用OpenAI API

        Args:
            prompt: 润色提示

        Returns:
            润色结果
        """
        response = self.ai_client.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一位专业的金融编辑，擅长润色投资分析文章，使其更加生动、专业且适合社区发布。"},
                {"role": "user", "content": prompt}
            ],
            temperature=AI_CONFIG['openai']['temperature'],
            max_tokens=AI_CONFIG['openai']['max_tokens']
        )

        return response.choices[0].message['content'].strip()

    def _call_baidu(self, prompt: str) -> str:
        """
        调用百度AI API

        Args:
            prompt: 润色提示

        Returns:
            润色结果
        """
        response = self.ai_client.simnet(self.polish_prompt, prompt)

        if response.get('error_code') == 0:
            return response.get('text', '').strip()
        else:
            raise Exception(f"百度AI API调用失败: {response.get('error_msg', '未知错误')}")

    def _save_polished_article(self, article: str, file_path: str):
        """
        保存润色后的文章

        Args:
            article: 润色后的文章
            file_path: 文件路径
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(article)
            logger.info(f"润色后的文章已保存至: {file_path}")
        except Exception as e:
            logger.error(f"保存润色后的文章失败: {e}")

    def batch_polish_articles(self, article_files: List[str]) -> Dict[str, str]:
        """
        批量润色文章

        Args:
            article_files: 文章文件列表

        Returns:
            润色结果字典
        """
        logger.info(f"开始批量润色{len(article_files)}篇文章")

        results = {}

        # 多线程润色
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []

            for article_file in article_files:
                future = executor.submit(
                    self._polish_single_article,
                    article_file
                )
                futures.append((article_file, future))

            for article_file, future in futures:
                try:
                    polished_article = future.result()
                    results[article_file] = polished_article
                    logger.info(f"已完成{len(results)}/{len(futures)}篇文章的润色: {article_file}")
                except Exception as e:
                    logger.error(f"润色文章{article_file}失败: {e}")
                    # 读取原始文章作为结果
                    try:
                        with open(article_file, 'r', encoding='utf-8') as f:
                            results[article_file] = f.read()
                    except Exception as e2:
                        logger.error(f"读取原始文章失败: {e2}")
                        results[article_file] = ""

        return results

    def _polish_single_article(self, article_file: str) -> str:
        """
        润色单篇文章

        Args:
            article_file: 文章文件路径

        Returns:
            润色后的文章
        """
        # 读取原始文章
        try:
            with open(article_file, 'r', encoding='utf-8') as f:
                article = f.read()
        except Exception as e:
            logger.error(f"读取文章失败: {e}")
            raise

        # 润色文章
        return self.polish_article(article, article_file)

    def generate_community_post(self, article: str) -> str:
        """
        生成适合社区发布的帖子

        Args:
            article: 润色后的文章

        Returns:
            社区帖子
        """
        logger.info("生成社区帖子")

        # 构建社区帖子
        post = f"""
        【基金分析】{self.fund_type}基金买卖点分析 - {datetime.now().strftime('%Y-%m-%d')}

        ---

        {article}

        ---

        *免责声明：本文由基金分析系统自动生成，仅供参考，不构成投资建议。投资者应根据自身风险承受能力和投资目标做出投资决策。*

        #基金分析#{self.fund_type}基金#投资建议#基金买卖点
        """

        return post

    def save_community_post(self, post: str, fund_type: str = 'mixed'):
        """
        保存社区帖子

        Args:
            post: 社区帖子
            fund_type: 基金类型
        """
        os.makedirs(ARTICLES_DIR, exist_ok=True)
        post_file = os.path.join(
            ARTICLES_DIR, 
            f'community_post_{fund_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
        )

        try:
            with open(post_file, 'w', encoding='utf-8') as f:
                f.write(post)
            logger.info(f"社区帖子已保存至: {post_file}")
            return post_file
        except Exception as e:
            logger.error(f"保存社区帖子失败: {e}")
            return None


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='润色基金分析文章')
    parser.add_argument('--fund-type', type=str, default='mixed', help='基金类型')
    parser.add_argument('--article-file', type=str, help='文章文件路径')
    parser.add_argument('--batch', action='store_true', help='批量润色')
    parser.add_argument('--community', action='store_true', help='生成社区帖子')

    args = parser.parse_args()

    # 初始化文章润色器
    polisher = ArticlePolisher(fund_type=args.fund_type)

    if args.article_file:
        # 润色单篇文章
        with open(args.article_file, 'r', encoding='utf-8') as f:
            article = f.read()

        polished_article = polisher.polish_article(article, args.article_file)

        if args.community:
            # 生成社区帖子
            post = polisher.generate_community_post(polished_article)
            post_file = polisher.save_community_post(post, args.fund_type)
            print(f"社区帖子已保存至: {post_file}")
        else:
            print("文章润色完成")

    elif args.batch:
        # 批量润色
        article_files = []
        for root, _, files in os.walk(ARTICLES_DIR):
            for file in files:
                if file.endswith('.md') and not file.endswith('_polished.md'):
                    article_files.append(os.path.join(root, file))

        results = polisher.batch_polish_articles(article_files)

        if args.community:
            # 生成社区帖子
            for article_file, polished_article in results.items():
                post = polisher.generate_community_post(polished_article)
                post_file = polisher.save_community_post(post, args.fund_type)
                print(f"社区帖子已保存至: {post_file}")

        print("批量润色完成")

    else:
        print("请指定要润色的文章文件或使用--batch参数批量润色")


if __name__ == '__main__':
    main()
