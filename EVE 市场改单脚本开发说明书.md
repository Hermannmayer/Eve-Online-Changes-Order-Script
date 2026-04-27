# EVE 市场改单脚本开发说明书

## 1. 项目概述

### 1.1 目标
开发一个 Python 脚本，**后台自动化维护 EVE Online 市场挂单的首位竞争**。  
脚本通过 ESI 接口读取角色订单和市场行情，判断是否需要调价；若需要，则通过 **GUI 自动化** 直接操作游戏窗口，模拟人工完成"修改订单价格"的操作。

### 1.2 运行模式
- 游戏必须以**窗口模式**运行（包括"全屏窗口化"），分辨率固定。
- 脚本常驻后台，每隔 N 分钟执行一次检查与改价周期。
- 自动化操作期间会**短暂接管鼠标和键盘**，聚焦游戏窗口，操作完成后释放。

---

## 2. 核心功能模块划分

| 模块 | 职责 |
|------|------|
| 认证模块 | 处理 ESI SSO 登录，管理 Access Token 与 Refresh Token |
| 数据采集模块 | 通过 ESI 获取角色当前挂单及对应物品的市场价格 |
| 决策模块 | 判断每个订单是否为首位，计算新价格，风险校验 |
| 自动化执行模块 | 操作游戏窗口，完成改价动作（图像识别 + 键鼠模拟） |
| 风险管理模块 | 价格波动保护、操作频率限制、错误处理与日志 |
| 配置模块 | 读取和加载用户配置文件（参数、路径、阈值等） |

---

## 3. 行为逻辑流程

```
循环开始（间隔可配置，默认 5 分钟）：
  │
  ├─ 1. 检查游戏窗口是否存在
  │     否 → 记录日志，等待下次循环
  │     是 → 继续
  │
  ├─ 2. 通过 ESI 拉取角色所有活跃订单
  │
  ├─ 3. 对每个订单：
  │     a. 根据 location_id 解析所在星域 (region_id)
  │     b. 获取该星域下、同物品、同买卖方向的当前市场订单
  │     c. 排除自身 order_id，确定市场最优价（卖单最低价 / 买单最高价）
  │     d. 判断自己是否已在首位：
  │         - 卖单：当前订单价格 ≤ 市场最低价（允许同价）
  │         - 买单：当前订单价格 ≥ 市场最高价
  │     e. 若在首位 → 跳过
  │     f. 若不在首位 → 计算新价格：
  │         卖单新价 = 市场最低价 × (1 - 0.1%)，向下取整到 0.01 ISK
  │         买单新价 = 市场最高价 × (1 + 0.1%)，向上取整到 0.01 ISK
  │     g. 风险检查：
  │         - 涨跌幅是否超过 5%？→ 是则记录并终止该订单改价
  │         - 距离上次修改是否超过冷却时间（默认 5 分钟）？→ 否则跳过
  │     h. 若通过检查，将订单加入"待改价队列"
  │
  ├─ 4. 激活游戏窗口（置顶），开始 GUI 自动化：
  │     对队列中每个订单：
  │        a. 打开市场窗口（若未打开）
  │        b. 搜索物品名称或 type_id
  │        c. 在订单列表中找到自己的订单（通过文本/图标识）
  │        d. 右键或点"修改订单"按钮
  │        e. 清空价格输入框，输入计算好的新价格
  │        f. 点击"确认"
  │        g. 记录操作日志
  │        h. 恢复游戏窗口原始状态（如关闭搜索等）
  │
  └─ 5. 释放游戏窗口焦点，记录本轮统计，休眠等待下一周期
```

---

## 4. ESI 接口清单

| 接口 | 用途 | 需要权限 |
|------|------|----------|
| `GET /v2/characters/{character_id}/orders/` | 获取角色当前挂单 | `esi-markets.read_character_orders.v1` |
| `GET /v1/markets/{region_id}/orders/` | 获取星域内指定物品/方向的订单 | 不需要 |
| `GET /v2/universe/names/` | ID 转名称（可选） | 不需要 |
| SSO 认证 | 获取 token | 需提前注册应用，回调获取 |

