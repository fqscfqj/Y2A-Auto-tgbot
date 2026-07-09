"""
引导管理器 - 简化版

流程：欢迎 → 配置API → 完成
API Token 配置移至设置菜单
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

logger = logging.getLogger(__name__)


class GuideState:
    """引导状态常量（简化版）"""
    WELCOME = 1
    CONFIG_API = 2


class GuideManager:
    """引导管理器
    
    简化的引导流程：
    1. 欢迎页面 - 介绍功能，提供开始配置按钮
    2. 配置API - 输入Y2A-Auto API地址
    3. 完成 - 配置成功，可以开始使用
    
    API Token 配置在设置菜单中完成。
    """
    
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
            [InlineKeyboardButton("⏭️ 稍后配置", callback_data="guide:skip")],
        ])
    
    @staticmethod
    def _complete_markup() -> InlineKeyboardMarkup:
        """完成页面按钮"""
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎯 发送示例", callback_data="main:send_example"),
                InlineKeyboardButton("⚙️ 设置", callback_data="main:settings"),
            ],
            [InlineKeyboardButton("❓ 帮助", callback_data="main:help")],
        ])
    
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
        elif guide.is_completed:
            # 已完成引导，显示欢迎回来消息
            return await GuideManager._show_already_completed(update, context, user)
        elif guide.is_skipped:
            # 之前跳过引导，询问是否重新开始
            return await GuideManager._show_restart_prompt(update, context, user, guide)
        
        # 继续当前步骤
        return await GuideManager._continue_guide(update, context, user, guide)
    
    @staticmethod
    async def _continue_guide(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               user: User, guide: UserGuide) -> int:
        """根据当前步骤继续引导"""
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

<b>📋 快速配置</b>
只需设置您的 Y2A-Auto API 地址即可开始使用。

<b>💡 提示</b>
• 配置完成后，直接发送 YouTube 链接即可转发
• 支持视频和播放列表链接
• 如需提交任务，请在设置中配置专用 API Token"""
        
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
• 配置完成后，请在设置中添加专用 API Token"""
        
        await GuideManager._safe_send(update, context, text, GuideManager._config_api_markup())
        return GuideState.CONFIG_API
    
    @staticmethod
    async def _show_completed(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               user: User, guide: UserGuide) -> int:
        """显示完成页面"""
        text = """<b>🎉 配置完成！</b>

现在您可以直接发送 YouTube 链接，机器人会自动转发到您的 Y2A-Auto 服务。

<b>🔧 后续操作</b>
• 发送链接 - 直接粘贴 YouTube 链接即可
• 设置 - 修改配置、添加 API Token、测试连接
• 帮助 - 查看详细使用说明"""
        
        await GuideManager._safe_send(update, context, text, GuideManager._complete_markup())
        return ConversationHandler.END
    
    @staticmethod
    async def _show_already_completed(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                       user: User) -> int:
        """显示已完成引导的提示"""
        from src.database.repository import UserStatsRepository
        
        user_id = user.id
        stats = UserStatsRepository.get_by_user_id(user_id) if user_id else None
        
        total = stats.total_forwards if stats else 0
        rate = f"{stats.success_rate:.1f}%" if stats and stats.total_forwards > 0 else "—"
        
        text = f"""<b>👋 欢迎回来，{html.escape(user.first_name or '用户')}！</b>

您已完成配置，可以直接发送 YouTube 链接进行转发。

<b>📊 使用统计</b>
• 总转发：{total} 次
• 成功率：{rate}"""
        
        markup = InlineKeyboardMarkup([
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
• 重新开始引导配置
• 直接进入设置进行配置"""
        
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
        """处理引导相关的回调按钮"""
        query = update.callback_query
        if not query:
            return ConversationHandler.END
        
        action = query.data or ""
        
        # 根据操作类型提供有意义的回调应答
        action_labels = {
            "guide:start_config": "开始配置...",
            "guide:skip": "跳过引导...",
            "guide:restart": "重新开始引导...",
        }
        answer_text = action_labels.get(action, "处理中...")
        await query.answer(answer_text)
        
        user = await UserManager.ensure_user_registered(update, context)
        if not user or user.id is None:
            await GuideManager._safe_send(update, context, "❌ 用户信息无效")
            return ConversationHandler.END
        
        user_id = user.id
        guide = UserGuideRepository.get_by_user_id(user_id)
        
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
        
        if action == "guide:start_config":
            # 开始配置 - 进入API配置步骤
            guide.current_step = GuideStep.CONFIG_API.value
            guide.updated_at = datetime.now()
            UserGuideRepository.update(guide)
            return await GuideManager._show_config_api(update, context, user, guide)
        
        elif action == "guide:skip":
            # 跳过引导
            guide.is_skipped = True
            guide.updated_at = datetime.now()
            UserGuideRepository.update(guide)
            
            text = """<b>⏭️ 已跳过引导</b>

您可以随时使用以下方式进行配置：
• /settings - 打开设置菜单
• /start - 重新开始引导"""
            
            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ 立即设置", callback_data="main:settings")],
            ])
            
            await GuideManager._safe_send(update, context, text, markup)
            return ConversationHandler.END
        
        elif action == "guide:restart":
            # 重新开始引导
            guide.current_step = GuideStep.WELCOME.value
            guide.completed_steps = "[]"
            guide.is_completed = False
            guide.is_skipped = False
            guide.updated_at = datetime.now()
            UserGuideRepository.update(guide)
            return await GuideManager._show_welcome(update, context, user, guide)
        
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
        
        if success:
            # 标记引导完成
            guide.current_step = GuideStep.COMPLETED.value
            guide.is_completed = True
            guide.mark_step_completed(GuideStep.CONFIG_API.value)
            guide.updated_at = datetime.now()
            UserGuideRepository.update(guide)
            
            # 显示成功消息并提供后续选项
            text = f"""<b>✅ 配置成功！</b>

API 地址：<code>{html.escape(api_url)}</code>

现在您可以直接发送 YouTube 链接进行转发。

<b>💡 建议</b>
• 点击"测试连接"验证配置是否正确
• 请继续在设置中添加专用 API Token"""
            
            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔬 测试连接", callback_data="test_connection")],
                [
                    InlineKeyboardButton("🎯 发送示例", callback_data="main:send_example"),
                    InlineKeyboardButton("⚙️ 更多设置", callback_data="main:settings"),
                ],
            ])
            
            await message.reply_text(text, reply_markup=markup, parse_mode='HTML')
            return ConversationHandler.END
        else:
            await message.reply_text("❌ 保存配置失败，请稍后重试")
            return GuideState.CONFIG_API
    
    @staticmethod
    async def handle_password_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理旧流程输入 - 重定向到设置"""
        message = update.message
        if message:
            await message.reply_text(
                "💡 API Token 配置已移至设置菜单。请完成引导后在设置中添加专用 API Token。",
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
                "⏭️ 已跳过引导。\n\n使用 /settings 进行配置，或 /start 重新开始引导。"
            )
        return ConversationHandler.END
    
    @staticmethod
    async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理 /cancel 命令"""
        message = update.message
        if message:
            await message.reply_text("❌ 引导已取消。使用 /start 重新开始。")
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
