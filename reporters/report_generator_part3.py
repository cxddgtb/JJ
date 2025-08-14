def _prepare_report_data(self, analysis_results, news_data, rank_data):
    """准备报告数据"""
    # 基金分类
    strong_buy_funds = []
    buy_funds = []
    cautious_funds = []
    not_recommend_funds = []

    # 对分析结果进行分类
    for result in analysis_results:
        recommendation = result.get('recommendation', '')

        fund_info = {
            'code': result.get('code', ''),
            'name': result.get('name', ''),
            'type': self._get_fund_type(result),
            'reason': result.get('recommendation_reason', ''),
            'expected_return': result.get('expected_return', ''),
            'risk_level': result.get('risk_level', ''),
            'buy_point': self._get_buy_point(result),
            'target_price': self._get_target_price(result),
            'stop_loss': self._get_stop_loss(result)
        }

        if recommendation == '强烈买入':
            strong_buy_funds.append(fund_info)
        elif recommendation == '买入':
            buy_funds.append(fund_info)
        elif recommendation == '谨慎持有':
            cautious_funds.append(fund_info)
        else:
            not_recommend_funds.append(fund_info)

    # 处理新闻数据
    hot_news = []
    for news in news_data[:10]:  # 只取前10条新闻
        hot_news.append({
            'title': news.get('title', ''),
            'source': news.get('source', ''),
            'summary': self._get_news_summary(news)
        })

    # 获取新闻来源
    news_sources = set()
    for news in news_data:
        news_sources.add(news.get('source', ''))
    news_sources = ', '.join(list(news_sources))

    # 获取排名来源
    rank_sources = ', '.join(list(rank_data.keys()))

    # 生成摘要
    summary = self._generate_summary(analysis_results)

    # 生成市场趋势描述
    market_trend = self._generate_market_trend(analysis_results)

    # 风险提示
    risk_warning = """投资有风险，入市需谨慎。本报告中的分析和建议仅供参考，不构成任何投资承诺。投资者应根据自身的风险承受能力和投资目标，独立做出投资决策。基金过往业绩不代表未来表现，基金净值存在波动风险。"""

    # 免责声明
    disclaimer = """本报告由基金分析系统自动生成，基于公开信息和数据分析，力求客观、公正，但不保证所有信息的准确性和完整性。报告中的任何观点、结论和建议仅供参考，不构成对任何人的投资建议。对于因使用或依赖本报告内容而导致的任何直接或间接损失，本系统不承担任何责任。投资者据此操作，风险自担。"""

    # 返回报告数据
    return {
        'report_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'fund_count': len(analysis_results),
        'news_sources': news_sources,
        'rank_sources': rank_sources,
        'summary': summary,
        'hot_news': hot_news,
        'market_trend': market_trend,
        'strong_buy_funds': strong_buy_funds,
        'buy_funds': buy_funds,
        'cautious_funds': cautious_funds,
        'not_recommend_funds': not_recommend_funds,
        'risk_warning': risk_warning,
        'disclaimer': disclaimer
    }

def _get_fund_type(self, fund_result):
    """获取基金类型"""
    # 尝试从基本信息中获取
    for source, data in fund_result.items():
        if isinstance(data, dict) and 'info' in data and 'type' in data['info']:
            return data['info']['type']

    # 尝试从基本面分析中获取
    if 'fundamental_analysis' in fund_result and 'type' in fund_result['fundamental_analysis']:
        return fund_result['fundamental_analysis']['type']

    return '未知'

def _get_buy_point(self, fund_result):
    """获取买入点"""
    buy_sell_points = fund_result.get('buy_sell_points', [])
    for point in buy_sell_points:
        if point.get('type') == 'buy':
            return point.get('price', '')
    return ''

def _get_target_price(self, fund_result):
    """获取目标价位"""
    buy_sell_points = fund_result.get('buy_sell_points', [])
    for point in buy_sell_points:
        if point.get('type') == 'target':
            return point.get('price', '')
    return ''

