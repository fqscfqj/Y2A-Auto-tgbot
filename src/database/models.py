from dataclasses import dataclass
from datetime import datetime
from typing import Optional

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