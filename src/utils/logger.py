import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional

from config import Config

class BotLogger:
    """机器人日志管理器"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BotLogger, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not BotLogger._initialized:
            self._setup_loggers()
            BotLogger._initialized = True
    
    def _setup_loggers(self):
        """设置所有日志记录器"""
        # 确保日志目录存在
        os.makedirs(Config.LOGS_DIR, exist_ok=True)
        
        # 设置根日志记录器
        self._setup_root_logger()
        
        # 设置特定模块的日志记录器
        self._setup_module_loggers()
    
    def _setup_root_logger(self):
        """设置根日志记录器"""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # 文件处理器（带轮转）
        file_handler = logging.handlers.RotatingFileHandler(
            Config.LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    def _setup_module_loggers(self):
        """设置特定模块的日志记录器"""
        # 用户操作日志
        self._setup_user_activity_logger()
        
        # 错误日志
        self._setup_error_logger()
        
        # API调用日志
        self._setup_api_logger()
    
    def _setup_user_activity_logger(self):
        """设置用户活动日志记录器"""
        logger = logging.getLogger('user_activity')
        logger.setLevel(logging.INFO)
        
        # 创建专用的用户活动日志文件
        user_activity_file = os.path.join(Config.LOGS_DIR, 'user_activity.log')
        handler = logging.handlers.RotatingFileHandler(
            user_activity_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        
        formatter = logging.Formatter(
            '%(asctime)s - USER:%(user_id)s - ACTION:%(action)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # 避免传播到根日志记录器
        logger.propagate = False
    
    def _setup_error_logger(self):
        """设置错误日志记录器"""
        logger = logging.getLogger('error')
        logger.setLevel(logging.ERROR)
        
        # 创建专用的错误日志文件
        error_file = os.path.join(Config.LOGS_DIR, 'error.log')
        handler = logging.handlers.RotatingFileHandler(
            error_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # 避免传播到根日志记录器
        logger.propagate = False
    
    def _setup_api_logger(self):
        """设置API调用日志记录器"""
        logger = logging.getLogger('api')
        logger.setLevel(logging.INFO)
        
        # 创建专用的API日志文件
        api_file = os.path.join(Config.LOGS_DIR, 'api.log')
        handler = logging.handlers.RotatingFileHandler(
            api_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        
        formatter = logging.Formatter(
            '%(asctime)s - METHOD:%(method)s - URL:%(url)s - STATUS:%(status)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # 避免传播到根日志记录器
        logger.propagate = False
    
    @staticmethod
    def log_user_activity(user_id: int, action: str, details: str = ""):
        """记录用户活动"""
        logger = logging.getLogger('user_activity')
        logger.info(
            details,
            extra={'user_id': user_id, 'action': action}
        )
    
    @staticmethod
    def log_error(error: Exception, context: str = ""):
        """记录错误"""
        logger = logging.getLogger('error')
        logger.error(
            f"{context}: {str(error)}",
            exc_info=True
        )
    
    @staticmethod
    def log_api_call(method: str, url: str, status_code: int, response_time: float, details: str = ""):
        """记录API调用"""
        logger = logging.getLogger('api')
        logger.info(
            f"Response time: {response_time:.2f}s - {details}",
            extra={'method': method, 'url': url, 'status': status_code}
        )
    
    @staticmethod
    def log_forward_attempt(user_id: int, youtube_url: str, success: bool, error_message: str = ""):
        """记录转发尝试"""
        logger = logging.getLogger('forward')
        logger.info(
            f"URL: {youtube_url} - Success: {success} - Error: {error_message}",
            extra={'user_id': user_id}
        )

# 全局日志管理器实例
bot_logger = BotLogger()

def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志记录器"""
    return logging.getLogger(name)