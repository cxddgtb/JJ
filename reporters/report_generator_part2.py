def generate_report(self, analysis_results=None, news_data=None, rank_data=None):
    """生成报告"""
    self.logger.info("开始生成报告...")

    # 如果没有提供数据，则加载数据
    if analysis_results is None:
        analysis_results = self.load_analysis_results()

    if news_data is None:
        news_data = self.load_news_data()

    if rank_data is None:
        rank_data = self.load_rank_data()

    # 创建模板
    self._create_templates()

    # 准备报告数据
    report_data = self._prepare_report_data(analysis_results, news_data, rank_data)

    # 生成Markdown报告
    markdown_report = self._generate_markdown_report(report_data)

    # 生成HTML报告
    html_report = self._generate_html_report(report_data)

    # 生成PDF报告（可选）
    if REPORT_CONFIG["REPORT_FORMAT"] == "pdf":
        self._generate_pdf_report(html_report)

    self.logger.info("报告生成完成")
    return {
        'markdown': markdown_report,
        'html': html_report,
        'data': report_data
    }

def _create_templates(self):
    """创建模板文件"""
    # Markdown模板
    markdown_template = """# 基金买卖操作分析报告

**报告生成时间**: {{ report_time }}
**分析基金数量**: {{ fund_count }}
**新闻数据来源**: {{ news_sources }}
**排名数据来源**: {{ rank_sources }}

## 摘要

{{ summary }}

## 市场概况

### 市场热点新闻

{% for news in hot_news %}
- **{{ news.title }}** (来源: {{ news.source }})
  {{ news.summary }}
{% endfor %}

### 市场整体趋势

{{ market_trend }}

## 推荐基金

### 强烈推荐买入

{% for fund in strong_buy_funds %}
#### {{ fund.name }} ({{ fund.code }})

- **基金类型**: {{ fund.type }}
- **推荐理由**: {{ fund.reason }}
- **预期收益**: {{ fund.expected_return }}
- **风险等级**: {{ fund.risk_level }}
- **买入点**: {{ fund.buy_point }}
- **目标价位**: {{ fund.target_price }}
- **止损价位**: {{ fund.stop_loss }}
{% endfor %}

### 推荐买入

{% for fund in buy_funds %}
#### {{ fund.name }} ({{ fund.code }})

- **基金类型**: {{ fund.type }}
- **推荐理由**: {{ fund.reason }}
- **预期收益**: {{ fund.expected_return }}
- **风险等级**: {{ fund.risk_level }}
- **买入点**: {{ fund.buy_point }}
- **目标价位**: {{ fund.target_price }}
- **止损价位**: {{ fund.stop_loss }}
{% endfor %}

### 谨慎推荐

{% for fund in cautious_funds %}
#### {{ fund.name }} ({{ fund.code }})

- **基金类型**: {{ fund.type }}
- **推荐理由**: {{ fund.reason }}
- **预期收益**: {{ fund.expected_return }}
- **风险等级**: {{ fund.risk_level }}
- **买入点**: {{ fund.buy_point }}
- **目标价位**: {{ fund.target_price }}
- **止损价位**: {{ fund.stop_loss }}
{% endfor %}

### 不推荐

{% for fund in not_recommend_funds %}
#### {{ fund.name }} ({{ fund.code }})

- **基金类型**: {{ fund.type }}
- **不推荐理由**: {{ fund.reason }}
- **风险等级**: {{ fund.risk_level }}
{% endfor %}

## 风险提示

{{ risk_warning }}

## 免责声明

{{ disclaimer }}

---
*本报告由基金分析系统自动生成，仅供参考，不构成投资建议。投资有风险，入市需谨慎。*
"""

    # 保存Markdown模板
    with open(os.path.join(self.template_dir, "report.md.j2"), "w", encoding="utf-8") as f:
        f.write(markdown_template)

    # HTML模板
    html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>基金买卖操作分析报告</title>
    <style>
        body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
            background-color: #f9f9f9;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: #fff;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #2c3e50;
            margin-top: 30px;
            margin-bottom: 15px;
            border-left: 4px solid #3498db;
            padding-left: 10px;
        }
        h3 {
            color: #34495e;
            margin-top: 25px;
            margin-bottom: 10px;
        }
        .meta-info {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 30px;
        }
        .meta-info p {
            margin: 5px 0;
        }
        .fund-card {
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
            background-color: #fff;
        }
        .fund-card h3 {
            margin-top: 0;
            color: #2c3e50;
        }
        .fund-card .fund-code {
            color: #7f8c8d;
            font-weight: normal;
        }
        .fund-info {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }
        .fund-info-item {
            background-color: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
        }
        .fund-info-item strong {
            color: #2c3e50;
        }
        .recommendation-strong-buy {
            border-left: 4px solid #27ae60;
        }
        .recommendation-buy {
            border-left: 4px solid #3498db;
        }
        .recommendation-cautious {
            border-left: 4px solid #f39c12;
        }
        .recommendation-not {
            border-left: 4px solid #e74c3c;
        }
        .news-item {
            border-bottom: 1px solid #eee;
            padding-bottom: 15px;
            margin-bottom: 15px;
        }
        .news-item:last-child {
            border-bottom: none;
        }
        .news-title {
            font-weight: bold;
            color: #2c3e50;
        }
        .news-source {
            color: #7f8c8d;
            font-size: 0.9em;
        }
        .risk-warning, .disclaimer {
            background-color: #fff3cd;
            border: 1px solid #ffeeba;
            border-radius: 5px;
            padding: 15px;
            margin-top: 30px;
        }
        .disclaimer {
            background-color: #f8d7da;
            border-color: #f5c6cb;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            color: #7f8c8d;
            font-size: 0.9em;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        table, th, td {
            border: 1px solid #ddd;
        }
        th, td {
            padding: 12px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>基金买卖操作分析报告</h1>

        <div class="meta-info">
            <p><strong>报告生成时间</strong>: {{ report_time }}</p>
            <p><strong>分析基金数量</strong>: {{ fund_count }}</p>
            <p><strong>新闻数据来源</strong>: {{ news_sources }}</p>
            <p><strong>排名数据来源</strong>: {{ rank_sources }}</p>
        </div>

        <h2>摘要</h2>
        <p>{{ summary }}</p>

        <h2>市场概况</h2>

        <h3>市场热点新闻</h3>
        {% for news in hot_news %}
        <div class="news-item">
            <div class="news-title">{{ news.title }}</div>
            <div class="news-source">来源: {{ news.source }}</div>
            <p>{{ news.summary }}</p>
        </div>
        {% endfor %}

        <h3>市场整体趋势</h3>
        <p>{{ market_trend }}</p>

        <h2>推荐基金</h2>

        <h3>强烈推荐买入</h3>
        {% for fund in strong_buy_funds %}
        <div class="fund-card recommendation-strong-buy">
            <h3>{{ fund.name }} <span class="fund-code">({{ fund.code }})</span></h3>
            <div class="fund-info">
                <div class="fund-info-item"><strong>基金类型</strong>: {{ fund.type }}</div>
                <div class="fund-info-item"><strong>推荐理由</strong>: {{ fund.reason }}</div>
                <div class="fund-info-item"><strong>预期收益</strong>: {{ fund.expected_return }}</div>
                <div class="fund-info-item"><strong>风险等级</strong>: {{ fund.risk_level }}</div>
                <div class="fund-info-item"><strong>买入点</strong>: {{ fund.buy_point }}</div>
                <div class="fund-info-item"><strong>目标价位</strong>: {{ fund.target_price }}</div>
                <div class="fund-info-item"><strong>止损价位</strong>: {{ fund.stop_loss }}</div>
            </div>
        </div>
        {% endfor %}

        <h3>推荐买入</h3>
        {% for fund in buy_funds %}
        <div class="fund-card recommendation-buy">
            <h3>{{ fund.name }} <span class="fund-code">({{ fund.code }})</span></h3>
            <div class="fund-info">
                <div class="fund-info-item"><strong>基金类型</strong>: {{ fund.type }}</div>
                <div class="fund-info-item"><strong>推荐理由</strong>: {{ fund.reason }}</div>
                <div class="fund-info-item"><strong>预期收益</strong>: {{ fund.expected_return }}</div>
                <div class="fund-info-item"><strong>风险等级</strong>: {{ fund.risk_level }}</div>
                <div class="fund-info-item"><strong>买入点</strong>: {{ fund.buy_point }}</div>
                <div class="fund-info-item"><strong>目标价位</strong>: {{ fund.target_price }}</div>
                <div class="fund-info-item"><strong>止损价位</strong>: {{ fund.stop_loss }}</div>
            </div>
        </div>
        {% endfor %}

        <h3>谨慎推荐</h3>
        {% for fund in cautious_funds %}
        <div class="fund-card recommendation-cautious">
            <h3>{{ fund.name }} <span class="fund-code">({{ fund.code }})</span></h3>
            <div class="fund-info">
                <div class="fund-info-item"><strong>基金类型</strong>: {{ fund.type }}</div>
                <div class="fund-info-item"><strong>推荐理由</strong>: {{ fund.reason }}</div>
                <div class="fund-info-item"><strong>预期收益</strong>: {{ fund.expected_return }}</div>
                <div class="fund-info-item"><strong>风险等级</strong>: {{ fund.risk_level }}</div>
                <div class="fund-info-item"><strong>买入点</strong>: {{ fund.buy_point }}</div>
                <div class="fund-info-item"><strong>目标价位</strong>: {{ fund.target_price }}</div>
                <div class="fund-info-item"><strong>止损价位</strong>: {{ fund.stop_loss }}</div>
            </div>
        </div>
        {% endfor %}

        <h3>不推荐</h3>
        {% for fund in not_recommend_funds %}
        <div class="fund-card recommendation-not">
            <h3>{{ fund.name }} <span class="fund-code">({{ fund.code }})</span></h3>
            <div class="fund-info">
                <div class="fund-info-item"><strong>基金类型</strong>: {{ fund.type }}</div>
                <div class="fund-info-item"><strong>不推荐理由</strong>: {{ fund.reason }}</div>
                <div class="fund-info-item"><strong>风险等级</strong>: {{ fund.risk_level }}</div>
            </div>
        </div>
        {% endfor %}

        <h2>风险提示</h2>
        <div class="risk-warning">
            <p>{{ risk_warning }}</p>
        </div>

        <h2>免责声明</h2>
        <div class="disclaimer">
            <p>{{ disclaimer }}</p>
        </div>

        <div class="footer">
            <p>本报告由基金分析系统自动生成，仅供参考，不构成投资建议。投资有风险，入市需谨慎。</p>
        </div>
    </div>
</body>
</html>
"""

    # 保存HTML模板
    with open(os.path.join(self.template_dir, "report.html.j2"), "w", encoding="utf-8") as f:
        f.write(html_template)
