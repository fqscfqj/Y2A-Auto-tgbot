"""
引导管理器

流程：欢迎 → 配置 API 地址 → 配置 API Token → 测试/开始使用
"""
import logging
import html
from typing import Optional
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, 
    ConversationHandler, 
    CallbackQueryHandler, 
    CommandHandler, 
    MessageHandler, 
    filters
)

from src.managers.user_manager import UserManager
from src.database.models import User, UserGuide, GuideStep
from src.database.repository import UserGuideRepository
from src.utils.config_status import get_config_status

logger = logging.getLogger(__name__)


class GuideState:
    """引导状态常量"""
    WELCOME = 1
    CONFIG_API = 2


class GuideManager:
    """引导管理器。"""
    
    # 示例YouTube链接
    EXAMPLE_YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    # ==================== 辅助方法 ====================
    
    @staticmethod
    async def _safe_send(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                         text: str, reply_markup: Optional[InlineKeyboardMarkup] = None) -> bool:
        """安全发送消息，支持编辑回调消息或发送新消息"""
        try:
            # 优先尝试编辑回调消息
            if update.callback_query:
                try:
                    await update.callback_query.edit_message_text(
                        text, reply_markup=reply_markup, parse_mode='HTML'
                    )
                    return True
                except Exception:
                    pass
            
            # 尝试回复消息
            message = update.effective_message or update.message
            if message:
                await message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
                return True
            
            # 最后尝试直接发送到聊天
            chat = update.effective_chat
            if chat:
                await context.bot.send_message(
                    chat_id=chat.id, text=text, reply_markup=reply_markup, parse_mode='HTML'
                )
                return True
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
        return False
    
    @staticmethod
    def _welcome_markup() -> InlineKeyboardMarkup:
        """欢迎页面按钮"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 开始配置", callback_data="guide:start_config")],
            [
                InlineKeyboardButton("⏭️ 跳过引导", callback_data="guide:skip"),
                InlineKeyboardButton("❓ 帮助", callback_data="main:help"),
            ],
        ])
    
    @staticmethod
    def _config_api_markup() -> InlineKeyboardMarkup:
        """配置API页面按钮"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⚙️ 打开设置", callback_data="main:settings")],
            [InlineKeyboardButton("⏭️ 稍后配置", callback_data="guide:skip")],
        ])
    
    @staticmethod
    def _complete_markup() -> InlineKeyboardMarkup:
        """完成页面按钮"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔬 测试连接", callback_data="main:test_connection")],
            [
                InlineKeyboardButton("🎯 发送示例", callback_data="main:send_example"),
                InlineKeyboardButton("⚙️ 设置", callback_data="main:settings"),
            ],
            [InlineKeyboardButton("❓ 帮助", callback_data="main:help")],
        ])

    @staticmethod
    def _next_step_markup(action: str) -> InlineKeyboardMarkup:
        """根据下一步生成引导按钮。"""
        callback = f"settings:{action}"
        if action == "set_api":
            label = "🔧 设置 API 地址"
        elif action == "set_api_token":
            label = "🔐 设置 API Token"
        else:
            callback = "main:test_connection"
            label = "🔬 测试连接"

        return InlineKeyboardMarkup([
            [InlineKeyboardButton(label, callback_data=callback)],
            [
                InlineKeyboardButton("⚙️ 打开设置", callback_data="main:settings"),
                InlineKeyboardButton("❓ 帮助", callback_data="main:help"),
            ],
        ])

    @staticmethod
    def mark_complete_if_ready(user_id: int) -> bool:
        """如果用户配置已完整，则标记引导完成。"""
        status = get_config_status(UserManager.get_user_config(user_id))
        if not status.is_ready:
            return False

        guide = UserGuideRepository.get_by_user_id(user_id)
        if not guide:
            guide = UserGuide(
                user_id=user_id,
                current_step=GuideStep.COMPLETED.value,
                completed_steps="[]",
                is_completed=True,
                is_skipped=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            guide.mark_step_completed(GuideStep.CONFIG_API.value)
            UserGuideRepository.create(guide)
            return True

        guide.current_step = GuideStep.COMPLETED.value
        guide.is_completed = True
        guide.is_skipped = False
        guide.mark_step_completed(GuideStep.CONFIG_API.value)
        guide.updated_at = datetime.now()
        UserGuideRepository.update(guide)
        return True
    
    # ==================== 引导流程 ====================
    
    @staticmethod
    async def start_guide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """开始引导流程 - 入口点"""
        user = await UserManager.ensure_user_registered(update, context)
        
        if user is None or user.id is None:
            logger.error("start_guide: 用户信息无效")
            await GuideManager._safe_send(update, context, "❌ 无法获取用户信息，请稍后重试")
            return ConversationHandler.END
        
        user_id = user.id
        guide = UserGuideRepository.get_by_user_id(user_id)
        status = get_config_status(UserManager.get_user_config(user_id))
        
        if not guide:
            # 创建新引导记录
            guide = UserGuide(
                user_id=user_id,
                current_step=GuideStep.WELCOME.value,
                completed_steps="[]",
                is_completed=False,
                is_skipped=False,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            UserGuideRepository.create(guide)
        elif guide.is_completed and status.is_ready:
            # 已完成引导，显示欢迎回来消息
            return await GuideManager._show_already_completed(update, context, user)
        elif guide.is_completed and not status.is_ready:
            guide.is_completed = False
            guide.updated_at = datetime.now()
            UserGuideRepository.update(guide)
            return await GuideManager._show_completed(update, context, user, guide)
        elif guide.is_skipped:
            if status.is_ready:
                GuideManager.mark_complete_if_ready(user_id)
                return await GuideManager._show_already_completed(update, context, user)
            if status.has_api_url:
                return await GuideManager._show_completed(update, context, user, guide)
            return await GuideManager._show_restart_prompt(update, context, user, guide)
        
        # 继续当前步骤
        return await GuideManager._continue_guide(update, context, user, guide)
    
    @staticmethod
    async def _continue_guide(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               user: User, guide: UserGuide) -> int:
        """根据当前步骤继续引导"""
        if user.id is not None:
            status = get_config_status(UserManager.get_user_config(user.id))
            if status.is_ready:
                GuideManager.mark_complete_if_ready(user.id)
                return await GuideManager._show_completed(update, context, user, guide)
            if status.has_api_url:
                return await GuideManager._show_completed(update, context, user, guide)

        step = guide.current_step
        
        if step == GuideStep.WELCOME.value:
            return await GuideManager._show_welcome(update, context, user, guide)
        elif step == GuideStep.CONFIG_API.value:
            return await GuideManager._show_config_api(update, context, user, guide)
        elif step == GuideStep.COMPLETED.value:
            return await GuideManager._show_completed(update, context, user, guide)
        else:
            # 兼容旧步骤（INTRO_FEATURES, CONFIG_PASSWORD等），跳转到配置API
            guide.current_step = GuideStep.CONFIG_API.value
            guide.updated_at = datetime.now()
            UserGuideRepository.update(guide)
            return await GuideManager._show_config_api(update, context, user, guide)
    
    @staticmethod
    async def _show_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                            user: User, guide: UserGuide) -> int:
        """显示欢迎页面"""
        safe_name = html.escape(user.first_name or "用户")
        
        text = f"""<b>👋 欢迎使用 Y2A-Auto Bot，{safe_name}！</b>

