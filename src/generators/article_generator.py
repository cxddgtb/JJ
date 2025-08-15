#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.logger import setup_logger
from utils.config import Config

class ArticleGenerator:
    def __init__(self):
        """初始化文章生成器"""
        self.logger = setup_logger('ArticleGenerator')

    def load_trading_signals(self, signals_file):
        """
        加载交易信号数据

        Args:
            signals_file (str): 交易信号文件路径

        Returns:
            dict: 交易信号数据
        """
        try:
            with open(signals_file, 'r', encoding='utf-8') as f:
                signals_data = json.load(f)

            self.logger.info(f"交易信号数据加载完成，共{len(signals_data.get('funds_signals', []))}只基金")
            return signals_data

        except Exception as e:
            self.logger.error(f"加载交易信号数据失败: {str(e)}")
            return {}

    def load_news_data(self, news_file):
        """
        加载新闻数据

        Args:
            news_file (str): 新闻数据文件路径

        Returns:
            list: 新闻数据列表
        """
        try:
            with open(news_file, 'r', encoding='utf-8') as f:
                news_data = json.load(f)

            self.logger.info(f"新闻数据加载完成，共{len(news_data)}条新闻")
            return news_data

        except Exception as e:
            self.logger.error(f"加载新闻数据失败: {str(e)}")
            return []

    def generate_market_overview(self, trading_signals, news_data):
        """
        生成市场概述

        Args:
            trading_signals (dict): 交易信号数据
            news_data (list): 新闻数据列表

        Returns:
            str: 市场概述文本
        """
        try:
            # 获取市场情绪和影响
            market_sentiment = trading_signals.get('market_sentiment', '未知')
            market_impact = trading_signals.get('market_impact', '未知')

            # 获取买入和卖出信号数量
            funds_signals = trading_signals.get('funds_signals', [])
            buy_count = sum(1 for signal in funds_signals if signal.get('signal') == '买入')
            sell_count = sum(1 for signal in funds_signals if signal.get('signal') == '卖出')
            hold_count = sum(1 for signal in funds_signals if signal.get('signal') == '观望')

            # 获取热门新闻主题
            top_topics = self.extract_top_topics(news_data, 5)

            # 构建市场概述
            overview = f"# 基金市场分析报告

"
            overview += f"**发布时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

"

            overview += "## 市场概述

"
            overview += f"当前市场整体情绪为**{market_sentiment}**，市场新闻影响级别为**{market_impact}**。"
            overview += f"本次分析共涵盖{len(funds_signals)}只基金，其中{buy_count}只基金给出买入信号，"
            overview += f"{sell_count}只基金给出卖出信号，{hold_count}只基金给出观望信号。

"

            if top_topics:
                overview += "近期市场关注的主要热点包括："
                for i, topic in enumerate(top_topics, 1):
                    overview += f"{i}. {topic}；"
                overview = overview.rstrip("；") + "。

"

            return overview

        except Exception as e:
            self.logger.error(f"生成市场概述失败: {str(e)}")
            return "## 市场概述

生成概述时出错
"

    def extract_top_topics(self, news_data, top_n=5):
        """
        提取热门话题

        Args:
            news_data (list): 新闻数据列表
            top_n (int): 返回前N个话题

        Returns:
            list: 热门话题列表
        """
        try:
            # 提取所有新闻的关键词
            all_keywords = []
            for news in news_data:
                content = f"{news.get('title', '')} {news.get('content', '')}"
                keywords = self.extract_keywords(content)
                all_keywords.extend(keywords)

            # 统计关键词频率
            keyword_freq = {}
            for keyword in all_keywords:
                keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1

            # 获取频率最高的前N个关键词
            sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)
            top_keywords = [keyword for keyword, freq in sorted_keywords[:top_n]]

            return top_keywords

        except Exception as e:
            self.logger.error(f"提取热门话题失败: {str(e)}")
            return []

    def extract_keywords(self, text, top_n=10):
        """
        从文本中提取关键词

        Args:
            text (str): 输入文本
            top_n (int): 返回前N个关键词

        Returns:
            list: 关键词列表
        """
        try:
            # 简单的关键词提取（实际应用中可以使用更复杂的算法）
            words = text.split()

            # 过滤停用词和短词
            stopwords = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
            keywords = [word for word in words if len(word) > 1 and word not in stopwords]

            # 统计词频
            keyword_freq = {}
            for keyword in keywords:
                keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1

            # 获取频率最高的前N个关键词
            sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)
            top_keywords = [keyword for keyword, freq in sorted_keywords[:top_n]]

            return top_keywords

        except Exception as e:
            self.logger.error(f"提取关键词失败: {str(e)}")
            return []

    def generate_technical_analysis(self, trading_signals):
        """
        生成技术分析部分

        Args:
            trading_signals (dict): 交易信号数据

        Returns:
            str: 技术分析文本
        """
        try:
            # 获取基金信号
            funds_signals = trading_signals.get('funds_signals', [])

            # 如果没有数据，返回空文本
            if not funds_signals:
                return "## 技术分析

