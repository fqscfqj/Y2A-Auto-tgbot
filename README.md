# Y2A-Auto Telegram Bot

本机器人是一个多用户的Telegram机器人，用于接收YouTube视频或播放列表链接，并自动转发到用户配置的Y2A-Auto服务。

## 功能特点

- 🌟 **多用户支持**: 每个用户可以独立配置自己的Y2A-Auto服务
- 🔧 **灵活配置**: 通过交互式设置菜单配置Y2A-Auto API地址和密码
- 📊 **用户统计**: 记录每个用户的转发次数和成功率
- 👮 **管理员功能**: 管理员可以查看所有用户信息和系统统计
- 🛡️ **权限控制**: 基于Telegram用户ID的管理员权限验证
- 📝 **详细日志**: 完整的用户活动日志和错误日志
- 🐳 **Docker支持**: 提供Docker镜像和Docker Compose配置

## 系统架构

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────┐
│  Telegram   │────▶│  Telegram Bot   │────▶│  Y2A-Auto     │
│   Client    │     │   (多用户)       │     │   Service    │
└─────────────┘     └─────────────────┘     └──────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ SQLite DB   │
                    │ (用户数据)   │
                    └─────────────┘
```

## 安装和部署

### 环境要求

- Python 3.10+
- Telegram Bot Token（必需）
- Y2A-Auto 服务实例

### 方法一：Docker部署 (推荐)

1. **克隆项目**
   ```bash
   git clone https://github.com/yourusername/Y2A-Auto-tgbot.git
   cd Y2A-Auto-tgbot
   ```

2. **配置环境变量**
   请为运行环境设置如下变量（示例为 Bash）：
   ```bash
   export TG_BOT_TOKEN=你的_TG_BOT_TOKEN
   export ADMIN_TELEGRAM_IDS=123456789,987654321  # 可选，多人用逗号分隔
   ```

3. **启动服务**
   编辑 `docker-compose.yml` 填入 `TG_BOT_TOKEN` 等环境变量后执行：
   ```bash
   docker-compose up -d
   ```

### 方法二：本地部署

1. **克隆项目**
   ```bash
   git clone https://github.com/yourusername/Y2A-Auto-tgbot.git
   cd Y2A-Auto-tgbot
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**
   ```bash
   # 以 PowerShell 为例
   $env:TG_BOT_TOKEN = "你的_TG_BOT_TOKEN"
   $env:ADMIN_TELEGRAM_IDS = "123456789,987654321"  # 可选
   ```

4. **运行数据库迁移**
   无需手动执行，`app.py` 在启动时会自动执行待处理迁移。

5. **启动机器人**
   ```bash
   python app.py
   ```

## 使用指南

### 快速开始

#### 1. 添加机器人
在Telegram中搜索机器人或通过邀请链接添加到您的聊天列表。

#### 2. 开始配置
发送 `/start` 命令，按照引导完成配置：
- **欢迎页面**：了解机器人功能
- **配置API**：输入 Y2A-Auto 服务地址
- **完成**：配置成功，可以开始使用

#### 3. 开始使用
配置完成后，直接发送 YouTube 链接即可自动转发。

### 配置Y2A-Auto服务（已按钮化）

#### 步骤1：打开设置菜单
发送 `/settings` 命令或使用消息下方按钮打开设置。所有操作均通过内联按钮完成：查看配置、设置 API、设置密码、测试连接、删除配置等。

#### 步骤2：设置API地址
1. 点击“设置 API”
2. 机器人会提示您输入 API 地址（直接发送即可）
3. 输入您的Y2A-Auto服务地址，例如：
   ```
   http://localhost:5000/tasks/add_via_extension
   ```
4. 确认后，API地址将被保存

#### 步骤3：设置密码（可选）
如果您的Y2A-Auto服务启用了密码保护：
1. 点击“设置密码”
2. 机器人会提示您输入密码（直接发送即可，或选择“跳过”）
3. 输入您的Y2A-Auto服务密码
4. 确认后，密码将被保存

如果您不需要密码，可以跳过此步骤。

#### 步骤4：测试连接
配置完成后，建议测试连接是否正常：
1. 点击“测试连接”
2. 机器人将尝试连接到您配置的 Y2A-Auto 服务并返回结果：
   - ✅ 连接成功，登录成功（如果设置了密码）
   - ✅ 连接成功（如果没有设置密码）
   - ⚠️ 连接成功，但登录失败（请检查密码）
   - ❌ 连接失败（请检查API地址）

