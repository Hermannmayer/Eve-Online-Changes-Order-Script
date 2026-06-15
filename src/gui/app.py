"""
PySide6 应用主窗口 - 侧边栏导航 + 页面堆栈
"""

import logging
from typing import Optional

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget, QStatusBar, QLabel,
)

from src.config import Config
from src.gui.theme import AppColors, get_stylesheet
from src.gui.main_page import PriceMonitorPage
from src.gui.config_page import ConfigPage
from src.gui.log_page import LogPage

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """EVE 价格监控主窗口"""

    PAGE_NAMES = ["price", "config", "log"]
    PAGE_TITLES = ["价格监控", "配置管理", "日志查看"]
    PAGE_ICONS = ["\U0001f4ca", "⚙️", "\U0001f4cb"]

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.pages: dict[str, QWidget] = {}

        self._init_ui()
        self._setup_pages()
        self._connect_signals()

        # 加载样式
        QApplication.instance().setStyleSheet(get_stylesheet())

    def _init_ui(self):
        """初始化窗口"""
        self.setWindowTitle("EVE 价格监控")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        # 居中
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

        # 中央部件
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 侧边栏 ──
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(160)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # 侧边栏标题
        title_label = QLabel("  EVE 价格监控")
        title_label.setStyleSheet(f"""
            font-size: 15px; font-weight: bold; color: {AppColors.TEXT_BRIGHT};
            padding: 16px 10px; background-color: {AppColors.BG_SIDEBAR};
        """)
        sidebar_layout.addWidget(title_label)
        sidebar_layout.addSpacing(8)

        # 导航列表
        self.nav_list = QListWidget()
        self.nav_list.setObjectName("navList")
        self.nav_list.setFocusPolicy(Qt.NoFocus)

        for i, (title, icon) in enumerate(zip(self.PAGE_TITLES, self.PAGE_ICONS)):
            item = QListWidgetItem(f"  {icon}  {title}")
            item.setData(Qt.UserRole, self.PAGE_NAMES[i])
            item.setSizeHint(QSize(0, 42))
            self.nav_list.addItem(item)

        sidebar_layout.addWidget(self.nav_list)
        sidebar_layout.addStretch()

        # 版本标签
        version_label = QLabel("v1.0")
        version_label.setStyleSheet(f"color: {AppColors.TEXT_SECONDARY}; font-size: 11px; padding: 8px 12px;")
        version_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(version_label)

        main_layout.addWidget(sidebar)

        # ── 内容区域 ──
        content_area = QWidget()
        content_area.setObjectName("contentArea")
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)

        main_layout.addWidget(content_area, 1)

        # ── 状态栏 ──
        self.status_bar = QStatusBar()
        self.status_bar.setObjectName("statusBar")
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)

    def _setup_pages(self):
        """创建各个页面"""
        self.pages["price"] = PriceMonitorPage(self.config, self)
        self.pages["config"] = ConfigPage(self.config, self)
        self.pages["log"] = LogPage(self)

        for name in self.PAGE_NAMES:
            self.stack.addWidget(self.pages[name])

        # 默认显示第一个
        self.nav_list.setCurrentRow(0)
        self.stack.setCurrentIndex(0)

    def _connect_signals(self):
        """连接信号"""
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)

    def _on_nav_changed(self, index: int):
        """导航切换"""
        if 0 <= index < len(self.PAGE_NAMES):
            self.stack.setCurrentIndex(index)

    def show_status(self, message: str, timeout: int = 5000):
        """显示状态栏消息"""
        self.status_label.setText(message)
        if timeout > 0:
            QTimer.singleShot(timeout, lambda: self.status_label.setText("就绪"))

    def closeEvent(self, event):
        """窗口关闭事件"""
        for page in self.pages.values():
            if hasattr(page, "on_close") and callable(page.on_close):
                page.on_close()
        super().closeEvent(event)
