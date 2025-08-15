#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI分析模块
使用AI分析基金数据并生成买卖点建议
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
    AI_CONFIG, OUTPUT_DIR, PROCESSED_DATA_DIR, ANALYSIS_RESULTS_DIR,
    INDICATORS_CONFIG, FUND_TYPES, LOG_CONFIG
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

class AIAnalyzer:
    """AI分析器类"""

    def __init__(self, fund_type: str = 'mixed', depth: str = 'medium'):
        """
        初始化AI分析器

        Args:
            fund_type: 基金类型
            depth: 分析深度
        """
        self.fund_type = fund_type
        self.depth = depth
        self.model = AI_CONFIG['default_model']

        # 加载提示词
        self.analysis_prompt = self._load_analysis_prompt()

        # 初始化AI客户端
        self._init_ai_client()

    def _init_ai_client(self):
        """初始化AI客户端"""
        if self.model == 'openai':
            try:
                import openai
                self.ai_client = openai
                self.ai_client.api_key = AI_CONFIG['openai']['api_key']
                logger.info("OpenAI客户端初始化成功")
            except Exception as e:
                logger.error(f"OpenAI客户端初始化失败: {e}")
                raise
        elif self.model == 'baidu':
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
            logger.warning(f"不支持的AI模型: {self.model}")
            raise ValueError(f"不支持的AI模型: {self.model}")

    def _load_analysis_prompt(self) -> str:
        """加载分析提示词"""
        prompt_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                 'templates', 'analysis_prompt.txt')

        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.warning(f"加载分析提示词失败: {e}")
            # 使用默认提示词
            return """
            请基于以下基金数据和新闻，分析当前基金的买卖点。

            基金数据:
            {fund_data}

            新闻数据:
            {news_data}

            请按照以下格式进行分析:
            1. 市场概况: [简要描述当前市场状况]
            2. 基金表现: [分析基金近期表现]
            3. 技术分析: [基于技术指标的分析]
            4. 基本面分析: [基于基本面指标的分析]
            5. 新闻影响: [分析新闻对基金的影响]
            6. 买卖建议: [给出明确的买入/卖出/持有建议]
            7. 风险提示: [提示相关风险]
            """

    def analyze_fund(self, fund_data: Dict[str, Any], news_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析基金数据并生成买卖点建议

        Args:
            fund_data: 基金数据
            news_data: 新闻数据

        Returns:
            分析结果
        """
        logger.info(f"开始分析{self.fund_type}基金")

        # 构建分析数据
        analysis_data = {
            'fund_type': self.fund_type,
            'fund_name': fund_data.get('name', '未知基金'),
            'fund_code': fund_data.get('code', '未知代码'),
            'fund_data': json.dumps(fund_data, ensure_ascii=False),
            'news_data': json.dumps(news_data[:10], ensure_ascii=False),  # 只使用前10条新闻
            'analysis_depth': self.depth,
            'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # 构建分析提示
        analysis_prompt = self.analysis_prompt.format(**analysis_data)

        # 调用AI进行分析
        try:
            if self.model == 'openai':
                response = self._call_openai(analysis_prompt)
            elif self.model == 'baidu':
                response = self._call_baidu(analysis_prompt)
            else:
                raise ValueError(f"不支持的AI模型: {self.model}")

            # 解析分析结果
            analysis_result = self._parse_analysis_result(response)

            # 保存分析结果
            self._save_analysis_result(fund_data.get('code', 'unknown'), analysis_result)

            return analysis_result

        except Exception as e:
            logger.error(f"AI分析失败: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'suggestion': '持有',
                'confidence': 0
            }

    def _call_openai(self, prompt: str) -> str:
        """
        调用OpenAI API

        Args:
            prompt: 分析提示

        Returns:
            AI分析结果
        """
        response = self.ai_client.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "你是一位专业的基金分析师，擅长分析基金数据并给出买卖建议。"},
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
            prompt: 分析提示

        Returns:
            AI分析结果
        """
        response = self.ai_client.simnet(self.analysis_prompt, prompt)

        if response.get('error_code') == 0:
            return response.get('text', '').strip()
        else:
            raise Exception(f"百度AI API调用失败: {response.get('error_msg', '未知错误')}")

    def _parse_analysis_result(self, response: str) -> Dict[str, Any]:
        """
        解析AI分析结果

        Args:
            response: AI分析结果

        Returns:
            解析后的分析结果
        """
        # 初始化结果
        result = {
            'status': 'success',
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'market_overview': '',
            'fund_performance': '',
            'technical_analysis': '',
            'fundamental_analysis': '',
            'news_impact': '',
            'suggestion': '持有',
            'confidence': 0,
            'reasoning': '',
            'risk_warning': ''
        }

        # 尝试解析各个部分
        try:
            # 使用正则表达式提取各个部分
            patterns = {
                'market_overview': r'市场概况[:：]\s*(.*?)(?=基金表现|$)',
                'fund_performance': r'基金表现[:：]\s*(.*?)(?=技术分析|$)',
                'technical_analysis': r'技术分析[:：]\s*(.*?)(?=基本面分析|$)',
                'fundamental_analysis': r'基本面分析[:：]\s*(.*?)(?=新闻影响|$)',
                'news_impact': r'新闻影响[:：]\s*(.*?)(?=买卖建议|$)',
                'suggestion': r'买卖建议[:：]\s*(.*?)(?=风险提示|$)',
                'risk_warning': r'风险提示[:：]\s*(.*?)(?=$)'
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, response, re.DOTALL)
                if match:
                    result[key] = match.group(1).strip()

            # 解析建议
            suggestion_text = result.get('suggestion', '')
            if '买入' in suggestion_text:
                result['suggestion'] = '买入'
                result['confidence'] = 0.7
            elif '卖出' in suggestion_text:
                result['suggestion'] = '卖出'
                result['confidence'] = 0.7
            else:
                result['suggestion'] = '持有'
                result['confidence'] = 0.5

            # 合并推理部分
            reasoning_parts = [
                result.get('market_overview', ''),
                result.get('fund_performance', ''),
                result.get('technical_analysis', ''),
                result.get('fundamental_analysis', ''),
                result.get('news_impact', '')
            ]
            result['reasoning'] = '

'.join(part for part in reasoning_parts if part)

        except Exception as e:
            logger.warning(f"解析AI分析结果失败: {e}")
            result['status'] = 'partial_success'
            result['reasoning'] = response

        return result

    def _save_analysis_result(self, fund_code: str, result: Dict[str, Any]):
        """
        保存分析结果

        Args:
            fund_code: 基金代码
            result: 分析结果
        """
        os.makedirs(ANALYSIS_RESULTS_DIR, exist_ok=True)
        output_file = os.path.join(ANALYSIS_RESULTS_DIR, f'{fund_code}_analysis.json')

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"分析结果已保存至: {output_file}")
        except Exception as e:
            logger.error(f"保存分析结果失败: {e}")

    def batch_analyze(self, fund_data_list: List[Dict[str, Any]], 
                     news_data_list: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        批量分析基金

        Args:
            fund_data_list: 基金数据列表
            news_data_list: 新闻数据列表

        Returns:
            批量分析结果
        """
        logger.info(f"开始批量分析{len(fund_data_list)}只{self.fund_type}基金")

        results = {}

        # 多线程分析
        from concurrent.futures import ThreadPoolExecutor, as_completed

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []

            for fund_data in fund_data_list:
                future = executor.submit(
                    self.analyze_fund,
                    fund_data,
                    news_data_list
                )
                futures.append((fund_data.get('code', 'unknown'), future))

            for fund_code, future in futures:
                try:
                    result = future.result()
                    results[fund_code] = result
                    logger.info(f"已完成{len(results)}/{len(futures)}只基金的分析: {fund_code}")
                except Exception as e:
                    logger.error(f"分析基金{fund_code}失败: {e}")
                    results[fund_code] = {
                        'status': 'error',
                        'message': str(e),
                        'suggestion': '持有',
                        'confidence': 0
                    }

        # 保存批量分析结果
        batch_result_file = os.path.join(
            ANALYSIS_RESULTS_DIR, 
            f'batch_analysis_{self.fund_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )

        try:
            with open(batch_result_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            logger.info(f"批量分析结果已保存至: {batch_result_file}")
        except Exception as e:
            logger.error(f"保存批量分析结果失败: {e}")

        return results

    def generate_market_overview(self, fund_data_list: List[Dict[str, Any]], 
                               news_data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成市场概况

        Args:
            fund_data_list: 基金数据列表
            news_data_list: 新闻数据列表

        Returns:
            市场概况
        """
        logger.info(f"开始生成{self.fund_type}基金市场概况")

        # 构建市场概况提示
        overview_prompt = f"""
        请基于以下基金数据和新闻，生成{self.fund_type}基金的市场概况。

        基金数据概览:
        - 基金总数: {len(fund_data_list)}
        - 平均收益率: {np.mean([d.get('ytd_return', 0) for d in fund_data_list]):.2%}
        - 平均波动率: {np.mean([d.get('volatility', 0) for d in fund_data_list]):.2%}

        新闻数据概览:
        - 新闻总数: {len(news_data_list)}
        - 主要新闻主题: {', '.join(list(set([n.get('category', '未知') for n in news_data_list[:10]])))}

        请生成一段简洁的市场概况，包括:
        1. 当前市场整体状况
        2. {self.fund_type}基金整体表现
        3. 主要影响因素
        4. 未来趋势展望
        """

        # 调用AI生成市场概况
        try:
            if self.model == 'openai':
                response = self._call_openai(overview_prompt)
            elif self.model == 'baidu':
                response = self._call_baidu(overview_prompt)
            else:
                raise ValueError(f"不支持的AI模型: {self.model}")

            # 解析市场概况
            market_overview = {
                'overview': response,
                'generated_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'fund_type': self.fund_type
            }

            # 保存市场概况
            overview_file = os.path.join(
                ANALYSIS_RESULTS_DIR, 
                f'market_overview_{self.fund_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            )

            with open(overview_file, 'w', encoding='utf-8') as f:
                json.dump(market_overview, f, ensure_ascii=False, indent=2)

            logger.info(f"市场概况已生成并保存至: {overview_file}")

            return market_overview

        except Exception as e:
            logger.error(f"生成市场概况失败: {e}")
            return {
                'overview': f"生成市场概况失败: {str(e)}",
                'generated_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'fund_type': self.fund_type
            }


if __name__ == '__main__':
    # 测试代码
    import argparse

    parser = argparse.ArgumentParser(description='基金数据分析工具')
    parser.add_argument('--fund-type', type=str, default='mixed', 
                       help='基金类型 (mixed/stock/bond/money_market/qdii)')
    parser.add_argument('--depth', type=str, default='medium', 
                       help='分析深度 (basic/medium/deep)')

    args = parser.parse_args()

    # 创建AI分析器
    analyzer = AIAnalyzer(fund_type=args.fund_type, depth=args.depth)

    # 测试数据
    test_fund_data = {
        'name': '测试混合型基金',
        'code': '000001',
        'nav': 1.5,
        'nav_date': '2023-06-01',
        'ytd_return': 0.05,
        'volatility': 0.1,
        'sharpe_ratio': 0.5,
        'max_drawdown': -0.05
    }

    test_news_data = [
        {
            'title': '市场迎来重大利好政策',
            'content': '政府出台了一系列支持资本市场发展的政策，预计将提振市场信心。',
            'publish_time': '2023-06-01',
            'source': '财经新闻'
        },
        {
            'title': '基金行业监管趋严',
            'content': '监管部门加强对基金行业的监管，要求提高信息披露透明度。',
            'publish_time': '2023-05-30',
            'source': '证券时报'
        }
    ]

    # 执行分析
    result = analyzer.analyze_fund(test_fund_data, test_news_data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
