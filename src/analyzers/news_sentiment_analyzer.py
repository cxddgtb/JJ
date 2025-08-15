#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import pandas as pd
import numpy as np
import logging
import jieba
import jieba.analyse
from datetime import datetime
from collections import Counter
import re

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.logger import setup_logger
from utils.config import Config

class NewsSentimentAnalyzer:
    def __init__(self):
        """初始化新闻情感分析器"""
        self.logger = setup_logger('NewsSentimentAnalyzer')

        # 初始化jieba分词
        jieba.initialize()

        # 加载自定义词典
        self.load_custom_dicts()

        # 情感词典
        self.positive_words = self.load_sentiment_dict('positive')
        self.negative_words = self.load_sentiment_dict('negative')

        # 基金相关关键词
        self.fund_keywords = self.load_fund_keywords()

    def load_custom_dicts(self):
        """加载自定义词典"""
        try:
            # 添加基金相关词典
            jieba.load_userdict(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                            'data', 'dicts', 'fund_dict.txt'))
            self.logger.info("自定义词典加载完成")
        except Exception as e:
            self.logger.warning(f"加载自定义词典失败: {str(e)}")

    def load_sentiment_dict(self, sentiment_type):
        """
        加载情感词典

        Args:
            sentiment_type (str): 情感类型，'positive'或'negative'

        Returns:
            set: 情感词集合
        """
        try:
            dict_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                    'data', 'dicts', f'{sentiment_type}_words.txt')

            with open(dict_file, 'r', encoding='utf-8') as f:
                words = set(line.strip() for line in f if line.strip())

            self.logger.info(f"加载{sentiment_type}情感词典完成，共{len(words)}个词")
            return words

        except Exception as e:
            self.logger.warning(f"加载{sentiment_type}情感词典失败: {str(e)}")
            return set()

    def load_fund_keywords(self):
        """
        加载基金相关关键词

        Returns:
            set: 基金关键词集合
        """
        try:
            keywords_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                        'data', 'dicts', 'fund_keywords.txt')

            with open(keywords_file, 'r', encoding='utf-8') as f:
                keywords = set(line.strip() for line in f if line.strip())

            self.logger.info(f"加载基金关键词完成，共{len(keywords)}个词")
            return keywords

        except Exception as e:
            self.logger.warning(f"加载基金关键词失败: {str(e)}")
            return set()

    def preprocess_text(self, text):
        """
        预处理文本

        Args:
            text (str): 原始文本

        Returns:
            str: 处理后的文本
        """
        try:
            # 去除HTML标签
            text = re.sub(r'<[^>]+>', '', text)

            # 去除特殊字符
            text = re.sub(r'[^\w\s]', '', text)

            # 去除多余空格
            text = re.sub(r'\s+', ' ', text).strip()

            return text

        except Exception as e:
            self.logger.error(f"文本预处理失败: {str(e)}")
            return text

    def segment_text(self, text):
        """
        文本分词

        Args:
            text (str): 待分词文本

        Returns:
            list: 分词结果
        """
        try:
            # 使用jieba分词
            words = jieba.lcut(text)

            # 过滤停用词
            stopwords = self.load_stopwords()
            words = [word for word in words if word not in stopwords and len(word) > 1]

            return words

        except Exception as e:
            self.logger.error(f"文本分词失败: {str(e)}")
            return []

    def load_stopwords(self):
        """
        加载停用词表

        Returns:
            set: 停用词集合
        """
        try:
            stopwords_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                         'data', 'dicts', 'stopwords.txt')

            with open(stopwords_file, 'r', encoding='utf-8') as f:
                stopwords = set(line.strip() for line in f if line.strip())

            return stopwords

        except Exception as e:
            self.logger.warning(f"加载停用词表失败: {str(e)}")
            return set()

    def calculate_sentiment(self, text):
        """
        计算文本情感分数

        Args:
            text (str): 待分析文本

        Returns:
            dict: 情感分析结果
        """
        try:
            # 预处理文本
            text = self.preprocess_text(text)

            # 分词
            words = self.segment_text(text)

            if not words:
                return {
                    'score': 0,
                    'positive_count': 0,
                    'negative_count': 0,
                    'positive_words': [],
                    'negative_words': [],
                    'keywords': []
                }

            # 计算情感词数量
            positive_count = sum(1 for word in words if word in self.positive_words)
            negative_count = sum(1 for word in words if word in self.negative_words)

            # 提取情感词
            positive_words = [word for word in words if word in self.positive_words]
            negative_words = [word for word in words if word in self.negative_words]

            # 提取关键词
            keywords = [word for word in words if word in self.fund_keywords]

            # 计算情感分数 (-1 到 1)
            score = (positive_count - negative_count) / len(words)

            return {
                'score': score,
                'positive_count': positive_count,
                'negative_count': negative_count,
                'positive_words': positive_words,
                'negative_words': negative_words,
                'keywords': keywords
            }

        except Exception as e:
            self.logger.error(f"计算文本情感失败: {str(e)}")
            return {
                'score': 0,
                'positive_count': 0,
                'negative_count': 0,
                'positive_words': [],
                'negative_words': [],
                'keywords': []
            }

    def analyze_news_sentiment(self, news_data):
        """
        分析新闻数据情感

        Args:
            news_data (list): 新闻数据列表

        Returns:
            dict: 情感分析结果
        """
        try:
            # 初始化结果
            results = {
                'total_news': len(news_data),
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
                'average_score': 0,
                'keyword_freq': Counter(),
                'news_sentiments': []
            }

            # 计算总情感分数
            total_score = 0

            # 分析每条新闻
            for news in news_data:
                # 合并标题和内容
                text = f"{news.get('title', '')} {news.get('content', '')}"

                # 计算情感
                sentiment = self.calculate_sentiment(text)

                # 添加到结果
                results['news_sentiments'].append({
                    'title': news.get('title', ''),
                    'source': news.get('source', ''),
                    'publish_time': news.get('publish_time', ''),
                    'url': news.get('url', ''),
                    'sentiment_score': sentiment['score'],
                    'sentiment_label': self.get_sentiment_label(sentiment['score']),
                    'keywords': sentiment['keywords']
                })

                # 更新统计信息
                total_score += sentiment['score']

                # 统计情感类型
                if sentiment['score'] > 0.05:
                    results['positive_count'] += 1
                elif sentiment['score'] < -0.05:
                    results['negative_count'] += 1
                else:
                    results['neutral_count'] += 1

                # 更新关键词频率
                results['keyword_freq'].update(sentiment['keywords'])

            # 计算平均情感分数
            results['average_score'] = total_score / len(news_data) if news_data else 0

            # 按情感分数排序
            results['news_sentiments'].sort(key=lambda x: x['sentiment_score'], reverse=True)

            self.logger.info("新闻情感分析完成")
            return results

        except Exception as e:
            self.logger.error(f"分析新闻情感失败: {str(e)}")
            return {}

    def get_sentiment_label(self, score):
        """
        根据情感分数获取情感标签

        Args:
            score (float): 情感分数

        Returns:
            str: 情感标签
        """
        if score > 0.05:
            return '积极'
        elif score < -0.05:
            return '消极'
        else:
            return '中性'

    def extract_topics(self, news_data, top_k=10):
        """
        提取新闻主题

        Args:
            news_data (list): 新闻数据列表
            top_k (int): 返回前k个主题

        Returns:
            list: 主题列表
        """
        try:
            # 合并所有新闻文本
            all_text = ' '.join([f"{news.get('title', '')} {news.get('content', '')}" for news in news_data])

            # 使用TF-IDF提取关键词
            keywords = jieba.analyse.extract_tags(all_text, topK=top_k, withWeight=True)

            # 使用TextRank提取关键词
            textrank_keywords = jieba.analyse.textrank(all_text, topK=top_k, withWeight=True)

            # 合并结果
            topics = []
            for keyword, weight in keywords:
                topics.append({
                    'keyword': keyword,
                    'weight': weight,
                    'method': 'TF-IDF'
                })

            for keyword, weight in textrank_keywords:
                # 检查是否已存在
                exists = any(t['keyword'] == keyword for t in topics)
                if not exists:
                    topics.append({
                        'keyword': keyword,
                        'weight': weight,
                        'method': 'TextRank'
                    })

            # 按权重排序
            topics.sort(key=lambda x: x['weight'], reverse=True)

            # 返回前top_k个主题
            return topics[:top_k]

        except Exception as e:
            self.logger.error(f"提取新闻主题失败: {str(e)}")
            return []

    def analyze_trend_impact(self, sentiment_data, historical_data=None):
        """
        分析新闻对市场趋势的影响

        Args:
            sentiment_data (dict): 情感分析结果
            historical_data (pd.DataFrame): 历史市场数据（可选）

        Returns:
            dict: 趋势影响分析结果
        """
        try:
            # 计算情感强度
            sentiment_intensity = sentiment_data['average_score']

            # 计算情感倾向
            if sentiment_data['positive_count'] > sentiment_data['negative_count']:
                sentiment_trend = '积极'
            elif sentiment_data['positive_count'] < sentiment_data['negative_count']:
                sentiment_trend = '消极'
            else:
                sentiment_trend = '中性'

            # 计算新闻关注度
           关注度 = sentiment_data['total_news']

            # 计算关键词关注度
            top_keywords = sentiment_data['keyword_freq'].most_common(5)

            # 构建分析结果
            impact_analysis = {
                'sentiment_intensity': sentiment_intensity,
                'sentiment_trend': sentiment_trend,
                'news_attention': 关注度,
                'top_keywords': top_keywords,
                'impact_level': self.get_impact_level(sentiment_intensity, 关注度),
                'recommendation': self.get_recommendation(sentiment_intensity, sentiment_trend)
            }

            # 如果有历史数据，分析历史相关性
            if historical_data is not None:
                correlation = self.calculate_historical_correlation(sentiment_data, historical_data)
                impact_analysis['historical_correlation'] = correlation

            self.logger.info("趋势影响分析完成")
            return impact_analysis

        except Exception as e:
            self.logger.error(f"分析趋势影响失败: {str(e)}")
            return {}

    def get_impact_level(self, sentiment_intensity, attention):
        """
        根据情感强度和关注度评估影响级别

        Args:
            sentiment_intensity (float): 情感强度
            attention (int): 关注度

        Returns:
            str: 影响级别
        """
        # 根据情感强度和关注度计算影响得分
        impact_score = abs(sentiment_intensity) * np.log(attention + 1)

        if impact_score > 0.5:
            return '高'
        elif impact_score > 0.2:
            return '中'
        else:
            return '低'

    def get_recommendation(self, sentiment_intensity, sentiment_trend):
        """
        根据情感分析结果给出投资建议

        Args:
            sentiment_intensity (float): 情感强度
            sentiment_trend (str): 情感倾向

        Returns:
            str: 投资建议
        """
        if sentiment_trend == '积极' and sentiment_intensity > 0.1:
            return '积极看好，可适当增仓'
        elif sentiment_trend == '消极' and sentiment_intensity < -0.1:
            return '谨慎观望，可适当减仓'
        else:
            return '市场情绪中性，维持现有仓位'

    def calculate_historical_correlation(self, sentiment_data, historical_data):
        """
        计算情感与历史市场数据的关联性

        Args:
            sentiment_data (dict): 情感分析结果
            historical_data (pd.DataFrame): 历史市场数据

        Returns:
            dict: 关联性分析结果
        """
        try:
            # 这里简化处理，实际应用中需要更复杂的分析
            # 例如计算情感分数与市场涨跌的相关系数

            # 假设historical_data包含'close'和'return'列
            if 'return' not in historical_data.columns:
                historical_data['return'] = historical_data['close'].pct_change()

            # 计算情感分数与市场收益的相关系数
            correlation = sentiment_data['average_score'] * historical_data['return'].mean()

            return {
                'correlation': correlation,
                'strength': '强' if abs(correlation) > 0.5 else '中' if abs(correlation) > 0.2 else '弱'
            }

        except Exception as e:
            self.logger.error(f"计算历史相关性失败: {str(e)}")
            return {}

    def save_sentiment_results(self, results, output_file):
        """
        保存情感分析结果

        Args:
            results (dict): 分析结果
            output_file (str): 输出文件路径
        """
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            # 保存为JSON
            import json
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

            self.logger.info(f"情感分析结果已保存到: {output_file}")

        except Exception as e:
            self.logger.error(f"保存情感分析结果失败: {str(e)}")

    def analyze_news_impact(self, news_data, historical_data=None):
        """
        完整的新闻影响分析流程

        Args:
            news_data (list): 新闻数据列表
            historical_data (pd.DataFrame): 历史市场数据（可选）

        Returns:
            dict: 完整的分析结果
        """
        try:
            # 分析新闻情感
            sentiment_results = self.analyze_news_sentiment(news_data)

            # 提取主题
            topics = self.extract_topics(news_data)

            # 分析趋势影响
            impact_results = self.analyze_trend_impact(sentiment_results, historical_data)

            # 构建完整结果
            complete_results = {
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'sentiment_analysis': sentiment_results,
                'topic_extraction': topics,
                'impact_analysis': impact_results
            }

            self.logger.info("新闻影响分析完成")
            return complete_results

        except Exception as e:
            self.logger.error(f"新闻影响分析失败: {str(e)}")
            return {}


