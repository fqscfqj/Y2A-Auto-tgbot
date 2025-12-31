"""
内存监控工具
用于监控内存使用情况，防止低端服务器宕机
"""
import psutil
import logging
import threading
import time
import gc
from typing import Optional, Callable

logger = logging.getLogger(__name__)

class MemoryMonitor:
    """内存监控器"""
    
    def __init__(self, warning_threshold: float = 80.0, critical_threshold: float = 90.0):
        self.warning_threshold = warning_threshold  # 警告阈值 (%)
        self.critical_threshold = critical_threshold  # 危险阈值 (%)
        self.warning_callback: Optional[Callable] = None
        self.critical_callback: Optional[Callable] = None
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        
    def set_warning_callback(self, callback: Callable) -> None:
        """设置警告回调函数"""
        self.warning_callback = callback
        
    def set_critical_callback(self, callback: Callable) -> None:
        """设置危险回调函数"""
        self.critical_callback = callback
    
    def get_memory_usage(self) -> dict:
        """获取内存使用情况"""
        memory = psutil.virtual_memory()
        return {
            'total': memory.total,
            'available': memory.available,
            'used': memory.used,
            'percentage': memory.percent
        }
    
    def check_memory(self) -> None:
        """检查内存使用情况"""
        memory_info = self.get_memory_usage()
        usage_percent = memory_info['percentage']
        
        if usage_percent >= self.critical_threshold:
            logger.critical(f"内存使用率达到危险水平: {usage_percent:.1f}%")
            if self.critical_callback:
                self.critical_callback(memory_info)
        elif usage_percent >= self.warning_threshold:
            logger.warning(f"内存使用率较高: {usage_percent:.1f}%")
            if self.warning_callback:
                self.warning_callback(memory_info)
    
    def start_monitoring(self, interval: int = 30) -> None:
        """开始监控"""
        if self._monitoring:
            return
            
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, 
            args=(interval,),
            daemon=True
        )
        self._monitor_thread.start()
        logger.info(f"内存监控已启动，检查间隔: {interval}秒")
    
    def stop_monitoring(self) -> None:
        """停止监控"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("内存监控已停止")
    
    def _monitor_loop(self, interval: int) -> None:
        """监控循环"""
        while self._monitoring:
            try:
                self.check_memory()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"内存监控异常: {e}")
                time.sleep(interval)

# 全局内存监控实例
memory_monitor = MemoryMonitor()

def init_memory_monitor() -> None:
    """初始化内存监控"""
    def on_warning(memory_info):
        logger.warning(f"内存警告: 使用率 {memory_info['percentage']:.1f}%, "
                      f"已用 {memory_info['used'] / 1024**2:.0f}MB, "
                      f"可用 {memory_info['available'] / 1024**2:.0f}MB")
        # 在警告级别进行轻量级清理
        # Local import to avoid circular imports at module load time
        from src.utils.resource_manager import resource_manager
        cleaned = resource_manager.cleanup_inactive_users()
        if cleaned > 0:
            logger.info(f"清理了 {cleaned} 个非活跃用户的资源记录")
    
    def on_critical(memory_info):
        logger.critical(f"内存危险: 使用率 {memory_info['percentage']:.1f}%, "
                       f"已用 {memory_info['used'] / 1024**2:.0f}MB, "
                       f"可用 {memory_info['available'] / 1024**2:.0f}MB")
        # 在危险级别进行紧急清理
        # Local import to avoid circular imports at module load time
        from src.utils.resource_manager import resource_manager
        cleaned = resource_manager.cleanup_inactive_users()
        if cleaned > 0:
            logger.info(f"紧急清理了 {cleaned} 个非活跃用户的资源记录")
        # 触发Python垃圾回收
        gc.collect()
        logger.info("已触发垃圾回收")
    
    memory_monitor.set_warning_callback(on_warning)
    memory_monitor.set_critical_callback(on_critical)
    memory_monitor.start_monitoring()

def get_memory_status() -> str:
    """获取内存状态字符串"""
    memory_info = memory_monitor.get_memory_usage()
    return (f"内存使用率: {memory_info['percentage']:.1f}%, "
            f"已用: {memory_info['used'] / 1024**2:.0f}MB, "
            f"可用: {memory_info['available'] / 1024**2:.0f}MB")