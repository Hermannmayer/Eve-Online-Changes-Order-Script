"""
价格监控仪表盘 - 主页面
显示监控物品的当前买/卖价格
"""

import logging
import time
from typing import Optional
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal, QObject, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox,
)
from PySide6.QtGui import QColor, QBrush

from src.config import Config
from src.gui.theme import AppColors

logger = logging.getLogger(__name__)


class PriceWorker(QObject):
    """后台价格更新线程（无认证，只调 ESI 公开 API）"""
    finished = Signal()
    error = Signal(str)
    result = Signal(list)

    def __init__(self, config: Config):
        super().__init__()
        self.config = config

    def run(self):
        """在后台线程执行"""
        try:
            import requests

            items = self.config.get("monitor.items", [])
            region_id = self.config.get("monitor.region_id", 10000002)
            proxies = self.config.get_proxy_dict() or None

            base_url = self.config.get("esi.base_url", "https://esi.evetech.net")
            user_agent = self.config.get("esi.user_agent", "EVE-Price-Monitor/1.0")
            headers = {"User-Agent": user_agent}

            results = []
            for item in items:
                type_id = item.get("type_id")
                name = item.get("name", str(type_id))
                try:
                    resp = requests.get(
                        f"{base_url}/v1/markets/{region_id}/orders/",
                        params={"type_id": type_id, "order_type": "all"},
                        headers=headers,
                        proxies=proxies,
                        timeout=15,
                    )
                    if resp.status_code != 200:
                        results.append({"type_id": type_id, "name": name, "error": f"HTTP {resp.status_code}"})
                        continue

                    orders = resp.json()
                    buy_orders = [o for o in orders if o.get("is_buy_order")]
                    sell_orders = [o for o in orders if not o.get("is_buy_order")]

                    best_buy = max(o["price"] for o in buy_orders) if buy_orders else 0
                    best_sell = min(o["price"] for o in sell_orders) if sell_orders else 0
                    volume = sum(o.get("volume_remain", 0) for o in orders)

                    results.append({
                        "type_id": type_id,
                        "name": name,
                        "best_buy": best_buy,
                        "best_sell": best_sell,
                        "spread": best_sell - best_buy if best_buy and best_sell else 0,
                        "volume": volume,
                        "orders": len(orders),
                        "error": None,
                    })
                except Exception as e:
                    results.append({"type_id": type_id, "name": name, "error": str(e)})

            self.result.emit(results)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class PriceMonitorPage(QWidget):
    """价格监控主页面"""

    def __init__(self, config: Config, main_window):
        super().__init__()
        self.config = config
        self.main_window = main_window
        self._is_running = False
        self._start_time: Optional[float] = None
        self._worker: Optional[QThread] = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_timer_display)

        self._init_ui()

    def _init_ui(self):
        """构建 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # 标题
        title_row = QHBoxLayout()
        title = QLabel("价格监控")
        title.setObjectName("sectionTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        layout.addLayout(title_row)

        # 运行状态卡片
        self._build_run_card(layout)

        # 价格表格
        self._build_price_table(layout)

        # 下方系统状态 + 配置摘要
        bottom_row = QHBoxLayout()
        self._build_status_card(bottom_row)
        self._build_config_summary(bottom_row)
        layout.addLayout(bottom_row)

        layout.addStretch()

    def _build_run_card(self, parent_layout: QVBoxLayout):
        """运行控制卡片"""
        card = QGroupBox()
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)

        # 状态指示
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet(f"color: {AppColors.TEXT_SECONDARY}; font-size: 20px;")
        layout.addWidget(self.status_indicator)

        status_col = QVBoxLayout()
        status_col.setSpacing(2)
        self.status_title = QLabel("运行状态")
        self.status_title.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.status_text = QLabel("就绪")
        self.status_text.setStyleSheet(f"color: {AppColors.TEXT_SECONDARY};")
        status_col.addWidget(self.status_title)
        status_col.addWidget(self.status_text)
        layout.addLayout(status_col)

        layout.addStretch()

        # 运行时间
        time_col = QVBoxLayout()
        time_col.setSpacing(2)
        time_label = QLabel("运行时间")
        time_label.setStyleSheet(f"font-size: 11px; color: {AppColors.TEXT_SECONDARY};")
        self.run_time_text = QLabel("--:--:--")
        self.run_time_text.setStyleSheet("font-size: 20px; font-weight: bold;")
        time_col.addWidget(time_label)
        time_col.addWidget(self.run_time_text)
        layout.addLayout(time_col)

        layout.addSpacing(32)

        # 刷新间隔
        interval = self.config.get("monitor.update_interval_minutes", 5)
        interval_col = QVBoxLayout()
        interval_col.setSpacing(2)
        interval_label = QLabel("刷新间隔")
        interval_label.setStyleSheet(f"font-size: 11px; color: {AppColors.TEXT_SECONDARY};")
        self.interval_text = QLabel(f"{interval} 分钟")
        self.interval_text.setStyleSheet("font-size: 15px; font-weight: bold;")
        interval_col.addWidget(interval_label)
        interval_col.addWidget(self.interval_text)
        layout.addLayout(interval_col)

        layout.addSpacing(16)

        # 按钮
        self.refresh_btn = QPushButton("立即刷新")
        self.refresh_btn.setObjectName("primary")
        self.refresh_btn.setMinimumWidth(120)
        self.refresh_btn.clicked.connect(self._manual_refresh)
        layout.addWidget(self.refresh_btn)

        self.toggle_btn = QPushButton("▶ 开始监控")
        self.toggle_btn.setObjectName("success")
        self.toggle_btn.setMinimumWidth(120)
        self.toggle_btn.clicked.connect(self._toggle_monitoring)
        layout.addWidget(self.toggle_btn)

        parent_layout.addWidget(card)

    def _build_price_table(self, parent_layout: QVBoxLayout):
        """价格数据表格"""
        self.price_table = QTableWidget(0, 6)
        self.price_table.setHorizontalHeaderLabels([
            "物品", "最高买价", "最低卖价", "差价", "订单量", "状态"
        ])

        header = self.price_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 6):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        self.price_table.setAlternatingRowColors(True)
        self.price_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.price_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.price_table.verticalHeader().setVisible(False)

        parent_layout.addWidget(self.price_table, 1)

    def _build_status_card(self, parent_layout: QHBoxLayout):
        """系统状态卡片"""
        card = QGroupBox("系统状态")
        card.setMinimumWidth(300)
        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        # ESI状态
        esi_row = QHBoxLayout()
        esi_row.addWidget(QLabel("ESI 连接"))
        esi_row.addStretch()
        self.esi_badge = QLabel("待检测")
        self.esi_badge.setStyleSheet(f"color: {AppColors.TEXT_SECONDARY};")
        esi_row.addWidget(self.esi_badge)
        layout.addLayout(esi_row)

        # 代理状态
        proxy_row = QHBoxLayout()
        proxy_row.addWidget(QLabel("代理"))
        proxy_row.addStretch()
        proxy_enabled = self.config.get("proxy.enabled", False)
        self.proxy_badge = QLabel("已启用" if proxy_enabled else "未启用")
        self.proxy_badge.setStyleSheet(
            f"color: {AppColors.SUCCESS if proxy_enabled else AppColors.TEXT_SECONDARY};"
        )
        proxy_row.addWidget(self.proxy_badge)
        layout.addLayout(proxy_row)

        # 配置状态
        cfg_row = QHBoxLayout()
        cfg_row.addWidget(QLabel("监控配置"))
        cfg_row.addStretch()
        items = self.config.get("monitor.items", [])
        self.cfg_badge = QLabel(f"{len(items)} 个物品")
        self.cfg_badge.setStyleSheet(f"color: {AppColors.PRIMARY};")
        cfg_row.addWidget(self.cfg_badge)
        layout.addLayout(cfg_row)

        # 更新时间
        layout.addSpacing(12)
        layout.addWidget(QLabel("更新时间"))
        self.update_time_label = QLabel("--")
        self.update_time_label.setStyleSheet(f"color: {AppColors.TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(self.update_time_label)

        layout.addStretch()
        parent_layout.addWidget(card)

    def _build_config_summary(self, parent_layout: QHBoxLayout):
        """配置摘要卡片"""
        card = QGroupBox("当前配置")
        layout = QVBoxLayout(card)
        layout.setSpacing(4)

        region_id = self.config.get("monitor.region_id", 10000002)
        interval = self.config.get("monitor.update_interval_minutes", 5)

        info_lines = [
            f"星域 ID: {region_id}",
            f"刷新间隔: {interval} 分钟",
            f"监控物品: {len(self.config.get('monitor.items', []))} 种",
        ]
        for line in info_lines:
            label = QLabel(line)
            label.setStyleSheet(f"color: {AppColors.TEXT_SECONDARY}; font-size: 12px;")
            layout.addWidget(label)

        layout.addStretch()
        parent_layout.addWidget(card)

    # ── 操作 ──

    def _toggle_monitoring(self):
        """启停监控"""
        if not self._is_running:
            items = self.config.get("monitor.items", [])
            if not items:
                QMessageBox.warning(self, "提示", "请先在「配置管理」中添加监控物品")
                return

            self._is_running = True
            self._start_time = time.time()
            self.status_text.setText("监控中...")
            self.status_text.setStyleSheet(f"color: {AppColors.SUCCESS};")
            self.status_indicator.setStyleSheet(f"color: {AppColors.SUCCESS}; font-size: 20px;")
            self.toggle_btn.setText("⏹ 停止监控")
            self.toggle_btn.setObjectName("danger")
            self.toggle_btn.style().unpolish(self.toggle_btn)
            self.toggle_btn.style().polish(self.toggle_btn)
            self._timer.start(1000)
            logger.info("价格监控已启动")
            self._fetch_prices()
        else:
            self._is_running = False
            self._start_time = None
            self._timer.stop()
            self.status_text.setText("已停止")
            self.status_text.setStyleSheet(f"color: {AppColors.TEXT_SECONDARY};")
            self.status_indicator.setStyleSheet(f"color: {AppColors.TEXT_SECONDARY}; font-size: 20px;")
            self.toggle_btn.setText("▶ 开始监控")
            self.toggle_btn.setObjectName("success")
            self.toggle_btn.style().unpolish(self.toggle_btn)
            self.toggle_btn.style().polish(self.toggle_btn)
            self.run_time_text.setText("--:--:--")
            logger.info("价格监控已停止")

        self.main_window.show_status(
            "监控已启动" if self._is_running else "监控已停止",
            timeout=3000,
        )

    def _manual_refresh(self):
        """手动刷新价格"""
        self._fetch_prices()

    def _fetch_prices(self):
        """启动后台线程获取价格"""
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("刷新中...")
        self.main_window.show_status("正在获取价格数据...")

        self._worker = QThread()
        worker_obj = PriceWorker(self.config)
        worker_obj.moveToThread(self._worker)

        self._worker.started.connect(worker_obj.run)
        worker_obj.finished.connect(self._worker.quit)
        worker_obj.finished.connect(worker_obj.deleteLater)
        worker_obj.finished.connect(self._on_refresh_finished)
        worker_obj.result.connect(self._on_prices_received)
        worker_obj.error.connect(self._on_refresh_error)

        self._worker.start()

    def _on_prices_received(self, results: list):
        """收到价格数据"""
        self.price_table.setRowCount(len(results))
        now = datetime.now().strftime("%H:%M:%S")
        self.update_time_label.setText(now)

        for row, data in enumerate(results):
            name = data.get("name", f"物品 {data['type_id']}")
            error = data.get("error")

            self.price_table.setItem(row, 0, QTableWidgetItem(name))

            if error:
                self.price_table.setItem(row, 1, QTableWidgetItem("--"))
                self.price_table.setItem(row, 2, QTableWidgetItem("--"))
                self.price_table.setItem(row, 3, QTableWidgetItem("--"))
                self.price_table.setItem(row, 4, QTableWidgetItem("--"))
                err_item = QTableWidgetItem("错误")
                err_item.setForeground(QBrush(QColor(AppColors.ERROR)))
                self.price_table.setItem(row, 5, err_item)
            else:
                best_buy = data.get("best_buy", 0)
                best_sell = data.get("best_sell", 0)
                spread = data.get("spread", 0)
                orders = data.get("orders", 0)

                buy_item = QTableWidgetItem(f"{best_buy:,.2f}" if best_buy else "--")
                buy_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                sell_item = QTableWidgetItem(f"{best_sell:,.2f}" if best_sell else "--")
                sell_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                spread_item = QTableWidgetItem(f"{spread:+,.2f}" if spread else "--")
                spread_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if spread > 0:
                    spread_item.setForeground(QBrush(QColor(AppColors.SUCCESS)))
                else:
                    spread_item.setForeground(QBrush(QColor(AppColors.TEXT_SECONDARY)))

                self.price_table.setItem(row, 1, buy_item)
                self.price_table.setItem(row, 2, sell_item)
                self.price_table.setItem(row, 3, spread_item)
                self.price_table.setItem(row, 4, QTableWidgetItem(str(orders)))

                status_item = QTableWidgetItem("正常")
                status_item.setForeground(QBrush(QColor(AppColors.SUCCESS)))
                self.price_table.setItem(row, 5, status_item)

        logger.info(f"价格数据已更新: {len(results)} 个物品")
        self.main_window.show_status(f"价格已更新 ({now})", timeout=3000)

    def _on_refresh_error(self, msg: str):
        """刷新出错"""
        logger.error(f"价格获取失败: {msg}")
        self.main_window.show_status(f"错误: {msg}", timeout=5000)

    def _on_refresh_finished(self):
        """刷新完成"""
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("立即刷新")

    def _update_timer_display(self):
        """更新运行时间显示"""
        if self._is_running and self._start_time:
            elapsed = time.time() - self._start_time
            h = int(elapsed // 3600)
            m = int((elapsed % 3600) // 60)
            s = int(elapsed % 60)
            self.run_time_text.setText(f"{h:02d}:{m:02d}:{s:02d}")

    def on_close(self):
        """关闭时的清理"""
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2000)
