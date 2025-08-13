#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据处理器模块
负责数据的保存、加载和格式化
"""

import json
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List, Any
import os

class DataProcessor:
    """数据处理器类"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def save_fund_data(self, fund_data_list: List[Dict], file_path: str):
        """保存基金数据"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(fund_data_list, f, ensure_ascii=False, indent=2, default=str)
            self.logger.info(f"基金数据已保存到: {file_path}")
        except Exception as e:
            self.logger.error(f"保存基金数据失败: {e}")
    
    def save_analysis_results(self, analysis_results: List[Dict], file_path: str):
        """保存分析结果"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_results, f, ensure_ascii=False, indent=2, default=str)
            self.logger.info(f"分析结果已保存到: {file_path}")
        except Exception as e:
            self.logger.error(f"保存分析结果失败: {e}")
    
    def save_report(self, report: Dict, file_path: str):
        """保存报告"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            self.logger.info(f"报告已保存到: {file_path}")
        except Exception as e:
            self.logger.error(f"保存报告失败: {e}")
    
    def format_fund_data_for_excel(self, fund_data_list: List[Dict]) -> pd.DataFrame:
        """格式化基金数据为Excel格式"""
        try:
            formatted_data = []
            for fund_data in fund_data_list:
                fund_code = fund_data.get('fund_code', '')
                fund_info = fund_data.get('fund_info', {})
                nav_data = fund_data.get('nav_data', [])
                
                if nav_data:
                    latest_nav = nav_data[-1] if isinstance(nav_data, list) else nav_data
                    row = {
                        '基金代码': fund_code,
                        '基金名称': fund_info.get('fund_name', ''),
                        '基金类型': fund_info.get('fund_type', ''),
                        '最新净值': latest_nav.get('累计净值', 0),
                        '净值日期': latest_nav.get('净值日期', ''),
                        '日收益率': latest_nav.get('日收益率', 0)
                    }
                    formatted_data.append(row)
            
            return pd.DataFrame(formatted_data)
        except Exception as e:
            self.logger.error(f"格式化基金数据失败: {e}")
            return pd.DataFrame()
    
    def format_analysis_results_for_excel(self, analysis_results: List[Dict]) -> pd.DataFrame:
        """格式化分析结果为Excel格式"""
        try:
            formatted_data = []
            for result in analysis_results:
                fund_code = result.get('fund_code', '')
                fund_info = result.get('fund_info', {})
                signals = result.get('trading_signals', {})
                
                row = {
                    '基金代码': fund_code,
                    '基金名称': fund_info.get('fund_name', ''),
                    '综合评分': result.get('overall_score', 0),
                    '交易信号': signals.get('current_signal', 'hold'),
                    '信号强度': signals.get('signal_strength', 0)
                }
                formatted_data.append(row)
            
            return pd.DataFrame(formatted_data)
        except Exception as e:
            self.logger.error(f"格式化分析结果失败: {e}")
            return pd.DataFrame()
    
    def save_to_excel(self, data: pd.DataFrame, file_path: str, sheet_name: str = 'Sheet1'):
        """保存数据到Excel文件"""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                data.to_excel(writer, sheet_name=sheet_name, index=False)
            self.logger.info(f"数据已保存到Excel: {file_path}")
        except Exception as e:
            self.logger.error(f"保存Excel文件失败: {e}")
