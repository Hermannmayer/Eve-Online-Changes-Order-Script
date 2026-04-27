# EVE 市场改单脚本

> **EVE Online Market Order Bot** — 自动维护市场挂单的首位竞争，通过 ESI 接口获取数据 + GUI 自动化操作游戏窗口完成改价。

## 📋 功能概述

本脚本常驻后台运行，每隔 N 分钟自动执行以下流程：

1. 通过 ESI 接口读取角色当前所有活跃挂单
2. 查询对应星域的市场行情，判断是否处于最优价（首位）
3. 若不在首位，计算新价格（卖单降价 0.1%，买单加价 0.1%）
4. 通过 **GUI 自动化**（图像识别 + 键鼠模拟）操作游戏窗口完成改价
5. 记录日志，等待下一周期

无需手动盯盘，实现全自动价格维护。

## 🖥 运行原理

```
┌─────────────────────────────────────────────┐
│  ESI 接口 (数据层)                          │
│  ┌──────────┐   ┌──────────────────┐        │
│  │ 角色订单  │   │ 市场价格查询      │        │
│  └────┬─────┘   └──────┬───────────┘        │
│       └────────┬───────┘                     │
│                ▼                             │
│         ┌──────────────┐                     │
│         │  价格决策引擎  │                     │
│         └──────┬───────┘                     │
│                ▼                             │
│  GUI 自动化 (操作层)                         │
│  ┌────────────────────────────────┐          │
│  │ mss (DXGI 截图)                │          │
│  │ opencv 模板匹配                │          │
│  │ pydirectinput 键鼠模拟         │          │
│  │ win32gui 窗口管理              │          │
│  └────────────────────────────────┘          │
│                ▼                             │
│          ✅ 改价完成                         │
└─────────────────────────────────────────────┘
```

## ✅ 功能特性

- **全自动循环**：定时检查所有挂单，自动调价
- **智能价格**：卖单比市场最低价低 0.1%，买单比市场最高价高 0.1%
- **风险保护**：价格波动 ±5% 自动熔断，防止误操作
- **冷却机制**：遵守游戏 5 分钟改价冷却限制
- **双层定位**：图像识别优先，坐标 Fallback 兜底
- **完整日志**：记录每次操作详情，日志每日轮转
- **DXGI 截图**：兼容 DirectX 游戏渲染，拒绝黑屏

## 📦 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | **Windows 10 / 11**（必需，依赖 Win32 API + DXGI） |
| Python | 3.9+ |
| 游戏模式 | 窗口模式或全屏窗口化 |
| 权限 | 建议以**管理员身份运行** |

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <仓库地址>
cd "Eve Online Changes Order Script"
```

### 2. 创建虚拟环境并安装依赖

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
.venv\Scripts\activate

# 安装所有依赖
pip install -r requirements.txt
```

### 3. 配置 ESI 认证