#### 步骤5：查看配置
可随时点击“查看配置”查看当前设置（地址以代码块方式展示，更清晰）。

#### 修改配置
如果您需要修改配置：
1. 重新执行 `/settings` 命令
2. 选择相应的设置选项进行修改
3. 修改完成后，建议再次测试连接

#### 删除配置
如果您想删除当前配置：
1. 执行 `/settings` 命令
2. 点击"删除配置"
3. 确认删除操作

⚠️ **注意**：删除配置后，您将无法使用转发功能，除非重新配置。

### 转发YouTube链接

#### 支持的链接类型
机器人支持以下类型的YouTube链接：
- 视频链接：`https://www.youtube.com/watch?v=VIDEO_ID`
- 短链接：`https://youtu.be/VIDEO_ID`
- 播放列表链接：`https://www.youtube.com/playlist?list=PLAYLIST_ID`
- 短播放列表链接：`https://youtu.be/playlist?list=PLAYLIST_ID`

#### 转发步骤
1. 确保您已正确配置Y2A-Auto服务
2. 直接向机器人发送YouTube链接
3. 机器人会自动识别链接并转发到您的Y2A-Auto服务
4. 您将收到转发结果：
   - ✅ 转发成功：已添加任务
   - ❌ 转发失败：[具体错误信息]

#### 转发示例
```
您: https://www.youtube.com/watch?v=dQw4w9WgXcQ

机器人: 检测到YouTube链接，正在转发到Y2A-Auto...
机器人: ✅ 转发成功：已添加任务
```

#### 错误处理
如果转发失败，机器人会提供详细的错误信息，常见错误包括：
- **未配置服务**：您尚未配置Y2A-Auto服务，请使用 /settings 命令进行配置
- **连接失败**：无法连接到Y2A-Auto服务，请检查API地址
- **认证失败**：Y2A-Auto服务需要登录，且自动登录失败，请检查密码
- **服务错误**：Y2A-Auto服务返回错误，请检查服务状态

### 管理员功能

#### 查看所有用户
- 发送 `/admin_users` 命令
- 查看所有注册用户列表及其配置状态，包括：
  - 用户ID
  - 用户名
  - 姓名
  - 状态
  - Y2A-Auto配置状态
  - 转发统计
  - 最后活动时间

#### 查看系统统计
- 发送 `/admin_stats` 命令
- 查看系统统计信息，包括：
  - 总用户数
  - 活跃用户数
  - 已配置用户数
  - 总转发次数
  - 成功转发次数
  - 失败转发次数
  - 成功率

#### 查看特定用户
- 发送 `/admin_user <用户ID>` 命令
- 查看指定用户的详细信息，包括：
  - 用户基本信息
  - Y2A-Auto配置详情
  - 使用统计详情

### 用户统计
机器人会自动记录您的转发统计信息，包括：
- 总转发次数
- 成功转发次数
- 失败转发次数
- 成功率
- 最后转发时间

## 环境变量说明

| 变量名 | 必需 | 说明 | 示例 |
|--------|------|------|------|
| `TG_BOT_TOKEN` | 是 | Telegram机器人的Token | `123456789:ABCdefGHijKLmnoPqrsTuVwxyz` |
| `ADMIN_TELEGRAM_IDS` | 否 | 管理员的Telegram用户ID列表，多个ID用逗号分隔 | `123456789,987654321` |
| `LOG_LEVEL` | 否 | 日志级别，默认为INFO | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

## 数据目录结构

```
data/
├── app.db          # SQLite数据库文件
└── logs/           # 日志目录（按需生成）
```

## 数据库结构

项目使用SQLite数据库，包含以下表：

- `users`: 用户基本信息
- `user_configs`: 用户Y2A-Auto配置
- `forward_records`: 转发记录
- `user_stats`: 用户统计信息
- `schema_migrations`: 数据库迁移记录

## 开发指南

### 项目结构（当前）