暂无数据
"

            # 统计技术指标信号
            technical_signals = {
                'ma_cross': 0,
                'macd_cross': 0,
                'rsi_oversold': 0,
                'rsi_overbought': 0,
                'bb_lower': 0,
                'bb_upper': 0,
                'stochastic_cross': 0,
                'cci_oversold': 0,
                'cci_overbought': 0,
                'adx_trend': 0
            }

            # 分析每个基金的技术指标
            for fund_signal in funds_signals:
                signal_details = fund_signal.get('signal_details', {})
                technical_factors = signal_details.get('technical_factors', [])

                # 统计技术指标信号
                for factor in technical_factors:
                    if '5日均线上穿20日均线' in factor or '5日均线下穿20日均线' in factor:
                        technical_signals['ma_cross'] += 1
                    elif 'MACD金叉形成' in factor or 'MACD死叉形成' in factor:
                        technical_signals['macd_cross'] += 1
                    elif 'RSI指标从超卖区回升' in factor:
                        technical_signals['rsi_oversold'] += 1
                    elif 'RSI指标进入超买区' in factor:
                        technical_signals['rsi_overbought'] += 1
                    elif '价格下轨反弹' in factor:
                        technical_signals['bb_lower'] += 1
                    elif '价格上轨回落' in factor:
                        technical_signals['bb_upper'] += 1
                    elif 'K值上穿D值' in factor or 'K值下穿D值' in factor:
                        technical_signals['stochastic_cross'] += 1
                    elif 'CCI从-100以下回升' in factor:
                        technical_signals['cci_oversold'] += 1
                    elif 'CCI从+100以上回落' in factor:
                        technical_signals['cci_overbought'] += 1
                    elif 'ADX > 25' in factor:
                        technical_signals['adx_trend'] += 1

            # 构建技术分析
            analysis = "## 技术分析

"

            # 计算技术指标信号占比
            total_signals = sum(technical_signals.values())
            if total_signals > 0:
                analysis += "从技术指标来看，各指标信号分布如下：

"

                # 移动平均线信号
                ma_count = technical_signals['ma_cross']
                if ma_count > 0:
                    ma_percent = ma_count / total_signals * 100
                    analysis += f"- **移动平均线信号**: {ma_count}个 ({ma_percent:.1f}%)
"
                    analysis += "  - 短期均线上穿长期均线，显示市场可能进入上升趋势
"
                    analysis += "  - 短期均线下穿长期均线，显示市场可能进入下降趋势

"

                # MACD信号
                macd_count = technical_signals['macd_cross']
                if macd_count > 0:
                    macd_percent = macd_count / total_signals * 100
                    analysis += f"- **MACD信号**: {macd_count}个 ({macd_percent:.1f}%)
"
                    analysis += "  - MACD金叉形成，显示市场动能可能增强
"
                    analysis += "  - MACD死叉形成，显示市场动能可能减弱

"

                # RSI信号
                rsi_oversold_count = technical_signals['rsi_oversold']
                rsi_overbought_count = technical_signals['rsi_overbought']
                if rsi_oversold_count > 0 or rsi_overbought_count > 0:
                    rsi_percent = (rsi_oversold_count + rsi_overbought_count) / total_signals * 100
                    analysis += f"- **RSI信号**: {rsi_oversold_count + rsi_overbought_count}个 ({rsi_percent:.1f}%)
"
                    if rsi_oversold_count > 0:
                        analysis += "  - RSI指标从超卖区回升，显示市场可能触底反弹
"
                    if rsi_overbought_count > 0:
                        analysis += "  - RSI指标进入超买区，显示市场可能面临回调压力

