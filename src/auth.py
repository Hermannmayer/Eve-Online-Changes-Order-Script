"""
ESI SSO 认证模块
使用 EVE SSO v1 端点 + 代理支持（解决中国大陆 Cloudflare 拦截问题）

核心问题：
  - login.eveonline.com 域名的 v1/v2 端点从中国大陆访问均会被 Cloudflare 拦截返回 HTML
  - 解决方案：通过代理服务器转发请求到 EVE SSO

参考文档：https://docs.eveonline.com/en/authentication/sso-authentication
"""

import os
import json
import base64
import logging
import threading
import webbrowser
from typing import Optional, Callable, Dict
from urllib.parse import urlencode, urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone
from traceback import format_exc

import requests

logger = logging.getLogger("auth")

# 常量
DEFAULT_CALLBACK_URL = "http://localhost:65010/callback/"
EVE_SSO_BASE = "https://login.eveonline.com"
ESI_URL = "https://esi.evetech.net"

# EVE SSO v1 端点
EVE_AUTHORIZE_URL = f"{EVE_SSO_BASE}/oauth/authorize"
EVE_TOKEN_URL = f"{EVE_SSO_BASE}/oauth/token"


class CallbackHandler(BaseHTTPRequestHandler):
    """处理 SSO 回调的 HTTP 服务器"""

    auth_code: Optional[str] = None
    auth_error: Optional[str] = None
    server_instance: Optional[HTTPServer] = None

    def do_GET(self):
        """处理 GET 回调请求"""
        try:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            if "code" in params:
                CallbackHandler.auth_code = params["code"][0]
                self._respond_success()
            elif "error" in params:
                CallbackHandler.auth_error = params["error"][0]
                self._respond_error(f"认证错误: {params['error'][0]}")
            else:
                self._respond_error("回调中未找到授权码")
        except Exception as e:
            logger.error(f"处理回调时出错: {e}")
            self._respond_error("服务器内部错误")

        # 发送响应后关闭服务器
        if CallbackHandler.server_instance:
            t = threading.Thread(target=CallbackHandler.server_instance.shutdown, daemon=True)
            t.start()

    def _respond_success(self):
        """发送成功响应页面"""
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            "<html><body><h3>✅ 认证成功！</h3><p>你可以关闭此窗口返回脚本。</p></body></html>".encode("utf-8")
        )

    def _respond_error(self, message: str):
        """发送错误响应页面"""
        self.send_response(400)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            f"<html><body><h3>❌ 认证失败</h3><p>{message}</p></body></html>".encode("utf-8")
        )

    def log_message(self, format, *args):
        """抑制 HTTP 服务器日志"""
        pass


