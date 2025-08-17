import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.database.db import execute_query, execute_update, execute_insert
from src.database.models import User, UserConfig, ForwardRecord, UserStats, UserGuide

logger = logging.getLogger(__name__)

class UserRepository:
    """用户数据访问层"""
    
    @staticmethod
    def get_by_telegram_id(telegram_id: int) -> Optional[User]:
        """通过Telegram ID获取用户"""
        query = "SELECT * FROM users WHERE telegram_id = ?"
        results = execute_query(query, (telegram_id,))
        
        if results:
            return User.from_dict(results[0])
        return None
    
    @staticmethod
    def get_by_id(user_id: int) -> Optional[User]:
        """通过用户ID获取用户"""
        query = "SELECT * FROM users WHERE id = ?"
        results = execute_query(query, (user_id,))
        
        if results:
            return User.from_dict(results[0])
        return None
    
    @staticmethod
    def get_all(active_only: bool = True) -> List[User]:
        """获取所有用户"""
        if active_only:
            query = "SELECT * FROM users WHERE is_active = 1 ORDER BY created_at DESC"
        else:
            query = "SELECT * FROM users ORDER BY created_at DESC"
        
        results = execute_query(query)
        return [User.from_dict(row) for row in results]
    
    @staticmethod
    def create(user: User) -> int:
        """创建新用户"""
        query = """
        INSERT INTO users (telegram_id, username, first_name, last_name, is_active, created_at, last_activity)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        now = datetime.now()
        params = (
            user.telegram_id,
            user.username,
            user.first_name,
            user.last_name,
            user.is_active,
            now,
            now
        )
        
        user_id = execute_insert(query, params)
        return user_id
    
    @staticmethod
    def update(user: User) -> bool:
        """更新用户信息"""
        query = """
        UPDATE users SET
            username = ?,
            first_name = ?,
            last_name = ?,
            is_active = ?,
            last_activity = ?
        WHERE id = ?
        """
        params = (
            user.username,
            user.first_name,
            user.last_name,
            user.is_active,
            user.last_activity,
            user.id
        )
        
        rows_affected = execute_update(query, params)
        return rows_affected > 0
    
    @staticmethod
    def update_last_activity(telegram_id: int) -> bool:
        """更新用户最后活动时间"""
        query = "UPDATE users SET last_activity = ? WHERE telegram_id = ?"
        params = (datetime.now(), telegram_id)
        
        rows_affected = execute_update(query, params)
        return rows_affected > 0

class UserConfigRepository:
    """用户配置数据访问层"""
    
    @staticmethod
    def get_by_user_id(user_id: int) -> Optional[UserConfig]:
        """通过用户ID获取配置"""
        query = "SELECT * FROM user_configs WHERE user_id = ?"
        results = execute_query(query, (user_id,))
        
        if results:
            return UserConfig.from_dict(results[0])
        return None
    
    @staticmethod
    def create(config: UserConfig) -> int:
        """创建用户配置"""
        query = """
        INSERT INTO user_configs (user_id, y2a_api_url, y2a_password, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """
        now = datetime.now()
        params = (
            config.user_id,
            config.y2a_api_url,
            config.y2a_password,
            now,
            now
        )
        
        config_id = execute_insert(query, params)
        return config_id
    
    @staticmethod
    def update(config: UserConfig) -> bool:
        """更新用户配置"""
        query = """
        UPDATE user_configs SET
            y2a_api_url = ?,
            y2a_password = ?,
            updated_at = ?
        WHERE id = ?
        """
        params = (
            config.y2a_api_url,
            config.y2a_password,
            datetime.now(),
            config.id
        )
        
        rows_affected = execute_update(query, params)
        return rows_affected > 0
    
    @staticmethod
    def update_by_user_id(user_id: int, y2a_api_url: str, y2a_password: Optional[str] = None) -> bool:
        """通过用户ID更新配置"""
        query = """
        UPDATE user_configs SET
            y2a_api_url = ?,
            y2a_password = ?,
            updated_at = ?
        WHERE user_id = ?
        """
        params = (
            y2a_api_url,
            y2a_password,
            datetime.now(),
            user_id
        )
        
        rows_affected = execute_update(query, params)
        return rows_affected > 0
    
    @staticmethod
    def delete_by_user_id(user_id: int) -> bool:
        """删除用户配置"""
        query = "DELETE FROM user_configs WHERE user_id = ?"
        rows_affected = execute_update(query, (user_id,))
        return rows_affected > 0

class ForwardRecordRepository:
    """转发记录数据访问层"""
    
    @staticmethod
    def create(record: ForwardRecord) -> int:
        """创建转发记录"""
        query = """
        INSERT INTO forward_records (user_id, youtube_url, status, response_message, created_at)
        VALUES (?, ?, ?, ?, ?)
        """
        params = (
            record.user_id,
            record.youtube_url,
            record.status,
            record.response_message,
            datetime.now()
        )
        
        record_id = execute_insert(query, params)
        return record_id
    
    @staticmethod
    def get_by_user_id(user_id: int, limit: int = 50) -> List[ForwardRecord]:
        """获取用户的转发记录"""
        query = "SELECT * FROM forward_records WHERE user_id = ? ORDER BY created_at DESC LIMIT ?"
        results = execute_query(query, (user_id, limit))
        return [ForwardRecord.from_dict(row) for row in results]
    
    @staticmethod
    def get_recent_by_user_id(user_id: int, days: int = 7) -> List[ForwardRecord]:
        """获取用户最近几天的转发记录"""
        query = """
        SELECT * FROM forward_records 
        WHERE user_id = ? AND created_at >= datetime('now', '-{} days')
        ORDER BY created_at DESC
        """.format(days)
        results = execute_query(query, (user_id,))
        return [ForwardRecord.from_dict(row) for row in results]

class UserStatsRepository:
    """用户统计数据访问层"""
    
    @staticmethod
    def get_by_user_id(user_id: int) -> Optional[UserStats]:
        """通过用户ID获取统计信息"""
        query = "SELECT * FROM user_stats WHERE user_id = ?"
        results = execute_query(query, (user_id,))
        
        if results:
            return UserStats.from_dict(results[0])
        return None
    
    @staticmethod
    def create(stats: UserStats) -> int:
        """创建用户统计"""
        query = """
        INSERT INTO user_stats (user_id, total_forwards, successful_forwards, failed_forwards, 
                              last_forward_date, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        now = datetime.now()
        params = (
            stats.user_id,
            stats.total_forwards,
            stats.successful_forwards,
            stats.failed_forwards,
            stats.last_forward_date,
            now,
            now
        )
        
        stats_id = execute_insert(query, params)
        return stats_id
    
    @staticmethod
    def update(stats: UserStats) -> bool:
        """更新用户统计"""
        query = """
        UPDATE user_stats SET
            total_forwards = ?,
            successful_forwards = ?,
            failed_forwards = ?,
            last_forward_date = ?,
            updated_at = ?
        WHERE id = ?
        """
        params = (
            stats.total_forwards,
            stats.successful_forwards,
            stats.failed_forwards,
            stats.last_forward_date,
            datetime.now(),
            stats.id
        )
        
        rows_affected = execute_update(query, params)
        return rows_affected > 0
    
    @staticmethod
    def increment_stats(user_id: int, is_successful: bool) -> bool:
        """增加用户统计"""
        # 首先检查是否存在统计记录
        stats = UserStatsRepository.get_by_user_id(user_id)
        
        if not stats:
            # 如果不存在，创建新的统计记录
            new_stats = UserStats(
                user_id=user_id,
                total_forwards=1,
                successful_forwards=1 if is_successful else 0,
                failed_forwards=0 if is_successful else 1,
                last_forward_date=datetime.now()
            )
            UserStatsRepository.create(new_stats)
            return True
        
        # 更新现有统计
        stats.total_forwards += 1
        if is_successful:
            stats.successful_forwards += 1
        else:
            stats.failed_forwards += 1
        stats.last_forward_date = datetime.now()
        
        return UserStatsRepository.update(stats)
    
    @staticmethod
    def get_all_stats() -> List[UserStats]:
        """获取所有用户统计"""
        query = "SELECT * FROM user_stats ORDER BY updated_at DESC"
        results = execute_query(query)
        return [UserStats.from_dict(row) for row in results]

class UserGuideRepository:
    """用户引导数据访问层"""
    
    @staticmethod
    def get_by_user_id(user_id: int) -> Optional[UserGuide]:
        """通过用户ID获取引导信息"""
        query = "SELECT * FROM user_guides WHERE user_id = ?"
        results = execute_query(query, (user_id,))
        
        if results:
            return UserGuide.from_dict(results[0])
        return None
    
    @staticmethod
    def create(guide: UserGuide) -> int:
        """创建用户引导记录"""
        query = """
        INSERT INTO user_guides (user_id, current_step, completed_steps, is_completed, is_skipped, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        now = datetime.now()
        params = (
            guide.user_id,
            guide.current_step,
            guide.completed_steps,
            guide.is_completed,
            guide.is_skipped,
            now,
            now
        )
        
        guide_id = execute_insert(query, params)
        return guide_id
    
    @staticmethod
    def update(guide: UserGuide) -> bool:
        """更新用户引导信息"""
        query = """
        UPDATE user_guides SET
            current_step = ?,
            completed_steps = ?,
            is_completed = ?,
            is_skipped = ?,
            updated_at = ?
        WHERE id = ?
        """
        params = (
            guide.current_step,
            guide.completed_steps,
            guide.is_completed,
            guide.is_skipped,
            datetime.now(),
            guide.id
        )
        
        rows_affected = execute_update(query, params)
        return rows_affected > 0
    
    @staticmethod
    def update_by_user_id(user_id: int, current_step: Optional[str] = None, completed_steps: Optional[str] = None,
                         is_completed: Optional[bool] = None, is_skipped: Optional[bool] = None) -> bool:
        """通过用户ID更新引导信息"""
        # 构建动态更新语句
        update_fields = []
        params = []
        
        if current_step is not None:
            update_fields.append("current_step = ?")
            params.append(current_step)
        
        if completed_steps is not None:
            update_fields.append("completed_steps = ?")
            params.append(completed_steps)
        
        if is_completed is not None:
            update_fields.append("is_completed = ?")
            params.append(is_completed)
        
        if is_skipped is not None:
            update_fields.append("is_skipped = ?")
            params.append(is_skipped)
        
        if not update_fields:
            return False
        
        # 添加更新时间和用户ID参数
        update_fields.append("updated_at = ?")
        params.append(datetime.now())
        params.append(user_id)
        
        query = f"UPDATE user_guides SET {', '.join(update_fields)} WHERE user_id = ?"
        
        rows_affected = execute_update(query, tuple(params))
        return rows_affected > 0
    
    @staticmethod
    def get_users_by_step(step: str) -> List[UserGuide]:
        """获取特定步骤的用户"""
        query = "SELECT * FROM user_guides WHERE current_step = ? AND is_completed = 0 AND is_skipped = 0"
        results = execute_query(query, (step,))
        return [UserGuide.from_dict(row) for row in results]
    
    @staticmethod
    def get_incomplete_guides(limit: int = 50) -> List[UserGuide]:
        """获取未完成引导的用户"""
        query = """
        SELECT * FROM user_guides
        WHERE is_completed = 0 AND is_skipped = 0
        ORDER BY created_at DESC
        LIMIT ?
        """
        results = execute_query(query, (limit,))
        return [UserGuide.from_dict(row) for row in results]