def _get_stop_loss(self, fund_result):
    """获取止损价位"""
    buy_sell_points = fund_result.get('buy_sell_points', [])
    for point in buy_sell_points:
        if point.get('type') == 'stop_loss':
            return point.get('price', '')
    return ''

def _get_news_summary(self, news):
    """获取新闻摘要"""
    detail = news.get('detail', '')
    if len(detail) > 100:
        return detail[:100] + '...'
    return detail

def _generate_summary(self, analysis_results):
    """生成报告摘要"""
    # 统计各类基金数量
    strong_buy_count = 0
    buy_count = 0
    cautious_count = 0
    not_recommend_count = 0

    for result in analysis_results:
        recommendation = result.get('recommendation', '')
        if recommendation == '强烈买入':
            strong_buy_count += 1
        elif recommendation == '买入':
            buy_count += 1
        elif recommendation == '谨慎持有':
            cautious_count += 1
        else:
            not_recommend_count += 1

    # 生成摘要
    summary = f"""本次分析了{len(analysis_results)}只基金，其中强烈推荐买入{strong_buy_count}只，推荐买入{buy_count}只，谨慎持有{cautious_count}只，不推荐{not_recommend_count}只。

从整体市场来看，当前市场处于{'上涨' if strong_buy_count + buy_count > cautious_count + not_recommend_count else '下跌'}趋势。
建议投资者重点关注强烈推荐买入的基金，同时注意控制风险，合理配置资产。"""

    return summary

def _generate_market_trend(self, analysis_results):
    """生成市场趋势描述"""
    # 统计各类基金的平均表现
    total_return = 0
    positive_count = 0
    negative_count = 0

    for result in analysis_results:
        expected_return = result.get('expected_return', '0%')
        try:
            # 去掉百分号并转换为浮点数
            return_value = float(expected_return.strip('%'))
            total_return += return_value

            if return_value > 0:
                positive_count += 1
            else:
                negative_count += 1
        except:
            pass

    # 计算平均收益率
    avg_return = total_return / len(analysis_results) if analysis_results else 0

    # 生成市场趋势描述
    if avg_return > 5:
        trend = "市场表现强劲，大部分基金呈现上涨趋势，投资者可适当增加权益类基金的配置比例。"
    elif avg_return > 0:
        trend = "市场表现平稳，部分基金表现良好，投资者可精选优质基金进行配置。"
    elif avg_return > -5:
        trend = "市场表现疲软，大部分基金呈现下跌趋势，投资者应保持谨慎，控制仓位。"
    else:
        trend = "市场表现弱势，大部分基金下跌明显，投资者应以防御为主，减少高风险基金的配置。"

    return trend

def _generate_markdown_report(self, report_data):
    """生成Markdown报告"""
    # 加载模板
    template = self.jinja_env.get_template('report.md.j2')

    # 渲染模板
    markdown_content = template.render(**report_data)

    # 保存Markdown报告
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    markdown_path = os.path.join(self.reports_dir, "markdown", f"fund_report_{timestamp}.md")

    with open(markdown_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    self.logger.info(f"Markdown报告已保存到 {markdown_path}")

    return markdown_content

def _generate_html_report(self, report_data):
    """生成HTML报告"""
    # 加载模板
    template = self.jinja_env.get_template('report.html.j2')

    # 渲染模板
    html_content = template.render(**report_data)

    # 保存HTML报告
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    html_path = os.path.join(self.reports_dir, "html", f"fund_report_{timestamp}.html")

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    self.logger.info(f"HTML报告已保存到 {html_path}")

    return html_content

def _generate_pdf_report(self, html_content):
    """生成PDF报告"""
    try:
        import weasyprint

        # 保存PDF报告
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_path = os.path.join(self.reports_dir, "pdf", f"fund_report_{timestamp}.pdf")

        # 生成PDF
        weasyprint.HTML(string=html_content).write_pdf(pdf_path)

        self.logger.info(f"PDF报告已保存到 {pdf_path}")

    except ImportError:
        self.logger.warning("未安装weasyprint，无法生成PDF报告")
    except Exception as e:
        self.logger.error(f"生成PDF报告出错: {str(e)}")
