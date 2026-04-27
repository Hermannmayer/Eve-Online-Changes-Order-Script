根据《EVE 市场改单脚本开发说明书》，我梳理了以下详细的开发步骤规划。该规划遵循**模块化、迭代式**开发原则，每个步骤都有明确的产出物，可在完成后进行独立测试。

---

## EVE 市场改单脚本 - 开发步骤规划

### 阶段一：项目初始化与环境搭建

**步骤 1 - 项目骨架与虚拟环境**
- 创建项目目录 `eve_market_bot/`
- 初始化 Python 虚拟环境（`.venv`）
- 创建 `requirements.txt`，列出所有依赖：
  ```
  requests>=2.31.0
  pyyaml>=6.0
  opencv-python>=4.8.0
  mss>=9.0.0
  pydirectinput>=1.0.4
  pynput>=1.7.6
  pywin32>=306
  ```
  > **变更说明**：使用 `mss`（DXGI 截图）替代 `pyautogui.screenshot()`（GDI 截图），解决 DirectX 游戏窗口截图黑屏问题；使用 `pydirectinput` 替代 `pyautogui` 的键盘鼠标模拟，提升 DirectX 游戏输入兼容性；移除 `keyboard`（需管理员权限），统一用 `pydirectinput` + `pynput` 替代。
- 创建目录结构：
  ```
  eve_market_bot/
  ├── src/
  │   ├── __init__.py
  │   ├── auth.py          # 认证模块
  │   ├── data_fetcher.py  # 数据采集模块
  │   ├── decision.py      # 决策模块
  │   ├── executor.py      # GUI自动化执行模块
  │   ├── vision.py        # 图像识别模块（新增，封装 mss 截图 + OpenCV 匹配）
  │   ├── risk.py          # 风险管理模块
  │   ├── config.py        # 配置模块
  │   ├── logger.py        # 日志模块
  │   └── main.py          # 主循环入口
  ├── templates/           # UI模板截图存放目录
  ├── config.yaml          # 用户配置文件
  ├── requirements.txt
  └── README.md
  ```
  > **结构调整**：新增 `vision.py`，将截图和图像识别独立为单独模块，与窗口管理（`WindowManager` 放在 `executor.py` 中）分离，职责更清晰。

**产出物：** 可运行的空项目结构，依赖一键安装

---

### 阶段二：基础设施模块开发

**步骤 2 - 配置加载模块 (`config.py`)**
- 实现 YAML 配置文件读取
- 提供 `load_config()` 函数，返回配置对象
- 配置项验证：必需字段检查，类型转换
- 提供默认值兜底（包括新增的 fallback_coordinates 默认值）

**步骤 3 - 日志模块 (`logger.py`)**
- 实现 `setup_logger()` 函数
- 日志格式：`时间 | 级别 | 消息`
- 文件输出 `market_bot.log` + 控制台输出
- 每日轮转，保留最近 7 天
- 提供便捷的 `log_order_action()` 函数记录订单操作

**步骤 4 - 风险管理模块 (`risk.py`)**
- `PriceGuardian` 类：价格波动检查（±5% 阈值）
- `CooldownTracker` 类：订单冷却跟踪（dict 维护最后修改时间）
- `ErrorCounter` 类：连续失败计数，暂停机制
- `retry_decorator`：通用重试装饰器

---

### 阶段三：核心业务模块开发

**步骤 5 - ESI 认证模块 (`auth.py`)**
- 实现 EsiAuth 类：
  - SSO 授权流程：启动本地 HTTP server（端口 65010）接收回调
  - Token 管理：Access Token 自动刷新（使用 Refresh Token）
  - Token 持久化到本地文件（避免每次重新登录）
- 提供 `get_headers()` 方法返回携带 `Authorization` 的请求头

**步骤 6 - ESI 数据采集模块 (`data_fetcher.py`)**
- 实现 `DataFetcher` 类：
  - `get_my_orders(character_id)` → 获取角色所有活跃订单
  - `get_market_orders(region_id, type_id, order_type)` → 获取市场订单
  - `resolve_region_id(location_id)` → 从 location_id 解析 region_id
  - ESI 请求错误处理：状态码检查、重试、ETag 缓存支持
- 请求频率控制：使用 `time.sleep` 避免被限流

