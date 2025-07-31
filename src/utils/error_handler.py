import logging
import traceback
from typing import Optional, Dict, Any

from telegram import Update
from telegram.ext import ContextTypes

from src.utils.logger import bot_logger

logger = logging.getLogger(__name__)

class BotError(Exception):
    """机器人基础异常类"""
    def __init__(self, message: str, user_message: str = None):
        self.message = message
        self.user_message = user_message or "操作失败，请稍后重试"
        super().__init__(self.message)

class UserNotConfiguredError(BotError):
    """用户未配置异常"""
    def __init__(self):
        super().__init__(
            "用户未配置Y2A-Auto服务",
            "您尚未配置Y2A-Auto服务，请使用 /settings 命令进行配置"
        )

class PermissionDeniedError(BotError):
    """权限被拒绝异常"""
    def __init__(self):
        super().__init__(
            "用户权限不足",
            "您没有权限执行此操作"
        )

class InvalidConfigurationError(BotError):
    """无效配置异常"""
    def __init__(self, detail: str):
        super().__init__(
            f"配置无效: {detail}",
            "配置无效，请检查您的设置"
        )

class APIError(BotError):
    """API调用异常"""
    def __init__(self, url: str, status_code: int, response: str):
        super().__init__(
            f"API调用失败: {url}, 状态码: {status_code}, 响应: {response}",
            "服务暂时不可用，请稍后重试"
        )

class DatabaseError(BotError):
    """数据库异常"""
    def __init__(self, operation: str):
        super().__init__(
            f"数据库操作失败: {operation}",
            "系统暂时不可用，请稍后重试"
        )

class ErrorHandler:
    """错误处理器"""
    
    @staticmethod
    async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE, error: Exception) -> None:
        """处理错误"""
        try:
            # 记录错误
            ErrorHandler._log_error(error, update, context)
            
            # 获取用户友好的错误消息
            user_message = ErrorHandler._get_user_message(error)
            
            # 发送错误消息给用户
            await ErrorHandler._send_error_message(update, user_message)
            
        except Exception as e:
            logger.error(f"处理错误时出错: {e}")
    
    @staticmethod
    def _log_error(error: Exception, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """记录错误日志"""
        # 获取用户信息
        user_id = None
        if update and update.effective_user:
            user_id = update.effective_user.id
        
        # 记录到错误日志
        bot_logger.log_error(error, f"User ID: {user_id}")
        
        # 记录详细错误信息
        error_type = type(error).__name__
        error_details = str(error)
        
        logger.error(
            f"Error type: {error_type}, User ID: {user_id}, Error: {error_details}",
            exc_info=True
        )
        
        # 如果是BotError，记录额外上下文
        if isinstance(error, BotError):
            logger.error(f"BotError message: {error.message}")
    
    @staticmethod
    def _get_user_message(error: Exception) -> str:
        """获取用户友好的错误消息"""
        if isinstance(error, BotError):
            return error.user_message
        
        # 默认错误消息
        return "操作失败，请稍后重试"
    
    @staticmethod
    async def _send_error_message(update: Update, message: str) -> None:
        """发送错误消息给用户"""
        try:
            if update.message:
                await update.message.reply_text(f"❌ {message}")
            elif update.callback_query:
                await update.callback_query.answer(f"❌ {message}", show_alert=True)
        except Exception as e:
            logger.error(f"发送错误消息失败: {e}")
    
    @staticmethod
    def handle_database_error(operation: str, error: Exception) -> None:
        """处理数据库错误"""
        bot_logger.log_error(error, f"Database operation: {operation}")
        logger.error(f"数据库操作失败: {operation}, 错误: {error}")
        raise DatabaseError(operation) from error
    
    @staticmethod
    def handle_api_error(url: str, status_code: int, response: str, error: Exception = None) -> None:
        """处理API错误"""
        error_msg = error or Exception(f"API调用失败: {url}")
        bot_logger.log_error(error_msg, f"API URL: {url}, Status: {status_code}")
        logger.error(f"API调用失败: {url}, 状态码: {status_code}, 响应: {response}")
        raise APIError(url, status_code, response) from error
    
    @staticmethod
    def handle_forward_error(user_id: int, youtube_url: str, error: Exception) -> None:
        """处理转发错误"""
        bot_logger.log_error(error, f"Forward attempt - User: {user_id}, URL: {youtube_url}")
        logger.error(f"转发失败 - 用户: {user_id}, URL: {youtube_url}, 错误: {error}")
        
        # 记录转发尝试
        bot_logger.log_forward_attempt(user_id, youtube_url, False, str(error))
    
    @staticmethod
    def log_user_activity(user_id: int, action: str, details: str = "") -> None:
        """记录用户活动"""
        bot_logger.log_user_activity(user_id, action, details)
    
    @staticmethod
    def log_api_call(method: str, url: str, status_code: int, response_time: float, details: str = "") -> None:
        """记录API调用"""
        bot_logger.log_api_call(method, url, status_code, response_time, details)

# 全局错误处理器实例
error_handler = ErrorHandler()

def handle_errors(func):
    """
    装饰器：自动处理函数中的错误
    """
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except BotError as e:
            await error_handler.handle_error(update, context, e)
        except Exception as e:
            await error_handler.handle_error(update, context, e)
    
    return wrapper