"""
情绪分析模块 - 市场情绪和新闻情感分析
"""
import pandas as pd
import numpy as np
import re
import jieba
import jieba.analyse
from collections import Counter
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
# 尝试导入wordcloud，如果失败则使用替代方案
try:
    from wordcloud import WordCloud
    HAS_WORDCLOUD = True
except ImportError:
    HAS_WORDCLOUD = False
    WordCloud = None
import matplotlib.pyplot as plt
from dataclasses import dataclass

from ..utils.logger import log_info, log_warning, log_error, log_debug

@dataclass
class SentimentScore:
    """情绪得分"""
    positive: float
    negative: float
    neutral: float
    compound: float
    confidence: float

class SentimentAnalyzer:
    """情绪分析器"""

    def __init__(self):
        # 加载情感词典
        self.positive_words = self._load_positive_words()
        self.negative_words = self._load_negative_words()
        self.degree_words = self._load_degree_words()
        self.negation_words = self._load_negation_words()

        # 基金相关关键词
        self.fund_keywords = [
            '基金', '净值', '收益', '回报', '投资', '理财', '配置', '持仓',
            '基金经理', '管理费', '申购', '赎回', '分红', '风险', '波动',
            '牛市', '熊市', '震荡', '上涨', '下跌', '涨幅', '跌幅'
        ]

        # 初始化jieba
        self._init_jieba()

    def _init_jieba(self):
        """初始化jieba分词"""
        # 添加基金相关词汇
        for word in self.fund_keywords:
            jieba.add_word(word)

        # 添加金融专业词汇
        finance_words = [
            '股票型基金', '债券型基金', '混合型基金', '指数基金', '货币基金',
            '私募基金', '公募基金', 'ETF', 'LOF', 'QDII',
            '基金定投', '基金转换', '基金分拆', '基金合并',
            '主动管理', '被动管理', '量化投资', '价值投资', '成长投资'
        ]

        for word in finance_words:
            jieba.add_word(word)

    def _load_positive_words(self) -> set:
        """加载积极词汇"""
        positive_words = {
            # 收益相关
            '上涨', '涨幅', '收益', '盈利', '获利', '赚钱', '回报', '增长', '增值',
            '正收益', '超额收益', '跑赢', '战胜', '优于', '超越', '领先',

            # 表现相关
            '优秀', '卓越', '出色', '亮眼', '强势', '稳健', '优异', '良好',
            '坚挺', '抗跌', '韧性', '稳定', '可靠', '值得信赖',

            # 趋势相关
            '看好', '看涨', '乐观', '积极', '正面', '利好', '向好', '回暖',
            '反弹', '回升', '复苏', '改善', '好转', '企稳',

            # 投资相关
            '买入', '增持', '配置', '推荐', '建议', '适合', '值得', '机会',
            '潜力', '前景', '预期', '看好', '布局'
        }
        return positive_words

    def _load_negative_words(self) -> set:
        """加载消极词汇"""
        negative_words = {
            # 亏损相关
            '下跌', '跌幅', '亏损', '损失', '缩水', '负收益', '跑输', '落后',
            'underperform', '表现不佳', '拖累', '重挫', '暴跌', '大跌',

            # 风险相关
            '风险', '危险', '警惕', '谨慎', '担忧', '忧虑', '不确定', '波动',
            '回撤', '最大回撤', '高风险', '不稳定', '脆弱',

            # 趋势相关
            '看空', '看跌', '悲观', '消极', '负面', '利空', '恶化', '下行',
            '衰退', '萎缩', '收缩', '疲软', '低迷', '困难',

            # 投资相关
            '卖出', '减持', '避免', '不建议', '不适合', '不值得', '谨慎',
            '观望', '等待', '暂停', '延迟'
        }
        return negative_words

    def _load_degree_words(self) -> Dict[str, float]:
        """加载程度词汇"""
        degree_words = {
            # 强程度
            '非常': 2.0, '极其': 2.0, '十分': 2.0, '相当': 1.8, '特别': 1.8,
            '格外': 1.8, '异常': 1.8, '极度': 2.0, '超级': 2.0, '巨大': 2.0,

            # 中程度
            '很': 1.5, '较': 1.3, '比较': 1.3, '还': 1.2, '更': 1.5,
            '挺': 1.3, '颇': 1.3, '相对': 1.2, '略': 0.8, '稍': 0.8,

            # 轻程度
            '有点': 0.8, '一点': 0.8, '一些': 0.8, '稍微': 0.8, '略微': 0.8,
            '微': 0.6, '轻微': 0.6, '小幅': 0.8, '温和': 0.8
        }
        return degree_words

    def _load_negation_words(self) -> set:
        """加载否定词汇"""
        negation_words = {
            '不', '没', '无', '非', '未', '否', '别', '莫', '勿', '毋',
            '不是', '不会', '不能', '不要', '不用', '没有', '没什么',
            '并非', '绝非', '决不', '从不', '永不', '从未'
        }
        return negation_words

    def analyze_news_sentiment(self, news_list: List[Dict]) -> Dict:
        """分析新闻情绪"""
        if not news_list:
            return {'overall_sentiment': 0, 'sentiment_distribution': {}, 'news_count': 0}

        sentiments = []
        detailed_analysis = []

        for news in news_list:
            title = news.get('title', '')
            content = news.get('content', '')
            text = f"{title} {content}"

            # 分析单条新闻情绪
            sentiment = self._analyze_text_sentiment(text)
            sentiments.append(sentiment.compound)

            detailed_analysis.append({
                'title': title,
                'url': news.get('url', ''),
                'publish_time': news.get('publish_time', ''),
                'sentiment_score': sentiment.compound,
                'positive': sentiment.positive,
                'negative': sentiment.negative,
                'neutral': sentiment.neutral,
                'confidence': sentiment.confidence
            })

        # 计算整体情绪
        overall_sentiment = np.mean(sentiments) if sentiments else 0

        # 情绪分布统计
        sentiment_distribution = self._calculate_sentiment_distribution(sentiments)

        # 时间序列情绪
        time_series = self._calculate_sentiment_time_series(detailed_analysis)

        # 关键词分析
        keywords = self._extract_sentiment_keywords(news_list)

        return {
            'overall_sentiment': round(overall_sentiment, 3),
            'sentiment_distribution': sentiment_distribution,
            'news_count': len(news_list),
            'time_series': time_series,
            'keywords': keywords,
            'detailed_analysis': detailed_analysis[:10],  # 只保留前10条详细分析
            'sentiment_trend': self._analyze_sentiment_trend(time_series),
            'market_mood': self._interpret_market_mood(overall_sentiment)
        }

    def _analyze_text_sentiment(self, text: str) -> SentimentScore:
        """分析文本情绪"""
        if not text.strip():
            return SentimentScore(0, 0, 1, 0, 0)

        # 分词
        words = jieba.lcut(text)

        # 情绪计算
        positive_score = 0
        negative_score = 0
        total_score = 0

        for i, word in enumerate(words):
            # 检查是否为情感词
            base_score = 0
            if word in self.positive_words:
                base_score = 1
            elif word in self.negative_words:
                base_score = -1

            if base_score != 0:
                # 应用程度词修饰
                degree = 1.0
                if i > 0 and words[i-1] in self.degree_words:
                    degree = self.degree_words[words[i-1]]

                # 应用否定词
                negation = False
                for j in range(max(0, i-3), i):
                    if words[j] in self.negation_words:
                        negation = True
                        break

                # 计算最终得分
                final_score = base_score * degree
                if negation:
                    final_score = -final_score

                total_score += final_score

                if final_score > 0:
                    positive_score += final_score
                else:
                    negative_score += abs(final_score)

        # 归一化处理
        total_words = len([w for w in words if w.strip() and len(w) > 1])
        if total_words > 0:
            compound = total_score / total_words
            positive = positive_score / total_words
            negative = negative_score / total_words
            neutral = max(0, 1 - positive - negative)
        else:
            compound = positive = negative = 0
            neutral = 1

        # 置信度计算
        sentiment_words = positive_score + negative_score
        confidence = min(1.0, sentiment_words / max(1, total_words * 0.1))

        return SentimentScore(
            positive=round(positive, 3),
            negative=round(negative, 3),
            neutral=round(neutral, 3),
            compound=round(compound, 3),
            confidence=round(confidence, 3)
        )

    def _calculate_sentiment_distribution(self, sentiments: List[float]) -> Dict:
        """计算情绪分布"""
        if not sentiments:
            return {'positive': 0, 'negative': 0, 'neutral': 0}

        positive_count = sum(1 for s in sentiments if s > 0.1)
        negative_count = sum(1 for s in sentiments if s < -0.1)
        neutral_count = len(sentiments) - positive_count - negative_count

        total = len(sentiments)

        return {
            'positive': round(positive_count / total * 100, 1),
            'negative': round(negative_count / total * 100, 1),
            'neutral': round(neutral_count / total * 100, 1)
        }

    def _calculate_sentiment_time_series(self, detailed_analysis: List[Dict]) -> List[Dict]:
        """计算情绪时间序列"""
        time_series = []

        # 按时间分组
        time_groups = {}
        for item in detailed_analysis:
            publish_time = item.get('publish_time', '')
            if publish_time:
                try:
                    date = pd.to_datetime(publish_time).date()
                    date_str = date.strftime('%Y-%m-%d')

                    if date_str not in time_groups:
                        time_groups[date_str] = []
                    time_groups[date_str].append(item['sentiment_score'])
                except:
                    continue

        # 计算每日平均情绪
        for date_str, scores in time_groups.items():
            avg_sentiment = np.mean(scores)
            time_series.append({
                'date': date_str,
                'sentiment': round(avg_sentiment, 3),
                'news_count': len(scores)
            })

        # 按日期排序
        time_series.sort(key=lambda x: x['date'])

        return time_series

    def _extract_sentiment_keywords(self, news_list: List[Dict]) -> Dict:
        """提取情绪关键词"""
        all_text = ""
        for news in news_list:
            title = news.get('title', '')
            content = news.get('content', '')
            all_text += f"{title} {content} "

        if not all_text.strip():
            return {'positive': [], 'negative': [], 'neutral': []}

        # 提取关键词
        keywords = jieba.analyse.extract_tags(all_text, topK=50, withWeight=True)

        # 分类关键词
        positive_keywords = []
        negative_keywords = []
        neutral_keywords = []

        for word, weight in keywords:
            if word in self.positive_words:
                positive_keywords.append({'word': word, 'weight': round(weight, 3)})
            elif word in self.negative_words:
                negative_keywords.append({'word': word, 'weight': round(weight, 3)})
            else:
                neutral_keywords.append({'word': word, 'weight': round(weight, 3)})

        return {
            'positive': positive_keywords[:10],
            'negative': negative_keywords[:10],
            'neutral': neutral_keywords[:10]
        }

    def _analyze_sentiment_trend(self, time_series: List[Dict]) -> str:
        """分析情绪趋势"""
        if len(time_series) < 2:
            return "数据不足"

        # 计算趋势
        sentiments = [item['sentiment'] for item in time_series]

        # 简单趋势分析
        recent_avg = np.mean(sentiments[-3:]) if len(sentiments) >= 3 else sentiments[-1]
        early_avg = np.mean(sentiments[:3]) if len(sentiments) >= 3 else sentiments[0]

        if recent_avg > early_avg + 0.1:
            return "情绪改善"
        elif recent_avg < early_avg - 0.1:
            return "情绪恶化"
        else:
            return "情绪稳定"

    def _interpret_market_mood(self, overall_sentiment: float) -> str:
        """解释市场情绪"""
        if overall_sentiment > 0.3:
            return "极度乐观"
        elif overall_sentiment > 0.1:
            return "乐观"
        elif overall_sentiment > -0.1:
            return "中性"
        elif overall_sentiment > -0.3:
            return "悲观"
        else:
            return "极度悲观"

    def analyze_social_sentiment(self, social_data: List[Dict]) -> Dict:
        """分析社交媒体情绪"""
        # 类似新闻情绪分析，但针对社交媒体特点调整
        return self.analyze_news_sentiment(social_data)

    def analyze_fund_specific_sentiment(self, fund_code: str, news_list: List[Dict]) -> Dict:
        """分析特定基金的情绪"""
        # 过滤与特定基金相关的新闻
        fund_related_news = []

        for news in news_list:
            title = news.get('title', '')
            content = news.get('content', '')
            text = f"{title} {content}".lower()

            # 检查是否包含基金代码或相关信息
            if (fund_code in text or 
                any(keyword in text for keyword in ['基金', '净值', '收益']) and
                any(keyword in text for keyword in [fund_code[:3], fund_code[3:]])):
                fund_related_news.append(news)

        if not fund_related_news:
            return {'message': '未找到相关新闻', 'related_news_count': 0}

        # 分析相关新闻情绪
        sentiment_result = self.analyze_news_sentiment(fund_related_news)
        sentiment_result['related_news_count'] = len(fund_related_news)
        sentiment_result['fund_code'] = fund_code

        return sentiment_result

    def create_sentiment_visualization(self, sentiment_data: Dict, save_path: str = None) -> str:
        """创建情绪可视化图表"""
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns

            plt.style.use('seaborn-v0_8')
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('基金市场情绪分析', fontsize=16, fontweight='bold')

            # 1. 情绪分布饼图
            ax1 = axes[0, 0]
            distribution = sentiment_data.get('sentiment_distribution', {})
            labels = ['积极', '消极', '中性']
            sizes = [distribution.get('positive', 0), 
                    distribution.get('negative', 0), 
                    distribution.get('neutral', 0)]
            colors = ['#2ecc71', '#e74c3c', '#95a5a6']

            ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax1.set_title('情绪分布')

            # 2. 时间序列情绪趋势
            ax2 = axes[0, 1]
            time_series = sentiment_data.get('time_series', [])
            if time_series:
                dates = [item['date'] for item in time_series]
                sentiments = [item['sentiment'] for item in time_series]

                ax2.plot(dates, sentiments, marker='o', linewidth=2, markersize=6)
                ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.7)
                ax2.set_title('情绪趋势')
                ax2.set_xlabel('日期')
                ax2.set_ylabel('情绪得分')
                ax2.tick_params(axis='x', rotation=45)

            # 3. 关键词词云
            ax3 = axes[1, 0]
            keywords = sentiment_data.get('keywords', {})
            positive_words = keywords.get('positive', [])
            negative_words = keywords.get('negative', [])

            if positive_words or negative_words:
                word_freq = {}
                for item in positive_words:
                    word_freq[item['word']] = item['weight']
                for item in negative_words:
                    word_freq[item['word']] = item['weight']

                if word_freq:
                    wordcloud = WordCloud(
                        font_path='simhei.ttf',  # 中文字体
                        width=400, height=300,
                        background_color='white',
                        max_words=50
                    ).generate_from_frequencies(word_freq)

                    ax3.imshow(wordcloud, interpolation='bilinear')
                    ax3.axis('off')
                    ax3.set_title('关键词')

            # 4. 情绪强度分布
            ax4 = axes[1, 1]
            overall_sentiment = sentiment_data.get('overall_sentiment', 0)
            sentiment_labels = ['极度悲观', '悲观', '中性', '乐观', '极度乐观']
            sentiment_ranges = [-1, -0.3, -0.1, 0.1, 0.3, 1]

            # 创建情绪强度条形图
            current_range = 2  # 默认中性
            for i, threshold in enumerate(sentiment_ranges[1:], 0):
                if overall_sentiment <= threshold:
                    current_range = i
                    break

            colors_bar = ['#d32f2f', '#f57c00', '#fbc02d', '#689f38', '#388e3c']
            bars = ax4.barh(sentiment_labels, [0.2, 0.2, 0.2, 0.2, 0.2], 
                           color=['lightgray'] * 5)
            bars[current_range].set_color(colors_bar[current_range])

            ax4.set_title(f'当前市场情绪: {sentiment_labels[current_range]}')
            ax4.set_xlabel('情绪强度')

            plt.tight_layout()

            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                log_info(f"情绪分析图表已保存: {save_path}")
                return save_path
            else:
                plt.show()
                return "图表已显示"

        except Exception as e:
            log_error(f"创建情绪可视化失败: {e}")
            return ""

    def generate_sentiment_report(self, sentiment_data: Dict) -> str:
        """生成情绪分析报告"""
        overall_sentiment = sentiment_data.get('overall_sentiment', 0)
        distribution = sentiment_data.get('sentiment_distribution', {})
        trend = sentiment_data.get('sentiment_trend', '未知')
        mood = sentiment_data.get('market_mood', '未知')
        news_count = sentiment_data.get('news_count', 0)

        report = f"""
# 基金市场情绪分析报告

## 整体情绪概况
- **整体情绪得分**: {overall_sentiment:.3f}
- **市场情绪**: {mood}
- **分析新闻数量**: {news_count}条
- **情绪趋势**: {trend}

## 情绪分布
- **积极情绪**: {distribution.get('positive', 0):.1f}%
- **消极情绪**: {distribution.get('negative', 0):.1f}%
- **中性情绪**: {distribution.get('neutral', 0):.1f}%

## 投资建议
"""

        if overall_sentiment > 0.2:
            report += "当前市场情绪较为乐观，投资者信心较强，但需注意风险控制，避免盲目跟风。"
        elif overall_sentiment > 0:
            report += "市场情绪偏向积极，适合谨慎乐观的投资策略，关注优质基金的配置机会。"
        elif overall_sentiment > -0.2:
            report += "市场情绪相对平稳，建议保持理性投资态度，重点关注基金基本面。"
        else:
            report += "市场情绪偏向悲观，建议谨慎投资，等待更好的入场时机，或考虑防御性配置。"

        return report

# 全局情绪分析器实例
sentiment_analyzer = SentimentAnalyzer()

def analyze_market_sentiment(news_list: List[Dict]) -> Dict:
    """分析市场情绪（便捷函数）"""
    return sentiment_analyzer.analyze_news_sentiment(news_list)

def analyze_fund_sentiment(fund_code: str, news_list: List[Dict]) -> Dict:
    """分析特定基金情绪（便捷函数）"""
    return sentiment_analyzer.analyze_fund_specific_sentiment(fund_code, news_list)

if __name__ == "__main__":
    # 测试情绪分析功能
    test_news = [
        {
            'title': '基金净值大幅上涨，投资者信心增强',
            'content': '今日多只基金净值出现显著上涨，市场表现良好...',
            'publish_time': '2024-01-15'
        },
        {
            'title': '市场波动加剧，基金投资需谨慎',
            'content': '受多重因素影响，基金市场出现较大波动...',
            'publish_time': '2024-01-16'
        }
    ]

    analyzer = SentimentAnalyzer()
    result = analyzer.analyze_news_sentiment(test_news)
    print(json.dumps(result, indent=2, ensure_ascii=False))
