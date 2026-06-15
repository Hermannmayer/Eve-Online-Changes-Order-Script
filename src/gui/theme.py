"""
OneDarkPro 暗黑主题 - QSS 样式表 + 颜色常量
"""

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication


class AppColors:
    """OneDarkPro 配色常量"""
    # 背景
    BG = "#282c34"
    BG_SIDEBAR = "#21252b"
    BG_CARD = "#2c323c"
    BG_INPUT = "#1e2229"
    BG_HOVER = "#3a3f4b"
    BG_SELECTION = "#3e4452"
    BG_LOG = "#1e1e1e"

    # 边框
    BORDER = "#3b4048"
    BORDER_LIGHT = "#4b5263"

    # 文字
    TEXT = "#abb2bf"
    TEXT_SECONDARY = "#5c6370"
    TEXT_BRIGHT = "#e5e7eb"
    TEXT_ACCENT = "#61afef"

    # 功能色
    PRIMARY = "#61afef"
    PRIMARY_HOVER = "#82bff5"
    SUCCESS = "#98c379"
    SUCCESS_HOVER = "#b0d78e"
    WARNING = "#e5c07b"
    WARNING_HOVER = "#edcf94"
    ERROR = "#e06c75"
    ERROR_HOVER = "#e98a93"
    INFO = "#56b6c2"
    ORANGE = "#d19a66"
    PURPLE = "#c678dd"

    # 表格
    TABLE_ROW_ALT = "#2c323c"
    TABLE_GRID = "#3b4048"
    TABLE_HEADER = "#21252b"
    TABLE_HEADER_TEXT = "#abb2bf"
    TABLE_SELECTION = "#3e4452"

    # 滚动条
    SCROLLBAR_BG = "#282c34"
    SCROLLBAR_HANDLE = "#4b5263"
    SCROLLBAR_HOVER = "#5c6370"


