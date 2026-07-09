import logging
from typing import Dict, Any

from telegram import Update
from telegram.ext import ContextTypes

from src.managers.user_manager import UserManager
from src.managers.admin_manager import AdminManager
from src.managers.settings_manager import SettingsManager
from src.managers.forward_manager import ForwardManager
from src.managers.guide_manager import GuideManager

logger = logging.getLogger(__name__)

HELP_TEXT = """
<b>🤖 Y2A-Auto Telegram Bot</b>

将 YouTube 链接自动转发到您的 Y2A-Auto 服务。

<b>📋 第一次使用</b>
1. 使用 /settings 设置 Y2A-Auto API 地址
2. 在 Y2A-Auto Web 设置页生成 Telegram Bot API Token
3. 回到 Bot 中设置 API Token
4. 测试连接后，直接发送 YouTube 链接即可转发

<b>🔐 关于 API Token</b>
Token 格式以 <code>y2a_tgbot_v1_</code> 开头，只授予 Bot 提交上传任务权限，不使用 Web 登录密码。

<b>🔧 常用命令</b>
• /start — 开始使用 / 查看状态
• /settings — 配置服务
• /help — 显示帮助

<b>💡 支持的链接</b>
• 视频：youtube.com/watch?v=... 或 youtu.be/...
• 播放列表：youtube.com/playlist?list=...

直接发送链接即可，无需任何命令！
"""

class CommandHandlers:
    """命令处理器类"""
    
    @staticmethod
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理/start命令"""
        await GuideManager.start_guide(update, context)
    
    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理/help命令"""
        await UserManager.ensure_user_registered(update, context)
        from src.managers.forward_manager import ForwardManager
        effective_message = update.effective_message
        if effective_message is None:
            logger.error("help_command: effective_message is None")
            return
        await effective_message.reply_text(HELP_TEXT, reply_markup=ForwardManager.main_menu_markup(include_example=True))
    
    @staticmethod
    async def admin_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理/admin_users命令"""
        user = await UserManager.ensure_user_registered(update, context)
        effective_message = update.effective_message
        if effective_message is None:
            logger.error("admin_users_command: effective_message is None")
            return
        # 检查管理员权限（确保 telegram_id 非 None）
        if user.telegram_id is None:
            await effective_message.reply_text("❌ 用户信息不完整，无法判断权限")
            return
        if not AdminManager.is_admin(int(user.telegram_id)):
            await effective_message.reply_text("❌ 您没有权限执行此命令")
            return

        # 获取所有用户信息
        users_data = AdminManager.get_all_users_with_config_and_stats()

        # 格式化并发送用户列表
        user_list_text = AdminManager.format_user_list(users_data)
        await effective_message.reply_text(user_list_text)
    
    @staticmethod
    async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理/admin_stats命令"""
        user = await UserManager.ensure_user_registered(update, context)
        effective_message = update.effective_message
        if effective_message is None:
            logger.error("admin_stats_command: effective_message is None")
            return
        # 检查管理员权限（确保 telegram_id 非 None）
        if user.telegram_id is None:
            await effective_message.reply_text("❌ 用户信息不完整，无法判断权限")
            return
        if not AdminManager.is_admin(int(user.telegram_id)):
            await effective_message.reply_text("❌ 您没有权限执行此命令")
            return

        # 获取系统统计信息
        stats = AdminManager.get_system_stats()

        # 格式化并发送统计信息
        stats_text = AdminManager.format_system_stats(stats)
        await effective_message.reply_text(stats_text)
    
    @staticmethod
    async def admin_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理/admin_user命令"""
        user = await UserManager.ensure_user_registered(update, context)
        effective_message = update.effective_message
        if effective_message is None:
            logger.error("admin_user_command: effective_message is None")
            return
        # 检查管理员权限（确保 telegram_id 非 None）
        if user.telegram_id is None:
            await effective_message.reply_text("❌ 用户信息不完整，无法判断权限")
            return
        if not AdminManager.is_admin(int(user.telegram_id)):
            await effective_message.reply_text("❌ 您没有权限执行此命令")
            return
        
        # 检查是否提供了用户ID参数
        if not context.args:
            await effective_message.reply_text("❌ 请提供用户ID，例如：/admin_user 123456789")
            return
        
        try:
            # 尝试解析用户ID
            target_user_id = int(context.args[0])
            
            # 获取用户信息
            user_data = AdminManager.get_user_with_config_and_stats(target_user_id)
            
            if not user_data:
                await effective_message.reply_text("❌ 未找到指定用户")
                return
            
            # 格式化并发送用户详细信息
            user_detail_text = AdminManager.format_user_detail(user_data)
            await effective_message.reply_text(user_detail_text)
            
        except ValueError:
            await effective_message.reply_text("❌ 用户ID必须是数字")
        except Exception as e:
            logger.error(f"处理/admin_user命令时出错: {e}")
            await effective_message.reply_text("❌ 处理命令时出错")
    
    @staticmethod
    async def clear_reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """清除历史 ForceReply 提示。
        使用方法：对那条“请在此输入 API 地址：”的消息进行回复，并发送 /clear_reply。
        机器人会尝试删除被回复的那条消息，从而清理输入框的固定回复提示。
        """
        await UserManager.ensure_user_registered(update, context)
        # 使用 effective_message 作为回退，避免 update.message 可能为 None
        msg = update.message or update.effective_message
        if msg is None:
            logger.error("clear_reply_command: no message available to operate on")
            return
        target = getattr(msg, "reply_to_message", None)

        if target and getattr(target.from_user, "is_bot", False):
            try:
                # 使用 msg.chat.id 确保静态类型检查通过
                await context.bot.delete_message(chat_id=msg.chat.id, message_id=target.message_id)
                await msg.reply_text("✅ 已清除强制回复提示。若仍看到提示，请关闭并重新打开聊天试试。")
                return
            except Exception as e:
                logger.error(f"清除 ForceReply 失败: {e}")
                # 继续给出指导
        await msg.reply_text(
            "ℹ️ 请先对那条提示消息进行“回复”，再发送 /clear_reply，我才能删除它。"
        )
    
    @staticmethod
    def get_command_handlers() -> Dict[str, Any]:
        """获取所有命令处理器"""
        return {
            'start': CommandHandlers.start_command,
            'help': CommandHandlers.help_command,
            'clear_reply': CommandHandlers.clear_reply_command,
            'admin_users': CommandHandlers.admin_users_command,
            'admin_stats': CommandHandlers.admin_stats_command,
            'admin_user': CommandHandlers.admin_user_command,
        }
    
    @staticmethod
    def get_settings_conversation_handler():
        """获取设置菜单的对话处理器"""
        return SettingsManager.get_conversation_handler()
    
    @staticmethod
    def get_guide_conversation_handler():
        """获取引导菜单的对话处理器"""
        return GuideManager.get_conversation_handler()