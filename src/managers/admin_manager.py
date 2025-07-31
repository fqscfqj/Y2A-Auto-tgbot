import os
import logging
from typing import List, Dict, Any, Optional

from src.database.models import User, UserConfig, UserStats
from src.database.repository import UserRepository, UserConfigRepository, UserStatsRepository

logger = logging.getLogger(__name__)

class AdminManager:
    """管理员管理器，负责管理员权限验证和管理员功能"""
    
    @staticmethod
    def is_admin(telegram_id: int) -> bool:
        """检查用户是否为管理员"""
        # 从环境变量获取管理员ID列表
        admin_ids_str = os.getenv('ADMIN_TELEGRAM_IDS', '')
        if not admin_ids_str:
            logger.warning("未设置管理员ID列表")
            return False
        
        try:
            # 将字符串转换为整数列表
            admin_ids = [int(id_str.strip()) for id_str in admin_ids_str.split(',')]
            return telegram_id in admin_ids
        except ValueError as e:
            logger.error(f"管理员ID列表格式错误: {e}")
            return False
    
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
        
        config = UserConfigRepository.get_by_user_id(user.id)
        stats = UserStatsRepository.get_by_user_id(user.id)
        
        return {
            'user': user,
            'config': config,
            'stats': stats
        }
    
    @staticmethod
    def get_all_users_with_config_and_stats() -> List[Dict[str, Any]]:
        """获取所有用户及其配置和统计信息"""
        users = UserRepository.get_all()
        result = []
        
        for user in users:
            config = UserConfigRepository.get_by_user_id(user.id)
            stats = UserStatsRepository.get_by_user_id(user.id)
            
            result.append({
                'user': user,
                'config': config,
                'stats': stats
            })
        
        return result
    
    @staticmethod
    def get_system_stats() -> Dict[str, Any]:
        """获取系统统计信息"""
        users = UserRepository.get_all()
        stats_list = UserStatsRepository.get_all_stats()
        
        total_users = len(users)
        active_users = len([u for u in users if u.is_active])
        configured_users = 0
        
        total_forwards = 0
        successful_forwards = 0
        failed_forwards = 0
        
        for stats in stats_list:
            total_forwards += stats.total_forwards
            successful_forwards += stats.successful_forwards
            failed_forwards += stats.failed_forwards
        
        # 计算已配置用户数
        for user in users:
            config = UserConfigRepository.get_by_user_id(user.id)
            if config and config.y2a_api_url:
                configured_users += 1
        
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
        
        result = f"用户列表 (共 {len(users_data)} 个用户):\n\n"
        
        for i, data in enumerate(users_data, 1):
            user = data['user']
            config = data['config']
            stats = data['stats']
            
            result += f"{i}. 用户ID: {user.telegram_id}\n"
            result += f"   用户名: @{user.username if user.username else '未设置'}\n"
            result += f"   姓名: {user.first_name or ''} {user.last_name or ''}\n"
            result += f"   状态: {'活跃' if user.is_active else '禁用'}\n"
            
            if config:
                result += f"   Y2A-Auto: 已配置\n"
            else:
                result += f"   Y2A-Auto: 未配置\n"
            
            if stats:
                result += f"   转发次数: {stats.total_forwards}\n"
                result += f"   成功率: {stats.success_rate:.1f}%\n"
            
            result += f"   最后活动: {user.last_activity.strftime('%Y-%m-%d %H:%M:%S') if user.last_activity else '未知'}\n\n"
        
        return result
    
    @staticmethod
    def format_system_stats(stats: Dict[str, Any]) -> str:
        """格式化系统统计信息"""
        result = "系统统计信息:\n\n"
        result += f"总用户数: {stats['total_users']}\n"
        result += f"活跃用户数: {stats['active_users']}\n"
        result += f"已配置用户数: {stats['configured_users']}\n\n"
        result += f"总转发次数: {stats['total_forwards']}\n"
        result += f"成功转发: {stats['successful_forwards']}\n"
        result += f"失败转发: {stats['failed_forwards']}\n"
        result += f"成功率: {stats['success_rate']}%\n"
        
        return result
    
    @staticmethod
    def format_user_detail(user_data: Dict[str, Any]) -> str:
        """格式化用户详细信息"""
        if not user_data:
            return "未找到用户信息"
        
        user = user_data['user']
        config = user_data['config']
        stats = user_data['stats']
        
        result = f"用户详细信息:\n\n"
        result += f"用户ID: {user.telegram_id}\n"
        result += f"用户名: @{user.username if user.username else '未设置'}\n"
        result += f"姓名: {user.first_name or ''} {user.last_name or ''}\n"
        result += f"状态: {'活跃' if user.is_active else '禁用'}\n"
        result += f"注册时间: {user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else '未知'}\n"
        result += f"最后活动: {user.last_activity.strftime('%Y-%m-%d %H:%M:%S') if user.last_activity else '未知'}\n\n"
        
        if config:
            result += f"Y2A-Auto配置:\n"
            result += f"API地址: {config.y2a_api_url}\n"
            result += f"密码: {'已设置' if config.y2a_password else '未设置'}\n"
            result += f"配置时间: {config.created_at.strftime('%Y-%m-%d %H:%M:%S') if config.created_at else '未知'}\n"
            result += f"最后更新: {config.updated_at.strftime('%Y-%m-%d %H:%M:%S') if config.updated_at else '未知'}\n\n"
        else:
            result += f"Y2A-Auto配置: 未配置\n\n"
        
        if stats:
            result += f"使用统计:\n"
            result += f"总转发次数: {stats.total_forwards}\n"
            result += f"成功转发: {stats.successful_forwards}\n"
            result += f"失败转发: {stats.failed_forwards}\n"
            result += f"成功率: {stats.success_rate:.1f}%\n"
            result += f"最后转发: {stats.last_forward_date.strftime('%Y-%m-%d %H:%M:%S') if stats.last_forward_date else '从未'}\n"
        else:
            result += f"使用统计: 无数据\n"
        
        return result