def get_stylesheet() -> str:
    """返回全局 QSS 样式表（OneDarkPro 暗黑主题）"""
    C = AppColors
    return f"""
    /* ── 全局 ── */
    QMainWindow, QWidget {{
        background-color: {C.BG};
        font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
        font-size: 13px;
        color: {C.TEXT};
    }}
    QWidget#sidebar {{
        background-color: {C.BG_SIDEBAR};
        border-right: 1px solid {C.BORDER};
    }}
    QWidget#contentArea {{
        background-color: {C.BG};
    }}

    /* ── 导航侧栏 ── */
    QListWidget#navList {{
        background-color: transparent;
        border: none;
        outline: none;
        padding: 4px;
    }}
    QListWidget#navList::item {{
        padding: 10px 14px;
        border-radius: 6px;
        color: {C.TEXT};
        margin: 1px 0;
    }}
    QListWidget#navList::item:hover {{
        background-color: {C.BG_HOVER};
        color: {C.TEXT_BRIGHT};
    }}
    QListWidget#navList::item:selected {{
        background-color: {C.PRIMARY};
        color: #ffffff;
        font-weight: bold;
    }}

    /* ── 按钮 ── */
    QPushButton {{
        border: 1px solid {C.BORDER};
        border-radius: 4px;
        padding: 6px 16px;
        background-color: {C.BG_CARD};
        color: {C.TEXT};
        min-height: 24px;
    }}
    QPushButton:hover {{
        background-color: {C.BG_HOVER};
        border-color: {C.BORDER_LIGHT};
    }}
    QPushButton:pressed {{
        background-color: {C.BG_SELECTION};
    }}
    QPushButton:disabled {{
        color: {C.TEXT_SECONDARY};
        background-color: {C.BG};
        border-color: {C.BORDER};
    }}
    QPushButton#primary {{
        background-color: {C.PRIMARY};
        color: #ffffff;
        border: none;
        font-weight: bold;
    }}
    QPushButton#primary:hover {{
        background-color: {C.PRIMARY_HOVER};
    }}
    QPushButton#success {{
        background-color: {C.SUCCESS};
        color: #ffffff;
        border: none;
        font-weight: bold;
    }}
    QPushButton#success:hover {{
        background-color: {C.SUCCESS_HOVER};
    }}
    QPushButton#danger {{
        background-color: {C.ERROR};
        color: #ffffff;
        border: none;
        font-weight: bold;
    }}
    QPushButton#danger:hover {{
        background-color: {C.ERROR_HOVER};
    }}

    /* ── 输入框 ── */
    QLineEdit, QSpinBox, QDoubleSpinBox {{
        border: 1px solid {C.BORDER};
        border-radius: 4px;
        padding: 4px 8px;
        background-color: {C.BG_INPUT};
        color: {C.TEXT};
        min-height: 20px;
        selection-background-color: {C.BG_SELECTION};
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {C.PRIMARY};
    }}

    /* ── 下拉框 ── */
    QComboBox {{
        border: 1px solid {C.BORDER};
        border-radius: 4px;
        padding: 4px 8px;
        background-color: {C.BG_INPUT};
        color: {C.TEXT};
        min-height: 20px;
    }}
    QComboBox:hover {{
        border-color: {C.PRIMARY};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {C.BG_CARD};
        color: {C.TEXT};
        border: 1px solid {C.BORDER};
        selection-background-color: {C.BG_SELECTION};
    }}

    /* ── 复选框 ── */
    QCheckBox {{
        spacing: 8px;
        color: {C.TEXT};
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {C.BORDER};
        border-radius: 3px;
        background-color: {C.BG_INPUT};
    }}
    QCheckBox::indicator:checked {{
        background-color: {C.PRIMARY};
        border-color: {C.PRIMARY};
    }}

    /* ── 卡片容器 ── */
    QGroupBox {{
        background-color: {C.BG_CARD};
        border: 1px solid {C.BORDER};
        border-radius: 8px;
        margin-top: 0;
        padding: 16px;
        font-weight: normal;
        color: {C.TEXT};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 16px;
        padding: 0 4px;
        color: {C.TEXT_BRIGHT};
        font-size: 14px;
        font-weight: bold;
    }}

    /* ── 表格 ── */
    QTableWidget {{
        border: 1px solid {C.BORDER};
        border-radius: 4px;
        gridline-color: {C.TABLE_GRID};
        background-color: {C.BG};
        alternate-background-color: {C.TABLE_ROW_ALT};
        color: {C.TEXT};
        selection-background-color: {C.TABLE_SELECTION};
    }}
    QTableWidget::item {{
        padding: 4px 8px;
        border-bottom: 1px solid {C.BORDER};
    }}
    QTableWidget::item:selected {{
        background-color: {C.TABLE_SELECTION};
        color: {C.TEXT_BRIGHT};
    }}
    QHeaderView::section {{
        background-color: {C.TABLE_HEADER};
        color: {C.TABLE_HEADER_TEXT};
        border: none;
        border-bottom: 1px solid {C.BORDER};
        padding: 6px 8px;
        font-weight: bold;
    }}

    /* ── 日志区域 ── */
    QTextEdit#logView {{
        background-color: {C.BG_LOG};
        color: {C.SUCCESS};
        border: 1px solid {C.BORDER};
        border-radius: 4px;
        font-family: "Consolas", "Courier New", monospace;
        font-size: 12px;
        padding: 8px;
    }}

    /* ── 状态栏 ── */
    QStatusBar {{
        background-color: {C.BG_SIDEBAR};
        border-top: 1px solid {C.BORDER};
        color: {C.TEXT_SECONDARY};
        font-size: 12px;
    }}
    QStatusBar::item {{
        border: none;
    }}

    /* ── 标签 ── */
    QLabel#sectionTitle {{
        font-size: 20px;
        font-weight: bold;
        color: {C.TEXT_BRIGHT};
    }}
    QLabel#helpText {{
        font-size: 12px;
        color: {C.TEXT_SECONDARY};
        font-style: italic;
    }}

    /* ── 进度条 ── */
    QProgressBar {{
        border: 1px solid {C.BORDER};
        border-radius: 4px;
        text-align: center;
        height: 18px;
        background-color: {C.BG_INPUT};
        color: {C.TEXT};
    }}
    QProgressBar::chunk {{
        background-color: {C.PRIMARY};
        border-radius: 3px;
    }}

    /* ── 滚动条 ── */
    QScrollBar:vertical {{
        width: 8px;
        background: {C.SCROLLBAR_BG};
    }}
    QScrollBar::handle:vertical {{
        background: {C.SCROLLBAR_HANDLE};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {C.SCROLLBAR_HOVER};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        height: 8px;
        background: {C.SCROLLBAR_BG};
    }}
    QScrollBar::handle:horizontal {{
        background: {C.SCROLLBAR_HANDLE};
        border-radius: 4px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {C.SCROLLBAR_HOVER};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    /* ── 对话框 ── */
    QMessageBox {{
        background-color: {C.BG_CARD};
        color: {C.TEXT};
    }}
    QMessageBox QLabel {{
        color: {C.TEXT};
    }}
    QMessageBox QPushButton {{
        min-width: 80px;
    }}

    /* ── 滚动区域 ── */
    QScrollArea {{
        border: none;
        background-color: transparent;
    }}
    QScrollArea > QWidget > QWidget {{
        background-color: transparent;
    }}

    /* ── Tab 切换 ── */
    QStackedWidget {{
        background-color: transparent;
    }}
    """
