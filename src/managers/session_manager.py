import logging
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from src.managers.user_manager import UserManager
from src.managers.admin_manager import AdminManager
from src.database.models import User

logger = logging.getLogger(__name__)


@dataclass
class UserSession:
    """用户会话数据"""
    telegram_id: int
    user_id: int
    username: str
    is_admin: bool = False
    last_activity: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    
    def update_activity(self) -> None:
        """更新最后活动时间"""
        self.last_activity = datetime.now()
    
    def is_expired(self, timeout_hours: int = 24) -> bool:
        """检查会话是否过期"""
        expiry_time = self.last_activity + timedelta(hours=timeout_hours)
        return datetime.now() > expiry_time


class SessionManager:
    """会话管理器，负责管理用户会话和权限控制"""
    
    def __init__(self):
        self._sessions: Dict[int, UserSession] = {}
        self._cleanup_interval = 300  # 5分钟清理一次过期会话 (从1小时改为5分钟)
        self._last_cleanup = time.time()
        self._max_sessions = 1000  # 最大会话数限制
        self._session_timeout_hours = 12  # 会话超时时间减少到12小时 (从24小时)
    
    def _get_field(self, obj: Any, name: str):
        """从 dict 或对象安全地读取字段（支持 attribute 或 key）。"""
        if isinstance(obj, dict):
            return obj.get(name)
        return getattr(obj, name, None)

    def get_or_create_session(self, telegram_user: Any) -> UserSession:
        """获取或创建用户会话"""
        # 首先清理过期会话
        self.cleanup_expired_sessions()
        
        telegram_id_raw = self._get_field(telegram_user, 'id')
        if telegram_id_raw is None:
            logger.error("无法获取 telegram_id，telegram_user 缺少 id 字段")
            raise ValueError("telegram_user.id is required")

        try:
            telegram_id = int(telegram_id_raw)
        except (TypeError, ValueError) as e:
            logger.error(f"无法解析 telegram_id: {telegram_id_raw!r} ({e})")
            raise ValueError("Invalid telegram_id") from e
        
        # 检查是否已有会话
        if telegram_id in self._sessions:
            session = self._sessions[telegram_id]
            session.update_activity()
            
            # 检查会话是否过期
            if session.is_expired(self._session_timeout_hours):
                logger.info(f"用户 {telegram_id} 的会话已过期，创建新会话")
                self._sessions.pop(telegram_id)
                return self._create_new_session(telegram_user)
            
            return session

        # 检查会话数是否超过限制
        if len(self._sessions) >= self._max_sessions:
            logger.warning(f"会话数达到上限 {self._max_sessions}，强制清理")
            self.cleanup_expired_sessions()
            
            # 如果清理后仍然超过限制，拒绝创建新会话
            if len(self._sessions) >= self._max_sessions:
                logger.error(f"无法创建新会话，已达到最大会话数限制 {self._max_sessions}")
                raise RuntimeError("服务器繁忙，请稍后再试")

        # 创建新会话
        return self._create_new_session(telegram_user)

    def _create_new_session(self, telegram_user: Any) -> UserSession:
        """创建新会话"""
        # 注册或更新用户
        user = UserManager.register_user(telegram_user)
        
        # 检查是否为管理员
        telegram_id_raw = self._get_field(telegram_user, 'id')
        try:
            telegram_id = int(telegram_id_raw) if telegram_id_raw is not None else None
        except (TypeError, ValueError):
            telegram_id = None

        is_admin = AdminManager.is_admin(telegram_id) if telegram_id is not None else False
        
        # 确保 user.id 不是 None
        if user.id is None:
            logger.error("创建会话失败：user.id 为 None")
            raise ValueError("user.id is required to create a session")

        # 确定 telegram_id 值（优先使用传入值，否则使用用户记录）
        if telegram_id is not None:
            telegram_id_val = telegram_id
        else:
            user_telegram_id = getattr(user, 'telegram_id', None)
            if user_telegram_id is None:
                logger.error("无法确定 telegram_id: 既未传入也不在 user 对象中")
                raise ValueError("telegram_id is required to create a session")
            # assert to help static type checkers that this is not None
            assert user_telegram_id is not None
            telegram_id_val = int(user_telegram_id)

        # 创建会话
        session = UserSession(
            telegram_id=telegram_id_val,
            user_id=int(user.id),
            username=user.username or "",
            is_admin=is_admin
        )

        self._sessions[session.telegram_id] = session
        logger.info(f"创建新会话: {session.telegram_id}, 管理员: {is_admin}")
        
        return session

    def get_session(self, telegram_id: int) -> Optional[UserSession]:
        """获取用户会话"""
        # 首先清理过期会话
        self.cleanup_expired_sessions()
        
        if telegram_id in self._sessions:
            session = self._sessions[telegram_id]
            
            # 检查会话是否过期
            if session.is_expired(self._session_timeout_hours):
                logger.info(f"用户 {telegram_id} 的会话已过期")
                self._sessions.pop(telegram_id)
                return None
            
            session.update_activity()
            return session
        
        return None

    def remove_session(self, telegram_id: int) -> bool:
        """移除用户会话"""
        if telegram_id in self._sessions:
            self._sessions.pop(telegram_id)
            logger.info(f"移除用户会话: {telegram_id}")
            return True
        return False

    def cleanup_expired_sessions(self) -> None:
        """清理过期会话"""
        current_time = time.time()
        
        # 检查是否需要清理
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        expired_sessions = []
        for telegram_id, session in list(self._sessions.items()):
            if session.is_expired(self._session_timeout_hours):
                expired_sessions.append(telegram_id)
        
        # 移除过期会话
        for telegram_id in expired_sessions:
            self._sessions.pop(telegram_id, None)
            logger.info(f"清理过期会话: {telegram_id}")
        
        # 如果会话数超过限制，移除最旧的会话
        if len(self._sessions) > self._max_sessions:
            # 按最后活动时间排序，移除最旧的会话
            sorted_sessions = sorted(
                self._sessions.items(), 
                key=lambda x: x[1].last_activity
            )
            excess_count = len(self._sessions) - self._max_sessions
            for i in range(excess_count):
                telegram_id = sorted_sessions[i][0]
                self._sessions.pop(telegram_id, None)
                logger.warning(f"清理超出限制的会话: {telegram_id}")
        
        if expired_sessions:
            logger.info(f"清理了 {len(expired_sessions)} 个过期会话")
        
        self._last_cleanup = current_time

    def get_active_sessions_count(self) -> int:
        """获取活跃会话数"""
        self.cleanup_expired_sessions()
        return len(self._sessions)

    def get_all_sessions(self) -> Dict[int, UserSession]:
        """获取所有会话"""
        self.cleanup_expired_sessions()
        return self._sessions.copy()

    def is_user_admin(self, telegram_id: int) -> bool:
        """检查用户是否为管理员"""
        session = self.get_session(telegram_id)
        if session:
            return session.is_admin
        
        # 如果没有会话，直接检查权限
        return AdminManager.is_admin(telegram_id)

    def set_session_data(self, telegram_id: int, key: str, value: Any) -> None:
        """设置会话数据"""
        session = self.get_session(telegram_id)
        if session:
            session.data[key] = value

    def get_session_data(self, telegram_id: int, key: str, default=None) -> Any:
        """获取会话数据"""
        session = self.get_session(telegram_id)
        if session and key in session.data:
            return session.data[key]
        return default

    def clear_session_data(self, telegram_id: int, key: Optional[str] = None) -> None:
        """清除会话数据"""
        session = self.get_session(telegram_id)
        if session:
            if key:
                session.data.pop(key, None)
            else:
                session.data.clear()


# 全局会话管理器实例
session_manager = SessionManager()