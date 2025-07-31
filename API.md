# Y2A-Auto Telegram Bot API 文档

本文档描述了Y2A-Auto Telegram Bot的内部API和接口，供开发者参考。

## 目录

- [数据模型](#数据模型)
- [数据库API](#数据库api)
- [管理器API](#管理器api)
- [处理器API](#处理器api)
- [工具API](#工具api)
- [错误处理](#错误处理)
- [扩展开发](#扩展开发)

## 数据模型

### User

用户基本信息模型。

```python
@dataclass
class User:
    id: Optional[int] = None
    telegram_id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
```

### UserConfig

用户Y2A-Auto配置模型。

```python
@dataclass
class UserConfig:
    id: Optional[int] = None
    user_id: Optional[int] = None
    y2a_api_url: Optional[str] = None
    y2a_password: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

### ForwardRecord

转发记录模型。

```python
@dataclass
class ForwardRecord:
    id: Optional[int] = None
    user_id: Optional[int] = None
    youtube_url: Optional[str] = None
    status: Optional[str] = None  # 'success', 'failed', 'pending'
    response_message: Optional[str] = None
    created_at: Optional[datetime] = None
```

### UserStats

用户统计模型。

```python
@dataclass
class UserStats:
    id: Optional[int] = None
    user_id: Optional[int] = None
    total_forwards: int = 0
    successful_forwards: int = 0
    failed_forwards: int = 0
    last_forward_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        """计算成功率"""
        if self.total_forwards == 0:
            return 0.0
        return (self.successful_forwards / self.total_forwards) * 100
```

## 数据库API

### UserRepository

用户数据访问层，提供用户相关的数据库操作。

```python
class UserRepository:
    @staticmethod
    def get_by_telegram_id(telegram_id: int) -> Optional[User]:
        """通过Telegram ID获取用户"""
        
    @staticmethod
    def get_by_id(user_id: int) -> Optional[User]:
        """通过用户ID获取用户"""
        
    @staticmethod
    def get_all(active_only: bool = True) -> List[User]:
        """获取所有用户"""
        
    @staticmethod
    def create(user: User) -> int:
        """创建新用户"""
        
    @staticmethod
    def update(user: User) -> bool:
        """更新用户信息"""
        
    @staticmethod
    def update_last_activity(telegram_id: int) -> bool:
        """更新用户最后活动时间"""
```

### UserConfigRepository

用户配置数据访问层，提供用户配置相关的数据库操作。

```python
class UserConfigRepository:
    @staticmethod
    def get_by_user_id(user_id: int) -> Optional[UserConfig]:
        """通过用户ID获取配置"""
        
    @staticmethod
    def create(config: UserConfig) -> int:
        """创建用户配置"""
        
    @staticmethod
    def update(config: UserConfig) -> bool:
        """更新用户配置"""
        
    @staticmethod
    def update_by_user_id(user_id: int, y2a_api_url: str, y2a_password: str = None) -> bool:
        """通过用户ID更新配置"""
        
    @staticmethod
    def delete_by_user_id(user_id: int) -> bool:
        """删除用户配置"""
```

### ForwardRecordRepository

转发记录数据访问层，提供转发记录相关的数据库操作。

```python
class ForwardRecordRepository:
    @staticmethod
    def create(record: ForwardRecord) -> int:
        """创建转发记录"""
        
    @staticmethod
    def get_by_user_id(user_id: int, limit: int = 50) -> List[ForwardRecord]:
        """获取用户的转发记录"""
        
    @staticmethod
    def get_recent_by_user_id(user_id: int, days: int = 7) -> List[ForwardRecord]:
        """获取用户最近几天的转发记录"""
```

### UserStatsRepository

用户统计数据访问层，提供用户统计相关的数据库操作。

```python
class UserStatsRepository:
    @staticmethod
    def get_by_user_id(user_id: int) -> Optional[UserStats]:
        """通过用户ID获取统计信息"""
        
    @staticmethod
    def create(stats: UserStats) -> int:
        """创建用户统计"""
        
    @staticmethod
    def update(stats: UserStats) -> bool:
        """更新用户统计"""
        
    @staticmethod
    def increment_stats(user_id: int, is_successful: bool) -> bool:
        """增加用户统计"""
        
    @staticmethod
    def get_all_stats() -> List[UserStats]:
        """获取所有用户统计"""
```

## 管理器API

### UserManager

用户管理器，负责用户注册、配置管理等功能。

```python
class UserManager:
    @staticmethod
    def register_user(telegram_user: Dict[str, Any]) -> User:
        """注册新用户或获取现有用户"""
        
    @staticmethod
    def get_user(telegram_id: int) -> Optional[User]:
        """获取用户信息"""
        
    @staticmethod
    def update_user_activity(telegram_id: int) -> bool:
        """更新用户最后活动时间"""
        
    @staticmethod
    def get_user_config(user_id: int) -> Optional[UserConfig]:
        """获取用户配置"""
        
    @staticmethod
    def has_user_config(user_id: int) -> bool:
        """检查用户是否有配置"""
        
    @staticmethod
    def save_user_config(user_id: int, y2a_api_url: str, y2a_password: str = None) -> bool:
        """保存用户配置"""
        
    @staticmethod
    def delete_user_config(user_id: int) -> bool:
        """删除用户配置"""
        
    @staticmethod
    def get_user_with_config(telegram_id: int) -> tuple:
        """获取用户及其配置"""
        
    @staticmethod
    def is_user_configured(telegram_id: int) -> bool:
        """检查用户是否已配置Y2A-Auto"""
        
    @staticmethod
    async def ensure_user_registered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> User:
        """确保用户已注册，如果未注册则自动注册"""
        
    @staticmethod
    def format_user_info(user: User, config: UserConfig = None) -> str:
        """格式化用户信息"""
```

### AdminManager

管理员管理器，负责管理员权限验证和管理员功能。

```python
class AdminManager:
    @staticmethod
    def is_admin(telegram_id: int) -> bool:
        """检查用户是否为管理员"""
        
    @staticmethod
    def get_all_users() -> List[User]:
        """获取所有用户"""
        
    @staticmethod
    def get_user_with_config_and_stats(telegram_id: int) -> Dict[str, Any]:
        """获取用户及其配置和统计信息"""
        
    @staticmethod
    def get_all_users_with_config_and_stats() -> List[Dict[str, Any]]:
        """获取所有用户及其配置和统计信息"""
        
    @staticmethod
    def get_system_stats() -> Dict[str, Any]:
        """获取系统统计信息"""
        
    @staticmethod
    def format_user_list(users_data: List[Dict[str, Any]]) -> str:
        """格式化用户列表"""
        
    @staticmethod
    def format_system_stats(stats: Dict[str, Any]) -> str:
        """格式化系统统计信息"""
        
    @staticmethod
    def format_user_detail(user_data: Dict[str, Any]) -> str:
        """格式化用户详细信息"""
```

### SettingsManager

设置菜单管理器，负责处理用户设置相关的交互。

```python
class SettingsManager:
    @staticmethod
    async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理/settings命令，显示设置菜单"""
        
    @staticmethod
    async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """处理设置菜单的回调查询"""
        
    @staticmethod
    def get_conversation_handler() -> ConversationHandler:
        """获取设置菜单的对话处理器"""
```

### ForwardManager

转发管理器，负责处理YouTube链接的转发逻辑。

```python
class ForwardManager:
    @staticmethod
    def is_youtube_url(text: str) -> bool:
        """检查是否为YouTube URL"""
        
    @staticmethod
    async def forward_youtube_url(update: Update, context: ContextTypes.DEFAULT_TYPE, youtube_url: str) -> None:
        """转发YouTube URL到Y2A-Auto"""
        
    @staticmethod
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理用户消息，检查是否为YouTube链接并转发"""
        
    @staticmethod
    async def test_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, config: UserConfig) -> str:
        """测试Y2A-Auto连接"""
```

### SessionManager

会话管理器，负责管理用户会话和权限控制。

```python
class SessionManager:
    def get_or_create_session(self, telegram_user: Dict[str, Any]) -> UserSession:
        """获取或创建用户会话"""
        
    def get_session(self, telegram_id: int) -> Optional[UserSession]:
        """获取用户会话"""
        
    def remove_session(self, telegram_id: int) -> bool:
        """移除用户会话"""
        
    def cleanup_expired_sessions(self) -> None:
        """清理过期会话"""
        
    def get_active_sessions_count(self) -> int:
        """获取活跃会话数"""
        
    def is_user_admin(self, telegram_id: int) -> bool:
        """检查用户是否为管理员"""
        
    def set_session_data(self, telegram_id: int, key: str, value: Any) -> None:
        """设置会话数据"""
        
    def get_session_data(self, telegram_id: int, key: str, default=None) -> Any:
        """获取会话数据"""
```

## 处理器API

### CommandHandlers

命令处理器类，处理各种Telegram命令。

```python
class CommandHandlers:
    @staticmethod
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理/start命令"""
        
    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理/help命令"""
        
    @staticmethod
    async def admin_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理/admin_users命令"""
        
    @staticmethod
    async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理/admin_stats命令"""
        
    @staticmethod
    async def admin_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理/admin_user命令"""
        
    @staticmethod
    def get_command_handlers() -> Dict[str, Any]:
        """获取所有命令处理器"""
```

### MessageHandlers

消息处理器类，处理非命令消息。

```python
class MessageHandlers:
    @staticmethod
    async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理文本消息"""
        
    @staticmethod
    def get_message_handler() -> MessageHandler:
        """获取消息处理器"""
```

## 工具API

### 装饰器

```python
def require_user_session(func: Callable) -> Callable:
    """装饰器：确保用户有有效会话"""

def require_admin(func: Callable) -> Callable:
    """装饰器：确保用户是管理员"""

def require_configured_user(func: Callable) -> Callable:
    """装饰器：确保用户已配置Y2A-Auto服务"""

def log_user_activity(action: str):
    """装饰器：记录用户活动"""

def handle_errors(func: Callable) -> Callable:
    """装饰器：统一错误处理"""
```

### 日志管理

```python
class BotLogger:
    @staticmethod
    def log_user_activity(user_id: int, action: str, details: str = ""):
        """记录用户活动"""
        
    @staticmethod
    def log_error(error: Exception, context: str = ""):
        """记录错误"""
        
    @staticmethod
    def log_api_call(method: str, url: str, status_code: int, response_time: float, details: str = ""):
        """记录API调用"""
        
    @staticmethod
    def log_forward_attempt(user_id: int, youtube_url: str, success: bool, error_message: str = ""):
        """记录转发尝试"""
```

### 错误处理

```python
class ErrorHandler:
    @staticmethod
    async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE, error: Exception) -> None:
        """处理错误"""
        
    @staticmethod
    def handle_database_error(operation: str, error: Exception) -> None:
        """处理数据库错误"""
        
    @staticmethod
    def handle_api_error(url: str, status_code: int, response: str, error: Exception = None) -> None:
        """处理API错误"""
        
    @staticmethod
    def handle_forward_error(user_id: int, youtube_url: str, error: Exception) -> None:
        """处理转发错误"""
```

## 错误处理

### 异常类型

```python
class BotError(Exception):
    """机器人基础异常类"""

class UserNotConfiguredError(BotError):
    """用户未配置异常"""

class PermissionDeniedError(BotError):
    """权限被拒绝异常"""

class InvalidConfigurationError(BotError):
    """无效配置异常"""

class APIError(BotError):
    """API调用异常"""

class DatabaseError(BotError):
    """数据库异常"""
```

### 错误处理流程

1. **捕获异常**: 在函数中使用try-except捕获异常
2. **记录日志**: 使用ErrorHandler记录错误日志
3. **用户反馈**: 向用户发送友好的错误消息
4. **恢复处理**: 根据错误类型进行相应的恢复处理

## 扩展开发

### 添加新命令

1. 在`CommandHandlers`类中添加新的命令处理方法
2. 在`get_command_handlers`方法中注册新命令
3. 在`app.py`中注册命令处理器

### 添加新功能

1. **数据模型**: 在`models.py`中添加新的数据模型
2. **数据访问层**: 在`repository.py`中添加相应的数据访问方法
3. **业务逻辑**: 在`managers/`中创建或更新相应的管理器
4. **处理器**: 在`handlers/`中添加新的处理器
5. **注册**: 在`app.py`中注册新的处理器

### 添加新日志类型

1. 在`BotLogger`类中添加新的日志记录方法
2. 在`_setup_loggers`方法中设置新的日志记录器
3. 在需要的地方调用新的日志记录方法

### 添加新装饰器

1. 在`decorators.py`中添加新的装饰器函数
2. 在需要的地方应用新的装饰器

### 示例：添加新功能

假设我们要添加一个"导出用户数据"的功能：

1. **添加数据模型** (如果需要)
   ```python
   @dataclass
   class UserDataExport:
       user_id: int
       export_data: str
       created_at: datetime
   ```

2. **添加数据访问层** (如果需要)
   ```python
   class UserDataExportRepository:
       @staticmethod
       def create(export: UserDataExport) -> int:
           """创建导出记录"""
           
       @staticmethod
       def get_by_user_id(user_id: int) -> List[UserDataExport]:
           """获取用户的导出记录"""
   ```

3. **添加业务逻辑**
   ```python
   class ExportManager:
       @staticmethod
       async def export_user_data(user_id: int) -> str:
           """导出用户数据"""
           
       @staticmethod
       def format_export_data(user_data: Dict[str, Any]) -> str:
           """格式化导出数据"""
   ```

4. **添加处理器**
   ```python
   class CommandHandlers:
       @staticmethod
       @require_admin
       async def export_user_data_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
           """处理/export_user_data命令"""
           # 获取用户ID
           user_id = int(context.args[0]) if context.args else None
           
           if not user_id:
               await update.message.reply_text("请提供用户ID")
               return
               
           # 导出用户数据
           export_data = await ExportManager.export_user_data(user_id)
           
           # 发送导出数据
           await update.message.reply_text(f"用户数据导出：\n\n{export_data}")
   ```

5. **注册命令**
   ```python
   def get_command_handlers() -> Dict[str, Any]:
       return {
           # ... 其他命令
           'export_user_data': CommandHandlers.export_user_data_command,
       }
   ```

6. **在app.py中注册**
   ```python
   # 获取命令处理器
   command_handlers = CommandHandlers.get_command_handlers()
   
   # 注册命令处理器
   for command, handler in command_handlers.items():
       application.add_handler(CommandHandler(command, handler))
   ```

通过这种方式，您可以轻松地扩展机器人的功能，同时保持代码的清晰和可维护性。