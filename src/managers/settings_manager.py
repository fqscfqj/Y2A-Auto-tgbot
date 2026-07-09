"""
设置管理器 - 优化版

提供统一的设置界面，支持：
- 查看当前配置
- 设置/修改API地址
- 设置/修改API Token
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
from telegram.constants import ChatAction

from src.managers.user_manager import UserManager
from src.database.models import User
from src.utils.config_status import get_config_status, is_tgbot_api_token, upload_target_label

logger = logging.getLogger(__name__)


class SettingsState(IntEnum):
    """设置状态"""
    MAIN_MENU = 0
    SET_API_URL = 1
    SET_API_TOKEN = 2
    DELETE_CONFIG = 3
    SET_UPLOAD_TARGET = 4


class SettingsManager:
    """设置管理器 - 优化版
    
    特点：
    - 统一的消息格式和按钮布局
    - 简化的状态管理
    - 清晰的用户反馈
    - 优化的交互体验
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
    def _main_menu_markup(config=None) -> InlineKeyboardMarkup:
        """主菜单按钮布局。"""
        status = get_config_status(config)
        primary_callback = f"settings:{status.next_action}"

        buttons = [[InlineKeyboardButton(f"➡️ {status.next_label}", callback_data=primary_callback)]]

        buttons.append([
            InlineKeyboardButton("🔧 API 地址", callback_data="settings:set_api"),
            InlineKeyboardButton("🔐 API Token", callback_data="settings:set_api_token"),
        ])

        if status.has_api_url:
            buttons.append([
                InlineKeyboardButton("🎯 投稿平台", callback_data="settings:set_upload_target"),
                InlineKeyboardButton("🔬 测试", callback_data="settings:test"),
            ])
            buttons.append([
                InlineKeyboardButton("🔍 查看", callback_data="settings:view"),
                InlineKeyboardButton("🗑️ 清空", callback_data="settings:delete"),
            ])
        else:
            buttons.append([InlineKeyboardButton("❓ 帮助", callback_data="main:help")])

        buttons.append([InlineKeyboardButton("✅ 完成", callback_data="settings:done")])
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def _format_status_panel(config) -> str:
        """格式化设置首页状态面板。"""
        status = get_config_status(config)
        api_display = f"<code>{html.escape(status.api_url)}</code>" if status.has_api_url else "❌ 未设置"
        if not status.has_api_token:
            token_display = "❌ 未设置"
        elif not status.has_valid_api_token:
            token_display = "⚠️ 格式需要检查"
        else:
            token_display = "✅ 已设置"

        ready_display = "✅ 可以转发" if status.is_ready else "⏳ 还差一步"
        target_display = upload_target_label(status.upload_target)

        return f"""<b>⚙️ 设置中心</b>

<b>当前状态</b>
• 服务地址：{api_display}
• API Token：{token_display}
• 投稿平台：{target_display}
• 可用状态：{ready_display}

<b>下一步</b>
{html.escape(status.summary)}"""

    @staticmethod
    def _back_markup() -> InlineKeyboardMarkup:
        """返回按钮"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ 返回", callback_data="settings:back")]
        ])

    @staticmethod
    def _skip_back_markup() -> InlineKeyboardMarkup:
        """清除和返回按钮（用于 API Token 设置）"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🧹 清除 Token", callback_data="settings:clear_api_token"),
                InlineKeyboardButton("⬅️ 返回", callback_data="settings:back"),
            ]
        ])

    @staticmethod
    def _post_api_markup() -> InlineKeyboardMarkup:
        """API设置成功后的按钮"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔐 设置 API Token", callback_data="settings:set_api_token")],
            [InlineKeyboardButton("⬅️ 返回", callback_data="settings:back")],
        ])

    @staticmethod
    def _post_token_markup() -> InlineKeyboardMarkup:
        """Token 设置成功后的按钮。"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔬 测试连接", callback_data="settings:test")],
            [InlineKeyboardButton("✅ 完成", callback_data="settings:done")],
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
                [InlineKeyboardButton("🔐 设置 API Token", callback_data="settings:set_api_token")],
                [InlineKeyboardButton("🔧 修改 API 地址", callback_data="settings:set_api")],
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
        
        config = UserManager.get_user_config(user.id)
        text = SettingsManager._format_status_panel(config)
        
        await SettingsManager._safe_reply(
            update, context, text, 
            reply_markup=SettingsManager._main_menu_markup(config)
        )
        return SettingsState.MAIN_MENU

    @staticmethod
    async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理设置相关的回调按钮"""
        query = update.callback_query
        if not query:
            return SettingsState.MAIN_MENU
        
        action = (query.data or "").replace("settings:", "")
        
        # 根据操作类型提供有意义的回调应答
        action_labels = {
            "view": "查看配置...",
            "set_api": "设置API地址...",
            "set_api_token": "设置API Token...",
            "set_upload_target": "设置投稿平台...",
            "upload_target_acfun": "设置为AcFun...",
            "upload_target_bilibili": "设置为bilibili...",
            "upload_target_both": "设置为同时投稿...",
            "upload_target_default": "使用服务器默认...",
            "test": "正在测试连接...",
            "delete": "删除配置...",
            "confirm_delete": "正在删除...",
            "clear_api_token": "清除API Token...",
            "back": "返回菜单...",
            "done": "完成设置",
        }
        await query.answer(action_labels.get(action, "处理中..."))
        
        user = await UserManager.ensure_user_registered(update, context)
        if not user or user.id is None:
            await SettingsManager._safe_reply(update, context, "❌ 用户信息无效")
            return SettingsState.MAIN_MENU
        
        # 路由到对应处理方法
        handlers = {
            "view": SettingsManager._view_config,
            "set_api": SettingsManager._set_api_start,
            "set_api_token": SettingsManager._set_api_token_start,
            "set_upload_target": SettingsManager._set_upload_target,
            "upload_target_acfun": SettingsManager._save_upload_target,
            "upload_target_bilibili": SettingsManager._save_upload_target,
            "upload_target_both": SettingsManager._save_upload_target,
            "upload_target_default": SettingsManager._save_upload_target,
            "test": SettingsManager._test_connection,
            "delete": SettingsManager._delete_start,
            "confirm_delete": SettingsManager._delete_confirm,
            "clear_api_token": SettingsManager._clear_api_token,
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
            status = get_config_status(config)
            if not status.has_api_token:
                token_status = "❌ 未设置"
            elif not status.has_valid_api_token:
                token_status = "⚠️ 格式需要检查"
            else:
                token_status = "✅ 已设置"
            created = config.created_at.strftime('%Y-%m-%d %H:%M') if config.created_at else "未知"
            updated = config.updated_at.strftime('%Y-%m-%d %H:%M') if config.updated_at else "未知"
            
            upload_target_display = upload_target_label(config.upload_target)
            
            text = f"""<b>🔍 当前配置</b>

