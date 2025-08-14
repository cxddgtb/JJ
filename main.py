import os
import sys
import logging
import json
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crawlers.crawler_manager import CrawlerManager
from analyzers.fund_analyzer import FundAnalyzer
from reporters.report_generator import ReportGenerator
from config import LOGGING_CONFIG

# 设置日志
import logging.config
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("Main")

def setup_environment():
    """设置环境"""
    # 创建必要的目录
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/funds", exist_ok=True)
    os.makedirs("data/news", exist_ok=True)
    os.makedirs("data/ranks", exist_ok=True)
    os.makedirs("data/analysis", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    os.makedirs("reports/markdown", exist_ok=True)
    os.makedirs("reports/html", exist_ok=True)
    os.makedirs("reports/pdf", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    os.makedirs("static/images", exist_ok=True)

def load_fund_list():
    """加载基金列表"""
    fund_list_path = "data/fund_list.json"
    if os.path.exists(fund_list_path):
        try:
            with open(fund_list_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('data', [])
        except Exception as e:
            logger.error(f"加载基金列表出错: {str(e)}")
    return []

def save_fund_list(fund_list):
    """保存基金列表"""
    fund_list_path = "data/fund_list.json"
    try:
        with open(fund_list_path, 'w', encoding='utf-8') as f:
            json.dump({
                'data': fund_list,
                'count': len(fund_list),
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"基金列表已保存到 {fund_list_path}")
    except Exception as e:
        logger.error(f"保存基金列表出错: {str(e)}")

def analyze_funds(fund_codes, analyzer, max_workers=5):
    """分析多个基金"""
    logger.info(f"开始分析 {len(fund_codes)} 只基金...")

    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_code = {executor.submit(analyzer.analyze_fund, code): code for code in fund_codes}

        for future in as_completed(future_to_code):
            code = future_to_code[future]
            try:
                result = future.result()
                if result:
                    results[code] = result
                    logger.info(f"基金 {code} 分析完成")
                else:
                    logger.warning(f"基金 {code} 分析失败")
            except Exception as e:
                logger.error(f"分析基金 {code} 出错: {str(e)}")

    logger.info(f"成功分析了 {len(results)} 只基金")
    return results

def main():
    """主函数"""
    logger.info("基金分析系统启动")

    # 设置环境
    setup_environment()

    try:
        # 初始化组件
        crawler_manager = CrawlerManager()
        analyzer = FundAnalyzer()
        report_generator = ReportGenerator()

        # 加载基金列表
        fund_list = load_fund_list()

        # 如果基金列表为空，则爬取基金列表
        if not fund_list:
            logger.info("基金列表为空，开始爬取基金列表...")
            fund_list = crawler_manager.crawl_all_fund_lists()
            save_fund_list(fund_list)

        # 限制分析的基金数量，避免工作量过大
        max_funds = 50  # 最多分析50只基金
        fund_codes = [fund['code'] for fund in fund_list[:max_funds]]

        # 爬取基金详情
        logger.info("开始爬取基金详情...")
        fund_details = crawler_manager.crawl_fund_details(fund_codes)

        # 爬取基金新闻
        logger.info("开始爬取基金新闻...")
        fund_news = crawler_manager.crawl_all_fund_news(limit_per_site=20)

        # 爬取基金排名
        logger.info("开始爬取基金排名...")
        fund_ranks = crawler_manager.crawl_fund_ranks(limit_per_site=20)

        # 分析基金
        logger.info("开始分析基金...")
        analysis_results = analyze_funds(fund_codes, analyzer)

        # 生成报告
        logger.info("开始生成报告...")
        report = report_generator.generate_report(
            analysis_results=list(analysis_results.values()),
            news_data=fund_news,
            rank_data=fund_ranks
        )

        # 保存报告到GitHub
        logger.info("保存报告到GitHub...")
        save_report_to_github(report)

        logger.info("基金分析系统运行完成")

    except Exception as e:
        logger.error(f"系统运行出错: {str(e)}")
        import traceback
        traceback.print_exc()

def save_report_to_github(report):
    """保存报告到GitHub"""
    try:
        # 获取GitHub token
        github_token = os.getenv("REPO_ACCESS_TOKEN")
        if not github_token:
            logger.warning("未找到GitHub token，跳过保存到GitHub")
            return

        # 导入GitHub库
        from github import Github

        # 初始化GitHub客户端
        g = Github(github_token)

        # 获取仓库
        repo_owner = os.getenv("GITHUB_REPOSITORY_OWNER", "your_username")
        repo_name = os.getenv("GITHUB_REPOSITORY_NAME", "fund_analysis")
        repo = g.get_repo(f"{repo_owner}/{repo_name}")

        # 生成报告文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"reports/fund_analysis_report_{timestamp}.md"

        # 创建报告内容
        report_content = report['markdown']

        # 提交报告到GitHub
        try:
            # 尝试获取文件，如果不存在则创建新文件
            file = repo.get_contents(report_filename)
            # 文件存在，更新文件
            repo.update_file(
                path=report_filename,
                message=f"更新基金分析报告 {timestamp}",
                content=report_content,
                sha=file.sha
            )
        except:
            # 文件不存在，创建新文件
            repo.create_file(
                path=report_filename,
                message=f"创建基金分析报告 {timestamp}",
                content=report_content
            )

        logger.info(f"报告已成功保存到GitHub: {report_filename}")

    except ImportError:
        logger.warning("未安装PyGithub库，无法保存报告到GitHub")
    except Exception as e:
        logger.error(f"保存报告到GitHub出错: {str(e)}")

if __name__ == "__main__":
    main()
