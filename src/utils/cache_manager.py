"""缓存管理器"""

import json
import pickle
import os
import time
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
from pathlib import Path
import hashlib

from .logger import log_info, log_warning, log_error, log_debug

class CacheManager:
    """缓存管理器"""

    def __init__(self, cache_dir: str = "cache", max_cache_size_mb: int = 500):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_cache_size = max_cache_size_mb * 1024 * 1024  # 转换为字节

        # 缓存元数据文件
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.metadata = self._load_metadata()

        # 启动时清理过期缓存
        self._cleanup_expired_cache()

    def _load_metadata(self) -> Dict:
        """加载缓存元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                log_warning(f"加载缓存元数据失败: {e}")

        return {}

    def _save_metadata(self):
        """保存缓存元数据"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log_error(f"保存缓存元数据失败: {e}")

    def _get_cache_file_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        # 使用MD5哈希来处理长键名和特殊字符
        key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def _cleanup_expired_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []

        for key, meta in self.metadata.items():
            if current_time > meta.get('expire_time', 0):
                expired_keys.append(key)

        for key in expired_keys:
            self._delete_cache_file(key)

        if expired_keys:
            log_info(f"清理了 {len(expired_keys)} 个过期缓存项")

    def _delete_cache_file(self, key: str):
        """删除缓存文件"""
        try:
            cache_file = self._get_cache_file_path(key)
            if cache_file.exists():
                cache_file.unlink()

            if key in self.metadata:
                del self.metadata[key]
                self._save_metadata()

        except Exception as e:
            log_error(f"删除缓存文件失败: {e}")

    def _check_cache_size(self):
        """检查缓存大小并清理"""
        total_size = 0
        file_sizes = []

        for key, meta in self.metadata.items():
            cache_file = self._get_cache_file_path(key)
            if cache_file.exists():
                size = cache_file.stat().st_size
                total_size += size
                file_sizes.append((key, size, meta.get('access_time', 0)))

        if total_size > self.max_cache_size:
            # 按访问时间排序，删除最旧的文件
            file_sizes.sort(key=lambda x: x[2])

            deleted_count = 0
            for key, size, _ in file_sizes:
                if total_size <= self.max_cache_size * 0.8:  # 清理到80%
                    break

                self._delete_cache_file(key)
                total_size -= size
                deleted_count += 1

            if deleted_count > 0:
                log_info(f"缓存大小超限，清理了 {deleted_count} 个文件")

    def set(self, key: str, value: Any, expire_hours: int = 24) -> bool:
        """设置缓存"""
        try:
            cache_file = self._get_cache_file_path(key)

            # 序列化数据
            if isinstance(value, (dict, list, str, int, float, bool)):
                # JSON序列化
                data = {'type': 'json', 'value': value}
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, default=str)
            else:
                # Pickle序列化
                data = {'type': 'pickle', 'value': value}
                with open(cache_file, 'wb') as f:
                    pickle.dump(data, f)

            # 更新元数据
            current_time = time.time()
            expire_time = current_time + (expire_hours * 3600)

            self.metadata[key] = {
                'create_time': current_time,
                'access_time': current_time,
                'expire_time': expire_time,
                'expire_hours': expire_hours
            }

            self._save_metadata()
            self._check_cache_size()

            log_debug(f"缓存已设置: {key} (过期时间: {expire_hours}小时)")
            return True

        except Exception as e:
            log_error(f"设置缓存失败: {e}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        try:
            # 检查是否存在且未过期
            if key not in self.metadata:
                return None

            meta = self.metadata[key]
            current_time = time.time()

            if current_time > meta.get('expire_time', 0):
                # 过期了，删除
                self._delete_cache_file(key)
                return None

            cache_file = self._get_cache_file_path(key)
            if not cache_file.exists():
                # 文件不存在，清理元数据
                del self.metadata[key]
                self._save_metadata()
                return None

            # 读取数据
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('type') == 'json':
                        value = data['value']
                    else:
                        # 尝试pickle读取
                        with open(cache_file, 'rb') as pf:
                            pickle_data = pickle.load(pf)
                            value = pickle_data['value']
            except (json.JSONDecodeError, UnicodeDecodeError):
                # 尝试pickle读取
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                    value = data['value']

            # 更新访问时间
            meta['access_time'] = current_time
            self._save_metadata()

            log_debug(f"缓存命中: {key}")
            return value

        except Exception as e:
            log_error(f"获取缓存失败: {e}")
            return None

    def delete(self, key: str) -> bool:
        """删除指定缓存"""
        try:
            self._delete_cache_file(key)
            log_debug(f"缓存已删除: {key}")
            return True
        except Exception as e:
            log_error(f"删除缓存失败: {e}")
            return False

    def clear(self) -> bool:
        """清空所有缓存"""
        try:
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()

            self.metadata.clear()
            self._save_metadata()

            log_info("所有缓存已清空")
            return True

        except Exception as e:
            log_error(f"清空缓存失败: {e}")
            return False

    def get_cache_info(self) -> Dict:
        """获取缓存信息"""
        try:
            total_files = len(self.metadata)
            total_size = 0
            expired_count = 0
            current_time = time.time()

            for key, meta in self.metadata.items():
                cache_file = self._get_cache_file_path(key)
                if cache_file.exists():
                    total_size += cache_file.stat().st_size

                if current_time > meta.get('expire_time', 0):
                    expired_count += 1

            return {
                'total_files': total_files,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'max_size_mb': round(self.max_cache_size / (1024 * 1024), 2),
                'usage_percent': round((total_size / self.max_cache_size) * 100, 2),
                'expired_count': expired_count,
                'cache_dir': str(self.cache_dir)
            }

        except Exception as e:
            log_error(f"获取缓存信息失败: {e}")
            return {}

    def cleanup(self):
        """手动清理缓存"""
        self._cleanup_expired_cache()
        self._check_cache_size()

# 全局缓存管理器实例
cache_manager = CacheManager()
