#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
"""

import json
import os
from typing import Dict, Any

class Config:
    """配置管理类"""
    
    def __init__(self, config_file='config/config.json'):
        self.config_file = config_file
        self.config = self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            'tushare_token': '',
            'max_workers': 10,
            'timeout': 300,
            'output_dir': 'output',
            'log_level': 'INFO',
            'fund_categories': ['股票型', '混合型', '债券型'],
            'analysis_periods': [7, 30, 90, 180, 365],
            'technical_indicators': ['MA', 'MACD', 'RSI', 'KDJ', 'BOLL'],
            'risk_levels': ['低风险', '中风险', '高风险'],
            'market_sources': [
                '东方财富',
                '新浪财经',
                '证券时报',
                '中国证券报',
                '上海证券报'
            ]
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            else:
                # 创建默认配置文件
                os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, ensure_ascii=False, indent=2)
                return default_config
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return default_config
    
    def get(self, key: str, default=None):
        """获取配置值"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置配置值"""
        self.config[key] = value
        self.save_config()
    
    def save_config(self):
        """保存配置文件"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def get_fund_categories(self) -> list:
        """获取基金分类"""
        return self.config.get('fund_categories', [])
    
    def get_analysis_periods(self) -> list:
        """获取分析周期"""
        return self.config.get('analysis_periods', [])
    
    def get_technical_indicators(self) -> list:
        """获取技术指标"""
        return self.config.get('technical_indicators', [])
    
    def get_market_sources(self) -> list:
        """获取市场数据源"""
        return self.config.get('market_sources', [])
