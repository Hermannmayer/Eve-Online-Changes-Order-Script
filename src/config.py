"""
配置模块 - 读取、保存、验证配置文件
支持 GUI 动态读写，默认值管理
"""

import os
import yaml
from typing import Any, Dict, List


# 配置默认值
DEFAULT_CONFIG: Dict[str, Any] = {
    "esi": {
        "client_id": "",
        "client_secret": "",
        "callback_url": "http://localhost:65010/callback/",
        "scopes": ["esi-markets.read_character_orders.v1",
                   "esi-markets.structure_markets.v1"]
    },
    "proxy": {
        "enabled": False,
        "http": "",
        "https": "",
    },
    "character": {
        "id": 0,
        "name": ""
    },
    "game": {
        "window_title": "EVE",
        "window_mode": "windowed",
        "resolution": {
            "width": 1920,
            "height": 1080
        }
    },
    "automation": {
        "interval_minutes": 5,
        "modify_cooldown_seconds": 300,
        "price_adjustment_percent": -0.1,
        "buy_price_adjustment_percent": 0.1,
        "max_price_change_percent": 5.0,
        "retry_attempts": 2
    },
    "templates": {
        "search_box": "templates/search_box.png",
        "modify_button": "templates/modify_button.png",
        "price_input": "templates/price_input.png",
        "confirm_button": "templates/confirm_button.png",
        "market_tab": "templates/market_tab.png"
    },
    "fallback_coordinates": {
        "search_box": {"x": 0.15, "y": 0.85},
        "my_order_row": {"x": 0.50, "y": 0.40},
        "modify_button": {"x": 0.80, "y": 0.50},
        "price_input": {"x": 0.50, "y": 0.55},
        "confirm_button": {"x": 0.50, "y": 0.65},
        "market_tab": {"x": 0.10, "y": 0.05}
    },
    "auth_data": {
        "access_token": "",
        "refresh_token": "",
        "expires_at": 0,
        "character_id": None,
        "character_name": ""
    }
}

# 配置项的元信息：路径 -> (显示名称, 类型, 说明, 最小值, 最大值)
CONFIG_META: Dict[str, tuple] = {
    "esi.client_id": ("Client ID", "text", "EVE Developer 应用的客户端 ID", None, None),
    "esi.client_secret": ("Client Secret", "password", "EVE Developer 应用的客户端密钥", None, None),
    "esi.callback_url": ("回调地址", "text", "OAuth 回调 URL（需与 EVE Developer 设置一致）", None, None),
    "esi.scopes": ("授权权限", "text", "ESI 授权范围（空格分隔）", None, None),
    "proxy.enabled": ("启用代理", "bool", "通过代理连接 EVE SSO（中国大陆用户建议开启）", None, None),
    "proxy.http": ("HTTP 代理", "text", "HTTP 代理地址，如 http://127.0.0.1:7890", None, None),
    "proxy.https": ("HTTPS 代理", "text", "HTTPS 代理地址，如 http://127.0.0.1:7890", None, None),
    "character.id": ("角色 ID", "number", "你的 EVE 角色 ID（整数）", 1, 9999999999),
    "character.name": ("角色名称", "text", "你的 EVE 角色名（选填，用于显示）", None, None),
    "game.window_title": ("游戏窗口标题", "text", "用于查找 EVE 游戏窗口", None, None),
    "game.window_mode": ("窗口模式", "select", "游戏窗口模式", None, None),
    "game.resolution.width": ("窗口宽度", "number", "游戏窗口像素宽度", 800, 7680),
    "game.resolution.height": ("窗口高度", "number", "游戏窗口像素高度", 600, 4320),
    "automation.interval_minutes": ("检查间隔", "number", "每次市场检查的时间间隔（分钟）", 1, 60),
    "automation.modify_cooldown_seconds": ("改价冷却", "number", "修改订单后的冷却时间（秒）", 60, 3600),
    "automation.price_adjustment_percent": ("卖单价调整%", "float", "卖单价格调整百分比（负数降低，正数升高）", -50.0, 50.0),
    "automation.buy_price_adjustment_percent": ("买单调整%", "float", "买单价格调整百分比（负数降低，正数升高）", -50.0, 50.0),
    "automation.max_price_change_percent": ("价格波动阈值%", "float", "单次价格变动最大允许百分比", 0.1, 100.0),
    "automation.retry_attempts": ("重试次数", "number", "操作失败时的最大重试次数", 0, 10),
    "templates.search_box": ("搜索框模板", "file", "市场物品搜索框的模板图片路径", None, None),
    "templates.modify_button": ("修改按钮模板", "file", "修改订单按钮的模板图片路径", None, None),
    "templates.price_input": ("价格输入框模板", "file", "价格输入框的模板图片路径", None, None),
    "templates.confirm_button": ("确认按钮模板", "file", "确认修改按钮的模板图片路径", None, None),
    "templates.market_tab": ("市场标签模板", "file", "市场窗口标签的模板图片路径", None, None),
    "fallback_coordinates.search_box.x": ("搜索框 X%", "float", "搜索框横向百分比位置（0~1）", 0.0, 1.0),
    "fallback_coordinates.search_box.y": ("搜索框 Y%", "float", "搜索框纵向百分比位置（0~1）", 0.0, 1.0),
    "fallback_coordinates.my_order_row.x": ("订单行 X%", "float", "订单列表行横向百分比位置（0~1）", 0.0, 1.0),
    "fallback_coordinates.my_order_row.y": ("订单行 Y%", "float", "订单列表行纵向百分比位置（0~1）", 0.0, 1.0),
    "fallback_coordinates.modify_button.x": ("修改按钮 X%", "float", "修改按钮横向百分比位置（0~1）", 0.0, 1.0),
    "fallback_coordinates.modify_button.y": ("修改按钮 Y%", "float", "修改按钮纵向百分比位置（0~1）", 0.0, 1.0),
    "fallback_coordinates.price_input.x": ("价格输入框 X%", "float", "价格输入框横向百分比位置（0~1）", 0.0, 1.0),
    "fallback_coordinates.price_input.y": ("价格输入框 Y%", "float", "价格输入框纵向百分比位置（0~1）", 0.0, 1.0),
    "fallback_coordinates.confirm_button.x": ("确认按钮 X%", "float", "确认按钮横向百分比位置（0~1）", 0.0, 1.0),
    "fallback_coordinates.confirm_button.y": ("确认按钮 Y%", "float", "确认按钮纵向百分比位置（0~1）", 0.0, 1.0),
    "fallback_coordinates.market_tab.x": ("市场标签 X%", "float", "市场标签横向百分比位置（0~1）", 0.0, 1.0),
    "fallback_coordinates.market_tab.y": ("市场标签 Y%", "float", "市场标签纵向百分比位置（0~1）", 0.0, 1.0),
}


