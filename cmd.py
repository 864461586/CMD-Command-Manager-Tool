import os
import sys
import subprocess
import threading
import datetime
import locale
import re
import webbrowser
from tkinter import filedialog
import ssl
import urllib.request
import urllib.error

import customtkinter as ctk
import tkinter as tk
README_TEXT = """
================================================================================
                      CMD 指令管理工具 (CMD Command Manager Tool)
                                  使用说明文档
================================================================================

版本：v1.0.0
作者：张广宁 grant.zhangz@goertek.com
日期：2026-02-28
平台：Windows
依赖：Python 3.8+, customtkinter

--------------------------------------------------------------------------------
一、软件简介
--------------------------------------------------------------------------------
这是一个基于 Python 和 CustomTkinter 开发的现代化命令行指令管理工具。
它专为简化重复性命令执行而设计，支持命令的添加、编辑、删除、拖拽排序、
批量导入导出，并提供实时终端输出、日志保存、智能搜索等功能。

适用场景：ADB 调试、系统维护、自动化脚本执行、批量任务处理等。

--------------------------------------------------------------------------------
二、主要功能
--------------------------------------------------------------------------------
1. 指令管理
   - 轻松添加、编辑、删除自定义命令。
   - 支持多行命令输入（适合编写简单脚本）。

2. 拖拽排序
   - 鼠标左键按住左侧命令按钮上下拖动，即可自由调整执行顺序。
   - 顺序调整后自动保存。

3. 实时执行与监控
   - 点击按钮立即执行命令。
   - 右侧终端窗口实时显示输出，不同次执行使用不同颜色区分。
   - 自动高亮错误关键词（如 error, fail, exception 等）。

4. 智能交互
   - 工具提示：鼠标悬停按钮查看完整命令。
   - 快捷键 Ctrl+F：唤起搜索框，查找终端输出内容。
   - 快捷键 Ctrl+C：
     * 若有选中文本 -> 复制文本。
     * 若无选中文本 -> 强制终止所有正在运行的命令。

5. 数据管理
   - 自动保存：指令列表自动保存至本地 adb_commands.txt。
   - 批量导入：支持导入符合格式的 .txt 文件，自动跳过重名项。
   - 导出分享：一键导出当前所有指令清单。
   - 日志保存：将终端输出保存为 .log 文件。

--------------------------------------------------------------------------------
三、详细使用指南
--------------------------------------------------------------------------------
1. 添加指令
   - 点击左上角 "+ 添加指令" 按钮。
   - 输入"指令名称"（按钮显示文字）和"命令内容"（支持多行）。
   - 点击"确定”保存。

2. 执行指令
   - 左键单击左侧列表中的命令按钮。
   - 观察右侧终端窗口的实时输出。
   - 执行期间按钮会显示"⏳ 执行中..."并暂时禁用。

3. 编辑/删除/复制
   - 右键单击命令按钮，弹出菜单：
     * 编辑：修改名称或命令。
     * 删除：移除该指令。
     * 复制命令：将名称和内容复制到剪贴板。

4. 调整顺序
   - 按住鼠标左键在按钮上拖动，将其移动到新位置后释放。

5. 终端操作技巧
   - 复制内容：选中文字后按 Ctrl+C。
   - 终止任务：未选中文字时按 Ctrl+C，可杀死所有后台运行进程。
   - 搜索内容：按 Ctrl+F，输入关键词，使用"查找下一个/上一个”定位。
   - 清屏/保存：点击右上角的"清除”或"保存”按钮。

6. 批量导入格式
   - 点击"批量导入”，选择 .txt 文件。
   - 文件格式示例：
     [指令名称]
     命令内容行1
     命令内容行2

     [下一个指令名称]
     命令内容

   - 注意：方括号内为名称，下方直到下一个方括号前的内容为命令，
     空行用于分隔（程序会自动处理首尾空行）。

--------------------------------------------------------------------------------
四、联系方式与致谢
--------------------------------------------------------------------------------
如有问题或建议，请联系：grant.zhangz@goertek.com

致谢：
- CustomTkinter 团队提供的现代化 UI 库
- 所有使用该工具的开发者

================================================================================
                           祝您使用愉快！
================================================================================
"""

# === 全局配置 ===
VERSION = "V1.0.0"

# 【重要】请在此处填入你存放最新版本号的文本文件 URL (内容只需一行，如: v1.0.0)
# 示例 (GitHub Raw): "https://raw.githubusercontent.com/yourname/yourrepo/main/version.txt"
# 如果没有地址，留空字符串即可，功能会自动禁用
UPDATE_CHECK_URL = "https://gitee.com/sdzgn/cmd-command-manager-tool/raw/master/version.txt"

# 下载页面地址 (当发现新版本时跳转的地址)
DOWNLOAD_URL = "https://gitee.com/sdzgn/cmd-command-manager-tool/version.txt"

ENCODING = locale.getpreferredencoding()

COLOR_CYCLE = [
    "#FFB6C1", "#87CEFA", "#98FB98", "#FFFFE0", "#DDA0DD",
    "#FFA07A", "#20B2AA", "#FFD700", "#CD5C5C", "#9ACD32"
]

