# 基金数据分析与买卖点生成系统

这是一个强大的GitHub工作流，用于搜索全网基金新闻、爬取基金数据和各种买卖指标，通过AI分析生成买卖操作文章。

## 功能特点

- 全网基金新闻搜索与爬取
- 多源基金数据获取（包括免费API）
- 多种买卖指标分析与计算
- AI驱动的买卖点分析
- 自动生成买卖操作建议文章
- 多线程处理提高效率
- 多浏览器与多搜索引擎支持
- AI文章润色功能

## 工作流程

1. **新闻搜索阶段**：使用多个搜索引擎和关键词策略搜索基金相关新闻
2. **数据爬取阶段**：从多个源爬取基金数据、指标和历史数据
3. **数据分析阶段**：结合新闻数据和指标数据，分析买卖点
4. **文章生成阶段**：AI生成买卖操作建议文章
5. **内容润色阶段**：AI润色文章，使其适合社区发布

## 环境要求

- Python 3.8+
- GitHub Actions
- 多种浏览器（Chrome, Firefox等）

## 配置说明

在使用前，请确保配置好以下内容：

1. GitHub Secrets中添加：
   - `REPO_ACCESS_TOKEN`: 用于GitHub API访问
   - `OPENAI_API_KEY`: 用于OpenAI API调用（可选）
   - `BAIDU_API_KEY`: 用于百度API调用（可选）
   - 其他需要的API密钥

## 文件结构

```
├── .github/
│   └── workflows/
│       └── fund_analysis.yml      # GitHub Actions工作流文件
├── src/
│   ├── __init__.py
│   ├── config.py                 # 配置文件
│   ├── news_crawler.py           # 新闻爬取模块
│   ├── data_crawler.py           # 数据爬取模块
│   ├── indicators.py             # 指标计算模块
│   ├── ai_analysis.py            # AI分析模块
│   ├── article_generator.py      # 文章生成模块
│   └── utils.py                  # 工具函数
├── templates/
│   ├── article_template.txt      # 文章模板
│   └── analysis_prompt.txt       # 分析提示词
├── outputs/
│   ├── raw_data/                 # 原始数据
│   ├── processed_data/           # 处理后数据
│   ├── analysis_results/         # 分析结果
│   └── articles/                 # 生成的文章
├── requirements.txt              # 依赖包列表
└── README.md                     # 项目说明文档
```

## 使用方法

1. Fork此仓库到你的GitHub账户
2. 根据需要修改配置文件
3. 提交更改并触发GitHub Actions工作流
4. 在`outputs/articles`目录中查看生成的文章

## 注意事项

- 请确保遵守各数据源的使用条款
- 避免过于频繁的请求，以免被目标网站封禁
- 定期更新API密钥和依赖包
