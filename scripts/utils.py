# scripts/utils.py
import os
import json
import logging
from datetime import datetime, timedelta

# 修复导入方式
try:
    from config.settings import settings
except ImportError:
    # 备用方案：直接定义必要设置
    class FallbackSettings:
        OUTPUT_DIR = "output"
    settings = FallbackSettings()

def setup_logging():
    """配置日志系统"""
    log_dir = os.path.join(settings.OUTPUT_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(
        log_dir, 
        f"trading_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# 其余函数保持不变...