```
Y2A-Auto-tgbot/
├── app.py                 # 主应用入口（自动执行数据库迁移）
├── config.py              # 配置管理（环境变量校验、数据/日志目录）
├── requirements.txt       # 依赖包列表
├── Dockerfile             # Docker镜像配置
├── docker-compose.yml     # Docker Compose配置
├── README.md              # 项目说明（本文件）
│
├── src/
│   ├── database/
│   │   ├── db.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── migrations/
│   │       ├── 001_initial.py
│   │       └── 002_add_user_guides.py
│   │
│   ├── managers/
│   │   ├── forward_manager.py
│   │   ├── guide_manager.py
│   │   ├── settings_manager.py
│   │   ├── user_manager.py
│   │   └── admin_manager.py
│   │
│   ├── handlers/
│   │   ├── command_handlers.py
│   │   └── message_handlers.py
│   │
│   └── utils/
│       ├── decorators.py
│       ├── error_handler.py
│       └── logger.py
│
└── data/
    ├── app.db
    └── logs/
```

### 添加新功能

1. **数据库模型**: 在 `src/database/models.py` 中添加新的数据模型
2. **数据访问层**: 在 `src/database/repository.py` 中添加相应的数据访问方法
3. **业务逻辑**: 在 `src/managers/` 中创建或更新相应的管理器
4. **处理器**: 在 `src/handlers/` 中添加新的命令或消息处理器
5. **注册处理器**: 在 `app.py` 中注册新的处理器

（已移除过时的 tests 目录与相关说明）

## 常见问题

### Q: 如何获取Telegram Bot Token？
A: 通过 [@BotFather](https://t.me/BotFather) 创建新机器人并获取Token。

### Q: 如何获取用户ID？
A: 可以通过 [@userinfobot](https://t.me/userinfobot) 获取您的Telegram用户ID。

### Q: 如何获取Y2A-Auto服务的API地址？
A: Y2A-Auto服务的API地址通常是：
```
http://您的服务器IP:端口/tasks/add_via_extension
```

例如：
```
http://localhost:5000/tasks/add_via_extension
http://192.168.1.100:5000/tasks/add_via_extension
```

### Q: 为什么转发失败？
A: 转发失败可能有多种原因：
1. **未配置服务**：请使用 `/settings` 命令配置您的Y2A-Auto服务
2. **API地址错误**：请检查您的Y2A-Auto服务地址是否正确
3. **密码错误**：如果Y2A-Auto服务有密码保护，请确保密码正确
4. **服务不可用**：请检查您的Y2A-Auto服务是否正常运行
5. **网络问题**：请检查网络连接是否正常

### Q: 如何测试我的配置是否正确？
A: 您可以使用 `/settings` 命令中的"测试连接"功能来验证您的配置。

### Q: 我可以修改我的配置吗？
A: 是的，您可以随时使用 `/settings` 命令修改您的配置。

### Q: 我可以删除我的配置吗？
A: 是的，您可以使用 `/settings` 命令中的"删除配置"功能删除您的配置。

### Q: 删除配置后我的数据会怎样？
A: 删除配置只会删除您的Y2A-Auto服务配置，不会删除您的用户账户和转发记录。如果您想重新使用，只需重新配置即可。

### Q: 为什么我无法使用管理员命令？
A: 管理员命令需要特定的权限。只有被设置为管理员的用户才能使用管理员命令。如果您需要管理员权限，请联系机器人管理员。

### Q: 如何查看日志？
A: 日志文件位于 `data/logs/` 目录下，包括：
- `app.log`: 应用运行日志
- `user_activity.log`: 用户活动日志
- `error.log`: 错误日志
- `api.log`: API调用日志

## 高级功能

### 批量转发
目前机器人不支持批量转发，您需要逐个发送YouTube链接。

### 自定义设置
机器人会记住您的配置，下次使用时无需重新配置。如果您有多个Y2A-Auto服务实例，您可以通过修改配置来切换不同的服务。

### 隐私保护
- 机器人只会记录必要的用户信息（Telegram ID、用户名、姓名）
- 您的Y2A-Auto配置（包括密码）会被安全存储
- 转发记录会被保存，但仅用于统计和故障排除
- 管理员可以查看用户统计信息，但无法查看您的具体配置内容

### 数据导出
如果您需要导出您的使用数据，请联系管理员。

## 联系支持

如果您在使用过程中遇到任何问题，或有任何建议，请通过以下方式联系我们：

- 在Telegram中直接联系机器人管理员
- 提交Issue到项目GitHub仓库
- 发送邮件至支持邮箱

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 贡献

欢迎提交 Issue 和 Pull Request！