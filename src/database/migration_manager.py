"""
数据库迁移管理器
负责运行所有待处理的数据库迁移
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Any

from src.database.db import execute_query, execute_script

logger = logging.getLogger(__name__)

class MigrationManager:
    """数据库迁移管理器"""
    
    @staticmethod
    def get_migration_files() -> List[str]:
        """获取所有迁移文件"""
        migrations_dir = Path(__file__).parent / "migrations"
        migration_files = []
        
        logger.info(f"搜索迁移文件的目录: {migrations_dir}")
        
        for file in migrations_dir.glob("*.py"):
            # 只处理以数字开头的迁移文件（如 001_initial.py, 002_add_user_guides.py）
            if file.name.startswith("__") or not file.name[0].isdigit():
                continue
            migration_files.append(file.stem)
            logger.info(f"找到迁移文件: {file.name}")
        
        # 按文件名排序，确保迁移按正确顺序执行
        migration_files.sort()
        logger.info(f"找到的迁移文件: {migration_files}")
        return migration_files
    
    @staticmethod
    def get_executed_migrations() -> List[str]:
        """获取已执行的迁移"""
        try:
            # 检查schema_migrations表是否存在
            tables = execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'")
            if not tables:
                logger.info("schema_migrations表不存在，返回空列表")
                return []
            
            # 获取已执行的迁移
            migrations = execute_query("SELECT version FROM schema_migrations ORDER BY version")
            executed_migrations = [migration['version'] for migration in migrations]
            logger.info(f"已执行的迁移: {executed_migrations}")
            return executed_migrations
        except Exception as e:
            logger.error(f"获取已执行迁移失败: {e}")
            return []
    
    @staticmethod
    def run_pending_migrations() -> bool:
        """运行所有待处理的迁移"""
        logger.info("开始检查待处理的数据库迁移...")
        
        try:
            # 获取所有迁移文件
            migration_files = MigrationManager.get_migration_files()
            executed_migrations = MigrationManager.get_executed_migrations()
            
            # 找出待处理的迁移
            pending_migrations = [
                migration for migration in migration_files 
                if migration not in executed_migrations
            ]
            
            if not pending_migrations:
                logger.info("没有待处理的迁移")
                return True
            
            logger.info(f"发现 {len(pending_migrations)} 个待处理的迁移: {pending_migrations}")
            
            # 运行待处理的迁移
            for migration in pending_migrations:
                logger.info(f"正在执行迁移: {migration}")
                
                # 动态导入迁移模块
                migration_module = __import__(f"src.database.migrations.{migration}", fromlist=["run_migration"])
                
                # 运行迁移
                success = migration_module.run_migration()
                if not success:
                    logger.error(f"迁移 {migration} 执行失败")
                    return False
                
                logger.info(f"迁移 {migration} 执行成功")
            
            logger.info("所有待处理的迁移执行完成")
            return True
            
        except Exception as e:
            logger.error(f"运行迁移失败: {e}")
            return False