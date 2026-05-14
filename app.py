"""
Enhanced File & Folder Manager — Kivy Application
═══════════════════════════════════════════════════
Features:
  • Tabbed browsing with multiple directory tabs
  • List view and grid view toggle
  • Preview panel for images and text files
  • Bookmarks — add/remove favorite folders (persisted)
  • Hidden files toggle
  • Select All / Invert Selection
  • Copy, Cut, Paste with conflict resolution
  • Move to Trash (safe delete)
  • ZIP support — compress selected / extract archives
  • Sort by name, size, date, type
  • Search / filter + deep recursive search
  • Right-click context menu
  • File properties with MD5 / SHA256 hash
  • Disk usage indicator
  • Dark / Light theme toggle
  • Recent locations in sidebar
  • Folder size calculation
  • Keyboard shortcuts (F1 for help)
  • Color-coded file types
  • Duplicate file finder
  • Open terminal at current path
  • Breadcrumb navigation
"""

import os
import shutil
import platform
import subprocess
import hashlib
import json
import zipfile
import threading
from datetime import datetime
from pathlib import Path

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.widget import Widget  # FIX: was missing
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line
from kivy.metrics import dp, sp
from kivy.properties import (
    StringProperty, BooleanProperty, ListProperty,
    OptionProperty, NumericProperty,
)
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.core.window import Window

# ═══════════════════════════════════════════════════════════════
#  THEMES
# ═══════════════════════════════════════════════════════════════
DARK = {
    "bg":       [0.12, 0.12, 0.16, 1],
    "bg2":      [0.15, 0.15, 0.19, 1],
    "bg3":      [0.19, 0.19, 0.24, 1],
    "bg_hover": [0.24, 0.24, 0.30, 1],
    "selected": [0.16, 0.32, 0.56, 1],
    "accent":   [0.28, 0.56, 0.86, 1],
    "text":     [0.93, 0.93, 0.96, 1],
    "text2":    [0.55, 0.56, 0.62, 1],
    "sidebar":  [0.09, 0.09, 0.12, 1],
    "header":   [0.10, 0.10, 0.14, 1],
    "danger":   [0.92, 0.28, 0.30, 1],
    "success":  [0.28, 0.72, 0.36, 1],
    "tab_active": [0.22, 0.22, 0.28, 1],
    "tab_inactive":[0.13, 0.13, 0.17, 1],
    "preview_bg": [0.10, 0.10, 0.14, 1],
}
LIGHT = {
    "bg":       [0.94, 0.94, 0.96, 1],
    "bg2":      [1.0, 1.0, 1.0, 1],
    "bg3":      [0.96, 0.96, 0.98, 1],
    "bg_hover": [0.86, 0.88, 0.92, 1],
    "selected": [0.56, 0.76, 0.96, 1],
    "accent":   [0.18, 0.46, 0.76, 1],
    "text":     [0.13, 0.13, 0.16, 1],
    "text2":    [0.48, 0.48, 0.52, 1],
    "sidebar":  [0.88, 0.88, 0.91, 1],
    "header":   [0.91, 0.91, 0.94, 1],
    "danger":   [0.82, 0.18, 0.20, 1],
    "success":  [0.18, 0.62, 0.26, 1],
    "tab_active": [1.0, 1.0, 1.0, 1],
    "tab_inactive":[0.91, 0.91, 0.94, 1],
    "preview_bg": [0.92, 0.92, 0.95, 1],
}

theme = dict(DARK)  # Mutable global theme dict

# ═══════════════════════════════════════════════════════════════
#  FILE TYPE COLORS & CATEGORIES
# ═══════════════════════════════════════════════════════════════
FILE_ICONS = {
    "folder": "📁", "txt": "📄", "md": "📝", "log": "📋", "csv": "📊",
    "py": "🐍", "js": "📜", "ts": "📜", "html": "🌐", "css": "🎨",
    "json": "📋", "xml": "📰", "yaml": "📋", "yml": "📋", "toml": "📋",
    "jpg": "🖼", "jpeg": "🖼", "png": "🖼", "gif": "🖼", "svg": "🖼",
    "bmp": "🖼", "webp": "🖼", "mp3": "🎵", "wav": "🎵", "flac": "🎵",
    "mp4": "🎬", "avi": "🎬", "mkv": "🎬", "mov": "🎬", "webm": "🎬",
    "pdf": "📕", "doc": "📘", "docx": "📘", "xls": "📗", "xlsx": "📗",
    "zip": "📦", "rar": "📦", "7z": "📦", "tar": "📦", "gz": "📦",
    "exe": "⚙", "sh": "⚙", "bat": "⚙", "java": "☕", "cpp": "⚙",
    "c": "⚙", "rb": "💎", "go": "🔵", "rs": "🦀", "swift": "🐦",
    "db": "🗃", "sql": "🗃", "iso": "💿", "dmg": "💿", "kt": "🟣",
}

CAT_COLORS = {
    "folder":     [0.96, 0.78, 0.26, 1],
    "image":      [0.92, 0.48, 0.72, 1],
    "audio":      [0.40, 0.80, 0.40, 1],
    "video":      [0.68, 0.40, 0.92, 1],
    "code":       [0.30, 0.76, 0.92, 1],
    "document":   [0.44, 0.60, 0.92, 1],
    "archive":    [0.92, 0.60, 0.28, 1],
    "executable": [0.92, 0.36, 0.36, 1],
    "data":       [0.60, 0.60, 0.72, 1],
    "text":       [0.80, 0.80, 0.84, 1],
    "other":      [0.70, 0.70, 0.76, 1],
}

CAT_NAMES = {
    "folder": "Folder", "image": "Image", "audio": "Audio",
    "video": "Video", "code": "Source Code", "document": "Document",
    "archive": "Archive", "executable": "Executable", "data": "Data",
    "text": "Text File", "other": "File",
}

_EXT_CAT = {}
for exts, cat in [
    ({"jpg","jpeg","png","gif","svg","bmp","webp","tiff","tif","ico"},"image"),
    ({"mp3","wav","flac","ogg","aac","wma","m4a","opus"},"audio"),
    ({"mp4","avi","mkv","mov","webm","wmv","flv","m4v"},"video"),
    ({"py","js","ts","html","css","java","cpp","c","rb","go","rs",
      "swift","kt","sh","bat","php","lua","r","scala"},"code"),
    ({"doc","docx","pdf","rtf","odt","xls","xlsx","ppt","pptx","md"},"document"),
    ({"zip","rar","7z","tar","gz","bz2","xz","zst"},"archive"),
    ({"exe","msi","dmg","app","deb","rpm","apk"},"executable"),
    ({"json","xml","yaml","yml","toml","ini","cfg","conf","sql","db","sqlite"},"data"),
    ({"txt","log","cfg"},"text"),
]:
    for e in exts:
        _EXT_CAT[e] = cat


def _icon(filename, is_dir):
    if is_dir:
        return FILE_ICONS["folder"]
    return FILE_ICONS.get(os.path.splitext(filename)[1].lower().lstrip("."), "📄")


def _category(filename, is_dir):
    if is_dir:
        return "folder"
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    return _EXT_CAT.get(ext, "other")


def _type_name(filename, is_dir):
    cat = _category(filename, is_dir)
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    if cat == "folder":
        return "Folder"
    return f"{ext.upper()} {CAT_NAMES[cat]}" if ext else CAT_NAMES[cat]


def _cat_color(filename, is_dir):
    return CAT_COLORS.get(_category(filename, is_dir), CAT_COLORS["other"])


def _fmt_size(n):
    if n is None or n < 0:
        return "—"
    for u in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{int(n)} {u}" if u == "B" else f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PB"


def _fmt_date(ts):
    try:
        dt = datetime.fromtimestamp(ts)
        now = datetime.now()
        if dt.date() == now.date():
            return f'Today {dt.strftime("%H:%M")}'
        if (now.date() - dt.date()).days == 1:
            return f'Yesterday {dt.strftime("%H:%M")}'
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "—"


def _open_sys(path):
    s = platform.system()
    try:
        if s == "Darwin":
            subprocess.Popen(["open", path])
        elif s == "Windows":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


def _calc_hash(path, algo="md5", chunk=8192):
    try:
        h = hashlib.new(algo)
        with open(path, "rb") as f:
            while True:
                data = f.read(chunk)
                if not data:
                    break
                h.update(data)
        return h.hexdigest()
    except Exception:
        return "Error"


def _folder_size(path):
    total = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total += os.path.getsize(fp)
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return total


def _folder_count(path):
    try:
        return sum(1 for _ in os.listdir(path))
    except (OSError, PermissionError):
        return -1


