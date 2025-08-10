import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from src.managers.user_manager import UserManager
from src.managers.settings_manager import SettingsManager
from src.database.models import User, UserGuide, GuideStep
from src.database.repository import UserGuideRepository

logger = logging.getLogger(__name__)

# 引导菜单状态
class GuideState(Enum):
    WELCOME = 1
    INTRO_FEATURES = 2
    CONFIG_API = 3
    CONFIG_PASSWORD = 4
    TEST_CONNECTION = 5
    SEND_EXAMPLE = 6
    COMPLETED = 7

class GuideManager:
    """引导管理器，负责处理用户引导流程"""
    
    # 示例YouTube链接
    EXAMPLE_YOUTUBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    @staticmethod
    async def start_guide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """开始引导流程"""
        user = await UserManager.ensure_user_registered(update, context)
        
        # 检查是否已有引导记录
        guide = UserGuideRepository.get_by_user_id(user.id)
        
        if not guide:
            # 创建新的引导记录
            guide = UserGuide(
                user_id=user.id,
                current_step=GuideStep.WELCOME.value,
                completed_steps="[]",
                is_completed=False,
                is_skipped=False,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            UserGuideRepository.create(guide)
        elif guide.is_completed:
            await update.message.reply_text("您已经完成了引导流程！如需重新配置，请使用 /settings 命令。")
            return ConversationHandler.END
        elif guide.is_skipped:
            await update.message.reply_text("您之前跳过了引导流程。现在重新开始引导吗？")
            keyboard = [
                [InlineKeyboardButton("重新开始", callback_data="restart_guide")],
                [InlineKeyboardButton("取消", callback_data="cancel_guide")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("请选择：", reply_markup=reply_markup)
            return GuideState.WELCOME
        
        # 根据当前步骤继续引导
        return await GuideManager._continue_guide(update, context, user, guide)
    
    @staticmethod
    async def _continue_guide(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, guide: UserGuide) -> int:
        """根据当前步骤继续引导"""
        current_step = guide.current_step
        
        if current_step == GuideStep.WELCOME.value:
            return await GuideManager._show_welcome(update, context, user, guide)
        elif current_step == GuideStep.INTRO_FEATURES.value:
            return await GuideManager._show_intro_features(update, context, user, guide)
        elif current_step == GuideStep.CONFIG_API.value:
            return await GuideManager._config_api(update, context, user, guide)
        elif current_step == GuideStep.CONFIG_PASSWORD.value:
            return await GuideManager._config_password(update, context, user, guide)
        elif current_step == GuideStep.TEST_CONNECTION.value:
            return await GuideManager._test_connection(update, context, user, guide)
        elif current_step == GuideStep.SEND_EXAMPLE.value:
            return await GuideManager._send_example(update, context, user, guide)
        elif current_step == GuideStep.COMPLETED.value:
            return await GuideManager._complete_guide(update, context, user, guide)
        else:
            # 未知步骤，重置为欢迎步骤
            guide.current_step = GuideStep.WELCOME.value
            UserGuideRepository.update(guide)
            return await GuideManager._show_welcome(update, context, user, guide)
    
    @staticmethod
    async def _show_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, guide: UserGuide) -> int:
        """显示欢迎步骤"""
        welcome_text = f"""
<b>👋 欢迎使用 Y2A-Auto Telegram Bot，{user.first_name}！</b>

本机器人可将 <b>YouTube</b> 链接自动转发到您的 <b>Y2A-Auto</b> 服务。

🚀 接下来将带您完成快速配置，仅需几分钟。

提示：随时可发送 /skip 跳过引导，或 /cancel 取消。
"""
        keyboard = [
            [InlineKeyboardButton("➡️ 继续", callback_data="next_step")],
            [InlineKeyboardButton("❓ 帮助", callback_data="main:help")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(welcome_text, reply_markup=reply_markup)
        
        return GuideState.WELCOME
    
    @staticmethod
    async def _show_intro_features(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, guide: UserGuide) -> int:
        """显示功能介绍步骤"""
        intro_text = """
<b>🤖 功能一览</b>
• 自动转发 YouTube 链接到 Y2A-Auto
• 支持视频 / 播放列表
• 自动处理认证
• 记录转发历史与统计

<b>📋 使用流程</b>
1) 设置 Y2A-Auto API 地址
2) （可选）设置密码
3) 测试连接
4) 发送链接自动转发
"""
        keyboard = [
            [InlineKeyboardButton("➡️ 继续", callback_data="next_step")],
            [InlineKeyboardButton("❓ 帮助", callback_data="main:help")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(intro_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(intro_text, reply_markup=reply_markup)
        
        return GuideState.INTRO_FEATURES
    
    @staticmethod
    async def _config_api(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, guide: UserGuide) -> int:
        """配置API地址步骤"""
        # 确保引导记录中的当前步骤同步为 CONFIG_API，
        # 以便通用消息处理可兜底识别并路由到此步骤的输入处理。
        if guide.current_step != GuideStep.CONFIG_API.value:
            guide.current_step = GuideStep.CONFIG_API.value
            guide.updated_at = datetime.now()
            UserGuideRepository.update(guide)
        config_text = """
<b>⚙️ 配置 Y2A-Auto API 地址</b>
示例：
• <code>https://y2a.example.com:4443</code>
• <code>http://localhost:5000</code>
• <code>http://192.168.1.100:5000</code>

提示：只需提供主机(可含端口)，系统会自动补全为 <code>/tasks/add_via_extension</code>。

请直接发送地址，或发送 /skip 跳过。
"""
        
        if update.callback_query:
            await update.callback_query.edit_message_text(config_text)
        else:
            await update.message.reply_text(config_text)
        
        return GuideState.CONFIG_API
    
    @staticmethod
    async def _config_password(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, guide: UserGuide) -> int:
        """配置密码步骤"""
        # 同步步骤为 CONFIG_PASSWORD，保证兜底逻辑可识别
        if guide.current_step != GuideStep.CONFIG_PASSWORD.value:
            guide.current_step = GuideStep.CONFIG_PASSWORD.value
            guide.updated_at = datetime.now()
            UserGuideRepository.update(guide)
        password_text = """
<b>🔐 配置密码（可选）</b>
如果您的 Y2A-Auto 服务设置了访问密码，请在此输入。
若无需密码，发送 /skip 跳过。

请输入密码：
"""
        
        if update.callback_query:
            await update.callback_query.edit_message_text(password_text)
        else:
            await update.message.reply_text(password_text)
        
        return GuideState.CONFIG_PASSWORD
    
    @staticmethod
    async def _test_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, guide: UserGuide) -> int:
        """测试连接步骤"""
        # 获取用户配置
        config = UserManager.get_user_config(user.id)
        
        if not config or not config.y2a_api_url:
            await update.message.reply_text("❌ 未找到有效的配置，请重新配置API地址。")
            return await GuideManager._config_api(update, context, user, guide)
        
        # 发送测试中消息
        if update.callback_query:
            await update.callback_query.edit_message_text("🔄 正在测试连接...")
        else:
            await update.message.reply_text("🔄 正在测试连接...")
        
        # 测试连接
        from src.managers.forward_manager import ForwardManager
        result = await ForwardManager.test_connection(update, context, user, config)
        
        test_text = f"""
<b>🔌 连接测试结果</b>

{result}

若失败，请检查配置，或点击下方按钮重新配置。
"""
        keyboard = [
            [InlineKeyboardButton("➡️ 继续", callback_data="next_step"), InlineKeyboardButton("🔁 重新配置", callback_data="reconfig")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(test_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(test_text, reply_markup=reply_markup)
        
        return GuideState.TEST_CONNECTION
    
    @staticmethod
    async def _send_example(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, guide: UserGuide) -> int:
        """发送示例链接步骤"""
        example_text = f"""
<b>🎯 最后一步：发送示例链接</b>
现在您可以发送 YouTube 链接进行转发了。也可点击下方按钮发送示例：

示例：{GuideManager.EXAMPLE_YOUTUBE_URL}
"""
        keyboard = [
            [InlineKeyboardButton("🎯 发送示例", callback_data="main:send_example")],
            [InlineKeyboardButton("✅ 完成引导", callback_data="complete_guide")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(example_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(example_text, reply_markup=reply_markup)
        
        return GuideState.SEND_EXAMPLE
    
    @staticmethod
    async def _complete_guide(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, guide: UserGuide) -> int:
        """完成引导"""
        complete_text = """
<b>🎉 引导完成</b>
现在您可以：
• 直接发送 YouTube 链接进行转发
• 点击下方按钮修改配置或查看帮助
"""
        keyboard = [
            [InlineKeyboardButton("⚙️ 设置", callback_data="main:settings"), InlineKeyboardButton("❓ 帮助", callback_data="main:help")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(complete_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(complete_text, reply_markup=reply_markup)
        
        # 更新引导状态为已完成
        guide.is_completed = True
        guide.current_step = GuideStep.COMPLETED.value
        guide.updated_at = datetime.now()
        UserGuideRepository.update(guide)
        
        return ConversationHandler.END
    
    @staticmethod
    async def guide_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理引导菜单的回调查询"""
        query = update.callback_query
        await query.answer()
        
        user = await UserManager.ensure_user_registered(update, context)
        guide = UserGuideRepository.get_by_user_id(user.id)
        
        if not guide:
            await query.edit_message_text("❌ 引导记录不存在，请使用 /start 重新开始")
            return ConversationHandler.END
        
        action = query.data
        
        if action == "next_step":
            # 标记当前步骤为已完成
            guide.mark_step_completed(guide.current_step)
            
            # 获取下一步骤
            next_step = guide.get_next_step()
            if next_step:
                guide.current_step = next_step
                UserGuideRepository.update(guide)
                return await GuideManager._continue_guide(update, context, user, guide)
            else:
                return await GuideManager._complete_guide(update, context, user, guide)
        
        elif action == "skip_guide":
            # 跳过整个引导
            guide.is_skipped = True
            guide.updated_at = datetime.now()
            UserGuideRepository.update(guide)
            
            await query.edit_message_text("已跳过引导流程。您可以使用 /settings 命令进行配置，或使用 /start 重新开始引导。")
            return ConversationHandler.END
        
        elif action == "skip_step":
            # 跳过当前步骤
            guide.mark_step_completed(guide.current_step)
            
            # 获取下一步骤
            next_step = guide.get_next_step()
            if next_step:
                guide.current_step = next_step
                UserGuideRepository.update(guide)
                return await GuideManager._continue_guide(update, context, user, guide)
            else:
                return await GuideManager._complete_guide(update, context, user, guide)
        
        elif action == "restart_guide":
            # 重新开始引导
            guide.current_step = GuideStep.WELCOME.value
            guide.completed_steps = "[]"
            guide.is_completed = False
            guide.is_skipped = False
            guide.updated_at = datetime.now()
            UserGuideRepository.update(guide)
            
            return await GuideManager._show_welcome(update, context, user, guide)
        
        elif action == "reconfig":
            # 重新配置
            guide.current_step = GuideStep.CONFIG_API.value
            UserGuideRepository.update(guide)
            
            return await GuideManager._config_api(update, context, user, guide)
        
        elif action == "send_example":
            # 发送示例链接
            from src.managers.forward_manager import ForwardManager
            
            # 模拟用户发送消息
            context.user_data['example_sent'] = True
            await ForwardManager.forward_youtube_url(update, context, GuideManager.EXAMPLE_YOUTUBE_URL)
            
            # 等待一段时间后显示完成消息
            import asyncio
            await asyncio.sleep(2)
            
            complete_text = """
✅ 示例链接已发送！

现在您已经了解了如何使用本机器人。直接发送YouTube链接即可自动转发。

🎉 引导流程已完成！感谢您的使用。
"""
            await update.message.reply_text(complete_text)
            
            # 更新引导状态为已完成
            guide.is_completed = True
            guide.current_step = GuideStep.COMPLETED.value
            guide.updated_at = datetime.now()
            UserGuideRepository.update(guide)
            
            return ConversationHandler.END
        
        elif action == "complete_guide":
            # 直接完成引导
            return await GuideManager._complete_guide(update, context, user, guide)
        
        elif action == "cancel_guide":
            # 取消引导
            await query.edit_message_text("引导已取消。您可以使用 /start 重新开始引导。")
            return ConversationHandler.END
        
        return GuideState.WELCOME
    
    @staticmethod
    async def handle_api_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理API地址输入"""
        user = await UserManager.ensure_user_registered(update, context)
        guide = UserGuideRepository.get_by_user_id(user.id)
        
        if not guide:
            await update.message.reply_text("❌ 引导记录不存在，请使用 /start 重新开始")
            return ConversationHandler.END
        
        api_url = update.message.text.strip()

        if not api_url:
            await update.message.reply_text("API地址不能为空，请重新输入")
            return GuideState.CONFIG_API

        # 与设置菜单逻辑保持一致：
        # - 允许只输入主机(可含端口)，默认补 https://
        # - 统一规范化为 /tasks/add_via_extension
        from src.managers.forward_manager import ForwardManager
        if not (api_url.startswith('http://') or api_url.startswith('https://')):
            api_url = 'https://' + api_url
        api_url = ForwardManager.normalize_api_url(api_url)
        
        # 获取现有配置
        config = UserManager.get_user_config(user.id)
        password = config.y2a_password if config else None
        
        # 保存配置
        success = UserManager.save_user_config(user.id, api_url, password)
        
        if success:
            await update.message.reply_text(f"✅ API地址已设置为: {api_url}")
            
            # 标记当前步骤为已完成
            guide.mark_step_completed(guide.current_step)
            
            # 获取下一步骤
            next_step = guide.get_next_step()
            if next_step:
                guide.current_step = next_step
                UserGuideRepository.update(guide)
                return await GuideManager._continue_guide(update, context, user, guide)
            else:
                return await GuideManager._complete_guide(update, context, user, guide)
        else:
            await update.message.reply_text("❌ 设置API地址失败，请稍后重试")
            return GuideState.CONFIG_API
    
    @staticmethod
    async def handle_password_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理密码输入"""
        user = await UserManager.ensure_user_registered(update, context)
        guide = UserGuideRepository.get_by_user_id(user.id)
        
        if not guide:
            await update.message.reply_text("❌ 引导记录不存在，请使用 /start 重新开始")
            return ConversationHandler.END
        
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
            
            # 标记当前步骤为已完成
            guide.mark_step_completed(guide.current_step)
            
            # 获取下一步骤
            next_step = guide.get_next_step()
            if next_step:
                guide.current_step = next_step
                UserGuideRepository.update(guide)
                return await GuideManager._continue_guide(update, context, user, guide)
            else:
                return await GuideManager._complete_guide(update, context, user, guide)
        else:
            await update.message.reply_text("❌ 设置密码失败，请稍后重试")
            return GuideState.CONFIG_PASSWORD
    
    @staticmethod
    async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """跳过引导"""
        user = await UserManager.ensure_user_registered(update, context)
        guide = UserGuideRepository.get_by_user_id(user.id)
        
        if guide:
            guide.is_skipped = True
            guide.updated_at = datetime.now()
            UserGuideRepository.update(guide)
        
        await update.message.reply_text("已跳过引导流程。您可以使用 /settings 命令进行配置。")
        return ConversationHandler.END
    
    @staticmethod
    async def continue_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """继续引导下一步"""
        user = await UserManager.ensure_user_registered(update, context)
        guide = UserGuideRepository.get_by_user_id(user.id)
        
        if not guide:
            await update.message.reply_text("❌ 引导记录不存在，请使用 /start 重新开始")
            return ConversationHandler.END
        
        # 标记当前步骤为已完成
        guide.mark_step_completed(guide.current_step)
        
        # 获取下一步骤
        next_step = guide.get_next_step()
        if next_step:
            guide.current_step = next_step
            UserGuideRepository.update(guide)
            return await GuideManager._continue_guide(update, context, user, guide)
        else:
            return await GuideManager._complete_guide(update, context, user, guide)
    
    @staticmethod
    async def reconfig_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """重新配置"""
        user = await UserManager.ensure_user_registered(update, context)
        guide = UserGuideRepository.get_by_user_id(user.id)
        
        if not guide:
            await update.message.reply_text("❌ 引导记录不存在，请使用 /start 重新开始")
            return ConversationHandler.END
        
        # 重新配置
        guide.current_step = GuideStep.CONFIG_API.value
        UserGuideRepository.update(guide)
        
        return await GuideManager._config_api(update, context, user, guide)
    
    @staticmethod
    async def send_example_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """发送示例链接"""
        user = await UserManager.ensure_user_registered(update, context)
        guide = UserGuideRepository.get_by_user_id(user.id)
        
        if not guide:
            await update.message.reply_text("❌ 引导记录不存在，请使用 /start 重新开始")
            return ConversationHandler.END
        
        # 发送示例链接
        from src.managers.forward_manager import ForwardManager
        
        # 模拟用户发送消息
        context.user_data['example_sent'] = True
        await ForwardManager.forward_youtube_url(update, context, GuideManager.EXAMPLE_YOUTUBE_URL)
        
        # 等待一段时间后显示完成消息
        import asyncio
        await asyncio.sleep(2)
        
        complete_text = """
✅ 示例链接已发送！

现在您已经了解了如何使用本机器人。直接发送YouTube链接即可自动转发。

🎉 引导流程已完成！感谢您的使用。
"""
        await update.message.reply_text(complete_text)
        
        # 更新引导状态为已完成
        guide.is_completed = True
        guide.current_step = GuideStep.COMPLETED.value
        guide.updated_at = datetime.now()
        UserGuideRepository.update(guide)
        
        return ConversationHandler.END
    
    @staticmethod
    async def complete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """直接完成引导"""
        user = await UserManager.ensure_user_registered(update, context)
        guide = UserGuideRepository.get_by_user_id(user.id)
        
        if not guide:
            await update.message.reply_text("❌ 引导记录不存在，请使用 /start 重新开始")
            return ConversationHandler.END
        
        return await GuideManager._complete_guide(update, context, user, guide)
    
    @staticmethod
    async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """取消引导"""
        await update.message.reply_text("引导已取消。您可以使用 /start 重新开始引导。")
        return ConversationHandler.END
    
    @staticmethod
    def get_conversation_handler() -> ConversationHandler:
        """获取引导菜单的对话处理器"""
        return ConversationHandler(
            entry_points=[CommandHandler("start", GuideManager.start_guide)],
            states={
                GuideState.WELCOME: [
                    CommandHandler("continue", GuideManager.continue_command),
                    CommandHandler("skip", GuideManager.skip_command),
                    CommandHandler("cancel", GuideManager.cancel_command)
                ],
                GuideState.INTRO_FEATURES: [
                    CommandHandler("continue", GuideManager.continue_command),
                    CommandHandler("skip", GuideManager.skip_command),
                    CommandHandler("cancel", GuideManager.cancel_command)
                ],
                GuideState.CONFIG_API: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, GuideManager.handle_api_input),
                    CommandHandler("skip", GuideManager.skip_command),
                    CommandHandler("cancel", GuideManager.cancel_command)
                ],
                GuideState.CONFIG_PASSWORD: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, GuideManager.handle_password_input),
                    CommandHandler("skip", GuideManager.skip_command),
                    CommandHandler("cancel", GuideManager.cancel_command)
                ],
                GuideState.TEST_CONNECTION: [
                    CommandHandler("continue", GuideManager.continue_command),
                    CommandHandler("reconfig", GuideManager.reconfig_command),
                    CommandHandler("cancel", GuideManager.cancel_command)
                ],
                GuideState.SEND_EXAMPLE: [
                    CommandHandler("send_example", GuideManager.send_example_command),
                    CommandHandler("complete", GuideManager.complete_command),
                    CommandHandler("cancel", GuideManager.cancel_command)
                ],
                GuideState.COMPLETED: [
                    CommandHandler("cancel", GuideManager.cancel_command)
                ]
            },
            fallbacks=[
                CommandHandler("skip", GuideManager.skip_command),
                CommandHandler("cancel", GuideManager.cancel_command)
            ],
            per_message=False
        )