"

                # 布林带信号
                bb_lower_count = technical_signals['bb_lower']
                bb_upper_count = technical_signals['bb_upper']
                if bb_lower_count > 0 or bb_upper_count > 0:
                    bb_percent = (bb_lower_count + bb_upper_count) / total_signals * 100
                    analysis += f"- **布林带信号**: {bb_lower_count + bb_upper_count}个 ({bb_percent:.1f}%)
"
                    if bb_lower_count > 0:
                        analysis += "  - 价格下轨反弹，显示市场可能获得支撑
"
                    if bb_upper_count > 0:
                        analysis += "  - 价格上轨回落，显示市场可能面临阻力

"

                # 随机指标信号
                stochastic_count = technical_signals['stochastic_cross']
                if stochastic_count > 0:
                    stochastic_percent = stochastic_count / total_signals * 100
                    analysis += f"- **随机指标信号**: {stochastic_count}个 ({stochastic_percent:.1f}%)
"
                    analysis += "  - K值上穿D值，显示市场可能进入上升趋势
"
                    analysis += "  - K值下穿D值，显示市场可能进入下降趋势

"

                # CCI信号
                cci_oversold_count = technical_signals['cci_oversold']
                cci_overbought_count = technical_signals['cci_overbought']
                if cci_oversold_count > 0 or cci_overbought_count > 0:
                    cci_percent = (cci_oversold_count + cci_overbought_count) / total_signals * 100
                    analysis += f"- **CCI信号**: {cci_oversold_count + cci_overbought_count}个 ({cci_percent:.1f}%)
"
                    if cci_oversold_count > 0:
                        analysis += "  - CCI从-100以下回升，显示市场可能触底反弹
"
                    if cci_overbought_count > 0:
                        analysis += "  - CCI从+100以上回落，显示市场可能面临回调压力

"

                # ADX信号
                adx_count = technical_signals['adx_trend']
                if adx_count > 0:
                    adx_percent = adx_count / total_signals * 100
                    analysis += f"- **ADX信号**: {adx_count}个 ({adx_percent:.1f}%)
"
                    analysis += "  - ADX > 25，显示市场趋势可能增强

"

                # 技术分析总结
                analysis += "### 技术分析总结

"
                if buy_count > sell_count:
                    analysis += "从技术指标来看，买入信号数量多于卖出信号，显示市场可能处于上升趋势。"
                    analysis += "建议投资者关注技术指标给出的买入信号，适当增加仓位。"
                elif sell_count > buy_count:
                    analysis += "从技术指标来看，卖出信号数量多于买入信号，显示市场可能处于下降趋势。"
                    analysis += "建议投资者关注技术指标给出的卖出信号，适当减少仓位。"
                else:
                    analysis += "从技术指标来看，买入和卖出信号数量相当，显示市场可能处于震荡行情。"
                    analysis += "建议投资者保持观望，等待更明确的方向信号。"
            else:
                analysis += "从技术指标来看，当前市场缺乏明确的方向信号，建议投资者保持观望。"

            return analysis

        except Exception as e:
            self.logger.error(f"生成技术分析失败: {str(e)}")
            return "## 技术分析

生成分析时出错
"

    def generate_news_analysis(self, trading_signals, news_data):
        """
        生成新闻分析部分

        Args:
            trading_signals (dict): 交易信号数据
            news_data (list): 新闻数据列表

        Returns:
            str: 新闻分析文本
        """
        try:
            # 获取市场情绪和影响
            market_sentiment = trading_signals.get('market_sentiment', '未知')
            market_impact = trading_signals.get('market_impact', '未知')

            # 获取基金信号
            funds_signals = trading_signals.get('funds_signals', [])

            # 如果没有数据，返回空文本
            if not news_data:
                return "## 新闻分析

暂无数据
"

            # 构建新闻分析
            analysis = "## 新闻分析

"

            # 市场情绪分析
            analysis += f"### 市场情绪分析

"
            analysis += f"当前市场整体情绪为**{market_sentiment}**，市场新闻影响级别为**{market_impact}**。

"

            # 积极新闻分析
            positive_news = [news for news in news_data if self.get_news_sentiment(news) == '积极']
            if positive_news:
                analysis += "#### 积极新闻

"
                analysis += "近期市场的主要积极新闻包括：

"

                # 只显示前3条积极新闻
                for i, news in enumerate(positive_news[:3], 1):
                    title = news.get('title', '无标题')
                    source = news.get('source', '未知来源')
                    analysis += f"{i}. **{title}** ({source})
