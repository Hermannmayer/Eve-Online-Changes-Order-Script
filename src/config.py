"""
配置模块 - 读取、保存、验证配置文件
简化版：去掉 ESI 认证配置，添加监控物品配置
"""

import os
import yaml
from typing import Any, Dict, List


DEFAULT_CONFIG: Dict[str, Any] = {
    "esi": {
        "base_url": "https://esi.evetech.net",
        "user_agent": "EVE-Price-Monitor/1.0",
    },
    "proxy": {
        "enabled": False,
        "http": "",
        "https": "",
    },
    "monitor": {
        "region_id": 10000002,
        "update_interval_minutes": 5,
        "items": [
            {"type_id": 34, "name": "Tritanium"},
            {"type_id": 35, "name": "Pyerite"},
        ],
    },
}


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
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(self._data, f, default_flow_style=False, allow_unicode=True,
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

    def get(self, key: str, default=None) -> Any:
        return _deep_get(self._data, key, default)

    def set(self, key: str, value):
        _deep_set(self._data, key, value)

    def get_all(self) -> dict:
        return self._data

    def validate(self) -> list[str]:
        errors = []
        if not self.get("esi.base_url"):
            errors.append("esi.base_url - API 地址未配置")
        items = self.get("monitor.items", [])
        if not items:
            errors.append("monitor.items - 未添加监控物品")
        proxy_enabled = self.get("proxy.enabled")
        if proxy_enabled:
            if not self.get("proxy.http", "") and not self.get("proxy.https", ""):
                errors.append("proxy - 已启用代理但未配置代理地址")
        return errors

    def get_proxy_dict(self) -> Dict[str, str]:
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
        import copy
        return copy.deepcopy(d)


def _deep_get(d: dict, path: str, default=None):
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
    keys = path.split(".")
    current = d
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value
