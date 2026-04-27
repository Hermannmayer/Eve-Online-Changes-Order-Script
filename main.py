"""
EVE Online 市场改单脚本 - 启动入口

使用方法：
    python main.py

请确保 config.yaml 已正确配置（可参考 config.yaml.example）。
"""

import sys
import os

# 将项目根目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import main

if __name__ == "__main__":
    main()
