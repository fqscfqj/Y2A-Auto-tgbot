import logging
from typing import Optional, Dict, Any
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from src.database.models import User, UserConfig, UserGuide, GuideStep
from src.database.repository import UserRepository, UserConfigRepository, UserGuideRepository

logger = logging.getLogger(__name__)

class UserManager:
    """用户管理器，负责用户注册、配置管理等功能"""
    
    @staticmethod
    def register_user(telegram_user) -> User:
        """注册新用户或获取现有用户"""
        # 检查是否是字典（来自上下文）还是Telegram User对象
        if isinstance(telegram_user, dict):
            telegram_id = telegram_user.get('id')
            username = telegram_user.get('username')
            first_name = telegram_user.get('first_name')
            last_name = telegram_user.get('last_name')
        else:
            # Telegram User对象
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
        user = UserManager.register_user(telegram_user)
        
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
    
    @staticmethod
    def get_user_guide(user_id: int) -> Optional[UserGuide]:
        """获取用户引导信息"""
        return UserGuideRepository.get_by_user_id(user_id)
    
    @staticmethod
    def create_user_guide(user_id: int) -> UserGuide:
        """创建用户引导记录"""
        guide = UserGuide(
            user_id=user_id,
            current_step=GuideStep.WELCOME.value,
            completed_steps="[]",
            is_completed=False,
            is_skipped=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        guide_id = UserGuideRepository.create(guide)
        guide.id = guide_id
        return guide
    
    @staticmethod
    def update_user_guide(guide: UserGuide) -> bool:
        """更新用户引导信息"""
        return UserGuideRepository.update(guide)
    
    @staticmethod
    def is_guide_completed(user_id: int) -> bool:
        """检查用户是否已完成引导"""
        guide = UserGuideRepository.get_by_user_id(user_id)
        return guide is not None and guide.is_completed
    
    @staticmethod
    def is_guide_skipped(user_id: int) -> bool:
        """检查用户是否跳过了引导"""
        guide = UserGuideRepository.get_by_user_id(user_id)
        return guide is not None and guide.is_skipped
    
    @staticmethod
    def get_current_guide_step(user_id: int) -> Optional[str]:
        """获取用户当前引导步骤"""
        guide = UserGuideRepository.get_by_user_id(user_id)
        if guide:
            return guide.current_step
        return None
    
    @staticmethod
    def ensure_user_guide(user_id: int) -> UserGuide:
        """确保用户有引导记录，如果没有则创建"""
        guide = UserGuideRepository.get_by_user_id(user_id)
        if not guide:
            guide = UserManager.create_user_guide(user_id)
        return guide
    
    @staticmethod
    def mark_guide_step_completed(user_id: int, step: str) -> bool:
        """标记引导步骤为已完成"""
        guide = UserGuideRepository.get_by_user_id(user_id)
        if not guide:
            return False
        
        guide.mark_step_completed(step)
        return UserGuideRepository.update(guide)
    
    @staticmethod
    def advance_guide_step(user_id: int) -> Optional[str]:
        """推进引导步骤到下一步"""
        guide = UserGuideRepository.get_by_user_id(user_id)
        if not guide:
            return None
        
        # 标记当前步骤为已完成
        guide.mark_step_completed(guide.current_step)
        
        # 获取下一步骤
        next_step = guide.get_next_step()
        if next_step:
            guide.current_step = next_step
            UserGuideRepository.update(guide)
            return next_step
        elif not guide.is_completed:
            # 如果没有下一步骤且未完成，则标记为完成
            guide.is_completed = True
            guide.current_step = GuideStep.COMPLETED.value
            UserGuideRepository.update(guide)
            return GuideStep.COMPLETED.value
        
        return None
    
    @staticmethod
    def skip_user_guide(user_id: int) -> bool:
        """跳过用户引导"""
        guide = UserGuideRepository.get_by_user_id(user_id)
        if not guide:
            return False
        
        guide.is_skipped = True
        guide.updated_at = datetime.now()
        return UserGuideRepository.update(guide)
    
    @staticmethod
    def reset_user_guide(user_id: int) -> bool:
        """重置用户引导"""
        guide = UserGuideRepository.get_by_user_id(user_id)
        if not guide:
            return False
        
        guide.current_step = GuideStep.WELCOME.value
        guide.completed_steps = "[]"
        guide.is_completed = False
        guide.is_skipped = False
        guide.updated_at = datetime.now()
        return UserGuideRepository.update(guide)