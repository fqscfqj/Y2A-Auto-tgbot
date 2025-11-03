import os
import sqlite3
import logging
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import time

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'app.db')

logger = logging.getLogger(__name__)

# 数据库连接池
class DatabasePool:
    """简单的数据库连接池实现"""
    
    # Connection retry constants
    MAX_CONNECTION_RETRIES = 50  # Maximum number of retries (5 seconds total)
    RETRY_SLEEP_DURATION = 0.1   # Sleep duration between retries in seconds
    
    def __init__(self, max_connections: int = 10):
        self._max_connections = max_connections
        self._connections: List[sqlite3.Connection] = []
        self._lock = threading.Lock()
        self._connection_count = 0
    
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        # Use a timeout-based retry instead of recursion to avoid stack overflow
        retry_count = 0
        
        while retry_count < self.MAX_CONNECTION_RETRIES:
            with self._lock:
                # 尝试从池中获取连接
                if self._connections:
                    conn = self._connections.pop()
                    # 检查连接是否仍然有效
                    try:
                        conn.execute("SELECT 1")
                        return conn
                    except sqlite3.Error:
                        # 连接无效，关闭并继续创建新连接
                        try:
                            conn.close()
                        except:
                            # Ignore any errors during connection cleanup
                            pass
                        self._connection_count -= 1
                
                # 创建新连接
                if self._connection_count < self._max_connections:
                    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
                    conn.row_factory = sqlite3.Row
                    # 设置WAL模式以提高并发性能
                    conn.execute("PRAGMA journal_mode=WAL")
                    # 设置更短的超时
                    conn.execute("PRAGMA busy_timeout=5000")
                    self._connection_count += 1
                    return conn
            
            # 如果达到最大连接数，等待并重试
            retry_count += 1
            time.sleep(self.RETRY_SLEEP_DURATION)
        
        # 如果仍然无法获取连接，抛出异常
        raise sqlite3.OperationalError(
            f"无法获取数据库连接: 超出最大重试次数({self.MAX_CONNECTION_RETRIES}), 最大连接数: {self._max_connections}"
        )
    
    def return_connection(self, conn: sqlite3.Connection) -> None:
        """归还数据库连接到池中"""
        with self._lock:
            # 检查连接是否仍然有效
            try:
                conn.execute("SELECT 1")
                # 连接有效，归还到池中（不关闭）
                if len(self._connections) < self._max_connections:
                    self._connections.append(conn)
                else:
                    # 池已满，关闭连接并减少计数
                    try:
                        conn.close()
                    except:
                        # Ignore any errors during connection cleanup
                        pass
                    self._connection_count -= 1
            except sqlite3.Error:
                # 连接无效，关闭并减少计数
                try:
                    conn.close()
                except:
                    # Ignore any errors during connection cleanup
                    pass
                self._connection_count -= 1

# 全局连接池实例
_db_pool = DatabasePool()

@contextmanager
def get_db_connection():
    """获取数据库连接上下文管理器"""
    conn = _db_pool.get_connection()
    try:
        yield conn
    finally:
        _db_pool.return_connection(conn)

def init_database() -> None:
    """初始化数据库，创建所有表"""
    with get_db_connection() as conn:
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
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_configs_user_id ON user_configs(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_forward_records_user_id ON forward_records(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_forward_records_status ON forward_records(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_forward_records_created_at ON forward_records(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_stats_user_id ON user_stats(user_id)')
            
            conn.commit()
            logger.info("数据库初始化完成")
            
        except sqlite3.Error as e:
            logger.error(f"数据库初始化失败: {e}")
            conn.rollback()
            raise

def execute_query(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """执行查询并返回结果"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            return results
        except sqlite3.Error as e:
            logger.error(f"查询执行失败: {e}, 查询: {query}, 参数: {params}")
            raise

def execute_update(query: str, params: tuple = ()) -> int:
    """执行更新/插入/删除操作并返回影响的行数"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            logger.error(f"更新操作失败: {e}, 查询: {query}, 参数: {params}")
            conn.rollback()
            raise

def execute_insert(query: str, params: tuple = ()) -> int:
    """执行插入操作并返回新行的ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, params)
            conn.commit()
            last_id = cursor.lastrowid
            # 确保返回 int（sqlite3 的 lastrowid 在某些情况下可能为 None）
            return int(last_id) if last_id is not None else 0
        except sqlite3.Error as e:
            logger.error(f"插入操作失败: {e}, 查询: {query}, 参数: {params}")
            conn.rollback()
            raise

def execute_script(script: str) -> None:
    """执行SQL脚本"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.executescript(script)
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"脚本执行失败: {e}")
            conn.rollback()
            raise