<b>API 地址</b>
<code>{api_url}</code>

<b>API Token</b>
{token_status}

<b>投稿平台</b>
{upload_target_display}

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
        
        text = """<b>第 1 步：设置 API 地址</b>

请发送您的 Y2A-Auto 服务地址。

<b>📝 示例</b>
<code>https://y2a.example.com</code>
<code>http://192.168.1.100:5000</code>
<code>localhost:5000</code>

<b>💡 说明</b>
• 只需输入主机和端口，接口路径会自动补全
• 如果 Bot 运行在服务器上，请填写服务器能访问到的地址
• 地址保存后，还需要设置专用 API Token"""
        
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
        
        # 保留现有 API Token
        config = UserManager.get_user_config(user.id)
        api_token = config.y2a_api_token if config else None
        
        # 保存配置
        success = UserManager.save_user_config(user.id, api_url, api_token)
        SettingsManager._ensure_user_data(context)
        cast(Dict[str, Any], context.user_data).pop('pending_input', None)
        
        if success:
            status = get_config_status(UserManager.get_user_config(user.id))
            if status.is_ready:
                from src.managers.guide_manager import GuideManager
                GuideManager.mark_complete_if_ready(user.id)
                next_text = "配置已完整。建议点击\"测试连接\"验证服务可达性和 Token 鉴权。"
                markup = SettingsManager._post_token_markup()
            else:
                next_text = "请继续设置专用 API Token。Token 需要在 Y2A-Auto Web 设置页生成。"
                markup = SettingsManager._post_api_markup()

            text = f"""<b>✅ API 地址已设置</b>

<code>{html.escape(api_url)}</code>

<b>下一步</b>
{next_text}"""
            
            await SettingsManager._safe_reply(
                update, context, text, 
                markup
            )
        else:
            await SettingsManager._safe_reply(
                update, context, 
                "❌ 设置失败，请稍后重试",
                SettingsManager._back_markup()
            )
        
        return SettingsState.MAIN_MENU

    # ==================== 设置API Token ====================

    @staticmethod
    async def _set_api_token_start(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> int:
        """开始设置 API Token"""
        if user.id is None:
            await SettingsManager._safe_reply(update, context, "❌ 用户信息无效")
            return SettingsState.MAIN_MENU
        
        config = UserManager.get_user_config(user.id)
        if not config or not config.y2a_api_url:
            await SettingsManager._safe_reply(
                update, context, 
                "<b>还不能设置 Token</b>\n\n请先设置 Y2A-Auto API 地址。Bot 需要知道任务提交到哪个服务。",
                InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔧 设置 API 地址", callback_data="settings:set_api")],
                    [InlineKeyboardButton("⬅️ 返回", callback_data="settings:back")],
                ])
            )
            return SettingsState.MAIN_MENU
        
        SettingsManager._ensure_user_data(context)
        cast(Dict[str, Any], context.user_data)['pending_input'] = 'set_api_token'
        
        status = get_config_status(config)
        if not status.has_api_token:
            current_status = "❌ 当前未设置 API Token"
        elif not status.has_valid_api_token:
            current_status = "⚠️ 当前 Token 格式需要检查"
        else:
            current_status = "✅ 当前已设置 API Token"
        
        text = f"""<b>第 2 步：设置 API Token</b>

{current_status}

请发送从 Y2A-Auto Web 设置页生成的 Telegram Bot API Token。

<b>📝 格式</b>
<code>y2a_tgbot_v1_...</code>

<b>💡 说明</b>
• Token 只具备提交上传任务权限
• Bot 会保存该 Token 用于发送任务
• 保存成功后，机器人会尽量删除您刚发送的 Token 消息"""
        
        await SettingsManager._safe_reply(
            update, context, text, 
            SettingsManager._skip_back_markup()
        )
        return SettingsState.SET_API_TOKEN

    @staticmethod
    async def _set_api_token_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理 API Token 输入"""
        user = await UserManager.ensure_user_registered(update, context)
        if not user or user.id is None:
            return SettingsState.MAIN_MENU
        
        message = update.effective_message or update.message
        if not message:
            return SettingsState.MAIN_MENU
        
        message_text = getattr(message, 'text', None)
        if not message_text:
            return SettingsState.MAIN_MENU
        
        api_token = message_text.strip()
        
        config = UserManager.get_user_config(user.id)
        if not config or not config.y2a_api_url:
            SettingsManager._ensure_user_data(context)
            cast(Dict[str, Any], context.user_data).pop('pending_input', None)
            await SettingsManager._safe_reply(
                update, context, 
                "❌ 请先设置 API 地址",
                SettingsManager._back_markup()
            )
            return SettingsState.MAIN_MENU

        if not is_tgbot_api_token(api_token):
            await SettingsManager._safe_reply(
                update, context,
                "<b>API Token 格式不正确</b>\n\n请复制 Y2A-Auto 设置页生成的完整 Token。它应以 <code>y2a_tgbot_v1_</code> 开头。",
                SettingsManager._back_markup()
            )
            return SettingsState.SET_API_TOKEN
        
        # 保存 API Token
        success = UserManager.save_user_config(user.id, config.y2a_api_url, api_token)
        SettingsManager._ensure_user_data(context)
        cast(Dict[str, Any], context.user_data).pop('pending_input', None)
        
        if success:
            from src.managers.guide_manager import GuideManager
            GuideManager.mark_complete_if_ready(user.id)

            text = """<b>✅ API Token 已设置</b>

