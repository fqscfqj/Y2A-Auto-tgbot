import os
import logging
from typing import List, Dict, Any, Optional

from src.database.models import User, UserConfig, UserStats
from src.database.repository import UserRepository, UserConfigRepository, UserStatsRepository

logger = logging.getLogger(__name__)

class AdminManager:
    """管理员管理器，负责管理员权限验证和管理员功能"""
    
    # 缓存管理员ID列表，避免每次都解析环境变量
    _admin_ids: Optional[List[int]] = None
    
    @classmethod
    def _get_admin_ids(cls) -> List[int]:
        """获取管理员ID列表（缓存）"""
        if cls._admin_ids is None:
            admin_ids_str = os.getenv('ADMIN_TELEGRAM_IDS', '')
            if not admin_ids_str:
                logger.warning("未设置管理员ID列表")
                cls._admin_ids = []
            else:
                try:
                    # 将字符串转换为整数列表
                    cls._admin_ids = [int(id_str.strip()) for id_str in admin_ids_str.split(',') if id_str.strip()]
                except ValueError as e:
                    logger.error(f"管理员ID列表格式错误: {e}")
                    cls._admin_ids = []
        return cls._admin_ids
    
    @staticmethod
    def is_admin(telegram_id: int) -> bool:
        """检查用户是否为管理员"""
        admin_ids = AdminManager._get_admin_ids()
        return telegram_id in admin_ids
    
    @staticmethod
    def get_all_users() -> List[User]:
        """获取所有用户"""
        return UserRepository.get_all()
    
    @staticmethod
    def get_user_with_config_and_stats(telegram_id: int) -> Dict[str, Any]:
        """获取用户及其配置和统计信息"""
        user = UserRepository.get_by_telegram_id(telegram_id)
        if not user:
            return {}
        
        config = UserConfigRepository.get_by_user_id(user.id) if user.id is not None else None
        stats = UserStatsRepository.get_by_user_id(user.id) if user.id is not None else None
        
        return {
            'user': user,
            'config': config,
            'stats': stats
        }
    
    @staticmethod
    def get_all_users_with_config_and_stats() -> List[Dict[str, Any]]:
        """获取所有用户及其配置和统计信息（优化：批量查询）"""
        users = UserRepository.get_all()
        
        # 批量获取所有配置和统计信息
        user_ids = [user.id for user in users if user.id is not None]
        
        # 使用批量查询方法，避免N+1查询问题
        configs_map = UserConfigRepository.get_by_user_ids(user_ids)
        stats_map = UserStatsRepository.get_by_user_ids(user_ids)
        
        # 组装结果
        result = []
        for user in users:
            result.append({
                'user': user,
                'config': configs_map.get(user.id) if user.id is not None else None,
                'stats': stats_map.get(user.id) if user.id is not None else None
            })
        
        return result
    
    @staticmethod
    def get_system_stats() -> Dict[str, Any]:
        """获取系统统计信息（优化：使用批量查询）"""
        users = UserRepository.get_all()
        stats_list = UserStatsRepository.get_all_stats()
        
        total_users = len(users)
        active_users = sum(1 for u in users if u.is_active)
        
        # 统计转发数据
        total_forwards = sum(stats.total_forwards for stats in stats_list)
        successful_forwards = sum(stats.successful_forwards for stats in stats_list)
        failed_forwards = sum(stats.failed_forwards for stats in stats_list)
        
        # 批量获取配置，计算已配置用户数
        user_ids = [user.id for user in users if user.id is not None]
        configs_map = UserConfigRepository.get_by_user_ids(user_ids)
        configured_users = sum(1 for config in configs_map.values() if config.y2a_api_url)
        
        # 计算成功率
        success_rate = 0
        if total_forwards > 0:
            success_rate = (successful_forwards / total_forwards) * 100
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'configured_users': configured_users,
            'total_forwards': total_forwards,
            'successful_forwards': successful_forwards,
            'failed_forwards': failed_forwards,
            'success_rate': round(success_rate, 2)
        }
    
    @staticmethod
    def format_user_list(users_data: List[Dict[str, Any]]) -> str:
        """格式化用户列表"""
        if not users_data:
            return "没有找到用户"
        
        lines = [f"用户列表 (共 {len(users_data)} 个用户):\n"]
        
        for i, data in enumerate(users_data, 1):
            user = data['user']
            config = data['config']
            stats = data['stats']
            
            user_lines = [
                f"{i}. 用户ID: {user.telegram_id}",
                f"   用户名: @{user.username if user.username else '未设置'}",
                f"   姓名: {user.first_name or ''} {user.last_name or ''}",
                f"   状态: {'活跃' if user.is_active else '禁用'}",
            ]
            
            if config:
                user_lines.append("   Y2A-Auto: 已配置")
            else:
                user_lines.append("   Y2A-Auto: 未配置")
            
            if stats:
                user_lines.append(f"   转发次数: {stats.total_forwards}")
                user_lines.append(f"   成功率: {stats.success_rate:.1f}%")
            
            user_lines.append(f"   最后活动: {user.last_activity.strftime('%Y-%m-%d %H:%M:%S') if user.last_activity else '未知'}")
            user_lines.append("")  # Empty line between users
            
            lines.extend(user_lines)
        
        return "\n".join(lines)
    
    @staticmethod
    def format_system_stats(stats: Dict[str, Any]) -> str:
        """格式化系统统计信息"""
        lines = [
            "系统统计信息:\n",
            f"总用户数: {stats['total_users']}",
            f"活跃用户数: {stats['active_users']}",
            f"已配置用户数: {stats['configured_users']}\n",
            f"总转发次数: {stats['total_forwards']}",
            f"成功转发: {stats['successful_forwards']}",
            f"失败转发: {stats['failed_forwards']}",
            f"成功率: {stats['success_rate']}%",
        ]
        return "\n".join(lines)
    
    @staticmethod
    def format_user_detail(user_data: Dict[str, Any]) -> str:
        """格式化用户详细信息"""
        if not user_data:
            return "未找到用户信息"
        
        user = user_data['user']
        config = user_data['config']
        stats = user_data['stats']
        
        lines = [
            "用户详细信息:\n",
            f"用户ID: {user.telegram_id}",
            f"用户名: @{user.username if user.username else '未设置'}",
            f"姓名: {user.first_name or ''} {user.last_name or ''}",
            f"状态: {'活跃' if user.is_active else '禁用'}",
            f"注册时间: {user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else '未知'}",
            f"最后活动: {user.last_activity.strftime('%Y-%m-%d %H:%M:%S') if user.last_activity else '未知'}\n",
        ]
        
        if config:
            lines.extend([
                "Y2A-Auto配置:",
                f"API地址: {config.y2a_api_url}",
                f"密码: {'已设置' if config.y2a_password else '未设置'}",
                f"配置时间: {config.created_at.strftime('%Y-%m-%d %H:%M:%S') if config.created_at else '未知'}",
                f"最后更新: {config.updated_at.strftime('%Y-%m-%d %H:%M:%S') if config.updated_at else '未知'}\n",
            ])
        else:
            lines.append("Y2A-Auto配置: 未配置\n")
        
        if stats:
            lines.extend([
                "使用统计:",
                f"总转发次数: {stats.total_forwards}",
                f"成功转发: {stats.successful_forwards}",
                f"失败转发: {stats.failed_forwards}",
                f"成功率: {stats.success_rate:.1f}%",
                f"最后转发: {stats.last_forward_date.strftime('%Y-%m-%d %H:%M:%S') if stats.last_forward_date else '从未'}",
            ])
        else:
            lines.append("使用统计: 无数据")
        
        return "\n".join(lines)