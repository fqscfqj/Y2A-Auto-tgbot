import os
import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'app.db')

logger = logging.getLogger(__name__)

def get_db_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 返回字典形式的行
    return conn

def init_database() -> None:
    """初始化数据库，创建所有表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 创建用户表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建用户配置表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            y2a_api_url TEXT NOT NULL,
            y2a_password TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        ''')
        
        # 创建转发记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS forward_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            youtube_url TEXT NOT NULL,
            status TEXT NOT NULL,
            response_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        ''')
        
        # 创建用户统计表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            total_forwards INTEGER DEFAULT 0,
            successful_forwards INTEGER DEFAULT 0,
            failed_forwards INTEGER DEFAULT 0,
            last_forward_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_configs_user_id ON user_configs(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_forward_records_user_id ON forward_records(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_forward_records_status ON forward_records(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_stats_user_id ON user_stats(user_id)')
        
        conn.commit()
        logger.info("数据库初始化完成")
        
    except sqlite3.Error as e:
        logger.error(f"数据库初始化失败: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def execute_query(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """执行查询并返回结果"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        return results
    except sqlite3.Error as e:
        logger.error(f"查询执行失败: {e}, 查询: {query}, 参数: {params}")
        raise
    finally:
        conn.close()

def execute_update(query: str, params: tuple = ()) -> int:
    """执行更新/插入/删除操作并返回影响的行数"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(query, params)
        conn.commit()
        return cursor.rowcount
    except sqlite3.Error as e:
        logger.error(f"更新操作失败: {e}, 查询: {query}, 参数: {params}")
        conn.rollback()
        raise
    finally:
        conn.close()

def execute_insert(query: str, params: tuple = ()) -> int:
    """执行插入操作并返回新行的ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(query, params)
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        logger.error(f"插入操作失败: {e}, 查询: {query}, 参数: {params}")
        conn.rollback()
        raise
    finally:
        conn.close()

def execute_script(script: str) -> None:
    """执行SQL脚本"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.executescript(script)
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"脚本执行失败: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()