本机器人可将 YouTube 链接自动转发到您的 Y2A-Auto 服务。

<b>📋 快速配置需要 2 步</b>
1. 设置 Y2A-Auto API 地址，让 Bot 知道任务提交到哪里
2. 设置 Telegram Bot API Token，让主服务只授权 Bot 提交上传任务

<b>💡 提示</b>
• 配置完成后，直接发送 YouTube 链接即可转发
• 支持视频和播放列表链接
• Token 只具备提交上传任务权限，不会使用 Web 登录密码"""
        
        await GuideManager._safe_send(update, context, text, GuideManager._welcome_markup())
        return GuideState.WELCOME
    
    @staticmethod
    async def _show_config_api(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                user: User, guide: UserGuide) -> int:
        """显示配置API页面"""
        # 更新当前步骤
        if guide.current_step != GuideStep.CONFIG_API.value:
            guide.current_step = GuideStep.CONFIG_API.value
            guide.updated_at = datetime.now()
            UserGuideRepository.update(guide)
        
        text = """<b>⚙️ 配置 Y2A-Auto API 地址</b>

请发送您的 Y2A-Auto 服务地址。

<b>📝 示例</b>
<code>https://y2a.example.com</code>
<code>http://192.168.1.100:5000</code>
<code>localhost:5000</code>