配置已完整。建议点击"测试连接"，确认 Bot 可以成功访问 Y2A-Auto 并通过 Token 鉴权。"""
            
            await SettingsManager._safe_reply(
                update, context, text, 
                SettingsManager._post_token_markup()
            )
            try:
                await message.delete()
            except Exception as e:
                logger.debug("无法删除 token 消息: %s", e)
        else:
            await SettingsManager._safe_reply(
                update, context, 
                "❌ 设置失败，请稍后重试",
                SettingsManager._back_markup()
            )
        
        return SettingsState.MAIN_MENU

    @staticmethod
    async def _clear_api_token(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> int:
        """清除 API Token"""
        if user.id is None:
            return SettingsState.MAIN_MENU

        SettingsManager._ensure_user_data(context)
        cast(Dict[str, Any], context.user_data).pop('pending_input', None)
        
        config = UserManager.get_user_config(user.id)
        if config and config.y2a_api_url:
            # 清除 API Token
            UserManager.save_user_config(user.id, config.y2a_api_url, "")
            
            await SettingsManager._safe_reply(
                update, context, 
                "<b>✅ 已清除 API Token</b>\n\n清除后 Bot 暂时无法提交上传任务。需要继续使用时，请重新设置 Token。",
                InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔐 重新设置 Token", callback_data="settings:set_api_token")],
                    [InlineKeyboardButton("⬅️ 返回", callback_data="settings:back")],
                ])
            )
        
        return SettingsState.MAIN_MENU

    # ==================== 投稿平台 ====================

    @staticmethod
    def _upload_target_markup(current_target: Optional[str] = None) -> InlineKeyboardMarkup:
        """投稿平台选择按钮"""
        def mark(val: Optional[str]) -> str:
            return "✅ " if current_target == val else ""

        return InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{mark('acfun')}AcFun", callback_data="settings:upload_target_acfun")],
            [InlineKeyboardButton(f"{mark('bilibili')}bilibili", callback_data="settings:upload_target_bilibili")],
            [InlineKeyboardButton(f"{mark('both')}同时投稿（AcFun + bilibili）", callback_data="settings:upload_target_both")],
            [InlineKeyboardButton(f"{mark(None)}使用服务器默认", callback_data="settings:upload_target_default")],
            [InlineKeyboardButton("⬅️ 返回", callback_data="settings:back")],
        ])

    @staticmethod
    async def _set_upload_target(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> int:
        """显示投稿平台选择菜单"""
        if user.id is None:
            await SettingsManager._safe_reply(update, context, "❌ 用户信息无效")
            return SettingsState.MAIN_MENU

        config = UserManager.get_user_config(user.id)
        current_target = config.upload_target if config else None

        text = """<b>🎯 设置投稿平台</b>

