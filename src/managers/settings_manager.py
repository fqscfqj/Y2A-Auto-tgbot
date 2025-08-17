import logging
import html
from enum import IntEnum
from typing import Any, Dict, Optional, cast

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.managers.user_manager import UserManager
from src.database.models import User

logger = logging.getLogger(__name__)


class SettingsState(IntEnum):
    MAIN_MENU = 0
    SET_API_URL = 1
    SET_PASSWORD = 2
    DELETE_CONFIG = 3


class SettingsManager:
    """Handlers for bot settings. Defensive: avoid optional-member access and validate user.id before DB calls."""

    @staticmethod
    def _ensure_user_data(context: ContextTypes.DEFAULT_TYPE) -> None:
        if getattr(context, 'user_data', None) is None:
            context.user_data = {}

    @staticmethod
    async def _safe_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup: Optional[InlineKeyboardMarkup] = None) -> None:
        """Try to edit callback message, else reply to message, else send to chat."""
        try:
            query = update.callback_query
            if query and getattr(query, 'message', None):
                try:
                    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
                    return
                except Exception:
                    pass

            message = update.effective_message or update.message
            if message:
                await message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
                return

            chat = update.effective_chat
            if chat:
                await context.bot.send_message(chat_id=chat.id, text=text, reply_markup=reply_markup, parse_mode='HTML')
        except Exception:
            logger.exception("Failed to send reply")

    @staticmethod
    def _settings_main_markup() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 查看配置", callback_data="view_config")],
            [InlineKeyboardButton("🔧 设置 API 地址", callback_data="set_api_url")],
            [InlineKeyboardButton("🔑 设置密码", callback_data="set_password")],
            [InlineKeyboardButton("🔬 测试连接", callback_data="test_connection")],
            [InlineKeyboardButton("❌ 删除配置", callback_data="delete_config")],
        ])

    @staticmethod
    def _view_config_markup() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 返回", callback_data="back")]])

    @staticmethod
    def _back_markup() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 返回", callback_data="back")]])

    @staticmethod
    def _post_set_api_markup() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔬 现在测试连接", callback_data="test_connection")],
            [InlineKeyboardButton("⬅️ 返回", callback_data="back")],
        ])

    @staticmethod
    def _test_result_markup() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ 返回", callback_data="back")]])

    @staticmethod
    def _test_success_markup() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton("✅ 完成", callback_data="back")]])

    @staticmethod
    async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = await UserManager.ensure_user_registered(update, context)

        settings_text = "<b>⚙️ 设置菜单</b>\n请选择需要执行的操作："

        SettingsManager._ensure_user_data(context)
        await SettingsManager._safe_reply(update, context, settings_text, reply_markup=SettingsManager._settings_main_markup())
        return SettingsState.MAIN_MENU

    @staticmethod
    async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        if query is None:
            logger.error("settings_callback called without callback_query")
            await SettingsManager._safe_reply(update, context, "发生错误：回调数据缺失", reply_markup=SettingsManager._settings_main_markup())
            return SettingsState.MAIN_MENU

        await query.answer()
        user = await UserManager.ensure_user_registered(update, context)
        action = getattr(query, 'data', None)
        if action is None:
            logger.error("callback_query.data is None")
            return SettingsState.MAIN_MENU

        if action == "view_config":
            return await SettingsManager._view_config(update, context, user)
        if action == "set_api_url":
            return await SettingsManager._set_api_url_start(update, context)
        if action == "set_password":
            return await SettingsManager._set_password_start(update, context)
        if action == "test_connection":
            return await SettingsManager._test_connection(update, context, user)
        if action == "delete_config":
            return await SettingsManager._delete_config_start(update, context)
        if action == "confirm_delete":
            return await SettingsManager._delete_config_confirm(update, context)
        if action == "back":
            await query.edit_message_text("<b>⚙️ 设置菜单</b>\n请选择需要执行的操作：", reply_markup=SettingsManager._settings_main_markup())
            return SettingsState.MAIN_MENU

        return SettingsState.MAIN_MENU

    @staticmethod
    async def _view_config(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> int:
        if user.id is None:
            logger.error("User.id is None in _view_config")
            await SettingsManager._safe_reply(update, context, "内部错误：用户ID缺失", reply_markup=SettingsManager._settings_main_markup())
            return SettingsState.MAIN_MENU

        config = UserManager.get_user_config(int(user.id))
        if config:
            config_text = "<b>当前配置</b>\n\n"
            config_text += f"API地址: <code>{html.escape(config.y2a_api_url or '')}</code>\n"
            config_text += f"密码: {'已设置' if config.y2a_password else '未设置'}\n"
            created = getattr(config, 'created_at', None)
            updated = getattr(config, 'updated_at', None)
            config_text += f"配置时间: {created.strftime('%Y-%m-%d %H:%M:%S') if created else '未知'}\n"
            config_text += f"最后更新: {updated.strftime('%Y-%m-%d %H:%M:%S') if updated else '未知'}"
        else:
            config_text = "<b>当前配置</b>\n\n您尚未配置Y2A-Auto服务。"

        await SettingsManager._safe_reply(update, context, config_text, reply_markup=SettingsManager._view_config_markup())
        return SettingsState.MAIN_MENU

    @staticmethod
    async def _set_api_url_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = (
            "<b>设置 API 地址</b>\n\n"
            "请直接发送新的 API 地址（支持只写主机:端口，将自动补全）。\n\n"
            "示例: <code>https://y2a.example.com:4443</code> 或 <code>http://localhost:5000</code>"
        )

        SettingsManager._ensure_user_data(context)
        user_data = cast(Dict[str, Any], context.user_data)
        user_data['pending_input'] = 'set_api'

        await SettingsManager._safe_reply(update, context, text, reply_markup=SettingsManager._back_markup())
        return SettingsState.SET_API_URL

    @staticmethod
    async def _set_api_url_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = await UserManager.ensure_user_registered(update, context)
        message = update.effective_message or (update.callback_query.message if update.callback_query else None) or update.message
        if not message:
            return SettingsState.MAIN_MENU
        message_text = getattr(message, 'text', None)
        if not message_text:
            return SettingsState.MAIN_MENU
        api_url = message_text.strip()

        SettingsManager._ensure_user_data(context)
        cast(Dict[str, Any], context.user_data).pop('pending_input', None)

        if not api_url:
            await SettingsManager._safe_reply(update, context, "API地址不能为空，请重新输入", reply_markup=SettingsManager._back_markup())
            return SettingsState.SET_API_URL

        from src.managers.forward_manager import ForwardManager
        if not (api_url.startswith('http://') or api_url.startswith('https://')):
            api_url = 'https://' + api_url
        api_url = ForwardManager.normalize_api_url(api_url)

        if user.id is None:
            logger.error("User.id is None in _set_api_url_end")
            await SettingsManager._safe_reply(update, context, "内部错误：用户ID缺失", reply_markup=SettingsManager._settings_main_markup())
            return SettingsState.MAIN_MENU

        config = UserManager.get_user_config(int(user.id))
        password = config.y2a_password if config else None

        success = UserManager.save_user_config(int(user.id), api_url, password)
        if success:
            await SettingsManager._safe_reply(update, context, f"✅ API地址已设置为: <code>{html.escape(api_url)}</code>\n\n是否现在进行连接测试？", reply_markup=SettingsManager._post_set_api_markup())
        else:
            await SettingsManager._safe_reply(update, context, "❌ 设置API地址失败，请稍后重试", reply_markup=SettingsManager._settings_main_markup())

        return SettingsState.MAIN_MENU

    @staticmethod
    async def _set_password_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = (
            "<b>设置密码（可选）</b>\n"
            "请直接发送密码；如无需密码，可点击下方“跳过”。"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏭️ 跳过", callback_data="skip")],
            [InlineKeyboardButton("⬅️ 返回", callback_data="back")],
        ])

        SettingsManager._ensure_user_data(context)
        cast(Dict[str, Any], context.user_data)['pending_input'] = 'set_password'
        await SettingsManager._safe_reply(update, context, text, reply_markup=markup)
        return SettingsState.SET_PASSWORD

    @staticmethod
    async def _set_password_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = await UserManager.ensure_user_registered(update, context)
        message = update.effective_message or (update.callback_query.message if update.callback_query else None) or update.message
        if not message:
            return SettingsState.MAIN_MENU
        message_text = getattr(message, 'text', None)
        if not message_text:
            return SettingsState.MAIN_MENU
        password = message_text.strip()

        SettingsManager._ensure_user_data(context)
        cast(Dict[str, Any], context.user_data).pop('pending_input', None)

        if user.id is None:
            logger.error("User.id is None in _set_password_end")
            await SettingsManager._safe_reply(update, context, "内部错误：用户ID缺失", reply_markup=SettingsManager._settings_main_markup())
            return SettingsState.MAIN_MENU

        config = UserManager.get_user_config(int(user.id))
        if not config:
            await SettingsManager._safe_reply(update, context, "请先设置API地址", reply_markup=SettingsManager._settings_main_markup())
            return SettingsState.MAIN_MENU

        success = UserManager.save_user_config(int(user.id), config.y2a_api_url or "", password)
        if success:
            await SettingsManager._safe_reply(update, context, "✅ 密码已设置\n\n是否现在进行连接测试？", reply_markup=SettingsManager._post_set_api_markup())
        else:
            await SettingsManager._safe_reply(update, context, "❌ 设置密码失败，请稍后重试", reply_markup=SettingsManager._settings_main_markup())

        return SettingsState.MAIN_MENU

    @staticmethod
    async def _test_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> int:
        if user.id is None:
            logger.error("User.id is None in _test_connection")
            await SettingsManager._safe_reply(update, context, "内部错误：用户ID缺失", reply_markup=SettingsManager._settings_main_markup())
            return SettingsState.MAIN_MENU

        config = UserManager.get_user_config(int(user.id))
        if not config:
            await SettingsManager._safe_reply(update, context, "❌ 您尚未配置Y2A-Auto服务", reply_markup=SettingsManager._settings_main_markup())
            return SettingsState.MAIN_MENU

        from src.managers.forward_manager import ForwardManager
        result = await ForwardManager.test_connection(update, context, user, config)
        text = f"<b>🔌 连接测试结果</b>\n\n{result}"
        markup = SettingsManager._test_success_markup() if str(result).startswith("✅") else SettingsManager._test_result_markup()

        await SettingsManager._safe_reply(update, context, text, reply_markup=markup)
        return SettingsState.MAIN_MENU

    @staticmethod
    async def _delete_config_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = (
            "<b>⚠️ 删除配置</b>\n\n"
            "删除后您将无法使用转发功能，除非重新配置。"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ 确认删除", callback_data="confirm_delete")],
            [InlineKeyboardButton("⬅️ 返回", callback_data="back")],
        ])

        await SettingsManager._safe_reply(update, context, text, reply_markup=markup)
        return SettingsState.DELETE_CONFIG

    @staticmethod
    async def _delete_config_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = await UserManager.ensure_user_registered(update, context)

        if user.id is None:
            logger.error("User.id is None in _delete_config_confirm")
            await SettingsManager._safe_reply(update, context, "内部错误：用户ID缺失", reply_markup=SettingsManager._settings_main_markup())
            return SettingsState.MAIN_MENU

        success = UserManager.delete_user_config(int(user.id))
        text = "✅ 配置已删除" if success else "❌ 删除配置失败"
        await SettingsManager._safe_reply(update, context, text, reply_markup=SettingsManager._settings_main_markup())
        return SettingsState.MAIN_MENU

    @staticmethod
    async def view_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = await UserManager.ensure_user_registered(update, context)
        return await SettingsManager._view_config(update, context, user)

    @staticmethod
    async def set_api_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        return await SettingsManager._set_api_url_start(update, context)

    @staticmethod
    async def set_password_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        return await SettingsManager._set_password_start(update, context)

    @staticmethod
    async def test_connection_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = await UserManager.ensure_user_registered(update, context)
        return await SettingsManager._test_connection(update, context, user)

    @staticmethod
    async def delete_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        return await SettingsManager._delete_config_start(update, context)

    @staticmethod
    async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await SettingsManager._safe_reply(update, context, "设置已取消")
        return ConversationHandler.END

    @staticmethod
    async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = await UserManager.ensure_user_registered(update, context)
        if user.id is None:
            logger.error("User.id is None in skip_command")
            await SettingsManager._safe_reply(update, context, "内部错误：用户ID缺失", reply_markup=SettingsManager._settings_main_markup())
            return SettingsState.MAIN_MENU

        config = UserManager.get_user_config(int(user.id))
        if not config:
            await SettingsManager._safe_reply(update, context, "请先设置API地址", reply_markup=SettingsManager._settings_main_markup())
            return SettingsState.MAIN_MENU

        success = UserManager.save_user_config(int(user.id), config.y2a_api_url or "", None)
        if success:
            await SettingsManager._safe_reply(update, context, "✅ 已跳过密码设置", reply_markup=SettingsManager._settings_main_markup())
        else:
            await SettingsManager._safe_reply(update, context, "❌ 保存配置失败，请稍后重试", reply_markup=SettingsManager._settings_main_markup())

        return SettingsState.MAIN_MENU

    @staticmethod
    def get_conversation_handler() -> ConversationHandler:
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
            per_message=False,
        )