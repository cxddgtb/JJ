# 基金分析系统

这是一个完全运行在GitHub上的工作流，用于爬取全网基金消息和数据，分析当下买卖点，并生成买卖操作文章。

## 功能特点

- 自动爬取多个基金网站的基金数据
- 使用机器学习和深度学习分析基金走势
- 生成详细的买卖操作建议报告
- 支持多线程处理，提高效率
- 完全自动化运行，无需人工干预

## 系统架构

### 爬虫模块 (crawlers/)

- **base_crawler.py**: 爬虫基类，定义了爬虫的基本功能和接口
- **eastmoney_crawler.py**: 天天基金网爬虫实现
- **sina_crawler.py**: 新浪财经爬虫实现
- **crawler_manager.py**: 爬虫管理器，用于统一管理所有爬虫

### 分析模块 (analyzers/)

- **fund_analyzer.py**: 基金分析器，用于分析基金数据并生成买卖点

### 报告模块 (reporters/)

- **report_generator.py**: 报告生成器，用于生成买卖操作文章

### 配置文件

- **config.py**: 系统配置文件，包含各种设置和参数
- **requirements.txt**: 项目依赖文件
- **main.py**: 主程序文件，用于整合所有模块并执行基金分析

## 使用方法

### 1. 克隆项目到本地

```bash
git clone https://github.com/your_username/fund_analysis.git
cd fund_analysis
```

### 2. 设置环境变量

在GitHub仓库的Settings > Secrets and variables > Actions中添加以下环境变量：

- `REPO_ACCESS_TOKEN`: 你的GitHub访问令牌
- `GITHUB_REPOSITORY_OWNER`: 你的GitHub用户名
- `GITHUB_REPOSITORY_NAME`: 仓库名称（默认为fund_analysis）

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 本地运行（可选）

如果你想本地测试系统，可以运行：

```bash
python main.py
```

### 5. 部署到GitHub Actions

系统已经配置为GitHub Actions工作流，会自动在每周一至周五的早上9点（中国时区）执行。你也可以手动触发工作流。

## 工作流程

1. **爬取数据**: 从多个基金网站爬取基金列表、详情、新闻和排名数据
2. **分析数据**: 使用技术分析和基本面分析方法，结合机器学习模型分析基金数据
3. **生成报告**: 基于分析结果生成买卖操作建议报告
4. **保存报告**: 将生成的报告保存到GitHub仓库

## 报告内容

生成的报告包含以下部分：

- **摘要**: 对整体市场和分析结果的概述
- **市场概况**: 包括市场热点新闻和整体趋势分析
- **推荐基金**: 按推荐等级分类的基金列表，包括买入点、目标价位和止损价位
- **风险提示**: 投资风险提示
- **免责声明**: 免责声明

## 注意事项

- 本系统仅供学习和研究使用，不构成任何投资建议
- 投资有风险，入市需谨慎
- 系统分析结果仅供参考，实际投资决策请结合自身情况

## 许可证

本项目采用MIT许可证，详情请参阅LICENSE文件。
