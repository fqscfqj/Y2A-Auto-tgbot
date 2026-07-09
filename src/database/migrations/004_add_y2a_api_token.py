"""
添加 y2a_api_token 字段并清理旧明文密码
"""
import logging
from src.database.db import execute_query, execute_update

logger = logging.getLogger(__name__)


def _column_exists(table_name: str, column_name: str) -> bool:
    try:
        rows = execute_query(f"PRAGMA table_info({table_name})")
        return any(row.get("name") == column_name for row in rows)
    except Exception as e:
        logger.error(f"查询 {table_name} 表结构失败: {e}")
        return False


def _migration_record_exists() -> bool:
    try:
        rows = execute_query(
            "SELECT 1 FROM schema_migrations WHERE version = ? LIMIT 1",
            ("004_add_y2a_api_token",),
        )
        return bool(rows)
    except Exception:
        return False


def run_migration():
    """运行数据库迁移"""
    logger.info("开始执行添加 y2a_api_token 字段的数据库迁移...")

    has_token_column = _column_exists("user_configs", "y2a_api_token")
    has_password_column = _column_exists("user_configs", "y2a_password")

    statements = []
    if not has_token_column:
        statements.append("ALTER TABLE user_configs ADD COLUMN y2a_api_token TEXT")

    if has_password_column:
        statements.append("UPDATE user_configs SET y2a_password = NULL")

    if not _migration_record_exists():
        statements.append(
            "INSERT INTO schema_migrations (version, description) "
            "VALUES ('004_add_y2a_api_token', '添加 y2a_api_token 字段并清理旧明文密码')"
        )

    if not statements:
        logger.info("y2a_api_token 字段迁移已完成，跳过本次迁移。")
        return True

    try:
        for statement in statements:
            execute_update(statement)
        logger.info("y2a_api_token 字段迁移完成")
        return True
    except Exception as e:
        logger.error(f"数据库迁移失败: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    success = run_migration()
    if success:
        print("数据库迁移成功完成")
    else:
        print("数据库迁移失败")
