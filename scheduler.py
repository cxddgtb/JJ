# scheduler.py
import schedule
import time
from datetime import datetime
from main import main

def job():
    """定时任务"""
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 开始执行基金分析任务...")
    try:
        main()
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 基金分析任务完成")
    except Exception as e:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 任务执行失败: {str(e)}")

def run_scheduler():
    """运行定时任务调度器"""
    # 每个交易日下午2点运行（北京时间）
    schedule.every().day.at("14:00").do(job)
    
    # 立即运行一次
    job()
    
    print("定时任务已启动，每周一至周五下午2点自动运行...")
    print("按 Ctrl+C 退出")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次
