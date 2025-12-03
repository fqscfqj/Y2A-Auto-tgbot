"""
设置管理器 - 优化版

提供统一的设置界面，支持：
- 查看当前配置
- 设置/修改API地址
- 设置/修改密码
- 测试连接
- 删除配置
"""
import logging
import html
from enum import IntEnum
from typing import Optional, cast, Dict, Any

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
    """设置状态"""
    MAIN_MENU = 0
    SET_API_URL = 1
    SET_PASSWORD = 2
    DELETE_CONFIG = 3


class SettingsManager:
    """设置管理器 - 优化版
    
    特点：
    - 统一的消息格式和按钮布局
    - 简化的状态管理
    - 清晰的用户反馈
    """

    # ==================== 辅助方法 ====================

    @staticmethod
    def _ensure_user_data(context: ContextTypes.DEFAULT_TYPE) -> None:
        """确保user_data已初始化"""
        if getattr(context, 'user_data', None) is None:
            context.user_data = {}

    @staticmethod
    async def _safe_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                          text: str, reply_markup: Optional[InlineKeyboardMarkup] = None) -> None:
        """安全发送消息，支持编辑或回复"""
        try:
            # 优先尝试编辑回调消息
            query = update.callback_query
            if query and getattr(query, 'message', None):
                try:
                    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
                    return
                except Exception:
                    pass

            # 尝试回复消息
            message = update.effective_message or update.message
            if message:
                await message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
                return

            # 最后尝试直接发送到聊天
            chat = update.effective_chat
            if chat:
                await context.bot.send_message(
                    chat_id=chat.id, text=text, reply_markup=reply_markup, parse_mode='HTML'
                )
        except Exception as e:
            logger.error(f"发送消息失败: {e}")

    # ==================== 按钮布局 ====================

    @staticmethod
    def _main_menu_markup(has_config: bool = False) -> InlineKeyboardMarkup:
        """主菜单按钮布局"""
        buttons = []
        
        if has_config:
            buttons.append([InlineKeyboardButton("🔍 查看配置", callback_data="settings:view")])
        
        buttons.extend([
            [InlineKeyboardButton("🔧 设置 API 地址", callback_data="settings:set_api")],
            [InlineKeyboardButton("🔑 设置密码", callback_data="settings:set_password")],
        ])
        
        if has_config:
            buttons.extend([
                [InlineKeyboardButton("🔬 测试连接", callback_data="settings:test")],
                [InlineKeyboardButton("🗑️ 删除配置", callback_data="settings:delete")],
            ])
        
        buttons.append([InlineKeyboardButton("✅ 完成", callback_data="settings:done")])
        
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def _back_markup() -> InlineKeyboardMarkup:
        """返回按钮"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ 返回", callback_data="settings:back")]
        ])

    @staticmethod
    def _skip_back_markup() -> InlineKeyboardMarkup:
        """跳过和返回按钮（用于密码设置）"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⏭️ 跳过", callback_data="settings:skip_password"),
                InlineKeyboardButton("⬅️ 返回", callback_data="settings:back"),
            ]
        ])

    @staticmethod
    def _post_api_markup() -> InlineKeyboardMarkup:
        """API设置成功后的按钮"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔬 测试连接", callback_data="settings:test")],
            [InlineKeyboardButton("⬅️ 返回", callback_data="settings:back")],
        ])

    @staticmethod
    def _test_result_markup(success: bool) -> InlineKeyboardMarkup:
        """测试结果按钮"""
        if success:
            return InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ 完成", callback_data="settings:done")]
            ])
        else:
            return InlineKeyboardMarkup([
                [InlineKeyboardButton("🔧 修改配置", callback_data="settings:set_api")],
                [InlineKeyboardButton("⬅️ 返回", callback_data="settings:back")],
            ])

    @staticmethod
    def _delete_confirm_markup() -> InlineKeyboardMarkup:
        """删除确认按钮"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⚠️ 确认删除", callback_data="settings:confirm_delete")],
            [InlineKeyboardButton("⬅️ 取消", callback_data="settings:back")],
        ])

    # ==================== 主要功能 ====================

    @staticmethod
    async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理 /settings 命令 - 显示设置主菜单"""
        user = await UserManager.ensure_user_registered(update, context)
        if not user or user.id is None:
            await SettingsManager._safe_reply(update, context, "❌ 用户信息无效")
            return ConversationHandler.END
        
        SettingsManager._ensure_user_data(context)
        
        # 检查是否有配置
        config = UserManager.get_user_config(user.id)
        has_config = bool(config and config.y2a_api_url)
        
        text = """<b>⚙️ 设置</b>