请选择投稿目标平台：

• <b>AcFun</b> - 仅上传到 AcFun
• <b>bilibili</b> - 仅上传到 bilibili
• <b>同时投稿</b> - 同时上传到 AcFun 和 bilibili
• <b>服务器默认</b> - 使用 Y2A-Auto 服务的默认设置"""

        await SettingsManager._safe_reply(
            update, context, text,
            SettingsManager._upload_target_markup(current_target)
        )
        return SettingsState.SET_UPLOAD_TARGET

    @staticmethod
    async def _save_upload_target(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> int:
        """保存投稿平台设置"""
        if user.id is None:
            await SettingsManager._safe_reply(update, context, "❌ 用户信息无效")
            return SettingsState.MAIN_MENU

        query = update.callback_query
        action = (query.data or "").replace("settings:", "") if query else ""

        target_map = {
            "upload_target_acfun": "acfun",
            "upload_target_bilibili": "bilibili",
            "upload_target_both": "both",
            "upload_target_default": None,
        }

        if action not in target_map:
            logger.warning("Unknown upload target action '%s' for user %s", action, user.id)
            await SettingsManager._safe_reply(
                update, context,
                "❌ 无效的投稿平台选项，请从菜单中重新选择。",
                SettingsManager._back_markup(),
            )
            return SettingsState.MAIN_MENU

        new_target = target_map[action]

        config = UserManager.get_user_config(user.id)
        if not config or not config.y2a_api_url:
            await SettingsManager._safe_reply(
                update, context,
                "❌ 请先设置 API 地址",
                SettingsManager._back_markup()
            )
            return SettingsState.MAIN_MENU

        # 直接设置 upload_target，保留其他字段
        success = UserManager.save_upload_target(user.id, new_target)

        if success:
            label_map = {"acfun": "AcFun", "bilibili": "bilibili", "both": "同时投稿（AcFun + bilibili）"}
            label = label_map.get(new_target or "", "服务器默认")
            text = f"<b>✅ 投稿平台已设置</b>\n\n当前设置：{label}"
        else:
            text = "❌ 设置失败，请稍后重试"

        await SettingsManager._safe_reply(update, context, text, SettingsManager._back_markup())
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
                "<b>还不能测试连接</b>\n\n请先设置 Y2A-Auto API 地址。",
                InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔧 设置 API 地址", callback_data="settings:set_api")],
                    [InlineKeyboardButton("⬅️ 返回", callback_data="settings:back")],
                ])
            )
            return SettingsState.MAIN_MENU

        status = get_config_status(config)
        if not status.is_ready:
            await SettingsManager._safe_reply(
                update,
                context,
                f"<b>还不能测试连接</b>\n\n{html.escape(status.summary)}",
                InlineKeyboardMarkup([
                    [InlineKeyboardButton(status.next_label, callback_data=f"settings:{status.next_action}")],
                    [InlineKeyboardButton("⬅️ 返回", callback_data="settings:back")],
                ])
            )
            return SettingsState.MAIN_MENU
        
        # 显示测试中消息
        await SettingsManager._safe_reply(update, context, "🔄 正在测试连接...\n\n正在检查服务可达性和 Token 鉴权。")
        
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
        SettingsManager._ensure_user_data(context)
        cast(Dict[str, Any], context.user_data).pop('pending_input', None)

        text = """<b>⚠️ 删除配置</b>

