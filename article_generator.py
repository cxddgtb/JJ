#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文章生成器模块
根据分析结果生成基金操作建议文章
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any
import random

class ArticleGenerator:
    """文章生成器类"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def generate_article(self, technical_report: Dict, trading_signals: Dict) -> str:
        """生成完整的分析文章"""
        try:
            self.logger.info("开始生成分析文章...")
            
            current_date = datetime.now().strftime('%Y年%m月%d日')
            
            title = f"基金市场分析报告：{current_date} 买卖点操作指南"
            introduction = "基于最新的基金数据分析，我们为您提供专业的投资建议。"
            
            # 生成文章内容
            article = f"""# {title}

## 引言
{introduction}

## 市场概况
{self.generate_market_overview(technical_report)}

## 买入推荐
{self.generate_buy_section(trading_signals)}

## 卖出建议
{self.generate_sell_section(trading_signals)}

## 风险提示
投资有风险，入市需谨慎。本报告仅供参考，不构成投资建议。

---
*报告生成时间：{current_date}*
"""
            
            self.logger.info("文章生成完成")
            return article
            
        except Exception as e:
            self.logger.error(f"生成文章失败: {e}")
            return "文章生成失败，请检查数据源和分析结果。"
    
    def generate_market_overview(self, technical_report: Dict) -> str:
        """生成市场概况部分"""
        try:
            summary = technical_report.get('summary', {})
            market_sentiment = technical_report.get('market_sentiment', '中性')
            
            buy_ratio = summary.get('buy_ratio', 0) * 100
            sell_ratio = summary.get('sell_ratio', 0) * 100
            total_funds = summary.get('total_funds', 0)
            avg_score = summary.get('avg_score', 50)
            
            return f"""当前市场整体呈现{market_sentiment}情绪，{buy_ratio:.1f}%的基金发出买入信号，{sell_ratio:.1f}%的基金建议卖出。

### 详细统计
- **分析基金总数**: {total_funds} 只
- **买入信号基金**: {summary.get('buy_signals', 0)} 只
- **卖出信号基金**: {summary.get('sell_signals', 0)} 只
- **平均综合评分**: {avg_score:.1f}/100
"""
            
        except Exception as e:
            self.logger.error(f"生成市场概况失败: {e}")
            return "市场概况分析暂时无法生成。"
    
    def generate_buy_section(self, trading_signals: Dict) -> str:
        """生成买入推荐部分"""
        try:
            buy_funds = trading_signals.get('buy', [])
            
            if not buy_funds:
                return "当前市场环境下，暂无明显买入机会，建议保持观望。"
            
            section = "基于技术分析，以下基金当前具有较好的买入机会：\n\n"
            
            for i, fund in enumerate(buy_funds[:10], 1):
                fund_code = fund.get('fund_code', '')
                fund_name = fund.get('fund_name', '')
                score = fund.get('score', 0)
                reasons = fund.get('reasons', [])
                
                section += f"### {i}. {fund_name} ({fund_code})\n"
                section += f"- **综合评分**: {score:.1f}/100\n"
                section += f"- **推荐理由**: {', '.join(reasons[:3])}\n\n"
            
            return section
            
        except Exception as e:
            self.logger.error(f"生成买入推荐失败: {e}")
            return "买入推荐生成失败。"
    
    def generate_sell_section(self, trading_signals: Dict) -> str:
        """生成卖出建议部分"""
        try:
            sell_funds = trading_signals.get('sell', [])
            
            if not sell_funds:
                return "当前市场环境下，暂无明显卖出信号，建议继续持有。"
            
            section = "基于风险控制考虑，以下基金建议及时卖出：\n\n"
            
            for i, fund in enumerate(sell_funds[:10], 1):
                fund_code = fund.get('fund_code', '')
                fund_name = fund.get('fund_name', '')
                score = fund.get('score', 0)
                reasons = fund.get('reasons', [])
                
                section += f"### {i}. {fund_name} ({fund_code})\n"
                section += f"- **综合评分**: {score:.1f}/100\n"
                section += f"- **卖出理由**: {', '.join(reasons[:3])}\n\n"
            
            return section
            
        except Exception as e:
            self.logger.error(f"生成卖出建议失败: {e}")
            return "卖出建议生成失败。"
