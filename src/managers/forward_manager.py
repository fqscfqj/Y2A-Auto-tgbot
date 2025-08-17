import logging
import os
import requests
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urlunparse
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from src.managers.user_manager import UserManager
from src.database.models import User, UserConfig, ForwardRecord
from src.database.repository import ForwardRecordRepository, UserStatsRepository

logger = logging.getLogger(__name__)

class ForwardManager:
    """转发管理器，负责处理YouTube链接的转发逻辑"""
    @staticmethod
    def normalize_api_url(input_url: str) -> str:
        """规范化用户输入的 API 地址。
        - 允许仅提供主机(含端口)，会自动补全为 /tasks/add_via_extension
        - 去除多余空白和尾部斜杠
        - 保留协议、主机、端口
        """
        if not input_url:
            return input_url
        raw = input_url.strip()
        # 如果没有协议，直接返回原值（上层会校验协议）
        try:
            parsed = urlparse(raw)
        except Exception:
            return raw

        scheme = parsed.scheme
        netloc = parsed.netloc or parsed.path  # 兼容用户粘贴仅主机的情况
        path = parsed.path if parsed.netloc else ""

        # 只接受 http/https；其余交给上层校验
        if scheme not in ("http", "https"):
            return raw

        # 规范化路径，若为空或根路径，则补全；若包含 add_via_extension 则保持（去掉尾部斜杠）
        if not path or path == "/":
            norm_path = "/tasks/add_via_extension"
        elif "add_via_extension" in path:
            norm_path = "/tasks/add_via_extension"
        else:
            # 用户给了其他路径，仍然强制到正确的添加任务接口
            norm_path = "/tasks/add_via_extension"

        # 重新组装，不带用户名密码、查询与片段
        return urlunparse((scheme, netloc, norm_path.rstrip("/"), "", "", ""))
    @staticmethod
    def main_menu_markup(include_example: bool = False) -> InlineKeyboardMarkup:
        """生成主菜单快捷操作按钮"""
        keyboard = [
            [
                InlineKeyboardButton("🚀 开始引导", callback_data="main:start"),
                InlineKeyboardButton("⚙️ 设置", callback_data="main:settings"),
            ],
            [
                InlineKeyboardButton("❓ 帮助", callback_data="main:help"),
            ],
        ]
        if include_example:
            keyboard[1].insert(0, InlineKeyboardButton("🎯 发送示例", callback_data="main:send_example"))
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def is_youtube_url(text: str) -> bool:
        """检查是否为YouTube URL"""
        return (
            text.startswith('https://youtu.be/') or
            text.startswith('http://youtu.be/') or
            'youtube.com/watch' in text or
            'youtube.com/playlist' in text or
            'youtu.be/playlist' in text
        )
    
    @staticmethod
    def parse_api_url(url: str) -> str:
        """解析API URL，提取Basic Auth信息，返回净化url"""
        parsed = urlparse(url)
        # 确保 netloc 为字符串，避免与 None 拼接导致类型错误
        netloc = parsed.hostname or ""
        if parsed.port:
            netloc += f':{parsed.port}'
        # 只替换netloc，不传username和password
        clean_url = urlunparse(parsed._replace(netloc=netloc))
        return clean_url
    
    @staticmethod
    def get_session() -> requests.Session:
        """返回预配置的 requests.Session。"""
        session = requests.Session()
        return session
    
    @staticmethod
    def try_login(session: requests.Session, y2a_api_url: str, y2a_password: Optional[str]) -> bool:
        """如有密码，尝试登录获取session cookie"""
        if not y2a_password:
            return False
        
        login_url = y2a_api_url.replace('/tasks/add_via_extension', '/login')
        try:
            resp = session.post(login_url, data={'password': y2a_password}, timeout=10, allow_redirects=True)
            if resp.ok and ('登录成功' in resp.text or resp.url.endswith('/')):
                logger.info('Y2A-Auto登录成功，已获取session cookie')
                return True
            logger.warning(f'Y2A-Auto登录失败: {resp.status_code}, {resp.text[:100]}')
        except Exception as e:
            logger.error(f'Y2A-Auto登录异常: {e}')
        return False

    @staticmethod
    async def _safe_send(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
        """安全地发送消息：优先使用 message.reply_text，其次使用 bot.send_message，最后尝试回答 callback_query。"""
        message_obj = getattr(update, "effective_message", None) or getattr(update, "message", None)
        if message_obj is not None:
            await message_obj.reply_text(text, reply_markup=reply_markup)
            return

        callback = getattr(update, 'callback_query', None)
        chat = getattr(update, 'effective_chat', None)
        chat_id = getattr(chat, 'id', None)
        if chat_id is not None:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
            return

        if callback is not None:
            # fallback: answer the callback (shows a popup) if no chat available
            await callback.answer(text)
    
    @staticmethod
    async def forward_youtube_url(update: Update, context: ContextTypes.DEFAULT_TYPE, youtube_url: str) -> None:
        """转发YouTube URL到Y2A-Auto"""
        user = await UserManager.ensure_user_registered(update, context)
        
        # 检查用户是否已配置
        # 确保传入的 telegram_id 不为 None，以满足 is_user_configured 的类型要求
        if user.telegram_id is None:
            await ForwardManager._safe_send(update, context, "无法识别您的 Telegram ID，请重新发送 /start 以完成注册。")
            return

        if not UserManager.is_user_configured(user.telegram_id):
            # 检查用户引导状态
            user_id = user.id
            guide = None
            if user_id is not None:
                guide = UserManager.get_user_guide(user_id)
            
            if guide and not guide.is_completed and not guide.is_skipped:
                # 用户正在引导过程中，提示继续引导
                message = update.effective_message or update.message
                await ForwardManager._safe_send(
                    update,
                    context,
                    "您尚未完成配置。请继续引导流程完成配置，或点击下方按钮打开设置。",
                    reply_markup=ForwardManager.main_menu_markup(),
                )
            else:
                # 用户未开始引导或已跳过引导
                await ForwardManager._safe_send(
                    update,
                    context,
                    "您尚未配置Y2A-Auto服务。可点击下方按钮开始引导或进入设置：",
                    reply_markup=ForwardManager.main_menu_markup(),
                )
            return
        
        # 获取用户配置
        user_data = UserManager.get_user_with_config(user.telegram_id)
        config = user_data[1]
        
        if not config or not getattr(config, 'y2a_api_url', None):
            await ForwardManager._safe_send(update, context, "您的Y2A-Auto配置不完整，请使用 /settings 命令重新配置")
            return
        
        # 发送正在转发的消息（安全访问 message）
        message_obj = getattr(update, "effective_message", None) or getattr(update, "message", None)
        if message_obj is not None:
            await message_obj.reply_text('检测到YouTube链接，正在转发到Y2A-Auto...')
        else:
            await ForwardManager._safe_send(update, context, '检测到YouTube链接，正在转发到Y2A-Auto...')

        # 创建转发记录
        forward_record = ForwardRecord(
            user_id=user.id,
            youtube_url=youtube_url,
            status='pending',
            response_message='',
            created_at=datetime.now()
        )

        try:
            # 执行转发
            success, resp_message = await ForwardManager._execute_forward(youtube_url, config)

            # 更新转发记录
            forward_record.status = 'success' if success else 'failed'
            forward_record.response_message = resp_message
            ForwardRecordRepository.create(forward_record)

            # 更新用户统计（仅当 user.id 可用时）
            if user.id is not None:
                UserStatsRepository.increment_stats(user.id, success)
            else:
                logger.warning("无法更新用户统计：user.id 为 None")

            # 发送结果消息
            text = f"✅ 转发成功：{resp_message}" if success else f"❌ 转发失败：{resp_message}"
            if message_obj is not None:
                await message_obj.reply_text(text)
            else:
                await ForwardManager._safe_send(update, context, text)

        except Exception as e:
            # 记录异常并更新转发记录与统计
            logger.exception("转发异常: %s", e)
            forward_record.status = 'failed'
            forward_record.response_message = str(e)
            ForwardRecordRepository.create(forward_record)

            if user.id is not None:
                UserStatsRepository.increment_stats(user.id, False)
            else:
                logger.warning("无法更新用户统计：user.id 为 None")

            err_text = f"❌ 转发异常：{e}"
            if message_obj is not None:
                await message_obj.reply_text(err_text)
            else:
                await ForwardManager._safe_send(update, context, err_text)
    
    @staticmethod
    async def _execute_forward(youtube_url: str, config: UserConfig) -> tuple[bool, str]:
        """执行转发操作"""
        session = ForwardManager.get_session()
        # 确保配置完整
        if not config or not getattr(config, 'y2a_api_url', None):
            return False, "Y2A-Auto API 地址未配置"
        # parse_api_url 需要 str，确保 y2a_api_url 非空字符串
        api_url = config.y2a_api_url
        if api_url is None:
            return False, "Y2A-Auto API 地址未配置"
        clean_url = ForwardManager.parse_api_url(api_url)
        
        try:
            resp = session.post(clean_url, json={'youtube_url': youtube_url}, timeout=10)
            
            # 如果需要登录且配置了密码
            if resp.status_code == 401 and getattr(config, 'y2a_password', None):
                # 尝试登录后重试（确保 api_url 非空）
                api_url = getattr(config, 'y2a_api_url', None)
                if api_url and ForwardManager.try_login(session, api_url, config.y2a_password):
                    resp = session.post(clean_url, json={'youtube_url': youtube_url}, timeout=10)
            
            if resp.ok:
                data = resp.json()
                if data.get('success'):
                    return True, data.get('message', '已添加任务')
                else:
                    return False, data.get('message', '未知错误')
            elif resp.status_code == 401:
                return False, "Y2A-Auto需要登录，且自动登录失败，请检查密码或手动登录Web。"
            else:
                return False, f"Y2A-Auto接口请求失败，状态码：{resp.status_code}"
        
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {e}")
            return False, f"网络请求异常：{e}"
        except Exception as e:
            logger.error(f"转发异常: {e}")
            return False, f"转发异常：{e}"
    
    @staticmethod
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理用户消息，检查是否为YouTube链接并转发"""
        # 确保用户已注册
        user = await UserManager.ensure_user_registered(update, context)

        # 安全获取 message 文本
        message_obj = getattr(update, "effective_message", None) or getattr(update, "message", None)
        raw_text = None
        if message_obj is not None:
            raw_text = getattr(message_obj, 'text', None)
        text = (raw_text or "").strip()

        # 优先处理设置流程：如果用户在设置 API/密码的状态中，应将文本视为输入而非当作链接
        try:
            from src.managers.settings_manager import SettingsState, SettingsManager
            user_data = context.user_data or {}
            pending_input = user_data.get("pending_input")
            if pending_input in ("set_api", "set_password"):
                if pending_input == "set_api":
                    await SettingsManager._set_api_url_end(update, context)
                elif pending_input == "set_password":
                    await SettingsManager._set_password_end(update, context)
                return
        except Exception:
            # 不要阻塞正常流程
            logger.debug("settings fallback handling failed", exc_info=True)

        # 引导流程处理（兜底）
        try:
            from src.database.models import GuideStep
            user_id = getattr(user, 'id', None)
            guide = None
            if user_id is not None:
                guide = UserManager.get_user_guide(user_id)
            if guide and not guide.is_completed and not guide.is_skipped:
                from src.managers.guide_manager import GuideManager
                if guide.current_step == GuideStep.CONFIG_API.value:
                    await GuideManager.handle_api_input(update, context)
                    return
                if guide.current_step == GuideStep.CONFIG_PASSWORD.value:
                    await GuideManager.handle_password_input(update, context)
                    return
        except Exception:
            logger.debug("guide fallback handling failed", exc_info=True)

        # 若不是 YouTube 链接，提示用户
        if not text or not ForwardManager.is_youtube_url(text):
            reply_markup = ForwardManager.main_menu_markup(include_example=True)
            prompt = (
                '请发送有效的YouTube视频或播放列表链接。\n\n也可以使用下方快捷操作：'
            )
            if message_obj is not None:
                await message_obj.reply_text(prompt, reply_markup=reply_markup)
            else:
                await ForwardManager._safe_send(update, context, prompt, reply_markup=reply_markup)
            return

        # 是 YouTube 链接，执行转发
        await ForwardManager.forward_youtube_url(update, context, text)
    
    @staticmethod
    async def test_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, config: UserConfig) -> str:
        """测试Y2A-Auto连接"""
        session = ForwardManager.get_session()
        # 确保配置中包含可用的 api_url
        api_url = getattr(config, 'y2a_api_url', None)
        if not api_url:
            return "❌ Y2A-Auto API 地址未配置"
        clean_url = ForwardManager.parse_api_url(api_url)

        def try_get(url: str, verify: bool | None = None):
            try:
                kwargs = {"timeout": 10, "allow_redirects": True}
                if verify is not None:
                    kwargs["verify"] = verify
                resp = session.get(url, **kwargs)
                return resp, None
            except requests.exceptions.RequestException as e:
                return None, e

        # 1) 首选访问 /login（最轻量且不改动数据）
        login_url = api_url.replace('/tasks/add_via_extension', '/login')

        # 1.1 正常证书校验
        resp, err = try_get(login_url, verify=None)
        # 1.2 若证书问题，允许忽略证书重试
        if err and isinstance(err, requests.exceptions.SSLError):
            resp, err = try_get(login_url, verify=False)

        # 1.3 若仍连接错误且是 https，试试 http 回退
        if (err and isinstance(err, requests.exceptions.ConnectionError)
                and login_url.startswith("https://")):
            http_login = login_url.replace("https://", "http://", 1)
            resp, err = try_get(http_login, verify=None)

        if resp is not None:
            # 能连上服务器
            if resp.status_code == 200:
                if config.y2a_password:
                    if ForwardManager.try_login(session, api_url, config.y2a_password):
                        return "✅ 连接成功，登录成功"
                    return "⚠️ 连接成功，但登录失败，请检查密码"
                return "✅ 连接成功"
            # 401/403 表示服务可达但需要鉴权
            if resp.status_code in (401, 403):
                return "⚠️ 服务可达，但需要登录或权限不足，请检查密码或服务设置"
            # 其余状态码，但已连接上
            return f"⚠️ 服务可达，但返回状态码：{resp.status_code}"

        # 2) /login 不可达，最后尝试目标 API 路径以区分网络问题
        resp2, err2 = try_get(clean_url, verify=None)
        if resp2 is not None:
            if resp2.status_code in (200, 400, 401, 403, 404, 405):
                return f"⚠️ 服务可达（状态码 {resp2.status_code}），但 /login 不可达，请检查服务配置"

        # 3) 仍然不可达，给出更明确的错误提示
        if isinstance(err or err2, requests.exceptions.Timeout):
            return "❌ 连接失败，请求超时"
        if isinstance(err or err2, requests.exceptions.ConnectionError):
            return "❌ 连接失败，无法连接到服务器（网络/端口/防火墙）"
        if isinstance(err or err2, requests.exceptions.SSLError):
            return "❌ 连接失败，TLS/证书错误，可尝试使用 http 或正确配置证书"

        return f"❌ 连接失败：{(err or err2) or '未知错误'}"
    
    @staticmethod
    async def handle_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理帮助命令"""
        from src.handlers.command_handlers import HELP_TEXT
        markup = ForwardManager.main_menu_markup(include_example=True)
        if update.callback_query:
            # try to edit the callback message
            try:
                await update.callback_query.edit_message_text(HELP_TEXT, reply_markup=markup)
            except Exception:
                await ForwardManager._safe_send(update, context, HELP_TEXT, reply_markup=markup)
        else:
            await ForwardManager._safe_send(update, context, HELP_TEXT, reply_markup=markup)
    
    @staticmethod
    async def handle_start_guide_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理开始引导命令"""
        from src.managers.guide_manager import GuideManager
        user = await UserManager.ensure_user_registered(update, context)
        if user.id is None:
            # 如果无法获取 user.id，提示用户重新注册并终止操作，避免将 None 传入只接受 int 的函数
            msg = "无法识别您的用户ID，请重新发送 /start 以完成注册。"
            # 使用安全发送函数
            await ForwardManager._safe_send(update, context, msg)
            return
        guide = UserManager.ensure_user_guide(user.id)
        await GuideManager._continue_guide(update, context, user, guide)
    
    @staticmethod
    async def handle_direct_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理直接配置命令"""
        from src.managers.settings_manager import SettingsManager
        await SettingsManager.settings_command(update, context)