# 获取程序所在目录（支持 PyInstaller 打包）
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

COMMANDS_FILE = os.path.join(APP_DIR, "adb_commands.txt")


# === 工具函数：命令序列化与解析 ===
def serialize_commands(commands):
    lines = []
    for name, cmd in commands:
        lines.append(f"[{name}]")
        lines.append(cmd)
        lines.append("")
    return "\n".join(lines)


def parse_commands_from_text(text):
    lines = text.splitlines()
    commands = []
    current_name = None
    current_lines = []

    for line in lines:
        stripped = line.rstrip('\r')
        if stripped.startswith("[") and stripped.endswith("]"):
            if current_name is not None:
                while current_lines and current_lines[0].strip() == "":
                    current_lines.pop(0)
                while current_lines and current_lines[-1].strip() == "":
                    current_lines.pop()
                cmd = "\n".join(current_lines)
                if cmd.strip():
                    commands.append((current_name, cmd))
            current_name = stripped[1:-1].strip()
            current_lines = []
        elif current_name is not None:
            current_lines.append(stripped)

    if current_name is not None:
        while current_lines and current_lines[0].strip() == "":
            current_lines.pop(0)
        while current_lines and current_lines[-1].strip() == "":
            current_lines.pop()
        cmd = "\n".join(current_lines)
        if cmd.strip():
            commands.append((current_name, cmd))

    return commands


# === ToolTip 类 ===
class ToolTip:
    def __init__(self, widget, text="", delay=500, wraplength=300):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.wraplength = wraplength
        self.tipwindow = None
        self.id = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.delay, self.showtip)

    def unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
        self.id = None

    def showtip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = ctk.CTkLabel(
            tw,
            text=self.text,
            justify="left",
            wraplength=self.wraplength,
            fg_color="#333333",
            text_color="white",
            corner_radius=6,
            font=("Consolas", 10)
        )
        label.pack(ipadx=8, ipady=6)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


# === 实时执行命令 ===
def run_command_realtime(command, output_callback, tag, on_complete=None, process_list=None):
    def target():
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding=ENCODING,
                errors='replace'
            )
            if process_list is not None:
                process_list.append(process)

            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            output_callback(f"[{timestamp}] ▶ 执行命令:\n{command}\n\n", tag)

            for line in iter(process.stdout.readline, ""):
                if line:
                    output_callback(line.rstrip() + "\n", tag)
            process.stdout.close()
            process.wait()
            output_callback("\n✅ 完成。\n\n", tag)
        except Exception as e:
            output_callback(f"\n💥 异常：{e}\n\n", tag)
        finally:
            if process_list is not None and process in process_list:
                process_list.remove(process)
            if on_complete:
                on_complete()

    threading.Thread(target=target, daemon=True).start()


# === 添加/编辑对话框 ===
class CommandDialog(ctk.CTkToplevel):
    def __init__(self, parent, title="添加指令", name="", command="", callback=None):
        super().__init__(parent)
        self.title(title)
        self.callback = callback
        self.transient(parent)
        self.grab_set()

        width, height = 500, 300
        x = parent.winfo_x() + (parent.winfo_width() - width) // 2
        y = parent.winfo_y() + (parent.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

        self.name_var = ctk.StringVar(value=name)

        ctk.CTkLabel(self, text="指令名称:").pack(pady=(10, 0))
        self.name_entry = ctk.CTkEntry(self, textvariable=self.name_var, width=450)
        self.name_entry.pack(pady=5)

        ctk.CTkLabel(self, text="命令（支持多行）:").pack()
        self.cmd_textbox = ctk.CTkTextbox(self, width=450, height=120, font=("Consolas", 11))
        self.cmd_textbox.pack(pady=5)
        if command:
            self.cmd_textbox.insert("0.0", command)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="确定", command=self.on_ok).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="取消", command=self.destroy).pack(side="left", padx=5)

        self.name_entry.focus()

    def on_ok(self):
        name = self.name_var.get().strip()
        cmd = self.cmd_textbox.get("0.0", "end").strip()
        if name and cmd and self.callback:
            self.callback(name, cmd)
        self.destroy()


