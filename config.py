import os
import logging
from typing import List, Optional

# 日志配置
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class Config:
    """应用配置类"""
    
    # Telegram Bot配置
    TELEGRAM_TOKEN = os.getenv('TG_BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')
    
    # 管理员配置
    ADMIN_TELEGRAM_IDS = os.getenv('ADMIN_TELEGRAM_IDS', '')
    
    # Y2A-Auto默认配置
    Y2A_AUTO_API_DEFAULT = 'http://localhost:5000/tasks/add_via_extension'
    
    # 数据库配置
    DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
    DATABASE_PATH = os.path.join(DATA_DIR, 'app.db')
    
    # 日志配置
    LOGS_DIR = os.path.join(DATA_DIR, 'logs')
    LOG_FILE = os.path.join(LOGS_DIR, 'app.log')
    
    @classmethod
    def get_admin_ids(cls) -> List[int]:
        """获取管理员ID列表"""
        if not cls.ADMIN_TELEGRAM_IDS:
            return []
        
        try:
            return [int(id_str.strip()) for id_str in cls.ADMIN_TELEGRAM_IDS.split(',')]
        except ValueError as e:
            logger.error(f"管理员ID列表格式错误: {e}")
            return []
    
    @classmethod
    def validate_config(cls) -> bool:
        """验证配置是否有效"""
        # 检查Telegram Token
        if not cls.TELEGRAM_TOKEN or cls.TELEGRAM_TOKEN == 'YOUR_TELEGRAM_BOT_TOKEN':
            logger.error("未设置有效的Telegram Bot Token")
            return False
        
        # 检查数据目录
        if not os.path.exists(cls.DATA_DIR):
            try:
                os.makedirs(cls.DATA_DIR, exist_ok=True)
                logger.info(f"创建数据目录: {cls.DATA_DIR}")
            except Exception as e:
                logger.error(f"创建数据目录失败: {e}")
                return False
        
        # 检查日志目录
        if not os.path.exists(cls.LOGS_DIR):
            try:
                os.makedirs(cls.LOGS_DIR, exist_ok=True)
                logger.info(f"创建日志目录: {cls.LOGS_DIR}")
            except Exception as e:
                logger.error(f"创建日志目录失败: {e}")
                return False
        
        logger.info("配置验证通过")
        return True
    
    # 说明：帮助文案已迁移到 handlers 层，并采用 HTML 样式与 inline 键盘，旧的 get_help_text 已移除。