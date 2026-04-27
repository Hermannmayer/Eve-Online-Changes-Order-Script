"""
认证模块 - ESI SSO 认证流程
"""

import requests
from typing import Optional


class ESIAuth:
    """处理 EVE SSO 认证，管理 Access Token 与 Refresh Token"""

    def __init__(self, client_id: str, client_secret: str, callback_url: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.callback_url = callback_url
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self._auth_url = "https://login.eveonline.com/v2/oauth"
        self._esi_url = "https://esi.evetech.net"

    def get_authorization_url(self, scopes: list[str]) -> str:
        """生成 SSO 授权 URL"""
        pass

    def exchange_authorization_code(self, code: str) -> bool:
        """用授权码换取 token"""
        pass

    def refresh_access_token(self) -> bool:
        """刷新 Access Token"""
        pass

    def get_character_id(self) -> int:
        """获取当前角色的 ID"""
        pass
