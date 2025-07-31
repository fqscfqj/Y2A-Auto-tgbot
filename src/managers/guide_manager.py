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
👋 欢迎使用Y2A-Auto Telegram Bot，{user.first_name}！

本机器人可以帮助您将YouTube链接自动转发到您配置的Y2A-Auto服务。

🚀 接下来我将引导您完成简单的配置，只需几分钟时间！

💡 提示：您可以随时输入 /skip 跳过引导，或输入 /cancel 取消。

请输入 /continue 继续引导，或输入 /skip 跳过引导。
"""
        
        if update.callback_query:
            await update.callback_query.edit_message_text(welcome_text)
        else:
            await update.message.reply_text(welcome_text)
        
        return GuideState.WELCOME
    
    @staticmethod
    async def _show_intro_features(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, guide: UserGuide) -> int:
        """显示功能介绍步骤"""
        intro_text = """
🤖 Y2A-Auto Telegram Bot 功能介绍：

✨ 主要功能：
• 自动转发YouTube链接到Y2A-Auto服务
• 支持YouTube视频和播放列表链接
• 自动处理认证和连接
• 记录转发历史和统计信息

📋 使用流程：
1. 配置Y2A-Auto服务的API地址
2. （可选）设置访问密码
3. 测试连接是否正常
4. 发送YouTube链接即可自动转发

准备好了吗？让我们开始配置吧！

请输入 /continue 继续下一步，或输入 /skip 跳过引导。
"""
        
        if update.callback_query:
            await update.callback_query.edit_message_text(intro_text)
        else:
            await update.message.reply_text(intro_text)
        
        return GuideState.INTRO_FEATURES
    
    @staticmethod
    async def _config_api(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, guide: UserGuide) -> int:
        """配置API地址步骤"""
        config_text = """
⚙️ 配置Y2A-Auto API地址

请输入您的Y2A-Auto服务的API地址，例如：
• http://localhost:5000/tasks/add_via_extension
• http://192.168.1.100:5000/tasks/add_via_extension

💡 提示：这是您部署Y2A-Auto服务的地址，通常以 /tasks/add_via_extension 结尾。

请输入API地址，或输入 /skip 跳过此步骤：
"""
        
        if update.callback_query:
            await update.callback_query.edit_message_text(config_text)
        else:
            await update.message.reply_text(config_text)
        
        return GuideState.CONFIG_API
    
    @staticmethod
    async def _config_password(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, guide: UserGuide) -> int:
        """配置密码步骤"""
        password_text = """
🔐 配置Y2A-Auto密码（可选）

如果您的Y2A-Auto服务设置了访问密码，请在此输入。
如果没有设置密码，可以直接输入 /skip 跳过此步骤。

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
🔌 连接测试结果：

{result}

如果连接失败，请检查您的配置是否正确，或使用 /settings 命令重新配置。

请输入 /continue 继续下一步，或输入 /reconfig 重新配置。
"""
        
        if update.callback_query:
            await update.callback_query.edit_message_text(test_text)
        else:
            await update.message.reply_text(test_text)
        
        return GuideState.TEST_CONNECTION
    
    @staticmethod
    async def _send_example(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, guide: UserGuide) -> int:
        """发送示例链接步骤"""
        example_text = f"""
🎯 最后一步：发送示例链接

现在您可以发送YouTube链接进行转发了！让我为您演示一下：

请输入 /send_example 发送示例链接，或者您也可以自己发送一个YouTube链接。

示例链接：{GuideManager.EXAMPLE_YOUTUBE_URL}

请输入 /send_example 发送示例链接，或输入 /complete 完成引导。
"""
        
        if update.callback_query:
            await update.callback_query.edit_message_text(example_text)
        else:
            await update.message.reply_text(example_text)
        
        return GuideState.SEND_EXAMPLE
    
    @staticmethod
    async def _complete_guide(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, guide: UserGuide) -> int:
        """完成引导"""
        complete_text = """
🎉 恭喜！您已经完成了所有引导步骤！

现在您可以：
• 直接发送YouTube链接进行转发
• 使用 /settings 命令修改配置
• 使用 /help 命令查看帮助信息

感谢您使用Y2A-Auto Telegram Bot！如有问题，请联系管理员。
"""
        
        if update.callback_query:
            await update.callback_query.edit_message_text(complete_text)
        else:
            await update.message.reply_text(complete_text)
        
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
        
        # 验证API地址格式
        if not (api_url.startswith('http://') or api_url.startswith('https://')):
            await update.message.reply_text("API地址必须以http://或https://开头，请重新输入")
            return GuideState.CONFIG_API
        
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