class EveSSOAuthenticator:
    """EVE SSO 认证器（v1 端点，支持代理）"""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        callback_url: str = DEFAULT_CALLBACK_URL,
        scopes: list[str] = None,
        user_agent: str = "EVE-Market-Bot/1.0",
        proxies: Optional[Dict[str, str]] = None,
    ):
        """
        Args:
            client_id: EVE Developer 应用 Client ID
            client_secret: EVE Developer 应用 Client Secret
            callback_url: OAuth 回调 URL
            scopes: ESI 授权范围
            user_agent: User-Agent
            proxies: 代理配置字典，如 {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.callback_url = callback_url
        self.scopes = scopes or ["esi-markets.read_character_orders.v1"]
        self.user_agent = user_agent
        self.proxies = proxies or {}

        # 认证状态
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._expires_at: float = 0
        self._character_id: Optional[int] = None
        self._character_name: Optional[str] = None

        # 重置回调处理器状态
        CallbackHandler.auth_code = None
        CallbackHandler.auth_error = None

    # ── 静态工具方法 ──
    @staticmethod
    def _decode_jwt_payload(token: str) -> dict:
        """安全解码 JWT 的 payload 部分"""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                logger.error(f"JWT 格式错误: 期望3部分，得到{len(parts)}部分")
                payload_b64 = parts[1] if len(parts) > 1 else parts[0]
            else:
                payload_b64 = parts[1]

            # 修复 base64 URL-safe padding
            padding = (4 - len(payload_b64) % 4) % 4
            if padding:
                payload_b64 += "=" * padding

            decoded_bytes = base64.urlsafe_b64decode(payload_b64)
            return json.loads(decoded_bytes)
        except Exception as e:
            logger.error(f"JWT payload 解码失败: {e}")
            raise

    @staticmethod
    def _build_basic_auth_header(client_id: str, client_secret: str) -> str:
        """手动构建 Basic Auth 头"""
        credentials = f"{client_id}:{client_secret}"
        encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
        return f"Basic {encoded}"

    # ── 授权 URL 构建 ──
    def get_authorize_url(self, state: str = None) -> str:
        """构建 EVE SSO 授权 URL（v1 端点）"""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.callback_url,
            "scope": " ".join(self.scopes),
            "state": state or "eve_market_bot",
        }
        return f"{EVE_AUTHORIZE_URL}?{urlencode(params)}"

    # ── Token 交换 ──
    def exchange_code_for_tokens(self, auth_code: str) -> dict:
        """用授权码交换 access_token 和 refresh_token"""
        auth_header = self._build_basic_auth_header(self.client_id, self.client_secret)

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": self.user_agent,
            "Authorization": auth_header,
            "Accept": "application/json",
        }

        body = urlencode({
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self.callback_url,
        })

        proxy_info = self.proxies.get("https") or self.proxies.get("http") or "无"
        logger.info(f"Token 交换请求: POST {EVE_TOKEN_URL} (代理: {proxy_info})")

        try:
            resp = requests.post(
                EVE_TOKEN_URL,
                data=body,
                headers=headers,
                proxies=self.proxies if self.proxies else None,
                timeout=30,
            )

            logger.info(f"Token 交换响应: HTTP {resp.status_code}, "
                       f"Content-Type: {resp.headers.get('Content-Type', 'N/A')}")

            if resp.status_code != 200:
                content_type = resp.headers.get("Content-Type", "")
                if "text/html" in content_type:
                    logger.error(f"收到 HTML 响应（Cloudflare 拦截）")
                    logger.error(f"建议：在配置中启用代理")
                    logger.error(f"响应(前300字): {resp.text[:300]}")
                else:
                    logger.error(f"Token 交换失败: {resp.text[:500]}")
                return {}

            token_data = resp.json()
            logger.info("Token 交换成功")

            # 解析 JWT 获取角色信息
            try:
                jwt_payload = self._decode_jwt_payload(token_data["access_token"])
                logger.info(f"JWT payload keys: {list(jwt_payload.keys())}")

                sub = jwt_payload.get("sub", "")
                if sub.startswith("CHARACTER_EVE:"):
                    self._character_id = int(sub.split(":")[1])
                self._character_name = jwt_payload.get("name", "")

                logger.info(f"角色: {self._character_name} (ID: {self._character_id})")
            except Exception as e:
                logger.warning(f"无法从 JWT 解析角色信息: {e}")

            self._access_token = token_data.get("access_token")
            self._refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 1200)
            self._expires_at = datetime.now(timezone.utc).timestamp() + expires_in

            return token_data

        except requests.exceptions.Timeout:
            logger.error("Token 交换请求超时")
            return {}
        except requests.exceptions.ProxyError as e:
            logger.error(f"代理连接失败: {e}")
            logger.error("请检查代理配置是否正确，或尝试关闭代理直接连接")
            return {}
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Token 交换连接失败: {e}")
            return {}
        except Exception as e:
            logger.error(f"Token 交换异常: {e}\n{format_exc()}")
            return {}

    # ── Token 刷新 ──
    def refresh_access_token(self) -> bool:
        """使用 refresh_token 刷新 access_token"""
        if not self._refresh_token:
            logger.error("没有 refresh_token，无法刷新")
            return False

        auth_header = self._build_basic_auth_header(self.client_id, self.client_secret)

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": self.user_agent,
            "Authorization": auth_header,
            "Accept": "application/json",
        }

        body = urlencode({
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
        })

        try:
            resp = requests.post(
                EVE_TOKEN_URL,
                data=body,
                headers=headers,
                proxies=self.proxies if self.proxies else None,
                timeout=30,
            )

            if resp.status_code != 200:
                logger.error(f"Token 刷新失败 (HTTP {resp.status_code}): {resp.text[:200]}")
                if resp.status_code == 400:
                    logger.error("refresh_token 可能已过期，需要重新认证")
                return False

            token_data = resp.json()
            self._access_token = token_data["access_token"]
            if "refresh_token" in token_data:
                self._refresh_token = token_data["refresh_token"]
            expires_in = token_data.get("expires_in", 1200)
            self._expires_at = datetime.now(timezone.utc).timestamp() + expires_in

            logger.info("Token 刷新成功")
            return True

        except Exception as e:
            logger.error(f"Token 刷新异常: {e}")
            return False

    # ── 启动本地服务器 ──
    def _start_callback_server(self) -> bool:
        """启动本地 HTTP 服务器等待回调"""
        parsed = urlparse(self.callback_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 65010

        try:
            server = HTTPServer((host, port), CallbackHandler)
            CallbackHandler.server_instance = server
            logger.info(f"回调服务器已启动: http://{host}:{port}")
            server.handle_request()
            return True
        except OSError as e:
            logger.error(f"无法启动回调服务器 (端口 {port} 可能被占用): {e}")
            return False
        except Exception as e:
            logger.error(f"启动回调服务器异常: {e}")
            return False

    # ── 完整认证流程 ──
    def authenticate(self, progress_callback: Callable = None) -> bool:
        """执行完整的 SSO 认证流程

        Args:
            progress_callback: 进度回调函数，参数为 (阶段名称, 进度百分比)

        Returns:
            bool: 认证是否成功
        """
        def progress(phase: str, pct: int = 0):
            if progress_callback:
                progress_callback(phase, pct)
            logger.info(f"[{pct}%] {phase}")

        # 重置状态
        CallbackHandler.auth_code = None
        CallbackHandler.auth_error = None

        # 1. 构建授权 URL
        progress("构建授权 URL", 10)
        auth_url = self.get_authorize_url()
        logger.info(f"授权 URL: {auth_url[:200]}...")

        # 2. 启动回调服务器
        progress("启动本地回调服务器...", 20)
        server_thread = threading.Thread(target=self._start_callback_server, daemon=True)
        server_thread.start()

        # 3. 打开浏览器
        progress("正在打开浏览器进行 EVE SSO 登录...", 30)
        try:
            webbrowser.open(auth_url)
            logger.info(f"浏览器已打开 EVE SSO 登录页面")
        except Exception as e:
            logger.warning(f"无法自动打开浏览器: {e}")
            logger.info(f"请手动打开以下链接进行授权:\n{auth_url}")
            print(f"\n⚠️  请手动打开以下链接进行 EVE SSO 授权:\n{auth_url}\n")

        # 4. 等待回调
        progress("等待 EVE 登录授权...", 40)
        server_thread.join(timeout=300)

        if CallbackHandler.auth_error:
            progress(f"认证错误: {CallbackHandler.auth_error}", 0)
            logger.error(f"SSO 返回错误: {CallbackHandler.auth_error}")
            return False

        if not CallbackHandler.auth_code:
            progress("未收到授权码（超时或取消）", 0)
            logger.error("未收到授权码，认证超时或用户取消")
            return False

        # 5. 交换 Token
        progress("正在交换 Token...", 60)
        logger.info(f"收到授权码: {CallbackHandler.auth_code[:20]}...")
        token_data = self.exchange_code_for_tokens(CallbackHandler.auth_code)
        if not token_data:
            progress("Token 交换失败", 0)
            return False

        progress("Token 交换成功", 80)

        # 6. 验证认证状态
        if not self._access_token:
            progress("未获取到 access_token", 0)
            logger.error("认证后未获取到 access_token")
            return False

        progress(f"认证成功！角色: {self._character_name or '未知'}", 100)
        return True

    # ── 从保存的数据恢复认证状态 ──
    def load_from_dict(self, data: dict) -> None:
        """从保存的字典数据恢复认证状态"""
        self._refresh_token = data.get("refresh_token", "")
        self._expires_at = data.get("expires_at", 0)
        self._character_id = data.get("character_id")
        self._character_name = data.get("character_name", "")
        logger.info(f"已加载认证状态: 角色={self._character_name}, token过期={self._expires_at}")

    def save_to_dict(self) -> dict:
        """保存认证状态到字典"""
        return {
            "refresh_token": self._refresh_token or "",
            "expires_at": self._expires_at,
            "character_id": self._character_id,
            "character_name": self._character_name or "",
        }

    # ── 属性访问 ──
    @property
    def is_authenticated(self) -> bool:
        """是否已认证且 token 未过期"""
        return bool(self._access_token) and self._expires_at > datetime.now(timezone.utc).timestamp()

    @property
    def character_id(self) -> Optional[int]:
        return self._character_id

    @property
    def character_name(self) -> Optional[str]:
        return self._character_name

    @property
    def access_token(self) -> Optional[str]:
        """获取有效的 access_token，必要时自动刷新"""
        now = datetime.now(timezone.utc).timestamp()
        if self._expires_at - now < 60 and self._refresh_token:
            logger.info("Token 即将过期，尝试刷新...")
            if self.refresh_access_token():
                return self._access_token
            else:
                logger.error("Token 刷新失败，返回旧的 access_token")
                return self._access_token
        return self._access_token

    @property
    def expires_at(self) -> float:
        return self._expires_at

    @property
    def refresh_token(self) -> Optional[str]:
        return self._refresh_token


# ── 便捷函数 ──
def authenticate_sync(
    client_id: str,
    client_secret: str,
    callback_url: str = DEFAULT_CALLBACK_URL,
    scopes: list[str] = None,
    progress_callback: Callable = None,
    proxies: Optional[Dict[str, str]] = None,
) -> Optional[EveSSOAuthenticator]:
    """同步认证便捷函数

    Args:
        client_id: EVE Developer 应用 Client ID
        client_secret: EVE Developer 应用 Client Secret
        callback_url: OAuth 回调 URL
        scopes: ESI 授权范围
        progress_callback: 进度回调
        proxies: 代理配置字典

    Returns:
        EveSSOAuthenticator or None
    """
    auth = EveSSOAuthenticator(
        client_id=client_id,
        client_secret=client_secret,
        callback_url=callback_url,
        scopes=scopes,
        proxies=proxies,
    )
    if auth.authenticate(progress_callback):
        return auth
    return None
