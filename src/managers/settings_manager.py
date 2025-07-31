import logging
from typing import Dict, Any, Optional, Tuple
from enum import Enum

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from src.managers.user_manager import UserManager
from src.database.models import User, UserConfig

logger = logging.getLogger(__name__)

# 设置菜单状态
class SettingsState(Enum):
    MAIN_MENU = 1
    SET_API_URL = 2
    SET_PASSWORD = 3
    VIEW_CONFIG = 4
    TEST_CONNECTION = 5
    DELETE_CONFIG = 6

class SettingsManager:
    """设置菜单管理器，负责处理用户设置相关的交互"""
    
    @staticmethod
    async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理/settings命令，显示设置菜单"""
        user = await UserManager.ensure_user_registered(update, context)
        
        settings_text = """
⚙️ 设置菜单

请使用以下命令进行设置：
• /view_config - 查看当前配置
• /set_api - 设置Y2A-Auto API地址
• /set_password - 设置Y2A-Auto密码
• /test_connection - 测试连接
• /delete_config - 删除配置
• /cancel - 取消设置

请输入您要执行的命令：
"""
        
        await update.message.reply_text(settings_text)
        
        return SettingsState.MAIN_MENU
    
    @staticmethod
    async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理设置菜单的回调查询"""
        query = update.callback_query
        await query.answer()
        
        user = await UserManager.ensure_user_registered(update, context)
        action = query.data
        
        if action == "view_config":
            return await SettingsManager._view_config(update, context, user)
        elif action == "set_api_url":
            return await SettingsManager._set_api_url_start(update, context)
        elif action == "set_password":
            return await SettingsManager._set_password_start(update, context)
        elif action == "test_connection":
            return await SettingsManager._test_connection(update, context, user)
        elif action == "delete_config":
            return await SettingsManager._delete_config_start(update, context)
        elif action == "back":
            await query.edit_message_text("设置已取消")
            return ConversationHandler.END
        
        return SettingsState.MAIN_MENU
    
    @staticmethod
    async def _view_config(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> int:
        """查看当前配置"""
        config = UserManager.get_user_config(user.id)
        
        if config:
            config_text = f"当前配置:\n\n"
            config_text += f"API地址: {config.y2a_api_url}\n"
            config_text += f"密码: {'已设置' if config.y2a_password else '未设置'}\n"
            config_text += f"配置时间: {config.created_at.strftime('%Y-%m-%d %H:%M:%S') if config.created_at else '未知'}\n"
            config_text += f"最后更新: {config.updated_at.strftime('%Y-%m-%d %H:%M:%S') if config.updated_at else '未知'}"
        else:
            config_text = "您尚未配置Y2A-Auto服务"
        
        config_text += "\n\n输入 /cancel 返回设置菜单。"
        
        await update.message.reply_text(config_text)
        
        return SettingsState.MAIN_MENU
    
    @staticmethod
    async def _set_api_url_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """开始设置API地址"""
        await update.message.reply_text(
            "请输入Y2A-Auto的API地址:\n\n"
            "例如: http://localhost:5000/tasks/add_via_extension\n\n"
            "输入 /cancel 取消设置"
        )
        
        return SettingsState.SET_API_URL
    
    @staticmethod
    async def _set_api_url_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """完成设置API地址"""
        user = await UserManager.ensure_user_registered(update, context)
        api_url = update.message.text.strip()
        
        if not api_url:
            await update.message.reply_text("API地址不能为空，请重新输入")
            return SettingsState.SET_API_URL
        
        # 验证API地址格式
        if not (api_url.startswith('http://') or api_url.startswith('https://')):
            await update.message.reply_text("API地址必须以http://或https://开头，请重新输入")
            return SettingsState.SET_API_URL
        
        # 获取现有配置
        config = UserManager.get_user_config(user.id)
        password = config.y2a_password if config else None
        
        # 保存配置
        success = UserManager.save_user_config(user.id, api_url, password)
        
        if success:
            await update.message.reply_text(f"✅ API地址已设置为: {api_url}")
        else:
            await update.message.reply_text("❌ 设置API地址失败，请稍后重试")
        
        return ConversationHandler.END
    
    @staticmethod
    async def _set_password_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """开始设置密码"""
        await update.message.reply_text(
            "请输入Y2A-Auto的密码（如果不需要密码请输入 /skip）:\n\n"
            "输入 /cancel 取消设置"
        )
        
        return SettingsState.SET_PASSWORD
    
    @staticmethod
    async def _set_password_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """完成设置密码"""
        user = await UserManager.ensure_user_registered(update, context)
        password = update.message.text.strip()
        
        # 获取现有配置
        config = UserManager.get_user_config(user.id)
        if not config:
            await update.message.reply_text("请先设置API地址")
            return ConversationHandler.END
        
        # 保存配置
        success = UserManager.save_user_config(user.id, config.y2a_api_url, password)
        
        if success:
            await update.message.reply_text("✅ 密码已设置")
        else:
            await update.message.reply_text("❌ 设置密码失败，请稍后重试")
        
        return ConversationHandler.END
    
    @staticmethod
    async def _test_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> int:
        """测试连接"""
        config = UserManager.get_user_config(user.id)
        
        if not config:
            await update.message.reply_text("❌ 您尚未配置Y2A-Auto服务")
            return SettingsState.MAIN_MENU
        
        # 这里应该实现实际的连接测试逻辑
        # 暂时只显示测试信息
        await update.message.reply_text(
            f"🔄 正在测试连接到: {config.y2a_api_url}\n\n"
            "连接测试功能将在后续版本中实现\n\n"
            "输入 /cancel 返回设置菜单。"
        )
        
        return SettingsState.MAIN_MENU
    
    @staticmethod
    async def _delete_config_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """开始删除配置"""
        await update.message.reply_text(
            "⚠️ 确定要删除Y2A-Auto配置吗？\n\n"
            "删除后您将无法使用转发功能，除非重新配置\n\n"
            "输入 /confirm_delete 确认删除，或输入 /cancel 取消"
        )
        
        return SettingsState.DELETE_CONFIG
    
    @staticmethod
    async def _delete_config_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """确认删除配置"""
        user = await UserManager.ensure_user_registered(update, context)
        
        success = UserManager.delete_user_config(user.id)
        
        if success:
            await update.message.reply_text("✅ 配置已删除")
        else:
            await update.message.reply_text("❌ 删除配置失败")
        
        return ConversationHandler.END
    
    @staticmethod
    async def view_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """查看配置命令"""
        user = await UserManager.ensure_user_registered(update, context)
        return await SettingsManager._view_config(update, context, user)
    
    @staticmethod
    async def set_api_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """设置API地址命令"""
        return await SettingsManager._set_api_url_start(update, context)
    
    @staticmethod
    async def set_password_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """设置密码命令"""
        return await SettingsManager._set_password_start(update, context)
    
    @staticmethod
    async def test_connection_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """测试连接命令"""
        user = await UserManager.ensure_user_registered(update, context)
        return await SettingsManager._test_connection(update, context, user)
    
    @staticmethod
    async def delete_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """删除配置命令"""
        return await SettingsManager._delete_config_start(update, context)
    
    @staticmethod
    async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """取消设置"""
        await update.message.reply_text("设置已取消")
        return ConversationHandler.END
    
    @staticmethod
    async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """跳过密码设置"""
        # 获取用户和现有配置
        user = await UserManager.ensure_user_registered(update, context)
        config = UserManager.get_user_config(user.id)
        
        if not config:
            await update.message.reply_text("请先设置API地址")
            return ConversationHandler.END
        
        # 保存配置（不设置密码）
        success = UserManager.save_user_config(user.id, config.y2a_api_url, None)
        
        if success:
            await update.message.reply_text("✅ 已跳过密码设置")
        else:
            await update.message.reply_text("❌ 保存配置失败，请稍后重试")
        
        return ConversationHandler.END
    
    @staticmethod
    def get_conversation_handler() -> ConversationHandler:
        """获取设置菜单的对话处理器"""
        return ConversationHandler(
            entry_points=[CommandHandler("settings", SettingsManager.settings_command)],
            states={
                SettingsState.MAIN_MENU: [
                    CommandHandler("view_config", SettingsManager.view_config_command),
                    CommandHandler("set_api", SettingsManager.set_api_command),
                    CommandHandler("set_password", SettingsManager.set_password_command),
                    CommandHandler("test_connection", SettingsManager.test_connection_command),
                    CommandHandler("delete_config", SettingsManager.delete_config_command),
                    CommandHandler("cancel", SettingsManager.cancel_command)
                ],
                SettingsState.SET_API_URL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, SettingsManager._set_api_url_end),
                    CommandHandler("cancel", SettingsManager.cancel_command)
                ],
                SettingsState.SET_PASSWORD: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, SettingsManager._set_password_end),
                    CommandHandler("skip", SettingsManager.skip_command),
                    CommandHandler("cancel", SettingsManager.cancel_command)
                ],
                SettingsState.DELETE_CONFIG: [
                    CommandHandler("confirm_delete", SettingsManager._delete_config_confirm),
                    CommandHandler("cancel", SettingsManager.cancel_command)
                ]
            },
            fallbacks=[CommandHandler("cancel", SettingsManager.cancel_command)],
            per_message=False
        )