1. 登录 [EVE Developers](https://developers.eveonline.com/) 创建应用
2. 获取 `client_id` 和 `client_secret`
3. 设置回调地址为 `http://localhost:65010/callback/`
4. 添加 Scope: `esi-markets.read_character_orders.v1`

### 4. 修改配置文件

复制并编辑 `config.yaml`：

```yaml
esi:
  client_id: "your_client_id"
  client_secret: "your_client_secret"
  callback_url: "http://localhost:65010/callback/"
  scopes: ["esi-markets.read_character_orders.v1"]

character:
  id: 123456789  # 你的角色 ID

game:
  window_title: "EVE - 角色名"
  window_mode: "windowed"
  resolution:
    width: 1920
    height: 1080

automation:
  interval_minutes: 5
  modify_cooldown_seconds: 300
  max_price_change_percent: 5

# ... 其他配置项见 config.yaml
```

### 5. 准备模板截图

将以下 UI 元素的截图（PNG）放入 `templates/` 目录：

| 截图 | 文件名 | 说明 |
|------|--------|------|
| 搜索框 | `search_box.png` | 市场窗口中的物品搜索输入框 |
| 修改按钮 | `modify_button.png` | "修改订单" 按钮 |
| 价格输入框 | `price_input.png` | 修改价格时的输入框 |
| 确认按钮 | `confirm_button.png` | 修改确认按钮 |
| 市场标签 | `market_tab.png` | 市场窗口标签（用于确认已打开） |

如模板匹配失败，脚本会自动使用配置中的百分比坐标作为 Fallback。

### 6. 运行脚本

```bash
# 确保已激活虚拟环境
.venv\Scripts\activate

# 以管理员身份运行（推荐）
python main.py
```

> ⚠ **注意**：建议以管理员身份运行脚本，以确保鼠标键盘事件能被 DirectX 游戏正确识别。

## 📁 项目结构

```
Eve Online Changes Order Script/
│
├── .venv/                     # Python 虚拟环境（已配置）
├── templates/                 # UI 元素模板截图（需自行准备）
│
├── src/                       # 源代码
│   ├── __init__.py            # 模块初始化
│   ├── auth.py                # ESI SSO 认证模块
│   ├── data_collector.py      # 数据采集模块
│   ├── decision.py            # 价格决策引擎
│   ├── automation.py          # GUI 自动化执行模块
│   ├── risk_manager.py        # 风险管理模块
│   ├── config.py              # 配置加载模块
│   └── main.py                # 主控逻辑（MarketBot 类）
│
├── main.py                    # 启动入口（可直接运行）
├── config.yaml.example        # 配置文件模板
├── .gitignore                 # Git 忽略规则
├── requirements.txt           # Python 依赖清单
├── README.md                  # 本文件
├── EVE 市场改单脚本开发说明书.md
└── EVE 市场改单脚本开发步骤规划.md
```

## ⚙ 配置文件说明

参考 `config.yaml`，主要配置项：

- **ESI 认证**：客户端 ID、密钥、回调地址
- **角色信息**：角色 ID
- **游戏窗口**：窗口标题、分辨率
- **自动化参数**：循环间隔、冷却时间、价格调整百分比
- **价格保护**：最大价格波动阈值
- **模板路径**：模板截图文件位置
- **Fallback 坐标**：基于窗口百分比定位（图像识别失败时使用）

## 🛡 安全机制

### 价格波动保护
- 单次价格变动超过 ±5% 自动终止改价
- 可在配置中调整阈值

### 操作冷却
- 每个订单修改后强制等待 300 秒（游戏硬限制）
- 脚本内部维护冷却计时，超时后才允许再次修改

### 频率限制
- ESI 请求遵循错误率限制，支持 ETag 缓存
- 主循环间隔 ≥ 5 分钟，避免过度操作

### 异常处理
- 图像识别失败 → Fallback 坐标定位 → 跳过该订单
- 游戏窗口丢失 → 等待下个周期
- ESI 请求失败 → 自动重试，连续失败暂停

## 📝 日志

日志文件 `market_bot.log` 格式：

```
时间 | 订单ID | 物品名 | 旧价 | 新价 | 是否首位 | 备注
```

每日自动轮转，保留最近 7 天。

## ⚠ 已知限制

1. **窗口模式必须**：游戏必须为窗口模式或全屏窗口化
2. **分辨率敏感**：模板截图与运行时分辩率一致时匹配率最高
3. **数据延迟**：ESI 数据存在 1~5 分钟缓存延迟
4. **输入接管**：改价期间会短暂接管鼠标键盘，建议无人值守运行
5. **UI 变化**：EVE 的 UI 皮肤/主题变化可能导致模板匹配失败（Fallback 备份生效）

## 🔧 依赖清单

| 包名 | 用途 |
|------|------|
| `requests` | ESI HTTP 请求 |
| `pyyaml` | 配置文件解析 |
| `opencv-python` | 图像模板匹配 |
| `mss` | DXGI 截图（兼容 DirectX） |
| `pydirectinput` | 键鼠模拟（兼容 DirectX 游戏） |
| `pynput` | 输入监听（可选） |
| `pywin32` | Windows 窗口管理（句柄操作） |

## 📄 许可证

本项目仅供学习研究使用。使用前请确保遵守 EVE Online 的用户协议（EULA）。

> **免责声明**：本脚本通过 GUI 自动化模拟人工操作，但使用自动化工具可能违反 EVE Online 的服务条款，使用者需自行承担风险。
