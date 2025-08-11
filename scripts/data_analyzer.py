import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from config import settings
from scripts.utils import save_data, get_trading_date, setup_logging

logger = setup_logging()

class TradingSignalAnalyzer:
    def __init__(self, stock_signals, fund_signals):
        self.stock_signals = stock_signals
        self.fund_signals = fund_signals
        self.trading_date = datetime.now().strftime('%Y-%m-%d')
        self.combined_signals = {}
        
    def analyze_market_trend(self):
        """分析市场整体趋势"""
        # 股票市场信号统计
        stock_signals = pd.DataFrame(self.stock_signals.values())
        stock_buy = len(stock_signals[stock_signals['signal'] == 1])
        stock_sell = len(stock_signals[stock_signals['signal'] == -1])
        stock_neutral = len(stock_signals[stock_signals['signal'] == 0])
        
        # 基金市场信号统计
        fund_signals = pd.DataFrame(self.fund_signals)
        fund_buy = len(fund_signals[fund_signals['signal'] == 1])
        fund_sell = len(fund_signals[fund_signals['signal'] == -1])
        fund_neutral = len(fund_signals[fund_signals['signal'] == 0])
        
        # 综合市场强度
        market_strength = 0
        market_strength += stock_buy - stock_sell
        market_strength += fund_buy - fund_sell
        
        # 市场情绪判断
        if market_strength > 5:
            market_sentiment = "强烈看涨"
        elif market_strength > 2:
            market_sentiment = "看涨"
        elif market_strength < -5:
            market_sentiment = "强烈看跌"
        elif market_strength < -2:
            market_sentiment = "看跌"
        else:
            market_sentiment = "中性"
            
        return {
            'date': self.trading_date,
            'stock_buy': stock_buy,
            'stock_sell': stock_sell,
            'stock_neutral': stock_neutral,
            'fund_buy': fund_buy,
            'fund_sell': fund_sell,
            'fund_neutral': fund_neutral,
            'market_strength': market_strength,
            'market_sentiment': market_sentiment
        }
        
    def generate_trading_recommendations(self):
        """生成交易推荐"""
        # 顶级买入推荐（股票）
        stock_signals = pd.DataFrame(self.stock_signals.values())
        top_buy_stocks = stock_signals[stock_signals['signal'] == 1].sort_values(
            by=['rsi', 'macd_hist'], ascending=[True, False]
        ).head(3)
        
        # 顶级卖出推荐（股票）
        top_sell_stocks = stock_signals[stock_signals['signal'] == -1].sort_values(
            by=['rsi', 'macd_hist'], ascending=[False, True]
        ).head(3)
        
        # 顶级买入推荐（基金）
        fund_signals = pd.DataFrame(self.fund_signals)
        top_buy_funds = fund_signals[fund_signals['signal'] == 1].sort_values(
            by='daily_return', ascending=False
        ).head(3)
        
        # 顶级卖出推荐（基金）
        top_sell_funds = fund_signals[fund_signals['signal'] == -1].sort_values(
            by='daily_return', ascending=True
        ).head(3)
        
        return {
            'top_buy_stocks': top_buy_stocks.to_dict('records'),
            'top_sell_stocks': top_sell_stocks.to_dict('records'),
            'top_buy_funds': top_buy_funds.to_dict('records'),
            'top_sell_funds': top_sell_funds.to_dict('records')
        }
        
    def visualize_market_data(self, market_trend):
        """生成市场数据可视化"""
        try:
            # 股票市场信号分布
            plt.figure(figsize=(10, 6))
            plt.subplot(1, 2, 1)
            plt.pie(
                [market_trend['stock_buy'], market_trend['stock_sell'], market_trend['stock_neutral']],
                labels=['买入', '卖出', '观望'],
                autopct='%1.1f%%',
                colors=['green', 'red', 'gray']
            )
            plt.title('股票市场信号分布')
            
            # 基金市场信号分布
            plt.subplot(1, 2, 2)
            plt.pie(
                [market_trend['fund_buy'], market_trend['fund_sell'], market_trend['fund_neutral']],
                labels=['买入', '卖出', '观望'],
                autopct='%1.1f%%',
                colors=['green', 'red', 'gray']
            )
            plt.title('基金市场信号分布')
            
            plt.tight_layout()
            img_path = save_data(plt, "market_distribution.png", "charts")
            plt.close()
            return img_path
        except Exception as e:
            logger.exception("生成可视化图表失败")
            return None
            
    def run(self):
        """执行综合分析"""
        logger.info("开始综合分析交易信号")
        
        # 分析市场趋势
        market_trend = self.analyze_market_trend()
        
        # 生成交易推荐
        recommendations = self.generate_trading_recommendations()
        
        # 生成可视化图表
        chart_path = self.visualize_market_data(market_trend)
        
        # 组合结果
        self.combined_signals = {
            'market_trend': market_trend,
            'recommendations': recommendations,
            'stock_signals': self.stock_signals,
            'fund_signals': self.fund_signals,
            'chart_path': chart_path
        }
        
        # 保存分析结果
        save_data(self.combined_signals, "combined_signals.json")
        logger.info("综合分析完成")
        return self.combined_signals
