# Telegram YouTube转发机器人

本机器人用于接收你从YouTube App分享的视频或播放列表链接，并自动转发到Y2A-Auto项目，实现一键添加搬运任务。

## 功能简介
- 支持接收YouTube视频/播放列表链接
- 自动转发到Y2A-Auto的 `/tasks/add_via_extension` 接口
- 支持/start 和 /help 命令

## 依赖
- python-telegram-bot==20.7
- requests

安装依赖：
```bash
pip install -r requirements.txt
```

## 配置
- 需在环境变量中设置 Telegram Bot Token：
  - `TG_BOT_TOKEN` 你的Telegram机器人Token
- 如需自定义Y2A-Auto API地址，可设置：
  - `Y2A_AUTO_API` 例如 `http://localhost:5000/tasks/add_via_extension`

## 运行
```bash
cd test
python tg_youtube_forward_bot.py
```

## 使用
- 在Telegram中向机器人发送YouTube链接即可。
- 支持YouTube视频和播放列表链接。
- 输入 /help 获取帮助信息。

---
如需关闭机器人，直接Ctrl+C终止进程即可。 

## Docker 部署

### 1. 构建镜像
```bash
cd test
# 构建镜像（可自定义tag）
docker build -f Dockerfile.tg_youtube_forward_bot -t tg_youtube_forward_bot .
```

### 2. 运行容器
```bash
docker run -d --name tg_youtube_forward_bot \
  -e TG_BOT_TOKEN=你的TelegramBotToken \
  -e Y2A_AUTO_API=http://host.docker.internal:5000/tasks/add_via_extension \
  tg_youtube_forward_bot
```

### 3. 使用 docker-compose
```bash
docker-compose -f docker-compose.tg_youtube_forward_bot.yml up -d
```

- 可在 `docker-compose.tg_youtube_forward_bot.yml` 中修改环境变量。
- 推荐 `Y2A_AUTO_API` 使用 `http://host.docker.internal:5000/tasks/add_via_extension` 以便容器访问宿主机服务。

--- 

## 密码保护兼容
- 支持Y2A-Auto的密码保护模式：
  - 只需设置环境变量 `Y2A_PASSWORD`，机器人会自动登录获取session cookie。
  - 若遇到401会自动尝试登录。
- 如需公网部署，建议使用HTTPS并妥善管理密码。 