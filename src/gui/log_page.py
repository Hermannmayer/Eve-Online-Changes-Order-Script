"""
日志查看页面 - PySide6 版本
实时显示日志，支持过滤、搜索、导出
"""

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QComboBox, QTextEdit, QFileDialog,
    QMessageBox,
)
from PySide6.QtGui import QColor, QTextCursor, QTextCharFormat

from src.gui.theme import AppColors

logger = logging.getLogger(__name__)


class LogHandler(logging.Handler):
    """自定义日志处理器，通过信号安全传递到 GUI 线程"""

    def __init__(self, signal: Signal):
        super().__init__()
        self.signal = signal
        self.setFormatter(logging.Formatter(
            '[%(asctime)s] %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        ))

    def emit(self, record):
        try:
            msg = self.format(record)
            self.signal.emit(msg)
        except Exception:
            self.handleError(record)


class LogPage(QWidget):
    """日志查看页面"""

    log_signal = Signal(str)

    LEVEL_COLORS = {
        "DEBUG": "#9E9E9E",
        "INFO": "#4CAF50",
        "WARNING": "#FF9800",
        "ERROR": "#EF5350",
        "CRITICAL": "#F44336",
    }

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self._log_lines: list[str] = []
        self._max_lines = 1000
        self._current_filter = "ALL"
        self._search_text = ""

        self._init_ui()
        self._setup_log_handler()

        # 连接信号
        self.log_signal.connect(self._on_log)

    def _init_ui(self):
        """构建 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # 标题
        title_row = QHBoxLayout()
        title = QLabel("日志查看")
        title.setObjectName("sectionTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        layout.addLayout(title_row)

        # 工具栏
        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索日志...")
        self.search_input.setFixedWidth(200)
        self.search_input.returnPressed.connect(self._on_search)
        toolbar.addWidget(self.search_input)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "调试", "信息", "警告", "错误"])
        self.filter_combo.setFixedWidth(100)
        self.filter_combo.currentTextChanged.connect(self._on_filter_change)
        toolbar.addWidget(self.filter_combo)

        toolbar.addStretch()

        self.line_count_label = QLabel("日志行数: 0")
        self.line_count_label.setStyleSheet(f"color: {AppColors.TEXT_SECONDARY}; font-size: 12px;")
        toolbar.addWidget(self.line_count_label)

        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self._clear_logs)
        toolbar.addWidget(clear_btn)

        copy_btn = QPushButton("复制")
        copy_btn.clicked.connect(self._copy_logs)
        toolbar.addWidget(copy_btn)

        export_btn = QPushButton("导出")
        export_btn.clicked.connect(self._export_logs)
        toolbar.addWidget(export_btn)

        layout.addLayout(toolbar)

        # 日志显示区域
        self.log_view = QTextEdit()
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QTextEdit.NoWrap)
        self.log_view.setUndoRedoEnabled(False)
        layout.addWidget(self.log_view, 1)

        # 添加初始日志
        self._append_log("[系统] 日志查看器已启动")
        self._append_log("[系统] 所有日志将显示在此处")

    def _setup_log_handler(self):
        """安装日志处理器"""
        self._handler = LogHandler(self.log_signal)
        self._handler.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(self._handler)

    def _on_log(self, msg: str):
        """接收日志消息"""
        self._add_log_line(msg)

    def _add_log_line(self, msg: str):
        """添加一行日志"""
        self._log_lines.append(msg)
        if len(self._log_lines) > self._max_lines:
            self._log_lines = self._log_lines[-self._max_lines:]

        self.line_count_label.setText(f"日志行数: {len(self._log_lines)}")

        if self._should_display(msg):
            self._append_log(msg)

    def _append_log(self, msg: str):
        """追加日志到显示区域（带颜色）"""
        color = self._get_level_color(msg)

        cursor = self.log_view.textCursor()
        cursor.movePosition(QTextCursor.End)

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.insertText(msg + "\n", fmt)

        # 自动滚动到底部
        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _get_level_color(self, msg: str) -> str:
        """根据日志级别返回颜色"""
        for level, color in self.LEVEL_COLORS.items():
            if f"[{level}]" in msg.upper():
                return color
        return "#E0E0E0"

    def _should_display(self, msg: str) -> bool:
        """判断是否应该显示该日志"""
        if self._search_text and self._search_text.lower() not in msg.lower():
            return False

        level_map = {"全部": "ALL", "调试": "DEBUG", "信息": "INFO", "警告": "WARNING", "错误": "ERROR"}
        filter_val = level_map.get(self._current_filter, "ALL")
        if filter_val != "ALL":
            if f"[{filter_val}]" not in msg.upper():
                return False

        return True

    def _on_filter_change(self, text: str):
        """过滤条件变更"""
        self._current_filter = text
        self._refresh_display()

    def _on_search(self):
        """搜索"""
        self._search_text = self.search_input.text().strip()
        self._refresh_display()

    def _refresh_display(self):
        """刷新日志显示"""
        self.log_view.clear()
        for line in self._log_lines:
            if self._should_display(line):
                self._append_log(line)

    def _clear_logs(self):
        """清空日志"""
        self._log_lines.clear()
        self.log_view.clear()
        self.line_count_label.setText("日志行数: 0")

    def _copy_logs(self):
        """复制日志到剪贴板"""
        text = self.log_view.toPlainText()
        if text:
            from PySide6.QtGui import QGuiApplication
            QGuiApplication.clipboard().setText(text)

    def _export_logs(self):
        """导出日志到文件"""
        path, _ = QFileDialog.getSaveFileName(
            self, "导出日志", "eve_price_log.txt",
            "文本文件 (*.txt *.log);;所有文件 (*.*)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.log_view.toPlainText())
                self.main_window.show_status(f"日志已保存到 {path}", timeout=3000)
            except Exception as e:
                QMessageBox.critical(self, "导出失败", str(e))

    def on_close(self):
        """释放资源"""
        logging.getLogger().removeHandler(self._handler)