**步骤 7 - 决策模块 (`decision.py`)**
- 实现 `OrderAnalyzer` 类：
  - `is_already_first(order, market_orders, order_type)` → 判断是否首位
  - `calculate_new_price(order, market_best_price, order_type)` → 计算新价格
    - 卖单：最优价 × (1 - 0.1%)，向下取整到 0.01
    - 买单：最优价 × (1 + 0.1%)，向上取整到 0.01
  - `build_modify_queue(my_orders, market_data)` → 生成待改价队列

---

### 阶段四：GUI 自动化模块开发（最复杂的部分）

**步骤 8 - 窗口管理 (`executor.py` 中包含 WindowManager)**
- 编写 `WindowManager` 类：
  - `find_game_window(window_title)` → 通过 `win32gui` 查找窗口句柄
  - `activate_window()` → `SetForegroundWindow` 置顶
  - `get_window_rect()` → 获取窗口位置与尺寸（left, top, width, height）
  - `is_window_active()` → 判断窗口是否存在且可操作
- **手动操作**：在游戏中截取以下 UI 元素的模板截图（PNG），放入 `templates/` 目录：
  - `search_box.png`（搜索框）
  - `modify_button.png`（修改订单按钮）
  - `price_input.png`（价格输入框）
  - `confirm_button.png`（确认按钮）
  - `market_tab.png`（市场标签页）

**步骤 9 - 图像识别模块 (`vision.py`) — 使用 mss + OpenCV**
- 实现 `VisionHelper` 类：
  - `capture_window_region(window_rect)` → 使用 **`mss`** 库截图游戏窗口区域
    - 通过 DXGI API 从 GPU 缓冲区直接抓取，避免 DirectX 游戏黑屏问题
    - 输出为 PIL.Image 对象，再转换为 OpenCV 格式处理
  - `locate_template(template_path, screenshot, confidence=0.8)` → 使用 `cv2.matchTemplate` 在截图中匹配 UI 元素
    - 支持多尺度匹配？当前版本暂不支持，要求运行时分辨率与截图时一致
  - `wait_for_element(template_path, window_rect, timeout=3)` → 不断截图并尝试匹配，直到超时或成功
  - **坐标定位 Fallback 机制**：
    - `locate_by_fallback(element_name, window_rect)` → 根据配置文件中的百分比坐标计算绝对像素坐标
    - 当 `locate_template()` 匹配失败时自动调用此方法作为兜底
    - 计算公式：`abs_x = window_rect.left + window_rect.width * percent_x`，`abs_y` 同理
    - 返回格式同模板匹配：`(x, y, w, h)`（w/h 使用默认值 10）
  - `locate_element(template_path, element_name, window_rect, confidence=0.8)` → 组合方法：先模板匹配，失败则 Fallback
- 识别结果格式：`(x, y, w, h)` 或 `None`

**步骤 10 - GUI 自动化执行器 (`executor.py` — 使用 pydirectinput)**
- 实现 `MarketExecutor` 类，封装完整的改价动作序列：
  - `__init__(self, vision_helper, window_manager, config)` → 注入依赖
  - `open_market_window()` → 打开市场窗口（点击市场标签/快捷键）
  - `search_item(item_name)` → 输入物品名称搜索（点击搜索框 → Ctrl+A 清空 → 输入物品名 → 回车）
  - `find_my_order()` → 在订单列表中找到自己的挂单（模板匹配/坐标 Fallback）
  - `click_modify_button()` → 点击修改订单按钮
  - `input_new_price(price)` → 清空并输入新价格（Ctrl+A → `pydirectinput.write(str(price))` → 回车）
  - `confirm_modification()` → 点击确认按钮
  - `execute_order_modification(order, new_price)` → 执行完整改价流程
- 使用 **`pydirectinput`** 进行点击和键盘操作（替代 `pyautogui`）：
  - `pydirectinput.moveTo(x, y)` → 移动鼠标
  - `pydirectinput.click()` → 点击
  - `pydirectinput.keyDown('ctrl')` / `keyUp('ctrl')` → 组合键
  - `pydirectinput.write(text)` → 输入文字
  - `pydirectinput.press('enter')` → 按回车
- 每步之间固定延时 0.2~0.5s（`time.sleep()`）
- 异常处理：
  - 图像识别失败 → 自动调用坐标 Fallback
  - 坐标 Fallback 也失败 → 重试 2 次，失败则跳过该订单并记录日志
  - 窗口丢失 → 停止当前轮次

---

### 阶段五：主循环集成