<b>💡 提示</b>
• 只需输入主机和端口，路径会自动补全
• 支持 http 和 https 协议
• 如果 Bot 和 Y2A-Auto 不在同一台机器，请填写 Bot 能访问到的地址
• 下一步还需要配置专用 API Token"""
        
        await GuideManager._safe_send(update, context, text, GuideManager._config_api_markup())
        return GuideState.CONFIG_API
    
    @staticmethod
    async def _show_completed(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               user: User, guide: UserGuide) -> int:
        """显示完成页面"""
        status = get_config_status(UserManager.get_user_config(user.id)) if user.id is not None else get_config_status(None)

        if not status.is_ready:
            if status.has_api_url:
                text = f"""<b>✅ API 地址已保存</b>

当前地址：<code>{html.escape(status.api_url)}</code>

<b>下一步：设置 API Token</b>
请在 Y2A-Auto Web 设置页生成 Telegram Bot API Token，然后回到这里粘贴完整 Token。

Token 格式以 <code>y2a_tgbot_v1_</code> 开头，只授予 Bot 提交上传任务的权限。"""
            else:
                text = """<b>配置尚未完成</b>

第一步需要先设置 Y2A-Auto API 地址。"""

            await GuideManager._safe_send(
                update,
                context,
                text,
                GuideManager._next_step_markup(status.next_action),
            )
            return ConversationHandler.END

        if user.id is not None:
            GuideManager.mark_complete_if_ready(user.id)

        text = """<b>🎉 配置完成！</b>

现在您可以直接发送 YouTube 链接，机器人会自动转发到您的 Y2A-Auto 服务。

<b>建议先做一次连接测试</b>
测试会检查 API 地址是否可达，以及 API Token 是否有效。"""
        
        await GuideManager._safe_send(update, context, text, GuideManager._complete_markup())
        return ConversationHandler.END
    
    @staticmethod
    async def _show_already_completed(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                       user: User) -> int:
        """显示已完成引导的提示"""
        from src.database.repository import UserStatsRepository
        
        user_id = user.id
        status = get_config_status(UserManager.get_user_config(user_id)) if user_id else get_config_status(None)
        if not status.is_ready:
            guide = UserGuideRepository.get_by_user_id(user_id) if user_id else None
            if guide:
                guide.is_completed = False
                guide.updated_at = datetime.now()
                UserGuideRepository.update(guide)
            return await GuideManager._show_completed(update, context, user, guide or UserGuide(user_id=user_id))

        stats = UserStatsRepository.get_by_user_id(user_id) if user_id else None
        
        total = stats.total_forwards if stats else 0
        rate = f"{stats.success_rate:.1f}%" if stats and stats.total_forwards > 0 else "—"
        
        text = f"""<b>👋 欢迎回来，{html.escape(user.first_name or '用户')}！</b>

配置已就绪，可以直接发送 YouTube 链接进行转发。

