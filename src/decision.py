"""
决策模块 - 判断订单是否为首位，计算新价格
"""

from typing import Optional


class DecisionEngine:
    """判断每个订单是否为首位，计算新价格"""

    def __init__(self, sell_adjust_percent: float = -0.1,
                 buy_adjust_percent: float = 0.1,
                 max_change_percent: float = 5.0):
        self.sell_adjust_percent = sell_adjust_percent
        self.buy_adjust_percent = buy_adjust_percent
        self.max_change_percent = max_change_percent

    def is_first_in_queue(self, order: dict, market_orders: list[dict]) -> bool:
        """判断订单是否已在首位"""
        pass

    def calculate_new_price(self, order: dict, market_orders: list[dict]) -> Optional[float]:
        """计算新价格"""
        pass

    def risk_check(self, old_price: float, new_price: float) -> bool:
        """风险检查：价格波动是否超过阈值"""
        pass
