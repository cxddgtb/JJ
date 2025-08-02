# 基金短线买卖大模型

这个项目是一个完全在GitHub上运行的基金短线买卖预测模型。通过GitHub Actions实现自动化的数据获取、模型训练和预测。

## 项目结构
- `data/`: 存储基金数据
- `models/`: 存储训练好的模型
- `scripts/`: 包含数据获取、预处理、训练和预测的脚本
- `.github/workflows/`: GitHub Actions工作流配置

## 功能特点
1. 自动从公开API获取基金数据
2. 使用机器学习算法训练短线交易模型
3. 基于最新数据进行买卖点预测
4. 通过GitHub Actions实现完全自动化

## 使用方法
1. Fork此仓库
2. 在GitHub Secrets中添加必要的API密钥
3. 触发GitHub Actions工作流开始训练或预测

## 免责声明
本项目仅供学习和研究使用，不构成任何投资建议。投资有风险，入市需谨慎。