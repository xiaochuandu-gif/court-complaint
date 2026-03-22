#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键投诉法院不立案不下裁定 v2.0
================================
针对法院立案庭不立案且不下不予立案裁定的问题，
一键自动向多个受理法官违法违纪的平台进行投诉。

v2.0 新增功能：
- 自动登录/注册各投诉平台
- 账号密码本地加密存储
- 手动接管模式（遇到验证码等问题时让用户操作）
- 浏览器自动化引擎（基于 Selenium）

使用方法：
1. 在左侧文本框撰写投诉内容
2. 在右侧勾选要投诉的平台
3. 点击"一键投诉"按钮
4. 程序会自动打开所有选中平台的投诉页面，并将投诉内容复制到剪贴板

运行环境：Python 3.6+
依赖：tkinter（标准库）、selenium + webdriver-manager（可选，用于自动登录）
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import webbrowser
import json
import os
import datetime
import threading
import subprocess
import sys

# 导入自定义模块
try:
    from account_manager import AccountManager
    ACCOUNT_MANAGER_AVAILABLE = True
except ImportError:
    ACCOUNT_MANAGER_AVAILABLE = False

try:
    from browser_engine import BrowserEngine, SELENIUM_AVAILABLE, check_and_install_dependencies
    BROWSER_ENGINE_AVAILABLE = True
except ImportError:
    BROWSER_ENGINE_AVAILABLE = False
    SELENIUM_AVAILABLE = False

try:
    from platform_adapters import get_adapter, LoginResult, ADAPTER_REGISTRY
    ADAPTERS_AVAILABLE = True
except ImportError:
    ADAPTERS_AVAILABLE = False


# ============================================================
# 投诉渠道数据
# ============================================================

COMPLAINT_CHANNELS = [
    {
        "category": "法院系统",
        "channels": [
            {
                "name": "最高人民法院违纪违法举报中心",
                "url": "https://jubao.court.gov.cn",
                "desc": "最高法院官方举报平台，可举报法院工作人员违纪违法行为",
                "phone": "",
                "enabled": True,
            },
            {
                "name": "人民法院网上申诉信访平台",
                "url": "https://ssxfpt.court.gov.cn",
                "desc": "法院系统统一的网上申诉信访入口",
                "phone": "",
                "enabled": True,
            },
            {
                "name": "12368诉讼服务热线",
                "url": "https://www.court.gov.cn",
                "desc": "法院诉讼服务热线，可投诉法官不作为、不立案等问题",
                "phone": "12368",
                "enabled": True,
            },
        ],
    },
    {
        "category": "检察院监督",
        "channels": [
            {
                "name": "12309中国检察网",
                "url": "https://www.12309.gov.cn",
                "desc": "检察院对法院有法律监督权，可举报法官涉嫌渎职",
                "phone": "12309",
                "enabled": True,
            },
        ],
    },
    {
        "category": "纪检监察系统",
        "channels": [
            {
                "name": "中央纪委国家监委举报网站",
                "url": "https://www.12388.gov.cn",
                "desc": "纪检监察机关举报平台，可举报法官违纪违法行为",
                "phone": "12388",
                "enabled": True,
            },
            {
                "name": "中央和国家机关纪检监察工委",
                "url": "https://zygjjg.12388.gov.cn",
                "desc": "中央和国家机关纪检监察工作委员会举报网站",
                "phone": "",
                "enabled": True,
            },
        ],
    },
    {
        "category": "人大信访系统",
        "channels": [
            {
                "name": "全国人大机关网上信访",
                "url": "http://www.npc.gov.cn/wsxf/",
                "desc": "全国人大常委会网上信访平台，人大对法院有监督权",
                "phone": "",
                "enabled": True,
            },
            {
                "name": "省人大信访（请根据所在省份选择）",
                "url": "",
                "desc": "各省人大常委会信访渠道，对本省法院有监督权",
                "phone": "",
                "enabled": True,
                "sub_channels": {
                    "北京市": "http://www.bjrd.gov.cn",
                    "天津市": "http://www.tjrd.gov.cn",
                    "河北省": "http://www.hbrd.gov.cn",
                    "山西省": "http://www.sxrd.gov.cn",
                    "内蒙古": "http://www.nmgrd.gov.cn",
                    "辽宁省": "http://www.lnrd.gov.cn",
                    "吉林省": "http://www.jlrd.gov.cn",
                    "黑龙江省": "http://www.hljrd.gov.cn",
                    "上海市": "http://www.spcsc.sh.cn",
                    "江苏省": "http://www.jsrd.gov.cn",
                    "浙江省": "http://www.zjrd.gov.cn",
                    "安徽省": "http://www.ahrd.gov.cn",
                    "福建省": "http://www.fjrd.gov.cn",
                    "江西省": "http://www.jxrd.gov.cn",
                    "山东省": "http://www.sdrd.gov.cn",
                    "河南省": "http://www.hnrd.gov.cn",
                    "湖北省": "http://www.hbrd.net",
                    "湖南省": "http://www.hnrd.gov.cn",
                    "广东省": "http://www.gdrd.cn",
                    "广西": "http://www.gxrd.gov.cn",
                    "海南省": "http://www.hainanpc.net",
                    "重庆市": "http://www.ccpc.cq.cn",
                    "四川省": "http://www.scspc.gov.cn",
                    "贵州省": "http://www.gzrd.gov.cn",
                    "云南省": "http://www.ynrd.gov.cn",
                    "西藏": "http://www.xzrd.gov.cn",
                    "陕西省": "http://www.sxrd.gov.cn",
                    "甘肃省": "http://www.gsrdw.gov.cn",
                    "青海省": "http://www.qhrd.gov.cn",
                    "宁夏": "http://www.nxrd.gov.cn",
                    "新疆": "http://www.xjpcsc.gov.cn",
                },
            },
        ],
    },
    {
        "category": "信访局系统",
        "channels": [
            {
                "name": "国家信访局网上信访",
                "url": "https://wsxf.gjxfj.gov.cn",
                "desc": "国家信访局统一网上信访平台，可反映法院不作为问题",
                "phone": "",
                "enabled": True,
            },
            {
                "name": "省信访局（请根据所在省份选择）",
                "url": "",
                "desc": "各省市信访局网上投诉平台",
                "phone": "",
                "enabled": True,
                "sub_channels": {
                    "北京市": "https://www.beijing.gov.cn",
                    "天津市": "https://xfj.tj.gov.cn",
                    "河北省": "http://wsxf.hebxf.gov.cn",
                    "山西省": "http://wsxf.shanxixf.gov.cn",
                    "内蒙古": "http://wsxf.nmgxfj.gov.cn",
                    "辽宁省": "http://wsxf.lnxfj.gov.cn",
                    "吉林省": "http://wsxf.jlxfj.gov.cn",
                    "黑龙江省": "http://wsxf.hljxfj.gov.cn",
                    "上海市": "https://wsxf.sh.gov.cn",
                    "江苏省": "http://wsxf.jsxfj.gov.cn",
                    "浙江省": "http://wsxf.zjxfj.gov.cn",
                    "安徽省": "http://wsxf.ahxf.gov.cn",
                    "福建省": "http://wsxf.fjxf.gov.cn",
                    "江西省": "http://wsxf.jxxfj.gov.cn",
                    "山东省": "http://wsxf.sdxfj.gov.cn",
                    "河南省": "http://wsxf.hnxfj.gov.cn",
                    "湖北省": "http://wsxf.hbxfj.gov.cn",
                    "湖南省": "http://wsxf.hnxfj.gov.cn",
                    "广东省": "https://ts.gdwsxf.gd.gov.cn",
                    "广西": "http://wsxf.gxxfj.gov.cn",
                    "海南省": "https://xf.hainan.gov.cn",
                    "重庆市": "http://wsxf.cqxfj.gov.cn",
                    "四川省": "http://wsxf.scxfj.gov.cn",
                    "贵州省": "http://wsxf.gzxfj.gov.cn",
                    "云南省": "http://wsxf.ynxfj.gov.cn",
                    "西藏": "http://wsxf.xzxfj.gov.cn",
                    "陕西省": "http://wsxf.sxxfj.gov.cn",
                    "甘肃省": "http://wsxf.gsxfj.gov.cn",
                    "青海省": "http://wsxf.qhxfj.gov.cn",
                    "宁夏": "http://wsxf.nxxfj.gov.cn",
                    "新疆": "http://wsxf.xjxfj.gov.cn",
                },
            },
        ],
    },
    {
        "category": "司法行政部门",
        "channels": [
            {
                "name": "司法部网上信访",
                "url": "https://www.moj.gov.cn/hdjl/hdjlwsxf/",
                "desc": "司法部网上信访邮箱：sfbxf@moj.gov.cn",
                "phone": "",
                "enabled": True,
            },
        ],
    },
    {
        "category": "政法委系统",
        "channels": [
            {
                "name": "12337政法干警违纪违法举报平台",
                "url": "https://www.12337.gov.cn",
                "desc": "中央政法委政法干警违纪违法举报平台",
                "phone": "12337",
                "enabled": True,
            },
        ],
    },
    {
        "category": "其他渠道",
        "channels": [
            {
                "name": "人民网领导留言板",
                "url": "https://liuyan.people.com.cn",
                "desc": "可向各级领导反映法院不立案问题",
                "phone": "",
                "enabled": True,
            },
            {
                "name": "国务院互联网+督查平台",
                "url": "https://tousu.www.gov.cn",
                "desc": "国务院督查平台，可反映政府部门不作为问题",
                "phone": "",
                "enabled": True,
            },
        ],
    },
]

