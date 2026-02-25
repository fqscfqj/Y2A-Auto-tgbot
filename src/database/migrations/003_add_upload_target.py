"""
添加upload_target字段到user_configs表的数据库迁移脚本
"""
import logging
from src.database.db import execute_query, execute_script

logger = logging.getLogger(__name__)


def _upload_target_column_exists() -> bool:
    """检查 user_configs 表中是否已经存在 upload_target 列。"""
    try:
        rows = execute_query("PRAGMA table_info(user_configs)")
        return any(row.get("name") == "upload_target" for row in rows)
    except Exception as e:
        logger.error(f"查询 user_configs 表结构失败: {e}")
        return False


def run_migration():
    """运行数据库迁移"""
    logger.info("开始执行添加upload_target字段的数据库迁移...")

    if _upload_target_column_exists():
        logger.info("user_configs.upload_target 列已存在，跳过本次迁移。")
        return True

    try:
        migration_sql = """
        ALTER TABLE user_configs ADD COLUMN upload_target TEXT;
        
        INSERT INTO schema_migrations (version, description)
        VALUES ('003_add_upload_target', '添加upload_target字段到user_configs表，支持指定投稿目标平台（acfun/bilibili/both）');
        """
        
        logger.info("执行SQL脚本添加upload_target字段并记录迁移信息...")
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
