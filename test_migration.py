#!/usr/bin/env python3
"""
测试数据库迁移的脚本
"""
import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.database.migration_manager import MigrationManager

def test_migration():
    """测试数据库迁移"""
    print("开始测试数据库迁移...")
    
    # 运行待处理的迁移
    success = MigrationManager.run_pending_migrations()
    
    if success:
        print("数据库迁移成功完成")
        
        # 检查数据库状态
        from src.database.db import execute_query
        
        # 获取所有表
        try:
            tables = execute_query("SELECT name FROM sqlite_master WHERE type='table'")
            print(f"数据库中的表: {[table['name'] for table in tables]}")
        except Exception as e:
            print(f"获取表列表失败: {e}")
            return False
        
        # 检查 schema_migrations 表
        try:
            migrations = execute_query("SELECT * FROM schema_migrations")
            print(f"已执行的迁移: {migrations}")
        except Exception as e:
            print(f"获取迁移记录失败: {e}")
            return False
        
        # 检查 user_guides 表是否存在
        try:
            user_guides_check = execute_query("SELECT name FROM sqlite_master WHERE type='table' AND name='user_guides'")
            if user_guides_check:
                print("user_guides 表存在")
                # 尝试查询表结构
                try:
                    structure = execute_query("PRAGMA table_info(user_guides)")
                    print(f"user_guides 表结构: {structure}")
                except Exception as e:
                    print(f"获取 user_guides 表结构失败: {e}")
                    return False
            else:
                print("user_guides 表不存在")
                return False
        except Exception as e:
            print(f"检查 user_guides 表失败: {e}")
            return False
        
        return True
    else:
        print("数据库迁移失败")
        return False

if __name__ == "__main__":
    success = test_migration()
    sys.exit(0 if success else 1)