<b>📊 使用统计</b>
• 总转发：{total} 次
• 成功率：{rate}"""
        
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔬 测试连接", callback_data="main:test_connection")],
            [
                InlineKeyboardButton("🎯 发送示例", callback_data="main:send_example"),
                InlineKeyboardButton("⚙️ 设置", callback_data="main:settings"),
            ],
            [InlineKeyboardButton("❓ 帮助", callback_data="main:help")],
        ])
        
        await GuideManager._safe_send(update, context, text, markup)
        return ConversationHandler.END
    
    @staticmethod
    async def _show_restart_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                    user: User, guide: UserGuide) -> int:
        """显示重新开始引导的提示"""
        text = """<b>👋 欢迎回来！</b>

您之前跳过了引导流程。

<b>🔧 您可以选择</b>
• 继续按步骤完成配置
• 直接进入设置菜单手动配置"""
        
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 重新开始", callback_data="guide:restart")],
            [
                InlineKeyboardButton("⚙️ 直接设置", callback_data="main:settings"),
                InlineKeyboardButton("❓ 帮助", callback_data="main:help"),
            ],
        ])
        
        await GuideManager._safe_send(update, context, text, markup)
        return GuideState.WELCOME
    
    # ==================== 回调处理 ====================
    
    @staticmethod
    async def guide_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理引导相关的回调按钮。"""
        query = update.callback_query
        if not query:
            return ConversationHandler.END

        action = query.data or ""
        action_labels = {
            "guide:start_config": "开始配置...",
            "guide:skip": "稍后配置...",
            "guide:restart": "继续配置...",
        }
        await query.answer(action_labels.get(action, "处理中..."))

        user = await UserManager.ensure_user_registered(update, context)
        if not user or user.id is None:
            await GuideManager._safe_send(update, context, "❌ 用户信息无效")
            return ConversationHandler.END

        guide = UserGuideRepository.get_by_user_id(user.id)
        if not guide:
            guide = UserGuide(
                user_id=user.id,
                current_step=GuideStep.WELCOME.value,
                completed_steps="[]",
                is_completed=False,
                is_skipped=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            UserGuideRepository.create(guide)

        if action in ("guide:start_config", "guide:restart"):
            guide.current_step = GuideStep.CONFIG_API.value
            guide.completed_steps = guide.completed_steps or "[]"
            guide.is_completed = False
            guide.is_skipped = False
            guide.updated_at = datetime.now()
            UserGuideRepository.update(guide)
            return await GuideManager._show_config_api(update, context, user, guide)

        if action == "guide:skip":
            guide.is_skipped = True
            guide.updated_at = datetime.now()
            UserGuideRepository.update(guide)

            text = """<b>⏭️ 已选择稍后配置</b>

需要使用时，请打开设置菜单继续配置 API 地址和 API Token。"""
            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ 立即设置", callback_data="main:settings")],
                [InlineKeyboardButton("❓ 帮助", callback_data="main:help")],
            ])

            await GuideManager._safe_send(update, context, text, markup)
            return ConversationHandler.END

        return GuideState.WELCOME
    
    # ==================== 输入处理 ====================
    
    @staticmethod
    async def handle_api_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理API地址输入"""
        message = update.message
        if not message or not message.text:
            return GuideState.CONFIG_API
        
        user = await UserManager.ensure_user_registered(update, context)
        if not user or user.id is None:
            await GuideManager._safe_send(update, context, "❌ 用户信息无效")
            return ConversationHandler.END
        
        user_id = user.id
        guide = UserGuideRepository.get_by_user_id(user_id)
        
        if not guide:
            await GuideManager._safe_send(update, context, "❌ 引导记录不存在，请使用 /start 重新开始")
            return ConversationHandler.END
        
        api_url = message.text.strip()
        
        if not api_url:
            await message.reply_text("❌ API 地址不能为空，请重新输入")
            return GuideState.CONFIG_API
        
        # 规范化URL
        from src.managers.forward_manager import ForwardManager
        if not (api_url.startswith('http://') or api_url.startswith('https://')):
            api_url = 'https://' + api_url
        api_url = ForwardManager.normalize_api_url(api_url)
        
        # 保存配置
        success = UserManager.save_user_config(user_id, api_url, None)
        
        if not success:
            await message.reply_text("❌ 保存配置失败，请稍后重试")
            return GuideState.CONFIG_API

        guide.mark_step_completed(GuideStep.CONFIG_API.value)
        guide.is_completed = False
        guide.is_skipped = False
        guide.updated_at = datetime.now()
        UserGuideRepository.update(guide)

        status = get_config_status(UserManager.get_user_config(user_id))
        if status.is_ready:
            GuideManager.mark_complete_if_ready(user_id)
            return await GuideManager._show_completed(update, context, user, guide)

        text = f"""<b>✅ API 地址已保存</b>

