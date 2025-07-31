import logging
from typing import Dict, Any

from telegram import Update
from telegram.ext import ContextTypes

from src.managers.user_manager import UserManager
from src.managers.admin_manager import AdminManager
from src.managers.settings_manager import SettingsManager
from src.managers.forward_manager import ForwardManager

logger = logging.getLogger(__name__)

HELP_TEXT = """
🤖 Y2A-Auto Telegram Bot

本机器人用于转发YouTube链接到您配置的Y2A-Auto服务。

📋 命令列表：
/start - 机器人介绍和欢迎信息
/help - 显示帮助信息
/settings - 配置Y2A-Auto服务

🔧 管理员命令：
/admin_users - 查看所有用户列表
/admin_stats - 查看系统统计信息
/admin_user <用户ID> - 查看指定用户详细信息

💡 使用方法：
1. 首次使用请运行 /settings 配置您的Y2A-Auto服务
2. 配置完成后，直接发送YouTube链接即可自动转发
3. 支持YouTube视频和播放列表链接

❓ 如需帮助，请联系管理员。
"""

class CommandHandlers:
    """命令处理器类"""
    
    @staticmethod
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理/start命令"""
        user = await UserManager.ensure_user_registered(update, context)
        
        welcome_text = f"""
👋 欢迎使用Y2A-Auto Telegram Bot，{user.first_name}！

本机器人可以帮助您将YouTube链接自动转发到您配置的Y2A-Auto服务。

🚀 快速开始：
1. 使用 /settings 命令配置您的Y2A-Auto服务
2. 配置完成后，直接发送YouTube链接即可自动转发

💡 提示：输入 /help 查看所有可用命令
"""
        
        await update.message.reply_text(welcome_text)
    
    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理/help命令"""
        await UserManager.ensure_user_registered(update, context)
        await update.message.reply_text(HELP_TEXT)
    
    @staticmethod
    async def admin_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理/admin_users命令"""
        user = await UserManager.ensure_user_registered(update, context)
        
        # 检查管理员权限
        if not AdminManager.is_admin(user.telegram_id):
            await update.message.reply_text("❌ 您没有权限执行此命令")
            return
        
        # 获取所有用户信息
        users_data = AdminManager.get_all_users_with_config_and_stats()
        
        # 格式化并发送用户列表
        user_list_text = AdminManager.format_user_list(users_data)
        await update.message.reply_text(user_list_text)
    
    @staticmethod
    async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理/admin_stats命令"""
        user = await UserManager.ensure_user_registered(update, context)
        
        # 检查管理员权限
        if not AdminManager.is_admin(user.telegram_id):
            await update.message.reply_text("❌ 您没有权限执行此命令")
            return
        
        # 获取系统统计信息
        stats = AdminManager.get_system_stats()
        
        # 格式化并发送统计信息
        stats_text = AdminManager.format_system_stats(stats)
        await update.message.reply_text(stats_text)
    
    @staticmethod
    async def admin_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理/admin_user命令"""
        user = await UserManager.ensure_user_registered(update, context)
        
        # 检查管理员权限
        if not AdminManager.is_admin(user.telegram_id):
            await update.message.reply_text("❌ 您没有权限执行此命令")
            return
        
        # 检查是否提供了用户ID参数
        if not context.args:
            await update.message.reply_text("❌ 请提供用户ID，例如：/admin_user 123456789")
            return
        
        try:
            # 尝试解析用户ID
            target_user_id = int(context.args[0])
            
            # 获取用户信息
            user_data = AdminManager.get_user_with_config_and_stats(target_user_id)
            
            if not user_data:
                await update.message.reply_text("❌ 未找到指定用户")
                return
            
            # 格式化并发送用户详细信息
            user_detail_text = AdminManager.format_user_detail(user_data)
            await update.message.reply_text(user_detail_text)
            
        except ValueError:
            await update.message.reply_text("❌ 用户ID必须是数字")
        except Exception as e:
            logger.error(f"处理/admin_user命令时出错: {e}")
            await update.message.reply_text("❌ 处理命令时出错")
    
    @staticmethod
    def get_command_handlers() -> Dict[str, Any]:
        """获取所有命令处理器"""
        return {
            'start': CommandHandlers.start_command,
            'help': CommandHandlers.help_command,
            'admin_users': CommandHandlers.admin_users_command,
            'admin_stats': CommandHandlers.admin_stats_command,
            'admin_user': CommandHandlers.admin_user_command,
        }
    
    @staticmethod
    def get_settings_conversation_handler():
        """获取设置菜单的对话处理器"""
        return SettingsManager.get_conversation_handler()