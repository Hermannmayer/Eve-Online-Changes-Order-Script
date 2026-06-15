"""
配置管理页面 - PySide6 版本
简化版：只保留 ESI 基础、代理、监控参数
"""

import logging
from typing import Optional, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QLabel, QLineEdit, QCheckBox, QSpinBox, QDoubleSpinBox,
    QComboBox, QGridLayout, QFormLayout, QMessageBox, QFrame,
    QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog,
)

from src.config import Config
from src.gui.theme import AppColors

logger = logging.getLogger(__name__)


class ConfigPage(QWidget):
    """配置管理页面"""

    def __init__(self, config: Config, main_window):
        super().__init__()
        self.config = config
        self.main_window = main_window

        self._init_ui()

    def _init_ui(self):
        """构建 UI"""
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # 标题
        title = QLabel("配置管理")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        # ESI 配置
        self._build_esi_section(layout)

        # 代理配置
        self._build_proxy_section(layout)

        # 监控配置
        self._build_monitor_section(layout)

        # 保存按钮
        self._build_button_bar(layout)

        layout.addStretch()

        scroll.setWidget(content)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _build_esi_section(self, parent: QVBoxLayout):
        """ESI 基础配置"""
        card = QGroupBox("ESI 基础配置")
        form = QFormLayout(card)
        form.setSpacing(8)

        self.esi_url_input = QLineEdit(
            self.config.get("esi.base_url", "https://esi.evetech.net")
        )
        form.addRow("API 地址:", self.esi_url_input)

        self.ua_input = QLineEdit(
            self.config.get("esi.user_agent", "EVE-Price-Monitor/1.0")
        )
        form.addRow("User-Agent:", self.ua_input)

        parent.addWidget(card)

    def _build_proxy_section(self, parent: QVBoxLayout):
        """代理配置"""
        card = QGroupBox("代理配置")
        form = QFormLayout(card)
        form.setSpacing(8)

        self.proxy_enabled = QCheckBox("启用代理")
        self.proxy_enabled.setChecked(self.config.get("proxy.enabled", False))
        form.addRow("", self.proxy_enabled)

        self.http_proxy_input = QLineEdit(
            self.config.get("proxy.http", "")
        )
        self.http_proxy_input.setPlaceholderText("例如: http://127.0.0.1:7890")
        form.addRow("HTTP 代理:", self.http_proxy_input)

        self.https_proxy_input = QLineEdit(
            self.config.get("proxy.https", "")
        )
        self.https_proxy_input.setPlaceholderText("例如: http://127.0.0.1:7890")
        form.addRow("HTTPS 代理:", self.https_proxy_input)

        # 测试按钮
        test_btn = QPushButton("测试代理连接")
        test_btn.clicked.connect(self._test_proxy)
        form.addRow("", test_btn)

        parent.addWidget(card)

    def _build_monitor_section(self, parent: QVBoxLayout):
        """监控参数配置"""
        card = QGroupBox("监控参数")
        form = QFormLayout(card)
        form.setSpacing(8)

        self.region_id_input = QSpinBox()
        self.region_id_input.setRange(1, 99999999)
        self.region_id_input.setValue(self.config.get("monitor.region_id", 10000002))
        self.region_id_input.setFixedWidth(200)
        form.addRow("星域 ID:", self.region_id_input)

        self.interval_input = QSpinBox()
        self.interval_input.setRange(1, 60)
        self.interval_input.setValue(self.config.get("monitor.update_interval_minutes", 5))
        self.interval_input.setSuffix(" 分钟")
        self.interval_input.setFixedWidth(200)
        form.addRow("刷新间隔:", self.interval_input)

        parent.addWidget(card)

        # 监控物品列表
        items_card = QGroupBox("监控物品列表")
        items_layout = QVBoxLayout(items_card)

        # 物品表格
        self.items_table = QTableWidget(0, 3)
        self.items_table.setHorizontalHeaderLabels(["type_id", "物品名称", ""])
        header = self.items_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setEditTriggers(QTableWidget.DoubleClicked)

        # 加载已有物品
        self._load_items()

        items_layout.addWidget(self.items_table, 1)

        # 添加物品按钮行
        btn_row = QHBoxLayout()
        add_btn = QPushButton("添加物品")
        add_btn.clicked.connect(self._add_item_row)
        delete_btn = QPushButton("删除选中")
        delete_btn.clicked.connect(self._delete_selected_item)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(delete_btn)
        btn_row.addStretch()

        items_layout.addLayout(btn_row)
        parent.addWidget(items_card)

    def _build_button_bar(self, parent: QVBoxLayout):
        """底部按钮栏"""
        btn_row = QHBoxLayout()

        save_btn = QPushButton("保存配置")
        save_btn.setObjectName("primary")
        save_btn.setMinimumWidth(120)
        save_btn.clicked.connect(self._save_config)
        btn_row.addWidget(save_btn)

        reset_btn = QPushButton("重置默认")
        reset_btn.clicked.connect(self._reset_defaults)
        btn_row.addWidget(reset_btn)

        validate_btn = QPushButton("验证配置")
        validate_btn.clicked.connect(self._validate_config)
        btn_row.addWidget(validate_btn)

        btn_row.addStretch()
        parent.addLayout(btn_row)

    # ── 物品列表操作 ──

    def _load_items(self):
        """从配置加载物品列表到表格"""
        items = self.config.get("monitor.items", [])
        self.items_table.setRowCount(len(items))
        for row, item in enumerate(items):
            type_id = QTableWidgetItem(str(item.get("type_id", "")))
            name = QTableWidgetItem(item.get("name", ""))

            del_btn = QPushButton("删除")
            del_btn.setFixedSize(60, 28)
            del_btn.clicked.connect(lambda checked, r=row: self._delete_item_row(r))

            self.items_table.setItem(row, 0, type_id)
            self.items_table.setItem(row, 1, name)
            self.items_table.setCellWidget(row, 2, del_btn)

    def _add_item_row(self):
        """添加一行空物品"""
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)

        type_id = QTableWidgetItem("")
        name = QTableWidgetItem("")

        del_btn = QPushButton("删除")
        del_btn.setFixedSize(60, 28)
        del_btn.clicked.connect(lambda checked, r=row: self._delete_item_row(r))

        self.items_table.setItem(row, 0, type_id)
        self.items_table.setItem(row, 1, name)
        self.items_table.setCellWidget(row, 2, del_btn)

    def _delete_selected_item(self):
        """删除选中行"""
        row = self.items_table.currentRow()
        if row >= 0:
            self._delete_item_row(row)

    def _delete_item_row(self, row: int):
        """删除指定行"""
        self.items_table.removeRow(row)
        # 重新绑定删除按钮（行号变了）
        for r in range(self.items_table.rowCount()):
            btn = self.items_table.cellWidget(r, 2)
            if btn:
                try:
                    btn.clicked.disconnect()
                except TypeError:
                    pass
                btn.clicked.connect(lambda checked, rr=r: self._delete_item_row(rr))

    # ── 保存与验证 ──

    def _save_config(self):
        """保存配置"""
        try:
            # ESI 配置
            self.config.set("esi.base_url", self.esi_url_input.text().strip())
            self.config.set("esi.user_agent", self.ua_input.text().strip())

            # 代理
            self.config.set("proxy.enabled", self.proxy_enabled.isChecked())
            self.config.set("proxy.http", self.http_proxy_input.text().strip())
            self.config.set("proxy.https", self.https_proxy_input.text().strip())

            # 监控参数
            self.config.set("monitor.region_id", self.region_id_input.value())
            self.config.set("monitor.update_interval_minutes", self.interval_input.value())

            # 物品列表
            items = []
            for row in range(self.items_table.rowCount()):
                type_id_item = self.items_table.item(row, 0)
                name_item = self.items_table.item(row, 1)
                if type_id_item and type_id_item.text().strip():
                    try:
                        items.append({
                            "type_id": int(type_id_item.text().strip()),
                            "name": name_item.text().strip() if name_item else "",
                        })
                    except ValueError:
                        continue

            self.config.set("monitor.items", items)

            if self.config.save():
                self.main_window.show_status("配置已保存", timeout=3000)
                logger.info("配置保存成功")
            else:
                QMessageBox.warning(self, "错误", "配置文件保存失败")

        except Exception as e:
            logger.error(f"保存配置出错: {e}")
            QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def _validate_config(self):
        """验证配置"""
        errors = self.config.validate()
        if not errors:
            QMessageBox.information(self, "验证通过", "所有配置项正确")
        else:
            msg = "\n".join(f"• {e}" for e in errors)
            QMessageBox.warning(self, "配置问题", msg)

    def _reset_defaults(self):
        """重置默认"""
        reply = QMessageBox.question(
            self, "确认重置",
            "重置所有配置为默认值？此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            from src.config import DEFAULT_CONFIG
            self.config._data = self.config._deep_copy(DEFAULT_CONFIG)
            self._load_items()
            self.main_window.show_status("已重置为默认值，请点击保存生效", timeout=5000)

    def _test_proxy(self):
        """测试代理连接"""
        import requests

        http_url = self.http_proxy_input.text().strip()
        https_url = self.https_proxy_input.text().strip()

        if not http_url and not https_url:
            QMessageBox.warning(self, "提示", "请先填写代理地址")
            return

        proxies = {}
        if http_url:
            proxies["http"] = http_url
        if https_url:
            proxies["https"] = https_url

        self.main_window.show_status("正在测试代理连接...")

        try:
            resp = requests.get(
                "https://login.eveonline.com/oauth/authorize",
                proxies=proxies if proxies else None,
                timeout=10,
                allow_redirects=False,
            )
            if "text/html" in resp.headers.get("Content-Type", "") and "Cloudflare" in resp.text:
                QMessageBox.warning(self, "测试失败", "仍收到 Cloudflare 拦截页面")
            else:
                QMessageBox.information(self, "测试成功", f"代理连接正常 (HTTP {resp.status_code})")
        except Exception as e:
            QMessageBox.critical(self, "测试失败", str(e))

    def on_close(self):
        """关闭清理"""
        pass