"

                if len(positive_news) > 3:
                    analysis += f"...以及其他{len(positive_news)-3}条积极新闻
"

                analysis += "
这些积极新闻对市场情绪产生了积极影响，有利于基金投资。

"

            # 消极新闻分析
            negative_news = [news for news in news_data if self.get_news_sentiment(news) == '消极']
            if negative_news:
                analysis += "#### 消极新闻

"
                analysis += "近期市场的主要消极新闻包括：

"

                # 只显示前3条消极新闻
                for i, news in enumerate(negative_news[:3], 1):
                    title = news.get('title', '无标题')
                    source = news.get('source', '未知来源')
                    analysis += f"{i}. **{title}** ({source})
"

                if len(negative_news) > 3:
                    analysis += f"...以及其他{len(negative_news)-3}条消极新闻
"

                analysis += "
这些消极新闻对市场情绪产生了消极影响，对基金投资形成压力。

"

            # 中性新闻分析
            neutral_news = [news for news in news_data if self.get_news_sentiment(news) == '中性']
            if neutral_news:
                analysis += "#### 中性新闻

"
                analysis += "近期市场的主要中性新闻包括：

"

                # 只显示前3条中性新闻
                for i, news in enumerate(neutral_news[:3], 1):
                    title = news.get('title', '无标题')
                    source = news.get('source', '未知来源')
                    analysis += f"{i}. **{title}** ({source})
"

                if len(neutral_news) > 3:
                    analysis += f"...以及其他{len(neutral_news)-3}条中性新闻
"

                analysis += "
这些中性新闻对市场情绪影响有限。

"

            # 新闻影响总结
            analysis += "### 新闻影响总结

"
            if market_sentiment == '积极':
                analysis += "从新闻分析来看，市场整体情绪积极，利好基金投资。"
                analysis += "建议投资者可以适当增加基金仓位，重点关注受益于积极新闻的基金产品。"
            elif market_sentiment == '消极':
                analysis += "从新闻分析来看，市场整体情绪消极，利空基金投资。"
                analysis += "建议投资者可以适当减少基金仓位，规避受到消极新闻影响的基金产品。"
            else:
                analysis += "从新闻分析来看，市场情绪中性，无明显利好或利空。"
                analysis += "建议投资者保持观望，等待更明确的信号。"

            return analysis

        except Exception as e:
            self.logger.error(f"生成新闻分析失败: {str(e)}")
            return "## 新闻分析

生成分析时出错
"

    def get_news_sentiment(self, news):
        """
        获取新闻情感

        Args:
            news (dict): 新闻数据

        Returns:
            str: 情感标签
        """
        try:
            # 简单的情感判断（实际应用中可以使用更复杂的算法）
            title = news.get('title', '')
            content = news.get('content', '')
            text = f"{title} {content}"

            # 积极关键词
            positive_keywords = ['利好', '上涨', '增长', '提升', '积极', '乐观', '看好', '强劲', '繁荣', '创新', '改革', '支持', '推动', '发展', '突破']

            # 消极关键词
            negative_keywords = ['利空', '下跌', '下降', '减少', '消极', '悲观', '看空', '疲软', '衰退', '风险', '担忧', '压力', '制约', '挑战', '困难']

            positive_count = sum(1 for keyword in positive_keywords if keyword in text)
            negative_count = sum(1 for keyword in negative_keywords if keyword in text)

            if positive_count > negative_count:
                return '积极'
            elif negative_count > positive_count:
                return '消极'
            else:
                return '中性'

        except Exception as e:
            self.logger.error(f"获取新闻情感失败: {str(e)}")
            return '中性'

    def generate_investment_recommendations(self, trading_signals):
        """
        生成投资建议部分

        Args:
            trading_signals (dict): 交易信号数据

        Returns:
            str: 投资建议文本
        """
        try:
            # 获取基金信号
            funds_signals = trading_signals.get('funds_signals', [])

            # 如果没有数据，返回空文本
            if not funds_signals:
                return "## 投资建议

暂无数据
"

            # 按信号类型分组
            buy_signals = [f for f in funds_signals if f.get('signal') == '买入']
            sell_signals = [f for f in funds_signals if f.get('signal') == '卖出']
            hold_signals = [f for f in funds_signals if f.get('signal') == '观望']

            # 构建投资建议
            recommendations = "## 投资建议