# 默认投诉模板
DEFAULT_TEMPLATE = """投诉人：[姓名]
联系电话：[电话]
身份证号：[身份证号]

被投诉单位：[XX法院立案庭]
被投诉人：[法官姓名/立案庭工作人员]

投诉事项：关于XX法院立案庭不立案且不下不予立案裁定的投诉

事实与理由：

本人于[日期]向[XX法院]提交民事起诉状及相关证据材料，请求立案受理本人与[被告名称]之间的[案由]纠纷一案。

然而，该法院立案庭至今既未依法予以立案，也未依法作出不予立案的裁定书，严重违反了以下法律规定：

一、《中华人民共和国民事诉讼法》第一百二十六条规定："人民法院应当保障当事人依照法律规定享有的起诉权利。对符合本法第一百二十二条的起诉，必须受理。符合起诉条件的，应当在七日内立案，并通知当事人；不符合起诉条件的，应当在七日内作出裁定书，不予受理；原告对裁定不服的，可以提起上诉。"

二、《最高人民法院关于人民法院登记立案若干问题的规定》第二条规定："对起诉、自诉，人民法院应当一律接收诉状，出具书面凭证并注明收到日期。"第八条规定："对当事人提出的起诉，人民法院应当在收到起诉状之日起七日内决定是否立案。"

三、该法院立案庭的行为属于典型的"不立不裁"，严重侵害了本人的诉权，违反了立案登记制的相关规定。

投诉请求：

1. 请依法督促[XX法院]立案庭对本人的起诉依法予以立案，或依法作出不予立案的书面裁定；
2. 请对相关责任人员的违法违纪行为进行调查处理；
3. 请将处理结果书面告知投诉人。

此致

投诉人：[姓名]
日期：[日期]"""


