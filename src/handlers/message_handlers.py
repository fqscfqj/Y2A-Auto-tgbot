import logging

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

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
            await update.message.reply_text("❌ 处理消息时出错，请稍后重试")
    
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