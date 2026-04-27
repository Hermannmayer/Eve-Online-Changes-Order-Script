"""
主题样式定义 - Flet 界面主题
"""

import flet as ft


def get_theme():
    """获取应用主题"""
    return ft.Theme(
        color_scheme_seed=ft.Colors.BLUE_GREY,
        use_material3=True,
        font_family="Microsoft YaHei",
        appbar_theme=ft.AppBarTheme(
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            center_title=True,
        ),
        navigation_bar_theme=ft.NavigationBarTheme(
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        ),
    )


# 颜色常量（使用 Flet 0.84.0 兼容的属性名）
class AppColors:
    PRIMARY = ft.Colors.BLUE_700
    SUCCESS = ft.Colors.GREEN_600
    WARNING = ft.Colors.ORANGE_700
    ERROR = ft.Colors.RED_700
    BG_DARK = ft.Colors.GREY_900
    BG_LIGHT = ft.Colors.GREY_50
    SURFACE = ft.Colors.GREY_100
    TEXT_PRIMARY = ft.Colors.GREY_900
    TEXT_SECONDARY = ft.Colors.GREY_600
    INFO = ft.Colors.BLUE_500
    ACCENT = ft.Colors.CYAN_500
    SECONDARY = ft.Colors.BLUE_GREY_600


# 尺寸常量
class AppSizes:
    SIDEBAR_WIDTH = 220
    CONTENT_PADDING = 30
    CARD_ELEVATION = 2
    INPUT_WIDTH = 400
    LABEL_WIDTH = 180
    BUTTON_HEIGHT = 40


def section_header(text: str) -> ft.Text:
    """创建区域标题"""
    return ft.Text(
        text,
        size=18,
        weight=ft.FontWeight.BOLD,
        color=AppColors.PRIMARY,
    )


def help_text(text: str) -> ft.Text:
    """创建帮助说明文本"""
    return ft.Text(
        text,
        size=12,
        color=AppColors.TEXT_SECONDARY,
        italic=True,
    )


def status_badge(text: str, color: str) -> ft.Container:
    """创建状态标签"""
    return ft.Container(
        content=ft.Text(text, size=12, color=ft.Colors.WHITE, weight=ft.FontWeight.BOLD),
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        border_radius=ft.border_radius.all(12),
        bgcolor=color,
    )
