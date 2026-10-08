# Y2A-Auto Telegram Bot

本机器人是一个多用户的Telegram机器人，用于接收YouTube视频或播放列表链接，并自动转发到用户配置的Y2A-Auto服务。

> 📖 **第一次使用？** 请先阅读 [接入教程](#接入教程)：
> [教程一：创建 Telegram 机器人并获取 Bot Token](#教程一创建-telegram-机器人并获取-bot-token) ·
> [教程二：连接 Y2A-Auto 服务（API 地址与 API Token）](#教程二连接-y2a-auto-服务api-地址与-api-token)

## 功能特点

- 🌟 **多用户支持**: 每个用户可以独立配置自己的Y2A-Auto服务
- 🔧 **灵活配置**: 通过交互式设置菜单配置 Y2A-Auto API 地址和专用 API Token（不再使用 Web 登录密码）
- 🔐 **最小权限 Token**: 使用 Y2A-Auto 设置页生成的 `y2a_tgbot_v1_...` 专用 Token，仅授权提交上传任务，可随时撤销
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

## 接入教程

新用户建议按顺序完成下面两个教程：先创建 Telegram 机器人拿到 Bot Token，再在 Y2A-Auto 中生成专用 API Token 并连接机器人。

1. [教程一：创建 Telegram 机器人并获取 Bot Token](#教程一创建-telegram-机器人并获取-bot-token)
2. [教程二：连接 Y2A-Auto 服务（API 地址与 API Token）](#教程二连接-y2a-auto-服务api-地址与-api-token)

### 教程一：创建 Telegram 机器人并获取 Bot Token

机器人必须先有一组 Bot Token 才能登录 Telegram 服务器。Token 由 Telegram 官方的 [@BotFather](https://t.me/BotFather) 创建并下发，这就是环境变量 `TG_BOT_TOKEN` 的取值来源。

#### 步骤 1：打开 BotFather

1. 在 Telegram 客户端搜索 `@BotFather`（带蓝色官方认证标识），或直接访问 https://t.me/BotFather
2. 点击 **START** 或发送 `/start`，打开指令列表

#### 步骤 2：创建机器人

1. 发送 `/newbot`
2. 按提示输入 **机器人显示名称**（可随意填写，支持中文，例如 `Y2A-Auto 转发机器人`）
3. 按提示输入 **机器人用户名**，要求：
   - 全局唯一，若提示已被占用请更换
   - 必须以 `bot` 结尾，例如 `my_y2a_auto_bot`
4. 创建成功后，BotFather 会返回类似下面的内容：

```
Done! Congratulations on your new bot. You will find it at t.me/my_y2a_auto_bot.
Use this token to access the HTTP API:
123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

Keep your token secure and store it safely, it can be used by anyone to control your bot.
```

其中 `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` 就是 **Bot Token**。

#### 步骤 3：保存 Token

- 复制**完整**一行 Token（包含中间的冒号，前后不要带空格或换行）
- 填入 `TG_BOT_TOKEN`（见 [安装和部署](#安装和部署)），或写入 `.env` / `docker-compose.yml`
- ⚠️ Token 等同于机器人的账号密码：**不要**发到群聊、不要提交到 Git 仓库、不要截图分享

#### 步骤 4（可选）：完善机器人资料

在 BotFather 中还可以继续配置：

| 指令 | 作用 |
| --- | --- |
| `/setname` | 修改机器人显示名称 |
| `/setdescription` | 设置机器人简介（用户点击 START 前看到的介绍） |
| `/setabouttext` | 设置机器人资料页介绍 |
| `/setuserpic` | 设置机器人头像 |
| `/setcommands` | 设置命令菜单，可粘贴 `start - 开始使用`、`settings - 配置 Y2A-Auto`、`help - 查看帮助` |
| `/setprivacy` | 群组隐私模式；若希望机器人在群组中读取链接，需选择 `Disable` |
| `/deletewebhook` | 机器人长期收不到消息时，可尝试清除 Webhook |

#### 步骤 5：验证机器人可用

1. 点击 BotFather 返回的链接 `t.me/你的机器人用户名`，进入与机器人的对话
2. 发送 `/start`，能收到回复即说明 Token 配置成功

#### 教程一常见问题

- **启动时报 `Unauthorized`**：Token 复制不完整或已被重置，请重新确认 `TG_BOT_TOKEN`
- **忘记 Token**：在 BotFather 中发送 `/mybots` → 选择机器人 → **API Token**
- **怀疑 Token 泄露**：在 BotFather 中发送 `/revoke` 并选择机器人，旧 Token 立即失效；拿到新 Token 后重启服务
- **多人使用需要创建多个机器人吗**：不需要。本机器人支持多用户，所有用户与同一个机器人对话，各自配置自己的 Y2A-Auto 服务

### 教程二：连接 Y2A-Auto 服务（API 地址与 API Token）

连接需要两份信息，缺一不可：

| 配置项 | 从哪里获取 | 示例 |
| --- | --- | --- |
| API 地址 | Y2A-Auto 服务的 Web 访问地址（只需主机 + 端口，路径会自动补全） | `http://192.168.1.100:5000` |
| API Token | Y2A-Auto Web → **设置** → **运维与安全** → 「Telegram Bot API Token」卡片点击「生成 Token」 | `y2a_tgbot_v1_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |

> ❗ 本机器人**不再使用 Y2A-Auto 的 Web 登录密码**。当机器人提示您需要「设置 API Token」时，请按下面第 3 步在 Y2A-Auto 设置页生成，再回到机器人粘贴。

#### 步骤 1：确认 Y2A-Auto 服务已启动

1. 部署并启动主服务（部署方式见 [Y2A-Auto 项目](https://github.com/fqscfqj/Y2A-Auto)）：
   ```bash
   docker compose up -d
   ```
2. 浏览器访问 Web 界面，默认地址 `http://localhost:5000`，能打开并登录即为正常
3. 记录 **机器人所在环境** 能访问到的地址：
   - 机器人与 Y2A-Auto 在**同一台机器**：`http://127.0.0.1:5000`
   - 机器人在 Docker 中、Y2A-Auto 在同一台宿主机：Docker Desktop 可用 `http://host.docker.internal:5000`，Linux 可先用 `ip addr` 查出宿主机内网 IP 再填写
   - 机器人与 Y2A-Auto **不在同一台机器**：填写 Y2A-Auto 所在机器的内网 IP / 域名 + 端口，例如 `http://192.168.1.100:5000`、`https://y2a.example.com`
   - ⚠️ `localhost` 只在同一容器 / 同一台机器内有效，跨机器填写 `localhost` 一定连接失败

#### 步骤 2：在机器人中填写 API 地址

1. 在 Telegram 中向机器人发送 `/settings`，打开设置菜单
2. 点击 **🔧 API 地址**，然后直接发送地址，例如：
   ```
   http://192.168.1.100:5000
   ```
3. 只填主机和端口即可，机器人会自动补全为 `.../tasks/add_via_extension`；直接粘贴完整接口地址（`http://主机:端口/tasks/add_via_extension`）也可以
4. 支持 `http` 与 `https`；地址中自带的用户名密码会被自动去除（鉴权改用专用 Token）
5. ⚠️ 建议始终带上协议头：若省略（例如只写 `localhost:5000`），机器人会按 `https://` 处理，纯 HTTP 服务可能连接失败

#### 步骤 3：在 Y2A-Auto Web 中生成 API Token

1. 打开 Y2A-Auto Web 界面并登录，默认 `http://localhost:5000`
2. 点击左侧导航 **设置**（页面地址为 `/settings`，页面标题「系统设置」）
3. 点击 **运维与安全** 标签页（也可直接访问 `http://你的地址:5000/settings#vtab-ops`）
4. 在该分组里找到 **Telegram Bot API Token** 卡片（标题上方标注「最小权限 API」，右上角状态默认为「未配置」）
5. 点击 **生成 Token**，在浏览器弹窗中确认（若已配置过，按钮显示为「重置 Token」）
6. ⚠️ **明文 Token 只会显示一次**，出现后请立刻复制整串内容，形如：
   ```
   y2a_tgbot_v1_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
7. 先粘贴到机器人或密码管理器中保存，再关闭页面；关闭页面后无法再次查看，只能重新生成
8. 页面上可随时查看当前状态（是否已配置、Token 尾号、生成时间），并提供 **撤销 Token** 按钮

> 如果「运维与安全」里没有这张卡片，说明主服务版本较旧，请先更新 Y2A-Auto 后重试：
> ```bash
> docker compose pull && docker compose up -d
> ```

关于这个 Token，需要了解：

- 只允许调用 `/tasks/add_via_extension` 提交上传任务（`Authorization: Bearer <Token>`）
- **不能**访问设置、日志、任务管理、维护等接口，也不使用 Web 登录密码
- 生成 / 重置新 Token 会让旧 Token **立即失效**；「撤销 Token」后机器人将无法提交新任务
- Y2A-Auto 只保存 Token 的哈希值，页面仅显示尾号和生成时间，无法反查明文
- 机器人这边会把 Token 存到自己的本地数据库（SQLite `data/app.db` 的 `user_configs.y2a_api_token` 字段），请保护好该数据库文件；不再需要时可用「🧹 清除 Token」或删除配置移除

#### 步骤 4：在机器人中填写 API Token

1. 在设置菜单点击 **🔐 API Token**（首次配置时机器人也会给出「设置 API Token」按钮）
2. 把第 3 步复制的**完整** Token 直接发送给机器人（不要加空格、不要换行、不要只复制一部分）
3. 机器人会校验格式：必须为 `y2a_tgbot_v1_` 开头 + 至少 32 位字母 / 数字 / `-` / `_`；格式错误会提示重新设置
4. 保存成功后，机器人会尝试自动删除您刚发送的 Token 消息（删除失败时请手动撤回该消息）
5. 需要清除时，点击机器人提示中的 **🧹 清除 Token**

#### 步骤 5：测试连接

1. 在设置菜单点击 **🔬 测试**（首次配置完成时机器人也会提供「测试连接」按钮）
2. 机器人会向你的 Y2A-Auto 提交一个空任务来验证「地址 + Token」是否同时有效，返回结果含义：
   - ✅ 连接成功，Token 有效（Y2A-Auto 会返回「YouTube URL不能为空」这类正常回包，说明地址与 Token 都正确）
   - ✅ 服务可达，Token 已通过鉴权（服务返回 400 但提示文案不同，同样表示鉴权通过）
   - ❌ 服务可达，但 Token 无效或权限不足 → Token 被重置 / 撤销 / 复制不完整
   - ⚠️ 服务可达，但返回其他状态码 → 请查看 Y2A-Auto 服务日志
   - ❌ 连接失败，无法连接到服务器 → 检查地址、端口、防火墙
   - ❌ 连接失败，请求超时 → 检查机器人所在网络能否访问该地址
   - ❌ 连接失败，TLS/证书错误 → 改用 `http` 或修正证书配置
3. 测试通过后，直接发送 YouTube 链接即可转发

#### 步骤 6（可选）：设置投稿平台

在设置菜单点击 **🎯 投稿平台**，可指定本次提交到 AcFun、bilibili、双平台，或使用「服务器默认」（即 Y2A-Auto 的 `UPLOAD_TARGET_DEFAULT`）。

#### 连接排查表

| 现象 | 常见原因 | 处理方式 |
| --- | --- | --- |
| 机器人提示「已保存 API 地址，还需要配置专用 API Token」 | 只填了 API 地址 | 完成本教程步骤 3–4 |
| 机器人提示「API Token 格式不正确」 | Token 复制不完整 / 夹带空格 / 错把 Web 密码当成 Token | 重新复制 `y2a_tgbot_v1_` 开头的完整 Token |
| 测试返回 401 / 403 | Token 已被重置、撤销或填错 | 在 Y2A-Auto 设置页重新生成 Token 并更新机器人 |
| 测试返回 404 | 该地址指向的不是 Y2A-Auto（端口被其他服务占用、反向代理改写了路径） | 确认 `http(s)://主机:端口` 能打开 Y2A-Auto 的 Web 界面，并去掉多余的路径改写 |
| 测试超时 / 无法连接 | 机器人无法访问该地址 | 检查端口放行、Docker 网络、反向代理，必要时改用内网 IP |
| 生成 Token 后请求仍被拒绝 | 仍是旧 Token | 重新生成会作废旧 Token，请在机器人中更新为最新 Token |

## 安装和部署

### 环境要求

- Python 3.10+
- Telegram Bot Token（必需）：通过 [@BotFather](https://t.me/BotFather) 创建机器人获取，详见 [教程一](#教程一创建-telegram-机器人并获取-bot-token)
- Y2A-Auto 服务实例（必需）：提供下载与投稿能力，连接方式详见 [教程二](#教程二连接-y2a-auto-服务api-地址与-api-token)

### 方法一：Docker部署 (推荐)

1. **克隆项目**
   ```bash
   git clone https://github.com/fqscfqj/Y2A-Auto-tgbot.git
   cd Y2A-Auto-tgbot
   ```

2. **配置环境变量**
   请为运行环境设置如下变量（示例为 Bash）：
   ```bash
   export TG_BOT_TOKEN=你的_TG_BOT_TOKEN  # 从 @BotFather 获取，见《教程一》
   export ADMIN_TELEGRAM_IDS=123456789,987654321  # 可选，多人用逗号分隔
   ```

   > `TG_BOT_TOKEN` 的获取方式见 [教程一：创建 Telegram 机器人并获取 Bot Token](#教程一创建-telegram-机器人并获取-bot-token)。注意区分 **Bot Token**（形如 `123456789:AAE...`，写在环境变量里）与 **Y2A-Auto API Token**（形如 `y2a_tgbot_v1_...`，在机器人 `/settings` 中填写，不要写进环境变量）。

3. **启动服务**
   编辑 `docker-compose.yml` 填入 `TG_BOT_TOKEN` 等环境变量后执行：
   ```bash
   docker-compose up -d
   ```

### 方法二：本地部署

1. **克隆项目**
   ```bash
   git clone https://github.com/fqscfqj/Y2A-Auto-tgbot.git
   cd Y2A-Auto-tgbot
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境变量**
   ```bash
   # 以 PowerShell 为例（TG_BOT_TOKEN 获取方式见《教程一》）
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
- **配置 API 地址**：输入 Y2A-Auto 服务地址
- **配置 API Token**：粘贴 Y2A-Auto 设置页生成的专用 Token（见 [教程二](#教程二连接-y2a-auto-服务api-地址与-api-token)）
- **测试连接**：验证地址与 Token 是否同时有效
- **完成**：配置成功，可以开始使用

#### 3. 开始使用
配置完成后，直接发送 YouTube 链接即可自动转发。

### 配置 Y2A-Auto 服务（按钮化操作）

完整获取方式（含 API Token 在哪里生成）见 [教程二：连接 Y2A-Auto 服务](#教程二连接-y2a-auto-服务api-地址与-api-token)，界面操作流程如下。

#### 步骤1：打开设置菜单
发送 `/settings` 命令或使用消息下方按钮打开设置。所有操作均通过内联按钮完成：查看配置、设置 API 地址、设置 API Token、设置投稿平台、测试连接、删除配置等。

#### 步骤2：设置 API 地址
1. 点击「🔧 API 地址」
2. 机器人会提示您输入 API 地址（直接发送即可）
3. 输入您的 Y2A-Auto 服务地址，例如：
   ```
   http://localhost:5000
   ```
   也可以直接填写完整接口地址 `http://localhost:5000/tasks/add_via_extension`；只填主机和端口时，机器人会自动补全路径。请务必带上 `http://` 或 `https://`，省略协议时机器人会按 `https://` 处理
4. 确认后，API 地址将被保存

#### 步骤3：设置 API Token（必需）

> ❗ 机器人使用 Y2A-Auto 设置页生成的**专用 Token**，**不再需要** Y2A-Auto 的 Web 登录密码。

1. 在 Y2A-Auto Web 界面点击 **设置 → 运维与安全 → Telegram Bot API Token**（也可直接访问 `/settings#vtab-ops`），点击「生成 Token」并**立即复制**（明文只显示一次）
2. 回到机器人，点击「🔐 API Token」
3. 直接把 `y2a_tgbot_v1_` 开头的完整 Token 发送给机器人
4. 机器人校验格式通过后即保存；如需清除，点击提示中的「🧹 清除 Token」

#### 步骤4：设置投稿平台（可选）
点击「🎯 投稿平台」，可选择 AcFun、bilibili、双平台或「服务器默认」。

#### 步骤5：测试连接
配置完成后，建议测试连接是否正常：
1. 点击「🔬 测试」
2. 机器人将尝试连接到您配置的 Y2A-Auto 服务并返回结果：
   - ✅ 连接成功，Token 有效
   - ⚠️ 服务可达，但返回其他状态码（请检查 Y2A-Auto 服务日志）
   - ❌ 服务可达，但 Token 无效或权限不足（Token 可能已被重置、撤销或复制错误）
   - ❌ 连接失败（请检查 API 地址、端口、防火墙或 TLS 证书）

#### 步骤6：查看配置
可随时点击「🔍 查看」查看当前设置（地址以代码块方式展示，更清晰；API Token 只显示是否已设置）。

#### 修改配置
如果您需要修改配置：
1. 重新执行 `/settings` 命令
2. 选择相应的设置选项进行修改
3. 修改完成后，建议再次测试连接

#### 删除配置
如果您想删除当前配置：
1. 执行 `/settings` 命令
2. 点击「🗑️ 清空」
3. 点击「⚠️ 确认删除」完成操作

⚠️ **注意**：删除操作会清除 API 地址、API Token 与投稿平台偏好，删除后您将无法使用转发功能，除非重新配置。

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
- **未配置服务**：您尚未配置 Y2A-Auto 服务，请使用 `/settings` 命令进行配置
- **缺少 API Token**：只设置了 API 地址，请按 [教程二](#教程二连接-y2a-auto-服务api-地址与-api-token) 在 Y2A-Auto 设置页生成 Token 后填入机器人
- **Token 格式不正确**：Token 复制不完整，或把 Web 登录密码当成了 Token，请重新复制 `y2a_tgbot_v1_` 开头的完整 Token
- **连接失败**：无法连接到 Y2A-Auto 服务，请检查 API 地址、端口与网络
- **认证失败**：Y2A-Auto 拒绝了该 Token，可能已被重置或撤销，请在设置页重新生成
- **服务错误**：Y2A-Auto 服务返回错误，请检查服务状态与日志
- **请求过于频繁**：为避免过载，每个用户每分钟最多允许 30 次转发，请稍后再试

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
| `TG_BOT_TOKEN` | 是 | Telegram 机器人的 Bot Token，通过 [@BotFather](https://t.me/BotFather) 创建机器人获取（见 [教程一](#教程一创建-telegram-机器人并获取-bot-token)） | `123456789:ABCdefGHijKLmnoPqrsTuVwxyz` |
| `ADMIN_TELEGRAM_IDS` | 否 | 管理员的Telegram用户ID列表，多个ID用逗号分隔 | `123456789,987654321` |
| `LOG_LEVEL` | 否 | 日志级别（预留变量，当前版本代码固定输出 INFO，尚未读取该变量） | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

> 📌 **注意区分两种 Token**：
> - `TG_BOT_TOKEN`（Bot Token，形如 `123456789:AAE...`）：机器人自身的凭证，属于**部署者**的环境变量，每个 Bot 只有一个。
> - Y2A-Auto API Token（形如 `y2a_tgbot_v1_...`）：Y2A-Auto 设置页生成的**最小权限接口凭证**，属于**每个用户**自己的配置，只能在机器人 `/settings → 🔐 API Token` 中填写，**不要**放进环境变量。

## 数据目录结构

```
data/
├── app.db          # SQLite数据库文件
└── logs/           # 日志目录（按需生成）
```

## 数据库结构

项目使用SQLite数据库，包含以下表：

- `users`: 用户基本信息
- `user_configs`: 用户 Y2A-Auto 配置（API 地址、API Token、投稿平台）
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
│   │   ├── migration_manager.py
│   │   └── migrations/
│   │       ├── 001_initial.py
│   │       ├── 002_add_user_guides.py
│   │       ├── 003_add_upload_target.py
│   │       └── 004_add_y2a_api_token.py
│   │
│   ├── managers/
│   │   ├── forward_manager.py
│   │   ├── guide_manager.py
│   │   ├── settings_manager.py
│   │   ├── user_manager.py
│   │   ├── session_manager.py
│   │   └── admin_manager.py
│   │
│   ├── handlers/
│   │   ├── command_handlers.py
│   │   └── message_handlers.py
│   │
│   └── utils/
│       ├── config_status.py   # 配置状态与 API Token 格式校验
│       ├── decorators.py
│       ├── error_handler.py
│       ├── memory_monitor.py
│       ├── resource_manager.py
│       └── logger.py
│
├── tests/
│   └── test_user_config_token.py
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

### 运行测试

```bash
python -m unittest discover -s tests
```

当前测试覆盖用户配置中的 `y2a_api_token` 字段、Token 格式校验与配置状态提示（`tests/test_user_config_token.py`）。

## 常见问题

### Q: 如何创建 Telegram 机器人并获取 Bot Token？
A: 在 Telegram 中打开 [@BotFather](https://t.me/BotFather)，发送 `/newbot`，依次设置机器人显示名称和以 `bot` 结尾的用户名，BotFather 返回的 `123456789:AAE...` 就是 Bot Token，填入环境变量 `TG_BOT_TOKEN` 即可。完整步骤与常用 BotFather 指令见 [教程一](#教程一创建-telegram-机器人并获取-bot-token)。

### Q: 配置机器人时让我输入 API Token，这个 Token 如何获取？
A: 这个 Token 由 **Y2A-Auto 服务**生成，不是 Telegram 的 Bot Token。获取步骤如下：
1. 打开并登录 Y2A-Auto Web 界面（默认 `http://localhost:5000`）
2. 进入左侧导航 **设置**（页面地址 `/settings`）
3. 点击 **运维与安全** 标签页（也可直接访问 `http://你的地址:5000/settings#vtab-ops`），找到 **Telegram Bot API Token** 卡片（标注「最小权限 API」）
4. 点击 **生成 Token** 并在弹窗中确认
5. ⚠️ 明文 Token 只会显示一次，请立即复制 `y2a_tgbot_v1_` 开头的整串内容
6. 回到机器人，发送 `/settings` → 点击 **🔐 API Token**，把 Token 直接粘贴发送
7. 点击 **🔬 测试** 验证：提示「连接成功，Token 有效」即可开始转发

该 Token 只允许调用 `/tasks/add_via_extension` 提交上传任务，不能访问设置、日志、任务管理、维护等接口，与 Web 登录密码无关；重新生成或撤销后旧 Token 立即失效。完整说明见 [教程二](#教程二连接-y2a-auto-服务api-地址与-api-token)。

### Q: 机器人提示还需要配置专用 API Token / Token 格式不正确？
A: 机器人要求 **API 地址** 与 **API Token** 同时有效：
- 只填了地址：按上一个问题在 Y2A-Auto 设置页生成 Token 并填写；
- 提示「格式不正确」：Token 复制不完整、夹带空格，或误把 Y2A-Auto 的 Web 登录密码当成 Token，请重新复制 `y2a_tgbot_v1_` 开头的完整 Token（后接至少 32 位字母 / 数字 / `-` / `_`）。

### Q: 如何获取用户ID？
A: 可以通过 [@userinfobot](https://t.me/userinfobot) 获取您的Telegram用户ID。

### Q: 如何获取Y2A-Auto服务的API地址？
A: API 地址就是 Y2A-Auto 服务的任务接口地址，格式为：
```
http(s)://主机:端口/tasks/add_via_extension
```

例如：
```
http://localhost:5000/tasks/add_via_extension
http://192.168.1.100:5000/tasks/add_via_extension
https://y2a.example.com/tasks/add_via_extension
```

在机器人 `/settings → 🔧 API 地址` 中只需填写 `http://主机:端口`，路径会自动补全（省略协议时机器人会按 `https://` 处理，建议显式写上 `http://`）。请确保填写的是**机器人所在环境能访问到**的地址（`localhost` 只在同一台机器 / 同一容器内有效）。

### Q: 还需要填写 Y2A-Auto 的 Web 登录密码吗？
A: 不需要。机器人已改用 Y2A-Auto 设置页生成的专用 API Token（最小权限），不再使用 Web 登录密码，也不会在机器人中保存密码。

### Q: API Token 丢失或怀疑泄露了怎么办？
A: 打开 Y2A-Auto **设置 → 运维与安全 → Telegram Bot API Token**：
- 卡片上的状态可查看是否已配置、Token 尾号与生成时间；
- 点击 **重置 Token** 生成新 Token，旧 Token 立即失效；复制新 Token 后在机器人 `/settings → 🔐 API Token` 中更新；
- 点击 **撤销 Token** 会立即阻止机器人提交新任务，需要时再重新生成即可。

### Q: 为什么转发失败？
A: 转发失败可能有多种原因：
1. **未配置服务**：请使用 `/settings` 命令配置您的 Y2A-Auto 服务（API 地址与 API Token）
2. **API地址错误**：请检查地址与端口，并确认机器人所在环境能访问该地址
3. **Token 无效**：Token 被重置 / 撤销、复制不完整或格式不对，请在 Y2A-Auto 设置页重新生成
4. **服务不可用**：请检查您的 Y2A-Auto 服务是否正常运行（可用 `docker compose logs -f` 查看日志）
5. **网络问题**：请检查网络连接是否正常
6. **触发限流**：每个用户每分钟最多 30 次转发，请稍后再试

### Q: 如何测试我的配置是否正确？
A: 您可以使用 `/settings` 命令中的「🔬 测试」功能来验证您的配置（会检查 API 地址可达性与 Token 鉴权结果）。

### Q: 我可以修改我的配置吗？
A: 是的，您可以随时使用 `/settings` 命令修改您的配置。

### Q: 我可以删除我的配置吗？
A: 是的，您可以使用 `/settings` 命令中的「🗑️ 清空」功能删除您的配置（需二次确认）。

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
机器人会记住您的配置，下次使用时无需重新配置。如果您有多个 Y2A-Auto 服务实例，可以通过 `/settings` 修改 API 地址与 API Token 来切换不同的服务。

### 隐私保护
- 机器人只会记录必要的用户信息（Telegram ID、用户名、姓名）
- 您的 Y2A-Auto 配置（API 地址与 API Token）会被保存在本地 SQLite 数据库中
- 机器人不再接收和保存 Y2A-Auto 的 Web 登录密码；如需修改密码，请直接在 Y2A-Auto Web 界面操作
- 转发记录会被保存，但仅用于统计和故障排除
- 管理员可以查看用户统计信息与配置状态（API 地址、API Token 是否已设置），但无法查看 Token 内容

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