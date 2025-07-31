import logging
from typing import Optional, Dict, Any
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from src.database.models import User, UserConfig
from src.database.repository import UserRepository, UserConfigRepository

logger = logging.getLogger(__name__)

class UserManager:
    """用户管理器，负责用户注册、配置管理等功能"""
    
    @staticmethod
    def register_user(telegram_user: Dict[str, Any]) -> User:
        """注册新用户或获取现有用户"""
        telegram_id = telegram_user.id
        username = telegram_user.username
        first_name = telegram_user.first_name
        last_name = telegram_user.last_name
        
        # 检查用户是否已存在
        user = UserRepository.get_by_telegram_id(telegram_id)
        
        if user:
            # 更新用户信息
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.last_activity = datetime.now()
            UserRepository.update(user)
            logger.info(f"更新用户信息: {telegram_id}")
        else:
            # 创建新用户
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                is_active=True,
                created_at=datetime.now(),
                last_activity=datetime.now()
            )
            user_id = UserRepository.create(user)
            user.id = user_id
            logger.info(f"注册新用户: {telegram_id}")
        
        return user
    
    @staticmethod
    def get_user(telegram_id: int) -> Optional[User]:
        """获取用户信息"""
        return UserRepository.get_by_telegram_id(telegram_id)
    
    @staticmethod
    def update_user_activity(telegram_id: int) -> bool:
        """更新用户最后活动时间"""
        return UserRepository.update_last_activity(telegram_id)
    
    @staticmethod
    def get_user_config(user_id: int) -> Optional[UserConfig]:
        """获取用户配置"""
        return UserConfigRepository.get_by_user_id(user_id)
    
    @staticmethod
    def has_user_config(user_id: int) -> bool:
        """检查用户是否有配置"""
        config = UserConfigRepository.get_by_user_id(user_id)
        return config is not None
    
    @staticmethod
    def save_user_config(user_id: int, y2a_api_url: str, y2a_password: str = None) -> bool:
        """保存用户配置"""
        # 检查是否已有配置
        config = UserConfigRepository.get_by_user_id(user_id)
        
        if config:
            # 更新现有配置
            return UserConfigRepository.update_by_user_id(user_id, y2a_api_url, y2a_password)
        else:
            # 创建新配置
            new_config = UserConfig(
                user_id=user_id,
                y2a_api_url=y2a_api_url,
                y2a_password=y2a_password,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            config_id = UserConfigRepository.create(new_config)
            return config_id is not None
    
    @staticmethod
    def delete_user_config(user_id: int) -> bool:
        """删除用户配置"""
        return UserConfigRepository.delete_by_user_id(user_id)
    
    @staticmethod
    def get_user_with_config(telegram_id: int) -> tuple:
        """获取用户及其配置"""
        user = UserRepository.get_by_telegram_id(telegram_id)
        if not user:
            return None, None
        
        config = UserConfigRepository.get_by_user_id(user.id)
        return user, config
    
    @staticmethod
    def is_user_configured(telegram_id: int) -> bool:
        """检查用户是否已配置Y2A-Auto"""
        user = UserRepository.get_by_telegram_id(telegram_id)
        if not user:
            return False
        
        config = UserConfigRepository.get_by_user_id(user.id)
        return config is not None and config.y2a_api_url
    
    @staticmethod
    async def ensure_user_registered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> User:
        """确保用户已注册，如果未注册则自动注册"""
        telegram_user = update.effective_user
        user = UserManager.register_user({
            'id': telegram_user.id,
            'username': telegram_user.username,
            'first_name': telegram_user.first_name,
            'last_name': telegram_user.last_name
        })
        
        # 更新用户活动时间
        UserManager.update_user_activity(telegram_user.id)
        
        return user
    
    @staticmethod
    def format_user_info(user: User, config: UserConfig = None) -> str:
        """格式化用户信息"""
        info = f"用户ID: {user.telegram_id}\n"
        info += f"用户名: @{user.username if user.username else '未设置'}\n"
        info += f"姓名: {user.first_name or ''} {user.last_name or ''}\n"
        info += f"状态: {'活跃' if user.is_active else '禁用'}\n"
        info += f"注册时间: {user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else '未知'}\n"
        info += f"最后活动: {user.last_activity.strftime('%Y-%m-%d %H:%M:%S') if user.last_activity else '未知'}\n"
        
        if config:
            info += f"\nY2A-Auto配置:\n"
            info += f"API地址: {config.y2a_api_url}\n"
            info += f"密码: {'已设置' if config.y2a_password else '未设置'}\n"
            info += f"配置时间: {config.created_at.strftime('%Y-%m-%d %H:%M:%S') if config.created_at else '未知'}\n"
        else:
            info += "\nY2A-Auto配置: 未配置"
        
        return info