# ═══════════════════════════════════════════════════════════════
#  PERSISTENCE
# ═══════════════════════════════════════════════════════════════
DATA_DIR = os.path.join(str(Path.home()), ".file_manager_data")
os.makedirs(DATA_DIR, exist_ok=True)


def _load_json(name, default):
    p = os.path.join(DATA_DIR, name)
    try:
        with open(p, "r") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(name, data):
    p = os.path.join(DATA_DIR, name)
    try:
        with open(p, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
#  KV RULES
# ═══════════════════════════════════════════════════════════════
KV = """
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp

<FileItemRow>:
    orientation: "horizontal"
    size_hint_y: None
    height: dp(38)
    padding: [dp(10), dp(2)]
    spacing: dp(6)
    canvas.before:
        Color:
            rgba: root.sel_bg if root.is_selected else root.norm_bg
        Rectangle:
            pos: root.pos
            size: root.size
        Color:
            rgba: 0.18, 0.18, 0.22, 0.5
        Line:
            rectangle: [*root.pos, *root.size]
            width: dp(0.4)

    Label:
        text: root.icon_char
        size_hint_x: None
        width: dp(28)
        font_size: sp(18)
        halign: "center"
        valign: "middle"
    Label:
        text: root.display_name
        halign: "left"
        valign: "middle"
        text_size: self.size
        color: root.name_color
        size_hint_x: 0.40
        font_size: sp(12)
        shorten: True
        shorten_from: "right"
    Label:
        text: root.filesize
        halign: "right"
        valign: "middle"
        text_size: self.size
        color: root.sub_color
        size_hint_x: None
        width: dp(76)
        font_size: sp(10)
    Label:
        text: root.filedate
        halign: "center"
        valign: "middle"
        text_size: self.size
        color: root.sub_color
        size_hint_x: None
        width: dp(120)
        font_size: sp(10)
    Label:
        text: root.filetype
        halign: "left"
        valign: "middle"
        text_size: self.size
        color: root.sub_color
        size_hint_x: None
        width: dp(76)
        font_size: sp(10)

<FileItemCard>:
    orientation: "vertical"
    size_hint: None, None
    size: dp(104), dp(104)
    padding: [dp(4), dp(2)]
    canvas.before:
        Color:
            rgba: root.sel_bg if root.is_selected else root.norm_bg
        RoundedRectangle:
            pos: root.pos
            size: root.size
            radius: [8]
    Label:
        text: root.icon_char
        font_size: sp(34)
        halign: "center"
        valign: "middle"
        size_hint_y: 0.60
    Label:
        text: root.display_name
        font_size: sp(9)
        halign: "center"
        valign: "top"
        text_size: self.width - dp(8), None
        color: root.name_color
        size_hint_y: 0.40
        shorten: True
        shorten_from: "right"
"""

Builder.load_string(KV)


# ═══════════════════════════════════════════════════════════════
#  FILE ITEM WIDGETS
# ═══════════════════════════════════════════════════════════════
class FileItemRow(BoxLayout):
    filepath = StringProperty("")
    display_name = StringProperty("")
    icon_char = StringProperty("")
    filesize = StringProperty("")
    filedate = StringProperty("")
    filetype = StringProperty("")
    is_dir = BooleanProperty(False)
    is_selected = BooleanProperty(False)
    norm_bg = ListProperty(theme["bg2"])
    sel_bg = ListProperty(theme["selected"])
    name_color = ListProperty(theme["text"])
    sub_color = ListProperty(theme["text2"])

    def __init__(self, filepath, name, is_dir, size_str, date_str,
                 type_str, icon, cat_color, on_select, on_open, **kw):
        super().__init__(**kw)
        self.filepath = filepath
        self.display_name = name
        self.is_dir = is_dir
        self.filesize = size_str
        self.filedate = date_str
        self.filetype = type_str
        self.icon_char = icon
        self.name_color = list(cat_color)
        self.sub_color = list(theme["text2"])
        self._on_select = on_select
        self._on_open = on_open

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        if touch.button == "right":
            self._on_select(self.filepath, exclusive=True)
            return True
        if touch.is_double_tap:
            self._on_open(self.filepath, self.is_dir)
        else:
            mod = Window._modifiers if hasattr(Window, '_modifiers') else []
            exclusive = 'ctrl' not in mod and 'shift' not in mod
            self._on_select(self.filepath, exclusive=exclusive)
        return True


class FileItemCard(BoxLayout):
    filepath = StringProperty("")
    display_name = StringProperty("")
    icon_char = StringProperty("")
    is_dir = BooleanProperty(False)
    is_selected = BooleanProperty(False)
    norm_bg = ListProperty(theme["bg3"])
    sel_bg = ListProperty(theme["selected"])
    name_color = ListProperty(theme["text"])

    def __init__(self, filepath, name, is_dir, icon,
                 cat_color, on_select, on_open, **kw):
        super().__init__(**kw)
        self.filepath = filepath
        self.display_name = name
        self.is_dir = is_dir
        self.icon_char = icon
        self.name_color = list(cat_color)
        self._on_select = on_select
        self._on_open = on_open

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        if touch.button == "right":
            self._on_select(self.filepath, exclusive=True)
            return True
        if touch.is_double_tap:
            self._on_open(self.filepath, self.is_dir)
        else:
            mod = Window._modifiers if hasattr(Window, '_modifiers') else []
            exclusive = 'ctrl' not in mod and 'shift' not in mod
            self._on_select(self.filepath, exclusive=exclusive)
        return True


# ═══════════════════════════════════════════════════════════════
#  CONTEXT MENU
# ═══════════════════════════════════════════════════════════════
class ContextMenu(FloatLayout):
    """Floating context menu that dismisses itself after an item is picked."""

    def __init__(self, items, pos, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        w = dp(200)
        line_h = dp(32)
        h = dp(len(items) * line_h + 10)
        self.size = (w, h)
        x = min(pos[0], Window.width - w - dp(8))
        y = min(pos[1], h + dp(8))
        y = max(y, dp(8))
        self.pos = (x, y)

        self._draw_bg()
        self.bind(pos=self._draw_bg, size=self._draw_bg)

        box = BoxLayout(orientation="vertical", padding=[dp(4), dp(4)],
                        spacing=dp(1), pos=self.pos, size=self.size)
        self.bind(pos=lambda i, v: setattr(box, 'pos', v),
                  size=lambda i, v: setattr(box, 'size', v))

        for label, callback in items:
            b = Button(text=label, size_hint_y=None, height=line_h,
                       background_color=(0, 0, 0, 0), color=theme["text"],
                       font_size=sp(11), halign="left", valign="middle",
                       background_normal="", background_down="")
            b.bind(on_release=lambda bt, cb=callback: self._pick(cb))
            box.add_widget(b)
        self.add_widget(box)

    def _draw_bg(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*theme["bg3"])
            RoundedRectangle(pos=self.pos, size=self.size, radius=[6])
            Color(*theme["accent"][:3], 0.4)
            Line(rounded_rectangle=(*self.pos, *self.size, 6), width=dp(1))

    def _pick(self, cb):
        if self.parent:
            self.parent.remove_widget(self)
        cb()


# ═══════════════════════════════════════════════════════════════
#  MAIN FILE MANAGER
# ═══════════════════════════════════════════════════════════════
class FileManager(BoxLayout):
    current_path = StringProperty("")
    view_mode = OptionProperty("list", options=["list", "grid"])
    sort_key = OptionProperty("name", options=["name", "size", "date", "type"])
    sort_rev = BooleanProperty(False)
    show_hidden = BooleanProperty(False)
    show_preview = BooleanProperty(False)

    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)
        self.home = str(Path.home())
        self.clipboard_src = []
        self.clipboard_mode = ""
        self.selected = []
        self._dark_mode = True
        self._status_text = "Ready"

        self.tabs = [{"path": self.home, "history": [self.home], "hist_idx": 0}]
        self.active_tab = 0

        self.bookmarks = _load_json("bookmarks.json", [self.home])
        self.recent = _load_json("recent.json", [])

        self._ctx_menu = None

        self._build_ui()
        Clock.schedule_once(lambda _: self._navigate(self.home), 0.05)
        Window.bind(on_keyboard=self._on_key, on_mouse_down=self._on_mouse)

    # ──────────────────────────────────────────────────────
    #  UI CONSTRUCTION
    # ──────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Tab bar ──
        self.tab_bar = BoxLayout(size_hint_y=None, height=dp(34),
                                 padding=[dp(2), dp(2)], spacing=dp(2))
        self._redraw_bg(self.tab_bar, theme["header"])
        self.add_widget(self.tab_bar)
        self._rebuild_tabs()

        # ── Top bar ──
        top = BoxLayout(size_hint_y=None, height=dp(42),
                        padding=[dp(6), dp(3)], spacing=dp(4))
        self._redraw_bg(top, theme["bg"])

        for icon, cb in [
            ("⬅", self.go_back), ("➡", self.go_forward),
            ("⬆", self.go_up),
            ("🏠", lambda: self._navigate(self.home)),
            ("🔄", self.refresh),
        ]:
            b = Button(text=icon, size_hint_x=None, width=dp(34),
                       font_size=sp(15), background_color=(0, 0, 0, 0),
                       color=theme["text"], background_normal="")
            b.bind(on_release=lambda bt, fn=cb: fn())
            top.add_widget(b)

        self.path_input = TextInput(
            multiline=False, hint_text="Path...", font_size=sp(12),
            background_color=theme["bg3"], foreground_color=theme["text"],
            cursor_color=theme["accent"],
            padding=[dp(8), dp(5), dp(8), dp(3)])
        self.path_input.bind(
            on_text_validate=lambda _: self._navigate(self.path_input.text))
        top.add_widget(self.path_input)

        self.search_input = TextInput(
            multiline=False, hint_text="🔍 Search...", size_hint_x=None,
            width=dp(160), font_size=sp(11),
            background_color=theme["bg3"], foreground_color=theme["text"],
            cursor_color=theme["accent"],
            padding=[dp(8), dp(5), dp(8), dp(3)])
        self.search_input.bind(on_text=lambda _, v: self._list_dir())
        top.add_widget(self.search_input)
        self.add_widget(top)

        # ── Breadcrumb ──
        self.crumb_bar = BoxLayout(size_hint_y=None, height=dp(26),
                                   padding=[dp(8), dp(1)], spacing=dp(2))
        self._redraw_bg(self.crumb_bar, theme["header"])
        self.add_widget(self.crumb_bar)

        # ── Action bar ──
        act = BoxLayout(size_hint_y=None, height=dp(34),
                        padding=[dp(4), dp(1)], spacing=dp(2))
        self._redraw_bg(act, theme["bg"])

        actions = [
            ("📁+", self.dlg_new_folder), ("📄+", self.dlg_new_file),
            ("📋Copy", self.copy_sel), ("✂Cut", self.cut_sel),
            ("📌Paste", self.paste), ("✏Rename", self.dlg_rename),
            ("🗑Del", self.dlg_delete), ("♻Trash", self.trash_sel),
            ("📦Zip", self.zip_sel), ("📤Unzip", self.unzip_sel),
            ("🔖Mark", self.toggle_bookmark),
            ("🔍Deep", self.dlg_deep_search),
            ("🔎Dupes", self.find_duplicates),
            ("💻Term", self.open_terminal),
        ]
        for label, cb in actions:
            b = Button(text=label, size_hint_x=None, width=dp(60),
                       font_size=sp(9), background_color=theme["bg3"],
                       color=theme["text"], background_normal="")
            b.bind(on_release=lambda bt, fn=cb: fn())
            act.add_widget(b)

        act.add_widget(Widget())

        self.sort_btn = Button(text="Sort:Name ▲", size_hint_x=None,
                               width=dp(88), font_size=sp(9),
                               background_color=theme["bg3"],
                               color=theme["text"], background_normal="")
        self.sort_btn.bind(on_release=lambda _: self._cycle_sort())
        act.add_widget(self.sort_btn)

        self.view_btn = Button(text="⊞Grid", size_hint_x=None,
                               width=dp(56), font_size=sp(9),
                               background_color=theme["bg3"],
                               color=theme["text"], background_normal="")
        self.view_btn.bind(on_release=lambda _: self._toggle_view())
        act.add_widget(self.view_btn)

        self.hidden_btn = Button(text="👁Hidden", size_hint_x=None,
                                 width=dp(64), font_size=sp(9),
                                 background_color=theme["bg3"],
                                 color=theme["text"], background_normal="")
        self.hidden_btn.bind(on_release=lambda _: self._toggle_hidden())
        act.add_widget(self.hidden_btn)

        self.preview_btn = Button(text="◀Prev", size_hint_x=None,
                                  width=dp(56), font_size=sp(9),
                                  background_color=theme["bg3"],
                                  color=theme["text"], background_normal="")
        self.preview_btn.bind(on_release=lambda _: self._toggle_preview())
        act.add_widget(self.preview_btn)

        self.theme_btn = Button(
            text="☀" if self._dark_mode else "🌙",
            size_hint_x=None, width=dp(36), font_size=sp(13),
            background_color=theme["bg3"], color=theme["text"],
            background_normal="")
        self.theme_btn.bind(on_release=lambda _: self._toggle_theme())
        act.add_widget(self.theme_btn)
        self.add_widget(act)

        # ── List header ──
        self.list_header = BoxLayout(size_hint_y=None, height=dp(26),
                                     padding=[dp(10), dp(1)], spacing=dp(6))
        self._redraw_bg(self.list_header, theme["header"])
        for txt, w, hx in [
            ("", dp(28), None), ("Name", None, 0.40),
            ("Size", dp(76), None), ("Modified", dp(120), None),
            ("Type", dp(76), None),
        ]:
            l = Label(text=txt, size_hint_x=hx if hx else None,
                      width=w if w else 0,
                      color=theme["text2"], font_size=sp(10),
                      halign="left" if txt == "Name" else "center",
                      valign="middle")
            l.bind(size=lambda i, v: setattr(i, "text_size", v))
            self.list_header.add_widget(l)
        self.add_widget(self.list_header)

        # ── Content: sidebar + files + preview ──
        self.content_area = BoxLayout(orientation="horizontal")

        # Sidebar
        self.sidebar = BoxLayout(orientation="vertical", size_hint_x=None,
                                 width=dp(160), padding=[dp(4), dp(6)],
                                 spacing=dp(1))
        self._redraw_bg(self.sidebar, theme["sidebar"])
        self._build_sidebar()
        self.content_area.add_widget(self.sidebar)

        # File scroll
        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(6),
                                 bar_color=[*theme["accent"][:3], 0.4])
        self.file_container = GridLayout(cols=1, size_hint_y=None,
                                         spacing=dp(1), padding=[dp(2), dp(2)])
        self.file_container.bind(
            minimum_height=self.file_container.setter("height"))
        self.scroll.add_widget(self.file_container)
        self.content_area.add_widget(self.scroll)

        # Preview panel
        self.preview_panel = BoxLayout(orientation="vertical",
                                       size_hint_x=None, width=dp(0),
                                       padding=[dp(4), dp(4)], spacing=dp(4))
        self._redraw_bg(self.preview_panel, theme["preview_bg"])
        self.content_area.add_widget(self.preview_panel)

        self.add_widget(self.content_area)

        # ── Status bar ──
        self.status_bar = BoxLayout(size_hint_y=None, height=dp(24),
                                    padding=[dp(10), dp(1)])
        self._redraw_bg(self.status_bar, theme["sidebar"])
        self.status_label = Label(text="Ready", halign="left",
                                  valign="middle", color=theme["text2"],
                                  font_size=sp(10))
        self.status_label.bind(size=lambda i, v: setattr(i, "text_size", v))
        self.status_bar.add_widget(self.status_label)

        self.disk_label = Label(text="", halign="right", valign="middle",
                                color=theme["text2"], font_size=sp(10),
                                size_hint_x=None, width=dp(200))
        self.disk_label.bind(size=lambda i, v: setattr(i, "text_size", v))
        self.status_bar.add_widget(self.disk_label)
        self.add_widget(self.status_bar)

    # ──────────────────────────────────────────────────────
    #  CANVAS HELPERS
    # ──────────────────────────────────────────────────────
    def _redraw_bg(self, widget, color):
        widget.canvas.before.clear()
        with widget.canvas.before:
            Color(*color)
            Rectangle(pos=widget.pos, size=widget.size)
        widget.bind(
            pos=lambda i, v: self._update_bg_pos(i, v),
            size=lambda i, v: self._update_bg_size(i, v),
        )

    @staticmethod
    def _update_bg_pos(widget, pos):
        for instr in widget.canvas.before.children:
            if isinstance(instr, Rectangle):
                instr.pos = pos

    @staticmethod
    def _update_bg_size(widget, size):
        for instr in widget.canvas.before.children:
            if isinstance(instr, Rectangle):
                instr.size = size

    # ──────────────────────────────────────────────────────
    #  STATUS BAR
    # ──────────────────────────────────────────────────────
    def _set_status(self, text):
        self._status_text = text
        n = len(self.selected)
        sel = f"  •  {n} selected" if n else ""
        self.status_label.text = text + sel

    def _update_disk(self):
        try:
            usage = shutil.disk_usage(self.current_path)
            pct = usage.used / usage.total * 100
            bar_len = 12
            filled = int(pct / 100 * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            self.disk_label.text = (
                f"{bar} {_fmt_size(usage.used)}/{_fmt_size(usage.total)}"
                f" ({pct:.0f}%)")
        except Exception:
            self.disk_label.text = ""

    # ──────────────────────────────────────────────────────
    #  TABS
    # ──────────────────────────────────────────────────────
    def _rebuild_tabs(self):
        self.tab_bar.clear_widgets()
        for i, tab in enumerate(self.tabs):
            name = os.path.basename(tab["path"]) or tab["path"]
            if len(name) > 16:
                name = name[:14] + "…"

            box = BoxLayout(size_hint_x=None, width=dp(140),
                            spacing=dp(2), padding=[dp(4), dp(2)])
            bg_c = (theme["tab_active"] if i == self.active_tab
                    else theme["tab_inactive"])
            box.canvas.before.clear()
            with box.canvas.before:
                Color(*bg_c)
                RoundedRectangle(pos=box.pos, size=box.size,
                                radius=[6, 6, 0, 0])
            box.bind(
                pos=lambda w, v, b=box, idx=i: self._update_tab_bg(b, idx),
                size=lambda w, v, b=box, idx=i: self._update_tab_bg(b, idx),
            )

            # FIX: Use Button to prevent on_touch_down collision with close
            lbl = Button(
                text=f"📁 {name}", halign="left", valign="middle",
                color=theme["text"], font_size=sp(10),
                size_hint_x=0.78,
                background_color=(0, 0, 0, 0),
                background_normal="", background_down="")
            lbl.bind(size=lambda inst, v: setattr(inst, "text_size", v))
            lbl.bind(on_release=lambda bt, idx=i: self._switch_tab(idx))
            box.add_widget(lbl)

            if len(self.tabs) > 1:
                close = Button(text="✕", size_hint_x=None, width=dp(22),
                               font_size=sp(10),
                               background_color=(0, 0, 0, 0),
                               color=theme["text2"],
                               background_normal="", background_down="")
                close.bind(on_release=lambda bt, idx=i: self._close_tab(idx))
                box.add_widget(close)

            self.tab_bar.add_widget(box)

        add_btn = Button(text="+", size_hint_x=None, width=dp(30),
                         font_size=sp(14), background_color=(0, 0, 0, 0),
                         color=theme["accent"], background_normal="")
        add_btn.bind(on_release=lambda _: self._add_tab())
        self.tab_bar.add_widget(add_btn)

    def _update_tab_bg(self, box, idx):
        box.canvas.before.clear()
        bg_c = (theme["tab_active"] if idx == self.active_tab
                else theme["tab_inactive"])
        with box.canvas.before:
            Color(*bg_c)
            RoundedRectangle(pos=box.pos, size=box.size,
                            radius=[6, 6, 0, 0])

    def _switch_tab(self, idx):
        if idx == self.active_tab:
            return
        self._save_tab_state()
        self.active_tab = idx
        tab = self.tabs[idx]
        self._rebuild_tabs()
        self._navigate_quiet(tab["path"])
        self.selected = []

    def _add_tab(self):
        self._save_tab_state()
        new_tab = {"path": self.home, "history": [self.home], "hist_idx": 0}
        self.tabs.append(new_tab)
        self.active_tab = len(self.tabs) - 1
        self._rebuild_tabs()
        self._navigate(self.home)

    def _close_tab(self, idx):
        if len(self.tabs) <= 1:
            return
        self.tabs.pop(idx)
        if self.active_tab >= len(self.tabs):
            self.active_tab = len(self.tabs) - 1
        elif self.active_tab > idx:
            self.active_tab -= 1
        elif self.active_tab == idx:
            self.active_tab = min(idx, len(self.tabs) - 1)
        self._rebuild_tabs()
        tab = self.tabs[self.active_tab]
        self._navigate_quiet(tab["path"])

    def _save_tab_state(self):
        if 0 <= self.active_tab < len(self.tabs):
            self.tabs[self.active_tab]["path"] = self.current_path

    # ──────────────────────────────────────────────────────
    #  SIDEBAR
    # ──────────────────────────────────────────────────────
    def _build_sidebar(self):
        self.sidebar.clear_widgets()
        self._redraw_bg(self.sidebar, theme["sidebar"])

        self.sidebar.add_widget(self._side_label("QUICK ACCESS"))
        quick = [
            ("🏠 Home", self.home),
            ("📁 Desktop", str(Path.home() / "Desktop")),
            ("📄 Documents", str(Path.home() / "Documents")),
            ("⬇ Downloads", str(Path.home() / "Downloads")),
            ("🖼 Pictures", str(Path.home() / "Pictures")),
            ("🎵 Music", str(Path.home() / "Music")),
            ("🎬 Videos", str(Path.home() / "Videos")),
        ]
        for lbl, p in quick:
            if os.path.isdir(p):
                self.sidebar.add_widget(self._side_btn(lbl, p))

        self.sidebar.add_widget(self._side_label("BOOKMARKS ⭐"))
        for bm in self.bookmarks:
            if os.path.isdir(bm):
                name = os.path.basename(bm) or bm
                self.sidebar.add_widget(self._side_btn(f"⭐ {name}", bm))

        self.sidebar.add_widget(self._side_label("RECENT 🕐"))
        for r in self.recent[:8]:
            if os.path.isdir(r):
                name = os.path.basename(r) or r
                if len(name) > 18:
                    name = name[:16] + "…"
                self.sidebar.add_widget(self._side_btn(f"🕐 {name}", r))

        self.sidebar.add_widget(self._side_label("DRIVES"))
        if platform.system() == "Windows":
            for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
                d = f"{letter}:\\"
                if os.path.isdir(d):
                    self.sidebar.add_widget(self._side_btn(f"💾 {d}", d))
        else:
            self.sidebar.add_widget(self._side_btn("💾 /", "/"))
            for m in (os.listdir("/mnt") if os.path.isdir("/mnt") else []):
                mp = f"/mnt/{m}"
                if os.path.isdir(mp):
                    self.sidebar.add_widget(self._side_btn(f"💾 {m}", mp))
            for m in (os.listdir("/media") if os.path.isdir("/media") else []):
                mp = f"/media/{m}"
                if os.path.isdir(mp):
                    for sub in os.listdir(mp):
                        spath = f"{mp}/{sub}"
                        if os.path.isdir(spath):
                            self.sidebar.add_widget(
                                self._side_btn(f"💾 {sub}", spath))

    def _side_label(self, txt):
        l = Label(text=txt, size_hint_y=None, height=dp(24),
                  halign="left", valign="middle",
                  color=theme["accent"], font_size=sp(9), bold=True)
        l.bind(size=lambda i, v: setattr(
            i, "text_size", (i.width - dp(12), i.height)))
        return l

    def _side_btn(self, lbl, path):
        b = Button(text=lbl, size_hint_y=None, height=dp(26),
                   halign="left", valign="middle",
                   font_size=sp(10), background_color=(0, 0, 0, 0),
                   color=theme["text"], background_normal="")
        b.bind(size=lambda i, v: setattr(
            i, "text_size", (i.width - dp(14), i.height)),
            on_release=lambda bt, pp=path: self._navigate(pp))
        return b

    # ──────────────────────────────────────────────────────
    #  NAVIGATION
    # ──────────────────────────────────────────────────────
    def _navigate(self, path):
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            self._show_msg("Error", f"Not a directory:\n{path}")
            return
        self._navigate_quiet(path)
        tab = self.tabs[self.active_tab]
        if tab["hist_idx"] < len(tab["history"]) - 1:
            tab["history"] = tab["history"][:tab["hist_idx"] + 1]
        tab["history"].append(path)
        tab["hist_idx"] = len(tab["history"]) - 1
        tab["path"] = path
        self._add_recent(path)

    def _navigate_quiet(self, path):
        self.current_path = path
        self.path_input.text = path
        self.selected = []
        self._build_crumb(path)
        self._list_dir()
        self._update_disk()
        self._update_preview()

    def go_back(self):
        tab = self.tabs[self.active_tab]
        if tab["hist_idx"] > 0:
            tab["hist_idx"] -= 1
            p = tab["history"][tab["hist_idx"]]
            tab["path"] = p
            self._navigate_quiet(p)

    def go_forward(self):
        tab = self.tabs[self.active_tab]
        if tab["hist_idx"] < len(tab["history"]) - 1:
            tab["hist_idx"] += 1
            p = tab["history"][tab["hist_idx"]]
            tab["path"] = p
            self._navigate_quiet(p)

    def go_up(self):
        parent = os.path.dirname(self.current_path)
        if parent != self.current_path:
            self._navigate(parent)

    def refresh(self):
        self._list_dir()
        self._update_disk()

    def _build_crumb(self, path):
        self.crumb_bar.clear_widgets()
        self._redraw_bg(self.crumb_bar, theme["header"])
        parts = path.replace("\\", "/").split("/")
        built = ""
        for i, part in enumerate(parts):
            if not part and i == 0:
                built = "/"
                lbl = "/"
            else:
                built = built.rstrip("/") + "/" + part if built else part
                lbl = part or "/"
            if not part and i > 0:
                continue
            target = built if built else "/"
            is_last = (i == len(parts) - 1
                       or (i == len(parts) - 2 and not parts[-1]))
            b = Button(text=f" {lbl} ", size_hint_x=None,
                       font_size=sp(11), background_color=(0, 0, 0, 0),
                       color=theme["text"] if is_last else theme["accent"],
                       background_normal="")
            b.bind(on_release=lambda bt, pp=target: self._navigate(pp))
            self.crumb_bar.add_widget(b)
            if not is_last:
                sep = Label(text="/", size_hint_x=None, width=dp(10),
                            color=theme["text2"], font_size=sp(11))
                self.crumb_bar.add_widget(sep)

    # ──────────────────────────────────────────────────────
    #  FILE LISTING
    # ──────────────────────────────────────────────────────
    def _list_dir(self):
        self.file_container.clear_widgets()
        path = self.current_path
        try:
            entries = os.listdir(path)
        except PermissionError:
            self._set_status("⛔ Permission denied")
            return
        except Exception as e:
            self._set_status(f"Error: {e}")
            return

        if not self.show_hidden:
            entries = [e for e in entries if not e.startswith(".")]

        items = []
        for name in entries:
            full = os.path.join(path, name)
            try:
                st = os.stat(full, follow_symlinks=False)
                is_d = os.path.isdir(full)
                items.append({
                    "name": name, "path": full, "is_dir": is_d,
                    "size": None if is_d else st.st_size,  # FIX: None for folders
                    "date": st.st_mtime,
                    "type": _type_name(name, is_d),
                    "icon": _icon(name, is_d),
                    "cat": _category(name, is_d),
                    "cat_color": _cat_color(name, is_d),
                })
            except (PermissionError, OSError):
                continue

        # FIX: safe sort key — handles None sizes
        key = self.sort_key
        rev = self.sort_rev

        def _sort_key(x):
            v = x[key]
            if v is None:
                return -1
            if isinstance(v, str):
                return v.lower()
            return v

        folders = sorted([i for i in items if i["is_dir"]],
                         key=_sort_key, reverse=rev)
        files = sorted([i for i in items if not i["is_dir"]],
                       key=_sort_key, reverse=rev)
        items = folders + files

        q = self.search_input.text.lower().strip()
        if q:
            items = [i for i in items if q in i["name"].lower()]

        if self.view_mode == "list":
            self.file_container.cols = 1
            for it in items:
                row = FileItemRow(
                    filepath=it["path"], name=it["name"],
                    is_dir=it["is_dir"],
                    size_str=_fmt_size(it["size"]),
                    date_str=_fmt_date(it["date"]),
                    type_str=it["type"], icon=it["icon"],
                    cat_color=it["cat_color"],
                    on_select=self._select_item,
                    on_open=self._open_item,
                )
                self.file_container.add_widget(row)
        else:
            cols = max(1, int(self.scroll.width / dp(112)))
            self.file_container.cols = cols
            for it in items:
                card = FileItemCard(
                    filepath=it["path"], name=it["name"],
                    is_dir=it["is_dir"], icon=it["icon"],
                    cat_color=it["cat_color"],
                    on_select=self._select_item,
                    on_open=self._open_item,
                )
                self.file_container.add_widget(card)

        nf = sum(1 for i in items if i["is_dir"])
        nfi = len(items) - nf
        tot = sum(i["size"] for i in items if i["size"] is not None)
        self._set_status(f"{nf} folders, {nfi} files  •  {_fmt_size(tot)}")

    # ──────────────────────────────────────────────────────
    #  SELECTION
    # ──────────────────────────────────────────────────────
    def _select_item(self, filepath, exclusive=True):
        if exclusive:
            self.selected = [filepath] if filepath not in self.selected else []
        else:
            if filepath in self.selected:
                self.selected.remove(filepath)
            else:
                self.selected.append(filepath)
        self._refresh_selection()
        self._update_preview()

    def _refresh_selection(self):
        for w in self.file_container.children:
            if hasattr(w, "is_selected"):
                w.is_selected = w.filepath in self.selected
        n = len(self.selected)
        sel = f"  •  {n} selected" if n else ""
        self.status_label.text = self._status_text + sel

    def select_all(self):
        for w in self.file_container.children:
            if hasattr(w, "filepath") and w.filepath not in self.selected:
                self.selected.append(w.filepath)
        self._refresh_selection()

    def invert_selection(self):
        new_sel = []
        for w in self.file_container.children:
            if hasattr(w, "filepath"):
                if w.filepath not in self.selected:
                    new_sel.append(w.filepath)
        self.selected = new_sel
        self._refresh_selection()

    # ──────────────────────────────────────────────────────
    #  OPEN
    # ──────────────────────────────────────────────────────
    def _open_item(self, filepath, is_dir):
        if is_dir:
            self._navigate(filepath)
        else:
            if filepath.lower().endswith((".zip", ".jar", ".apk")):
                self._offer_extract(filepath)
            else:
                _open_sys(filepath)

    def _offer_extract(self, filepath):
        def _do():
            self._extract_zip(filepath, self.current_path)
        self._confirm_dialog(
            "Extract Archive",
            f"Extract {os.path.basename(filepath)}\nto current folder?",
            on_confirm=_do,
            alt_label="Open Instead",
            alt_action=lambda: _open_sys(filepath))

    # ──────────────────────────────────────────────────────
    #  SORT / VIEW / HIDDEN / PREVIEW / THEME
    # ──────────────────────────────────────────────────────
    def _cycle_sort(self):
        order = ["name", "size", "date", "type"]
        idx = order.index(self.sort_key)
        if self.sort_rev:
            self.sort_rev = False
            idx = (idx + 1) % len(order)
            self.sort_key = order[idx]
        else:
            self.sort_rev = True
        arrow = "▼" if self.sort_rev else "▲"
        self.sort_btn.text = f"Sort:{self.sort_key.title()} {arrow}"
        self._list_dir()

    def _toggle_view(self):
        self.view_mode = "grid" if self.view_mode == "list" else "list"
        self.view_btn.text = "≡List" if self.view_mode == "grid" else "⊞Grid"
        self.list_header.height = dp(26) if self.view_mode == "list" else 0
        self.list_header.opacity = 1 if self.view_mode == "list" else 0
        self._list_dir()

    def _toggle_hidden(self):
        self.show_hidden = not self.show_hidden
        self.hidden_btn.text = "👁ON" if self.show_hidden else "👁Hidden"
        self._list_dir()

    def _toggle_preview(self):
        self.show_preview = not self.show_preview
        self.preview_panel.width = dp(260) if self.show_preview else dp(0)
        self.preview_btn.text = "◀Prev" if self.show_preview else "▶Prev"
        self._update_preview()

    def _toggle_theme(self):
        # FIX: use flag instead of broken `theme is DARK` identity check
        self._dark_mode = not self._dark_mode
        if self._dark_mode:
            theme.clear(); theme.update(DARK)
        else:
            theme.clear(); theme.update(LIGHT)
        self.theme_btn.text = "☀" if self._dark_mode else "🌙"
        Window.clearcolor = theme["bg"][:3] + [1]
        self.clear_widgets()
        self._build_ui()
        self._navigate_quiet(self.current_path)

    # ──────────────────────────────────────────────────────
    #  PREVIEW PANEL
    # ──────────────────────────────────────────────────────
    def _update_preview(self):
        if not self.show_preview:
            return
        self.preview_panel.clear_widgets()
        self._redraw_bg(self.preview_panel, theme["preview_bg"])

        if not self.selected:
            lbl = Label(text="Select a file\nto preview",
                        color=theme["text2"], font_size=sp(12),
                        halign="center", valign="middle")
            lbl.bind(size=lambda i, v: setattr(i, "text_size", v))
            self.preview_panel.add_widget(lbl)
            return

        path = self.selected[-1]
        name = os.path.basename(path)
        is_d = os.path.isdir(path)
        ext = os.path.splitext(name)[1].lower().lstrip(".")

        hdr = Label(text=f"{_icon(name, is_d)} {name}",
                    color=_cat_color(name, is_d), font_size=sp(12),
                    halign="center", valign="middle",
                    size_hint_y=None, height=dp(40))
        hdr.bind(size=lambda i, v: setattr(i, "text_size", v))
        self.preview_panel.add_widget(hdr)

        sep = BoxLayout(size_hint_y=None, height=dp(1))
        with sep.canvas.before:
            Color(*theme["accent"][:3], 0.3)
            Rectangle(pos=sep.pos, size=sep.size)
        sep.bind(pos=lambda i, v: self._update_bg_pos(i, v),
                 size=lambda i, v: self._update_bg_size(i, v))
        self.preview_panel.add_widget(sep)

        if is_d:
            count = _folder_count(path)
            info = f"📁 Folder\n\nContents: {count} items"
            if 0 < count <= 50:
                try:
                    items = sorted(os.listdir(path))[:20]
                    info += "\n\n" + "\n".join(f"  {i}" for i in items)
                    if count > 20:
                        info += f"\n  ... +{count - 20} more"
                except PermissionError:
                    info += "\n\n⛔ No access"
            lbl = Label(text=info, color=theme["text"], font_size=sp(10),
                        halign="left", valign="top")
            lbl.bind(size=lambda i, v: setattr(
                i, "text_size", (v[0] - dp(8), None)))
            sv = ScrollView()
            sv.add_widget(lbl)
            self.preview_panel.add_widget(sv)

        elif ext in ("png", "jpg", "jpeg", "gif", "bmp", "webp", "svg"):
            try:
                img = KivyImage(source=path, allow_stretch=True,
                                keep_ratio=True, size_hint_y=0.6)
                self.preview_panel.add_widget(img)
                try:
                    st = os.stat(path)
                    info = (f"Size: {_fmt_size(st.st_size)}\n"
                            f"Modified: {_fmt_date(st.st_mtime)}")
                except Exception:
                    info = ""
                if info:
                    lbl = Label(text=info, color=theme["text2"],
                                font_size=sp(9), halign="left", valign="top")
                    lbl.bind(size=lambda i, v: setattr(
                        i, "text_size", (v[0] - dp(8), None)))
                    self.preview_panel.add_widget(lbl)
            except Exception:
                lbl = Label(text="Cannot preview\nthis image",
                            color=theme["text2"], font_size=sp(11))
                self.preview_panel.add_widget(lbl)

        elif ext in ("txt", "md", "py", "js", "ts", "html", "css", "json",
                     "xml", "yaml", "yml", "toml", "ini", "cfg", "sh",
                     "bat", "log", "csv", "sql", "c", "cpp", "java", "rb",
                     "go", "rs", "swift", "kt", "php", "lua", "r"):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()[:80]
                content = "".join(lines)
                if len(content) > 5000:
                    content = content[:5000] + "\n... (truncated)"
                lbl = Label(text=content, color=theme["text"],
                            font_size=sp(9), halign="left", valign="top",
                            font_name="RobotoMono")
                lbl.bind(size=lambda i, v: setattr(
                    i, "text_size", (v[0] - dp(8), None)))
                sv = ScrollView()
                sv.add_widget(lbl)
                self.preview_panel.add_widget(sv)
            except Exception:
                lbl = Label(text="Cannot preview\nthis file",
                            color=theme["text2"], font_size=sp(11))
                self.preview_panel.add_widget(lbl)
        else:
            try:
                st = os.stat(path)
                info = (
                    f"📄 {ext.upper() if ext else 'File'}\n\n"
                    f"Size: {_fmt_size(st.st_size)}\n"
                    f"Modified: {_fmt_date(st.st_mtime)}\n"
                    f"Type: {_type_name(name, is_d)}"
                )
            except Exception:
                info = "No info available"
            lbl = Label(text=info, color=theme["text"], font_size=sp(10),
                        halign="left", valign="top")
            lbl.bind(size=lambda i, v: setattr(
                i, "text_size", (v[0] - dp(8), None)))
            self.preview_panel.add_widget(lbl)

    # ──────────────────────────────────────────────────────
    #  CLIPBOARD — Copy / Cut / Paste
    # ──────────────────────────────────────────────────────
    def copy_sel(self):
        if not self.selected:
            self._set_status("Nothing selected to copy")
            return
        self.clipboard_src = list(self.selected)
        self.clipboard_mode = "copy"
        n = len(self.clipboard_src)
        self._set_status(f"Copied {n} item(s)")

    def cut_sel(self):
        if not self.selected:
            self._set_status("Nothing selected to cut")
            return
        self.clipboard_src = list(self.selected)
        self.clipboard_mode = "cut"
        n = len(self.clipboard_src)
        self._set_status(f"Cut {n} item(s)")

    def paste(self):
        if not self.clipboard_src or not self.clipboard_mode:
            self._set_status("Nothing to paste")
            return
        dest = self.current_path
        conflicts = []
        for src in self.clipboard_src:
            name = os.path.basename(src)
            target = os.path.join(dest, name)
            if (os.path.exists(target) and
                    os.path.abspath(src) != os.path.abspath(target)):
                conflicts.append(name)

        if conflicts:
            self._paste_conflict_dialog(conflicts, dest)
        else:
            self._do_paste(dest, overwrite=False)

    def _paste_conflict_dialog(self, conflicts, dest):
        n = len(conflicts)
        names = ", ".join(conflicts[:5])
        if n > 5:
            names += f" … +{n - 5} more"
        msg = f"{n} file(s) already exist:\n{names}\n\nOverwrite all?"
        self._confirm_dialog(
            "Paste Conflict", msg,
            on_confirm=lambda: self._do_paste(dest, overwrite=True),
            on_cancel=lambda: self._do_paste(dest, overwrite=False))

    def _do_paste(self, dest, overwrite=False):
        errors = []
        for src in list(self.clipboard_src):
            name = os.path.basename(src)
            target = os.path.join(dest, name)
            if os.path.abspath(src) == os.path.abspath(target):
                continue
            if os.path.exists(target):
                if overwrite:
                    try:
                        if os.path.isdir(target):
                            shutil.rmtree(target)
                        else:
                            os.remove(target)
                    except Exception as e:
                        errors.append(f"{name}: {e}")
                        continue
                else:
                    continue
            try:
                if self.clipboard_mode == "copy":
                    if os.path.isdir(src):
                        shutil.copytree(src, target)
                    else:
                        shutil.copy2(src, target)
                elif self.clipboard_mode == "cut":
                    shutil.move(src, target)
            except Exception as e:
                errors.append(f"{name}: {e}")

        if self.clipboard_mode == "cut":
            self.clipboard_src = []
            self.clipboard_mode = ""

        if errors:
            self._show_msg("Paste Errors",
                           "Some items failed:\n" + "\n".join(errors[:10]))
        else:
            self._set_status("Paste complete")
        self.refresh()

    # ──────────────────────────────────────────────────────
    #  NEW FOLDER / NEW FILE
    # ──────────────────────────────────────────────────────
    def dlg_new_folder(self):
        self._input_dialog("New Folder", "Folder name",
                           lambda name: self._create_item(name, is_dir=True))

    def dlg_new_file(self):
        self._input_dialog("New File", "File name",
                           lambda name: self._create_item(name, is_dir=False))

    def _create_item(self, name, is_dir):
        if not name.strip():
            return
        target = os.path.join(self.current_path, name.strip())
        if os.path.exists(target):
            self._show_msg("Error", f"Already exists:\n{target}")
            return
        try:
            if is_dir:
                os.makedirs(target, exist_ok=True)
            else:
                Path(target).touch()
            self.refresh()
            self._set_status(
                f"Created {'folder' if is_dir else 'file'}: {name}")
        except Exception as e:
            self._show_msg("Error", str(e))

    # ──────────────────────────────────────────────────────
    #  RENAME
    # ──────────────────────────────────────────────────────
    def dlg_rename(self):
        if not self.selected:
            self._set_status("Select a file to rename")
            return
        path = self.selected[0]
        old_name = os.path.basename(path)
        self._input_dialog("Rename", "New name",
                           lambda name: self._do_rename(path, name),
                           initial=old_name)

    def _do_rename(self, old_path, new_name):
        if not new_name.strip():
            return
        new_path = os.path.join(os.path.dirname(old_path), new_name.strip())
        if new_path == old_path:
            return
        if os.path.exists(new_path):
            self._show_msg("Error", f"Already exists:\n{new_path}")
            return
        try:
            os.rename(old_path, new_path)
            self.selected = [new_path]
            self.refresh()
            self._set_status(f"Renamed to {new_name}")
        except Exception as e:
            self._show_msg("Error", str(e))

    # ──────────────────────────────────────────────────────
    #  DELETE / TRASH
    # ──────────────────────────────────────────────────────
    def dlg_delete(self):
        if not self.selected:
            self._set_status("Nothing selected")
            return
        n = len(self.selected)
        self._confirm_dialog(
            "Permanent Delete",
            f"Permanently delete {n} item(s)?\nThis cannot be undone.",
            on_confirm=self._do_delete)

    def _do_delete(self):
        errors = []
        for path in list(self.selected):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except Exception as e:
                errors.append(f"{os.path.basename(path)}: {e}")
        self.selected = []
        if errors:
            self._show_msg("Delete Errors", "\n".join(errors[:10]))
        self.refresh()

    def trash_sel(self):
        if not self.selected:
            self._set_status("Nothing selected")
            return
        try:
            from send2trash import send2trash
            has_trash = True
        except ImportError:
            has_trash = False

        if has_trash:
            errors = []
            for path in list(self.selected):
                try:
                    send2trash(path)
                except Exception as e:
                    errors.append(f"{os.path.basename(path)}: {e}")
            self.selected = []
            if errors:
                self._show_msg("Trash Errors", "\n".join(errors[:10]))
            self.refresh()
        else:
            self._confirm_dialog(
                "Trash Unavailable",
                "send2trash not installed.\nPermanently delete instead?",
                on_confirm=self._do_delete)

    # ──────────────────────────────────────────────────────
    #  ZIP / UNZIP
    # ──────────────────────────────────────────────────────
    def zip_sel(self):
        if not self.selected:
            self._set_status("Nothing selected to zip")
            return
        default_name = os.path.basename(self.selected[0]) + ".zip"
        self._input_dialog("Create ZIP", "Archive name",
                           lambda name: self._do_zip(name),
                           initial=default_name)

    def _do_zip(self, name):
        if not name.strip():
            return
        if not name.lower().endswith(".zip"):
            name += ".zip"
        zip_path = os.path.join(self.current_path, name)
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for src in self.selected:
                    if os.path.isdir(src):
                        for dirpath, dirnames, filenames in os.walk(src):
                            for f in filenames:
                                fp = os.path.join(dirpath, f)
                                arcname = os.path.relpath(
                                    fp, self.current_path)
                                zf.write(fp, arcname)
                    else:
                        arcname = os.path.relpath(src, self.current_path)
                        zf.write(src, arcname)
            self._set_status(f"Created {name}")
            self.refresh()
        except Exception as e:
            self._show_msg("ZIP Error", str(e))

    def unzip_sel(self):
        zips = [p for p in self.selected
                if p.lower().endswith((".zip", ".jar", ".apk"))]
        if not zips:
            self._set_status("No ZIP files selected")
            return
        for zp in zips:
            self._extract_zip(zp, self.current_path)
        self.refresh()

    def _extract_zip(self, zip_path, dest_dir):
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(dest_dir)
            self._set_status(f"Extracted {os.path.basename(zip_path)}")
        except Exception as e:
            self._show_msg("Extract Error", str(e))

    # ──────────────────────────────────────────────────────
    #  BOOKMARKS / RECENT
    # ──────────────────────────────────────────────────────
    def toggle_bookmark(self):
        path = self.current_path
        if path in self.bookmarks:
            self.bookmarks.remove(path)
            self._set_status(f"Bookmark removed: {path}")
        else:
            self.bookmarks.append(path)
            self._set_status(f"Bookmark added: {path}")
        _save_json("bookmarks.json", self.bookmarks)
        self._build_sidebar()

    def _add_recent(self, path):
        if path in self.recent:
            self.recent.remove(path)
        self.recent.insert(0, path)
        self.recent = self.recent[:20]
        _save_json("recent.json", self.recent)

    # ──────────────────────────────────────────────────────
    #  DEEP SEARCH
    # ──────────────────────────────────────────────────────
    def dlg_deep_search(self):
        self._input_dialog("Deep Search", "Search term (recursive)",
                           lambda term: self._run_deep_search(term))

    def _run_deep_search(self, term):
        if not term.strip():
            return
        self._set_status(f"Searching for '{term}'…")

        def _search():
            results = []
            try:
                for dirpath, dirnames, filenames in os.walk(
                        self.current_path):
                    for f in filenames:
                        if term.lower() in f.lower():
                            results.append(os.path.join(dirpath, f))
                    for d in dirnames:
                        if term.lower() in d.lower():
                            results.append(os.path.join(dirpath, d))
            except Exception:
                pass
            return results

        def _run_thread():
            results = _search()
            Clock.schedule_once(lambda _: _show_results(results))

        def _show_results(results):
            n = len(results)
            if n == 0:
                self._show_msg("Deep Search", f"No results for '{term}'")
            elif n <= 50:
                text = "\n".join(results)
                self._show_msg(f"Deep Search ({n} results)", text)
            else:
                text = "\n".join(results[:50]) + f"\n… +{n - 50} more"
                self._show_msg(f"Deep Search ({n} results)", text)
            self._set_status(f"Deep search: {n} result(s)")

        t = threading.Thread(target=_run_thread, daemon=True)
        t.start()

    # ──────────────────────────────────────────────────────
    #  DUPLICATE FINDER
    # ──────────────────────────────────────────────────────
    def find_duplicates(self):
        self._set_status("Scanning for duplicates…")

        def _scan():
            size_map = {}
            try:
                for dirpath, dirnames, filenames in os.walk(
                        self.current_path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        try:
                            s = os.path.getsize(fp)
                        except OSError:
                            continue
                        if s == 0:
                            continue
                        size_map.setdefault(s, []).append(fp)
            except Exception:
                pass

            dupes = {}
            for size, paths in size_map.items():
                if len(paths) < 2:
                    continue
                hash_map = {}
                for p in paths:
                    h = _calc_hash(p, "md5")
                    if h != "Error":
                        hash_map.setdefault(h, []).append(p)
                for h, hpaths in hash_map.items():
                    if len(hpaths) >= 2:
                        dupes.setdefault(size, []).extend(hpaths)
            return dupes

        def _run_thread():
            dupes = _scan()
            Clock.schedule_once(lambda _: _show_dupes(dupes))

        def _show_dupes(dupes):
            if not dupes:
                self._show_msg("Duplicates", "No duplicates found.")
                self._set_status("No duplicates found")
                return
            lines = []
            total_wasted = 0
            for size, paths in dupes.items():
                total_wasted += size * (len(paths) - 1)
                lines.append(
                    f"--- {len(paths)} files × {_fmt_size(size)} ---")
                for p in paths:
                    lines.append(f"  {p}")
            if total_wasted > 0:
                lines.append(f"\nWasted space: {_fmt_size(total_wasted)}")
            text = "\n".join(lines[:80])
            if len(lines) > 80:
                text += f"\n… +{len(lines) - 80} more"
            self._show_msg("Duplicate Files", text)
            self._set_status(
                f"Found duplicates — {_fmt_size(total_wasted)} wasted")

        t = threading.Thread(target=_run_thread, daemon=True)
        t.start()

    # ──────────────────────────────────────────────────────
    #  OPEN TERMINAL
    # ──────────────────────────────────────────────────────
    def open_terminal(self):
        s = platform.system()
        path = self.current_path
        try:
            if s == "Windows":
                subprocess.Popen(
                    ["cmd", "/K", f"cd /D {path}"],
                    creationflags=subprocess.CREATE_NEW_CONSOLE)
            elif s == "Darwin":
                script = (f'tell application "Terminal"\n'
                          f'do script "cd \'{path}\'"\n'
                          f'end tell')
                subprocess.Popen(["osascript", "-e", script])
            else:
                for term_cmd in [
                    ["gnome-terminal", "--working-directory", path],
                    ["konsole", "--workdir", path],
                    ["xfce4-terminal", "--working-directory", path],
                    ["xterm", "-e", f"cd '{path}' && $SHELL"],
                ]:
                    try:
                        subprocess.Popen(term_cmd)
                        break
                    except FileNotFoundError:
                        continue
            self._set_status(f"Terminal opened at {path}")
        except Exception as e:
            self._show_msg("Terminal Error", str(e))

    # ──────────────────────────────────────────────────────
    #  CONTEXT MENU
    # ──────────────────────────────────────────────────────
    def _show_context_menu(self, wx, wy):
        self._dismiss_context_menu()
        if self.selected:
            path = self.selected[0]
            is_d = os.path.isdir(path)
            items = [
                ("📂 Open", lambda: self._open_item(path, is_d)),
                ("📋 Copy", self.copy_sel),
                ("✂  Cut", self.cut_sel),
                ("✏ Rename", self.dlg_rename),
                ("🗑 Delete", self.dlg_delete),
                ("♻  Trash", self.trash_sel),
                ("📦 Add to ZIP", self.zip_sel),
                ("📄 Properties", lambda: self._show_properties(path)),
            ]
        else:
            items = [
                ("📁+ New Folder", self.dlg_new_folder),
                ("📄+ New File", self.dlg_new_file),
                ("📌 Paste", self.paste),
                ("🔄 Refresh", self.refresh),
                ("🔍 Deep Search", self.dlg_deep_search),
                ("🔖 Toggle Bookmark", self.toggle_bookmark),
                ("💻 Open Terminal", self.open_terminal),
            ]
        self._ctx_menu = ContextMenu(items, (wx, wy))
        self.add_widget(self._ctx_menu)

    def _dismiss_context_menu(self):
        if self._ctx_menu and self._ctx_menu.parent:
            self.remove_widget(self._ctx_menu)
        self._ctx_menu = None

    # ──────────────────────────────────────────────────────
    #  FILE PROPERTIES
    # ──────────────────────────────────────────────────────
    def _show_properties(self, path):
        name = os.path.basename(path)
        is_d = os.path.isdir(path)
        try:
            st = os.stat(path)
            size = st.st_size if not is_d else _folder_size(path)
            info = (
                f"{_icon(name, is_d)} {name}\n\n"
                f"Path: {path}\n"
                f"Type: {_type_name(name, is_d)}\n"
                f"Size: {_fmt_size(size)}\n"
                f"Modified: {_fmt_date(st.st_mtime)}\n"
                f"Accessed: {_fmt_date(st.st_atime)}\n"
            )
            if not is_d and size is not None and size < 50 * 1024 * 1024:
                md5 = _calc_hash(path, "md5")
                sha = _calc_hash(path, "sha256")
                info += f"\nMD5:    {md5}\nSHA256: {sha}"
            elif not is_d:
                info += "\n(Hashes skipped — file too large)"
        except Exception as e:
            info = f"Error reading file:\n{e}"
        self._show_msg(f"Properties — {name}", info)

    # ──────────────────────────────────────────────────────
    #  KEYBOARD SHORTCUTS
    # ──────────────────────────────────────────────────────
    def _on_key(self, window, key, scancode, codepoint, modifier):
        # Don't intercept when typing in text inputs
        if (hasattr(self, 'path_input') and self.path_input.focus) or \
           (hasattr(self, 'search_input') and self.search_input.focus):
            return False

        if key == 294:  # F5
            self.refresh()
            return True
        elif key == 293:  # F4
            self.open_terminal()
            return True
        elif key == 290:  # F1
            self._show_help()
            return True
        elif codepoint == 'a' and 'ctrl' in modifier:
            self.select_all()
            return True
        elif codepoint == 'i' and 'ctrl' in modifier:
            self.invert_selection()
            return True
        elif codepoint == 'c' and 'ctrl' in modifier:
            self.copy_sel()
            return True
        elif codepoint == 'x' and 'ctrl' in modifier:
            self.cut_sel()
            return True
        elif codepoint == 'v' and 'ctrl' in modifier:
            self.paste()
            return True
        elif codepoint == 'h' and 'ctrl' in modifier:
            self._toggle_hidden()
            return True
        elif key == 8:  # Backspace
            self.go_up()
            return True
        elif key == 13:  # Enter
            if self.selected:
                path = self.selected[0]
                is_d = os.path.isdir(path)
                self._open_item(path, is_d)
            return True
        elif key == 46:  # Delete
            self.dlg_delete()
            return True
        return False

    def _on_mouse(self, window, x, y, button, modifiers):
        if button == 'right':
            if hasattr(self, 'scroll') and \
                    self.scroll.collide_point(*self.scroll.to_widget(x, y)):
                self._show_context_menu(x, y)
                return True
        if button == 'left':
            self._dismiss_context_menu()
        return False

    def _show_help(self):
        help_text = (
            "Keyboard Shortcuts:\n\n"
            "Ctrl+C: Copy\n"
            "Ctrl+X: Cut\n"
            "Ctrl+V: Paste\n"
            "Ctrl+A: Select All\n"
            "Ctrl+I: Invert Selection\n"
            "Ctrl+H: Toggle Hidden Files\n"
            "Delete: Delete selected\n"
            "Backspace: Go Up\n"
            "Enter: Open selected\n"
            "F5: Refresh\n"
            "F4: Terminal\n"
            "F1: Help\n"
        )
        self._show_msg("Help — Keyboard Shortcuts", help_text)

    # ──────────────────────────────────────────────────────
    #  DIALOGS
    # ──────────────────────────────────────────────────────
    def _show_msg(self, title, message, on_confirm=None):
        content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        lbl = Label(text=message, color=theme["text"], font_size=sp(12),
                    halign="left", valign="top")
        lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0] - dp(8), None)))
        content.add_widget(lbl)

        btn_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
        ok_btn = Button(text="OK", background_color=theme["accent"],
                        color=theme["text"], background_normal="")
        btn_row.add_widget(ok_btn)
        content.add_widget(btn_row)

        popup = Popup(title=title, content=content,
                      size_hint=(0.6, 0.4),
                      background_color=theme["bg3"],
                      separator_color=theme["accent"],
                      title_color=theme["text"])

        ok_btn.bind(on_release=lambda _: popup.dismiss())

        if on_confirm:
            popup.bind(on_dismiss=lambda _: on_confirm())

        popup.open()

    def _input_dialog(self, title, hint, callback, initial=""):
        content = BoxLayout(orientation='vertical',
                            padding=dp(10), spacing=dp(10))
        ti = TextInput(text=initial, hint_text=hint, multiline=False,
                       font_size=sp(13), background_color=theme["bg3"],
                       foreground_color=theme["text"],
                       cursor_color=theme["accent"])
        content.add_widget(ti)

        btn_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(5))

        def _ok(instance):
            callback(ti.text.strip())
            popup.dismiss()

        def _cancel(instance):
            popup.dismiss()

        ok_btn = Button(text="OK", background_color=theme["accent"],
                        color=theme["text"])
        cancel_btn = Button(text="Cancel",
                            background_color=theme["bg3"],
                            color=theme["text"])
        ok_btn.bind(on_release=_ok)
        cancel_btn.bind(on_release=_cancel)

        btn_row.add_widget(Widget())
        btn_row.add_widget(ok_btn)
        btn_row.add_widget(cancel_btn)
        content.add_widget(btn_row)

        popup = Popup(title=title, content=content,
                      size_hint=(0.6, 0.35),
                      background=theme["bg2"],
                      title_color=theme["text"],
                      separator_color=theme["accent"])
        ti.bind(on_text_validate=lambda _: _ok(None))
        popup.open()
        Clock.schedule_once(lambda _: setattr(ti, 'focus', True), 0.1)

    def _confirm_dialog(self, title, message, on_confirm, on_cancel=None,
                        alt_label=None, alt_action=None):
        content = BoxLayout(orientation='vertical',
                            padding=dp(10), spacing=dp(10))
        lbl = Label(text=message, color=theme["text"], font_size=sp(12),
                    halign="left", valign="middle")
        lbl.bind(size=lambda i, v: setattr(i, "text_size", (v[0], None)))
        content.add_widget(lbl)

        btn_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(5))

        def _do_confirm(instance):
            popup.dismiss()
            on_confirm()

        def _do_cancel(instance):
            popup.dismiss()
            if on_cancel:
                on_cancel()

        def _do_alt(instance):
            popup.dismiss()
            if alt_action:
                alt_action()

        confirm_btn = Button(text="Confirm",
                             background_color=theme["accent"],
                             color=theme["text"])
        cancel_btn = Button(text="Cancel",
                            background_color=theme["bg3"],
                            color=theme["text"])
        confirm_btn.bind(on_release=_do_confirm)
        cancel_btn.bind(on_release=_do_cancel)

        btn_row.add_widget(Widget())
        btn_row.add_widget(confirm_btn)
        if alt_label:
            alt_btn = Button(text=alt_label,
                             background_color=theme["bg3"],
                             color=theme["text"])
            alt_btn.bind(on_release=_do_alt)
            btn_row.add_widget(alt_btn)
        btn_row.add_widget(cancel_btn)

        content.add_widget(btn_row)
        popup = Popup(title=title, content=content,
                      size_hint=(0.6, 0.4),
                      background=theme["bg2"],
                      title_color=theme["text"],
                      separator_color=theme["accent"])
        popup.open()


# ═══════════════════════════════════════════════════════════════
#  APP ENTRY POINT
# ═══════════════════════════════════════════════════════════════
class FileManagerApp(App):
    def build(self):
        Window.clearcolor = theme["bg"][:3] + [1]
        return FileManager()


if __name__ == "__main__":
    FileManagerApp().run()