请选择要进行的操作："""
        
        await SettingsManager._safe_reply(
            update, context, text, 
            reply_markup=SettingsManager._main_menu_markup(has_config)
        )
        return SettingsState.MAIN_MENU

    @staticmethod
    async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理设置相关的回调按钮"""
        query = update.callback_query
        if not query:
            return SettingsState.MAIN_MENU
        
        await query.answer()
        
        user = await UserManager.ensure_user_registered(update, context)
        if not user or user.id is None:
            await SettingsManager._safe_reply(update, context, "❌ 用户信息无效")
            return SettingsState.MAIN_MENU
        
        action = (query.data or "").replace("settings:", "")
        
        # 路由到对应处理方法
        handlers = {
            "view": SettingsManager._view_config,
            "set_api": SettingsManager._set_api_start,
            "set_password": SettingsManager._set_password_start,
            "test": SettingsManager._test_connection,
            "delete": SettingsManager._delete_start,
            "confirm_delete": SettingsManager._delete_confirm,
            "skip_password": SettingsManager._skip_password,
            "back": SettingsManager._back_to_menu,
            "done": SettingsManager._done,
        }
        
        handler = handlers.get(action)
        if handler:
            return await handler(update, context, user)
        
        return SettingsState.MAIN_MENU

    # ==================== 查看配置 ====================

    @staticmethod
    async def _view_config(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> int:
        """查看当前配置"""
        if user.id is None:
            await SettingsManager._safe_reply(update, context, "❌ 用户信息无效")
            return SettingsState.MAIN_MENU
        
        config = UserManager.get_user_config(user.id)
        
        if config and config.y2a_api_url:
            api_url = html.escape(config.y2a_api_url)
            password_status = "✅ 已设置" if config.y2a_password else "❌ 未设置"
            created = config.created_at.strftime('%Y-%m-%d %H:%M') if config.created_at else "未知"
            updated = config.updated_at.strftime('%Y-%m-%d %H:%M') if config.updated_at else "未知"
            
            text = f"""<b>🔍 当前配置</b>

<b>API 地址</b>
<code>{api_url}</code>

<b>密码</b>
{password_status}

<b>时间</b>
• 创建：{created}
• 更新：{updated}"""
        else:
            text = """<b>🔍 当前配置</b>

❌ 您尚未配置 Y2A-Auto 服务。

请点击"设置 API 地址"开始配置。"""
        
        await SettingsManager._safe_reply(update, context, text, SettingsManager._back_markup())
        return SettingsState.MAIN_MENU

    # ==================== 设置API ====================

    @staticmethod
    async def _set_api_start(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> int:
        """开始设置API地址"""
        SettingsManager._ensure_user_data(context)
        user_data = cast(Dict[str, Any], context.user_data)
        user_data['pending_input'] = 'set_api'
        
        text = """<b>🔧 设置 API 地址</b>

请发送您的 Y2A-Auto 服务地址。

<b>📝 示例</b>
<code>https://y2a.example.com</code>
<code>http://192.168.1.100:5000</code>
<code>localhost:5000</code>

<b>💡 提示</b>
只需输入主机和端口，路径会自动补全。"""
        
        await SettingsManager._safe_reply(update, context, text, SettingsManager._back_markup())
        return SettingsState.SET_API_URL

    @staticmethod
    async def _set_api_url_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理API地址输入"""
        user = await UserManager.ensure_user_registered(update, context)
        if not user or user.id is None:
            return SettingsState.MAIN_MENU
        
        message = update.effective_message or update.message
        if not message:
            return SettingsState.MAIN_MENU
        
        message_text = getattr(message, 'text', None)
        if not message_text:
            return SettingsState.MAIN_MENU
        
        api_url = message_text.strip()
        
        # 清除pending状态
        SettingsManager._ensure_user_data(context)
        cast(Dict[str, Any], context.user_data).pop('pending_input', None)
        
        if not api_url:
            await SettingsManager._safe_reply(
                update, context, 
                "❌ API 地址不能为空，请重新输入",
                SettingsManager._back_markup()
            )
            return SettingsState.SET_API_URL
        
        # 规范化URL
        from src.managers.forward_manager import ForwardManager
        if not (api_url.startswith('http://') or api_url.startswith('https://')):
            api_url = 'https://' + api_url
        api_url = ForwardManager.normalize_api_url(api_url)
        
        # 保留现有密码
        config = UserManager.get_user_config(user.id)
        password = config.y2a_password if config else None
        
        # 保存配置
        success = UserManager.save_user_config(user.id, api_url, password)
        
        if success:
            text = f"""<b>✅ API 地址已设置</b>

<code>{html.escape(api_url)}</code>

建议点击"测试连接"验证配置是否正确。"""
            
            await SettingsManager._safe_reply(
                update, context, text, 
                SettingsManager._post_api_markup()
            )
        else:
            await SettingsManager._safe_reply(
                update, context, 
                "❌ 设置失败，请稍后重试",
                SettingsManager._back_markup()
            )
        
        return SettingsState.MAIN_MENU

    # ==================== 设置密码 ====================

    @staticmethod
    async def _set_password_start(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> int:
        """开始设置密码"""
        if user.id is None:
            await SettingsManager._safe_reply(update, context, "❌ 用户信息无效")
            return SettingsState.MAIN_MENU
        
        config = UserManager.get_user_config(user.id)
        if not config or not config.y2a_api_url:
            await SettingsManager._safe_reply(
                update, context, 
                "❌ 请先设置 API 地址",
                SettingsManager._back_markup()
            )
            return SettingsState.MAIN_MENU
        
        SettingsManager._ensure_user_data(context)
        cast(Dict[str, Any], context.user_data)['pending_input'] = 'set_password'
        
        current_status = "✅ 当前已设置密码" if config.y2a_password else "❌ 当前未设置密码"
        
        text = f"""<b>🔑 设置密码</b>

{current_status}

请发送新密码，或点击"跳过"清除现有密码。

<b>💡 提示</b>
密码用于自动登录 Y2A-Auto 服务。如果您的服务没有设置密码保护，可以跳过此步骤。"""
        
        await SettingsManager._safe_reply(
            update, context, text, 
            SettingsManager._skip_back_markup()
        )
        return SettingsState.SET_PASSWORD

    @staticmethod
    async def _set_password_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理密码输入"""
        user = await UserManager.ensure_user_registered(update, context)
        if not user or user.id is None:
            return SettingsState.MAIN_MENU
        
        message = update.effective_message or update.message
        if not message:
            return SettingsState.MAIN_MENU
        
        message_text = getattr(message, 'text', None)
        if not message_text:
            return SettingsState.MAIN_MENU
        
        password = message_text.strip()
        
        # 清除pending状态
        SettingsManager._ensure_user_data(context)
        cast(Dict[str, Any], context.user_data).pop('pending_input', None)
        
        config = UserManager.get_user_config(user.id)
        if not config or not config.y2a_api_url:
            await SettingsManager._safe_reply(
                update, context, 
                "❌ 请先设置 API 地址",
                SettingsManager._back_markup()
            )
            return SettingsState.MAIN_MENU
        
        # 保存密码
        success = UserManager.save_user_config(user.id, config.y2a_api_url, password)
        
        if success:
            text = """<b>✅ 密码已设置</b>

建议点击"测试连接"验证配置是否正确。"""
            
            await SettingsManager._safe_reply(
                update, context, text, 
                SettingsManager._post_api_markup()
            )
        else:
            await SettingsManager._safe_reply(
                update, context, 
                "❌ 设置失败，请稍后重试",
                SettingsManager._back_markup()
            )
        
        return SettingsState.MAIN_MENU

    @staticmethod
    async def _skip_password(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> int:
        """跳过/清除密码"""
        if user.id is None:
            return SettingsState.MAIN_MENU
        
        config = UserManager.get_user_config(user.id)
        if config and config.y2a_api_url:
            # 清除密码
            UserManager.save_user_config(user.id, config.y2a_api_url, "")
            
            await SettingsManager._safe_reply(
                update, context, 
                "✅ 已清除密码设置",
                SettingsManager._back_markup()
            )
        
        return SettingsState.MAIN_MENU

    # ==================== 测试连接 ====================

    @staticmethod
    async def _test_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> int:
        """测试连接"""
        if user.id is None:
            await SettingsManager._safe_reply(update, context, "❌ 用户信息无效")
            return SettingsState.MAIN_MENU
        
        config = UserManager.get_user_config(user.id)
        if not config or not config.y2a_api_url:
            await SettingsManager._safe_reply(
                update, context, 
                "❌ 请先配置 Y2A-Auto 服务",
                SettingsManager._back_markup()
            )
            return SettingsState.MAIN_MENU
        
        # 显示测试中消息
        await SettingsManager._safe_reply(update, context, "🔄 正在测试连接...")
        
        # 执行测试
        from src.managers.forward_manager import ForwardManager
        result = await ForwardManager.test_connection(update, context, user, config)
        
        success = result.startswith("✅")
        
        text = f"""<b>🔬 连接测试结果</b>

{result}"""
        
        await SettingsManager._safe_reply(
            update, context, text, 
            SettingsManager._test_result_markup(success)
        )
        return SettingsState.MAIN_MENU

    # ==================== 删除配置 ====================

    @staticmethod
    async def _delete_start(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> int:
        """开始删除配置"""
        text = """<b>⚠️ 删除配置</b>

确定要删除当前配置吗？

删除后您将无法使用转发功能，除非重新配置。"""
        
        await SettingsManager._safe_reply(
            update, context, text, 
            SettingsManager._delete_confirm_markup()
        )
        return SettingsState.DELETE_CONFIG

    @staticmethod
    async def _delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> int:
        """确认删除配置"""
        if user.id is None:
            return SettingsState.MAIN_MENU
        
        success = UserManager.delete_user_config(user.id)
        
        if success:
            text = """<b>✅ 配置已删除</b>

如需重新配置，请使用 /settings 命令。"""
        else:
            text = "❌ 删除失败，请稍后重试"
        
        await SettingsManager._safe_reply(
            update, context, text, 
            SettingsManager._main_menu_markup(has_config=False)
        )
        return SettingsState.MAIN_MENU

    # ==================== 导航 ====================

    @staticmethod
    async def _back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> int:
        """返回主菜单"""
        # 清除pending状态
        SettingsManager._ensure_user_data(context)
        cast(Dict[str, Any], context.user_data).pop('pending_input', None)
        
        return await SettingsManager.settings_command(update, context)

    @staticmethod
    async def _done(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> int:
        """完成设置"""
        text = """<b>✅ 设置完成</b>

现在您可以直接发送 YouTube 链接进行转发。

使用 /settings 随时修改配置。"""
        
        from src.managers.forward_manager import ForwardManager
        markup = ForwardManager.main_menu_markup(include_example=True)
        
        await SettingsManager._safe_reply(update, context, text, markup)
        return ConversationHandler.END

    # ==================== 命令处理 ====================

    @staticmethod
    async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理 /cancel 命令"""
        SettingsManager._ensure_user_data(context)
        cast(Dict[str, Any], context.user_data).pop('pending_input', None)
        
        await SettingsManager._safe_reply(update, context, "设置已取消")
        return ConversationHandler.END

    # ==================== 对话处理器 ====================

    @staticmethod
    def get_conversation_handler() -> ConversationHandler:
        """获取设置对话处理器"""
        return ConversationHandler(
            entry_points=[CommandHandler("settings", SettingsManager.settings_command)],
            states={
                SettingsState.MAIN_MENU: [
                    CallbackQueryHandler(
                        SettingsManager.settings_callback, 
                        pattern=r"^settings:"
                    ),
                ],
                SettingsState.SET_API_URL: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, 
                        SettingsManager._set_api_url_end
                    ),
                    CallbackQueryHandler(
                        SettingsManager.settings_callback, 
                        pattern=r"^settings:"
                    ),
                ],
                SettingsState.SET_PASSWORD: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, 
                        SettingsManager._set_password_end
                    ),
                    CallbackQueryHandler(
                        SettingsManager.settings_callback, 
                        pattern=r"^settings:"
                    ),
                ],
                SettingsState.DELETE_CONFIG: [
                    CallbackQueryHandler(
                        SettingsManager.settings_callback, 
                        pattern=r"^settings:"
                    ),
                ],
            },
            fallbacks=[CommandHandler("cancel", SettingsManager.cancel_command)],
            per_message=False,
        )
