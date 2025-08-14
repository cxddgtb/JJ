"""
日志工具模块
"""
import logging
import logging.handlers
import os
from datetime import datetime
import sys
from pathlib import Path

class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""

    COLORS = {
        'DEBUG': '[36m',     # 青色
        'INFO': '[32m',      # 绿色
        'WARNING': '[33m',   # 黄色
        'ERROR': '[31m',     # 红色
        'CRITICAL': '[35m',  # 紫色
    }
    RESET = '[0m'

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)

class Logger:
    """统一日志管理器"""

    def __init__(self, name='FundAnalysis', log_dir='logs'):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # 创建logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # 避免重复添加handler
        if not self.logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self):
        """设置日志处理器"""

        # 文件处理器 - 详细日志
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / f"{self.name.lower()}.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        # 错误文件处理器
        error_handler = logging.handlers.RotatingFileHandler(
            self.log_dir / f"{self.name.lower()}_error.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)

        # 控制台处理器 - 彩色输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)

        # 添加处理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(console_handler)

    def debug(self, message, *args, **kwargs):
        """调试日志"""
        self.logger.debug(message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        """信息日志"""
        self.logger.info(message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        """警告日志"""
        self.logger.warning(message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        """错误日志"""
        self.logger.error(message, *args, **kwargs)

    def critical(self, message, *args, **kwargs):
        """严重错误日志"""
        self.logger.critical(message, *args, **kwargs)

    def exception(self, message, *args, **kwargs):
        """异常日志（包含堆栈信息）"""
        self.logger.exception(message, *args, **kwargs)

class TaskLogger:
    """任务日志记录器"""

    def __init__(self, task_name, base_logger=None):
        self.task_name = task_name
        self.base_logger = base_logger or Logger()
        self.start_time = None
        self.end_time = None

    def start(self, message=""):
        """开始任务"""
        self.start_time = datetime.now()
        msg = f"[{self.task_name}] 开始执行"
        if message:
            msg += f" - {message}"
        self.base_logger.info(msg)

    def progress(self, current, total, message=""):
        """记录进度"""
        percentage = (current / total) * 100 if total > 0 else 0
        msg = f"[{self.task_name}] 进度: {current}/{total} ({percentage:.1f}%)"
        if message:
            msg += f" - {message}"
        self.base_logger.info(msg)

    def success(self, message=""):
        """任务成功"""
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds() if self.start_time else 0
        msg = f"[{self.task_name}] 执行成功 (耗时: {duration:.2f}秒)"
        if message:
            msg += f" - {message}"
        self.base_logger.info(msg)

    def error(self, error, message=""):
        """任务错误"""
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds() if self.start_time else 0
        msg = f"[{self.task_name}] 执行失败 (耗时: {duration:.2f}秒)"
        if message:
            msg += f" - {message}"
        msg += f" - 错误: {str(error)}"
        self.base_logger.error(msg)

    def warning(self, message):
        """任务警告"""
        msg = f"[{self.task_name}] 警告: {message}"
        self.base_logger.warning(msg)

class CrawlerLogger:
    """爬虫专用日志记录器"""

    def __init__(self, base_logger=None):
        self.base_logger = base_logger or Logger()
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0

    def request_start(self, url, method="GET"):
        """记录请求开始"""
        self.request_count += 1
        self.base_logger.debug(f"请求开始 [{self.request_count}] {method} {url}")

    def request_success(self, url, status_code, response_time):
        """记录请求成功"""
        self.success_count += 1
        self.base_logger.debug(f"请求成功 {status_code} {url} (耗时: {response_time:.3f}s)")

    def request_error(self, url, error, retry_count=0):
        """记录请求错误"""
        self.error_count += 1
        retry_info = f" (重试: {retry_count})" if retry_count > 0 else ""
        self.base_logger.error(f"请求失败 {url}{retry_info} - {str(error)}")

    def rate_limit(self, url, delay):
        """记录限速"""
        self.base_logger.warning(f"触发限速 {url} - 延迟 {delay}秒")

    def summary(self):
        """输出统计摘要"""
        total = self.request_count
        success_rate = (self.success_count / total * 100) if total > 0 else 0
        self.base_logger.info(
            f"爬取统计 - 总请求: {total}, 成功: {self.success_count}, "
            f"失败: {self.error_count}, 成功率: {success_rate:.1f}%"
        )

class PerformanceLogger:
    """性能监控日志"""

    def __init__(self, base_logger=None):
        self.base_logger = base_logger or Logger()

    def memory_usage(self, process_name, memory_mb):
        """记录内存使用"""
        self.base_logger.debug(f"内存使用 [{process_name}]: {memory_mb:.1f}MB")

    def cpu_usage(self, process_name, cpu_percent):
        """记录CPU使用"""
        self.base_logger.debug(f"CPU使用 [{process_name}]: {cpu_percent:.1f}%")

    def disk_usage(self, path, usage_percent):
        """记录磁盘使用"""
        self.base_logger.debug(f"磁盘使用 [{path}]: {usage_percent:.1f}%")

    def network_traffic(self, bytes_sent, bytes_recv):
        """记录网络流量"""
        sent_mb = bytes_sent / 1024 / 1024
        recv_mb = bytes_recv / 1024 / 1024
        self.base_logger.debug(f"网络流量 - 发送: {sent_mb:.1f}MB, 接收: {recv_mb:.1f}MB")

# 创建默认日志实例
default_logger = Logger()
crawler_logger = CrawlerLogger(default_logger)
performance_logger = PerformanceLogger(default_logger)

# 便捷函数
def log_debug(message, *args, **kwargs):
    default_logger.debug(message, *args, **kwargs)

def log_info(message, *args, **kwargs):
    default_logger.info(message, *args, **kwargs)

def log_warning(message, *args, **kwargs):
    default_logger.warning(message, *args, **kwargs)

def log_error(message, *args, **kwargs):
    default_logger.error(message, *args, **kwargs)

def log_critical(message, *args, **kwargs):
    default_logger.critical(message, *args, **kwargs)

def log_exception(message, *args, **kwargs):
    default_logger.exception(message, *args, **kwargs)

def create_task_logger(task_name):
    """创建任务日志记录器"""
    return TaskLogger(task_name, default_logger)

if __name__ == "__main__":
    # 测试日志功能
    logger = Logger("测试")

    logger.debug("这是调试信息")
    logger.info("这是普通信息")
    logger.warning("这是警告信息")
    logger.error("这是错误信息")
    logger.critical("这是严重错误")

    # 测试任务日志
    task_logger = TaskLogger("测试任务", logger)
    task_logger.start("开始执行测试")
    task_logger.progress(50, 100, "处理中...")
    task_logger.success("测试完成")
