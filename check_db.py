#!/usr/bin/env python3
"""
检查数据库状态的脚本
"""
import os
import sys
import sqlite3
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.db import get_db_connection, execute_query

def check_database():
    """检查数据库状态"""
    print("检查数据库状态...")
    
    # 获取所有表
    try:
        tables = execute_query("SELECT name FROM sqlite_master WHERE type='table'")
        print(f"数据库中的表: {[table['name'] for table in tables]}")
    except Exception as e:
        print(f"获取表列表失败: {e}")
        return
    
    # 检查 schema_migrations 表
    try:
        migrations = execute_query("SELECT * FROM schema_migrations")
        print(f"已执行的迁移: {migrations}")
    except Exception as e:
        print(f"获取迁移记录失败: {e}")
    
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
        else:
            print("user_guides 表不存在")
    except Exception as e:
        print(f"检查 user_guides 表失败: {e}")

if __name__ == "__main__":
    check_database()