> 注意：**不存在通过 ESI 修改价格的接口**，因此所有改价操作必须走 GUI 自动化。

---

## 5. GUI 自动化方案

### 5.1 窗口操作
- 使用 `win32gui` 查找 EVE 客户端窗口句柄，获取位置与大小。
- 必要时将窗口置顶 (`SetForegroundWindow`)，操作完成后可解除置顶。

### 5.2 截图与图像识别方案（重要：DirectX 兼容性问题）

#### 5.2.1 背景说明
EVE Online 使用 **DirectX 11/12** 硬件加速渲染。传统的 GDI 截图方案（如 `pyautogui.screenshot()` 底层调用的 `PIL.ImageGrab.grab()`）对于 DirectX 游戏窗口**可能只能捕获到黑色画面**，导致模板匹配完全失效。

因此，本项目采用 **DXGI（DirectX Graphics Infrastructure）截图方案** 替代传统 GDI 截图。

#### 5.2.2 截图引擎：mss（Multi-Screen Shot）
- 使用 `mss` 库，通过 **DXGI API** 直接从 GPU 缓冲区抓取画面。
- 可以正确捕获 DirectX 游戏窗口的画面内容。
- 使用方式：指定要截取的屏幕区域（可仅截取游戏窗口区域，提高性能）。
- 输出格式为 `PIL.Image` 对象，可直接传递给 OpenCV 处理。

#### 5.2.3 模板匹配
- **模板截图准备**：首次使用时，手动截取以下 UI 元素的模板截图（PNG），放入 `templates/` 目录：
  - 市场窗口图标/标签（确认市场已打开）
  - 搜索输入框
  - "修改订单"按钮
  - 价格输入框
  - "确认"按钮
  - 订单列表中自己订单的高亮标识（如角色名称或特定颜色条）
- 使用 `opencv-python` 的 `cv2.matchTemplate` 匹配位置，置信度阈值可通过配置调整（默认 0.8）。
- 匹配结果格式：`(x, y, w, h)` 表示元素在窗口中的矩形区域。

#### 5.2.4 坐标定位 Fallback 机制
由于模板匹配对分辨率/UI 主题变化敏感，本方案设计**双层定位策略**：

1. **第一层（优先）**：图像模板匹配，返回精确像素坐标。
2. **第二层（兜底）**：在配置文件中预定义每个 UI 元素相对于游戏窗口的**百分比坐标**。
   - 例如：搜索框在窗口 `(15%, 85%)` 位置。
   - 当模板匹配失败时，根据窗口当前尺寸和预设百分比计算出绝对坐标。
   - 这种方案对不同分辨率有较好的适应性。

### 5.3 键盘鼠标模拟：pydirectinput

#### 5.3.1 方案选型理由
- 直接使用标准 `pyautogui` 的输入模拟在某些 DirectX 游戏（包括 EVE Online）中可能被忽略。
- **`pydirectinput`** 是 `pyautogui` 的 DirectX 游戏专用分支，通过 **SendInput API** 发送输入事件，兼容性更好。
- API 与 `pyautogui` 高度一致（`click()`, `moveTo()`, `keyDown()`, `keyUp()`, `write()` 等），迁移成本低。

#### 5.3.2 操作细节
- 输入价格时：先 `Ctrl+A` 全选清空，再 `write(str(new_price))` 键入新价格，最后 `press('enter')` 或点击确认按钮。
- 每步操作之间加入短延时（0.2~0.5 秒），防止游戏响应不及时。

### 5.4 等待与验证
- 弹出确认对话框时，等待不超过 3 秒，检测确认按钮出现（模板匹配）。
- 改价后无直接 API 验证，可短暂等待后通过重新截图确认价格是否更新（可选）。

---

## 6. 风险控制与安全机制

### 6.1 价格波动保护
- 每次计算新价格时，对比旧价格，**变动幅度超过 ±5% 则停止改价**，并在控制台打印警告。
- 可扩展：记录异常物品，可配置黑名单。

### 6.2 操作冷却
- 同一 `order_id` 修改后，必须等待 **≥ 300 秒（5分钟）** 才能再次修改（游戏硬限制）。
- 脚本内部维护一个 `dict[order_id] = last_modified_time`，超时后才允许再次修改。

