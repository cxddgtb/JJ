# 基金数据分析与买卖点预测系统

这是一个强大的GitHub工作流，用于爬取全网基金新闻和基金数据，分析买卖点，并生成操作文章。

## 功能特点

- 爬取全网基金新闻
- 爬取各个板块的基金数据
- 计算多项买卖指标（长期、中期、短期）
- 基于新闻数据和指标分析买卖点
- 生成详细的买卖操作文章
- 使用多线程提高效率
- 集成AI大模型进行智能分析

## 工作流程

1. 数据爬取
   - 基金新闻爬取
   - 各板块基金数据爬取
2. 数据处理
   - 数据清洗
   - 指标计算
3. 买卖点分析
   - 基于技术指标分析
   - 结合新闻情绪分析
4. 报告生成
   - 生成买卖点表格
   - 创建详细分析文章

## 使用方法

1. Fork此仓库
2. 配置GitHub Secrets
   - REPO_ACCESS_TOKEN: 您的GitHub访问令牌
   - OPENAI_API_KEY: OpenAI API密钥（可选，用于AI分析）
3. 创建工作流触发事件或手动触发

## 文件结构

```
├── .github/
│   └── workflows/
│       └── fund_analysis_workflow.yml
├── src/
│   ├── crawlers/
│   │   ├── news_crawler.py
│   │   └── fund_data_crawler.py
│   ├── analyzers/
│   │   ├── technical_analyzer.py
│   │   └── news_sentiment_analyzer.py
│   ├── models/
│   │   ├── indicators.py
│   │   └── trading_signals.py
│   └── generators/
│       ├── report_generator.py
│       └── article_generator.py
├── utils/
│   ├── config.py
│   ├── logger.py
│   └── helpers.py
├── data/
│   ├── raw/
│   ├── processed/
│   └── reports/
└── requirements.txt
```
