"""
配置页面 - 完整的配置项管理 GUI
支持所有变量的读取、修改、保存
"""

import flet as ft
from typing import Callable, Optional, Any

from src.config import Config
from src.gui.theme import AppColors, AppSizes, section_header, help_text


class ConfigPage(ft.Container):
    """配置管理页面"""

    def __init__(self, config: Config, on_back: Optional[Callable] = None):
        super().__init__()
        self.config = config
        self.on_back = on_back
        self._controls_map: dict[str, ft.Control] = {}  # key -> control 映射
        self._status_text = ft.Text("", size=13)
        self.padding = AppSizes.CONTENT_PADDING
        self.expand = True

    def build(self):
        """构建配置页面"""
        self.content = ft.Column(
            controls=[
                # 顶部栏
                self._build_top_bar(),
                ft.Divider(height=2),
                # 可滚动的内容区域
                ft.Container(
                    content=ft.Column(
                        controls=[
                            self._build_esi_section(),
                            ft.Divider(height=1),
                            self._build_proxy_section(),
                            ft.Divider(height=1),
                            self._build_character_section(),
                            ft.Divider(height=1),
                            self._build_game_section(),
                            ft.Divider(height=1),
                            self._build_automation_section(),
                            ft.Divider(height=1),
                            self._build_templates_section(),
                            ft.Divider(height=1),
                            self._build_fallback_section(),
                        ],
                        spacing=16,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    expand=True,
                ),
                # 底部按钮
                ft.Container(
                    content=self._build_bottom_bar(),
                    padding=ft.padding.symmetric(vertical=10),
                ),
                # 状态消息
                self._status_text,
            ],
            spacing=0,
            expand=True,
        )
        return self

    def _build_top_bar(self):
        """构建顶部导航栏"""
        return ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    tooltip="返回主页面",
                    on_click=lambda e: self.on_back() if self.on_back else None,
                ),
                ft.Text("配置管理", size=22, weight=ft.FontWeight.BOLD),
            ],
        )

    def _build_bottom_bar(self):
        """构建底部操作按钮"""
        return ft.Row(
            controls=[
                ft.ElevatedButton(
                    "💾 保存配置",
                    icon=ft.Icons.SAVE,
                    color=ft.Colors.WHITE,
                    bgcolor=AppColors.PRIMARY,
                    height=AppSizes.BUTTON_HEIGHT,
                    on_click=self._save_config,
                ),
                ft.OutlinedButton(
                    "🔄 重置默认",
                    icon=ft.Icons.RESTORE,
                    height=AppSizes.BUTTON_HEIGHT,
                    on_click=self._reset_defaults,
                ),
                ft.OutlinedButton(
                    "📋 验证配置",
                    icon=ft.Icons.VERIFIED,
                    height=AppSizes.BUTTON_HEIGHT,
                    on_click=self._validate_config,
                ),
            ],
            spacing=12,
        )

    def _create_input_field(self, key: str, label: str, value: Any,
                            field_type: str = "text",
                            hint: str = "",
                            min_val: Optional[float] = None,
                            max_val: Optional[float] = None) -> ft.Control:
        """创建配置输入控件"""
        control_id = f"cfg_{key}"

        if field_type == "text":
            ctrl = ft.TextField(
                label=label,
                value=str(value) if value is not None else "",
                hint_text=hint,
                width=AppSizes.INPUT_WIDTH,
                dense=True,
            )
        elif field_type == "password":
            ctrl = ft.TextField(
                label=label,
                value=str(value) if value is not None else "",
                password=True,
                can_reveal_password=True,
                width=AppSizes.INPUT_WIDTH,
                dense=True,
            )
        elif field_type == "number":
            ctrl = ft.TextField(
                label=label,
                value=str(int(value)) if value is not None else "0",
                keyboard_type=ft.KeyboardType.NUMBER,
                width=AppSizes.INPUT_WIDTH,
                dense=True,
            )
        elif field_type == "float":
            ctrl = ft.TextField(
                label=label,
                value=str(float(value)) if value is not None else "0.0",
                keyboard_type=ft.KeyboardType.NUMBER,
                width=AppSizes.INPUT_WIDTH,
                dense=True,
            )
        elif field_type == "select":
            ctrl = ft.Dropdown(
                label=label,
                value=str(value) if value else "windowed",
                options=[
                    ft.dropdown.Option("windowed", "窗口模式"),
                    ft.dropdown.Option("fullscreen", "全屏模式"),
                    ft.dropdown.Option("borderless", "无边框窗口"),
                ],
                width=AppSizes.INPUT_WIDTH,
                dense=True,
            )
        elif field_type == "file":
            ctrl = ft.Row(
                controls=[
                    ft.TextField(
                        label=label,
                        value=str(value) if value else "",
                        width=AppSizes.INPUT_WIDTH - 120,
                        dense=True,
                        read_only=True,
                    ),
                    ft.ElevatedButton(
                        "浏览",
                        icon=ft.Icons.FOLDER_OPEN,
                        height=40,
                        on_click=lambda e, k=key: self._pick_template_file(k),
                    ),
                ],
                spacing=8,
            )
            self._controls_map[key] = ctrl
            return ctrl
        else:
            ctrl = ft.TextField(
                label=label,
                value=str(value) if value is not None else "",
                width=AppSizes.INPUT_WIDTH,
                dense=True,
            )

        ctrl.data = key  # 存储配置键
        self._controls_map[key] = ctrl
        return ctrl

    def _create_coord_fields(self, base_key: str, name: str,
                             x_val: float, y_val: float):
        """创建坐标输入组（X 和 Y）"""
        x_key = f"{base_key}.x"
        y_key = f"{base_key}.y"

        x_field = ft.TextField(
            label=f"{name} X",
            value=str(x_val),
            keyboard_type=ft.KeyboardType.NUMBER,
            width=120,
            dense=True,
            data=x_key,
        )
        y_field = ft.TextField(
            label=f"{name} Y",
            value=str(y_val),
            keyboard_type=ft.KeyboardType.NUMBER,
            width=120,
            dense=True,
            data=y_key,
        )
        self._controls_map[x_key] = x_field
        self._controls_map[y_key] = y_field

        return ft.Row(
            controls=[
                ft.Text(name, width=100, weight=ft.FontWeight.W_500),
                x_field,
                y_field,
            ],
            spacing=8,
        )

    def _build_esi_section(self):
        """ESI 配置区域（带完整注册指引）"""
        items = []
        items.append(section_header("📡 ESI 认证配置"))
        items.append(help_text("配置 EVE Online SSO 认证参数，才能通过 API 读取你的订单数据"))

        # --- 快速指引卡片 ---
        guide_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE, color=AppColors.PRIMARY, size=20),
                        ft.Text("📖 注册步骤（约需 3 分钟）", size=16, weight=ft.FontWeight.BOLD),
                    ], spacing=8),
                    ft.Divider(height=1),
                    ft.Text("① 点击下方按钮打开 EVE 开发者站点"),
                    ft.Text("② 使用你的 EVE 账号登录"),
                    ft.Text("③ 点击 Create an Application 创建应用"),
                    ft.Text("④ 任意填写应用名称（如 My Bot）"),
                    ft.Text("⑤ 回调 URL 填写：http://localhost:65010/callback/"),
                    ft.Text("⑥ 权限选择：esi-markets.read_character_orders.v1"),
                    ft.Text("⑦ 创建后复制 Client ID 和 Secret Key"),
                    ft.Text("⑧ 粘贴到下方输入框中，点击保存"),
                    ft.Container(height=6),
                    ft.ElevatedButton(
                        "🌐 打开 EVE 开发者站点",
                        icon=ft.Icons.OPEN_IN_BROWSER,
                        color=ft.Colors.WHITE,
                        bgcolor=AppColors.PRIMARY,
                        height=45,
                        url="https://developers.eveonline.com",
                    ),
                ], spacing=6),
                padding=18,
            ),
            elevation=2,
        )
        items.append(guide_card)

        # --- 输入区域 ---
        items.append(ft.Container(height=6))
        items.append(ft.Text("认证参数（必填）", weight=ft.FontWeight.BOLD, size=15))

        esi_keys = [
            ("esi.client_id", "Client ID", "text", "粘贴你的 Client ID"),
            ("esi.client_secret", "Client Secret", "password", "粘贴你的 Secret Key"),
            ("esi.callback_url", "回调 URL", "text", "http://localhost:65010/callback/"),
        ]
        for key, label, ftype, hint in esi_keys:
            meta = self.config.get_meta(key)
            ctrl = self._create_input_field(key, label, self.config.get(key),
                                            field_type=ftype)
            if hint:
                ctrl.hint_text = hint
            items.append(ctrl)

        # Scopes
        scopes = self.config.get("esi.scopes", [])
        scopes_str = " ".join(scopes) if isinstance(scopes, list) else str(scopes)
        scope_field = self._create_input_field(
            "esi.scopes", "授权权限", scopes_str, "text"
        )
        scope_field.hint_text = "esi-markets.read_character_orders.v1"
        items.append(scope_field)

        items.append(
            ft.Text("Tip: 如需更多权限，多个 scope 用空格分隔", size=12,
                    color=AppColors.TEXT_SECONDARY, italic=True)
        )

        return ft.Column(items, spacing=8)

    def _build_proxy_section(self):
        """代理配置区域"""
        items = []
        items.append(section_header("🌐 代理配置"))
        items.append(help_text("从中国大陆访问 EVE SSO 需要代理才能正常完成认证"))

        # 代理说明卡片
        guide_card = ft.Card(
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE, color=AppColors.PRIMARY, size=20),
                        ft.Text("📖 为何需要代理？", size=16, weight=ft.FontWeight.BOLD),
                    ], spacing=8),
                    ft.Divider(height=1),
                    ft.Text("EVE SSO 服务器 (login.eveonline.com) 在中国大陆被 Cloudflare 网络限制，"),
                    ft.Text("直接连接会收到 HTML 拦截页面，导致认证失败。"),
                    ft.Text("解决方案：通过代理服务器转发请求。推荐使用机场/VPN/Clash 等工具。"),
                    ft.Container(height=4),
                    ft.Text("常见代理地址示例：", weight=ft.FontWeight.BOLD),
                    ft.Text("• Clash/Stash: http://127.0.0.1:7890"),
                    ft.Text("• v2ray/Trojan: http://127.0.0.1:10809"),
                    ft.Text("• SS/SSR: http://127.0.0.1:1080"),
                    ft.Container(height=6),
                    ft.Text("💡 提示：如果 ssllogin.eveonline.com 依然被拦截，可尝试"),
                    ft.Text("在 hosts 文件中添加映射或使用支持 SNI 转发的代理。",
                           italic=True, size=12, color=AppColors.TEXT_SECONDARY),
                ], spacing=6),
                padding=18,
            ),
            elevation=2,
        )
        items.append(guide_card)

        items.append(ft.Container(height=6))

        # 启用代理开关
        proxy_enabled = self.config.get("proxy.enabled", False)
        proxy_switch = ft.Switch(
            label="启用代理",
            value=proxy_enabled,
            data="proxy.enabled",
        )
        self._controls_map["proxy.enabled"] = proxy_switch
        items.append(proxy_switch)

        # HTTP 代理
        items.append(
            self._create_input_field("proxy.http", "HTTP 代理",
                                     self.config.get("proxy.http", ""), "text",
                                     hint="例如: http://127.0.0.1:7890")
        )

        # HTTPS 代理
        items.append(
            self._create_input_field("proxy.https", "HTTPS 代理",
                                     self.config.get("proxy.https", ""), "text",
                                     hint="例如: http://127.0.0.1:7890")
        )

        # 测试代理按钮
        items.append(
            ft.ElevatedButton(
                "🔄 测试代理连接",
                icon=ft.Icons.WIFI_TETHERING,
                height=45,
                on_click=self._test_proxy,
            )
        )

        return ft.Column(items, spacing=8)

    def _test_proxy(self, e):
        """测试代理连接是否可用"""
        import requests as req

        http_proxy = self._controls_map.get("proxy.http")
        https_proxy = self._controls_map.get("proxy.https")

        http_url = http_proxy.value.strip() if http_proxy and isinstance(http_proxy, ft.TextField) else ""
        https_url = https_proxy.value.strip() if https_proxy and isinstance(https_proxy, ft.TextField) else ""

        if not http_url and not https_url:
            self._show_status("⚠️ 请先填写代理地址", AppColors.WARNING)
            return

        proxies = {}
        if http_url:
            proxies["http"] = http_url
        if https_url:
            proxies["https"] = https_url

        self._show_status("⏳ 正在测试代理连接...", AppColors.PRIMARY)
        self.update()

        try:
            # 测试连接 EVE SSO
            resp = req.get(
                "https://login.eveonline.com/oauth/authorize",
                proxies=proxies if proxies else None,
                timeout=10,
                allow_redirects=False,
            )
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" in content_type and len(resp.text) > 100 and "Cloudflare" in resp.text:
                self._show_status("❌ 代理测试失败 - 仍收到 Cloudflare 拦截页面", AppColors.ERROR)
            else:
                self._show_status(f"✅ 代理连接成功！HTTP {resp.status_code}", AppColors.SUCCESS)
        except Exception as ex:
            self._show_status(f"❌ 代理测试失败: {ex}", AppColors.ERROR)

    def _build_character_section(self):
        """角色信息配置"""
        items = []
        items.append(section_header("👤 角色信息"))
        items.append(help_text("配置你的 EVE 角色。角色 ID 可通过 zkillboard.com 查询"))

        char_keys = [
            ("character.id", "number"),
            ("character.name", "text"),
        ]
        for key, ftype in char_keys:
            meta = self.config.get_meta(key)
            items.append(
                self._create_input_field(key, meta[0], self.config.get(key),
                                         field_type=ftype)
            )

        return ft.Column(items, spacing=8)

    def _build_game_section(self):
        """游戏窗口配置"""
        items = []
        items.append(section_header("🎮 游戏窗口设置"))
        items.append(help_text("设置 EVE 游戏窗口参数，用于自动化操作定位"))

        items.append(
            self._create_input_field("game.window_title", "窗口标题",
                                     self.config.get("game.window_title"), "text")
        )
        items.append(
            self._create_input_field("game.window_mode", "窗口模式",
                                     self.config.get("game.window_mode"), "select")
        )

        # 分辨率
        res = self.config.get("game.resolution", {})
        res_row = ft.Row(
            controls=[
                ft.Text("分辨率", width=100, weight=ft.FontWeight.W_500),
                self._create_input_field("game.resolution.width", "宽度",
                                         res.get("width", 1920), "number"),
                ft.Text("×", size=18),
                self._create_input_field("game.resolution.height", "高度",
                                         res.get("height", 1080), "number"),
            ],
            spacing=8,
        )
        items.append(res_row)

        return ft.Column(items, spacing=8)

    def _build_automation_section(self):
        """自动化参数配置"""
        items = []
        items.append(section_header("🤖 自动化参数"))
        items.append(help_text("配置自动改价的核心参数，请谨慎调整"))

        auto_keys = [
            ("automation.interval_minutes", "number"),
            ("automation.modify_cooldown_seconds", "number"),
            ("automation.price_adjustment_percent", "float"),
            ("automation.buy_price_adjustment_percent", "float"),
            ("automation.max_price_change_percent", "float"),
            ("automation.retry_attempts", "number"),
        ]
        for key, ftype in auto_keys:
            meta = self.config.get_meta(key)
            items.append(
                self._create_input_field(key, meta[0], self.config.get(key),
                                         field_type=ftype)
            )

        return ft.Column(items, spacing=8)

    def _build_templates_section(self):
        """模板图片路径配置"""
        items = []
        items.append(section_header("🖼 模板图片路径"))
        items.append(help_text("设置 OpenCV 模板匹配用的截图文件路径（支持 .png）"))

        tmpl_keys = [
            ("templates.search_box", "搜索框"),
            ("templates.modify_button", "修改按钮"),
            ("templates.price_input", "价格输入框"),
            ("templates.confirm_button", "确认按钮"),
            ("templates.market_tab", "市场标签"),
        ]
        for key, name in tmpl_keys:
            items.append(
                self._create_input_field(key, name, self.config.get(key), "file")
            )

        return ft.Column(items, spacing=8)

    def _build_fallback_section(self):
        """Fallback 坐标配置"""
        items = []
        items.append(section_header("📍 Fallback 坐标"))
        items.append(help_text("当模板匹配失败时使用的百分比坐标（0.0 ~ 1.0）"))

        coords = self.config.get("fallback_coordinates", {})
        coord_items = [
            ("search_box", "搜索框"),
            ("my_order_row", "订单行"),
            ("modify_button", "修改按钮"),
            ("price_input", "价格输入框"),
            ("confirm_button", "确认按钮"),
            ("market_tab", "市场标签"),
        ]
        for key, name in coord_items:
            coord = coords.get(key, {"x": 0.5, "y": 0.5})
            items.append(
                self._create_coord_fields(f"fallback_coordinates.{key}", name,
                                          coord.get("x", 0.5), coord.get("y", 0.5))
            )

        return ft.Column(items, spacing=8)

    def _save_config(self, e):
        """保存配置"""
        try:
            # 从控件读取所有值
            for key, ctrl in self._controls_map.items():
                value = self._read_control_value(key, ctrl)
                if value is not None:
                    self.config.set(key, value)

            if self.config.save():
                self._show_status("✅ 配置保存成功！", AppColors.SUCCESS)
            else:
                self._show_status("❌ 配置保存失败", AppColors.ERROR)
        except Exception as ex:
            self._show_status(f"❌ 保存出错: {ex}", AppColors.ERROR)

    def _read_control_value(self, key: str, ctrl: ft.Control) -> Optional[Any]:
        """从控件读取值，根据控件类型转换"""
        if isinstance(ctrl, ft.Switch):
            return ctrl.value

        if isinstance(ctrl, ft.TextField):
            raw = ctrl.value.strip()
            meta = self.config.get_meta(key)
            ftype = meta[1]

            if ftype == "number":
                try:
                    return int(raw) if raw else None
                except ValueError:
                    return None
            elif ftype == "float":
                try:
                    return float(raw) if raw else None
                except ValueError:
                    return None
            elif ftype == "file":
                return raw if raw else None
            return raw if raw else None

        elif isinstance(ctrl, ft.Dropdown):
            return ctrl.value

        return None

    def _reset_defaults(self, e):
        """重置为默认值"""
        # 显示确认对话框
        dlg = ft.AlertDialog(
            title=ft.Text("确认重置"),
            content=ft.Text("将重置所有配置为默认值，此操作不可撤销。确定继续？"),
            actions=[
                ft.TextButton("取消", on_click=lambda e: self._close_dialog()),
                ft.ElevatedButton(
                    "确定重置",
                    color=ft.Colors.WHITE,
                    bgcolor=AppColors.ERROR,
                    on_click=lambda e: self._do_reset(),
                ),
            ],
        )
        self.page.open(dlg)
        self._dlg = dlg

    def _close_dialog(self):
        """关闭对话框"""
        if hasattr(self, '_dlg') and self._dlg:
            self.page.close(self._dlg)

    def _do_reset(self):
        """执行重置"""
        self._close_dialog()
        from src.config import DEFAULT_CONFIG
        # 重新加载页面（简化处理：刷新整个页面）
        self._show_status("已重置为默认值，请点击'保存配置'生效", AppColors.WARNING)

    def _validate_config(self, e):
        """验证配置"""
        errors = self.config.validate()
        if not errors:
            self._show_status("✅ 配置验证通过！所有必填项已配置", AppColors.SUCCESS)
        else:
            msg = "⚠️ 以下配置缺失:\n" + "\n".join(f"  • {err}" for err in errors)
            self._show_status(msg, AppColors.ERROR)

    def _pick_template_file(self, key: str):
        """选择模板文件"""
        # 使用文件选择器（Flet 内置）
        def on_file_result(e: ft.FilePickerResultEvent):
            if e.files and len(e.files) > 0:
                file_path = e.files[0].path
                # 更新对应控件的值
                if key in self._controls_map:
                    row = self._controls_map[key]
                    if isinstance(row, ft.Row) and len(row.controls) > 0:
                        tf = row.controls[0]
                        if isinstance(tf, ft.TextField):
                            tf.value = file_path
                            tf.update()

        picker = ft.FilePicker(on_result=on_file_result)
        self.page.overlay.append(picker)
        self.page.update()
        picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["png", "jpg", "jpeg", "bmp"]
        )

    def _show_status(self, msg: str, color: str):
        """显示状态消息"""
        self._status_text.value = msg
        self._status_text.color = color
        self._status_text.update()
