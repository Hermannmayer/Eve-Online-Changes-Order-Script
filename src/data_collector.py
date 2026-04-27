"""
数据采集模块 - 通过 ESI 获取角色挂单及市场价格
"""

from typing import Optional


class DataCollector:
    """获取角色当前挂单及对应物品的市场价格"""

    def __init__(self, auth):
        self.auth = auth
        self._esi_url = "https://esi.evetech.net"

    def get_character_orders(self, character_id: int) -> list[dict]:
        """获取角色当前所有活跃挂单"""
        pass

    def get_market_orders(self, region_id: int, type_id: int, order_type: str) -> list[dict]:
        """获取指定星域内某物品的当前市场订单"""
        pass

    def get_region_id(self, location_id: int) -> int:
        """根据 location_id 解析所在星域 ID"""
        pass

    def get_type_name(self, type_id: int) -> str:
        """获取物品名称"""
        pass
