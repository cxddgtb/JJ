import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from config import ANALYSIS_PARAMS

class FundAnalyzer:
    """基金分析器，用于分析基金数据并生成买卖点"""

    def __init__(self):
        self.logger = logging.getLogger("FundAnalyzer")
        self.data_dir = "data"
        self.reports_dir = "reports"
        self._ensure_dirs()
        self.params = ANALYSIS_PARAMS

    def _ensure_dirs(self):
        """确保必要的目录存在"""
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(os.path.join(self.reports_dir, "charts"), exist_ok=True)
        os.makedirs(os.path.join(self.reports_dir, "analysis"), exist_ok=True)

    def load_fund_data(self, fund_code):
        """加载基金数据"""
        import json

        file_path = os.path.join(self.data_dir, "funds", f"{fund_code}.json")
        if not os.path.exists(file_path):
            self.logger.error(f"基金 {fund_code} 的数据文件不存在")
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"加载基金 {fund_code} 数据出错: {str(e)}")
            return None

    def load_news_data(self, days=7):
        """加载新闻数据"""
        import json
        from glob import glob

        news_files = glob(os.path.join(self.data_dir, "news", "news_*.json"))
        news_files.sort(reverse=True)  # 按文件名降序排序，最新的在前

        news_data = []
        cutoff_date = datetime.now() - timedelta(days=days)

        for file_path in news_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for news in data.get('data', []):
                    news_time = datetime.strptime(news['crawl_time'], '%Y-%m-%d %H:%M:%S')
                    if news_time >= cutoff_date:
                        news_data.append(news)

                # 如果已经获取了足够多的新闻，可以提前退出
                if len(news_data) >= 100:  # 假设我们最多需要100条新闻
                    break

            except Exception as e:
                self.logger.error(f"加载新闻文件 {file_path} 出错: {str(e)}")

        return news_data

    def analyze_fund(self, fund_code):
        """分析单个基金"""
        self.logger.info(f"开始分析基金 {fund_code}...")

        # 加载基金数据
        fund_data = self.load_fund_data(fund_code)
        if not fund_data:
            return None

        # 分析结果
        analysis_result = {
            'code': fund_code,
            'name': '',
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'technical_analysis': {},
            'fundamental_analysis': {},
            'sentiment_analysis': {},
            'recommendation': '',
            'risk_level': '',
            'buy_sell_points': []
        }

        # 获取基金名称
        for source, data in fund_data.items():
            if 'info' in data and 'name' in data['info']:
                analysis_result['name'] = data['info']['name']
                break

        # 技术分析
        analysis_result['technical_analysis'] = self._technical_analysis(fund_data)

        # 基本面分析
        analysis_result['fundamental_analysis'] = self._fundamental_analysis(fund_data)

        # 情感分析
        news_data = self.load_news_data()
        analysis_result['sentiment_analysis'] = self._sentiment_analysis(fund_code, news_data)

        # 综合分析和推荐
        self._comprehensive_analysis(analysis_result)

        # 生成买卖点
        analysis_result['buy_sell_points'] = self._generate_buy_sell_points(analysis_result)

        # 保存分析结果
        self._save_analysis_result(analysis_result)

        self.logger.info(f"基金 {fund_code} 分析完成")
        return analysis_result

    def _technical_analysis(self, fund_data):
        """技术分析"""
        result = {
            'trend': '',
            'strength': '',
            'indicators': {}
        }

        # 获取净值数据
        nav_data = None
        for source, data in fund_data.items():
            if 'nav' in data and data['nav']:
                nav_data = data['nav']
                break

        if not nav_data:
            return result

        try:
            # 转换为DataFrame
            df = pd.DataFrame(nav_data)
            df['date'] = pd.to_datetime(df['date'])
            df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
            df = df.dropna()
            df = df.sort_values('date')

            # 计算移动平均线
            df['ma_short'] = df['nav'].rolling(window=self.params['SHORT_TERM_MA']).mean()
            df['ma_mid'] = df['nav'].rolling(window=self.params['MID_TERM_MA']).mean()
            df['ma_long'] = df['nav'].rolling(window=self.params['LONG_TERM_MA']).mean()

            # 计算RSI
            df['rsi'] = self._calculate_rsi(df['nav'], self.params['RSI_PERIOD'])

            # 计算MACD
            macd_data = self._calculate_macd(df['nav'], self.params['MACD_FAST'], 
                                           self.params['MACD_SLOW'], self.params['MACD_SIGNAL'])
            df['macd'] = macd_data['macd']
            df['macd_signal'] = macd_data['signal']
            df['macd_histogram'] = macd_data['histogram']

            # 计算布林带
            bollinger_data = self._calculate_bollinger_bands(df['nav'], self.params['BOLLINGER_PERIOD'], 
                                                          self.params['BOLLINGER_STD_DEV'])
            df['bb_upper'] = bollinger_data['upper']
            df['bb_middle'] = bollinger_data['middle']
            df['bb_lower'] = bollinger_data['lower']

            # 获取最新数据
            latest = df.iloc[-1]

            # 趋势判断
            if latest['ma_short'] > latest['ma_mid'] > latest['ma_long']:
                result['trend'] = '上升趋势'
            elif latest['ma_short'] < latest['ma_mid'] < latest['ma_long']:
                result['trend'] = '下降趋势'
            else:
                result['trend'] = '震荡趋势'

            # 强度判断
            if latest['rsi'] > self.params['RSI_OVERBOUGHT']:
                result['strength'] = '超买'
            elif latest['rsi'] < self.params['RSI_OVERSOLD']:
                result['strength'] = '超卖'
            elif latest['rsi'] > 50:
                result['strength'] = '强势'
            else:
                result['strength'] = '弱势'

            # 保存指标数据
            result['indicators'] = {
                'ma_short': float(latest['ma_short']),
                'ma_mid': float(latest['ma_mid']),
                'ma_long': float(latest['ma_long']),
                'rsi': float(latest['rsi']),
                'macd': float(latest['macd']),
                'macd_signal': float(latest['macd_signal']),
                'macd_histogram': float(latest['macd_histogram']),
                'bb_upper': float(latest['bb_upper']),
                'bb_middle': float(latest['bb_middle']),
                'bb_lower': float(latest['bb_lower']),
                'current_nav': float(latest['nav'])
            }

            # 预测未来走势
            result['prediction'] = self._predict_trend(df)

        except Exception as e:
            self.logger.error(f"技术分析出错: {str(e)}")

        return result

    def _calculate_rsi(self, prices, period=14):
        """计算RSI指标"""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """计算MACD指标"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()

        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal).mean()
        histogram = macd - signal_line

        return {
            'macd': macd,
            'signal': signal_line,
            'histogram': histogram
        }

    def _calculate_bollinger_bands(self, prices, period=20, std_dev=2):
        """计算布林带"""
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()

        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        return {
            'upper': upper,
            'middle': middle,
            'lower': lower
        }

    def _predict_trend(self, df, days=5):
        """预测未来走势"""
        try:
            # 准备数据
            data = df['nav'].values.reshape(-1, 1)

            # 数据归一化
            scaler = MinMaxScaler(feature_range=(0, 1))
            scaled_data = scaler.fit_transform(data)

            # 创建时间序列数据
            X, y = [], []
            for i in range(60, len(scaled_data)):
                X.append(scaled_data[i-60:i, 0])
                y.append(scaled_data[i, 0])

            X, y = np.array(X), np.array(y)
            X = np.reshape(X, (X.shape[0], X.shape[1], 1))

            # 构建LSTM模型
            model = Sequential()
            model.add(LSTM(units=50, return_sequences=True, input_shape=(X.shape[1], 1)))
            model.add(Dropout(0.2))
            model.add(LSTM(units=50, return_sequences=False))
            model.add(Dropout(0.2))
            model.add(Dense(units=25))
            model.add(Dense(units=1))

            model.compile(optimizer='adam', loss='mean_squared_error')

            # 训练模型
            model.fit(X, y, epochs=10, batch_size=32, verbose=0)

            # 预测未来值
            last_60_days = scaled_data[-60:].reshape(1, -1, 1)
            predictions = []

            for _ in range(days):
                pred = model.predict(last_60_days)[0, 0]
                predictions.append(pred)
                # 更新输入，添加预测值并移除最早的值
                new_input = np.append(last_60_days[0, 1:, 0], pred).reshape(1, -1, 1)
                last_60_days = new_input

            # 反归一化
            predictions = np.array(predictions).reshape(-1, 1)
            predictions = scaler.inverse_transform(predictions)

            # 计算趋势
            current_price = df['nav'].iloc[-1]
            future_prices = predictions.flatten()

            trend = "上涨" if future_prices[-1] > current_price else "下跌"
            change_percent = ((future_prices[-1] - current_price) / current_price) * 100

            return {
                'trend': trend,
                'change_percent': float(change_percent),
                'predicted_prices': future_prices.tolist()
            }

        except Exception as e:
            self.logger.error(f"预测走势出错: {str(e)}")
            return {
                'trend': '未知',
                'change_percent': 0,
                'predicted_prices': []
            }

    def _fundamental_analysis(self, fund_data):
        """基本面分析"""
        result = {
            'scale_rating': '',
            'manager_rating': '',
            'performance_rating': '',
            'risk_rating': '',
            'overall_rating': ''
        }

        try:
            # 获取基金基本信息
            fund_info = None
            for source, data in fund_data.items():
                if 'info' in data and data['info']:
                    fund_info = data['info']
                    break

            if not fund_info:
                return result

            # 基金规模评级
            scale = fund_info.get('scale', '')
            if scale:
                scale_num = float(''.join(filter(lambda x: x.isdigit() or x == '.', scale)))
                if scale_num > 50:
                    result['scale_rating'] = '大型'
                elif scale_num > 10:
                    result['scale_rating'] = '中型'
                else:
                    result['scale_rating'] = '小型'

            # 基金经理评级（简化版，实际应该根据基金经理历史业绩评估）
            manager = fund_info.get('manager', '')
            result['manager_rating'] = '待评估' if manager else '未知'

            # 获取净值数据用于业绩评估
            nav_data = None
            for source, data in fund_data.items():
                if 'nav' in data and data['nav']:
                    nav_data = data['nav']
                    break

            if nav_data:
                # 转换为DataFrame
                df = pd.DataFrame(nav_data)
                df['date'] = pd.to_datetime(df['date'])
                df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
                df = df.dropna()
                df = df.sort_values('date')

                # 计算年化收益率
                if len(df) > 0:
                    first_nav = df['nav'].iloc[0]
                    last_nav = df['nav'].iloc[-1]
                    days = (df['date'].iloc[-1] - df['date'].iloc[0]).days

                    if days > 0 and first_nav > 0:
                        annual_return = ((last_nav / first_nav) ** (365 / days) - 1) * 100

                        if annual_return > 15:
                            result['performance_rating'] = '优秀'
                        elif annual_return > 8:
                            result['performance_rating'] = '良好'
                        elif annual_return > 0:
                            result['performance_rating'] = '一般'
                        else:
                            result['performance_rating'] = '较差'

                        # 计算波动率（风险）
                        daily_returns = df['nav'].pct_change().dropna()
                        volatility = daily_returns.std() * (365 ** 0.5) * 100

                        if volatility > 20:
                            result['risk_rating'] = '高风险'
                        elif volatility > 10:
                            result['risk_rating'] = '中风险'
                        else:
                            result['risk_rating'] = '低风险'

            # 综合评级（简化版）
            ratings = [
                result.get('scale_rating', ''),
                result.get('manager_rating', ''),
                result.get('performance_rating', ''),
                result.get('risk_rating', '')
            ]

            if '优秀' in ratings or '大型' in ratings:
                result['overall_rating'] = '推荐'
            elif '良好' in ratings or '中型' in ratings:
                result['overall_rating'] = '关注'
            else:
                result['overall_rating'] = '谨慎'

        except Exception as e:
            self.logger.error(f"基本面分析出错: {str(e)}")

        return result

    def _sentiment_analysis(self, fund_code, news_data):
        """情感分析"""
        result = {
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0,
            'sentiment_score': 0,
            'related_news': []
        }

        try:
            from snownlp import SnowNLP
            import jieba
            import re

            # 基金关键词
            fund_keywords = [fund_code]
            for source, data in self.load_fund_data(fund_code).items():
                if 'info' in data and 'name' in data['info']:
                    fund_name = data['info']['name']
                    # 从基金名称中提取关键词
                    name_parts = re.split(r'[()（）\s]', fund_name)
                    fund_keywords.extend([part for part in name_parts if part])

            # 分析每条新闻
            for news in news_data:
                title = news.get('title', '')
                detail = news.get('detail', '')
                content = title + ' ' + detail

                # 检查是否与基金相关
                is_related = False
                for keyword in fund_keywords:
                    if keyword in content:
                        is_related = True
                        break

                if not is_related:
                    continue

                # 情感分析
                s = SnowNLP(content)
                sentiment_score = s.sentiments

                if sentiment_score > 0.6:
                    result['positive_count'] += 1
                elif sentiment_score < 0.4:
                    result['negative_count'] += 1
                else:
                    result['neutral_count'] += 1

                # 保存相关新闻
                result['related_news'].append({
                    'title': title,
                    'url': news.get('url', ''),
                    'sentiment_score': sentiment_score,
                    'publish_time': news.get('crawl_time', '')
                })

            # 计算综合情感分数
            total = len(result['related_news'])
            if total > 0:
                result['sentiment_score'] = (result['positive_count'] - result['negative_count']) / total

        except Exception as e:
            self.logger.error(f"情感分析出错: {str(e)}")

        return result

    def _comprehensive_analysis(self, analysis_result):
        """综合分析"""
        try:
            # 获取各项分析结果
            tech = analysis_result['technical_analysis']
            fundamental = analysis_result['fundamental_analysis']
            sentiment = analysis_result['sentiment_analysis']

            # 计算综合评分
            tech_score = 0
            fundamental_score = 0
            sentiment_score = 0

            # 技术分析评分
            if tech.get('trend') == '上升趋势':
                tech_score += 30
            elif tech.get('trend') == '震荡趋势':
                tech_score += 15

            if tech.get('strength') == '强势':
                tech_score += 20
            elif tech.get('strength') == '超卖':
                tech_score += 15
            elif tech.get('strength') == '超买':
                tech_score -= 10

            prediction = tech.get('prediction', {})
            if prediction.get('trend') == '上涨':
                tech_score += 20
            elif prediction.get('trend') == '下跌':
                tech_score -= 20

            tech_score = max(0, min(100, tech_score))

            # 基本面分析评分
            if fundamental.get('scale_rating') == '大型':
                fundamental_score += 20
            elif fundamental.get('scale_rating') == '中型':
                fundamental_score += 10

            if fundamental.get('performance_rating') == '优秀':
                fundamental_score += 40
            elif fundamental.get('performance_rating') == '良好':
                fundamental_score += 25
            elif fundamental.get('performance_rating') == '一般':
                fundamental_score += 10

            if fundamental.get('risk_rating') == '低风险':
                fundamental_score += 20
            elif fundamental.get('risk_rating') == '中风险':
                fundamental_score += 10

            if fundamental.get('overall_rating') == '推荐':
                fundamental_score += 20
            elif fundamental.get('overall_rating') == '关注':
                fundamental_score += 10

            fundamental_score = max(0, min(100, fundamental_score))

            # 情感分析评分
            sentiment_total = sentiment.get('positive_count', 0) + sentiment.get('negative_count', 0) + sentiment.get('neutral_count', 0)
            if sentiment_total > 0:
                sentiment_score = (sentiment.get('positive_count', 0) / sentiment_total) * 100

            # 综合评分（加权平均）
            comprehensive_score = (tech_score * 0.5 + fundamental_score * 0.3 + sentiment_score * 0.2)

            # 生成推荐
            if comprehensive_score > 70:
                analysis_result['recommendation'] = '强烈推荐买入'
                analysis_result['risk_level'] = '低'
            elif comprehensive_score > 50:
                analysis_result['recommendation'] = '推荐买入'
                analysis_result['risk_level'] = '中低'
            elif comprehensive_score > 30:
                analysis_result['recommendation'] = '持有观望'
                analysis_result['risk_level'] = '中'
            elif comprehensive_score > 15:
                analysis_result['recommendation'] = '考虑卖出'
                analysis_result['risk_level'] = '中高'
            else:
                analysis_result['recommendation'] = '建议卖出'
                analysis_result['risk_level'] = '高'

            # 保存综合评分
            analysis_result['comprehensive_score'] = {
                'technical': tech_score,
                'fundamental': fundamental_score,
                'sentiment': sentiment_score,
                'overall': comprehensive_score
            }

        except Exception as e:
            self.logger.error(f"综合分析出错: {str(e)}")

    def _generate_buy_sell_points(self, analysis_result):
        """生成买卖点"""
        buy_sell_points = []

        try:
            # 获取技术分析结果
            tech = analysis_result['technical_analysis']
            indicators = tech.get('indicators', {})

            # 当前价格
            current_price = indicators.get('current_nav', 0)

            # 基于RSI生成买卖点
            rsi = indicators.get('rsi', 50)
            if rsi < self.params['RSI_OVERSOLD']:
                buy_sell_points.append({
                    'type': '买入',
                    'reason': f'RSI指标({rsi:.2f})低于超卖线({self.params["RSI_OVERSOLD"]})，可能出现反弹',
                    'strength': '强',
                    'price': current_price
                })
            elif rsi > self.params['RSI_OVERBOUGHT']:
                buy_sell_points.append({
                    'type': '卖出',
                    'reason': f'RSI指标({rsi:.2f})高于超买线({self.params["RSI_OVERBOUGHT"]})，可能出现回调',
                    'strength': '强',
                    'price': current_price
                })

            # 基于MACD生成买卖点
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            macd_histogram = indicators.get('macd_histogram', 0)

            if macd_histogram > 0 and macd > macd_signal:
                buy_sell_points.append({
                    'type': '买入',
                    'reason': 'MACD指标金叉，显示上涨趋势',
                    'strength': '中',
                    'price': current_price
                })
            elif macd_histogram < 0 and macd < macd_signal:
                buy_sell_points.append({
                    'type': '卖出',
                    'reason': 'MACD指标死叉，显示下跌趋势',
                    'strength': '中',
                    'price': current_price
                })

            # 基于布林带生成买卖点
            bb_upper = indicators.get('bb_upper', 0)
            bb_middle = indicators.get('bb_middle', 0)
            bb_lower = indicators.get('bb_lower', 0)

            if current_price <= bb_lower:
                buy_sell_points.append({
                    'type': '买入',
                    'reason': f'价格({current_price:.4f})接近布林带下轨({bb_lower:.4f})，可能反弹',
                    'strength': '中',
                    'price': current_price
                })
            elif current_price >= bb_upper:
                buy_sell_points.append({
                    'type': '卖出',
                    'reason': f'价格({current_price:.4f})接近布林带上轨({bb_upper:.4f})，可能回调',
                    'strength': '中',
                    'price': current_price
                })

            # 基于移动平均线生成买卖点
            ma_short = indicators.get('ma_short', 0)
            ma_mid = indicators.get('ma_mid', 0)
            ma_long = indicators.get('ma_long', 0)

            if ma_short > ma_mid > ma_long:
                buy_sell_points.append({
                    'type': '买入',
                    'reason': '短期、中期、长期均线呈多头排列，显示上涨趋势',
                    'strength': '强',
                    'price': current_price
                })
            elif ma_short < ma_mid < ma_long:
                buy_sell_points.append({
                    'type': '卖出',
                    'reason': '短期、中期、长期均线呈空头排列，显示下跌趋势',
                    'strength': '强',
                    'price': current_price
                })

            # 基于预测生成买卖点
            prediction = tech.get('prediction', {})
            if prediction.get('trend') == '上涨':
                change_percent = prediction.get('change_percent', 0)
                if change_percent > 5:  # 预测上涨超过5%
                    buy_sell_points.append({
                        'type': '买入',
                        'reason': f'模型预测未来可能上涨{change_percent:.2f}%',
                        'strength': '中',
                        'price': current_price
                    })
            elif prediction.get('trend') == '下跌':
                change_percent = prediction.get('change_percent', 0)
                if change_percent < -5:  # 预测下跌超过5%
                    buy_sell_points.append({
                        'type': '卖出',
                        'reason': f'模型预测未来可能下跌{change_percent:.2f}%',
                        'strength': '中',
                        'price': current_price
                    })

            # 根据综合评分生成买卖点
            comprehensive_score = analysis_result.get('comprehensive_score', {}).get('overall', 50)
            if comprehensive_score > 70:
                buy_sell_points.append({
                    'type': '买入',
                    'reason': f'综合评分({comprehensive_score:.1f})较高，建议买入',
                    'strength': '强',
                    'price': current_price
                })
            elif comprehensive_score < 30:
                buy_sell_points.append({
                    'type': '卖出',
                    'reason': f'综合评分({comprehensive_score:.1f})较低，建议卖出',
                    'strength': '强',
                    'price': current_price
                })

        except Exception as e:
            self.logger.error(f"生成买卖点出错: {str(e)}")

        return buy_sell_points

    def _save_analysis_result(self, analysis_result):
        """保存分析结果"""
        import json

        file_path = os.path.join(self.reports_dir, "analysis", f"{analysis_result['code']}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)

        self.logger.info(f"分析结果已保存到 {file_path}")

    def analyze_multiple_funds(self, fund_codes, max_workers=5):
        """分析多个基金"""
        self.logger.info(f"开始分析 {len(fund_codes)} 只基金...")

        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_code = {executor.submit(self.analyze_fund, code): code for code in fund_codes}

            for future in as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    result = future.result()
                    if result:
                        results[code] = result
                except Exception as e:
                    self.logger.error(f"分析基金 {code} 出错: {str(e)}")

        self.logger.info(f"成功分析了 {len(results)} 只基金")
        return results
