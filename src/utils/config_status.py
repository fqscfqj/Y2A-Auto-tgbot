from dataclasses import dataclass
from typing import Optional

from src.database.models import UserConfig


TG_BOT_API_TOKEN_PREFIX = "y2a_tgbot_v1_"


@dataclass(frozen=True)
class ConfigStatus:
    api_url: str
    upload_target: Optional[str]
    has_api_url: bool
    has_api_token: bool
    has_valid_api_token: bool
    is_ready: bool
    next_action: str
    next_label: str
    summary: str


def is_tgbot_api_token(token: str) -> bool:
    token = str(token or "").strip()
    if not token.startswith(TG_BOT_API_TOKEN_PREFIX):
        return False
    random_part = token[len(TG_BOT_API_TOKEN_PREFIX):]
    return len(random_part) >= 32 and all(ch.isalnum() or ch in "_-" for ch in random_part)


def get_config_status(config: Optional[UserConfig]) -> ConfigStatus:
    api_url = str(getattr(config, "y2a_api_url", None) or "").strip()
    api_token = str(getattr(config, "y2a_api_token", None) or "").strip()
    upload_target = getattr(config, "upload_target", None) if config else None

    has_api_url = bool(api_url)
    has_api_token = bool(api_token)
    has_valid_api_token = is_tgbot_api_token(api_token) if has_api_token else False
    is_ready = has_api_url and has_valid_api_token

    if not has_api_url:
        next_action = "set_api"
        next_label = "设置 API 地址"
        summary = "还没有连接到您的 Y2A-Auto 服务。"
    elif not has_api_token:
        next_action = "set_api_token"
        next_label = "设置 API Token"
        summary = "已保存 API 地址，还需要配置专用 API Token。"
    elif not has_valid_api_token:
        next_action = "set_api_token"
        next_label = "重新设置 API Token"
        summary = "API Token 格式不正确，请重新复制主服务生成的完整 Token。"
    else:
        next_action = "test"
        next_label = "测试连接"
        summary = "配置已完整，可以发送 YouTube 链接。"

    return ConfigStatus(
        api_url=api_url,
        upload_target=upload_target,
        has_api_url=has_api_url,
        has_api_token=has_api_token,
        has_valid_api_token=has_valid_api_token,
        is_ready=is_ready,
        next_action=next_action,
        next_label=next_label,
        summary=summary,
    )


def upload_target_label(upload_target: Optional[str]) -> str:
    labels = {
        "acfun": "AcFun",
        "bilibili": "bilibili",
        "both": "同时投稿（AcFun + bilibili）",
    }
    return labels.get(upload_target or "", "服务器默认")
