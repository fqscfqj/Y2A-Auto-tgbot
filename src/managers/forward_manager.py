import logging
import os
import asyncio
import json
import aiohttp
import requests
from typing import Optional, Tuple, NamedTuple
from urllib.parse import urlparse, urlunparse
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import threading
from collections import defaultdict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.constants import ChatAction

from src.managers.user_manager import UserManager
from src.database.models import User, UserConfig, ForwardRecord
from src.database.repository import ForwardRecordRepository, UserStatsRepository
from src.utils.resource_manager import OperationContext, resource_manager

logger = logging.getLogger(__name__)

# Async HTTP connection pool configuration constants
AIOHTTP_MAX_CONNECTIONS = 20  # Maximum total connections
AIOHTTP_MAX_CONNECTIONS_PER_HOST = 10  # Maximum connections per host
AIOHTTP_DNS_CACHE_TTL = 300  # DNS cache TTL in seconds
AIOHTTP_TOTAL_TIMEOUT = 30  # Total request timeout in seconds
AIOHTTP_CONNECT_TIMEOUT = 10  # Connection timeout in seconds

# Async HTTP session for non-blocking requests
_aiohttp_session: Optional[aiohttp.ClientSession] = None
_aiohttp_lock = asyncio.Lock()


class SimpleResponse(NamedTuple):
    """Simple response object for async HTTP requests."""
    status: int
    ok: bool


async def get_aiohttp_session() -> aiohttp.ClientSession:
    """Get or create an async HTTP session with connection pooling."""
    global _aiohttp_session
    async with _aiohttp_lock:
        if _aiohttp_session is None or _aiohttp_session.closed:
            timeout = aiohttp.ClientTimeout(
                total=AIOHTTP_TOTAL_TIMEOUT, 
                connect=AIOHTTP_CONNECT_TIMEOUT
            )
            connector = aiohttp.TCPConnector(
                limit=AIOHTTP_MAX_CONNECTIONS,
                limit_per_host=AIOHTTP_MAX_CONNECTIONS_PER_HOST,
                ttl_dns_cache=AIOHTTP_DNS_CACHE_TTL,
                enable_cleanup_closed=True
            )
            _aiohttp_session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            )
    return _aiohttp_session


async def cleanup_aiohttp_session() -> None:
    """Cleanup the async HTTP session. Public function for shutdown."""
    global _aiohttp_session
    async with _aiohttp_lock:
        if _aiohttp_session and not _aiohttp_session.closed:
            await _aiohttp_session.close()
            _aiohttp_session = None
            logger.info("异步HTTP会话已关闭")

class RateLimiter:
    """简单的速率限制器"""
    
    def __init__(self, max_requests: int = 10, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(list)
        self.lock = threading.Lock()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._cleanup_running = False
    
    def start_cleanup(self, interval: int = 30):
        """启动定期清理线程"""
        if self._cleanup_running:
            return
        
        self._cleanup_running = True
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, args=(interval,), daemon=True)
        self._cleanup_thread.start()
        logger.info(f"速率限制器清理线程已启动，清理间隔: {interval}秒")
    
    def stop_cleanup(self):
        """停止清理线程"""
        self._cleanup_running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
    
    def _cleanup_loop(self, interval: int):
        """清理循环"""
        while self._cleanup_running:
            try:
                self._cleanup_expired_requests()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"速率限制器清理异常: {e}")
                time.sleep(interval)
    
    def _cleanup_expired_requests(self):
        """清理过期的请求记录"""
        current_time = time.time()
        with self.lock:
            # 清理所有用户的过期请求
            for key in list(self.requests.keys()):
                self.requests[key] = [
                    req_time for req_time in self.requests[key]
                    if current_time - req_time < self.time_window
                ]
                # 如果该用户没有请求了，删除这个key以节省内存
                if not self.requests[key]:
                    del self.requests[key]
    
    def is_allowed(self, key: str) -> bool:
        """检查是否允许请求"""
        current_time = time.time()
        
        with self.lock:
            # 直接过滤并检查时间窗口内的请求
            recent_requests = [
                req_time for req_time in self.requests.get(key, [])
                if current_time - req_time < self.time_window
            ]
            
            # 检查是否超过限制
            if len(recent_requests) >= self.max_requests:
                return False
            
            # 记录新请求
            recent_requests.append(current_time)
            self.requests[key] = recent_requests
            return True

