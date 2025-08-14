import os
import logging
import json
import markdown
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader
from config import REPORT_CONFIG

class ReportGenerator:
    """报告生成器，用于生成买卖操作文章"""

    def __init__(self):
        self.logger = logging.getLogger("ReportGenerator")
        self.data_dir = "data"
        self.reports_dir = REPORT_CONFIG["OUTPUT_DIR"]
        self.template_dir = REPORT_CONFIG["TEMPLATE_DIR"]
        self.static_dir = REPORT_CONFIG["STATIC_DIR"]
        self._ensure_dirs()

        # 设置Jinja2环境
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=True
        )

    def _ensure_dirs(self):
        """确保必要的目录存在"""
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.template_dir, exist_ok=True)
        os.makedirs(self.static_dir, exist_ok=True)
        os.makedirs(os.path.join(self.static_dir, "images"), exist_ok=True)
        os.makedirs(os.path.join(self.reports_dir, "markdown"), exist_ok=True)
        os.makedirs(os.path.join(self.reports_dir, "html"), exist_ok=True)
        os.makedirs(os.path.join(self.reports_dir, "pdf"), exist_ok=True)

    def load_analysis_results(self, analysis_dir=None):
        """加载分析结果"""
        if analysis_dir is None:
            analysis_dir = os.path.join(self.data_dir, "analysis")

        analysis_files = []
        for root, _, files in os.walk(analysis_dir):
            for file in files:
                if file.endswith('.json'):
                    analysis_files.append(os.path.join(root, file))

        results = []
        for file_path in analysis_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results.append(data)
            except Exception as e:
                self.logger.error(f"加载分析文件 {file_path} 出错: {str(e)}")

        return results

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

    def load_rank_data(self):
        """加载排名数据"""
        import json
        from glob import glob

        rank_files = glob(os.path.join(self.data_dir, "ranks", "ranks_*.json"))
        rank_files.sort(reverse=True)  # 按文件名降序排序，最新的在前

        if not rank_files:
            return {}

        try:
            with open(rank_files[0], 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"加载排名文件 {rank_files[0]} 出错: {str(e)}")
            return {}
