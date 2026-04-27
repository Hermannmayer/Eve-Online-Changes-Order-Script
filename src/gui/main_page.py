"""
主页面 - 仪表盘和自动化控制
"""

import logging
import time
from typing import Optional, Callable

import flet as ft

from src.config import Config
from src.gui.theme import AppColors, AppSizes, status_badge

logger = logging.getLogger(__name__)


class MainPage(ft.Container):
    """主仪表盘页面"""

    def __init__(self, config: Config,
                 on_navigate_config: Optional[Callable] = None,
                 on_navigate_auth: Optional[Callable] = None,
                 on_navigate_log: Optional[Callable] = None):
        super().__init__()
        self.config = config
        self.on_navigate_config = on_navigate_config
        self.on_navigate_auth = on_navigate_auth
        self.on_navigate_log = on_navigate_log

        self._is_running = False
        self._start_time: Optional[float] = None
        self._status_text = ft.Text("就绪", size=14)
        self._run_button = ft.ElevatedButton(
            "▶ 开始运行",
            icon=ft.Icons.PLAY_ARROW,
            height=48,
            color=ft.Colors.WHITE,
            bgcolor=AppColors.SUCCESS,
            on_click=self._toggle_run,
        )
        self._run_time_text = ft.Text("00:00:00", size=24, weight=ft.FontWeight.BOLD)
        self._interval_text = ft.Text("")
        self._auth_status_badge = ft.Container()
        self._config_status_badge = ft.Container()

        self.padding = AppSizes.CONTENT_PADDING
        self.expand = True

    def build(self):
        """构建主页面"""
        self.content = ft.Column(
            controls=[
                # 顶部标题
                ft.Row(
                    controls=[
                        ft.Text("🏠 主控制台", size=22, weight=ft.FontWeight.BOLD),
                        ft.Container(expand=True),
                        ft.Text("EVE 市场改单脚本", size=14,
                                color=AppColors.TEXT_SECONDARY),
                    ],
                ),
                ft.Divider(height=2),
                # 主要内容区域（滚动）
                ft.Container(
                    content=ft.Column(
                        controls=[
                            # 运行状态卡片
                            self._build_run_card(),
                            ft.Row(
                                controls=[
                                    # 系统状态卡片
                                    ft.Container(
                                        content=self._build_status_card(),
                                        expand=1,
                                    ),
                                    ft.Container(width=16),
                                    # 配置摘要卡片
                                    ft.Container(
                                        content=self._build_config_summary_card(),
                                        expand=1,
                                    ),
                                ],
                            ),
                            # 快速入口卡片
                            self._build_quick_actions_card(),
                            # 使用说明
                            self._build_help_card(),
                        ],
                        spacing=16,
                        scroll=ft.ScrollMode.AUTO,
                        expand=True,
                    ),
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )
        return self

    def _build_run_card(self):
        """运行控制卡片"""
        # 更新运行状态显示
        if self._is_running:
            run_time = time.time() - self._start_time if self._start_time else 0
            hours = int(run_time // 3600)
            minutes = int((run_time % 3600) // 60)
            seconds = int(run_time % 60)
            self._run_time_text.value = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(
                            ft.Icons.PLAY_CIRCLE if self._is_running else ft.Icons.PAUSE_CIRCLE,
                            color=AppColors.SUCCESS if self._is_running else ft.Colors.GREY_500,
                            size=32,
                        ),
                        ft.Column([
                            ft.Text("运行状态", size=18, weight=ft.FontWeight.BOLD),
                            self._status_text,
                        ], spacing=4),
                        ft.Container(expand=True),
                        self._run_button,
                    ], spacing=16),
                    ft.Divider(height=1),
                    ft.Row([
                        ft.Column([
                            ft.Text("运行时间", size=12, color=AppColors.TEXT_SECONDARY),
                            self._run_time_text,
                        ]),
                        ft.Container(expand=True),
                        ft.Column([
                            ft.Text("检查间隔", size=12, color=AppColors.TEXT_SECONDARY),
                            ft.Text(f"{self.config.get('automation.interval_minutes', 5)} 分钟",
                                    size=16, weight=ft.FontWeight.BOLD),
                        ]),
                        ft.Container(width=40),
                        ft.Column([
                            ft.Text("改价调整", size=12, color=AppColors.TEXT_SECONDARY),
                            ft.Text(
                                f"{self.config.get('automation.price_adjustment_percent', -0.1):+.1f}%",
                                size=16, weight=ft.FontWeight.BOLD,
                                color=AppColors.ERROR if self.config.get('automation.price_adjustment_percent', -0.1) < 0
                                else AppColors.SUCCESS
                            ),
                        ]),
                    ]),
                ], spacing=12),
                padding=20,
            ),
            elevation=AppSizes.CARD_ELEVATION,
        )

    def _build_status_card(self):
        """系统状态卡片"""
        auth_data = self.config.get("auth_data", {})
        has_credentials = bool(
            self.config.get("esi.client_id") and
            self.config.get("esi.client_secret")
        )
        has_token = bool(auth_data.get("access_token") or auth_data.get("refresh_token"))
        has_character = bool(self.config.get("character.id"))

        auth_status = "已认证" if has_token else "未认证"
        auth_color = AppColors.SUCCESS if has_token else ft.Colors.GREY_600

        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("📊 系统状态", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    ft.Row([
                        ft.Text("ESI 凭证", size=13),
                        ft.Container(expand=True),
                        status_badge("✅ 已配置" if has_credentials else "❌ 未配置",
                                     AppColors.SUCCESS if has_credentials else ft.Colors.GREY_600),
                    ]),
                    ft.Row([
                        ft.Text("认证状态", size=13),
                        ft.Container(expand=True),
                        status_badge(auth_status, auth_color),
                    ]),
                    ft.Row([
                        ft.Text("角色配置", size=13),
                        ft.Container(expand=True),
                        status_badge("✅ 已配置" if has_character else "❌ 未配置",
                                     AppColors.SUCCESS if has_character else ft.Colors.GREY_600),
                    ]),
                    ft.Row([
                        ft.Text("模板图片", size=13),
                        ft.Container(expand=True),
                        status_badge("❌ 待配置", ft.Colors.GREY_600),
                    ]),
                ], spacing=8),
                padding=20,
            ),
            elevation=AppSizes.CARD_ELEVATION,
        )

    def _build_config_summary_card(self):
        """配置摘要卡片"""
        interval = self.config.get("automation.interval_minutes", 5)
        price_adj = self.config.get("automation.price_adjustment_percent", -0.1)
        cooldown = self.config.get("automation.modify_cooldown_seconds", 300)
        char_name = self.config.get("character.name", "")
        window_title = self.config.get("game.window_title", "EVE")
        retry = self.config.get("automation.retry_attempts", 2)

        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("⚙️ 当前配置", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    ft.Text(f"角色: {char_name or '未设置'}", size=13),
                    ft.Text(f"窗口: {window_title}", size=13),
                    ft.Text(f"间隔: {interval} 分钟 / 冷却: {cooldown} 秒", size=13),
                    ft.Text(f"卖单调整: {price_adj:+.1f}% / 重试: {retry} 次", size=13),
                ], spacing=6),
                padding=20,
            ),
            elevation=AppSizes.CARD_ELEVATION,
        )

    def _build_quick_actions_card(self):
        """快速入口卡片"""
        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Text("🚀 快捷操作", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    ft.Row([
                        ft.ElevatedButton(
                            "🔐 ESI 认证",
                            icon=ft.Icons.VERIFIED_USER,
                            height=50,
                            width=160,
                            on_click=lambda e: self.on_navigate_auth() if self.on_navigate_auth else None,
                        ),
                        ft.ElevatedButton(
                            "⚙️ 配置管理",
                            icon=ft.Icons.SETTINGS,
                            height=50,
                            width=160,
                            on_click=lambda e: self.on_navigate_config() if self.on_navigate_config else None,
                        ),
                        ft.ElevatedButton(
                            "📋 日志查看",
                            icon=ft.Icons.DESCRIPTION,
                            height=50,
                            width=160,
                            on_click=lambda e: self.on_navigate_log() if self.on_navigate_log else None,
                        ),
                    ], spacing=12),
                ], spacing=8),
                padding=20,
            ),
            elevation=AppSizes.CARD_ELEVATION,
        )

    def _build_help_card(self):
        """使用说明卡片"""
        return ft.Container(
            content=ft.Column([
                ft.Text("📖 快速开始", size=16, weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_SECONDARY),
                ft.Text("1. 前往「配置管理」填写 EVE Developer 的 Client ID 和 Secret",
                        size=12, color=AppColors.TEXT_SECONDARY),
                ft.Text("2. 在「配置管理」中设置角色 ID 和游戏窗口参数",
                        size=12, color=AppColors.TEXT_SECONDARY),
                ft.Text("3. 前往「ESI 认证」点击按钮完成 SSO 登录授权",
                        size=12, color=AppColors.TEXT_SECONDARY),
                ft.Text("4. 返回主界面点击「开始运行」启动自动化改价",
                        size=12, color=AppColors.TEXT_SECONDARY),
                ft.Text("5. 通过「日志查看」监控运行状况",
                        size=12, color=AppColors.TEXT_SECONDARY),
            ], spacing=4),
            bgcolor=ft.Colors.BLUE_GREY_50,
            border_radius=8,
            padding=16,
        )

    def _toggle_run(self, e):
        """切换运行状态"""
        # 检查必要条件
        auth_data = self.config.get("auth_data", {})
        has_token = bool(auth_data.get("access_token") or auth_data.get("refresh_token"))
        has_character = bool(self.config.get("character.id"))

        if not self._is_running:
            # 启动前检查
            if not has_token:
                self._show_snack("⚠️ 请先完成 ESI 认证", AppColors.WARNING)
                return
            if not has_character:
                self._show_snack("⚠️ 请先配置角色 ID", AppColors.WARNING)
                return

            # 启动运行
            self._is_running = True
            self._start_time = time.time()
            self._status_text.value = "运行中..."
            self._status_text.color = AppColors.SUCCESS
            self._run_button.text = "⏹ 停止运行"
            self._run_button.bgcolor = AppColors.ERROR
            self._run_button.icon = ft.Icons.STOP
            self._show_snack("✅ 自动化已启动", AppColors.SUCCESS)
            logger.info("自动化流程已启动")
        else:
            # 停止运行
            self._is_running = False
            self._start_time = None
            self._status_text.value = "已停止"
            self._status_text.color = AppColors.ERROR
            self._run_button.text = "▶ 开始运行"
            self._run_button.bgcolor = AppColors.SUCCESS
            self._run_button.icon = ft.Icons.PLAY_ARROW
            self._show_snack("⏹ 自动化已停止", AppColors.WARNING)
            logger.info("自动化流程已停止")

        self._run_button.update()
        self._status_text.update()

    def _show_snack(self, msg: str, color: str):
        """显示 SnackBar 通知"""
        snack = ft.SnackBar(
            content=ft.Text(msg, color=ft.Colors.WHITE),
            bgcolor=color,
            duration=2000,
        )
        self.page.overlay.append(snack)
        snack.open = True
        self.page.update()
