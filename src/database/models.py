from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class GuideStep(Enum):
    """引导步骤枚举（简化版）"""
    NOT_STARTED = "not_started"         # 未开始引导
    WELCOME = "welcome"                 # 欢迎步骤
    CONFIG_API = "config_api"           # 配置API地址
    COMPLETED = "completed"             # 引导完成
    SKIPPED = "skipped"                 # 跳过引导
    # 以下保留用于兼容旧数据
    INTRO_FEATURES = "intro_features"   # (已废弃) 介绍功能
    CONFIG_PASSWORD = "config_password" # (已废弃) 配置密码
    TEST_CONNECTION = "test_connection" # (已废弃) 测试连接
    SEND_EXAMPLE = "send_example"       # (已废弃) 发送示例链接

@dataclass
class User:
    """用户模型"""
    id: Optional[int] = None
    telegram_id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """从字典创建User实例"""
        created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        last_activity = datetime.fromisoformat(data['last_activity']) if data.get('last_activity') else None
        
        return cls(
            id=data.get('id'),
            telegram_id=data.get('telegram_id'),
            username=data.get('username'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            is_active=bool(data.get('is_active', True)),
            created_at=created_at,
            last_activity=last_activity
        )
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'telegram_id': self.telegram_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None
        }

@dataclass
class UserConfig:
    """用户配置模型"""
    id: Optional[int] = None
    user_id: Optional[int] = None
    y2a_api_url: Optional[str] = None
    y2a_password: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'UserConfig':
        """从字典创建UserConfig实例"""
        created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        updated_at = datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        
        return cls(
            id=data.get('id'),
            user_id=data.get('user_id'),
            y2a_api_url=data.get('y2a_api_url'),
            y2a_password=data.get('y2a_password'),
            created_at=created_at,
            updated_at=updated_at
        )
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'y2a_api_url': self.y2a_api_url,
            'y2a_password': self.y2a_password,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

@dataclass
class ForwardRecord:
    """转发记录模型"""
    id: Optional[int] = None
    user_id: Optional[int] = None
    youtube_url: Optional[str] = None
    status: Optional[str] = None  # 'success', 'failed', 'pending'
    response_message: Optional[str] = None
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ForwardRecord':
        """从字典创建ForwardRecord实例"""
        created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        
        return cls(
            id=data.get('id'),
            user_id=data.get('user_id'),
            youtube_url=data.get('youtube_url'),
            status=data.get('status'),
            response_message=data.get('response_message'),
            created_at=created_at
        )
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'youtube_url': self.youtube_url,
            'status': self.status,
            'response_message': self.response_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

@dataclass
class UserStats:
    """用户统计模型"""
    id: Optional[int] = None
    user_id: Optional[int] = None
    total_forwards: int = 0
    successful_forwards: int = 0
    failed_forwards: int = 0
    last_forward_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'UserStats':
        """从字典创建UserStats实例"""
        last_forward_date = datetime.fromisoformat(data['last_forward_date']) if data.get('last_forward_date') else None
        created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        updated_at = datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        
        return cls(
            id=data.get('id'),
            user_id=data.get('user_id'),
            total_forwards=data.get('total_forwards', 0),
            successful_forwards=data.get('successful_forwards', 0),
            failed_forwards=data.get('failed_forwards', 0),
            last_forward_date=last_forward_date,
            created_at=created_at,
            updated_at=updated_at
        )
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'total_forwards': self.total_forwards,
            'successful_forwards': self.successful_forwards,
            'failed_forwards': self.failed_forwards,
            'last_forward_date': self.last_forward_date.isoformat() if self.last_forward_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.total_forwards == 0:
            return 0.0
        return (self.successful_forwards / self.total_forwards) * 100


@dataclass
class UserGuide:
    """用户引导模型"""
    id: Optional[int] = None
    user_id: Optional[int] = None
    current_step: Optional[str] = None  # GuideStep枚举值
    completed_steps: Optional[str] = None  # JSON格式存储已完成的步骤
    is_completed: bool = False
    is_skipped: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'UserGuide':
        """从字典创建UserGuide实例"""
        created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else None
        updated_at = datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        
        return cls(
            id=data.get('id'),
            user_id=data.get('user_id'),
            current_step=data.get('current_step'),
            completed_steps=data.get('completed_steps'),
            is_completed=bool(data.get('is_completed', False)),
            is_skipped=bool(data.get('is_skipped', False)),
            created_at=created_at,
            updated_at=updated_at
        )
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'current_step': self.current_step,
            'completed_steps': self.completed_steps,
            'is_completed': self.is_completed,
            'is_skipped': self.is_skipped,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def mark_step_completed(self, step: str) -> None:
        """标记步骤为已完成"""
        import json
        
        # 解析已完成的步骤
        completed_steps = []
        if self.completed_steps:
            try:
                completed_steps = json.loads(self.completed_steps)
            except json.JSONDecodeError:
                completed_steps = []
        
        # 添加新步骤（如果尚未完成）
        if step not in completed_steps:
            completed_steps.append(step)
            self.completed_steps = json.dumps(completed_steps)
        
        # 更新时间
        self.updated_at = datetime.now()
    
    def is_step_completed(self, step: str) -> bool:
        """检查步骤是否已完成"""
        import json
        
        if not self.completed_steps:
            return False
        
        try:
            completed_steps = json.loads(self.completed_steps)
            return step in completed_steps
        except json.JSONDecodeError:
            return False
    
    def get_next_step(self) -> Optional[str]:
        """获取下一步骤（简化版流程）"""
        if self.is_completed or self.is_skipped:
            return None
        
        # 简化的步骤顺序：欢迎 → 配置API → 完成
        step_order = [
            GuideStep.WELCOME.value,
            GuideStep.CONFIG_API.value,
        ]
        
        # 如果当前步骤为空，返回第一步
        if not self.current_step:
            return step_order[0]
        
        # 兼容旧数据：如果是旧的中间步骤，直接跳到配置API或完成
        old_steps = [GuideStep.INTRO_FEATURES.value, GuideStep.CONFIG_PASSWORD.value, 
                     GuideStep.TEST_CONNECTION.value, GuideStep.SEND_EXAMPLE.value]
        if self.current_step in old_steps:
            return GuideStep.CONFIG_API.value
        
        # 找到当前步骤在顺序中的位置
        try:
            current_index = step_order.index(self.current_step)
            if current_index < len(step_order) - 1:
                return step_order[current_index + 1]
        except ValueError:
            # 如果当前步骤不在顺序中，返回第一步
            return step_order[0]
        
        # 如果已经是最后一步，标记为完成
        self.is_completed = True
        self.current_step = GuideStep.COMPLETED.value
        self.updated_at = datetime.now()
        return None