API 地址：<code>{html.escape(api_url)}</code>

<b>下一步：设置 API Token</b>
请在 Y2A-Auto Web 设置页生成 Telegram Bot API Token，然后点击下方按钮粘贴到这里。

<b>为什么需要 Token？</b>
Bot 不再使用您的 Web 登录密码。专用 Token 只允许提交上传任务，权限更小，也可以随时在主服务撤销。"""

        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔐 设置 API Token", callback_data="settings:set_api_token")],
            [
                InlineKeyboardButton("🔧 修改地址", callback_data="settings:set_api"),
                InlineKeyboardButton("❓ 帮助", callback_data="main:help"),
            ],
        ])

        await message.reply_text(text, reply_markup=markup, parse_mode='HTML')
        return ConversationHandler.END
    
    @staticmethod
    async def handle_password_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理旧流程输入 - 重定向到设置"""
        message = update.message
        if message:
            await message.reply_text(
                "💡 现在请通过设置菜单配置专用 API Token。点击 /settings 后选择“设置 API Token”。",
                parse_mode='HTML'
            )
        return ConversationHandler.END
    
    # ==================== 命令处理 ====================
    
    @staticmethod
    async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理 /skip 命令"""
        user = await UserManager.ensure_user_registered(update, context)
        if not user or user.id is None:
            return ConversationHandler.END
        
        guide = UserGuideRepository.get_by_user_id(user.id)
        if guide:
            guide.is_skipped = True
            guide.updated_at = datetime.now()
            UserGuideRepository.update(guide)
        
        message = update.message
        if message:
            await message.reply_text(
                "⏭️ 已跳过引导。\n\n需要使用时，请发送 /settings 继续配置 API 地址和 API Token。"
            )
        return ConversationHandler.END
    
    @staticmethod
    async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理 /cancel 命令"""
        message = update.message
        if message:
            await message.reply_text("已取消引导。发送 /start 可以继续配置。")
        return ConversationHandler.END
    
    # ==================== 兼容方法 ====================
    
    @staticmethod
    async def continue_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """兼容旧的 /continue 命令 - 重定向到start"""
        return await GuideManager.start_guide(update, context)
    
    @staticmethod
    async def reconfig_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """兼容旧的 /reconfig 命令 - 重定向到设置"""
        from src.managers.settings_manager import SettingsManager
        return await SettingsManager.settings_command(update, context)
    
    # ==================== 对话处理器 ====================
    
    @staticmethod
    def get_conversation_handler() -> ConversationHandler:
        """获取引导对话处理器"""
        return ConversationHandler(
            entry_points=[CommandHandler("start", GuideManager.start_guide)],
            states={
                GuideState.WELCOME: [
                    CallbackQueryHandler(GuideManager.guide_callback, pattern=r"^guide:"),
                    CommandHandler("skip", GuideManager.skip_command),
                    CommandHandler("cancel", GuideManager.cancel_command),
                ],
                GuideState.CONFIG_API: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, GuideManager.handle_api_input),
                    CallbackQueryHandler(GuideManager.guide_callback, pattern=r"^guide:"),
                    CommandHandler("skip", GuideManager.skip_command),
                    CommandHandler("cancel", GuideManager.cancel_command),
                ],
            },
            fallbacks=[
                CommandHandler("skip", GuideManager.skip_command),
                CommandHandler("cancel", GuideManager.cancel_command),
            ],
            per_message=False,
        )
