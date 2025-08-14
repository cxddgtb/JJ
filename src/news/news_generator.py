"""新闻生成器 - 生成基金相关新闻和市场资讯"""

import random
from datetime import datetime, timedelta
from typing import List, Dict
import jieba
from ..utils.logger import log_info, log_warning, log_error, log_debug

class NewsGenerator:
    """新闻生成器 - 生成真实的基金市场新闻"""

    def __init__(self):
        # 新闻模板库
        self.news_templates = {
            'market_trend': [
                '{date}，{market_name}表现{trend_word}，{fund_type}基金{performance}。市场分析师认为，{reason}，预计{prediction}。',
                '今日{market_name}{trend_desc}，{fund_type}类基金{return_desc}。专家表示，{analysis}，投资者应{advice}。',
                '{date}收盘，{market_name}{trend_result}，{fund_type}基金整体{performance_result}。{expert_view}，{future_outlook}。'
            ],
            'fund_performance': [
                '{fund_company}旗下{fund_name}近期表现{performance}，{period}收益率达到{return_rate}。基金经理{manager}表示，{strategy}。',
                '{fund_name}({fund_code})今日{performance_desc}，净值{nav_change}。该基金{fund_feature}，{manager_comment}。',
                '明星基金{fund_name}继续{trend_word}，{analysis_period}{return_desc}。投资者关注{focus_point}，{market_outlook}。'
            ],
            'industry_news': [
                '{industry}板块今日{trend_desc}，相关{fund_type}基金{performance}。分析认为，{reason}，{outlook}。',
                '受{news_factor}影响，{industry}行业{impact_desc}，{fund_type}基金{result}。专家建议{advice}。',
                '{industry}主题投资升温，多只相关基金{performance}。{analysis}，{investment_suggestion}。'
            ],
            'policy_impact': [
                '央行{policy_action}，{fund_type}基金{impact_result}。市场人士分析，{policy_analysis}，{market_response}。',
                '监管层{regulation_action}，基金行业{industry_impact}。{fund_type}基金{performance_impact}，{expert_opinion}。',
                '{policy_news}发布，{affected_sector}{sector_impact}。相关基金{fund_impact}，{investment_advice}。'
            ]
        }

        # 词汇库
        self.vocabulary = {
            'market_names': ['A股市场', '沪深两市', '创业板', '科创板', '主板市场'],
            'trend_words': ['强势', '疲软', '震荡', '上涨', '下跌', '回调', '反弹'],
            'trend_desc': ['走强', '走弱', '震荡整理', '小幅上涨', '微幅下跌', '冲高回落'],
            'performance_words': ['表现亮眼', '涨幅居前', '表现平稳', '小幅回调', '大幅上涨'],
            'fund_types': ['股票型', '混合型', '债券型', '指数型', 'QDII', 'ETF'],
            'industries': ['科技', '医药', '消费', '金融', '地产', '能源', '制造业', '新能源'],
            'fund_companies': ['易方达', '华夏', '南方', '嘉实', '广发', '汇添富', '富国', '招商', '工银瑞信', '建信'],
            'analysis_terms': ['技术面', '基本面', '资金面', '政策面', '情绪面'],
            'time_periods': ['近一周', '近一月', '近三月', '今年以来', '近半年'],
            'experts': ['市场分析师', '基金经理', '投资专家', '研究员', '资深投资顾问'],
            'policy_actions': ['降准', '降息', '加息', '定向降准', '逆回购', '公开市场操作'],
            'news_factors': ['业绩预告', '政策利好', '行业整合', '技术突破', '国际形势变化']
        }

        # 预设基金信息
        self.fund_info = {
            '000001': {'name': '华夏成长混合', 'company': '华夏基金', 'manager': '张明'},
            '110022': {'name': '易方达消费行业', 'company': '易方达基金', 'manager': '李强'},
            '163402': {'name': '兴全趋势投资', 'company': '兴全基金', 'manager': '王磊'},
            '519674': {'name': '银河创新成长', 'company': '银河基金', 'manager': '刘洋'},
            '000248': {'name': '汇添富消费行业', 'company': '汇添富基金', 'manager': '陈静'}
        }

    def generate_market_news(self, count: int = 10) -> List[Dict]:
        """生成市场新闻"""
        news_list = []

        for i in range(count):
            news_type = random.choice(['market_trend', 'fund_performance', 'industry_news', 'policy_impact'])
            news_item = self._generate_news_by_type(news_type, i)
            news_list.append(news_item)

        log_info(f"生成了 {len(news_list)} 条市场新闻")
        return news_list

    def _generate_news_by_type(self, news_type: str, index: int) -> Dict:
        """根据类型生成新闻"""
        template = random.choice(self.news_templates[news_type])

        # 生成发布时间
        publish_time = datetime.now() - timedelta(hours=random.randint(1, 48))

        if news_type == 'market_trend':
            return self._generate_market_trend_news(template, publish_time, index)
        elif news_type == 'fund_performance':
            return self._generate_fund_performance_news(template, publish_time, index)
        elif news_type == 'industry_news':
            return self._generate_industry_news(template, publish_time, index)
        else:  # policy_impact
            return self._generate_policy_news(template, publish_time, index)

    def _generate_market_trend_news(self, template: str, publish_time: datetime, index: int) -> Dict:
        """生成市场趋势新闻"""
        market_name = random.choice(self.vocabulary['market_names'])
        trend_word = random.choice(self.vocabulary['trend_words'])
        fund_type = random.choice(self.vocabulary['fund_types'])
        performance = random.choice(self.vocabulary['performance_words'])

        # 构造新闻内容
        content = template.format(
            date=publish_time.strftime('%Y年%m月%d日'),
            market_name=market_name,
            trend_word=trend_word,
            fund_type=fund_type,
            performance=performance,
            trend_desc=random.choice(self.vocabulary['trend_desc']),
            return_desc=f"平均收益率{random.uniform(-2, 3):.2f}%",
            reason=f"受{random.choice(self.vocabulary['news_factors'])}影响",
            prediction=f"未来{random.choice(['一周', '两周', '一个月'])}市场将{random.choice(['继续震荡', '逐步企稳', '保持活跃'])}",
            analysis=f"从{random.choice(self.vocabulary['analysis_terms'])}来看，当前市场{random.choice(['趋势向好', '存在分歧', '需要观察'])}",
            advice=f"{random.choice(['谨慎操作', '理性投资', '关注风险', '把握机会'])}",
            trend_result=f"{random.choice(['收涨', '收跌', '收平'])}{random.uniform(0.1, 2.5):.2f}%",
            performance_result=f"{random.choice(['上涨', '下跌'])}{random.uniform(0.5, 3.0):.2f}%",
            expert_view=f"{random.choice(self.vocabulary['experts'])}认为，当前{random.choice(['估值合理', '存在机会', '需要谨慎'])}",
            future_outlook=f"预计{random.choice(['短期内震荡为主', '中期趋势向好', '需关注政策变化'])}"
        )

        title = f"{market_name}{trend_word}，{fund_type}基金{performance}"

        return {
            'id': f'news_{index+1}',
            'title': title,
            'content': content,
            'publish_time': publish_time.isoformat(),
            'source': random.choice(['财经网', '基金报', '证券时报', '投资快报', '市场观察']),
            'category': '市场动态',
            'sentiment': self._determine_sentiment(content),
            'keywords': self._extract_keywords(content),
            'read_count': random.randint(1000, 50000),
            'comment_count': random.randint(10, 500)
        }

    def _generate_fund_performance_news(self, template: str, publish_time: datetime, index: int) -> Dict:
        """生成基金业绩新闻"""
        fund_code = random.choice(list(self.fund_info.keys()))
        fund_data = self.fund_info[fund_code]

        content = template.format(
            fund_company=fund_data['company'],
            fund_name=fund_data['name'],
            fund_code=fund_code,
            manager=fund_data['manager'],
            performance=random.choice(['优异', '亮眼', '稳健', '波动']),
            period=random.choice(self.vocabulary['time_periods']),
            return_rate=f"{random.uniform(-5, 15):.2f}%",
            performance_desc=random.choice(['净值上涨', '净值下跌', '净值波动']),
            nav_change=f"{random.choice(['上涨', '下跌'])}{random.uniform(0.1, 3.0):.2f}%",
            fund_feature=f"该基金{random.choice(['重仓科技股', '专注消费板块', '坚持价值投资', '注重风控'])}",
            manager_comment=f"基金经理表示将{random.choice(['继续坚持投资策略', '适度调整仓位', '密切关注市场变化'])}",
            trend_word=random.choice(['强势表现', '稳健增长', '震荡上行']),
            analysis_period=random.choice(self.vocabulary['time_periods']),
            return_desc=f"收益率{random.uniform(-3, 8):.2f}%",
            focus_point=random.choice(['后市走向', '投资机会', '风险控制']),
            market_outlook=f"预计{random.choice(['维持乐观', '保持谨慎', '继续关注'])}",
            strategy=f"将{random.choice(['保持现有配置', '适度增加仓位', '优化持仓结构'])}"
        )

        title = f"{fund_data['name']}表现{random.choice(['亮眼', '优异', '稳健'])}，{random.choice(self.vocabulary['time_periods'])}收益率达{random.uniform(2, 10):.1f}%"

        return {
            'id': f'news_{index+1}',
            'title': title,
            'content': content,
            'publish_time': publish_time.isoformat(),
            'source': random.choice(['基金报', '投资者报', '理财周报', '基金观察']),
            'category': '基金业绩',
            'related_funds': [fund_code],
            'sentiment': self._determine_sentiment(content),
            'keywords': self._extract_keywords(content),
            'read_count': random.randint(2000, 80000),
            'comment_count': random.randint(20, 800)
        }

    def _generate_industry_news(self, template: str, publish_time: datetime, index: int) -> Dict:
        """生成行业新闻"""
        industry = random.choice(self.vocabulary['industries'])
        fund_type = random.choice(self.vocabulary['fund_types'])

        content = template.format(
            industry=industry,
            fund_type=fund_type,
            trend_desc=random.choice(self.vocabulary['trend_desc']),
            performance=random.choice(self.vocabulary['performance_words']),
            news_factor=random.choice(self.vocabulary['news_factors']),
            impact_desc=f"{random.choice(['迎来利好', '面临挑战', '出现分化'])}",
            reason=f"{industry}行业{random.choice(['基本面改善', '政策支持加强', '技术突破明显'])}",
            outlook=f"预计{random.choice(['短期内', '中期内', '长期内'])}该板块将{random.choice(['继续受益', '保持活跃', '震荡上行'])}",
            result=f"{random.choice(['收益明显', '表现分化', '整体上涨'])}",
            advice=f"投资者{random.choice(['可适当关注', '需谨慎操作', '可逢低布局'])}",
            analysis=f"分析师认为{industry}板块{random.choice(['估值合理', '成长性突出', '具备投资价值'])}",
            investment_suggestion=f"建议{random.choice(['长期持有', '分批布局', '关注龙头'])}"
        )

        title = f"{industry}板块{random.choice(self.vocabulary['trend_desc'])}，相关基金{random.choice(['受益明显', '表现活跃', '涨幅居前'])}"

        return {
            'id': f'news_{index+1}',
            'title': title,
            'content': content,
            'publish_time': publish_time.isoformat(),
            'source': random.choice(['行业观察', '板块分析', '投资前线', '市场脉搏']),
            'category': '行业动态',
            'industry': industry,
            'sentiment': self._determine_sentiment(content),
            'keywords': self._extract_keywords(content),
            'read_count': random.randint(1500, 60000),
            'comment_count': random.randint(15, 600)
        }

    def _generate_policy_news(self, template: str, publish_time: datetime, index: int) -> Dict:
        """生成政策新闻"""
        policy_action = random.choice(self.vocabulary['policy_actions'])
        fund_type = random.choice(self.vocabulary['fund_types'])

        content = template.format(
            policy_action=policy_action,
            fund_type=fund_type,
            impact_result=f"{random.choice(['迎来利好', '受到冲击', '影响有限'])}",
            policy_analysis=f"此次{policy_action}主要{random.choice(['释放流动性', '调节市场预期', '支持实体经济'])}",
            market_response=f"市场{random.choice(['反应积极', '表现平稳', '出现分化'])}",
            regulation_action=f"发布{random.choice(['新规', '指导意见', '管理办法'])}",
            industry_impact=f"{random.choice(['影响深远', '变化显著', '稳中有变'])}",
            performance_impact=f"{random.choice(['表现亮眼', '波动加大', '走势分化'])}",
            expert_opinion=f"专家表示这将{random.choice(['促进行业发展', '规范市场秩序', '提升投资效率'])}",
            policy_news=f"{random.choice(['重要政策', '新规定', '指导意见'])}",
            affected_sector=f"{random.choice(self.vocabulary['industries'])}等板块",
            sector_impact=f"{random.choice(['获得提振', '面临调整', '影响有限'])}",
            fund_impact=f"{random.choice(['普遍受益', '表现分化', '谨慎应对'])}",
            investment_advice=f"建议投资者{random.choice(['密切关注', '理性看待', '把握机会'])}"
        )

        title = f"央行{policy_action}，{fund_type}基金{random.choice(['迎来利好', '影响几何', '如何应对'])}"

        return {
            'id': f'news_{index+1}',
            'title': title,
            'content': content,
            'publish_time': publish_time.isoformat(),
            'source': random.choice(['政策解读', '央行观察', '监管动态', '政策前沿']),
            'category': '政策影响',
            'policy_type': policy_action,
            'sentiment': self._determine_sentiment(content),
            'keywords': self._extract_keywords(content),
            'read_count': random.randint(3000, 100000),
            'comment_count': random.randint(50, 1000)
        }

    def _determine_sentiment(self, content: str) -> str:
        """判断新闻情感倾向"""
        positive_words = ['上涨', '利好', '增长', '优异', '亮眼', '受益', '机会', '看好']
        negative_words = ['下跌', '利空', '下滑', '挑战', '风险', '担忧', '谨慎', '冲击']

        pos_count = sum(1 for word in positive_words if word in content)
        neg_count = sum(1 for word in negative_words if word in content)

        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        else:
            return 'neutral'

    def _extract_keywords(self, content: str) -> List[str]:
        """提取关键词"""
        # 使用jieba提取关键词
        keywords = jieba.analyse.extract_tags(content, topK=5)
        return keywords

    def generate_fund_specific_news(self, fund_code: str, fund_name: str) -> List[Dict]:
        """为特定基金生成相关新闻"""
        news_list = []

        # 生成3-5条相关新闻
        for i in range(random.randint(3, 5)):
            news_type = random.choice(['fund_performance', 'industry_news'])

            if news_type == 'fund_performance':
                # 临时添加基金信息
                if fund_code not in self.fund_info:
                    self.fund_info[fund_code] = {
                        'name': fund_name,
                        'company': f'{fund_name[:2]}基金',
                        'manager': random.choice(['张伟', '李明', '王强', '刘洋', '陈静'])
                    }

            news_item = self._generate_news_by_type(news_type, i)
            news_item['related_funds'] = [fund_code]
            news_list.append(news_item)

        return news_list

# 全局新闻生成器实例
news_generator = NewsGenerator()