# === 主应用 ===
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 1. 设置窗口图标
        try:
            if getattr(sys, 'frozen', False):
                icon_path = os.path.join(sys._MEIPASS, "app_icon.ico")
            else:
                icon_path = "app_icon.ico"

            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception as e:
            print(f"图标加载失败：{e}")

        self.title(f"CMD Command Manager Tool {VERSION}")
        self.geometry("1250x600")

        self.commands = []
        self.button_widgets = []
        self.color_index = 0
        self._current_toast = None
        self.active_processes = []

        # 搜索相关状态
        self.search_window = None
        self.search_term = ""
        self.search_matches = []
        self.current_match_index = -1

        # 拖拽状态
        self.dragging = False
        self.drag_start_y = None
        self.drag_threshold = 5

        self.load_commands_from_file()
        self.create_ui()

        # 启动后延迟 1 秒自动检查更新
        if UPDATE_CHECK_URL:
            self.after(1000, lambda: threading.Thread(target=self.check_for_updates, daemon=True).start())

    def create_ui(self):
        main_frame = ctk.CTkFrame(self, corner_radius=20, border_width=2, border_color="gray")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # --- 底部区域：版本信息 | 邮箱 | 帮助文档 | 检查更新 ---
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(side="bottom", pady=(0, 10))

        # 左侧：版本和邮箱
        info_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True)

        label_prefix = ctk.CTkLabel(
            info_frame,
            text=f"版本 : {VERSION} | 张广宁 ",
            font=("Arial", 16, "bold"),  # 字体变大并加粗
            text_color="gray",  # 改为蓝色 (十六进制)
            anchor="w"  # 文字左对齐
        )
        label_prefix.pack(side="left")

        self.email_label = ctk.CTkLabel(
            info_frame,
            text="grant.zhangz@goertek.com",
            font=("Arial", 16, "underline"),
            text_color="#1f6aa5",
            cursor="hand2"
        )
        self.email_label.pack(side="left")
        self.email_label.bind("<Button-1>", lambda e: self.copy_email("grant.zhangz@goertek.com"))
        self.email_label.bind("<Enter>", lambda e: self.email_label.configure(text_color="#144870"))
        self.email_label.bind("<Leave>", lambda e: self.email_label.configure(text_color="#1f6aa5"))

        # 右侧：操作按钮组 (检查更新 & 帮助文档)
        action_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        action_frame.pack(side="right")

        # 帮助文档按钮
        ctk.CTkButton(
            action_frame,
            text="📖 帮助文档",
            width=90,
            height=28,
            font=("Arial", 12),
            fg_color="transparent",
            border_width=1,
            border_color="#cccccc",
            text_color="#555555",
            hover_color="#f0f0f0",
            command=self.show_readme_window
        ).pack(side="right", padx=(10, 0))

        # # 检查更新按钮
        self.update_btn = ctk.CTkButton(
            action_frame,
            text="🔄 检查更新",
            width=90,
            height=28,
            font=("Arial", 12),
            fg_color="transparent",
            border_width=1,
            border_color="#cccccc",
            text_color="#555555",
            hover_color="#f0f0f0",
            command=lambda: threading.Thread(target=self.check_for_updates, daemon=True).start()
        )
        self.update_btn.pack(side="right", padx=(10, 0))

        # --- 左侧容器 (仅保留添加/导入) ---
        left_container = ctk.CTkFrame(main_frame, fg_color="transparent")
        left_container.pack(side="left", fill="y", padx=(10, 5), pady=10)

        top_btn_frame = ctk.CTkFrame(left_container, fg_color="transparent")
        top_btn_frame.pack(pady=(0, 10), padx=10, fill="x")

        # 第一排：添加 | 导入
        btn_row1 = ctk.CTkFrame(top_btn_frame, fg_color="transparent")
        btn_row1.pack(fill="x")

        ctk.CTkButton(
            btn_row1,
            text="+ 添加指令",
            corner_radius=10,
            fg_color="green",
            hover_color="#2E8B57",
            command=self.open_add_dialog
        ).pack(side="left", fill="x", expand=True, padx=(0, 3))

        ctk.CTkButton(
            btn_row1,
            text="📥 批量导入",
            corner_radius=10,
            fg_color="#1f6aa5",
            hover_color="#144870",
            command=self.import_commands
        ).pack(side="left", fill="x", expand=True, padx=(3, 0))

        # 左侧列表区域
        self.left_frame = ctk.CTkScrollableFrame(
            left_container,
            width=180,
            corner_radius=15,
            fg_color="#f0f0f0",
            border_width=2,
            border_color="gray"
        )
        self.left_frame.pack(fill="both", expand=True)
        self.refresh_buttons()

        # --- 右侧终端区域 ---
        right_frame = ctk.CTkFrame(
            main_frame,
            corner_radius=15,
            fg_color="white",
            border_width=2,
            border_color="gray"
        )
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        label = ctk.CTkLabel(right_frame, text="终端输出", font=("Consolas", 14, "bold"), text_color="black")
        label.pack(pady=(5, 0))

        self.output_textbox = ctk.CTkTextbox(
            right_frame,
            wrap="none",
            font=("Consolas", 12),
            text_color="white",
            fg_color="#2b2b2b"
        )
        self.output_textbox.pack(fill="both", expand=True, padx=10, pady=10)
        self.output_textbox.configure(state="disabled")

        self.output_textbox.bind("<Control-c>", self.handle_ctrl_c)
        self.output_textbox.bind("<Control-f>", self.show_search_dialog)

        self.output_textbox.tag_config("alert", foreground="#FF0000", background="#FFF0F0")

        btn_clear = ctk.CTkButton(right_frame, text="🗑️ 清除", width=60, height=24, command=self.clear_output)
        btn_save = ctk.CTkButton(right_frame, text="💾 保存", width=60, height=24, command=self.save_log)
        btn_export = ctk.CTkButton(right_frame, text="📤 导出脚本", width=80, height=24, command=self.export_script)

        btn_clear.place(relx=1.0, rely=0.0, x=-70, y=10, anchor="ne")
        btn_save.place(relx=1.0, rely=0.0, x=-5, y=10, anchor="ne")
        btn_export.place(relx=1.0, rely=0.0, x=-155, y=10, anchor="ne")

    # === 复制邮箱 ===
    def copy_email(self, email_address):
        try:
            self.clipboard_clear()
            self.clipboard_append(email_address)
            self.update()
            self.show_toast(f"✅ 已复制邮箱:\n{email_address}", duration=2000)
            original_color = self.email_label.cget("text_color")
            self.email_label.configure(text_color="#2E8B57")
            self.after(500, lambda: self.email_label.configure(text_color=original_color))
        except Exception as e:
            self.show_toast(f"❌ 复制失败：{e}")

    # === 检查更新逻辑 ===
    def check_for_updates(self):
        if not UPDATE_CHECK_URL:
            return
        try:
            self.after(0, lambda: self.update_btn.configure(text="⏳ 检查中...", state="disabled"))

            # 创建忽略 SSL 的 Context
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            MY_GITEE_COOKIE = "oschina_new_user=false; sensorsdata2015jssdkchannel=%7B%22prop%22%3A%7B%22_sa_channel_landing_url%22%3A%22%22%7D%7D; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%22196e37504747f8-0eea285058c6568-4c657b58-1638720-196e37504754db%22%2C%22first_id%22%3A%22%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E5%BC%95%E8%8D%90%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC%22%2C%22%24latest_referrer%22%3A%22https%3A%2F%2Fwww.oschina.net%2Fp%2Fgithub%3Fhmsr%3Daladdin1e1%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTk2ZTM3NTA0NzQ3ZjgtMGVlYTI4NTA1OGM2NTY4LTRjNjU3YjU4LTE2Mzg3MjAtMTk2ZTM3NTA0NzU0ZGIifQ%3D%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%22%2C%22value%22%3A%22%22%7D%2C%22%24device_id%22%3A%22196e37504747f8-0eea285058c6568-4c657b58-1638720-196e37504754db%22%7D; yp_riddler_id=c19737c8-2159-4735-9d3c-fcca6c39e94a; abymg_id=1_69A0BBCD93CDA7D441260119F461F8E7ADAE46ECF9C1A0D2C9EC260AC783EA08; BEC=4431548549a19240b277aa1ec69b0837; user_locale=zh-CN; Hm_lvt_24f17767262929947cc3631f99bfd274=1772282713; HMACCOUNT=F9032F78B8685296; user_return_to_0=%2F%3Fchannel_utm_content%3DGitee%2520%257C%2520DevOps%2520%25E7%25A0%2594%25E5%258F%2591%25E6%2595%2588%25E8%2583%25BD%25E5%25B9%25B3%25E5%258F%25B0%26channel_utm_medium%3Dsem%26channel_link_type%3Dweb%26channel_utm_source%3D%25E7%2599%25BE%25E5%25BA%25A6%26sat_cf%3D2%26channel_utm_campaign%3D%25E5%2593%2581%25E4%25B8%2593%26channel_utm_term%3D%25E4%25B8%25BB%25E6%25A0%2587%25E9%25A2%25981%26_channel_track_key%3DWagVxbYD%26link_version%3D1%26wl_src%3Dbaidu; tz=Asia%2FShanghai; remember_user_token=BAhbCFsGaQMCiItJIiIkMmEkMTAkd2NwMDNuTFNwbGU1TjJDRElxQ0MxdQY6BkVUSSIXMTc3MjI4Mjg4MC40NDY0NDgzBjsARg%3D%3D--d2bc8995925c26fecd00cd4e3e746afc9e5d5c61; gitee_user=true; csrf_token=9nZeTMORYnb0vC%2FEr%2F%2FFxNZ6xPfcXF9QjPjsdcV2KLwRtPd4sLXMpgcoCFytaAIiSJkSFbIhXg3v0rIs%2Bzv4VA%3D%3D; remote_way=ssh; nox_jst_v1=2.0_d8fb_9kaiCMKriwvYzMuY+dqjUUgxvb2xvvqtrBjlY6Lzivsu1S12ylGkJ9BrItVdvw40DfD9AgnVNje7zNvNoG7nFHrF9BTQ7YuRihWLs2bmLaq3QTUIpXueaDORvjwY7EcM52yKoKhlAVMo2lir79vcb2u1xF+HPBxk/pq1uep5FMPkPs93Pl0lYlJ9ofaPWJ4jPKx9AYYen55wgH/o8jVO9/bCKOkZWQub3PX64hOSbK6EaENK+zy093FXH/vLjBGR64HDP3CTP5oO15HcFCvSv8oIzuM/pjmVgX6vDYhgbKc=; Hm_lpvt_24f17767262929947cc3631f99bfd274=1772285256; gitee-session-n=anJPUkxJN0RocDdyR1AreFIvNFNXdWN5Mkx5U3ZZOERYK1k1NDM1a1I5QkNXazZIdXo2bUhrL3QrQ1dZLzFpUDdCWXoyaG12cEZ6UUtMMUVtQitqVHZHcGMxeXhYcThVb1JHUXJUcmdFai84K0tsQzVJeldFQmo5VTMyVXVwZDNQT2g4NWU1NUQ4V1B3OFFOaVM4SDF3bTBaWUtUM0VoZUt0UWh2OEZJZ05KZk9zU3JIYklER0haN001aFRvUEtCcnRxc0RYenFEUzBVVG9oNWVtU0QxQmVoQmRyeWRBeHV6VklEbThLQkw0MVh1SGRKVnpXdHIxR2txQ25GRkhHWElSc3lyWmpkWDNxNDVZcklMdU5NcVQ1RFhNOGEvbVNxSGJ5V0RtL01acVF6bkE1c3luVURvb3paWS94eFNaZWZuZnRYNDRlbG1wd3pJM1hVMEk4VStrMkdGTTJLelBqWk9uN29tRnlwSlRtWUFxMVp4TmtLc3NXWGdybGorUEdwREhlaE1OOWxWU0FTeGpocFRQWWhzdjF5V1hXRG94dEJ6bFN5KzdWdm00aXNQbGFDdU5wRFBtaEtGdVNhTmMyZDJoSmZPakZIMWxNMmhBSjAzdG1GMmg3UTZxU3lEM2tENWtGK0dQdU04Mi9VMFBkTURaSjVtQjZxbUhBazU3U2haSHRJbm1peXBBSDVxUmttTFllSnVqNUdpZ2RzZDFqSmE5QUJZSHh0T3FCVW1UaE5rUmxkSWxjSkFIaXkweE82TzlZYlc5OFNTVU1VWEFySnc3SmhTVzJJYk5ISjFkVzJsQmVoZ2I5cDU0cz0tLWlKV3BWQ1ZFNnVyQmdybnZHd21XUFE9PQ%3D%3D--dddd515c7e504ee62ff0b985c1493d7bb32dca49"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/plain, */*',
                'Referer': 'https://gitee.com/sdzgn/cmd-command-manager-tool',
                'Connection': 'keep-alive',
                'Cookie': MY_GITEE_COOKIE  # <--- 加上这一行
            }
            # response = requests.get(UPDATE_CHECK_URL, headers=headers, timeout=5, verify=False)
            req = urllib.request.Request(UPDATE_CHECK_URL, headers=headers)

            # 使用 opener 显式传入 context
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
            # 禁用重定向有时也能解决 403 (防止跳转到 HTML 页面)
            # 但通常 urllib 会自动处理 302，如果 302 后变 403，说明目标链接不对

            with opener.open(req, timeout=5) as response:
                latest_version = response.read().decode('utf-8').strip()

            # 校验内容
            if "<!DOCTYPE" in latest_version or "<html" in latest_version.lower():
                raise Exception("获取到了 HTML 页面而非版本号，请检查 URL 是否为 Raw 链接")

            if latest_version != VERSION:
                self.after(0, lambda: self.show_update_dialog(latest_version))
            else:
                self.after(0, lambda: self.show_toast("✅ 当前已是最新版本", duration=2000))

        except urllib.error.HTTPError as e:
            print(f"HTTP 错误代码：{e}")
            self.after(0,
                       lambda: self.show_toast(f"❌ 网络拒绝访问 ({e})\n请检查 Raw 链接或稍后再试", duration=5000))
        except Exception as e:
            print(f"其他错误：{e}")
            self.after(0, lambda: self.show_toast(f"❌ 检查失败：{str(e)}", duration=4000))
        finally:
            self.after(0, lambda: self.update_btn.configure(text="🔄 检查更新", state="normal"))

    def show_update_dialog(self, latest_version):
        win = ctk.CTkToplevel(self)
        win.title("发现新版本")
        win.geometry("400x200")
        win.transient(self)
        win.grab_set()

        x = self.winfo_x() + (self.winfo_width() - 400) // 2
        y = self.winfo_y() + (self.winfo_height() - 200) // 2
        win.geometry(f"400x200+{x}+{y}")

        ctk.CTkLabel(win, text=f"🎉 发现新版本：{latest_version}", font=("Arial", 16, "bold"), text_color="#2E8B57").pack(
            pady=20)
        ctk.CTkLabel(win, text=f"当前版本：{VERSION}\n是否前往下载最新版？", font=("Arial", 12)).pack(pady=5)

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=20)

        def open_download():
            if DOWNLOAD_URL:
                webbrowser.open(DOWNLOAD_URL)
            else:
                self.show_toast("❌ 未配置下载链接")
            win.destroy()

        ctk.CTkButton(btn_frame, text="稍后再说", fg_color="transparent", border_width=1, command=win.destroy).pack(
            side="left", padx=10)
        ctk.CTkButton(btn_frame, text="立即下载", fg_color="#1f6aa5", command=open_download).pack(side="left", padx=10)

    # === 显示 README 窗口 ===
    def show_readme_window(self):
        # 1. 创建窗口 (先不要设置 geometry，否则无法自动计算大小)
        top = ctk.CTkToplevel(self)
        top.title("帮助文档")

        # 设置一个初始大小 (用户调整前的大小，也可以设小一点让内容决定)
        # 这里设为 600x600 作为基准
        window_width = 580
        window_height = 600
        top.geometry(f"{window_width}x{window_height}")

        # ✅ 核心步骤：计算居中坐标
        # 获取主窗口 (self) 的位置和大小
        main_x = self.winfo_x()
        main_y = self.winfo_y()
        main_w = self.winfo_width()
        main_h = self.winfo_height()

        # 计算子窗口左上角应该在的位置
        # 公式：主窗口左边距 + (主窗口宽 - 子窗口宽) / 2
        pos_x = main_x + (main_w - window_width) // 2
        pos_y = main_y + (main_h - window_height) // 2

        # 应用新的几何位置 (x+y)
        top.geometry(f"+{pos_x}+{pos_y}")

        # ✅ 设置置顶和焦点
        top.attributes('-topmost', True)
        top.focus_force()

        # --- 以下内容保持不变 ---

        # 创建文本框
        textbox = ctk.CTkTextbox(top, wrap="word", font=("Consolas", 12))
        textbox.pack(fill="both", expand=True, padx=10, pady=10)

        # 直接插入字符串
        textbox.insert("0.0", README_TEXT)
        textbox.configure(state="disabled")

        # 刷新界面确保生效
        top.update()

    # === 其他原有方法 (refresh_buttons, run_command 等) 保持不变 ===
    def refresh_buttons(self):
        for widget in self.left_frame.winfo_children():
            widget.destroy()
        self.button_widgets.clear()

        for name, cmd in self.commands:
            btn = ctk.CTkButton(self.left_frame, text=name, corner_radius=10)
            btn.pack(pady=5, padx=10, fill="x")
            btn.bind("<Button-3>", lambda e, n=name, c=cmd: self.show_context_menu(e, n, c))
            ToolTip(btn, text=cmd, wraplength=250)
            btn.bind("<Button-1>", lambda e, b=btn, n=name, c=cmd: self.on_button_press(e, b, n, c))
            btn.bind("<B1-Motion>", self.on_button_motion)
            btn.bind("<ButtonRelease-1>", self.on_button_release)
            self.button_widgets.append((btn, name, cmd))

    def on_button_press(self, event, button, name, cmd):
        self.dragging = False
        self.drag_start_y = event.y_root
        self._pressed_button = button
        self._pressed_name = name
        self._pressed_cmd = cmd

    def on_button_motion(self, event):
        if self.drag_start_y is not None and not self.dragging:
            dy = abs(event.y_root - self.drag_start_y)
            if dy > self.drag_threshold:
                self.dragging = True
                if self._pressed_button:
                    self._pressed_button.lift()
                    self._pressed_button.configure(fg_color="transparent")

        if self.dragging and self._pressed_button:
            y_in_frame = event.y_root - self.left_frame.winfo_rooty()
            frame_height = self.left_frame.winfo_height()
            if frame_height <= 0: return
            btn_height = 50
            target_index = min(len(self.commands) - 1, max(0, int(y_in_frame / btn_height)))
            current_index = None
            for i, (btn, _, _) in enumerate(self.button_widgets):
                if btn == self._pressed_button:
                    current_index = i
                    break
            if current_index is None: return
            if target_index != current_index:
                item = self.commands.pop(current_index)
                new_index = target_index if target_index < current_index else target_index
                self.commands.insert(new_index, item)
                self.refresh_buttons()
                for btn, name, cmd in self.button_widgets:
                    if name == item[0] and cmd == item[1]:
                        self._pressed_button = btn
                        break

    def on_button_release(self, event):
        try:
            if not self.dragging:
                if self._pressed_button and self._pressed_name and self._pressed_cmd:
                    self.run_command(self._pressed_name, self._pressed_cmd)
        finally:
            self.dragging = False
            self.drag_start_y = None
            self._pressed_button = None
            self._pressed_name = None
            self._pressed_cmd = None
            self.save_commands_to_file()

    def show_context_menu(self, event, name, cmd):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="编辑", command=lambda: self.open_edit_dialog(name, cmd))
        menu.add_command(label="删除", command=lambda: self.delete_command(name, cmd), foreground="red")
        menu.add_command(label="复制命令", command=lambda: self.copy_command_to_clipboard(name, cmd))
        menu.tk_popup(event.x_root, event.y_root)

    def copy_command_to_clipboard(self, name, command):
        self.clipboard_clear()
        self.clipboard_append(f"{name}:\n{command}")
        self.show_toast(f"已复制指令：{name}")

    def import_commands(self):
        filepath = filedialog.askopenfilename(title="选择批量导入文件",
                                              filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not filepath: return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            new_commands = parse_commands_from_text(content)
        except Exception as e:
            self.show_toast(f"导入失败：{e}");
            return
        if not new_commands:
            self.show_toast("未找到有效指令");
            return
        existing_names = {name for name, _ in self.commands}
        filtered_commands = []
        skipped_count = 0
        for name, cmd in new_commands:
            if name in existing_names:
                skipped_count += 1
            else:
                filtered_commands.append((name, cmd))
                existing_names.add(name)
        if filtered_commands:
            self.commands.extend(filtered_commands)
            self.refresh_buttons()
            self.save_commands_to_file()
            msg = f"成功导入 {len(filtered_commands)} 条指令"
            if skipped_count > 0: msg += f"（跳过 {skipped_count} 条重复）"
            self.show_toast(msg)
        else:
            msg = f"所有指令已存在，跳过 {skipped_count} 条" if skipped_count else "未找到有效的新指令"
            self.show_toast(msg)

    def open_add_dialog(self):
        def on_save(name, cmd):
            self.commands.append((name, cmd))
            self.refresh_buttons()
            self.save_commands_to_file()

        CommandDialog(self, "添加新指令", callback=on_save)

    def open_edit_dialog(self, old_name, old_cmd):
        def on_save(new_name, new_cmd):
            for i, (n, c) in enumerate(self.commands):
                if n == old_name and c == old_cmd:
                    self.commands[i] = (new_name, new_cmd)
                    break
            self.refresh_buttons()
            self.save_commands_to_file()

        CommandDialog(self, "编辑指令", old_name, old_cmd, on_save)

    def delete_command(self, name, cmd):
        self.commands = [(n, c) for n, c in self.commands if not (n == name and c == cmd)]
        self.refresh_buttons()
        self.save_commands_to_file()

    def append_output(self, text, tag):
        def _update():
            self.output_textbox.configure(state="normal")
            alert_keywords = ["exception", "error", "fail", "fatal", "no devices", "not found", "access denied",
                              "permission denied", "timeout", "crash", "invalid", "missing", "unable to", "denied"]
            lines = text.splitlines(keepends=True)
            for line in lines:
                lower_line = line.lower()
                is_alert = any(kw in lower_line for kw in alert_keywords)
                if is_alert:
                    self.output_textbox.insert("end", line, "alert")
                else:
                    self.output_textbox.insert("end", line, tag)
            self.output_textbox.configure(state="disabled")
            self.output_textbox.see("end")

        self.after(0, _update)

    def load_commands_from_file(self):
        try:
            if os.path.exists(COMMANDS_FILE):
                with open(COMMANDS_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
                self.commands = parse_commands_from_text(content)
            else:
                self.commands = []
        except Exception as e:
            self.show_toast(f"加载失败：{e}");
            self.commands = []

    def save_commands_to_file(self):
        try:
            content = serialize_commands(self.commands)
            with open(COMMANDS_FILE, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            self.show_toast(f"保存失败：{e}")

    def export_script(self):
        if not self.commands: return
        content = serialize_commands(self.commands)
        filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")],
                                                title="导出为指令清单（.txt）", initialfile="adb_commands.txt")
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(content)
                self.show_toast(f"导出成功:\n{os.path.basename(filename)}")
            except Exception as e:
                self.show_toast(f"导出失败：{e}")

    def clear_output(self):
        self.output_textbox.configure(state="normal")
        self.output_textbox.delete("0.0", "end")
        self.output_textbox.configure(state="disabled")

    def save_log(self):
        content = self.output_textbox.get("0.0", "end").strip()
        if not content: return
        default_name = f"adb_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        filename = filedialog.asksaveasfilename(defaultextension=".log",
                                                filetypes=[("Log files", "*.log"), ("Text files", "*.txt")],
                                                title="保存日志", initialfile=default_name)
        if filename:
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(content)
                self.show_toast("日志已保存")
            except Exception as e:
                self.show_toast(f"保存失败：{e}")

    def run_command(self, name, command):
        target_btn = None
        for btn, n, c in self.button_widgets:
            if n == name and c == command: target_btn = btn; break
        original_text = name
        if target_btn: target_btn.configure(text="⏳ 执行中...", state="disabled")

        def on_complete():
            def restore_button():
                if target_btn:
                    try:
                        target_btn.configure(text=original_text, state="normal")
                    except tk.TclError:
                        pass

            self.after(0, restore_button)

        color = COLOR_CYCLE[self.color_index % len(COLOR_CYCLE)]
        tag_name = f"run_{self.color_index}"
        self.color_index += 1
        self.output_textbox.tag_config(tag_name, foreground=color)
        run_command_realtime(command, self.append_output, tag_name, on_complete=on_complete,
                             process_list=self.active_processes)

    def handle_ctrl_c(self, event):
        try:
            start_index = self.output_textbox.index("sel.first")
            end_index = self.output_textbox.index("sel.last")
            selected_text = self.output_textbox.get(start_index, end_index)
            self.output_textbox.configure(state="normal")
            self.output_textbox.event_generate("<<Copy>>")
            self.clipboard_clear()
            self.clipboard_append(selected_text)
            self.output_textbox.configure(state="disabled")
            return "break"
        except tk.TclError:
            self.terminate_all_commands()
            return "break"

    def terminate_all_commands(self):
        if not self.active_processes:
            self.show_toast("没有正在运行的命令");
            return
        count = len(self.active_processes)
        for proc in self.active_processes[:]:
            try:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                else:
                    proc.terminate(); proc.wait(timeout=2)
            except:
                try:
                    proc.kill()
                except:
                    pass
        self.active_processes.clear()
        self.append_output(f"\n🛑 已强制终止 {count} 个命令。\n\n", "terminate")
        self.show_toast(f"已终止 {count} 个运行中的命令")

    def show_search_dialog(self, event=None):
        if self.search_window and self.search_window.winfo_exists():
            self.search_window.lift();
            return
        self.search_window = ctk.CTkToplevel(self)
        self.search_window.title("查找")
        self.search_window.geometry("300x100")
        self.search_window.transient(self)
        self.search_window.grab_set()
        x = self.winfo_x() + self.winfo_width() // 2 - 150
        y = self.winfo_y() + self.winfo_height() // 2 - 50
        self.search_window.geometry(f"300x100+{x}+{y}")
        entry_frame = ctk.CTkFrame(self.search_window, fg_color="transparent")
        entry_frame.pack(pady=10, padx=10, fill="x")
        self.search_entry = ctk.CTkEntry(entry_frame, placeholder_text="输入要查找的文本...")
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.case_sensitive_var = ctk.BooleanVar(value=False)
        case_check = ctk.CTkCheckBox(entry_frame, text="区分大小写", variable=self.case_sensitive_var,
                                     command=self._on_search_option_change)
        case_check.pack(side="right", padx=(10, 0))
        btn_frame = ctk.CTkFrame(self.search_window, fg_color="transparent")
        btn_frame.pack(pady=(0, 10), padx=10, fill="x")
        ctk.CTkButton(btn_frame, text="查找下一个", width=80, command=self.find_next).pack(side="left", padx=(0, 5))
        ctk.CTkButton(btn_frame, text="查找上一个", width=80, command=self.find_prev).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="关闭", width=60, command=self.close_search).pack(side="right")
        self.search_entry.bind("<Return>", lambda e: self.find_next())
        self.search_entry.focus()
        self.search_window.protocol("WM_DELETE_WINDOW", self.close_search)

    def _perform_search(self):
        query = self.search_entry.get()
        if not query: self.clear_search_highlight(); return []
        content = self.output_textbox.get("1.0", "end-1c")
        matches = []
        flags = 0 if self.case_sensitive_var.get() else re.IGNORECASE
        try:
            for match in re.finditer(re.escape(query), content, flags):
                start_idx = f"1.0 + {match.start()} chars"
                end_idx = f"1.0 + {match.end()} chars"
                matches.append((start_idx, end_idx))
        except Exception:
            matches = []
        self.clear_search_highlight()
        for start, end in matches: self.output_textbox.tag_add("search_highlight", start, end)
        self.output_textbox.tag_config("search_highlight", background="#FFFF00", foreground="black")
        return matches

    def find_next(self):
        matches = self._perform_search()
        if not matches: return
        if not hasattr(self, '_search_index') or self._search_index >= len(matches) - 1:
            self._search_index = 0
        else:
            self._search_index += 1
        start, end = matches[self._search_index]
        self.output_textbox.see(start)
        self.output_textbox.tag_remove("search_current", "1.0", "end")
        self.output_textbox.tag_add("search_current", start, end)
        self.output_textbox.tag_config("search_current", background="#FFA500", foreground="black")

    def find_prev(self):
        matches = self._perform_search()
        if not matches: return
        if not hasattr(self, '_search_index') or self._search_index <= 0:
            self._search_index = len(matches) - 1
        else:
            self._search_index -= 1
        start, end = matches[self._search_index]
        self.output_textbox.see(start)
        self.output_textbox.tag_remove("search_current", "1.0", "end")
        self.output_textbox.tag_add("search_current", start, end)
        self.output_textbox.tag_config("search_current", background="#FFA500", foreground="black")

    def _on_search_option_change(self):
        if self.search_entry.get():
            self._perform_search()
            if hasattr(self, '_search_index'): self.find_next()

    def clear_search_highlight(self):
        try:
            self.output_textbox.tag_delete("search_highlight")
            self.output_textbox.tag_delete("search_current")
        except tk.TclError:
            pass

    def close_search(self):
        if self.search_window:
            self.search_window.destroy()
            self.search_window = None
        self.clear_search_highlight()
        if hasattr(self, '_search_index'): delattr(self, '_search_index')

    def show_toast(self, message, duration=2000):
        if self._current_toast:
            try:
                self._current_toast.destroy()
            except:
                pass
        toast = ctk.CTkToplevel(self)
        self._current_toast = toast
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        x = self.winfo_x() + self.winfo_width() // 2 - 150
        y = self.winfo_y() + self.winfo_height() // 3
        toast.geometry(f"300x40+{x}+{y}")
        label = ctk.CTkLabel(toast, text=message, fg_color="white", text_color="black", corner_radius=8,
                             font=("Arial", 12), padx=10, pady=5)
        label.pack(expand=True, fill="both")

        def _destroy():
            if self._current_toast == toast: self._current_toast = None
            try:
                toast.destroy()
            except:
                pass

        toast.after(duration, _destroy)


# === 启动 ===
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    app = App()
    app.mainloop()