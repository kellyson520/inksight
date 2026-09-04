"""
初始化并导出所有 Provider 模块
"""
from .base import register_provider, dispatch_provider, list_registered_providers
from .rss_provider import generate_rss
from .crypto_provider import generate_crypto
from .webhook_provider import generate_webhook_data
from .hotlist_provider import generate_hotlist
from .disaster_provider import generate_disaster_alert

__all__ = [
    "register_provider",
    "dispatch_provider",
    "list_registered_providers",
    "generate_rss",
    "generate_crypto",
    "generate_webhook_data",
    "generate_hotlist",
    "generate_disaster_alert",
]
