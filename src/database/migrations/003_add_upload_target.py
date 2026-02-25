"""
添加upload_target字段到user_configs表的数据库迁移脚本
"""
import logging
from src.database.db import execute_script

logger = logging.getLogger(__name__)

def run_migration():
    """运行数据库迁移"""
    logger.info("开始执行添加upload_target字段的数据库迁移...")
    
    try:
        migration_sql = """
        -- 添加upload_target列到user_configs表（如果不存在）
        ALTER TABLE user_configs ADD COLUMN upload_target TEXT;
        
        -- 记录迁移信息
        INSERT INTO schema_migrations (version, description)
        VALUES ('003_add_upload_target', '添加upload_target字段到user_configs表，支持指定投稿目标平台（acfun/bilibili/both）');
        """
        
        logger.info("执行SQL脚本添加upload_target字段...")
        execute_script(migration_sql)
        
        logger.info("upload_target字段迁移完成")
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
