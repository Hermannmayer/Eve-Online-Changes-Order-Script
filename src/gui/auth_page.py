"""
认证页面 - ESI SSO 登录流程 GUI
"""

import threading
import time
import logging
from typing import Optional, Callable

import flet as ft

from src.auth import EveSSOAuthenticator
from src.config import Config
from src.gui.theme import AppColors, AppSizes, section_header, help_text, status_badge

logger = logging.getLogger(__name__)


class AuthPage(ft.Container):
    """ESI SSO 认证页面"""

    def __init__(self, config: Config, on_back: Optional[Callable] = None,
                 on_auth_success: Optional[Callable] = None):
        super().__init__()
        self.config = config
        self.on_back = on_back
        self.on_auth_success = on_auth_success

        self._auth: Optional[EveSSOAuthenticator] = None
        self._auth_thread: Optional[threading.Thread] = None
        self._is_authenticating = False
        self._status_text = ft.Text("", size=13)
        self._char_name_text = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
        self._char_id_text = ft.Text("", size=13, color=AppColors.TEXT_SECONDARY)
        self._token_status_text = ft.Text("", size=13)
        self._auth_button = self._create_auth_button()
        self._status_indicator = ft.Container(
            width=12, height=12, border_radius=6, bgcolor=ft.Colors.GREY_400
        )

        self.padding = AppSizes.CONTENT_PADDING
        self.expand = True

    def build(self):
        """构建认证页面"""
        # 初始化认证器
        self._init_auth()

        self.content = ft.Column(
            controls=[
                self._build_top_bar(),
                ft.Divider(height=2),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            self._build_auth_status_card(),
                            ft.Divider(height=1),
                            self._build_auth_flow_card(),
                            ft.Divider(height=1),
                            self._build_token_info_card(),
                            ft.Divider(height=1),
                            self._build_help_card(),
                        ],
                        spacing=16,
                        scroll=ft.ScrollMode.AUTO,
                        expand=True,
                    ),
                    expand=True,
                ),
                ft.Container(
                    content=self._build_bottom_bar(),
                    padding=ft.padding.symmetric(vertical=10),
                ),
                self._status_text,
            ],
            spacing=0,
            expand=True,
        )
        return self

    def _init_auth(self):
        """初始化认证器"""
        client_id = self.config.get("esi.client_id", "")
        client_secret = self.config.get("esi.client_secret", "")
        callback_url = self.config.get("esi.callback_url",
                                       "http://localhost:65010/callback/")
        proxies = self.config.get_proxy_dict()

        scopes = self.config.get("esi.scopes", ["esi-markets.read_character_orders.v1"])
        if isinstance(scopes, str):
            scopes = scopes.split()

        if client_id and client_secret:
            self._auth = EveSSOAuthenticator(
                client_id, client_secret, callback_url, scopes,
                proxies=proxies,
            )
            # 从配置恢复 token
            auth_data = self.config.get("auth_data", {})
            if auth_data and auth_data.get("refresh_token"):
                self._auth.load_from_dict(auth_data)
        else:
            self._auth = EveSSOAuthenticator(
                "", "", callback_url, scopes,
                proxies=proxies,
            )

    def _build_top_bar(self):
        """顶部导航"""
        return ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    tooltip="返回主页面",
                    on_click=lambda e: self.on_back() if self.on_back else None,
                ),
                ft.Text("🔐 ESI 认证", size=22, weight=ft.FontWeight.BOLD),
            ],
        )

    def _build_auth_status_card(self):
        """认证状态卡片"""
        # 判断当前认证状态
        is_valid = self._auth and self._auth.is_authenticated
        char_name = self._auth.character_name if self._auth else None
        char_id = self._auth.character_id if self._auth else None

        if is_valid:
            status_color = AppColors.SUCCESS
            badge = status_badge("✅ 已认证", AppColors.SUCCESS)
            self._char_name_text.value = char_name or "未知角色"
            self._char_id_text.value = f"角色 ID: {char_id}" if char_id else ""
            self._status_indicator.bgcolor = AppColors.SUCCESS
            token_info = "Token 有效"
        else:
            # 检查是否有 refresh_token
            has_refresh = bool(self._auth and self._auth.refresh_token)
            if has_refresh:
                status_color = AppColors.WARNING
                badge = status_badge("⚠️ Token 过期", AppColors.WARNING)
                self._status_indicator.bgcolor = AppColors.WARNING
                token_info = "Token 已过期，可刷新"
            else:
                status_color = ft.Colors.GREY_600
                badge = status_badge("❌ 未认证", ft.Colors.GREY_600)
                self._status_indicator.bgcolor = ft.Colors.GREY_400
                token_info = "尚未认证"

        self._token_status_text.value = token_info

        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        self._status_indicator,
                        ft.Text("认证状态", size=18, weight=ft.FontWeight.BOLD),
                        badge,
                    ], spacing=12),
                    ft.Row([
                        ft.Column([
                            self._char_name_text,
                            self._char_id_text,
                        ]),
                    ]),
                    self._token_status_text,
                ], spacing=8),
                padding=20,
            ),
            elevation=AppSizes.CARD_ELEVATION,
        )

    def _build_auth_flow_card(self):
        """认证流程操作卡片"""
        # 检查 Client ID/Secret 是否已配置
        has_credentials = bool(
            self.config.get("esi.client_id") and
            self.config.get("esi.client_secret")
        )

        if not has_credentials:
            credential_warning = ft.Container(
                content=ft.Text(
                    "⚠️ 请先在「配置管理」页面填写 Client ID 和 Client Secret",
                    color=AppColors.WARNING,
                    weight=ft.FontWeight.BOLD,
                ),
                bgcolor=ft.Colors.AMBER_50,
                padding=12,
                border_radius=8,
            )
        else:
            credential_warning = ft.Text("")

        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    section_header("🔄 认证流程"),
                    help_text("通过 EVE Online SSO 登录获取 API 访问权限"),
                    credential_warning,
                    ft.Text("操作步骤：", weight=ft.FontWeight.BOLD),
                    ft.Text("1. 点击下方按钮，在浏览器中打开 EVE 登录页面"),
                    ft.Text("2. 使用你的 EVE 账号登录并授权"),
                    ft.Text("3. 授权成功后自动跳转回本程序"),
                    ft.Text("4. 系统将自动获取 Access Token 并保存"),
                    ft.Container(height=10),
                    self._auth_button,
                ], spacing=6),
                padding=20,
            ),
            elevation=AppSizes.CARD_ELEVATION,
        )

    def _build_token_info_card(self):
        """Token 信息卡片"""
        expires_info = "未获取"
        if self._auth and self._auth.expires_at > 0:
            expires_time = time.strftime(
                "%Y-%m-%d %H:%M:%S",
                time.localtime(self._auth.expires_at)
            )
            expires_info = expires_time

        has_refresh = bool(self._auth and self._auth.refresh_token)

        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    section_header("📋 Token 信息"),
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("项目")),
                            ft.DataColumn(ft.Text("状态")),
                        ],
                        rows=[
                            ft.DataRow(cells=[
                                ft.DataCell(ft.Text("Access Token")),
                                ft.DataCell(ft.Text(
                                    "✅ 已获取" if self._auth and self._auth.access_token else "❌ 未获取"
                                )),
                            ]),
                            ft.DataRow(cells=[
                                ft.DataCell(ft.Text("Refresh Token")),
                                ft.DataCell(ft.Text(
                                    "✅ 已获取" if has_refresh else "❌ 未获取"
                                )),
                            ]),
                            ft.DataRow(cells=[
                                ft.DataCell(ft.Text("过期时间")),
                                ft.DataCell(ft.Text(expires_info)),
                            ]),
                        ],
                    ),
                ], spacing=8),
                padding=20,
            ),
            elevation=AppSizes.CARD_ELEVATION,
        )

    def _build_help_card(self):
        """帮助说明卡片"""
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    section_header("❓ 帮助说明"),
                    help_text("如何获取 Client ID 和 Client Secret"),
                    ft.Text("1. 访问 https://developers.eveonline.com "),
                    ft.Text("2. 登录并创建一个新应用"),
                    ft.Text("3. 设置回调 URL 为 http://localhost:65010/callback/"),
                    ft.Text("4. 添加权限: esi-markets.read_character_orders.v1"),
                    ft.Text("5. 在「配置管理」中填写 Client ID 和 Secret"),
                ], spacing=4),
                padding=20,
            ),
            elevation=AppSizes.CARD_ELEVATION,
        )

    def _build_bottom_bar(self):
        """底部按钮"""
        return ft.Row(
            controls=[
                ft.OutlinedButton(
                    "🔄 刷新状态",
                    icon=ft.Icons.REFRESH,
                    height=AppSizes.BUTTON_HEIGHT,
                    on_click=self._refresh_status,
                ),
                ft.ElevatedButton(
                    "💾 保存认证信息",
                    icon=ft.Icons.SAVE,
                    color=ft.Colors.WHITE,
                    bgcolor=AppColors.PRIMARY,
                    height=AppSizes.BUTTON_HEIGHT,
                    on_click=self._save_auth_data,
                ),
            ],
            spacing=12,
        )

    def _create_auth_button(self) -> ft.ElevatedButton:
        """创建认证按钮"""
        has_auth = self._auth and self._auth.is_authenticated
        if has_auth:
            return ft.ElevatedButton(
                "🔄 重新认证",
                icon=ft.Icons.REFRESH,
                height=50,
                on_click=self._start_auth_flow,
            )
        else:
            return ft.ElevatedButton(
                "🔗 前往 EVE 登录授权",
                icon=ft.Icons.LOGIN,
                height=50,
                color=ft.Colors.WHITE,
                bgcolor=AppColors.PRIMARY,
                on_click=self._start_auth_flow,
            )

    def _start_auth_flow(self, e):
        """启动认证流程"""
        client_id = self.config.get("esi.client_id", "")
        client_secret = self.config.get("esi.client_secret", "")
        callback_url = self.config.get("esi.callback_url",
                                       "http://localhost:65010/callback/")

        if not client_id or not client_secret:
            self._show_status("⚠️ 请先配置 Client ID 和 Client Secret", AppColors.WARNING)
            return

        if self._is_authenticating:
            self._show_status("⏳ 正在认证中，请勿重复操作...", AppColors.WARNING)
            return

        # 重新初始化认证器
        scopes = self.config.get("esi.scopes", ["esi-markets.read_character_orders.v1"])
        if isinstance(scopes, str):
            scopes = scopes.split()
        proxies = self.config.get_proxy_dict()
        self._auth = EveSSOAuthenticator(
            client_id, client_secret, callback_url, scopes,
            proxies=proxies,
        )
        auth_data = self.config.get("auth_data", {})
        if auth_data and auth_data.get("refresh_token"):
            self._auth.load_from_dict(auth_data)

        # 更新按钮状态
        self._auth_button.text = "⏳ 正在认证..."
        self._auth_button.disabled = True
        self._auth_button.update()
        self._is_authenticating = True

        # 在后台线程中执行 SSO 流程
        self._auth_thread = threading.Thread(
            target=self._run_sso_flow,
            daemon=True
        )
        self._auth_thread.start()

    def _run_sso_flow(self):
        """在后台运行 SSO 流程"""
        try:
            scopes = self.config.get("esi.scopes",
                                      ["esi-markets.read_character_orders.v1"])
            if isinstance(scopes, str):
                scopes = scopes.split()

            # 使用进度回调更新 UI
            def on_progress(phase: str, pct: int):
                logger.info(f"SSO 进度: [{pct}%] {phase}")
            
            success = self._auth.authenticate(progress_callback=on_progress)

            if success:
                # 保存认证信息到配置
                self.config.set("character.id", self._auth.character_id)
                self.config.set("character.name", self._auth.character_name or "")
                auth_data = self._auth.save_to_dict()
                for key, value in auth_data.items():
                    self.config.set(f"auth_data.{key}", value)
                self.config.save()

                # 更新 UI
                self._on_auth_success()
            else:
                self._on_auth_failure("认证失败，请重试")

        except Exception as ex:
            logger.error(f"SSO 流程出错: {ex}")
            self._on_auth_failure(f"认证出错: {ex}")

    def _on_auth_success(self):
        """认证成功回调"""
        self._is_authenticating = False
        self._show_status("✅ 认证成功！", AppColors.SUCCESS)
        self._refresh_ui()

    def _on_auth_failure(self, msg: str):
        """认证失败回调"""
        self._is_authenticating = False
        self._show_status(f"❌ {msg}", AppColors.ERROR)
        self._refresh_ui()

    def _refresh_ui(self):
        """刷新整个 UI"""
        self._auth_button.text = "🔗 前往 EVE 登录授权"
        self._auth_button.disabled = False
        # 重建认证状态卡片
        self.build()
        self.update()

    def _refresh_status(self, e):
        """手动刷新状态"""
        # 尝试用 refresh token 刷新
        if self._auth and self._auth.refresh_token:
            if self._auth.refresh_access_token():
                self._show_status("✅ Token 已刷新成功", AppColors.SUCCESS)
                self._save_auth_data(None)
            else:
                self._show_status("⚠️ 刷新失败，可能需要重新认证", AppColors.WARNING)
        self._refresh_ui()

    def _save_auth_data(self, e):
        """保存认证信息到配置文件"""
        if not self._auth:
            self._show_status("⚠️ 没有认证信息可保存", AppColors.WARNING)
            return

        auth_data = self._auth.save_to_dict()
        for key, value in auth_data.items():
            self.config.set(f"auth_data.{key}", value)

        if self._auth.character_id:
            self.config.set("character.id", self._auth.character_id)
        if self._auth.character_name:
            self.config.set("character.name", self._auth.character_name)

        if self.config.save():
            self._show_status("✅ 认证信息已保存", AppColors.SUCCESS)
        else:
            self._show_status("❌ 保存失败", AppColors.ERROR)

    def _show_status(self, msg: str, color: str):
        """显示状态消息"""
        self._status_text.value = msg
        self._status_text.color = color
        self._status_text.update()
