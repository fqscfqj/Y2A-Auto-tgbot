import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from urllib.parse import urlparse, urlunparse

# 配置区
TELEGRAM_TOKEN = os.getenv('TG_BOT_TOKEN', 'YOUR_TELEGRAM_BOT_TOKEN')  # 建议用环境变量
Y2A_AUTO_API_RAW = os.getenv('Y2A_AUTO_API', 'http://localhost:5000')
Y2A_PASSWORD = os.getenv('Y2A_PASSWORD', '')

# 自动补全API路径
if not Y2A_AUTO_API_RAW.rstrip('/').endswith('/tasks/add_via_extension'):
    Y2A_AUTO_API = Y2A_AUTO_API_RAW.rstrip('/') + '/tasks/add_via_extension'
else:
    Y2A_AUTO_API = Y2A_AUTO_API_RAW

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

HELP_TEXT = (
    "本机器人用于转发YouTube链接到Y2A-Auto。\n"
    "直接发送YouTube视频链接即可自动转发。\n"
    "命令：\n"
    "/start - 机器人介绍\n"
    "/help - 显示帮助信息"
)

def parse_api_url(url):
    """解析API URL，提取Basic Auth信息，返回净化url"""
    parsed = urlparse(url)
    netloc = parsed.hostname
    if parsed.port:
        netloc += f':{parsed.port}'
    # 只替换netloc，不传username和password
    clean_url = urlunparse(parsed._replace(netloc=netloc))
    return clean_url

def get_session():
    """返回requests.Session()，如后续需扩展可在此配置。"""
    return requests.Session()

def try_login(session):
    """如有密码，尝试登录获取session cookie"""
    if not Y2A_PASSWORD:
        return False
    login_url = Y2A_AUTO_API.replace('/tasks/add_via_extension', '/login')
    try:
        resp = session.post(login_url, data={'password': Y2A_PASSWORD}, timeout=10, allow_redirects=True)
        if resp.ok and ('登录成功' in resp.text or resp.url.endswith('/')):
            logger.info('Y2A-Auto登录成功，已获取session cookie')
            return True
        logger.warning(f'Y2A-Auto登录失败: {resp.status_code}, {resp.text[:100]}')
    except Exception as e:
        logger.error(f'Y2A-Auto登录异常: {e}')
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "欢迎使用YouTube转发机器人！\n" + HELP_TEXT
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT)

def is_youtube_url(text: str) -> bool:
    return (
        text.startswith('https://youtu.be/') or
        text.startswith('http://youtu.be/') or
        'youtube.com/watch' in text or
        'youtube.com/playlist' in text or
        'youtu.be/playlist' in text
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    if is_youtube_url(text):
        await update.message.reply_text('检测到YouTube链接，正在转发到Y2A-Auto...')
        session = get_session()
        clean_url = parse_api_url(Y2A_AUTO_API)
        try:
            resp = session.post(clean_url, json={'youtube_url': text}, timeout=10)
            if resp.status_code == 401 and Y2A_PASSWORD:
                # 尝试登录后重试
                if try_login(session):
                    resp = session.post(clean_url, json={'youtube_url': text}, timeout=10)
            if resp.ok:
                data = resp.json()
                if data.get('success'):
                    await update.message.reply_text(f"转发成功：{data.get('message','已添加任务')}")
                else:
                    await update.message.reply_text(f"转发失败：{data.get('message','未知错误')}")
            elif resp.status_code == 401:
                await update.message.reply_text("Y2A-Auto需要登录，且自动登录失败，请检查密码或手动登录Web。")
            else:
                await update.message.reply_text(f"Y2A-Auto接口请求失败，状态码：{resp.status_code}")
        except Exception as e:
            logger.error(f"转发异常: {e}")
            await update.message.reply_text(f"转发异常：{e}")
    else:
        await update.message.reply_text('请发送有效的YouTube视频或播放列表链接。\n输入 /help 获取帮助。')

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Telegram bot started...")
    application.run_polling()

if __name__ == "__main__":
    main() 