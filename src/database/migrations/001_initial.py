"""
初始数据库迁移脚本
创建所有必要的表和索引
"""
import logging
from datetime import datetime
from src.database.db import init_database, execute_script

logger = logging.getLogger(__name__)

def run_migration():
    """运行数据库迁移"""
    logger.info("开始执行初始数据库迁移...")
    
    try:
        # 初始化数据库，创建所有表
        init_database()
        
        # 记录迁移信息
        migration_sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL,
            description TEXT,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        INSERT INTO schema_migrations (version, description) 
        VALUES ('001_initial', '初始数据库结构，创建用户、配置、转发记录和统计表');
        """
        
        execute_script(migration_sql)
        
        logger.info("初始数据库迁移完成")
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