import logging
import html
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
    def _settings_main_markup() -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton("👀 查看配置", callback_data="view_config"),
                InlineKeyboardButton("⚙️ 设置API", callback_data="set_api_url"),
            ],
            [
                InlineKeyboardButton("🔐 设置密码", callback_data="set_password"),
                InlineKeyboardButton("🔌 测试连接", callback_data="test_connection"),
            ],
            [
                InlineKeyboardButton("🗑️ 删除配置", callback_data="delete_config"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def _back_markup() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 返回", callback_data="back")]])

    @staticmethod
    def _view_config_markup() -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton("⚙️ 修改 API", callback_data="set_api_url"),
                InlineKeyboardButton("🔐 修改密码", callback_data="set_password"),
            ],
            [
                InlineKeyboardButton("🔌 测试连接", callback_data="test_connection"),
            ],
            [
                InlineKeyboardButton("⬅️ 返回", callback_data="back"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def _test_result_markup() -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("⚙️ 修改 API", callback_data="set_api_url")],
            [InlineKeyboardButton("⬅️ 返回", callback_data="back")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def _post_set_api_markup() -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("🔌 测试连接", callback_data="test_connection")],
            [InlineKeyboardButton("⬅️ 返回", callback_data="back")],
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def _test_success_markup() -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("🎯 发送示例", callback_data="main:send_example")],
            [InlineKeyboardButton("⬅️ 返回", callback_data="back")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理/settings命令，显示设置菜单"""
        user = await UserManager.ensure_user_registered(update, context)
        
        settings_text = """
<b>⚙️ 设置菜单</b>
请选择需要执行的操作：
"""

        message = update.effective_message
        await message.reply_text(settings_text, reply_markup=SettingsManager._settings_main_markup())

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
        elif action == "confirm_delete":
            return await SettingsManager._delete_config_confirm(update, context)
        elif action == "back":
            # 返回到主菜单
            await query.edit_message_text("<b>⚙️ 设置菜单</b>\n请选择需要执行的操作：", reply_markup=SettingsManager._settings_main_markup())
            return SettingsState.MAIN_MENU
        
        return SettingsState.MAIN_MENU
    
    @staticmethod
    async def _view_config(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> int:
        """查看当前配置"""
        config = UserManager.get_user_config(user.id)
        
        if config:
            config_text = "<b>当前配置</b>\n\n"
            config_text += f"API地址: <code>{html.escape(config.y2a_api_url)}</code>\n"
            config_text += f"密码: {'已设置' if config.y2a_password else '未设置'}\n"
            config_text += f"配置时间: {config.created_at.strftime('%Y-%m-%d %H:%M:%S') if config.created_at else '未知'}\n"
            config_text += f"最后更新: {config.updated_at.strftime('%Y-%m-%d %H:%M:%S') if config.updated_at else '未知'}"
        else:
            config_text = "<b>当前配置</b>\n\n您尚未配置Y2A-Auto服务。"

        markup = SettingsManager._view_config_markup()
        if update.callback_query:
            await update.callback_query.edit_message_text(config_text, reply_markup=markup)
        else:
            await update.effective_message.reply_text(config_text, reply_markup=markup)

        return SettingsState.MAIN_MENU
    
    @staticmethod
    async def _set_api_url_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """开始设置API地址"""
        text = (
            "<b>设置 API 地址</b>\n\n"
            "请直接发送新的 API 地址（支持只写主机:端口，将自动补全）。\n\n"
            "示例: <code>https://y2a.example.com:4443</code> 或 <code>http://localhost:5000</code>"
        )
        # 标记当前需要用户发送的输入类型，避免普通消息处理器误判
        context.user_data['pending_input'] = 'set_api'
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=SettingsManager._back_markup())
        else:
            await update.effective_message.reply_text(text, reply_markup=SettingsManager._back_markup())
        
        return SettingsState.SET_API_URL
    
    @staticmethod
    async def _set_api_url_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """完成设置API地址"""
        user = await UserManager.ensure_user_registered(update, context)
        api_url = update.message.text.strip()
        
        # 清除 pending 标记
        context.user_data.pop('pending_input', None)

        if not api_url:
            await update.message.reply_text("API地址不能为空，请重新输入", reply_markup=SettingsManager._back_markup())
            return SettingsState.SET_API_URL
        
        # 允许用户只输入域名:端口，或完整URL；统一规范化
        from src.managers.forward_manager import ForwardManager
        # 若缺少协议，默认补 https://
        if not (api_url.startswith('http://') or api_url.startswith('https://')):
            api_url = 'https://' + api_url
        api_url = ForwardManager.normalize_api_url(api_url)
        
        # 获取现有配置
        config = UserManager.get_user_config(user.id)
        password = config.y2a_password if config else None
        
        # 保存配置
        success = UserManager.save_user_config(user.id, api_url, password)
        
        if success:
            await update.message.reply_text(
                f"✅ API地址已设置为: <code>{html.escape(api_url)}</code>\n\n是否现在进行连接测试？",
                reply_markup=SettingsManager._post_set_api_markup()
            )
        else:
            await update.message.reply_text("❌ 设置API地址失败，请稍后重试", reply_markup=SettingsManager._settings_main_markup())
        
        return SettingsState.MAIN_MENU
    
    @staticmethod
    async def _set_password_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """开始设置密码"""
        text = (
            "<b>设置密码（可选）</b>\n"
            "请直接发送密码；如无需密码，可点击下方“跳过”。"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭️ 跳过", callback_data="skip")],
            [InlineKeyboardButton("⬅️ 返回", callback_data="back")],
        ])
        context.user_data['pending_input'] = 'set_password'
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=markup)
        else:
            await update.effective_message.reply_text(text, reply_markup=markup)
        
        return SettingsState.SET_PASSWORD
    
    @staticmethod
    async def _set_password_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """完成设置密码"""
        user = await UserManager.ensure_user_registered(update, context)
        password = update.message.text.strip()
        
        context.user_data.pop('pending_input', None)

        # 获取现有配置
        config = UserManager.get_user_config(user.id)
        if not config:
            await update.message.reply_text("请先设置API地址", reply_markup=SettingsManager._settings_main_markup())
            return SettingsState.MAIN_MENU
        
        # 保存配置
        success = UserManager.save_user_config(user.id, config.y2a_api_url, password)
        
        if success:
            await update.message.reply_text(
                "✅ 密码已设置\n\n是否现在进行连接测试？",
                reply_markup=SettingsManager._post_set_api_markup()
            )
        else:
            await update.message.reply_text("❌ 设置密码失败，请稍后重试", reply_markup=SettingsManager._settings_main_markup())
        
        return SettingsState.MAIN_MENU
    
    @staticmethod
    async def _test_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> int:
        """测试连接"""
        config = UserManager.get_user_config(user.id)
        
        if not config:
            text = "❌ 您尚未配置Y2A-Auto服务"
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=SettingsManager._settings_main_markup())
            else:
                await update.effective_message.reply_text(text, reply_markup=SettingsManager._settings_main_markup())
            return SettingsState.MAIN_MENU

        # 实际连接测试
        from src.managers.forward_manager import ForwardManager
        result = await ForwardManager.test_connection(update, context, user, config)
        text = f"<b>🔌 连接测试结果</b>\n\n{result}"
        markup = (
            SettingsManager._test_success_markup() if str(result).startswith("✅")
            else SettingsManager._test_result_markup()
        )
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=markup)
        else:
            await update.effective_message.reply_text(text, reply_markup=markup)

        return SettingsState.MAIN_MENU
    
    @staticmethod
    async def _delete_config_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """开始删除配置"""
        text = (
            "<b>⚠️ 删除配置</b>\n\n"
            "删除后您将无法使用转发功能，除非重新配置。"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ 确认删除", callback_data="confirm_delete")],
            [InlineKeyboardButton("⬅️ 返回", callback_data="back")],
        ])
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=markup)
        else:
            await update.effective_message.reply_text(text, reply_markup=markup)
        
        return SettingsState.DELETE_CONFIG
    
    @staticmethod
    async def _delete_config_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """确认删除配置"""
        user = await UserManager.ensure_user_registered(update, context)

        success = UserManager.delete_user_config(user.id)

        text = "✅ 配置已删除" if success else "❌ 删除配置失败"
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=SettingsManager._settings_main_markup())
        else:
            await update.effective_message.reply_text(text, reply_markup=SettingsManager._settings_main_markup())

        return SettingsState.MAIN_MENU
    
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
        await update.effective_message.reply_text("设置已取消")
        return ConversationHandler.END
    
    @staticmethod
    async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """跳过密码设置"""
        # 获取用户和现有配置
        user = await UserManager.ensure_user_registered(update, context)
        config = UserManager.get_user_config(user.id)
        
        if not config:
            await update.effective_message.reply_text("请先设置API地址", reply_markup=SettingsManager._settings_main_markup())
            return SettingsState.MAIN_MENU
        
        # 保存配置（不设置密码）
        success = UserManager.save_user_config(user.id, config.y2a_api_url, None)
        
        if success:
            await update.effective_message.reply_text("✅ 已跳过密码设置", reply_markup=SettingsManager._settings_main_markup())
        else:
            await update.effective_message.reply_text("❌ 保存配置失败，请稍后重试", reply_markup=SettingsManager._settings_main_markup())

        return SettingsState.MAIN_MENU
    
    @staticmethod
    def get_conversation_handler() -> ConversationHandler:
        """获取设置菜单的对话处理器"""
        return ConversationHandler(
            entry_points=[CommandHandler("settings", SettingsManager.settings_command)],
            states={
                SettingsState.MAIN_MENU: [
                    CallbackQueryHandler(SettingsManager.settings_callback, pattern=r"^(view_config|set_api_url|set_password|test_connection|delete_config|back)$"),
                ],
                SettingsState.SET_API_URL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, SettingsManager._set_api_url_end),
                    CallbackQueryHandler(SettingsManager.settings_callback, pattern=r"^back$"),
                ],
                SettingsState.SET_PASSWORD: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, SettingsManager._set_password_end),
                    CallbackQueryHandler(SettingsManager.skip_command, pattern=r"^skip$"),
                    CallbackQueryHandler(SettingsManager.settings_callback, pattern=r"^back$"),
                ],
                SettingsState.DELETE_CONFIG: [
                    CallbackQueryHandler(SettingsManager.settings_callback, pattern=r"^(confirm_delete|back)$"),
                ]
            },
            fallbacks=[CommandHandler("cancel", SettingsManager.cancel_command)],
            per_message=False
        )