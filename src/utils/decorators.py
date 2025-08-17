import functools
import logging
from typing import Callable, Any, Dict, Optional

from telegram import Update
from telegram.ext import ContextTypes

from src.managers.session_manager import session_manager

logger = logging.getLogger(__name__)

def require_user_session(func: Callable) -> Callable:
    """
    装饰器：确保用户有有效会话
    """
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            # 获取用户信息
            telegram_user = update.effective_user
            if not telegram_user:
                if update.message:
                    await update.message.reply_text("❌ 无法获取用户信息")
                elif update.callback_query:
                    await update.callback_query.answer("❌ 无法获取用户信息", show_alert=True)
                else:
                    logger.warning("无法向用户发送消息：既没有 message 也没有 callback_query")
                return
            
            # 获取或创建会话
            session = session_manager.get_or_create_session({
                'id': telegram_user.id,
                'username': telegram_user.username,
                'first_name': telegram_user.first_name,
                'last_name': telegram_user.last_name
            })
            
            # 将会话添加到上下文
            if context.user_data is None:
                context.user_data = {}  # type: ignore[assignment]
            context.user_data['session'] = session
            
            # 调用原函数
            return await func(update, context, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"会话处理错误: {e}")
            if update.message:
                await update.message.reply_text("❌ 处理请求时出错")
            elif update.callback_query:
                await update.callback_query.answer("❌ 处理请求时出错", show_alert=True)
            else:
                logger.exception("无法发送错误消息：既没有 message 也没有 callback_query")
    
    return wrapper

def require_admin(func: Callable) -> Callable:
    """
    装饰器：确保用户是管理员
    """
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            # 获取用户信息
            telegram_user = update.effective_user
            if not telegram_user:
                if update.message:
                    await update.message.reply_text("❌ 无法获取用户信息")
                elif update.callback_query:
                    await update.callback_query.answer("❌ 无法获取用户信息", show_alert=True)
                else:
                    logger.warning("无法向用户发送消息：既没有 message 也没有 callback_query")
                return
            
            # 检查管理员权限
            if not session_manager.is_user_admin(telegram_user.id):
                if update.message:
                    await update.message.reply_text("❌ 您没有权限执行此操作")
                elif update.callback_query:
                    await update.callback_query.answer("❌ 您没有权限执行此操作", show_alert=True)
                else:
                    logger.warning("权限拒绝，但无法通知用户：既没有 message 也没有 callback_query")
                return
            
            # 获取或创建会话
            session = session_manager.get_or_create_session({
                'id': telegram_user.id,
                'username': telegram_user.username,
                'first_name': telegram_user.first_name,
                'last_name': telegram_user.last_name
            })
            
            # 将会话添加到上下文
            if context.user_data is None:
                context.user_data = {}  # type: ignore[assignment]
            context.user_data['session'] = session
            
            # 调用原函数
            return await func(update, context, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"权限检查错误: {e}")
            if update.message:
                await update.message.reply_text("❌ 处理请求时出错")
            elif update.callback_query:
                await update.callback_query.answer("❌ 处理请求时出错", show_alert=True)
            else:
                logger.exception("无法发送错误消息：既没有 message 也没有 callback_query")
    
    return wrapper

def require_configured_user(func: Callable) -> Callable:
    """
    装饰器：确保用户已配置Y2A-Auto服务
    """
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            # 获取用户信息
            telegram_user = update.effective_user
            if not telegram_user:
                if update.message:
                    await update.message.reply_text("❌ 无法获取用户信息")
                elif update.callback_query:
                    await update.callback_query.answer("❌ 无法获取用户信息", show_alert=True)
                else:
                    logger.warning("无法向用户发送消息：既没有 message 也没有 callback_query")
                return
            
            # 获取或创建会话
            session = session_manager.get_or_create_session({
                'id': telegram_user.id,
                'username': telegram_user.username,
                'first_name': telegram_user.first_name,
                'last_name': telegram_user.last_name
            })
            
            # 将会话添加到上下文
            if context.user_data is None:
                context.user_data = {}  # type: ignore[assignment]
            context.user_data['session'] = session
            
            # 检查用户是否已配置
            from src.managers.user_manager import UserManager
            if not UserManager.is_user_configured(telegram_user.id):
                if update.message:
                    await update.message.reply_text(
                        "您尚未配置Y2A-Auto服务，请使用 /settings 命令进行配置"
                    )
                elif update.callback_query:
                    await update.callback_query.answer(
                        "您尚未配置Y2A-Auto服务，请使用 /settings 命令进行配置", show_alert=True
                    )
                else:
                    logger.info("用户未配置，但无法通知：既没有 message 也没有 callback_query")
                return
            
            # 调用原函数
            return await func(update, context, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"配置检查错误: {e}")
            if update.message:
                await update.message.reply_text("❌ 处理请求时出错")
            elif update.callback_query:
                await update.callback_query.answer("❌ 处理请求时出错", show_alert=True)
            else:
                logger.exception("无法发送错误消息：既没有 message 也没有 callback_query")
    
    return wrapper

def log_user_activity(action: str):
    """
    装饰器：记录用户活动
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            try:
                # 获取用户信息
                telegram_user = update.effective_user
                if telegram_user:
                    logger.info(f"用户 {telegram_user.id} 执行操作: {action}")
                
                # 调用原函数
                return await func(update, context, *args, **kwargs)
                
            except Exception as e:
                logger.error(f"记录用户活动错误: {e}")
                raise
        
        return wrapper
    return decorator

def handle_errors(func: Callable) -> Callable:
    """
    装饰器：统一错误处理
    """
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            logger.error(f"处理命令时出错: {e}")
            
            # 尝试向用户发送错误消息
            try:
                if update.message:
                    await update.message.reply_text("❌ 处理请求时出错，请稍后重试")
                elif update.callback_query:
                    await update.callback_query.answer("❌ 处理请求时出错", show_alert=True)
            except Exception as inner_e:
                logger.error(f"发送错误消息失败: {inner_e}")
    
    return wrapper