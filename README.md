# 基金数据分析与买卖点生成系统

这是一个完全运行在GitHub上的自动化基金分析系统，能够爬取全网基金数据、分析买卖点并生成操作建议文章。

## 功能特点

- 🔄 **自动化运行**: 通过GitHub Actions实现定时自动运行
- 📊 **多线程爬取**: 支持并发爬取基金数据，提高效率
- 📈 **技术分析**: 包含MA、MACD、RSI、KDJ、布林带等技术指标
- 🎯 **买卖点判断**: 基于多指标综合分析生成买卖信号
- 📝 **文章生成**: 自动生成专业的投资分析文章
- 📊 **图表生成**: 自动生成分析图表和可视化报告
- 💾 **数据存储**: 支持JSON和Excel格式的数据导出

## 系统架构

```
├── main.py                 # 主程序入口
├── fund_crawler.py         # 基金数据爬虫
├── fund_analyzer.py        # 基金分析器
├── article_generator.py    # 文章生成器
├── data_processor.py       # 数据处理器
├── utils/                  # 工具模块
│   ├── logger.py          # 日志配置
│   └── config.py          # 配置管理
├── .github/workflows/      # GitHub Actions工作流
└── requirements.txt        # 依赖包列表
```

## 技术指标

系统使用以下技术指标进行基金分析：

- **移动平均线 (MA)**: 5日、10日、20日、60日均线
- **MACD**: 指数平滑移动平均线
- **RSI**: 相对强弱指标
- **KDJ**: 随机指标
- **布林带**: 价格通道指标
- **趋势强度**: 线性回归分析
- **波动率**: 年化波动率计算
- **动量指标**: 价格动量分析

## 风险评估

系统包含完整的风险评估体系：

- **最大回撤**: 计算历史最大回撤
- **夏普比率**: 风险调整后收益
- **VaR**: 风险价值计算
- **综合风险评分**: 多维度风险评估

## 安装和使用

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/fund-analysis-system.git
cd fund-analysis-system
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置参数

在GitHub仓库的Settings > Secrets中添加以下密钥：

- `TUSHARE_TOKEN`: Tushare数据接口的API密钥

### 4. 运行系统

#### 手动运行
```bash
python main.py
```

#### 自动运行
系统会通过GitHub Actions在以下时间自动运行：
- 每天上午9点
- 每天下午3点
- 代码推送时
- 手动触发

## 输出文件

系统运行后会生成以下文件：

### 数据文件
- `data/fund_data.json`: 原始基金数据
- `output/analysis_results.json`: 分析结果
- `reports/market_report.json`: 市场报告

### 文章文件
- `output/fund_analysis_article_YYYYMMDD_HHMMSS.md`: 分析文章

### 图表文件
- `charts/signal_distribution.png`: 信号分布图
- `charts/score_distribution.png`: 评分分布图
- `charts/risk_distribution.png`: 风险分布图
- `charts/technical_heatmap.png`: 技术指标热力图

### Excel文件
- `output/fund_analysis_YYYYMMDD_HHMMSS.xlsx`: 分析数据表格

## 配置说明

### 系统配置

在`config/config.json`中可以配置以下参数：

```json
{
  "tushare_token": "your_token_here",
  "max_workers": 10,
  "timeout": 300,
  "output_dir": "output",
  "log_level": "INFO",
  "fund_categories": ["股票型", "混合型", "债券型"],
  "analysis_periods": [7, 30, 90, 180, 365],
  "technical_indicators": ["MA", "MACD", "RSI", "KDJ", "BOLL"]
}
```

### 工作流配置

GitHub Actions工作流配置在`.github/workflows/fund_analysis.yml`中：

- **触发条件**: 定时任务、代码推送、手动触发
- **运行环境**: Ubuntu最新版
- **Python版本**: 3.9
- **超时设置**: 30分钟

## 注意事项

1. **数据源**: 系统使用东方财富、新浪财经等公开数据源
2. **风险提示**: 本系统仅供学习研究使用，不构成投资建议
3. **API限制**: 请注意各数据源的API调用频率限制
4. **网络环境**: 确保GitHub Actions能够正常访问数据源

## 故障排除

### 常见问题

1. **依赖安装失败**
   - 检查Python版本是否为3.9+
   - 尝试使用国内镜像源

2. **数据爬取失败**
   - 检查网络连接
   - 验证API密钥是否正确
   - 查看日志文件获取详细错误信息

3. **分析结果异常**
   - 检查数据完整性
   - 验证技术指标参数
   - 查看分析日志

### 日志查看

系统会生成详细的日志文件：

- `logs/fund_analysis_system_YYYYMMDD_HHMMSS.log`: 主程序日志
- `logs/fund_analysis_system_error_YYYYMMDD_HHMMSS.log`: 错误日志

## 贡献指南

欢迎提交Issue和Pull Request来改进系统：

1. Fork本仓库
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

本项目采用MIT许可证，详见LICENSE文件。

## 免责声明

本系统仅供学习和研究使用，不构成任何投资建议。投资有风险，入市需谨慎。使用者应自行承担投资风险，作者不承担任何投资损失责任。