class ComplaintApp:
    """一键投诉法院不立案不下裁定 - 主应用类 v2.0"""

    def __init__(self, root):
        self.root = root
        self.root.title("一键投诉 v2.0 - 法院不立案不下裁定投诉工具")
        self.root.geometry("1200x850")
        self.root.minsize(900, 650)

        # 配置文件路径
        self.config_dir = os.path.join(os.path.expanduser("~"), ".court_complaint")
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.history_file = os.path.join(self.config_dir, "history.json")
        self.browser_data_dir = os.path.join(self.config_dir, "browser_data")

        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)

        # 渠道选择状态
        self.channel_vars = {}
        # 省份选择
        self.province_var = tk.StringVar(value="请选择省份")

        # 账号管理器
        self.account_manager = None
        if ACCOUNT_MANAGER_AVAILABLE:
            self.account_manager = AccountManager(self.config_dir)

        # 浏览器引擎
        self.browser_engine = None
        self._browser_thread = None
        self._auto_login_running = False

        # 设置样式
        self._setup_styles()
        # 构建界面
        self._build_ui()
        # 加载配置
        self._load_config()

    def _setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        style.theme_use("clam")

        # 主色调
        BG = "#fafafa"
        FG = "#1a1a2e"
        ACCENT = "#dc2626"
        BORDER = "#e2e8f0"
        CARD_BG = "#ffffff"

        self.root.configure(bg=BG)

        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD_BG, relief="solid", borderwidth=1)
        style.configure("TLabel", background=BG, foreground=FG, font=("Microsoft YaHei UI", 10))
        style.configure("Title.TLabel", background=BG, foreground=FG, font=("Microsoft YaHei UI", 18, "bold"))
        style.configure("Subtitle.TLabel", background=BG, foreground="#64748b", font=("Microsoft YaHei UI", 10))
        style.configure("Category.TLabel", background=CARD_BG, foreground=FG, font=("Microsoft YaHei UI", 11, "bold"))
        style.configure("Desc.TLabel", background=CARD_BG, foreground="#64748b", font=("Microsoft YaHei UI", 9))
        style.configure("Phone.TLabel", background=CARD_BG, foreground=ACCENT, font=("Microsoft YaHei UI", 9, "bold"))

        style.configure("TCheckbutton", background=CARD_BG, foreground=FG, font=("Microsoft YaHei UI", 10))
        style.map("TCheckbutton", background=[("active", CARD_BG)])

        style.configure("Accent.TButton", font=("Microsoft YaHei UI", 12, "bold"))
        style.configure("TButton", font=("Microsoft YaHei UI", 10))

        style.configure("TCombobox", font=("Microsoft YaHei UI", 10))

        style.configure("TNotebook", background=BG)
        style.configure("TNotebook.Tab", font=("Microsoft YaHei UI", 10), padding=[12, 6])

        # 新增状态样式
        style.configure("Status.TLabel", background=BG, foreground="#059669", font=("Microsoft YaHei UI", 9))
        style.configure("Warning.TLabel", background=BG, foreground="#d97706", font=("Microsoft YaHei UI", 9))
        style.configure("Error.TLabel", background=BG, foreground="#dc2626", font=("Microsoft YaHei UI", 9))

    def _build_ui(self):
        """构建主界面"""
        # 顶部标题栏
        header = ttk.Frame(self.root)
        header.pack(fill=tk.X, padx=20, pady=(15, 5))

        ttk.Label(header, text="⚖ 一键投诉 v2.0", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(
            header,
            text="针对法院立案庭不立案且不下不予立案裁定",
            style="Subtitle.TLabel",
        ).pack(side=tk.LEFT, padx=(15, 0), pady=(5, 0))

        # 省份选择栏
        province_frame = ttk.Frame(self.root)
        province_frame.pack(fill=tk.X, padx=20, pady=(5, 5))

        ttk.Label(province_frame, text="所在省份：").pack(side=tk.LEFT)
        provinces = ["请选择省份"] + list(
            COMPLAINT_CHANNELS[3]["channels"][1]["sub_channels"].keys()
        )
        province_combo = ttk.Combobox(
            province_frame,
            textvariable=self.province_var,
            values=provinces,
            state="readonly",
            width=15,
        )
        province_combo.pack(side=tk.LEFT, padx=(5, 15))
        ttk.Label(
            province_frame,
            text="（选择省份后，省人大信访和省信访局将自动匹配对应网址）",
            style="Subtitle.TLabel",
        ).pack(side=tk.LEFT)

        # 主体区域 - 左右分栏
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        # ====== 左侧：投诉内容编辑区 ======
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=3)

        # 左侧标签页
        left_notebook = ttk.Notebook(left_frame)
        left_notebook.pack(fill=tk.BOTH, expand=True)

        # 投诉内容标签页
        content_tab = ttk.Frame(left_notebook)
        left_notebook.add(content_tab, text="  投诉内容  ")

        # 工具栏
        toolbar = ttk.Frame(content_tab)
        toolbar.pack(fill=tk.X, pady=(5, 3))

        ttk.Button(toolbar, text="加载模板", command=self._load_template).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="清空内容", command=self._clear_content).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="从文件导入", command=self._import_from_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="保存到文件", command=self._save_to_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="保存草稿", command=self._save_draft).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="加载草稿", command=self._load_draft).pack(side=tk.LEFT, padx=2)

        # 文本编辑区
        self.text_editor = scrolledtext.ScrolledText(
            content_tab,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 11),
            padx=10,
            pady=10,
            relief="solid",
            borderwidth=1,
            bg="#ffffff",
            fg="#1a1a2e",
            insertbackground="#1a1a2e",
            selectbackground="#dc2626",
            selectforeground="#ffffff",
        )
        self.text_editor.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # 字数统计
        self.char_count_var = tk.StringVar(value="字数：0")
        ttk.Label(content_tab, textvariable=self.char_count_var, style="Subtitle.TLabel").pack(
            anchor=tk.E, padx=5
        )
        self.text_editor.bind("<KeyRelease>", self._update_char_count)

        # ====== 账号管理标签页 ======
        account_tab = ttk.Frame(left_notebook)
        left_notebook.add(account_tab, text="  账号管理  ")
        self._build_account_tab(account_tab)

        # ====== 自动登录日志标签页 ======
        log_tab = ttk.Frame(left_notebook)
        left_notebook.add(log_tab, text="  登录日志  ")
        self._build_log_tab(log_tab)

        # 使用说明标签页
        help_tab = ttk.Frame(left_notebook)
        left_notebook.add(help_tab, text="  使用说明  ")

        help_text = scrolledtext.ScrolledText(
            help_tab,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 11),
            padx=15,
            pady=15,
            relief="flat",
            bg="#fafafa",
            fg="#1a1a2e",
        )
        help_text.pack(fill=tk.BOTH, expand=True)
        help_text.insert(
            tk.END,
            """使用说明 v2.0
═══════════════════════════════════════

本工具用于针对法院立案庭"不立案且不下不予立案裁定"的违法行为，一键向多个监督平台提交投诉。

【v2.0 新增功能】

★ 自动登录：自动打开浏览器并登录各投诉平台
★ 账号管理：本地加密保存各平台的用户名和密码
★ 自动注册：使用预设手机号和邮箱自动注册新账号
★ 手动接管：遇到验证码等问题时，弹窗提示用户手动操作

【操作步骤】

第一步：配置账号（首次使用）
    切换到"账号管理"标签页，设置默认注册手机号和邮箱。
    可以为每个平台单独设置用户名和密码。

第二步：选择省份
    在顶部下拉框选择您所在的省份。

第三步：撰写投诉内容
    在"投诉内容"标签页中撰写您的投诉材料。

第四步：选择投诉平台
    在右侧勾选您要投诉的平台。

第五步：一键投诉
    点击底部红色的"一键投诉"按钮，程序将：
    ① 自动启动浏览器
    ② 逐个登录选中的投诉平台（如有保存的账号）
    ③ 遇到验证码等问题时弹窗提示手动操作
    ④ 自动将投诉内容复制到剪贴板
    ⑤ 打开所有投诉页面

    也可以选择"传统模式"（不自动登录，仅打开网页）。

【法律依据】

• 《民事诉讼法》第126条：法院应在7日内立案或作出不予立案裁定
• 《最高人民法院关于人民法院登记立案若干问题的规定》
• 《人民法院工作人员处分条例》

【注意事项】

1. 自动登录功能需要安装 selenium：pip install selenium webdriver-manager
2. 投诉内容请实事求是，如实反映情况
3. 建议保留好起诉材料的递交凭证
4. 投诉后请关注各平台的回复和处理进度
5. 账号密码以编码形式保存在本地，请注意保护
""",
        )
        help_text.configure(state=tk.DISABLED)

        # ====== 右侧：投诉渠道选择区 ======
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)

        # 右侧标题
        right_header = ttk.Frame(right_frame)
        right_header.pack(fill=tk.X, pady=(5, 5))
        ttk.Label(right_header, text="投诉平台", style="Category.TLabel").pack(side=tk.LEFT)

        btn_frame = ttk.Frame(right_header)
        btn_frame.pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="全选", command=self._select_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="全不选", command=self._deselect_all).pack(side=tk.LEFT, padx=2)

        # 渠道列表（可滚动）
        canvas = tk.Canvas(right_frame, bg="#fafafa", highlightthickness=0)
        scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.channels_frame = ttk.Frame(canvas)

        self.channels_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=self.channels_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        # Linux 滚轮支持
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        # ====== 底部操作栏 ======
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(fill=tk.X, padx=20, pady=(5, 10))

        # 选中数量提示
        self.selected_count_var = tk.StringVar(value="已选择 0 个平台")
        ttk.Label(bottom_frame, textvariable=self.selected_count_var).pack(side=tk.LEFT)

        # 填充渠道列表
        self._populate_channels()

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(bottom_frame, textvariable=self.status_var, style="Status.TLabel")
        status_label.pack(side=tk.LEFT, padx=(20, 0))

        # 一键投诉按钮（自动登录模式）
        auto_submit_btn = tk.Button(
            bottom_frame,
            text="🚀 一键投诉（自动登录）",
            font=("Microsoft YaHei UI", 13, "bold"),
            bg="#dc2626",
            fg="#ffffff",
            activebackground="#b91c1c",
            activeforeground="#ffffff",
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2",
            command=self._submit_with_auto_login,
        )
        auto_submit_btn.pack(side=tk.RIGHT)

        # 传统模式按钮
        classic_btn = tk.Button(
            bottom_frame,
            text="📋 传统模式（仅打开网页）",
            font=("Microsoft YaHei UI", 11),
            bg="#475569",
            fg="#ffffff",
            activebackground="#334155",
            activeforeground="#ffffff",
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2",
            command=self._submit_complaints,
        )
        classic_btn.pack(side=tk.RIGHT, padx=(0, 10))

        # 复制内容按钮
        copy_btn = tk.Button(
            bottom_frame,
            text="📋 仅复制",
            font=("Microsoft YaHei UI", 10),
            bg="#6b7280",
            fg="#ffffff",
            activebackground="#4b5563",
            activeforeground="#ffffff",
            relief="flat",
            padx=10,
            pady=8,
            cursor="hand2",
            command=self._copy_content,
        )
        copy_btn.pack(side=tk.RIGHT, padx=(0, 10))

    # ============================================================
    # 账号管理标签页
    # ============================================================

    def _build_account_tab(self, parent):
        """构建账号管理标签页"""
        # 默认注册信息区域
        default_frame = ttk.LabelFrame(parent, text=" 默认注册信息 ", padding=10)
        default_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        row1 = ttk.Frame(default_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="手机号：", width=10).pack(side=tk.LEFT)
        self.default_phone_var = tk.StringVar()
        ttk.Entry(row1, textvariable=self.default_phone_var, width=30).pack(side=tk.LEFT, padx=5)

        row2 = ttk.Frame(default_frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="邮箱：", width=10).pack(side=tk.LEFT)
        self.default_email_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.default_email_var, width=30).pack(side=tk.LEFT, padx=5)

        row3 = ttk.Frame(default_frame)
        row3.pack(fill=tk.X, pady=2)
        ttk.Label(row3, text="默认密码：", width=10).pack(side=tk.LEFT)
        self.default_password_var = tk.StringVar()
        ttk.Entry(row3, textvariable=self.default_password_var, width=30, show="*").pack(side=tk.LEFT, padx=5)
        ttk.Label(row3, text="（用于自动注册时设置密码）", style="Subtitle.TLabel").pack(side=tk.LEFT, padx=5)

        btn_row = ttk.Frame(default_frame)
        btn_row.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(btn_row, text="保存默认信息", command=self._save_default_credentials).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="安装自动登录依赖", command=self._install_dependencies).pack(side=tk.LEFT, padx=2)

        # 依赖状态
        dep_status = "已安装" if SELENIUM_AVAILABLE else "未安装（点击上方按钮安装）"
        dep_color = "#059669" if SELENIUM_AVAILABLE else "#d97706"
        dep_label = ttk.Label(btn_row, text=f"Selenium 状态: {dep_status}")
        dep_label.pack(side=tk.LEFT, padx=(15, 0))

        # 平台账号列表区域
        accounts_frame = ttk.LabelFrame(parent, text=" 各平台账号 ", padding=10)
        accounts_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 说明文字
        ttk.Label(
            accounts_frame,
            text="为每个投诉平台设置登录账号。未设置的平台将在投诉时提示手动登录。",
            style="Subtitle.TLabel",
            wraplength=500,
        ).pack(anchor=tk.W, pady=(0, 5))

        # 平台账号编辑区（可滚动）
        acc_canvas = tk.Canvas(accounts_frame, bg="#fafafa", highlightthickness=0, height=250)
        acc_scrollbar = ttk.Scrollbar(accounts_frame, orient=tk.VERTICAL, command=acc_canvas.yview)
        self.acc_inner_frame = ttk.Frame(acc_canvas)

        self.acc_inner_frame.bind(
            "<Configure>", lambda e: acc_canvas.configure(scrollregion=acc_canvas.bbox("all"))
        )
        acc_canvas.create_window((0, 0), window=self.acc_inner_frame, anchor="nw")
        acc_canvas.configure(yscrollcommand=acc_scrollbar.set)

        acc_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        acc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 填充平台账号表单
        self.platform_account_entries = {}
        self._populate_account_entries()

        # 底部按钮
        acc_btn_frame = ttk.Frame(parent)
        acc_btn_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(acc_btn_frame, text="保存所有账号", command=self._save_all_accounts).pack(side=tk.LEFT, padx=2)
        ttk.Button(acc_btn_frame, text="清空所有账号", command=self._clear_all_accounts).pack(side=tk.LEFT, padx=2)
        ttk.Button(acc_btn_frame, text="批量设置（用默认账号填充所有平台）", command=self._batch_fill_accounts).pack(side=tk.LEFT, padx=2)

        # 加载已保存的账号
        self._load_saved_accounts()

    def _populate_account_entries(self):
        """填充平台账号输入表单"""
        all_platforms = []
        for cat in COMPLAINT_CHANNELS:
            for ch in cat["channels"]:
                if ch.get("phone") and not ch.get("url"):
                    continue  # 跳过纯电话渠道
                all_platforms.append(ch["name"])

        for i, platform in enumerate(all_platforms):
            frame = tk.Frame(self.acc_inner_frame, bg="#ffffff", relief="solid", bd=1, padx=8, pady=4)
            frame.pack(fill=tk.X, padx=3, pady=2)

            # 平台名
            tk.Label(frame, text=platform, font=("Microsoft YaHei UI", 9, "bold"),
                     bg="#ffffff", fg="#1a1a2e", width=30, anchor=tk.W).grid(row=0, column=0, sticky=tk.W)

            # 用户名
            tk.Label(frame, text="用户名:", font=("Microsoft YaHei UI", 9),
                     bg="#ffffff").grid(row=0, column=1, padx=(10, 2))
            user_entry = tk.Entry(frame, width=18, font=("Microsoft YaHei UI", 9))
            user_entry.grid(row=0, column=2, padx=2)

            # 密码
            tk.Label(frame, text="密码:", font=("Microsoft YaHei UI", 9),
                     bg="#ffffff").grid(row=0, column=3, padx=(10, 2))
            pwd_entry = tk.Entry(frame, width=18, font=("Microsoft YaHei UI", 9), show="*")
            pwd_entry.grid(row=0, column=4, padx=2)

            # 登录状态指示
            status_label = tk.Label(frame, text="未登录", font=("Microsoft YaHei UI", 8),
                                    bg="#ffffff", fg="#9ca3af")
            status_label.grid(row=0, column=5, padx=(10, 2))

            self.platform_account_entries[platform] = {
                "username": user_entry,
                "password": pwd_entry,
                "status": status_label,
            }

    def _save_default_credentials(self):
        """保存默认注册信息"""
        if not self.account_manager:
            messagebox.showwarning("提示", "账号管理模块未加载")
            return
        phone = self.default_phone_var.get().strip()
        email = self.default_email_var.get().strip()
        password = self.default_password_var.get().strip()

        if not phone and not email:
            messagebox.showwarning("提示", "请至少填写手机号或邮箱")
            return

        self.account_manager.set_default_credentials(phone, email, password)
        messagebox.showinfo("成功", "默认注册信息已保存")

    def _save_all_accounts(self):
        """保存所有平台的账号信息"""
        if not self.account_manager:
            messagebox.showwarning("提示", "账号管理模块未加载")
            return

        saved_count = 0
        for platform, entries in self.platform_account_entries.items():
            username = entries["username"].get().strip()
            password = entries["password"].get().strip()
            if username and password:
                defaults = self.account_manager.get_default_credentials() or {}
                self.account_manager.save_account(
                    platform, username, password,
                    phone=defaults.get("phone", ""),
                    email=defaults.get("email", ""),
                )
                saved_count += 1

        messagebox.showinfo("成功", f"已保存 {saved_count} 个平台的账号信息")

    def _clear_all_accounts(self):
        """清空所有账号"""
        if not messagebox.askyesno("确认", "确定要清空所有已保存的账号信息吗？"):
            return
        for platform, entries in self.platform_account_entries.items():
            entries["username"].delete(0, tk.END)
            entries["password"].delete(0, tk.END)
            entries["status"].config(text="未登录", fg="#9ca3af")
            if self.account_manager:
                self.account_manager.delete_account(platform)
        messagebox.showinfo("成功", "所有账号信息已清空")

    def _batch_fill_accounts(self):
        """用默认账号信息批量填充所有平台"""
        if not self.account_manager:
            messagebox.showwarning("提示", "账号管理模块未加载")
            return

        defaults = self.account_manager.get_default_credentials()
        if not defaults:
            messagebox.showwarning("提示", "请先保存默认注册信息（手机号/邮箱/密码）")
            return

        phone = defaults.get("phone", "")
        password = defaults.get("default_password", "")

        if not phone:
            messagebox.showwarning("提示", "默认手机号为空，无法批量填充")
            return

        for platform, entries in self.platform_account_entries.items():
            if not entries["username"].get().strip():
                entries["username"].delete(0, tk.END)
                entries["username"].insert(0, phone)
            if not entries["password"].get().strip() and password:
                entries["password"].delete(0, tk.END)
                entries["password"].insert(0, password)

        messagebox.showinfo("成功", "已用默认信息填充空白账号")

    def _load_saved_accounts(self):
        """加载已保存的账号到输入框"""
        if not self.account_manager:
            return

        # 加载默认信息
        defaults = self.account_manager.get_default_credentials()
        if defaults:
            self.default_phone_var.set(defaults.get("phone", ""))
            self.default_email_var.set(defaults.get("email", ""))
            self.default_password_var.set(defaults.get("default_password", ""))

        # 加载各平台账号
        all_accounts = self.account_manager.get_all_accounts()
        for platform, info in all_accounts.items():
            if platform in self.platform_account_entries:
                entries = self.platform_account_entries[platform]
                entries["username"].delete(0, tk.END)
                entries["username"].insert(0, info.get("username", ""))
                entries["password"].delete(0, tk.END)
                entries["password"].insert(0, info.get("password", ""))

    def _install_dependencies(self):
        """安装自动登录所需的依赖"""
        if messagebox.askyesno("安装依赖", "将安装 selenium 和 webdriver-manager。\n需要联网，是否继续？"):
            try:
                self.status_var.set("正在安装依赖...")
                self.root.update()
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "selenium", "webdriver-manager", "-q"],
                    timeout=120,
                )
                messagebox.showinfo("成功", "依赖安装完成！请重启程序以生效。")
                self.status_var.set("依赖安装完成，请重启程序")
            except Exception as e:
                messagebox.showerror("错误", f"安装失败: {e}\n请手动运行: pip install selenium webdriver-manager")
                self.status_var.set("依赖安装失败")

    # ============================================================
    # 登录日志标签页
    # ============================================================

    def _build_log_tab(self, parent):
        """构建登录日志标签页"""
        self.log_text = scrolledtext.ScrolledText(
            parent,
            wrap=tk.WORD,
            font=("Consolas", 10),
            padx=10,
            pady=10,
            relief="solid",
            borderwidth=1,
            bg="#1e1e2e",
            fg="#cdd6f4",
            insertbackground="#cdd6f4",
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 配置日志文本颜色标签
        self.log_text.tag_configure("info", foreground="#89b4fa")
        self.log_text.tag_configure("success", foreground="#a6e3a1")
        self.log_text.tag_configure("warning", foreground="#f9e2af")
        self.log_text.tag_configure("error", foreground="#f38ba8")
        self.log_text.tag_configure("takeover", foreground="#fab387")
        self.log_text.tag_configure("timestamp", foreground="#6c7086")

        # 底部按钮
        log_btn_frame = ttk.Frame(parent)
        log_btn_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(log_btn_frame, text="清空日志", command=lambda: self.log_text.delete("1.0", tk.END)).pack(side=tk.LEFT)

        self._log("一键投诉 v2.0 - 自动登录系统就绪", "info")

    def _log(self, message: str, level: str = "info"):
        """写入日志"""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.log_text.insert(tk.END, f"{message}\n", level)
        self.log_text.see(tk.END)

    # ============================================================
    # 渠道列表
    # ============================================================

    def _populate_channels(self):
        """填充投诉渠道列表"""
        for cat_data in COMPLAINT_CHANNELS:
            category = cat_data["category"]

            # 分类标题
            cat_frame = ttk.Frame(self.channels_frame)
            cat_frame.pack(fill=tk.X, padx=5, pady=(10, 3))

            ttk.Label(cat_frame, text=f"▎{category}", style="Category.TLabel").pack(
                anchor=tk.W
            )

            # 渠道列表
            for ch in cat_data["channels"]:
                ch_frame = tk.Frame(
                    self.channels_frame, bg="#ffffff", relief="solid", bd=1, padx=10, pady=8
                )
                ch_frame.pack(fill=tk.X, padx=8, pady=2)

                # 复选框
                var = tk.BooleanVar(value=ch["enabled"])
                self.channel_vars[ch["name"]] = {
                    "var": var,
                    "url": ch["url"],
                    "data": ch,
                }

                cb = tk.Checkbutton(
                    ch_frame,
                    text=ch["name"],
                    variable=var,
                    font=("Microsoft YaHei UI", 10),
                    bg="#ffffff",
                    activebackground="#ffffff",
                    command=self._update_selected_count,
                )
                cb.pack(anchor=tk.W)

                # 描述
                desc_label = tk.Label(
                    ch_frame,
                    text=ch["desc"],
                    font=("Microsoft YaHei UI", 9),
                    fg="#64748b",
                    bg="#ffffff",
                    wraplength=350,
                    justify=tk.LEFT,
                )
                desc_label.pack(anchor=tk.W, padx=(22, 0))

                # 电话
                if ch.get("phone"):
                    phone_label = tk.Label(
                        ch_frame,
                        text=f"📞 电话：{ch['phone']}",
                        font=("Microsoft YaHei UI", 9, "bold"),
                        fg="#dc2626",
                        bg="#ffffff",
                    )
                    phone_label.pack(anchor=tk.W, padx=(22, 0))

        self._update_selected_count()

    def _update_selected_count(self):
        """更新选中数量"""
        count = sum(1 for v in self.channel_vars.values() if v["var"].get())
        self.selected_count_var.set(f"已选择 {count} 个平台")

    def _update_char_count(self, event=None):
        """更新字数统计"""
        content = self.text_editor.get("1.0", tk.END).strip()
        self.char_count_var.set(f"字数：{len(content)}")

    def _select_all(self):
        """全选"""
        for v in self.channel_vars.values():
            v["var"].set(True)
        self._update_selected_count()

    def _deselect_all(self):
        """全不选"""
        for v in self.channel_vars.values():
            v["var"].set(False)
        self._update_selected_count()

    def _load_template(self):
        """加载投诉模板"""
        if self.text_editor.get("1.0", tk.END).strip():
            if not messagebox.askyesno("确认", "当前已有内容，加载模板将覆盖现有内容。是否继续？"):
                return
        self.text_editor.delete("1.0", tk.END)
        self.text_editor.insert("1.0", DEFAULT_TEMPLATE)
        self._update_char_count()

    def _clear_content(self):
        """清空内容"""
        if self.text_editor.get("1.0", tk.END).strip():
            if messagebox.askyesno("确认", "确定要清空所有内容吗？"):
                self.text_editor.delete("1.0", tk.END)
                self._update_char_count()

    def _import_from_file(self):
        """从文件导入"""
        filepath = filedialog.askopenfilename(
            title="选择投诉内容文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
        )
        if filepath:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                self.text_editor.delete("1.0", tk.END)
                self.text_editor.insert("1.0", content)
                self._update_char_count()
                messagebox.showinfo("成功", f"已从文件导入内容：\n{filepath}")
            except Exception as e:
                messagebox.showerror("错误", f"读取文件失败：{e}")

    def _save_to_file(self):
        """保存到文件"""
        content = self.text_editor.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("提示", "投诉内容为空，无法保存。")
            return

        filepath = filedialog.asksaveasfilename(
            title="保存投诉内容",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfile=f"投诉内容_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        )
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("成功", f"投诉内容已保存到：\n{filepath}")
            except Exception as e:
                messagebox.showerror("错误", f"保存文件失败：{e}")

    def _save_draft(self):
        """保存草稿"""
        content = self.text_editor.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("提示", "投诉内容为空，无法保存草稿。")
            return
        try:
            draft = {
                "content": content,
                "province": self.province_var.get(),
                "timestamp": datetime.datetime.now().isoformat(),
                "channels": {k: v["var"].get() for k, v in self.channel_vars.items()},
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(draft, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("成功", "草稿已保存。")
        except Exception as e:
            messagebox.showerror("错误", f"保存草稿失败：{e}")

    def _load_draft(self):
        """加载草稿"""
        if not os.path.exists(self.config_file):
            messagebox.showinfo("提示", "没有找到已保存的草稿。")
            return
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                draft = json.load(f)

            if self.text_editor.get("1.0", tk.END).strip():
                if not messagebox.askyesno("确认", "当前已有内容，加载草稿将覆盖现有内容。是否继续？"):
                    return

            self.text_editor.delete("1.0", tk.END)
            self.text_editor.insert("1.0", draft.get("content", ""))
            self.province_var.set(draft.get("province", "请选择省份"))

            saved_channels = draft.get("channels", {})
            for name, info in self.channel_vars.items():
                if name in saved_channels:
                    info["var"].set(saved_channels[name])

            self._update_char_count()
            self._update_selected_count()

            ts = draft.get("timestamp", "未知")
            messagebox.showinfo("成功", f"已加载草稿（保存时间：{ts}）")
        except Exception as e:
            messagebox.showerror("错误", f"加载草稿失败：{e}")

    def _load_config(self):
        """加载配置"""
        pass  # 首次运行无需加载

    def _copy_content(self):
        """仅复制投诉内容到剪贴板"""
        content = self.text_editor.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("提示", "投诉内容为空，请先撰写投诉内容。")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        messagebox.showinfo("成功", "投诉内容已复制到剪贴板！\n在投诉页面中使用 Ctrl+V 粘贴。")

    def _get_province_url(self, channel_data):
        """根据选择的省份获取对应的URL"""
        province = self.province_var.get()
        if province == "请选择省份" or not channel_data.get("sub_channels"):
            return channel_data.get("url", "")
        return channel_data["sub_channels"].get(province, "")

    # ============================================================
    # 传统模式投诉（仅打开网页）
    # ============================================================

    def _submit_complaints(self):
        """传统模式 - 仅打开网页并复制内容"""
        content = self.text_editor.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("提示", "请先撰写投诉内容！")
            return

        # 收集选中的渠道
        selected = []
        for name, info in self.channel_vars.items():
            if info["var"].get():
                ch_data = info["data"]
                url = ch_data.get("url", "")

                if ch_data.get("sub_channels"):
                    url = self._get_province_url(ch_data)

                if url:
                    selected.append({"name": name, "url": url})
                elif ch_data.get("phone"):
                    selected.append({"name": name, "url": "", "phone": ch_data["phone"]})

        if not selected:
            messagebox.showwarning("提示", "请至少选择一个投诉平台！")
            return

        # 检查省份选择
        province = self.province_var.get()
        has_province_channel = any(
            info["data"].get("sub_channels") and info["var"].get()
            for info in self.channel_vars.values()
        )
        if has_province_channel and province == "请选择省份":
            if not messagebox.askyesno(
                "提示",
                "您选择了省级投诉渠道，但未选择省份。\n省级渠道将无法打开对应网址。\n\n是否继续？",
            ):
                return

        # 复制内容到剪贴板
        self.root.clipboard_clear()
        self.root.clipboard_append(content)

        # 统计
        url_channels = [s for s in selected if s.get("url")]
        phone_channels = [s for s in selected if not s.get("url") and s.get("phone")]

        # 确认对话框
        msg = f"即将执行以下操作：\n\n"
        msg += f"✅ 投诉内容已复制到剪贴板\n"
        msg += f"🌐 将打开 {len(url_channels)} 个投诉网站\n"
        if phone_channels:
            msg += f"📞 以下渠道需要电话投诉：\n"
            for ch in phone_channels:
                msg += f"   • {ch['name']}：{ch.get('phone', '')}\n"
        msg += f"\n在每个投诉页面中使用 Ctrl+V 粘贴投诉内容。\n\n确认开始？"

        if not messagebox.askyesno("确认投诉", msg):
            return

        # 打开所有投诉网站
        opened = 0
        failed = []
        for ch in url_channels:
            try:
                webbrowser.open(ch["url"])
                opened += 1
            except Exception as e:
                failed.append(f"{ch['name']}: {e}")

        # 保存投诉记录
        self._save_history(content, selected, province)

        # 结果提示
        result_msg = f"操作完成！\n\n"
        result_msg += f"📋 投诉内容已复制到剪贴板\n"
        result_msg += f"🌐 已打开 {opened} 个投诉网站\n"
        if failed:
            result_msg += f"\n⚠ 以下网站打开失败：\n"
            for f_msg in failed:
                result_msg += f"   • {f_msg}\n"
        if phone_channels:
            result_msg += f"\n📞 请另外拨打以下电话进行投诉：\n"
            for ch in phone_channels:
                result_msg += f"   • {ch['name']}：{ch.get('phone', '')}\n"
        result_msg += f"\n请在每个投诉页面中粘贴（Ctrl+V）投诉内容并提交。"

        messagebox.showinfo("投诉结果", result_msg)

    # ============================================================
    # 自动登录模式投诉
    # ============================================================

    def _submit_with_auto_login(self):
        """自动登录模式 - 启动浏览器自动登录后打开投诉页面"""
        if not BROWSER_ENGINE_AVAILABLE or not SELENIUM_AVAILABLE:
            result = messagebox.askyesno(
                "自动登录不可用",
                "自动登录功能需要安装 selenium 和 webdriver-manager。\n\n"
                "是否切换到传统模式（仅打开网页）？\n\n"
                "要安装依赖，请到【账号管理】标签页点击【安装自动登录依赖】。",
            )
            if result:
                self._submit_complaints()
            return

        if not ADAPTERS_AVAILABLE:
            messagebox.showerror("错误", "平台适配器模块未加载，请检查 platform_adapters.py 文件。")
            return

        content = self.text_editor.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("提示", "请先撰写投诉内容！")
            return

        # 收集选中的渠道
        selected = []
        for name, info in self.channel_vars.items():
            if info["var"].get():
                ch_data = info["data"]
                url = ch_data.get("url", "")
                if ch_data.get("sub_channels"):
                    url = self._get_province_url(ch_data)
                selected.append({"name": name, "url": url, "data": ch_data})

        if not selected:
            messagebox.showwarning("提示", "请至少选择一个投诉平台！")
            return

        # 先保存所有账号
        self._save_all_accounts_silent()

        # 复制内容到剪贴板
        self.root.clipboard_clear()
        self.root.clipboard_append(content)

        # 确认
        msg = f"即将启动自动登录模式：\n\n"
        msg += f"📋 投诉内容已复制到剪贴板\n"
        msg += f"🤖 将自动登录 {len(selected)} 个投诉平台\n"
        msg += f"⚠ 遇到验证码等问题时会弹窗提示您手动操作\n\n"
        msg += f"确认开始？"

        if not messagebox.askyesno("自动登录投诉", msg):
            return

        # 在后台线程中执行自动登录
        self._auto_login_running = True
        self.status_var.set("正在启动浏览器...")
        self._log("=" * 50, "info")
        self._log("开始自动登录投诉流程", "info")

        thread = threading.Thread(
            target=self._auto_login_worker,
            args=(selected, content),
            daemon=True,
        )
        thread.start()

    def _save_all_accounts_silent(self):
        """静默保存所有账号"""
        if not self.account_manager:
            return
        for platform, entries in self.platform_account_entries.items():
            username = entries["username"].get().strip()
            password = entries["password"].get().strip()
            if username and password:
                defaults = self.account_manager.get_default_credentials() or {}
                self.account_manager.save_account(
                    platform, username, password,
                    phone=defaults.get("phone", ""),
                    email=defaults.get("email", ""),
                )

    def _auto_login_worker(self, selected_channels, content):
        """自动登录工作线程"""
        try:
            # 启动浏览器
            self._update_ui_status("正在启动浏览器...")
            self._log("正在启动 Chrome 浏览器...", "info")

            engine = BrowserEngine(headless=False, user_data_dir=self.browser_data_dir)
            engine.set_status_callback(self._browser_status_callback)

            if not engine.start():
                self._log("浏览器启动失败！请检查 Chrome 是否已安装。", "error")
                self._update_ui_status("浏览器启动失败")
                self.root.after(0, lambda: messagebox.showerror("错误", "浏览器启动失败，请检查 Chrome 是否已安装。"))
                return

            self.browser_engine = engine
            self._log("浏览器启动成功", "success")

            # 逐个处理选中的平台
            success_count = 0
            manual_count = 0
            fail_count = 0
            phone_channels = []

            for i, ch_info in enumerate(selected_channels):
                if not self._auto_login_running:
                    self._log("用户取消了操作", "warning")
                    break

                name = ch_info["name"]
                url = ch_info.get("url", "")
                ch_data = ch_info.get("data", {})

                self._log(f"\n--- [{i+1}/{len(selected_channels)}] {name} ---", "info")
                self._update_ui_status(f"正在处理 ({i+1}/{len(selected_channels)}): {name}")

                # 纯电话渠道
                if ch_data.get("phone") and not url:
                    phone_channels.append({"name": name, "phone": ch_data["phone"]})
                    self._log(f"  电话渠道: {ch_data['phone']}，跳过自动登录", "info")
                    continue

                # 获取适配器
                adapter = get_adapter(name, engine)

                # 检查是否有保存的账号
                account = None
                if self.account_manager:
                    account = self.account_manager.get_account(name)

                if adapter.NEEDS_LOGIN:
                    if account:
                        # 尝试自动登录
                        self._log(f"  使用保存的账号尝试登录...", "info")
                        result = adapter.auto_login(account["username"], account["password"])

                        if result.is_success():
                            self._log(f"  ✅ {result.message}", "success")
                            self._update_platform_status(name, "已登录", "#059669")
                            success_count += 1
                        elif result.need_takeover:
                            # 需要手动接管
                            self._log(f"  ⚠ {result.message}", "takeover")
                            self._update_platform_status(name, "需手动操作", "#d97706")
                            engine.enter_takeover_mode(result.message)

                            # 在主线程弹出提示
                            self.root.after(0, lambda n=name, m=result.message: self._show_takeover_dialog(n, m))

                            # 等待用户完成手动操作
                            completed = engine.wait_for_takeover_complete(timeout=300)
                            if completed:
                                self._log(f"  ✅ 用户已完成手动操作", "success")
                                self._update_platform_status(name, "已登录", "#059669")
                                success_count += 1
                            else:
                                self._log(f"  ⚠ 手动操作超时", "warning")
                                manual_count += 1
                        else:
                            self._log(f"  ❌ {result.message}", "error")
                            self._update_platform_status(name, "登录失败", "#dc2626")
                            fail_count += 1
                    else:
                        # 没有保存的账号，尝试注册或提示手动登录
                        defaults = self.account_manager.get_default_credentials() if self.account_manager else None
                        if defaults and defaults.get("phone"):
                            self._log(f"  未保存账号，尝试自动注册...", "info")
                            result = adapter.auto_register(
                                defaults["phone"],
                                defaults.get("email", ""),
                                defaults.get("default_password", ""),
                            )
                            if result.need_takeover:
                                self._log(f"  ⚠ {result.message}", "takeover")
                                engine.enter_takeover_mode(result.message)
                                self.root.after(0, lambda n=name, m=result.message: self._show_takeover_dialog(n, m))
                                completed = engine.wait_for_takeover_complete(timeout=300)
                                if completed:
                                    self._log(f"  ✅ 用户已完成手动操作", "success")
                                    success_count += 1
                                else:
                                    manual_count += 1
                            elif result.is_success():
                                success_count += 1
                            else:
                                fail_count += 1
                        else:
                            # 直接打开页面，提示手动登录
                            self._log(f"  未保存账号，打开页面供手动登录...", "warning")
                            if url:
                                engine.navigate(url, wait_seconds=2)
                                engine.enter_takeover_mode(f"请在浏览器中手动登录 {name}")
                                self.root.after(0, lambda n=name: self._show_takeover_dialog(
                                    n, f"请在浏览器中手动登录 {n}，完成后点击【继续】"))
                                completed = engine.wait_for_takeover_complete(timeout=300)
                                if completed:
                                    success_count += 1
                                else:
                                    manual_count += 1
                else:
                    # 不需要登录的平台，直接打开
                    self._log(f"  该平台无需登录", "info")
                    if url:
                        engine.navigate(url, wait_seconds=2)
                    success_count += 1

                # 打开投诉页面（在新标签页中）
                if url and not ch_data.get("phone"):
                    try:
                        engine.switch_to_new_tab(url)
                        self._log(f"  已打开投诉页面: {url}", "info")
                    except Exception:
                        self._log(f"  打开投诉页面失败", "warning")

            # 完成
            self._log(f"\n{'=' * 50}", "info")
            self._log(f"自动登录流程完成", "info")
            self._log(f"  成功: {success_count}  手动: {manual_count}  失败: {fail_count}", "info")

            if phone_channels:
                self._log(f"\n📞 以下渠道需要电话投诉:", "warning")
                for ch in phone_channels:
                    self._log(f"  • {ch['name']}: {ch['phone']}", "warning")

            self._update_ui_status(f"完成 - 成功:{success_count} 手动:{manual_count} 失败:{fail_count}")

            # 保存投诉记录
            province = self.province_var.get()
            self._save_history(content, selected_channels, province)

            # 结果提示
            self.root.after(0, lambda: messagebox.showinfo(
                "自动登录完成",
                f"自动登录流程已完成！\n\n"
                f"✅ 成功登录: {success_count} 个平台\n"
                f"⚠ 手动操作: {manual_count} 个平台\n"
                f"❌ 登录失败: {fail_count} 个平台\n\n"
                f"📋 投诉内容已在剪贴板中\n"
                f"请在各投诉页面中粘贴（Ctrl+V）内容并提交。\n\n"
                f"浏览器窗口保持打开，您可以继续操作。"
            ))

        except Exception as e:
            self._log(f"自动登录流程异常: {e}", "error")
            self._update_ui_status("自动登录异常")
            self.root.after(0, lambda: messagebox.showerror("错误", f"自动登录流程异常: {e}"))
        finally:
            self._auto_login_running = False

    def _browser_status_callback(self, message: str, level: str):
        """浏览器引擎状态回调"""
        self.root.after(0, lambda: self._log(message, level))

    def _update_ui_status(self, text: str):
        """更新 UI 状态栏"""
        self.root.after(0, lambda: self.status_var.set(text))

    def _update_platform_status(self, platform: str, status: str, color: str):
        """更新平台登录状态"""
        def _update():
            if platform in self.platform_account_entries:
                self.platform_account_entries[platform]["status"].config(text=status, fg=color)
        self.root.after(0, _update)

    def _show_takeover_dialog(self, platform_name: str, message: str):
        """显示手动接管对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"需要手动操作 - {platform_name}")
        dialog.geometry("500x250")
        dialog.transient(self.root)
        dialog.grab_set()

        # 图标和标题
        title_frame = ttk.Frame(dialog)
        title_frame.pack(fill=tk.X, padx=20, pady=(20, 10))
        tk.Label(title_frame, text="⚠", font=("", 32)).pack(side=tk.LEFT)
        tk.Label(title_frame, text=f"手动接管: {platform_name}",
                 font=("Microsoft YaHei UI", 14, "bold")).pack(side=tk.LEFT, padx=10)

        # 消息
        msg_frame = ttk.Frame(dialog)
        msg_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        tk.Label(msg_frame, text=message, font=("Microsoft YaHei UI", 11),
                 wraplength=450, justify=tk.LEFT).pack(anchor=tk.W)

        tk.Label(msg_frame, text="\n请在浏览器窗口中完成操作，然后点击下方按钮继续。",
                 font=("Microsoft YaHei UI", 10), fg="#64748b",
                 wraplength=450, justify=tk.LEFT).pack(anchor=tk.W)

        # 按钮
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=20, pady=20)

        def on_continue():
            if self.browser_engine:
                self.browser_engine.exit_takeover_mode()
            dialog.destroy()

        def on_skip():
            if self.browser_engine:
                self.browser_engine.exit_takeover_mode()
            dialog.destroy()

        tk.Button(btn_frame, text="✅ 已完成，继续", font=("Microsoft YaHei UI", 12, "bold"),
                  bg="#059669", fg="#ffffff", padx=20, pady=8,
                  command=on_continue).pack(side=tk.RIGHT, padx=5)

        tk.Button(btn_frame, text="⏭ 跳过此平台", font=("Microsoft YaHei UI", 11),
                  bg="#6b7280", fg="#ffffff", padx=15, pady=8,
                  command=on_skip).pack(side=tk.RIGHT, padx=5)

    # ============================================================
    # 投诉历史
    # ============================================================

    def _save_history(self, content, channels, province):
        """保存投诉历史记录"""
        try:
            history = []
            if os.path.exists(self.history_file):
                with open(self.history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)

            record = {
                "timestamp": datetime.datetime.now().isoformat(),
                "province": province,
                "content_preview": content[:100] + "..." if len(content) > 100 else content,
                "channels": [ch["name"] if isinstance(ch, dict) else ch for ch in channels],
                "channel_count": len(channels),
            }
            history.append(record)

            # 只保留最近50条记录
            history = history[-50:]

            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # 历史记录保存失败不影响主功能

    def on_closing(self):
        """程序关闭时清理资源"""
        self._auto_login_running = False
        if self.browser_engine:
            try:
                self.browser_engine.stop()
            except Exception:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()

    # 设置DPI感知（Windows）
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = ComplaintApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
