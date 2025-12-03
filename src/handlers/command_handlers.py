import logging
import html
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

<b>📋 使用方法</b>
1. 使用 /settings 配置 API 地址
2. 直接发送 YouTube 链接即可转发

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
        user = await UserManager.ensure_user_registered(update, context)
        safe_name = html.escape(user.first_name or "")

        # 安全地获取消息对象以避免 optional member 访问警告
        effective_message = update.effective_message
        if effective_message is None:
            logger.error("start_command: effective_message is None")
            return

        # 确保 user.id 非 None 再调用需要 int 的函数，避免将 Optional[int] 传递给类型为 int 的参数
        if user.id is None:
            await effective_message.reply_text("❌ 用户信息不完整，无法处理请求")
            return
        user_id = int(user.id)

        # 检查用户引导状态
        guide = UserManager.get_user_guide(user_id)
        
        if not guide:
            # 新用户，创建引导记录并开始引导
            guide = UserManager.ensure_user_guide(user_id)
            await GuideManager.start_guide(update, context)
            return
        elif guide.is_completed:
            # 已完成引导的用户
            from src.database.repository import UserStatsRepository
            user_stats = UserStatsRepository.get_by_user_id(user_id)

            total_forwards = user_stats.total_forwards if user_stats else 0
            success_rate = getattr(user_stats, "success_rate", None)
            success_rate_str = f"{success_rate:.1f}%" if success_rate is not None else "0%"

            welcome_text = f"""
👋 欢迎回来，{safe_name}！

您已经完成了引导配置，可以直接发送YouTube链接进行转发。

📊 您的统计信息：
• 总转发次数：{total_forwards}
• 成功率：{success_rate_str}

🔧 其他命令：
• /settings - 修改配置
• /help - 查看帮助
"""
            await effective_message.reply_text(welcome_text)
        elif guide.is_skipped:
            # 跳过引导的用户
            welcome_text = f"""
👋 欢迎回来，{safe_name}！

您之前跳过了引导流程。您可以选择：

🚀 选项：
• /start - 重新开始引导流程
• /settings - 直接进行配置
• /help - 查看帮助信息
"""
            await effective_message.reply_text(welcome_text)
        else:
            # 未完成引导的用户，继续引导
            await GuideManager._continue_guide(update, context, user, guide)
    
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