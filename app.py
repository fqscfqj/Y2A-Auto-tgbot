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

from telegram.ext import Application, CommandHandler, ConversationHandler
from config import Config
from src.database.db import init_database
from src.database.migration_manager import MigrationManager
from src.handlers.command_handlers import CommandHandlers
from src.handlers.message_handlers import MessageHandlers

# 配置日志
logger = logging.getLogger(__name__)

def main():
    """主函数，启动Telegram Bot"""
    try:
        # 验证配置
        if not Config.validate_config():
            logger.error("配置验证失败，请检查环境变量")
            sys.exit(1)
        
        # 初始化数据库
        logger.info("初始化数据库...")
        init_database()
        logger.info("数据库初始化完成")
        
        # 运行数据库迁移
        logger.info("运行数据库迁移...")
        if MigrationManager.run_pending_migrations():
            logger.info("数据库迁移完成")
        else:
            logger.error("数据库迁移失败")
            sys.exit(1)
        
        # 创建Telegram应用
        logger.info("创建Telegram应用...")
        application = Application.builder().token(Config.TELEGRAM_TOKEN).build()
        
        # 获取命令处理器
        command_handlers = CommandHandlers.get_command_handlers()
        
        # 注册命令处理器
        for command, handler in command_handlers.items():
            application.add_handler(CommandHandler(command, handler))
        
        # 注册设置菜单对话处理器
        settings_handler = CommandHandlers.get_settings_conversation_handler()
        application.add_handler(settings_handler)
        
        # 注册引导对话处理器
        guide_handler = CommandHandlers.get_guide_conversation_handler()
        application.add_handler(guide_handler)
        
        # 注册配置选择回调查询处理器
        config_choice_handler = MessageHandlers.get_config_choice_callback_handler()
        application.add_handler(config_choice_handler)
        
        # 注册消息处理器
        message_handler = MessageHandlers.get_message_handler()
        application.add_handler(message_handler)
        
        # 启动Bot
        logger.info("启动Y2A-Auto Telegram Bot...")
        application.run_polling(drop_pending_updates=True)
        
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭Bot...")
    except Exception as e:
        logger.error(f"启动Bot时出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()