"""
Flet 应用入口 - 主应用控制器
管理页面路由和全局状态
"""

import logging
from typing import Optional

import flet as ft

from src.config import Config
from src.gui.theme import get_theme, AppColors, AppSizes
from src.gui.main_page import MainPage
from src.gui.config_page import ConfigPage
from src.gui.auth_page import AuthPage
from src.gui.log_page import LogPage

logger = logging.getLogger(__name__)


class EveMarketApp:
    """Flet GUI 应用主控制器"""

    def __init__(self, config: Config):
        self.config = config
        self.page: Optional[ft.Page] = None

        # 页面引用
        self._main_page: Optional[MainPage] = None
        self._config_page: Optional[ConfigPage] = None
        self._auth_page: Optional[AuthPage] = None
        self._log_page: Optional[LogPage] = None

        # 导航历史
        self._nav_stack: list[str] = ["main"]

    def run(self):
        """启动 Flet 应用"""
        ft.app(target=self._main, assets_dir="templates")

    async def _main(self, page: ft.Page):
        """Flet 主函数（异步初始化）"""
        self.page = page
        page.title = "EVE 市场改单脚本"
        page.theme = get_theme()
        page.padding = 0
        page.window.min_width = 900
        page.window.min_height = 650
        page.window.width = 1100
        page.window.height = 750

        # 窗口图标 (可选)
        try:
            page.window.icon = "templates/icon.ico"
        except Exception:
            pass

        # Flet 0.84+ window.center() 是 async 方法
        try:
            await page.window.center()
        except Exception:
            pass

        # 显示主页面
        self._show_main_page()

        page.update()

    def _clear_page(self):
        """清除当前页面内容"""
        if self.page and self.page.controls:
            self.page.controls.clear()
        # 释放日志页面资源
        if self._log_page:
            self._log_page.dispose()
            self._log_page = None

    def _show_main_page(self):
        """显示主页面"""
        self._clear_page()
        self._main_page = MainPage(
            config=self.config,
            on_navigate_config=self._show_config_page,
            on_navigate_auth=self._show_auth_page,
            on_navigate_log=self._show_log_page,
        )
        self.page.add(self._main_page)
        self._nav_stack.append("main")
        self.page.update()

    def _show_config_page(self):
        """显示配置页面"""
        self._clear_page()
        self._config_page = ConfigPage(
            config=self.config,
            on_back=self._go_back,
        )
        self.page.add(self._config_page)
        self._nav_stack.append("config")
        self.page.update()

    def _show_auth_page(self):
        """显示认证页面"""
        self._clear_page()
        self._auth_page = AuthPage(
            config=self.config,
            on_back=self._go_back,
        )
        self.page.add(self._auth_page)
        self._nav_stack.append("auth")
        self.page.update()

    def _show_log_page(self):
        """显示日志页面"""
        self._clear_page()
        self._log_page = LogPage(
            on_back=self._go_back,
        )
        self.page.add(self._log_page)
        self._nav_stack.append("log")
        self.page.update()

    def _go_back(self):
        """返回上一页"""
        if len(self._nav_stack) > 1:
            self._nav_stack.pop()  # 当前页
            prev = self._nav_stack[-1]
            if prev == "main":
                self._show_main_page()
            elif prev == "config":
                self._show_config_page()
            elif prev == "auth":
                self._show_auth_page()
            elif prev == "log":
                self._show_log_page()
