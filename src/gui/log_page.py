"""
日志页面 - 实时日志查看
"""

import logging
from io import StringIO
from typing import Optional, Callable

import flet as ft

from src.gui.theme import AppColors, AppSizes


class LogHandler(logging.Handler):
    """自定义日志处理器，将日志消息发送到 GUI"""

    def __init__(self, callback: Callable[[str], None]):
        super().__init__()
        self.callback = callback
        self.setFormatter(logging.Formatter(
            '[%(asctime)s] %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        ))

    def emit(self, record):
        try:
            msg = self.format(record)
            self.callback(msg)
        except Exception:
            self.handleError(record)


class LogPage(ft.Container):
    """日志查看页面"""

    def __init__(self, on_back: Optional[Callable] = None):
        super().__init__()
        self.on_back = on_back
        self._log_lines: list[str] = []
        self._max_lines = 1000
        self._log_display = ft.Text(
            value="",
            size=12,
            font_family="Consolas",
            color=ft.Colors.GREEN_300,
            selectable=True,
        )
        self._log_container = ft.Container(
            content=self._log_display,
            bgcolor=ft.Colors.GREY_900,
            border_radius=8,
            padding=12,
            expand=True,
        )
        self._filter_dropdown = ft.Dropdown(
            value="ALL",
            options=[
                ft.dropdown.Option("ALL", "全部"),
                ft.dropdown.Option("DEBUG", "调试"),
                ft.dropdown.Option("INFO", "信息"),
                ft.dropdown.Option("WARNING", "警告"),
                ft.dropdown.Option("ERROR", "错误"),
            ],
            width=100,
            dense=True,
            on_change=self._on_filter_change,
        )
        self._search_field = ft.TextField(
            hint_text="搜索日志...",
            width=200,
            dense=True,
            on_submit=self._on_search,
        )
        self._current_filter = "ALL"
        self._search_text = ""

        self.padding = AppSizes.CONTENT_PADDING
        self.expand = True

        # 安装日志处理器
        self._handler = LogHandler(self._on_log)
        self._handler.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(self._handler)

    def build(self):
        """构建日志页面"""
        # 添加一些初始日志
        self._add_log_line("[系统] 日志查看器已启动")
        self._add_log_line("[系统] 所有控制台输出将显示在此处")

        self.content = ft.Column(
            controls=[
                # 顶部栏
                ft.Row(
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            tooltip="返回主页面",
                            on_click=lambda e: self.on_back() if self.on_back else None,
                        ),
                        ft.Text("📋 日志查看", size=22, weight=ft.FontWeight.BOLD),
                        ft.Container(expand=True),
                        self._search_field,
                        self._filter_dropdown,
                        ft.IconButton(
                            icon=ft.Icons.CLEAR_ALL,
                            tooltip="清空日志",
                            on_click=self._clear_logs,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.CONTENT_COPY,
                            tooltip="复制日志",
                            on_click=self._copy_logs,
                        ),
                    ],
                ),
                ft.Divider(height=2),
                # 工具栏
                ft.Row(
                    controls=[
                        ft.Text(f"日志行数: {len(self._log_lines)}",
                                size=12, color=AppColors.TEXT_SECONDARY),
                        ft.Container(expand=True),
                        ft.OutlinedButton(
                            "📥 导出日志",
                            icon=ft.Icons.DOWNLOAD,
                            height=35,
                            on_click=self._export_logs,
                        ),
                    ],
                ),
                # 日志显示区域
                self._log_container,
            ],
            spacing=8,
            expand=True,
        )
        return self

    def _add_log_line(self, msg: str):
        """添加一行日志"""
        self._log_lines.append(msg)
        if len(self._log_lines) > self._max_lines:
            self._log_lines = self._log_lines[-self._max_lines:]

        # 根据过滤条件决定是否显示
        if self._should_display(msg):
            if self._log_display.value:
                self._log_display.value += "\n" + msg
            else:
                self._log_display.value = msg
            # 自动滚动到底部
            self._log_display.update()

    def _on_log(self, msg: str):
        """接收日志消息的回调"""
        self._add_log_line(msg)

    def _should_display(self, msg: str) -> bool:
        """判断是否应该显示该日志"""
        # 搜索过滤
        if self._search_text and self._search_text.lower() not in msg.lower():
            return False

        # 级别过滤
        if self._current_filter != "ALL":
            level_tag = f"[{self._current_filter}]"
            if level_tag not in msg.upper():
                return False

        return True

    def _on_filter_change(self, e):
        """过滤条件变更"""
        self._current_filter = self._filter_dropdown.value
        self._refresh_display()

    def _on_search(self, e):
        """搜索"""
        self._search_text = self._search_field.value or ""
        self._refresh_display()

    def _refresh_display(self):
        """刷新日志显示"""
        # 重新应用过滤
        filtered = []
        for line in self._log_lines:
            if self._should_display(line):
                filtered.append(line)

        self._log_display.value = "\n".join(filtered)
        self._log_display.update()

    def _clear_logs(self, e):
        """清空日志"""
        self._log_lines.clear()
        self._log_display.value = ""
        self._log_display.update()

    def _copy_logs(self, e):
        """复制日志到剪贴板"""
        if self._log_display.value:
            self.page.set_clipboard(self._log_display.value)
            # 显示提示
            snack = ft.SnackBar(
                content=ft.Text("✅ 日志已复制到剪贴板"),
                duration=2000,
            )
            self.page.overlay.append(snack)
            snack.open = True
            self.page.update()

    def _export_logs(self, e):
        """导出日志到文件"""
        def on_save_result(e: ft.FilePickerResultEvent):
            if e.path:
                try:
                    with open(e.path, "w", encoding="utf-8") as f:
                        f.write(self._log_display.value or "")
                    snack = ft.SnackBar(
                        content=ft.Text(f"✅ 日志已保存到 {e.path}"),
                        duration=3000,
                    )
                    self.page.overlay.append(snack)
                    snack.open = True
                    self.page.update()
                except Exception as ex:
                    snack = ft.SnackBar(
                        content=ft.Text(f"❌ 保存失败: {ex}"),
                        duration=3000,
                    )
                    self.page.overlay.append(snack)
                    snack.open = True
                    self.page.update()

        save_dialog = ft.FilePicker(on_result=on_save_result)
        self.page.overlay.append(save_dialog)
        self.page.update()
        save_dialog.save_file(
            file_name="eve_market_bot_log.txt",
            allowed_extensions=["txt", "log"]
        )

    def dispose(self):
        """释放资源"""
        logging.getLogger().removeHandler(self._handler)
