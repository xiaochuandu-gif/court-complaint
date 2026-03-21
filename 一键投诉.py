#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键投诉法院不立案不下裁定
============================
针对法院立案庭不立案且不下不予立案裁定的问题，
一键自动向多个受理法官违法违纪的平台进行投诉。

使用方法：
1. 在左侧文本框撰写投诉内容
2. 在右侧勾选要投诉的平台
3. 点击"一键投诉"按钮
4. 程序会自动打开所有选中平台的投诉页面，并将投诉内容复制到剪贴板

运行环境：Python 3.6+（仅使用标准库，无需额外安装）
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import webbrowser
import json
import os
import datetime

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
    """一键投诉法院不立案不下裁定 - 主应用类"""

    def __init__(self, root):
        self.root = root
        self.root.title("一键投诉 - 法院不立案不下裁定投诉工具")
        self.root.geometry("1200x800")
        self.root.minsize(900, 600)

        # 配置文件路径
        self.config_dir = os.path.join(os.path.expanduser("~"), ".court_complaint")
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.history_file = os.path.join(self.config_dir, "history.json")

        # 确保配置目录存在
        os.makedirs(self.config_dir, exist_ok=True)

        # 渠道选择状态
        self.channel_vars = {}
        # 省份选择
        self.province_var = tk.StringVar(value="请选择省份")

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

    def _build_ui(self):
        """构建主界面"""
        # 顶部标题栏
        header = ttk.Frame(self.root)
        header.pack(fill=tk.X, padx=20, pady=(15, 5))

        ttk.Label(header, text="⚖ 一键投诉", style="Title.TLabel").pack(side=tk.LEFT)
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
            """使用说明
═══════════════════════════════════════

本工具用于针对法院立案庭"不立案且不下不予立案裁定"的违法行为，一键向多个监督平台提交投诉。

【操作步骤】

第一步：选择省份
    在顶部下拉框选择您所在的省份，程序会自动匹配省人大信访和省信访局的网址。

第二步：撰写投诉内容
    在"投诉内容"标签页中撰写您的投诉材料。
    可以点击"加载模板"按钮使用预设的投诉模板，然后修改其中的具体信息。

第三步：选择投诉平台
    在右侧勾选您要投诉的平台。建议全选以最大化投诉效果。

第四步：一键投诉
    点击底部红色的"一键投诉"按钮，程序将：
    ① 自动将投诉内容复制到系统剪贴板
    ② 依次在浏览器中打开所有选中平台的投诉页面
    ③ 您只需在每个页面中粘贴（Ctrl+V）投诉内容并提交

【法律依据】

• 《民事诉讼法》第126条：法院应在7日内立案或作出不予立案裁定
• 《最高人民法院关于人民法院登记立案若干问题的规定》
• 《人民法院工作人员处分条例》

【投诉渠道说明】

• 法院系统：直接向法院内部监督部门投诉
• 检察院：对法院有法律监督权
• 纪检监察：监督法官违纪违法行为
• 人大信访：人大对法院有监督权
• 信访局：国家信访系统
• 政法委：政法干警违纪违法举报
• 其他渠道：领导留言板、国务院督查等

【注意事项】

1. 投诉内容请实事求是，如实反映情况
2. 建议保留好起诉材料的递交凭证
3. 投诉后请关注各平台的回复和处理进度
4. 部分平台需要实名注册后才能提交投诉
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
        bottom_frame.pack(fill=tk.X, padx=20, pady=(5, 15))

        # 选中数量提示（必须在_populate_channels之前定义）
        self.selected_count_var = tk.StringVar(value="已选择 0 个平台")
        ttk.Label(bottom_frame, textvariable=self.selected_count_var).pack(side=tk.LEFT)

        # 填充渠道列表
        self._populate_channels()

        # 一键投诉按钮
        submit_btn = tk.Button(
            bottom_frame,
            text="🚀 一键投诉",
            font=("Microsoft YaHei UI", 14, "bold"),
            bg="#dc2626",
            fg="#ffffff",
            activebackground="#b91c1c",
            activeforeground="#ffffff",
            relief="flat",
            padx=30,
            pady=8,
            cursor="hand2",
            command=self._submit_complaints,
        )
        submit_btn.pack(side=tk.RIGHT)

        # 复制内容按钮
        copy_btn = tk.Button(
            bottom_frame,
            text="📋 仅复制内容",
            font=("Microsoft YaHei UI", 11),
            bg="#475569",
            fg="#ffffff",
            activebackground="#334155",
            activeforeground="#ffffff",
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2",
            command=self._copy_content,
        )
        copy_btn.pack(side=tk.RIGHT, padx=(0, 10))

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

    def _submit_complaints(self):
        """一键投诉 - 核心功能"""
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

                # 如果有子渠道（省级），获取省份对应URL
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
                "channels": [ch["name"] for ch in channels],
                "channel_count": len(channels),
            }
            history.append(record)

            # 只保留最近50条记录
            history = history[-50:]

            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # 历史记录保存失败不影响主功能


def main():
    root = tk.Tk()

    # 设置DPI感知（Windows）
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = ComplaintApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