"

            # 总体建议
            recommendations += "### 总体建议

"
            if len(buy_signals) > len(sell_signals):
                recommendations += "从整体来看，买入信号数量多于卖出信号，显示市场可能处于上升趋势。"
                recommendations += "建议投资者可以适当增加基金仓位，重点关注买入信号较强的基金产品。"
            elif len(sell_signals) > len(buy_signals):
                recommendations += "从整体来看，卖出信号数量多于买入信号，显示市场可能处于下降趋势。"
                recommendations += "建议投资者可以适当减少基金仓位，规避卖出信号较强的基金产品。"
            else:
                recommendations += "从整体来看，买入和卖出信号数量相当，显示市场可能处于震荡行情。"
                recommendations += "建议投资者保持观望，等待更明确的方向信号。"

            recommendations += "
"

            # 具体建议
            recommendations += "### 具体建议

"

            # 买入建议
            if buy_signals:
                recommendations += "#### 建议买入基金

"
                recommendations += "以下基金给出买入信号，建议投资者重点关注：

"

                # 按评分排序
                sorted_buy_signals = sorted(buy_signals, key=lambda x: x.get('total_score', 0), reverse=True)

                for i, fund_signal in enumerate(sorted_buy_signals[:5], 1):  # 只显示前5只
                    fund_code = fund_signal.get('fund_code', '未知')
                    fund_name = fund_signal.get('fund_name', '未知')
                    strength = fund_signal.get('signal_strength', '弱')
                    total_score = fund_signal.get('total_score', 0)

                    recommendations += f"{i}. **{fund_code} - {fund_name}**
"
                    recommendations += f"   - 信号强度: {strength}
"
                    recommendations += f"   - 综合评分: {total_score:.2f}
"

                    # 添加买入理由
                    signal_details = fund_signal.get('signal_details', {})
                    technical_factors = signal_details.get('technical_factors', [])
                    news_factors = signal_details.get('news_factors', [])

                    if technical_factors:
                        recommendations += "   - 技术面理由: "
                        for factor in technical_factors[:2]:  # 只显示前2个理由
                            recommendations += f"{factor}；"
                        recommendations = recommendations.rstrip("；") + "
"

                    if news_factors:
                        recommendations += "   - 消息面理由: "
                        for factor in news_factors[:1]:  # 只显示前1个理由
                            recommendations += f"{factor}；"
                        recommendations = recommendations.rstrip("；") + "
"

                    recommendations += "
"

                if len(buy_signals) > 5:
                    recommendations += f"...以及其他{len(buy_signals)-5}只基金

"

            # 卖出建议
            if sell_signals:
                recommendations += "#### 建议卖出基金

"
                recommendations += "以下基金给出卖出信号，建议投资者谨慎对待：

"

                # 按评分排序
                sorted_sell_signals = sorted(sell_signals, key=lambda x: abs(x.get('total_score', 0)), reverse=True)

                for i, fund_signal in enumerate(sorted_sell_signals[:5], 1):  # 只显示前5只
                    fund_code = fund_signal.get('fund_code', '未知')
                    fund_name = fund_signal.get('fund_name', '未知')
                    strength = fund_signal.get('signal_strength', '弱')
                    total_score = fund_signal.get('total_score', 0)

                    recommendations += f"{i}. **{fund_code} - {fund_name}**
"
                    recommendations += f"   - 信号强度: {strength}
"
                    recommendations += f"   - 综合评分: {total_score:.2f}
"

                    # 添加卖出理由
                    signal_details = fund_signal.get('signal_details', {})
                    technical_factors = signal_details.get('technical_factors', [])
                    news_factors = signal_details.get('news_factors', [])

                    if technical_factors:
                        recommendations += "   - 技术面理由: "
                        for factor in technical_factors[:2]:  # 只显示前2个理由
                            recommendations += f"{factor}；"
                        recommendations = recommendations.rstrip("；") + "
"

                    if news_factors:
                        recommendations += "   - 消息面理由: "
                        for factor in news_factors[:1]:  # 只显示前1个理由
                            recommendations += f"{factor}；"
                        recommendations = recommendations.rstrip("；") + "
"

                    recommendations += "
"

                if len(sell_signals) > 5:
                    recommendations += f"...以及其他{len(sell_signals)-5}只基金

