#!/usr/bin/env python3
"""
Y2A-Auto Telegram Bot - 多用户版本
主应用入口
"""
import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from telegram.ext import Application, CommandHandler, ConversationHandler, CallbackQueryHandler, Defaults
from telegram.constants import ParseMode
from config import Config
from src.database.db import init_database
from src.database.migration_manager import MigrationManager
from src.handlers.command_handlers import CommandHandlers
from src.handlers.message_handlers import MessageHandlers
from src.utils.memory_monitor import init_memory_monitor, memory_monitor

# 配置日志
logger = logging.getLogger(__name__)

def main():
    """主函数，启动Telegram Bot"""
    try:
        # 验证配置
        if not Config.validate_config():
            logger.error("配置验证失败，请检查环境变量")
            sys.exit(1)
        
        # 运行数据库迁移（包括初始化）
        logger.info("运行数据库迁移...")
        if MigrationManager.run_pending_migrations():
            logger.info("数据库迁移完成")
        else:
            logger.error("数据库迁移失败")
            sys.exit(1)
        
        # 初始化内存监控
        logger.info("初始化内存监控...")
        init_memory_monitor()
        
        # 创建Telegram应用
        logger.info("创建Telegram应用...")
        application = (
            Application
            .builder()
            .token(Config.TELEGRAM_TOKEN)
            .defaults(Defaults(parse_mode=ParseMode.HTML))
            .build()
        )
        
        # 获取命令处理器
        command_handlers = CommandHandlers.get_command_handlers()
        
        # 注册命令处理器
        for command, handler in command_handlers.items():
            application.add_handler(CommandHandler(command, handler))
        
        # 注册设置菜单对话处理器
        settings_handler = CommandHandlers.get_settings_conversation_handler()
        application.add_handler(settings_handler)
        # 注册设置菜单的通用回调（按钮化）
        from src.managers.settings_manager import SettingsManager
        settings_callback_handler = CallbackQueryHandler(
            SettingsManager.settings_callback, 
            pattern=r"^settings:"
        )
        application.add_handler(settings_callback_handler)
        
        # 注册引导对话处理器
        guide_handler = CommandHandlers.get_guide_conversation_handler()
        application.add_handler(guide_handler)
        # 注册引导相关回调（用于处理引导内按钮）
        from src.managers.guide_manager import GuideManager
        guide_callback_handler = CallbackQueryHandler(
            GuideManager.guide_callback, 
            pattern=r"^guide:"
        )
        application.add_handler(guide_callback_handler)
        
        # 注册帮助命令处理器
        help_handler = MessageHandlers.get_help_command_handler()
        application.add_handler(help_handler)
        
        # 注册开始引导命令处理器
        start_guide_handler = MessageHandlers.get_start_guide_command_handler()
        application.add_handler(start_guide_handler)
        
        # 注册直接配置命令处理器
        direct_config_handler = MessageHandlers.get_direct_config_command_handler()
        application.add_handler(direct_config_handler)
        
        # 注册通用回调处理器（主菜单/快捷操作）
        main_callback_handler = MessageHandlers.get_main_menu_callback_handler()
        application.add_handler(main_callback_handler)

        # 注册消息处理器
        message_handler = MessageHandlers.get_message_handler()
        application.add_handler(message_handler)
        
        # 启动Bot
        logger.info("启动Y2A-Auto Telegram Bot...")
        application.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭Bot...")
        # 停止内存监控
        memory_monitor.stop_monitoring()
        # 清理异步HTTP会话
        _cleanup_aiohttp_session()
    except Exception as e:
        logger.error(f"启动Bot时出错: {e}")
        sys.exit(1)


def _cleanup_aiohttp_session():
    """清理异步HTTP会话"""
    try:
        import asyncio
        from src.managers.forward_manager import cleanup_aiohttp_session
        # Create a new event loop for cleanup to ensure completion
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(cleanup_aiohttp_session())
        finally:
            loop.close()
    except Exception as e:
        logger.debug(f"清理异步HTTP会话时出错: {e}")

if __name__ == "__main__":
    main()