**步骤 11 - 主循环 (`main.py`)**
- 实现 `main()` 函数，按流程文档执行：
  1. 加载配置
  2. 初始化所有模块（Config → Logger → EsiAuth → DataFetcher → OrderAnalyzer → PriceGuardian → CooldownTracker → WindowManager → VisionHelper → MarketExecutor）
  3. 进入无限循环：
     - 检查游戏窗口是否存在
     - ESI 获取我的订单
     - 每个订单获取市场数据 → 决策 → 风险检查 → 加入队列
     - 激活窗口，执行 GUI 改价
     - 释放焦点，记录日志，休眠
- 支持 `Ctrl+C` 优雅退出（`signal` 或 `try/except KeyboardInterrupt`）
- 本轮统计输出：处理订单数、成功数、失败数、跳过数

**步骤 12 - 启动脚本**
- 创建 `run.bat`（Windows 一键启动，建议以管理员身份运行）：
  ```bat
  @echo off
  title EVE Market Bot
  cd /d %~dp0
  call .venv\Scripts\activate
  python src\main.py
  pause
  ```
- 创建 `run_as_admin.bat`（提权运行辅助脚本）：
  ```bat
  @echo off
  title EVE Market Bot
  cd /d %~dp0
  call .venv\Scripts\activate
  python src\main.py
  pause
  ```

---

### 阶段六：测试与文档

**步骤 13 - 各模块单元测试**
- 为以下模块编写测试：
  - `test_config.py`：配置加载与校验
  - `test_decision.py`：首位判断、价格计算逻辑（可离线测试）
  - `test_risk.py`：冷却跟踪、价格波动检测
  - `test_vision.py`：截图与模板匹配（需提供测试截图）
- 使用 `unittest` 或 `pytest`

**步骤 14 - 集成测试与微调**
- 实际运行脚本，观察行为日志
- 调整 GUI 操作的延时参数和识别置信度
- 验证 ESI 认证流程完整可用
- 测试 mss 截图兼容性：确认在不同 EVE UI 设置下是否都能正确捕获画面
- 测试 pydirectinput 输入兼容性：确认 EVE 窗口是否能正确响应模拟输入

**步骤 15 - 编写 README 使用文档**
- 运行环境要求（Windows 10/11, Python 3.9+）
- 安装步骤（pip install -r requirements.txt）
- **管理员权限说明**（pydirectinput 需要以管理员身份运行）
- 配置说明（如何获取 client_id、角色 ID 等）
- 截图模板生成指南（如何使用 mss 截取 UI 模板）
- 坐标 Fallback 配置说明（如何设置百分比坐标）
- 启动与停止方法
- 故障排除 FAQ

---

## 开发优先级建议

| 优先级 | 步骤 | 原因 |
|--------|------|------|
| 🔴 P0 | 步骤 1-3（项目骨架、配置、日志） | 所有模块的基础 |
| 🔴 P0 | 步骤 5-6（ESI 认证与数据采集） | 核心数据源，决定脚本是否能获取数据 |
| 🟡 P1 | 步骤 7（决策模块） | 业务核心逻辑，可独立测试 |
| 🟡 P1 | 步骤 4（风险管理） | 安全保障，防止亏损 |
| 🟠 P2 | 步骤 8-10（GUI 自动化） | **最复杂的部分**，包含 mss 截图 + pydirectinput 输入 + 坐标 Fallback |
| 🟠 P2 | 步骤 11（主循环集成） | 串联所有模块 |
| 🟢 P3 | 步骤 12-15（启动脚本、测试、文档） | 完善和交付 |

---

## 技术栈变更总结

| 变更项 | 旧方案 | 新方案 | 原因 |
|--------|--------|--------|------|
| 截图引擎 | `pyautogui.screenshot()`（GDI） | `mss`（DXGI） | DirectX 游戏窗口 GDI 截图可能黑屏 |
| 鼠标/键盘输入 | `pyautogui` | `pydirectinput` | DirectX 游戏输入兼容性更好 |
| 键盘监听 | `keyboard` | `pynput`（已存在） | 减少依赖项，避免管理员权限冲突 |
| 图像定位 | 纯模板匹配 | 模板匹配 + 坐标百分比 Fallback | 抗分辨率/UI 变化能力更强 |
| 模块结构 | 无独立 vision 模块 | 新增 `vision.py` | 职责分离，截图和识别逻辑独立 |