def _deep_get(d: dict, path: str, default=None):
    """通过点号路径获取嵌套字典的值"""
    keys = path.split(".")
    value = d
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return default
        if value is None:
            return default
    return value


def _deep_set(d: dict, path: str, value):
    """通过点号路径设置嵌套字典的值"""
    keys = path.split(".")
    current = d
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def _deep_delete(d: dict, path: str):
    """通过点号路径删除嵌套字典的值"""
    keys = path.split(".")
    current = d
    for key in keys[:-1]:
        if key not in current:
            return
        current = current[key]
    current.pop(keys[-1], None)


class Config:
    """加载、管理和保存配置文件"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self._data: Dict[str, Any] = self._deep_copy(DEFAULT_CONFIG)

    def load(self) -> bool:
        """加载 YAML 配置文件"""
        if not os.path.exists(self.config_path):
            return False
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
            if loaded:
                self._merge(loaded)
            return True
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return False

    def save(self) -> bool:
        """保存配置到 YAML 文件"""
        try:
            # 导出配置（排除内部字段）
            export_data = self._export()
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(export_data, f, default_flow_style=False, allow_unicode=True,
                          sort_keys=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False

    def _merge(self, loaded: dict, base: dict = None):
        """递归合并加载的配置到当前配置"""
        if base is None:
            base = self._data
        for key, value in loaded.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge(value, base[key])
            else:
                base[key] = value

    def _export(self) -> dict:
        """导出配置用于保存（排除内部字段）"""
        export = {}
        for key, value in self._data.items():
            if key == "auth_data":
                # 只保存 refresh_token 和 character 信息
                export[key] = {
                    "refresh_token": value.get("refresh_token", ""),
                    "expires_at": value.get("expires_at", 0),
                    "character_id": value.get("character_id"),
                    "character_name": value.get("character_name", "")
                }
            else:
                export[key] = value
        return export

    def get(self, key: str, default=None) -> Any:
        """获取配置项，支持点号分隔的嵌套访问"""
        return _deep_get(self._data, key, default)

    def set(self, key: str, value):
        """设置配置项，支持点号分隔的嵌套访问"""
        _deep_set(self._data, key, value)

    def delete(self, key: str):
        """删除配置项"""
        _deep_delete(self._data, key)

    def get_all(self) -> dict:
        """获取完整配置字典"""
        return self._data

    def validate(self) -> list[str]:
        """验证配置完整性，返回缺失项列表"""
        errors = []
        # ESI 配置验证
        if not self.get("esi.client_id"):
            errors.append("esi.client_id - Client ID 未配置")
        if not self.get("esi.client_secret"):
            errors.append("esi.client_secret - Client Secret 未配置")

        # 角色验证
        char_id = self.get("character.id")
        if char_id is None or char_id == 0:
            errors.append("character.id - 角色 ID 未配置")

        # 游戏窗口验证
        if not self.get("game.window_title"):
            errors.append("game.window_title - 窗口标题未配置")

        # 自动化参数验证
        interval = self.get("automation.interval_minutes")
        if interval is None or interval < 1:
            errors.append("automation.interval_minutes - 检查间隔应 ≥ 1 分钟")

        # 代理验证
        proxy_enabled = self.get("proxy.enabled")
        if proxy_enabled:
            http_proxy = self.get("proxy.http", "")
            https_proxy = self.get("proxy.https", "")
            if not http_proxy and not https_proxy:
                errors.append("proxy - 已启用代理但未配置代理地址")

        return errors

    def get_meta(self, key: str) -> tuple:
        """获取配置项的元信息 (label, type, desc, min, max)"""
        meta = CONFIG_META.get(key)
        if meta:
            return meta
        # 自动推断类型
        value = self.get(key)
        if isinstance(value, bool):
            return (key, "bool", "", None, None)
        elif isinstance(value, int):
            return (key, "number", "", None, None)
        elif isinstance(value, float):
            return (key, "float", "", None, None)
        else:
            return (key, "text", "", None, None)

    def get_all_keys(self) -> List[str]:
        """获取所有可配置的键列表"""
        return list(CONFIG_META.keys())

    def get_proxy_dict(self) -> Dict[str, str]:
        """获取代理配置字典（用于 requests）"""
        if not self.get("proxy.enabled"):
            return {}
        proxies = {}
        http = self.get("proxy.http", "")
        https = self.get("proxy.https", "")
        if http:
            proxies["http"] = http
        if https:
            proxies["https"] = https
        return proxies

    @staticmethod
    def _deep_copy(d: dict) -> dict:
        """深拷贝字典"""
        import copy
        return copy.deepcopy(d)