确定要删除当前 Y2A-Auto 配置吗？

这会清除 API 地址、API Token 和投稿平台偏好。删除后 Bot 将无法提交上传任务，除非重新配置。"""
        
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
        SettingsManager._ensure_user_data(context)
        cast(Dict[str, Any], context.user_data).pop('pending_input', None)
        
        success = UserManager.delete_user_config(user.id)
        
        if success:
            text = """<b>✅ 配置已删除</b>

如需重新配置，请使用 /settings 命令。"""
        else:
            text = "❌ 删除失败，请稍后重试"
        
        await SettingsManager._safe_reply(
            update, context, text, 
            SettingsManager._main_menu_markup(None)
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
        config = UserManager.get_user_config(user.id) if user.id is not None else None
        status = get_config_status(config)

        if not status.is_ready:
            text = f"""<b>设置尚未完成</b>

{html.escape(status.summary)}

请先完成下一步，之后就可以直接发送 YouTube 链接。"""
            await SettingsManager._safe_reply(
                update,
                context,
                text,
                InlineKeyboardMarkup([
                    [InlineKeyboardButton(status.next_label, callback_data=f"settings:{status.next_action}")],
                    [InlineKeyboardButton("⬅️ 返回", callback_data="settings:back")],
                ])
            )
            return SettingsState.MAIN_MENU

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
                SettingsState.SET_API_TOKEN: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND, 
                        SettingsManager._set_api_token_end
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
                SettingsState.SET_UPLOAD_TARGET: [
                    CallbackQueryHandler(
                        SettingsManager.settings_callback,
                        pattern=r"^settings:"
                    ),
                ],
            },
            fallbacks=[CommandHandler("cancel", SettingsManager.cancel_command)],
            per_message=False,
        )