class ForwardManager:
    """转发管理器，负责处理YouTube链接的转发逻辑"""
    
    # 全局HTTP会话实例，支持连接池
    _http_session: Optional[requests.Session] = None
    # 速率限制器
    _rate_limiter = RateLimiter(max_requests=30, time_window=60)  # 每分钟最多30个请求
    # 标记是否已初始化
    _initialized = False
    
    @classmethod
    def _ensure_initialized(cls):
        """确保速率限制器已初始化"""
        if not cls._initialized:
            cls._rate_limiter.start_cleanup(interval=60)  # 每60秒清理一次
            cls._initialized = True
    
    @classmethod
    def _get_http_session(cls) -> requests.Session:
        """获取全局HTTP会话实例，支持连接池和重试机制"""
        cls._ensure_initialized()  # 确保初始化
        
        if cls._http_session is None:
            cls._http_session = requests.Session()
            
            # 配置重试策略
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
            )
            
            # 配置HTTP适配器
            adapter = HTTPAdapter(
                max_retries=retry_strategy,
                pool_connections=10,  # 连接池大小
                pool_maxsize=20,      # 最大连接数
                pool_block=False      # 非阻塞模式
            )
            
            cls._http_session.mount("http://", adapter)
            cls._http_session.mount("https://", adapter)
            
        return cls._http_session
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
                InlineKeyboardButton("⚙️ 设置", callback_data="main:settings"),
                InlineKeyboardButton("❓ 帮助", callback_data="main:help"),
            ],
        ]
        if include_example:
            keyboard.insert(0, [InlineKeyboardButton("🎯 发送示例", callback_data="main:send_example")])
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
        return ForwardManager._get_http_session()
    
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
    def _check_login_markers(content_type: str, text_raw: str) -> bool:
        """Check if content type and text contain login page markers.
        
        This is the common logic used by both _looks_like_login_html and 
        _looks_like_login_html_from_text to avoid code duplication.
        """
        content_type_lower = content_type.lower()
        if 'application/json' in content_type_lower:
            return False

        text_lower = text_raw.lower()
        looks_like_html = (
            'text/html' in content_type_lower
            or text_lower.startswith('<!doctype html')
            or text_lower.startswith('<html')
        )
        if not looks_like_html:
            return False

        markers = (
            '<html',
            'login',
            '登录',
            '<title>登录',
            'name="password"',
            'form action="/login',
        )
        return any(marker in text_lower for marker in markers)

    @staticmethod
    def _looks_like_login_html(resp: requests.Response) -> bool:
        """粗略判断返回是否为登录页 HTML，避免误将登录页当作成功结果。"""
        content_type = resp.headers.get('Content-Type') or ''
        text_raw = resp.text or ''
        return ForwardManager._check_login_markers(content_type, text_raw)

    @staticmethod
    def _looks_like_login_html_from_text(content_type: str, text_raw: str) -> bool:
        """Check if response text looks like a login HTML page (for async usage)."""
        return ForwardManager._check_login_markers(content_type, text_raw)

    @staticmethod
    async def _async_try_login(session: aiohttp.ClientSession, y2a_api_url: str, y2a_password: Optional[str]) -> bool:
        """Async version: attempt login to get session cookie."""
        if not y2a_password:
            return False
        
        login_url = y2a_api_url.replace('/tasks/add_via_extension', '/login')
        try:
            async with session.post(login_url, data={'password': y2a_password}, allow_redirects=True) as resp:
                text = await resp.text()
                if resp.ok and ('登录成功' in text or str(resp.url).endswith('/')):
                    logger.info('Y2A-Auto登录成功（异步），已获取session cookie')
                    return True
                logger.warning(f'Y2A-Auto登录失败（异步）: {resp.status}, {text[:100]}')
        except Exception as e:
            logger.error(f'Y2A-Auto登录异常（异步）: {e}')
        return False

    @staticmethod
    async def _send_typing_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send typing indicator to show the bot is processing."""
        try:
            chat = update.effective_chat
            if chat:
                await context.bot.send_chat_action(chat_id=chat.id, action=ChatAction.TYPING)
        except Exception as e:
            logger.debug(f"Failed to send typing action: {e}")

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

        # 检查服务器是否过载
        if resource_manager.is_overloaded():
            await ForwardManager._safe_send(
                update, 
                context, 
                "服务器当前负载较高，请稍后再试。"
            )
            return

        # 速率限制检查
        user_key = f"user_{user.telegram_id}"
        if not ForwardManager._rate_limiter.is_allowed(user_key):
            await ForwardManager._safe_send(
                update, 
                context, 
                "请求过于频繁，请稍后再试。为了服务器稳定性，每分钟最多允许30个请求。"
            )
            return

        # 使用资源管理器进行操作
        try:
            with OperationContext(user_id=user.telegram_id, operation_name="forward_youtube"):
                await ForwardManager._forward_youtube_internal(update, context, youtube_url, user)
        except RuntimeError as e:
            await ForwardManager._safe_send(update, context, f"服务器繁忙: {str(e)}")
            return

    @staticmethod 
    async def _forward_youtube_internal(update: Update, context: ContextTypes.DEFAULT_TYPE, youtube_url: str, user: User) -> None:
        """内部转发逻辑，已在资源管理器保护下"""
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
        
        # 发送typing指示器，让用户知道机器人正在处理
        await ForwardManager._send_typing_action(update, context)
        
        if message_obj is not None:
            await message_obj.reply_text('🔄 检测到YouTube链接，正在转发到Y2A-Auto...')
        else:
            await ForwardManager._safe_send(update, context, '🔄 检测到YouTube链接，正在转发到Y2A-Auto...')

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
    async def _execute_forward(youtube_url: str, config: UserConfig) -> Tuple[bool, str]:
        """执行转发操作 - 使用异步HTTP请求"""
        # 确保配置完整
        if not config or not getattr(config, 'y2a_api_url', None):
            return False, "Y2A-Auto API 地址未配置"
        api_url = config.y2a_api_url
        if api_url is None:
            return False, "Y2A-Auto API 地址未配置"
        clean_url = ForwardManager.parse_api_url(api_url)
        
        # 构建请求体，包含可选的upload_target
        request_body: dict = {'youtube_url': youtube_url}
        upload_target = getattr(config, 'upload_target', None)
        if upload_target:
            request_body['upload_target'] = upload_target

        login_attempted = False
        session = await get_aiohttp_session()
        
        max_attempts = 2
        try:
            for attempt in range(max_attempts):  # 最多重试一次（自动登录后再重发）
                try:
                    async with session.post(clean_url, json=request_body) as resp:
                        status = resp.status
                        content_type = resp.headers.get('Content-Type', '')
                        text = await resp.text()

                        # 401 明确需要登录
                        if status == 401:
                            if getattr(config, 'y2a_password', None) and not login_attempted:
                                if api_url and await ForwardManager._async_try_login(session, api_url, config.y2a_password):
                                    login_attempted = True
                                    continue
                                return False, "Y2A-Auto需要登录，自动登录失败，请检查密码或手动登录Web。"
                            return False, "Y2A-Auto需要登录，请在设置中填写密码。"

                        # 返回登录页 HTML（未返回401，但实际未登录）
                        if ForwardManager._looks_like_login_html_from_text(content_type, text):
                            if getattr(config, 'y2a_password', None) and not login_attempted:
                                if api_url and await ForwardManager._async_try_login(session, api_url, config.y2a_password):
                                    login_attempted = True
                                    continue
                                return False, "Y2A-Auto需要登录，自动登录失败，请检查密码或手动登录Web。"
                            return False, "Y2A-Auto需要登录，请在设置中填写密码或先在Web登录后重试。"

                        if 200 <= status < 300:
                            try:
                                data = json.loads(text)
                            except json.JSONDecodeError:
                                body_preview = text.strip()[:200]
                                if len(text.strip()) > 200:
                                    body_preview += '...'
                                logger.error(
                                    "Y2A-Auto 返回非 JSON 响应，状态码=%s，响应体预览=%s",
                                    status,
                                    body_preview,
                                )
                                return False, "Y2A-Auto 返回非 JSON 响应，请检查服务是否正常"
                            if data.get('success'):
                                return True, data.get('message', '已添加任务')
                            else:
                                return False, data.get('message', '未知错误')
                        else:
                            return False, f"Y2A-Auto接口请求失败，状态码：{status}"

                except asyncio.TimeoutError:
                    logger.warning("Y2A-Auto 请求超时，尝试重试（attempt=%s）", attempt)
                    if attempt < max_attempts - 1:
                        # 还有重试机会，继续下一轮
                        continue
                    return False, "请求超时，请检查网络连接或服务器状态"
                except aiohttp.ClientError as e:
                    logger.error("异步请求客户端异常 (attempt=%s): %s", attempt, e)
                    if attempt < max_attempts - 1:
                        # 还有重试机会，继续下一轮
                        continue
                    return False, f"网络请求异常：{e}"

            return False, "Y2A-Auto请求失败，已尝试自动登录"

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

        # 优先处理设置流程：如果用户在设置 API/密码的状态中
        try:
            from src.managers.settings_manager import SettingsManager
            user_data = context.user_data or {}
            pending_input = user_data.get("pending_input")
            if pending_input == "set_api":
                await SettingsManager._set_api_url_end(update, context)
                return
            elif pending_input == "set_password":
                await SettingsManager._set_password_end(update, context)
                return
        except Exception:
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
        except Exception:
            logger.debug("guide fallback handling failed", exc_info=True)

        # 若不是 YouTube 链接，提示用户
        if not text or not ForwardManager.is_youtube_url(text):
            reply_markup = ForwardManager.main_menu_markup(include_example=True)
            prompt = '请发送 YouTube 视频或播放列表链接。'
            if message_obj is not None:
                await message_obj.reply_text(prompt, reply_markup=reply_markup)
            else:
                await ForwardManager._safe_send(update, context, prompt, reply_markup=reply_markup)
            return

        # 是 YouTube 链接，执行转发
        await ForwardManager.forward_youtube_url(update, context, text)
    
    @staticmethod
    async def test_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, config: UserConfig) -> str:
        """测试Y2A-Auto连接 - 使用异步HTTP请求"""
        # 发送typing指示器
        await ForwardManager._send_typing_action(update, context)
        
        # 确保配置中包含可用的 api_url
        api_url = getattr(config, 'y2a_api_url', None)
        if not api_url:
            return "❌ Y2A-Auto API 地址未配置"
        clean_url = ForwardManager.parse_api_url(api_url)
        
        session = await get_aiohttp_session()

        async def try_get(url: str, ssl: Optional[bool] = None) -> Tuple[Optional[SimpleResponse], Optional[Exception]]:
            temp_session: Optional[aiohttp.ClientSession] = None
            try:
                if ssl is False:
                    # Create a new session with SSL verification disabled
                    connector = aiohttp.TCPConnector(ssl=False)
                    temp_session = aiohttp.ClientSession(
                        connector=connector,
                        timeout=aiohttp.ClientTimeout(total=10)
                    )
                    async with temp_session.get(url, allow_redirects=True) as resp:
                        status = resp.status
                        return SimpleResponse(status=status, ok=200 <= status < 300), None
                else:
                    async with session.get(url, allow_redirects=True) as resp:
                        status = resp.status
                        return SimpleResponse(status=status, ok=200 <= status < 300), None
            except (aiohttp.ClientSSLError, aiohttp.ClientConnectorError, asyncio.TimeoutError, Exception) as e:
                return None, e
            finally:
                if temp_session is not None and not temp_session.closed:
                    try:
                        await temp_session.close()
                    except Exception as close_err:
                        logger.warning("Failed to close temporary aiohttp session: %s", close_err)

        # 1) 首选访问 /login（最轻量且不改动数据）
        login_url = api_url.replace('/tasks/add_via_extension', '/login')

        # 1.1 正常证书校验
        resp, err = await try_get(login_url)
        
        # 1.2 若证书问题，允许忽略证书重试
        if err and isinstance(err, aiohttp.ClientSSLError):
            resp, err = await try_get(login_url, ssl=False)

        # 1.3 若仍连接错误且是 https，试试 http 回退
        if err and isinstance(err, aiohttp.ClientConnectorError) and login_url.startswith("https://"):
            http_login = login_url.replace("https://", "http://", 1)
            resp, err = await try_get(http_login)

        if resp is not None:
            # 能连上服务器
            if resp.status == 200:
                if config.y2a_password:
                    if await ForwardManager._async_try_login(session, api_url, config.y2a_password):
                        return "✅ 连接成功，登录成功"
                    return "⚠️ 连接成功，但登录失败，请检查密码"
                return "✅ 连接成功"
            # 401/403 表示服务可达但需要鉴权
            if resp.status in (401, 403):
                return "⚠️ 服务可达，但需要登录或权限不足，请检查密码或服务设置"
            # 其余状态码，但已连接上
            return f"⚠️ 服务可达，但返回状态码：{resp.status}"

        # 2) /login 不可达，最后尝试目标 API 路径以区分网络问题
        resp2, err2 = await try_get(clean_url)
        if resp2 is not None:
            if resp2.status in (200, 400, 401, 403, 404, 405):
                return f"⚠️ 服务可达（状态码 {resp2.status}），但 /login 不可达，请检查服务配置"

        # 3) 仍然不可达，给出更明确的错误提示
        final_err = err or err2
        if isinstance(final_err, asyncio.TimeoutError):
            return "❌ 连接失败，请求超时"
        if isinstance(final_err, aiohttp.ClientConnectorError):
            return "❌ 连接失败，无法连接到服务器（网络/端口/防火墙）"
        if isinstance(final_err, aiohttp.ClientSSLError):
            return "❌ 连接失败，TLS/证书错误，可尝试使用 http 或正确配置证书"

        return f"❌ 连接失败：{final_err or '未知错误'}"
    
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