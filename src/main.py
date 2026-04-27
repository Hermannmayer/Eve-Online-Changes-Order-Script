"""
EVE Online 市场改单脚本 - 主入口
"""

import time
import logging
import sys
from typing import List, Optional

from src.config import Config
from src.auth import ESIAuth
from src.data_collector import DataCollector
from src.decision import DecisionEngine
from src.automation import GUIAutomation
from src.risk_manager import RiskManager, setup_logger

logger = logging.getLogger(__name__)


class MarketBot:
    """市场改单机器人主控类"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger()
        self.auth = ESIAuth(
            config.get("esi.client_id"),
            config.get("esi.client_secret"),
            config.get("esi.callback_url")
        )
        self.data_collector = DataCollector(self.auth)
        self.decision_engine = DecisionEngine(
            sell_adjust_percent=config.get("automation.price_adjustment_percent", -0.1),
            buy_adjust_percent=config.get("automation.buy_price_adjustment_percent", 0.1),
            max_change_percent=config.get("automation.max_price_change_percent", 5.0)
        )
        self.automation = GUIAutomation(
            window_title=config.get("game.window_title"),
            templates=config.get("templates"),
            fallback_coords=config.get("fallback_coordinates")
        )
        self.risk_manager = RiskManager(
            cooldown_seconds=config.get("automation.modify_cooldown_seconds", 300)
        )
        self._running = False

    def run_once(self):
        """执行一轮检查与改价"""
        self.logger.info("=== 开始新一轮检查 ===")

        # 1. 检查游戏窗口
        if not self.automation.find_game_window():
            self.logger.warning("游戏窗口未找到，跳过本轮")
            return

        # 2. 获取角色挂单
        character_id = self.config.get("character.id")
        orders = self.data_collector.get_character_orders(character_id)
        self.logger.info(f"获取到 {len(orders)} 个活跃订单")

        # 3. 逐个分析订单
        to_modify = []
        for order in orders:
            try:
                # 解析星域
                region_id = self.data_collector.get_region_id(order.get("location_id"))
                # 获取市场价格
                market_orders = self.data_collector.get_market_orders(
                    region_id, order.get("type_id"), order.get("is_buy_order")
                )
                # 判断首位
                if self.decision_engine.is_first_in_queue(order, market_orders):
                    self.logger.info(f"订单 {order.get('order_id')} 已在首位，跳过")
                    continue
                # 计算新价格
                new_price = self.decision_engine.calculate_new_price(order, market_orders)
                if new_price is None:
                    continue
                # 风险检查
                if not self.decision_engine.risk_check(order.get("price"), new_price):
                    self.logger.warning(f"订单 {order.get('order_id')} 价格波动超限，跳过")
                    continue
                # 冷却检查
                if not self.risk_manager.check_cooldown(order.get("order_id")):
                    continue
                to_modify.append((order, new_price))
            except Exception as e:
                self.logger.error(f"处理订单 {order.get('order_id')} 时出错: {e}")

        # 4. GUI 自动化改价
        if to_modify:
            self.automation.activate_window()
            for order, new_price in to_modify:
                success = self.automation.modify_order(order, new_price)
                if success:
                    self.risk_manager.record_modification(order.get("order_id"))
                    self.risk_manager.log_order_action(
                        order.get("order_id"),
                        order.get("type_id"),
                        order.get("price"),
                        new_price,
                        False,
                        "改价成功"
                    )
                    time.sleep(1)  # 操作间隔

        self.logger.info(f"=== 本轮完成，改价 {len(to_modify)} 个订单 ===")

    def run(self):
        """主循环"""
        self._running = True
        interval = self.config.get("automation.interval_minutes", 5) * 60

        self.logger.info("EVE 市场改单脚本启动")
        while self._running:
            try:
                self.run_once()
            except Exception as e:
                self.logger.error(f"运行出错: {e}")
            self.logger.info(f"等待 {interval} 秒后下一轮...")
            time.sleep(interval)

    def stop(self):
        """停止运行"""
        self._running = False


def run_cli():
    """CLI 模式入口（原始逻辑）"""
    config = Config()
    if not config.load():
        print("错误：无法加载配置文件 config.yaml")
        print("请先复制 config.yaml.example 为 config.yaml 并填写配置")
        return

    errors = config.validate()
    if errors:
        print("配置缺失以下项：")
        for err in errors:
            print(f"  - {err}")
        return

    bot = MarketBot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
        print("\n脚本已停止")


def run_gui():
    """GUI 模式入口"""
    config = Config()
    if not config.load():
        print("错误：无法加载配置文件 config.yaml")
        print("请先复制 config.yaml.example 为 config.yaml 并填写配置")
        return

    from src.gui.app import EveMarketApp
    app = EveMarketApp(config)
    app.run()


def main():
    """主入口 - 默认启动 GUI，--cli 切换到命令行模式"""
    if "--cli" in sys.argv or "-c" in sys.argv:
        run_cli()
    else:
        run_gui()


if __name__ == "__main__":
    main()
