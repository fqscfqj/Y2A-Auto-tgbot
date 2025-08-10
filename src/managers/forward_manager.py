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
        netloc = parsed.hostname
        if parsed.port:
            netloc += f':{parsed.port}'
        # 只替换netloc，不传username和password
        clean_url = urlunparse(parsed._replace(netloc=netloc))
        return clean_url
    
    @staticmethod
    def get_session() -> requests.Session:
        """返回预配置的 requests.Session。
        - 默认强制使用 IPv4（很多 Docker 环境缺少 IPv6，避免优先走 AAAA 导致连不上）
        - 可通过环境变量 FORCE_IPV4=0 关闭此行为
        """
        session = requests.Session()
        if os.getenv("FORCE_IPV4", "1") == "1":
            try:
                import socket
                import urllib3.util.connection as urllib3_connection

                def _allowed_gai_family() -> int:
                    return socket.AF_INET

                urllib3_connection.allowed_gai_family = _allowed_gai_family
                logger.info("已启用 IPv4 优先策略 (FORCE_IPV4=1)")
            except Exception as e:
                logger.warning(f"启用 IPv4 优先策略失败: {e}")
        return session
    
    @staticmethod
    def try_login(session: requests.Session, y2a_api_url: str, y2a_password: str) -> bool:
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
    async def forward_youtube_url(update: Update, context: ContextTypes.DEFAULT_TYPE, youtube_url: str) -> None:
        """转发YouTube URL到Y2A-Auto"""
        user = await UserManager.ensure_user_registered(update, context)
        
        # 检查用户是否已配置
        if not UserManager.is_user_configured(user.telegram_id):
            # 检查用户引导状态
            guide = UserManager.get_user_guide(user.id)
            
            if guide and not guide.is_completed and not guide.is_skipped:
                # 用户正在引导过程中，提示继续引导
                message = update.effective_message
                await message.reply_text(
                    "您尚未完成配置。请继续引导流程完成配置，或点击下方按钮打开设置。",
                    reply_markup=ForwardManager.main_menu_markup()
                )
            else:
                # 用户未开始引导或已跳过引导
                message = update.effective_message
                await message.reply_text(
                    "您尚未配置Y2A-Auto服务。可点击下方按钮开始引导或进入设置：",
                    reply_markup=ForwardManager.main_menu_markup()
                )
            return
        
        # 获取用户配置
        user_data = UserManager.get_user_with_config(user.telegram_id)
        config = user_data[1]
        
        if not config or not config.y2a_api_url:
            await update.message.reply_text(
                "您的Y2A-Auto配置不完整，请使用 /settings 命令重新配置"
            )
            return
        
        # 发送正在转发的消息
        message = update.effective_message
        await message.reply_text('检测到YouTube链接，正在转发到Y2A-Auto...')
        
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
            success, message = await ForwardManager._execute_forward(youtube_url, config)
            
            # 更新转发记录
            forward_record.status = 'success' if success else 'failed'
            forward_record.response_message = message
            ForwardRecordRepository.create(forward_record)
            
            # 更新用户统计
            UserStatsRepository.increment_stats(user.id, success)
            
            # 发送结果消息
            if success:
                await update.effective_message.reply_text(f"✅ 转发成功：{message}")
            else:
                await update.effective_message.reply_text(f"❌ 转发失败：{message}")
        
        except Exception as e:
            logger.error(f"转发异常: {e}")
            
            # 更新转发记录
            forward_record.status = 'failed'
            forward_record.response_message = str(e)
            ForwardRecordRepository.create(forward_record)
            
            # 更新用户统计
            UserStatsRepository.increment_stats(user.id, False)
            
            await update.effective_message.reply_text(f"❌ 转发异常：{e}")
    
    @staticmethod
    async def _execute_forward(youtube_url: str, config: UserConfig) -> tuple[bool, str]:
        """执行转发操作"""
        session = ForwardManager.get_session()
        clean_url = ForwardManager.parse_api_url(config.y2a_api_url)
        
        try:
            resp = session.post(clean_url, json={'youtube_url': youtube_url}, timeout=10)
            
            # 如果需要登录且配置了密码
            if resp.status_code == 401 and config.y2a_password:
                # 尝试登录后重试
                if ForwardManager.try_login(session, config.y2a_api_url, config.y2a_password):
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
        user = await UserManager.ensure_user_registered(update, context)
        text = update.message.text.strip()
        
        # 优先处理设置流程：如果用户在设置 API/密码的状态中，应将文本视为输入而非当作链接
        from src.managers.settings_manager import SettingsState
        user_data = context.user_data
        # ConversationHandler 通常管理状态在内部，这里额外根据提示语与最近动作进行兜底判断：
        pending_input = user_data.get("pending_input")
        if pending_input in ("set_api", "set_password"):
            # 兜底处理：若当前不是由 ConversationHandler 接管（例如通过主菜单按钮进入设置），
            # 则直接调用对应的设置处理函数完成保存，避免用户输入被当作普通消息忽略。
            try:
                from src.managers.settings_manager import SettingsManager
                if pending_input == "set_api":
                    await SettingsManager._set_api_url_end(update, context)
                elif pending_input == "set_password":
                    await SettingsManager._set_password_end(update, context)
            finally:
                # 无论是否成功，均停止后续作为普通消息的处理
                return

        # 兜底处理引导流程：若用户正处于引导步骤中的“配置 API/密码”，
        # 且当前并非由 ConversationHandler 接管（例如通过主菜单按钮进入引导），
        # 则将本次文本输入交给引导的对应处理函数，避免用户感觉“卡住”。
        try:
            from src.database.models import GuideStep
            guide = UserManager.get_user_guide(user.id)
            if guide and not guide.is_completed and not guide.is_skipped:
                if guide.current_step == GuideStep.CONFIG_API.value:
                    from src.managers.guide_manager import GuideManager
                    await GuideManager.handle_api_input(update, context)
                    return
                if guide.current_step == GuideStep.CONFIG_PASSWORD.value:
                    from src.managers.guide_manager import GuideManager
                    await GuideManager.handle_password_input(update, context)
                    return
        except Exception as _:
            # 兜底逻辑不应影响正常流程，忽略异常
            pass

        if ForwardManager.is_youtube_url(text):
            await ForwardManager.forward_youtube_url(update, context, text)
        else:
            # 检查用户引导状态
            guide = UserManager.get_user_guide(user.id)
            
            if guide and not guide.is_completed and not guide.is_skipped:
                # 用户正在引导过程中，提示继续引导
                await update.effective_message.reply_text(
                    '请发送有效的YouTube视频或播放列表链接。\n\n您也可以点击下方按钮继续引导或打开设置。',
                    reply_markup=ForwardManager.main_menu_markup()
                )
            else:
                # 提供命令提示
                await update.effective_message.reply_text(
                    '请发送有效的YouTube视频或播放列表链接。\n\n也可以使用下方快捷操作：',
                    reply_markup=ForwardManager.main_menu_markup(include_example=True)
                )
    
    @staticmethod
    async def test_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, config: UserConfig) -> str:
        """测试Y2A-Auto连接"""
        session = ForwardManager.get_session()
        clean_url = ForwardManager.parse_api_url(config.y2a_api_url)

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
        login_url = config.y2a_api_url.replace('/tasks/add_via_extension', '/login')

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
                    if ForwardManager.try_login(session, config.y2a_api_url, config.y2a_password):
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
            await update.callback_query.edit_message_text(HELP_TEXT, reply_markup=markup)
        else:
            await update.effective_message.reply_text(HELP_TEXT, reply_markup=markup)
    
    @staticmethod
    async def handle_start_guide_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理开始引导命令"""
        from src.managers.guide_manager import GuideManager
        user = await UserManager.ensure_user_registered(update, context)
        guide = UserManager.ensure_user_guide(user.id)
        await GuideManager._continue_guide(update, context, user, guide)
    
    @staticmethod
    async def handle_direct_config_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理直接配置命令"""
        from src.managers.settings_manager import SettingsManager
        await SettingsManager.settings_command(update, context)