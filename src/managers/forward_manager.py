import logging
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
        """返回requests.Session()，如后续需扩展可在此配置。"""
        return requests.Session()
    
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
                await update.message.reply_text(
                    "您尚未完成配置。请继续引导流程完成配置，或使用 /settings 命令直接配置。"
                )
            else:
                # 用户未开始引导或已跳过引导
                keyboard = [
                    [InlineKeyboardButton("开始引导配置", callback_data="start_guide")],
                    [InlineKeyboardButton("直接配置", callback_data="direct_config")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "您尚未配置Y2A-Auto服务。请选择配置方式：",
                    reply_markup=reply_markup
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
        await update.message.reply_text('检测到YouTube链接，正在转发到Y2A-Auto...')
        
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
                await update.message.reply_text(f"✅ 转发成功：{message}")
            else:
                await update.message.reply_text(f"❌ 转发失败：{message}")
        
        except Exception as e:
            logger.error(f"转发异常: {e}")
            
            # 更新转发记录
            forward_record.status = 'failed'
            forward_record.response_message = str(e)
            ForwardRecordRepository.create(forward_record)
            
            # 更新用户统计
            UserStatsRepository.increment_stats(user.id, False)
            
            await update.message.reply_text(f"❌ 转发异常：{e}")
    
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
        
        if ForwardManager.is_youtube_url(text):
            await ForwardManager.forward_youtube_url(update, context, text)
        else:
            # 检查用户引导状态
            guide = UserManager.get_user_guide(user.id)
            
            if guide and not guide.is_completed and not guide.is_skipped:
                # 用户正在引导过程中，提示继续引导
                await update.message.reply_text(
                    '请发送有效的YouTube视频或播放列表链接。\n'
                    '如果您需要帮助，请输入 /help 查看可用命令。\n'
                    '您也可以继续完成引导流程来配置机器人。'
                )
            else:
                # 提供命令提示
                keyboard = [
                    [InlineKeyboardButton("查看帮助", callback_data="show_help")],
                    [InlineKeyboardButton("开始引导", callback_data="start_guide")],
                    [InlineKeyboardButton("直接配置", callback_data="direct_config")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    '请发送有效的YouTube视频或播放列表链接。\n\n'
                    '🤖 您可以尝试以下操作：',
                    reply_markup=reply_markup
                )
    
    @staticmethod
    async def test_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User, config: UserConfig) -> str:
        """测试Y2A-Auto连接"""
        session = ForwardManager.get_session()
        clean_url = ForwardManager.parse_api_url(config.y2a_api_url)
        
        try:
            # 尝试访问登录页面来测试连接
            login_url = config.y2a_api_url.replace('/tasks/add_via_extension', '/login')
            resp = session.get(login_url, timeout=10)
            
            if resp.status_code == 200:
                # 如果配置了密码，尝试登录
                if config.y2a_password:
                    if ForwardManager.try_login(session, config.y2a_api_url, config.y2a_password):
                        return "✅ 连接成功，登录成功"
                    else:
                        return "⚠️ 连接成功，但登录失败，请检查密码"
                else:
                    return "✅ 连接成功"
            else:
                return f"❌ 连接失败，状态码：{resp.status_code}"
        
        except requests.exceptions.ConnectionError:
            return "❌ 连接失败，无法连接到服务器"
        except requests.exceptions.Timeout:
            return "❌ 连接失败，请求超时"
        except Exception as e:
            return f"❌ 连接失败：{e}"
    
    @staticmethod
    async def handle_config_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """处理配置选择的回调查询"""
        query = update.callback_query
        await query.answer()
        
        user = await UserManager.ensure_user_registered(update, context)
        action = query.data
        
        if action == "show_help":
            # 显示帮助信息
            from src.handlers.command_handlers import CommandHandlers
            await CommandHandlers.help_command(update, context)
        elif action == "start_guide":
            # 开始引导流程
            from src.managers.guide_manager import GuideManager
            guide = UserManager.ensure_user_guide(user.id)
            await GuideManager._continue_guide(update, context, user, guide)
        elif action == "direct_config":
            # 直接配置
            from src.managers.settings_manager import SettingsManager
            await SettingsManager.settings_command(update, context)