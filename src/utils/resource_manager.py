"""
资源管理器
用于管理和限制资源使用，防止低端服务器宕机
"""
import logging
import threading
import time
from typing import Optional, Dict, Any
from collections import defaultdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ResourceManager:
    """资源管理器，负责监控和限制资源使用"""
    
    def __init__(self):
        self._concurrent_operations = 0
        self._max_concurrent_operations = 50  # 最大并发操作数
        self._operation_lock = threading.Lock()
        self._user_operation_count = defaultdict(int)
        self._user_operation_lock = threading.Lock()
        self._max_user_operations = 5  # 每用户最大并发操作数
        
        # 操作统计
        self._total_operations = 0
        self._rejected_operations = 0
        self._error_operations = 0
    
    def cleanup_inactive_users(self) -> int:
        """清理没有活跃操作的用户记录，返回清理的用户数"""
        with self._user_operation_lock:
            initial_count = len(self._user_operation_count)
            # 只保留有活跃操作的用户
            self._user_operation_count = defaultdict(int, {
                uid: count for uid, count in self._user_operation_count.items() if count > 0
            })
            return initial_count - len(self._user_operation_count)
        
    def acquire_operation_slot(self, user_id: Optional[int] = None) -> bool:
        """获取操作槽位"""
        with self._operation_lock:
            # 检查全局并发限制
            if self._concurrent_operations >= self._max_concurrent_operations:
                self._rejected_operations += 1
                logger.warning(f"拒绝操作: 全局并发数达到限制 {self._max_concurrent_operations}")
                return False
            
            # 检查用户并发限制
            if user_id is not None:
                with self._user_operation_lock:
                    if self._user_operation_count[user_id] >= self._max_user_operations:
                        self._rejected_operations += 1
                        logger.warning(f"拒绝操作: 用户 {user_id} 并发数达到限制 {self._max_user_operations}")
                        return False
                    
                    self._user_operation_count[user_id] += 1
            
            self._concurrent_operations += 1
            self._total_operations += 1
            return True
    
    def release_operation_slot(self, user_id: Optional[int] = None, success: bool = True) -> None:
        """释放操作槽位"""
        with self._operation_lock:
            if self._concurrent_operations > 0:
                self._concurrent_operations -= 1
            
            if not success:
                self._error_operations += 1
            
            if user_id is not None:
                with self._user_operation_lock:
                    if self._user_operation_count[user_id] > 0:
                        self._user_operation_count[user_id] -= 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取资源使用统计"""
        return {
            'concurrent_operations': self._concurrent_operations,
            'max_concurrent_operations': self._max_concurrent_operations,
            'total_operations': self._total_operations,
            'rejected_operations': self._rejected_operations,
            'error_operations': self._error_operations,
            'active_users': sum(1 for count in self._user_operation_count.values() if count > 0)
        }
    
    def is_overloaded(self) -> bool:
        """检查是否过载"""
        usage_ratio = self._concurrent_operations / self._max_concurrent_operations
        return usage_ratio > 0.8  # 80% 以上认为是高负载

# 全局资源管理器实例
resource_manager = ResourceManager()

class OperationContext:
    """操作上下文管理器，自动管理资源槽位"""
    
    def __init__(self, user_id: Optional[int] = None, operation_name: str = "unknown"):
        self.user_id = user_id
        self.operation_name = operation_name
        self.acquired = False
        self.success = True
    
    def __enter__(self):
        self.acquired = resource_manager.acquire_operation_slot(self.user_id)
        if not self.acquired:
            raise RuntimeError(f"无法获取资源槽位进行操作: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            self.success = exc_type is None
            resource_manager.release_operation_slot(self.user_id, self.success)
        
        if exc_type is not None:
            logger.error(f"操作 {self.operation_name} 执行失败: {exc_val}")

def get_resource_status() -> str:
    """获取资源状态字符串"""
    stats = resource_manager.get_stats()
    return (f"并发操作: {stats['concurrent_operations']}/{stats['max_concurrent_operations']}, "
            f"总操作数: {stats['total_operations']}, "
            f"拒绝数: {stats['rejected_operations']}, "
            f"错误数: {stats['error_operations']}, "
            f"活跃用户: {stats['active_users']}")