def main():
    """主函数"""
    # 创建新闻情感分析器实例
    analyzer = NewsSentimentAnalyzer()

    # 示例新闻数据
    news_data = [
        {
            'title': '基金市场迎来利好政策',
            'content': '近日，监管部门发布了一系列支持基金行业发展的政策，为市场注入了强劲动力。业内专家表示，这些政策将有助于提升基金行业的整体竞争力。',
            'source': '财经新闻',
            'publish_time': '2023-06-01',
            'url': 'http://example.com/news1'
        },
        {
            'title': '股市波动加剧，基金净值承压',
            'content': '受国际形势和国内经济数据影响，近期股市波动加剧，导致部分基金净值出现较大回撤。投资者应密切关注市场变化，适当调整投资策略。',
            'source': '证券时报',
            'publish_time': '2023-06-02',
            'url': 'http://example.com/news2'
        },
        {
            'title': '新基金发行火热，投资者热情高涨',
            'content': '今年以来，新基金发行市场持续火热，多只基金一日售罄。这表明投资者对资本市场的信心正在逐步恢复。',
            'source': '上海证券报',
            'publish_time': '2023-06-03',
            'url': 'http://example.com/news3'
        }
    ]

    # 分析新闻情感
    sentiment_results = analyzer.analyze_news_sentiment(news_data)
    print(f"平均情感分数: {sentiment_results['average_score']}")

    # 提取主题
    topics = analyzer.extract_topics(news_data)
    print("热门主题:", topics)

    # 完整分析
    complete_results = analyzer.analyze_news_impact(news_data)
    print("完整分析结果:", complete_results)

    # 保存结果
    analyzer.save_sentiment_results(complete_results, 'news_sentiment_results.json')


if __name__ == '__main__':
    main()
