"""
认证模块 - ESI SSO 认证流程（完整实现）
支持本地 HTTP 服务器接收 OAuth 回调，自动管理 Token 刷新
"""

import time
import json
import threading
import logging
from typing import Optional, Callable
from urllib.parse import urlencode, urlparse, parse_qs

import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

logger = logging.getLogger(__name__)


class ESIAuth:
    """处理 EVE SSO 认证，管理 Access Token 与 Refresh Token"""

    def __init__(self, client_id: str, client_secret: str, callback_url: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.callback_url = callback_url
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.expires_at: float = 0.0  # token 过期时间戳
        self.character_id: Optional[int] = None
        self.character_name: Optional[str] = None
        self._auth_url = "https://login.eveonline.com/v2/oauth"
        self._esi_url = "https://esi.evetech.net"

        # 回调服务器
        self._callback_server: Optional[HTTPServer] = None
        self._callback_thread: Optional[threading.Thread] = None
        self._callback_port: int = 65010
        self._on_token_acquired: Optional[Callable] = None

        # 解析回调端口
        parsed = urlparse(callback_url)
        if parsed.port:
            self._callback_port = parsed.port
        elif parsed.scheme == "http":
            self._callback_port = 80

    def get_authorization_url(self, scopes: list[str]) -> str:
        """生成 SSO 授权 URL"""
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.callback_url,
            "scope": " ".join(scopes) if scopes else "",
            "state": "eve_market_bot"
        }
        return f"{self._auth_url}/authorize?{urlencode(params)}"

    def _parse_token_response(self, resp_data: dict) -> bool:
        """解析 token 响应"""
        if "access_token" not in resp_data:
            logger.error("Token 响应缺少 access_token")
            return False

        self.access_token = resp_data["access_token"]
        self.refresh_token = resp_data.get("refresh_token", self.refresh_token)
        expires_in = resp_data.get("expires_in", 1200)
        self.expires_at = time.time() + expires_in - 60  # 提前 60 秒刷新

        # 解码 JWT 获取角色信息
        try:
            self._decode_jwt_payload()
        except Exception as e:
            logger.warning(f"解析 JWT 失败: {e}")

        return True

    def _decode_jwt_payload(self):
        """从 Access Token (JWT) 中解码角色信息"""
        if not self.access_token:
            return
        # JWT 是 base64 编码的三段式 token
        parts = self.access_token.split(".")
        if len(parts) != 3:
            return
        # 解码 payload（第二部分）
        import base64
        payload = parts[1]
        # 修复 padding
        payload += "=" * (4 - len(payload) % 4)
        try:
            decoded = base64.urlsafe_b64decode(payload)
            data = json.loads(decoded)
            self.character_id = data.get("sub", "").split(":")[-1]
            if self.character_id:
                self.character_id = int(self.character_id)
            self.character_name = data.get("name")
            logger.info(f"JWT 解码成功: 角色={self.character_name}, ID={self.character_id}")
        except Exception as e:
            logger.warning(f"JWT 解码失败: {e}")

    def exchange_authorization_code(self, code: str) -> bool:
        """用授权码换取 token"""
        try:
            resp = requests.post(
                f"{self._auth_url}/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": self.callback_url,
                },
                auth=(self.client_id, self.client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30
            )
            if resp.status_code != 200:
                logger.error(f"换取 token 失败: {resp.status_code} {resp.text}")
                return False
            return self._parse_token_response(resp.json())
        except requests.RequestException as e:
            logger.error(f"换取 token 请求异常: {e}")
            return False

    def refresh_access_token(self) -> bool:
        """刷新 Access Token"""
        if not self.refresh_token:
            logger.error("无 Refresh Token，无法刷新")
            return False
        try:
            resp = requests.post(
                f"{self._auth_url}/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                },
                auth=(self.client_id, self.client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30
            )
            if resp.status_code != 200:
                logger.error(f"刷新 token 失败: {resp.status_code} {resp.text}")
                return False
            return self._parse_token_response(resp.json())
        except requests.RequestException as e:
            logger.error(f"刷新 token 请求异常: {e}")
            return False

    def get_character_id(self) -> Optional[int]:
        """获取当前角色的 ID"""
        if self.character_id:
            return self.character_id
        # 尝试从 JWT 中获取
        self._decode_jwt_payload()
        return self.character_id

    def get_character_name(self) -> Optional[str]:
        """获取当前角色名称"""
        if self.character_name:
            return self.character_name
        self._decode_jwt_payload()
        return self.character_name

    def is_token_valid(self) -> bool:
        """检查 token 是否有效（未过期）"""
        return bool(self.access_token) and time.time() < self.expires_at

    def get_valid_token(self) -> Optional[str]:
        """获取有效 token，自动刷新"""
        if self.is_token_valid():
            return self.access_token
        if self.refresh_token:
            if self.refresh_access_token():
                return self.access_token
        return None

    # ---- 本地回调服务器 ----

    class _CallbackHandler(BaseHTTPRequestHandler):
        """处理 OAuth 回调的 HTTP 请求处理器"""

        auth_instance: Optional['ESIAuth'] = None
        auth_code: Optional[str] = None

        def do_GET(self):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            if "code" in params:
                code = params["code"][0]
                self.__class__.auth_code = code
                # 显示成功页面
                self.send_response(200)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    "<html><body><h2>✅ 认证成功！</h2>"
                    "<p>授权码已接收，你可以关闭此页面返回脚本。</p>"
                    "</body></html>".encode("utf-8")
                )
            elif "error" in params:
                error = params.get("error", ["未知错误"])[0]
                self.send_response(400)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    f"<html><body><h2>❌ 认证失败</h2>"
                    f"<p>错误: {error}</p></body></html>".encode("utf-8")
                )
            else:
                self.send_response(400)
                self.send_header("Content-type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    "<html><body><h2>❌ 无效请求</h2>"
                    "<p>未收到授权码。</p></body></html>".encode("utf-8")
                )

        def log_message(self, format, *args):
            """抑制 HTTP 服务器日志"""
            pass

    def start_callback_server(self) -> bool:
        """启动本地 HTTP 服务器监听回调"""
        try:
            self.__class__._CallbackHandler.auth_instance = self
            self.__class__._CallbackHandler.auth_code = None

            self._callback_server = HTTPServer(
                ("", self._callback_port),
                self.__class__._CallbackHandler
            )
            self._callback_thread = threading.Thread(
                target=self._callback_server.serve_forever,
                daemon=True
            )
            self._callback_thread.start()
            logger.info(f"回调服务器已启动，端口 {self._callback_port}")
            return True
        except OSError as e:
            logger.error(f"启动回调服务器失败: {e}")
            return False

    def stop_callback_server(self):
        """停止本地回调服务器"""
        if self._callback_server:
            self._callback_server.shutdown()
            self._callback_server = None
            logger.info("回调服务器已停止")

    def wait_for_callback(self, timeout: float = 300) -> Optional[str]:
        """等待 OAuth 回调，返回授权码"""
        start_time = time.time()
        handler_class = self.__class__._CallbackHandler

        while time.time() - start_time < timeout:
            if handler_class.auth_code:
                code = handler_class.auth_code
                handler_class.auth_code = None  # 重置
                return code
            time.sleep(0.5)
        return None

    def start_sso_flow(self, scopes: list[str],
                       on_token_acquired: Optional[Callable] = None,
                       timeout: float = 300) -> bool:
        """
        启动完整 SSO 流程：
        1. 启动本地回调服务器
        2. 打开浏览器跳转到 EVE 登录
        3. 等待回调获取授权码
        4. 换取 Token
        """
        self._on_token_acquired = on_token_acquired

        # 启动回调服务器
        if not self.start_callback_server():
            return False

        # 生成授权 URL 并打开浏览器
        auth_url = self.get_authorization_url(scopes)
        logger.info(f"打开浏览器进行 SSO 授权...")
        self._open_browser(auth_url)

        # 等待回调
        logger.info("等待用户授权...")
        code = self.wait_for_callback(timeout)
        if not code:
            logger.error("等待授权超时")
            self.stop_callback_server()
            return False

        # 换取 token
        logger.info("换取 Access Token...")
        success = self.exchange_authorization_code(code)

        # 停止回调服务器
        self.stop_callback_server()

        if success:
            logger.info(f"SSO 认证成功！角色: {self.character_name}")
            if self._on_token_acquired:
                self._on_token_acquired()
        else:
            logger.error("SSO 认证失败")

        return success

    @staticmethod
    def _open_browser(url: str):
        """在默认浏览器中打开 URL（使用 webbrowser 模块避免 shell 截断 & 符号）"""
        import webbrowser
        try:
            webbrowser.open(url)
        except Exception as e:
            logger.error(f"打开浏览器失败: {e}")
            # 备选方案：使用 subprocess（需正确处理 & 符号）
            import subprocess
            import sys
            try:
                if sys.platform == "win32":
                    # Windows cmd.exe 会把 & 当作命令分隔符，需用引号包裹
                    subprocess.Popen(['cmd', '/c', 'start', '', url],
                                     shell=False)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", url])
                else:
                    subprocess.Popen(["xdg-open", url])
            except Exception as e2:
                logger.error(f"备用方式打开浏览器也失败: {e2}")

    def to_dict(self) -> dict:
        """导出认证信息为字典（用于保存）"""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "character_id": self.character_id,
            "character_name": self.character_name,
        }

    def from_dict(self, data: dict):
        """从字典恢复认证信息"""
        self.access_token = data.get("access_token")
        self.refresh_token = data.get("refresh_token")
        self.expires_at = data.get("expires_at", 0)
        self.character_id = data.get("character_id")
        self.character_name = data.get("character_name")
