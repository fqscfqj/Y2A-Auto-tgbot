"""
添加用户引导表的数据库迁移脚本
"""
import os
import sys
import logging
import sqlite3
from pathlib import Path

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'app.db')

# 确保数据目录存在
data_dir = os.path.dirname(DB_PATH)
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

logger = logging.getLogger(__name__)

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 返回字典形式的行
    return conn

def execute_script(script):
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

def run_migration():
    """运行数据库迁移"""
    logger.info("开始执行添加用户引导表的数据库迁移...")
    
    try:
        migration_sql = """
        -- 创建schema_migrations表（如果不存在）
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL,
            description TEXT,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        -- 创建用户引导表
        CREATE TABLE IF NOT EXISTS user_guides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            current_step TEXT DEFAULT 'not_started',
            completed_steps TEXT DEFAULT '[]',
            is_completed BOOLEAN DEFAULT 0,
            is_skipped BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        
        -- 创建索引
        CREATE INDEX IF NOT EXISTS idx_user_guides_user_id ON user_guides(user_id);
        
        -- 记录迁移信息
        INSERT INTO schema_migrations (version, description)
        VALUES ('002_add_user_guides', '添加用户引导表，用于跟踪用户引导进度');
        """
        
        execute_script(migration_sql)
        
        logger.info("用户引导表迁移完成")
        return True
        
    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        return False

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行迁移
    success = run_migration()
    if success:
        print("数据库迁移成功完成")
    else:
        print("数据库迁移失败")