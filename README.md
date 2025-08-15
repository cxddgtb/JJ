# 基金数据分析与买卖点预测系统

<<<<<<< HEAD
这是一个强大的GitHub工作流，用于爬取全网基金新闻和基金数据，分析买卖点，并生成操作文章。
=======
本项目是一个完全运行在GitHub上的工作流，用于爬取全网基金新闻和基金数据，并通过新闻数据和各项指标分析当下基金数据的买卖点，最后生成买卖操作文章。
>>>>>>> b18564d6e095109b4e15afc2fd8319e3704d4f68

## 功能特点

- 爬取全网基金新闻
- 爬取各个板块的基金数据
- 计算多项买卖指标（长期、中期、短期）
<<<<<<< HEAD
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
=======
- 使用AI模型分析买卖点
- 生成买卖点表格（买入、卖出、观望）
- 生成买卖操作文章，包含新闻数据及具体原因
- 使用多线程提高效率
- 在关键步骤集成AI大模型分析

## 项目结构
>>>>>>> b18564d6e095109b4e15afc2fd8319e3704d4f68

```
├── .github/
│   └── workflows/
<<<<<<< HEAD
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
=======
│       └── fund_analysis_workflow.yml    # GitHub工作流配置
├── src/
│   ├── crawlers/                         # 爬虫模块
│   │   ├── news_crawler.py               # 新闻爬虫
│   │   └── fund_crawler.py               # 基金数据爬虫
│   ├── indicators/                       # 指标计算模块
│   │   ├── long_term_indicators.py       # 长期指标计算
│   │   ├── mid_term_indicators.py        # 中期指标计算
│   │   └── short_term_indicators.py      # 短期指标计算
│   ├── analysis/                         # 分析模块
│   │   ├── buy_sell_analysis.py          # 买卖点分析
│   │   └── ai_analysis.py                # AI分析
│   ├── report/                           # 报告生成模块
│   │   ├── generate_table.py             # 生成买卖点表格
│   │   └── generate_article.py           # 生成操作文章
│   └── utils/                            # 工具模块
│       ├── thread_pool.py                # 线程池
│       └── config.py                     # 配置文件
├── data/                                 # 数据存储目录
├── output/                               # 输出目录
├── requirements.txt                      # Python依赖
└── main.py                               # 主程序入口
```

## 使用说明

1. Fork此仓库到您的GitHub账户
2. 在仓库设置中配置名为REPO_ACCESS_TOKEN的GitHub Token
3. 工作流将自动运行，您可以在Actions标签页查看运行结果
4. 生成的报告和文章将保存在output目录中

## 注意事项

- 本项目仅用于学习和研究目的，不构成投资建议
- 所有数据均来自公开网络，请确保遵守相关网站的使用条款
>>>>>>> b18564d6e095109b4e15afc2fd8319e3704d4f68