### 6.3 频率限制
- 全局循环间隔 ≥ 5 分钟，避免过度调用 ESI 或高频操作游戏。
- ESI 请求必须遵守错误率限制（使用 `ETag` 缓存，减少不必要的请求）。

### 6.4 异常处理
- 图像识别失败：先尝试坐标定位 Fallback，若仍失败则跳过该订单，记录错误日志。
- 游戏窗口丢失：停止当前轮次，等待下周期。
- ESI 请求失败：重试机制，连续失败暂停后续操作。

### 6.5 日志
- 所有操作输出到 `market_bot.log`，格式：`时间 | 订单ID | 物品名 | 旧价 | 新价 | 是否首位 | 原因/备注`。
- 每日轮转日志文件，保留最近 7 天。

---

## 7. 配置文件结构

使用 `config.yaml`，包含以下项：

```yaml
esi:
  client_id: "your_client_id"
  client_secret: "your_client_secret"
  callback_url: "http://localhost:65010/callback/"
  scopes: ["esi-markets.read_character_orders.v1"]

character:
  id: 123456789  # 角色ID

game:
  window_title: "EVE - 角色名"  # 用于查找窗口
  window_mode: "windowed"
  resolution:
    width: 1920
    height: 1080

automation:
  interval_minutes: 5           # 主循环间隔
  modify_cooldown_seconds: 300  # 单订单修改冷却（游戏硬限制 5 分钟）
  price_adjustment_percent: -0.1   # 卖单价调整百分比（负数表示降低）
  buy_price_adjustment_percent: 0.1  # 买单调整百分比
  max_price_change_percent: 5    # 价格波动风险阈值
  retry_attempts: 2              # 图像识别重试次数

templates:
  search_box: "templates/search_box.png"
  modify_button: "templates/modify_button.png"
  price_input: "templates/price_input.png"
  confirm_button: "templates/confirm_button.png"
  market_tab: "templates/market_tab.png"

# 坐标定位 Fallback（基于游戏窗口的百分比位置）
# 用于模板匹配失败时的兜底方案
# 格式：{x_percent, y_percent} 范围 0.0~1.0
fallback_coordinates:
  search_box:              {x: 0.15, y: 0.85}
  my_order_row:            {x: 0.50, y: 0.40}
  modify_button:           {x: 0.80, y: 0.50}
  price_input:             {x: 0.50, y: 0.55}
  confirm_button:          {x: 0.50, y: 0.65}
  market_tab:              {x: 0.10, y: 0.05}
```

---

## 8. 运行环境要求

### 8.1 系统要求
- **操作系统**：Windows 10 / 11（必需，依赖 Win32 API 和 DXGI）
- **Python**：3.9+
- **游戏设置**：窗口模式运行（包括"全屏窗口化"），建议固定分辨率（如 1920×1080）

### 8.2 安装依赖
```bash
pip install requests>=2.31.0
pip install pyyaml>=6.0
pip install opencv-python>=4.8.0
pip install mss>=9.0.0
pip install pydirectinput>=1.0.4
pip install pynput>=1.7.6
pip install pywin32>=306
```

合并安装：
```bash
pip install requests pyyaml opencv-python mss pydirectinput pynput pywin32
```

### 8.3 管理员权限说明
- `pydirectinput` 在 Windows 上**建议以管理员权限运行**，以确保鼠标/键盘输入事件能够被 DirectX 应用程序正确识别。
- 可通过右键 `命令提示符` → `以管理员身份运行`，或创建快捷方式勾选"以管理员身份运行"。
- `mss`（DXGI 截图）无需额外权限。

### 8.4 已知限制
- 游戏必须为窗口模式，且分辨率固定（模板截图与运行时分辨率一致时匹配率最高）。
- EVE Online 的 UI 主题/皮肤变化可能导致模板匹配失败（此时 fallback 坐标定位生效）。
- ESI 数据存在缓存延迟（通常 1~5 分钟），改价决策基于非实时数据。
- 脚本运行期间会短暂接管鼠标键盘，建议在无人值守时运行。

---
