"""
初始化并导出所有 Provider 模块
"""
from .base import register_provider, dispatch_provider, list_registered_providers
from .rss_provider import generate_rss
from .crypto_provider import generate_crypto
from .webhook_provider import generate_webhook_data
from .hotlist_provider import generate_hotlist
from .disaster_provider import generate_disaster_alert
from .gold_provider import generate_gold
from .wechat_read_provider import generate_wechat_read
from .douban_movie_provider import generate_douban_movie
from .smzdm_provider import generate_smzdm
from .tech_radar_provider import generate_tech_radar
from .qr_code_provider import generate_qr_code

__all__ = [
    "register_provider",
    "dispatch_provider",
    "list_registered_providers",
    "generate_rss",
    "generate_crypto",
    "generate_webhook_data",
    "generate_hotlist",
    "generate_disaster_alert",
    "generate_gold",
    "generate_wechat_read",
    "generate_douban_movie",
    "generate_smzdm",
    "generate_tech_radar",
    "generate_qr_code",
]
