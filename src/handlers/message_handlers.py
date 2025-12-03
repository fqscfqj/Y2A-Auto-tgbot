import logging

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters, CallbackQueryHandler

from src.managers.forward_manager import ForwardManager

logger = logging.getLogger(__name__)

class MessageHandlers:
    """消息处理器类"""
    
    @staticmethod
    async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理文本消息"""
        try:
            await ForwardManager.handle_message(update, context)
        except Exception as e:
            logger.error(f"处理文本消息时出错: {e}")
            # update.message can be None according to type hints; check before calling reply_text
            message = update.message
            if message:
                await message.reply_text("❌ 处理消息时出错，请稍后重试")
            else:
                # 如果没有 message，记录无法回复的情况（保持原有行为的安全性）
                logger.error("无法发送错误通知：update.message 为 None")
    
    @staticmethod
    def get_message_handler() -> MessageHandler:
        """获取消息处理器"""
        return MessageHandler(filters.TEXT & ~filters.COMMAND, MessageHandlers.handle_text_message)
    
    @staticmethod
    def get_help_command_handler():
        """获取帮助命令处理器"""
        from telegram.ext import CommandHandler
        from src.managers.forward_manager import ForwardManager
        return CommandHandler("help", ForwardManager.handle_help_command)
    
    @staticmethod
    def get_start_guide_command_handler():
        """获取开始引导命令处理器"""
        from telegram.ext import CommandHandler
        from src.managers.forward_manager import ForwardManager
        return CommandHandler("start_guide", ForwardManager.handle_start_guide_command)
    
    @staticmethod
    def get_direct_config_command_handler():
        """获取直接配置命令处理器"""
        from telegram.ext import CommandHandler
        from src.managers.forward_manager import ForwardManager
        return CommandHandler("direct_config", ForwardManager.handle_direct_config_command)

    @staticmethod
    async def handle_main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理主菜单相关的回调按钮"""
        query = update.callback_query
        if query:
            await query.answer()

        # 确保用户已注册
        from src.managers.user_manager import UserManager
        await UserManager.ensure_user_registered(update, context)

        data = query.data if query else ""

        # 延迟导入以避免循环依赖
        from src.managers.forward_manager import ForwardManager
        from src.managers.settings_manager import SettingsManager
        from src.managers.guide_manager import GuideManager

        if data == "main:start":
            await GuideManager.start_guide(update, context)
        elif data == "main:settings":
            await SettingsManager.settings_command(update, context)
        elif data == "main:help":
            await ForwardManager.handle_help_command(update, context)
        elif data == "main:send_example":
            await ForwardManager.forward_youtube_url(update, context, GuideManager.EXAMPLE_YOUTUBE_URL)
        elif data == "test_connection":
            # 兼容引导完成后的测试连接按钮
            user = await UserManager.ensure_user_registered(update, context)
            if user and user.id:
                config = UserManager.get_user_config(user.id)
                if config:
                    result = await ForwardManager.test_connection(update, context, user, config)
                    message = update.effective_message
                    if message:
                        await message.reply_text(f"🔬 测试结果\n\n{result}")
        else:
            # 未识别的回调，忽略
            return

    @staticmethod
    def get_main_menu_callback_handler() -> CallbackQueryHandler:
        """获取主菜单回调处理器"""
        return CallbackQueryHandler(
            MessageHandlers.handle_main_menu_callback, 
            pattern=r"^(main:|test_connection)"
        )