"

            # 观望建议
            if hold_signals:
                recommendations += "#### 建议观望基金

"
                recommendations += "以下基金给出观望信号，建议投资者保持关注：

"

                # 按评分排序
                sorted_hold_signals = sorted(hold_signals, key=lambda x: abs(x.get('total_score', 0)), reverse=True)

                for i, fund_signal in enumerate(sorted_hold_signals[:5], 1):  # 只显示前5只
                    fund_code = fund_signal.get('fund_code', '未知')
                    fund_name = fund_signal.get('fund_name', '未知')
                    strength = fund_signal.get('signal_strength', '弱')
                    total_score = fund_signal.get('total_score', 0)

                    recommendations += f"{i}. **{fund_code} - {fund_name}**
"
                    recommendations += f"   - 信号强度: {strength}
"
                    recommendations += f"   - 综合评分: {total_score:.2f}
"
                    recommendations += "
"

                if len(hold_signals) > 5:
                    recommendations += f"...以及其他{len(hold_signals)-5}只基金

"

            # 风险提示
            recommendations += "### 风险提示

"
            recommendations += "- 以上分析仅供参考，不构成投资建议
"
            recommendations += "- 基金投资有风险，需谨慎决策
"
            recommendations += "- 建议结合自身风险承受能力进行投资
"
            recommendations += "- 定期关注市场变化，及时调整投资策略
"
            recommendations += "- 过往业绩不代表未来表现
"

            return recommendations

        except Exception as e:
            self.logger.error(f"生成投资建议失败: {str(e)}")
            return "## 投资建议

生成建议时出错
"

    def generate_article(self, trading_signals, news_data, output_file):
        """
        生成完整文章

        Args:
            trading_signals (dict): 交易信号数据
            news_data (list): 新闻数据列表
            output_file (str): 输出文件路径
        """
        try:
            # 生成文章各部分
            market_overview = self.generate_market_overview(trading_signals, news_data)
            technical_analysis = self.generate_technical_analysis(trading_signals)
            news_analysis = self.generate_news_analysis(trading_signals, news_data)
            investment_recommendations = self.generate_investment_recommendations(trading_signals)

            # 合并文章
            article = market_overview + "
" + technical_analysis + "
" + news_analysis + "
" + investment_recommendations

            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

            # 保存文章
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(article)

            self.logger.info(f"文章已生成并保存到: {output_file}")

        except Exception as e:
            self.logger.error(f"生成文章失败: {str(e)}")


def main():
    """主函数"""
    # 创建文章生成器实例
    generator = ArticleGenerator()

    # 示例数据
    trading_signals = {
        'generation_time': '2023-06-01 12:00:00',
        'market_sentiment': '积极',
        'market_impact': '中',
        'funds_signals': [
            {
                'fund_code': '110022',
                'fund_name': '易方达蓝筹精选',
                'technical_score': 0.65,
                'news_score': 0.45,
                'total_score': 0.58,
                'signal': '买入',
                'signal_strength': '中',
                'signal_details': {
                    'technical_factors': [
                        '5日均线上穿20日均线',
                        'MACD金叉形成',
                        'RSI指标从超卖区回升'
                    ],
                    'news_factors': [
                        '市场整体情绪积极，利好基金投资',
                        '基金公司业绩表现良好'
                    ]
                }
            },
            {
                'fund_code': '000217',
                'fund_name': '国泰估值优势',
                'technical_score': -0.35,
                'news_score': -0.20,
                'total_score': -0.30,
                'signal': '卖出',
                'signal_strength': '中',
                'signal_details': {
                    'technical_factors': [
                        '5日均线下穿20日均线',
                        'MACD死叉形成',
                        'RSI指标进入超买区'
                    ],
                    'news_factors': [
                        '市场整体情绪消极，利空基金投资'
                    ]
                }
            },
            {
                'fund_code': '000345',
                'fund_name': '长城行业',
                'technical_score': 0.10,
                'news_score': 0.05,
                'total_score': 0.08,
                'signal': '观望',
                'signal_strength': '弱',
                'signal_details': {
                    'technical_factors': [
                        '均线系统纠缠，方向不明'
                    ],
                    'news_factors': [
                        '市场情绪中性，无明显利好或利空'
                    ]
                }
            }
        ]
    }

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

    # 生成文章
    generator.generate_article(trading_signals, news_data, 'analysis_report.md')


if __name__ == '__main__':
    main()
