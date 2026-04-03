#!/usr/bin/env python
"""
C/H File Encoding Converter — GUI
드래그 앤 드롭으로 파일/폴더를 추가하고 UTF-8로 변환합니다.
"""

import os
import sys
import shutil
import datetime
import threading
import ctypes
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from app_version import APP_NAME, APP_VERSION, APP_AUTHOR, APP_EMAIL

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

# ─────────────────────────────────────────────
#  색상 팔레트 (모던 블루)
# ─────────────────────────────────────────────
C = {
    "bg":          "#F0F4F8",
    "bg_dark":     "#E2E8F0",
    "card":        "#FFFFFF",
    "border":      "#CBD5E1",
    "primary":     "#2563EB",
    "primary_hov": "#1D4ED8",
    "primary_fg":  "#FFFFFF",
    "success":     "#16A34A",
    "warning":     "#B45309",
    "error":       "#DC2626",
    "skip":        "#64748B",
    "text":        "#1E293B",
    "text_sub":    "#64748B",
    "drop_bg":     "#EFF6FF",
    "drop_border": "#93C5FD",
    "header_bg":   "#1E3A5F",
    "header_fg":   "#FFFFFF",
    "row_alt":     "#F8FAFC",
    "sel":         "#DBEAFE",
}

FONT_UI      = ("Segoe UI", 11)
FONT_BOLD    = ("Segoe UI", 11, "bold")
FONT_H1      = ("Segoe UI", 15, "bold")
FONT_MONO    = ("Consolas", 11)
FONT_CAPTION = ("Segoe UI", 10)
FONT_BADGE   = ("Segoe UI", 9, "bold")

# ─────────────────────────────────────────────
#  인코딩 감지 (convert.py 와 동일 로직)
# ─────────────────────────────────────────────
DETECT_ORDER = [
    ("utf-8-sig", "UTF-8 BOM"),
    ("utf-8",     "UTF-8"),
    ("cp949",     "CP949 / EUC-KR"),
    ("euc-kr",    "EUC-KR"),
    ("latin-1",   "Latin-1"),
]


def resource_path(*parts: str) -> Path:
    """
    개발 환경과 PyInstaller 번들 환경 모두에서 리소스 경로를 반환.
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


def build_backup_path(path: Path, backup_stamp: str) -> Path:
    """
    원본 파일과 같은 폴더에 백업 파일 경로를 만든다.
    예: main.c -> main_backup_20260403_091500.c
    """
    return path.with_name(f"{path.stem}_backup_{backup_stamp}{path.suffix}")


def enable_high_dpi():
    """
    Windows에서 DPI virtualization으로 흐릿해지는 현상을 줄인다.
    """
    if sys.platform != "win32":
        return

    user32 = getattr(ctypes.windll, "user32", None)
    shcore = getattr(ctypes.windll, "shcore", None)

    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        return
    except Exception:
        pass

    try:
        shcore.SetProcessDpiAwareness(1)
        return
    except Exception:
        pass

    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass


def apply_tk_scaling(root: tk.Tk):
    """
    현재 디스플레이 DPI에 맞춰 Tk 스케일을 적용한다.
    """
    try:
        scaling = root.winfo_fpixels("1i") / 72.0
        if scaling > 1.0:
            root.tk.call("tk", "scaling", scaling)
    except Exception:
        pass

def detect_encoding(raw: bytes):
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return "utf-16", "UTF-16 BOM"
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig", "UTF-8 BOM"
    for enc, label in DETECT_ORDER:
        try:
            raw.decode(enc)
            return enc, label
        except (UnicodeDecodeError, LookupError):
            continue
    try:
        import chardet
        r = chardet.detect(raw)
        e, c = r.get("encoding"), r.get("confidence", 0)
        if e and c > 0.5:
            return e, f"chardet({e})"
    except ImportError:
        pass
    return None, "감지 실패"

def is_utf8_clean(raw: bytes) -> bool:
    if raw.startswith(b"\xef\xbb\xbf"):
        return False
    try:
        raw.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False

def decode_preview(raw: bytes, enc: str, lines: int = 40) -> str:
    try:
        text = raw.decode(enc, errors="replace")
        return "\n".join(text.splitlines()[:lines])
    except Exception:
        return "(미리보기 불가)"

# ─────────────────────────────────────────────
#  파일 항목 데이터 클래스
# ─────────────────────────────────────────────
class FileItem:
    STATUS_CONVERT = "변환 예정"
    STATUS_SKIP    = "이미 UTF-8"
    STATUS_ERROR   = "오류"
    STATUS_DONE    = "완료"
    STATUS_FAILED  = "실패"

    def __init__(self, path: Path):
        self.path = path
        raw = path.read_bytes()
        self.raw = raw
        if is_utf8_clean(raw):
            self.enc, self.enc_label = "utf-8", "UTF-8"
            self.status = self.STATUS_SKIP
        else:
            self.enc, self.enc_label = detect_encoding(raw)
            self.status = self.STATUS_CONVERT if self.enc else self.STATUS_ERROR
        self.error_msg = ""

    @property
    def arrow(self):
        return f"{self.enc_label} → UTF-8" if self.status == self.STATUS_CONVERT else self.enc_label

    def convert(self, backup_stamp: str | None):
        if self.status not in (self.STATUS_CONVERT,):
            return
        try:
            text = self.raw.decode(self.enc)
        except Exception as e:
            self.status = self.STATUS_FAILED
            self.error_msg = str(e)
            return
        if backup_stamp:
            try:
                dest = build_backup_path(self.path, backup_stamp)
                shutil.copy2(self.path, dest)
            except Exception:
                pass
        try:
            self.path.write_bytes(text.encode("utf-8"))
            self.status = self.STATUS_DONE
        except Exception as e:
            self.status = self.STATUS_FAILED
            self.error_msg = str(e)

# ─────────────────────────────────────────────
#  커스텀 위젯
# ─────────────────────────────────────────────
class HoverButton(tk.Button):
    def __init__(self, master, **kw):
        self._bg     = kw.pop("bg",     C["primary"])
        self._bg_hov = kw.pop("bg_hov", C["primary_hov"])
        self._fg     = kw.pop("fg",     C["primary_fg"])
        super().__init__(master, bg=self._bg, fg=self._fg,
                         activebackground=self._bg_hov, activeforeground=self._fg,
                         relief="flat", cursor="hand2", **kw)
        self.bind("<Enter>", lambda e: self.config(bg=self._bg_hov))
        self.bind("<Leave>", lambda e: self.config(bg=self._bg))

class SmallButton(HoverButton):
    def __init__(self, master, **kw):
        kw.setdefault("font",    FONT_UI)
        kw.setdefault("padx",   10)
        kw.setdefault("pady",    4)
        kw.setdefault("bd",      0)
        super().__init__(master, **kw)

class BigButton(HoverButton):
    def __init__(self, master, **kw):
        kw.setdefault("font",   ("Segoe UI", 12, "bold"))
        kw.setdefault("padx",   24)
        kw.setdefault("pady",    8)
        kw.setdefault("bd",      0)
        super().__init__(master, **kw)

# ─────────────────────────────────────────────
#  메인 앱
# ─────────────────────────────────────────────
class App:
    EXTENSIONS = (".c", ".h", ".cpp", ".hpp")

    def __init__(self, root: tk.Tk):
        self.root = root
        self.items: list[FileItem] = []
        self.selected_item: FileItem | None = None
        self._setup_window()
        self._build_ui()
        self._configure_dnd()

    # ── 윈도우 기본 설정
    def _setup_window(self):
        self.root.title(f"{APP_NAME}  ·  C/H 파일 인코딩 변환기")
        self._set_initial_geometry()
        self.root.configure(bg=C["bg"])
        self._icon_image = None
        self._apply_icon()

    def _set_initial_geometry(self):
        """
        첫 실행 시 현재 화면에 맞춰 창 크기를 잡는다.
        Windows에서는 시작부터 넉넉하게 보이도록 최대화 우선.
        """
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        min_w = min(960, max(820, screen_w - 120))
        min_h = min(700, max(620, screen_h - 120))
        self.root.minsize(min_w, min_h)

        if sys.platform == "win32":
            try:
                self.root.state("zoomed")
                return
            except Exception:
                pass

        width = min(1400, max(min_w, int(screen_w * 0.92)))
        height = min(940, max(min_h, int(screen_h * 0.88)))
        width = min(width, max(min_w, screen_w - 40))
        height = min(height, max(min_h, screen_h - 80))

        pos_x = max(0, (screen_w - width) // 2)
        pos_y = max(0, (screen_h - height) // 3)
        self.root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

    def _apply_icon(self):
        """
        PNG 아이콘을 우선 사용한다.
        PyInstaller 번들에서는 assets/icon.png 를 함께 포함해야 한다.
        """
        icon_png = resource_path("assets", "icon.png")
        if not icon_png.exists():
            return

        try:
            self._icon_image = tk.PhotoImage(file=str(icon_png))
            self.root.iconphoto(True, self._icon_image)
        except Exception:
            pass

    # ── 전체 UI 구성
    def _build_ui(self):
        self._build_header()

        body = tk.Frame(self.root, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self._build_drop_zone(body)

        mid = tk.Frame(body, bg=C["bg"])
        mid.pack(fill="both", expand=True, pady=(12, 0))
        mid.columnconfigure(0, weight=3)
        mid.columnconfigure(1, weight=2)
        mid.rowconfigure(0, weight=1)

        self._build_file_list(mid)
        self._build_preview(mid)
        self._build_footer(body)

    # ── 헤더
    def _build_header(self):
        hdr = tk.Frame(self.root, bg=C["header_bg"], height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        info_btn = tk.Button(
            hdr,
            text="ⓘ",
            command=self._show_about_info,
            font=("Segoe UI Symbol", 15, "bold"),
            bg="#16324D",
            fg="#BFDBFE",
            activebackground="#21405F",
            activeforeground="#E2E8F0",
            relief="flat",
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
        )
        info_btn.pack(side="right", padx=(12, 16), pady=10)

        icon = tk.Label(hdr, text="⟳", font=("Segoe UI", 22, "bold"),
                        bg=C["header_bg"], fg="#60A5FA")
        icon.pack(side="left", padx=(18, 6), pady=8)

        tk.Label(hdr, text=APP_NAME, font=FONT_H1,
                 bg=C["header_bg"], fg=C["header_fg"]).pack(side="left", pady=8)
        tk.Label(hdr, text="C / H 파일 인코딩 감지 · UTF-8 변환",
                 font=FONT_CAPTION, bg=C["header_bg"],
                 fg="#94A3B8").pack(side="left", padx=(10, 0), pady=8)

    def _show_about_info(self):
        messagebox.showinfo(
            "정보",
            f"{APP_NAME}\n\n"
            f"버전: v{APP_VERSION}\n"
            f"작성자: {APP_AUTHOR}\n"
            f"이메일: {APP_EMAIL}",
        )

    # ── 드롭 존
    def _build_drop_zone(self, parent):
        outer = tk.Frame(parent, bg=C["drop_border"], bd=0)
        outer.pack(fill="x", pady=(12, 0))

        inner = tk.Frame(outer, bg=C["drop_bg"], pady=14)
        inner.pack(fill="x", padx=2, pady=2)

        lbl_icon = tk.Label(inner, text="📂", font=("Segoe UI", 24),
                            bg=C["drop_bg"])
        lbl_icon.pack(side="left", padx=(20, 8))

        txt_frame = tk.Frame(inner, bg=C["drop_bg"])
        txt_frame.pack(side="left", fill="y")

        tk.Label(txt_frame, text="파일이나 폴더를 여기에 끌어다 놓으세요",
                 font=FONT_BOLD, bg=C["drop_bg"], fg=C["text"]).pack(anchor="w")
        tk.Label(txt_frame, text="또는 아래 버튼을 클릭하세요",
                 font=FONT_CAPTION, bg=C["drop_bg"],
                 fg=C["text_sub"]).pack(anchor="w")

        btn_frame = tk.Frame(inner, bg=C["drop_bg"])
        btn_frame.pack(side="right", padx=20)

        SmallButton(btn_frame, text="📁  폴더 선택",
                    command=self._browse_folder).pack(side="left", padx=4)
        SmallButton(btn_frame, text="📄  파일 추가",
                    bg=C["bg_dark"], bg_hov="#CBD5E1",
                    fg=C["text"],
                    command=self._browse_files).pack(side="left", padx=4)
        SmallButton(btn_frame, text="🗑  목록 지우기",
                    bg="#FEE2E2", bg_hov="#FECACA",
                    fg=C["error"],
                    command=self._clear_list).pack(side="left", padx=4)

        self.drop_zone = outer

    # ── 파일 목록 (Treeview)
    def _build_file_list(self, parent):
        card = tk.Frame(parent, bg=C["card"],
                        highlightbackground=C["border"], highlightthickness=1)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # 헤더
        hdr = tk.Frame(card, bg=C["primary"], pady=8)
        hdr.pack(fill="x")
        self.list_title = tk.Label(hdr, text="📋  파일 목록  (0)",
                                   font=FONT_BOLD, bg=C["primary"],
                                   fg=C["primary_fg"])
        self.list_title.pack(side="left", padx=14)

        # Treeview
        cols = ("name", "encoding", "status")
        self.tree = ttk.Treeview(card, columns=cols, show="headings",
                                 selectmode="browse")
        self.tree.heading("name",     text="파일명")
        self.tree.heading("encoding", text="인코딩")
        self.tree.heading("status",   text="상태")
        self.tree.column("name",     width=200, minwidth=120)
        self.tree.column("encoding", width=160, minwidth=100)
        self.tree.column("status",   width=90,  minwidth=70)

        vsb = ttk.Scrollbar(card, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(card, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right",  fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # row 태그 색상
        self.tree.tag_configure("convert", foreground=C["primary"])
        self.tree.tag_configure("skip",    foreground=C["skip"])
        self.tree.tag_configure("error",   foreground=C["error"])
        self.tree.tag_configure("done",    foreground=C["success"])
        self.tree.tag_configure("failed",  foreground=C["error"])

        # treeview 스타일
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=C["card"],
                        fieldbackground=C["card"],
                        foreground=C["text"],
                        rowheight=30,
                        font=FONT_UI)
        style.configure("Treeview.Heading",
                        background=C["bg_dark"],
                        foreground=C["text"],
                        font=FONT_BOLD,
                        relief="flat")
        style.map("Treeview",
                  background=[("selected", C["sel"])],
                  foreground=[("selected", C["primary"])])

    # ── 미리보기 패널
    def _build_preview(self, parent):
        card = tk.Frame(parent, bg=C["card"],
                        highlightbackground=C["border"], highlightthickness=1)
        card.grid(row=0, column=1, sticky="nsew")

        hdr = tk.Frame(card, bg=C["primary"], pady=8)
        hdr.pack(fill="x")
        self.prev_title = tk.Label(hdr, text="🔍  미리보기",
                                   font=FONT_BOLD, bg=C["primary"],
                                   fg=C["primary_fg"])
        self.prev_title.pack(side="left", padx=14)

        # 인코딩 정보 배지
        self.prev_badge = tk.Label(hdr, text="",
                                   font=FONT_BADGE,
                                   bg="#1D4ED8", fg="#BFDBFE",
                                   padx=8, pady=2)
        self.prev_badge.pack(side="left", padx=6)

        # 파일 경로
        self.prev_path = tk.Label(card, text="← 파일을 선택하면 내용이 표시됩니다",
                                  font=FONT_CAPTION, bg=C["bg_dark"],
                                  fg=C["text_sub"], anchor="w", padx=8, pady=4)
        self.prev_path.pack(fill="x")

        # 텍스트
        txt_frame = tk.Frame(card, bg=C["card"])
        txt_frame.pack(fill="both", expand=True)

        self.prev_text = tk.Text(txt_frame,
                                 font=FONT_MONO,
                                 bg="#1E1E2E", fg="#CDD6F4",
                                 insertbackground="#CDD6F4",
                                 relief="flat", bd=0,
                                 wrap="none", state="disabled",
                                 selectbackground="#313244")
        vsb2 = ttk.Scrollbar(txt_frame, orient="vertical",
                              command=self.prev_text.yview)
        hsb2 = ttk.Scrollbar(txt_frame, orient="horizontal",
                              command=self.prev_text.xview)
        self.prev_text.configure(yscrollcommand=vsb2.set,
                                 xscrollcommand=hsb2.set)
        vsb2.pack(side="right", fill="y")
        hsb2.pack(side="bottom", fill="x")
        self.prev_text.pack(fill="both", expand=True)

        # 행 번호 색상 태그
        self.prev_text.tag_configure("lineno", foreground="#585B70")
        self.prev_text.tag_configure("korean", foreground="#89DCEB")

    # ── 푸터 (옵션 + 변환 버튼 + 상태바)
    def _build_footer(self, parent):
        footer = tk.Frame(parent, bg=C["bg"])
        footer.pack(fill="x", pady=(12, 0))

        # 옵션
        opt = tk.Frame(footer, bg=C["bg"])
        opt.pack(side="left")

        self.var_recursive = tk.BooleanVar(value=True)
        self.var_backup    = tk.BooleanVar(value=True)

        self._chk(opt, "📁  하위 폴더 포함", self.var_recursive).pack(side="left", padx=(0, 16))
        self._chk(opt, "💾  백업 생성",       self.var_backup).pack(side="left")

        # 상태 레이블
        self.status_var = tk.StringVar(value="대기 중")
        tk.Label(footer, textvariable=self.status_var,
                 font=FONT_CAPTION, bg=C["bg"],
                 fg=C["text_sub"]).pack(side="left", padx=20)

        # 변환 버튼
        self.convert_btn = BigButton(footer, text="⟳   UTF-8 로 변환",
                                     command=self._start_convert)
        self.convert_btn.pack(side="right")

        # 진행바
        self.progress = ttk.Progressbar(footer, length=160,
                                         mode="determinate")
        self.progress.pack(side="right", padx=(0, 12))

    def _chk(self, parent, text, var):
        return tk.Checkbutton(parent, text=text, variable=var,
                              font=FONT_UI, bg=C["bg"], fg=C["text"],
                              activebackground=C["bg"],
                              selectcolor=C["card"],
                              cursor="hand2")

    # ── Drag & Drop 설정
    def _configure_dnd(self):
        if not DND_AVAILABLE:
            return
        self.drop_zone.drop_target_register(DND_FILES)
        self.drop_zone.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event):
        # 윈도우 DnD 경로는 중괄호로 감싸진 경우 있음
        raw = event.data.strip()
        paths = self.root.tk.splitlist(raw)
        for p in paths:
            self._add_path(Path(p))

    # ── 파일/폴더 추가
    def _browse_folder(self):
        d = filedialog.askdirectory(title="폴더 선택")
        if d:
            self._add_path(Path(d))

    def _browse_files(self):
        files = filedialog.askopenfilenames(
            title="파일 선택",
            filetypes=[("C/H 소스 파일", "*.c *.h *.cpp *.hpp"),
                       ("모든 파일", "*.*")])
        for f in files:
            self._add_path(Path(f))

    def _add_path(self, path: Path):
        recursive = self.var_recursive.get()
        if path.is_file():
            self._add_file(path)
        elif path.is_dir():
            pattern = "**/*" if recursive else "*"
            for ext in self.EXTENSIONS:
                for fp in sorted(path.glob(f"{pattern}{ext}")):
                    self._add_file(fp)
        self._refresh_list()

    def _add_file(self, path: Path):
        # 중복 방지
        if any(it.path == path for it in self.items):
            return
        try:
            item = FileItem(path)
            self.items.append(item)
        except Exception as e:
            pass

    def _clear_list(self):
        self.items.clear()
        self.selected_item = None
        self._refresh_list()
        self._show_preview(None)

    # ── 목록 갱신
    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for idx, it in enumerate(self.items):
            tag = {
                FileItem.STATUS_CONVERT: "convert",
                FileItem.STATUS_SKIP:    "skip",
                FileItem.STATUS_ERROR:   "error",
                FileItem.STATUS_DONE:    "done",
                FileItem.STATUS_FAILED:  "failed",
            }.get(it.status, "skip")

            icon = {
                "convert": "🔄",
                "skip":    "✓",
                "error":   "✗",
                "done":    "✅",
                "failed":  "❌",
            }.get(tag, "·")

            self.tree.insert("", "end", iid=str(idx),
                             values=(f"{icon}  {it.path.name}",
                                     it.enc_label,
                                     it.status),
                             tags=(tag,))

        cnt = len(self.items)
        conv = sum(1 for i in self.items if i.status == FileItem.STATUS_CONVERT)
        self.list_title.config(text=f"📋  파일 목록  ({cnt}개, 변환 대상 {conv}개)")
        self._update_status()

    # ── 선택 이벤트
    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        self.selected_item = self.items[idx]
        self._show_preview(self.selected_item)

    # ── 미리보기 표시
    def _show_preview(self, item: FileItem | None):
        self.prev_text.config(state="normal")
        self.prev_text.delete("1.0", "end")

        if item is None:
            self.prev_title.config(text="🔍  미리보기")
            self.prev_badge.config(text="")
            self.prev_path.config(text="← 파일을 선택하면 내용이 표시됩니다")
            self.prev_text.config(state="disabled")
            return

        self.prev_title.config(text=f"🔍  {item.path.name}")
        self.prev_badge.config(text=f" {item.enc_label} ")
        self.prev_path.config(text=str(item.path))

        enc = item.enc or "utf-8"
        content = decode_preview(item.raw, enc, lines=60)

        for lineno, line in enumerate(content.splitlines(), start=1):
            # 행 번호
            self.prev_text.insert("end", f"{lineno:4d}  ", "lineno")
            # 내용
            self.prev_text.insert("end", line + "\n")

        self.prev_text.config(state="disabled")
        self.prev_text.see("1.0")

    # ── 상태바 업데이트
    def _update_status(self):
        total   = len(self.items)
        conv    = sum(1 for i in self.items if i.status == FileItem.STATUS_CONVERT)
        done    = sum(1 for i in self.items if i.status == FileItem.STATUS_DONE)
        skipped = sum(1 for i in self.items if i.status == FileItem.STATUS_SKIP)
        failed  = sum(1 for i in self.items if i.status == FileItem.STATUS_FAILED)
        errors  = sum(1 for i in self.items if i.status == FileItem.STATUS_ERROR)

        parts = []
        if conv:   parts.append(f"변환 대기 {conv}")
        if done:   parts.append(f"완료 {done}")
        if skipped:parts.append(f"스킵 {skipped}")
        if failed: parts.append(f"실패 {failed}")
        if errors: parts.append(f"오류 {errors}")
        self.status_var.set("  /  ".join(parts) if parts else f"파일 {total}개")

    # ── 변환 실행
    def _start_convert(self):
        targets = [i for i in self.items if i.status == FileItem.STATUS_CONVERT]
        if not targets:
            messagebox.showinfo("알림", "변환할 파일이 없습니다.")
            return

        backup_stamp = None
        backup_example = None
        if self.var_backup.get():
            backup_stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_example = build_backup_path(targets[0].path, backup_stamp)

        self.convert_btn.config(state="disabled", text="변환 중…")
        self.progress["maximum"] = len(targets)
        self.progress["value"]   = 0

        def worker():
            for idx, item in enumerate(targets):
                item.convert(backup_stamp)
                self.root.after(0, lambda i=idx: (
                    self._refresh_list(),
                    self.progress.config(value=i + 1)
                ))
            self.root.after(0, self._on_convert_done, backup_stamp, backup_example)

        threading.Thread(target=worker, daemon=True).start()

    def _on_convert_done(self, backup_stamp, backup_example):
        self.convert_btn.config(state="normal", text="⟳   UTF-8 로 변환")
        self._refresh_list()

        done   = sum(1 for i in self.items if i.status == FileItem.STATUS_DONE)
        failed = sum(1 for i in self.items if i.status == FileItem.STATUS_FAILED)

        msg = f"변환 완료: {done}개"
        if failed:
            msg += f"\n실패: {failed}개"
        if backup_stamp and backup_example:
            msg += (
                "\n\n백업 방식:\n"
                "원본 파일과 같은 폴더에 백업 파일 생성\n"
                f"예시:\n{backup_example}"
            )
        messagebox.showinfo("변환 완료", msg)


# ─────────────────────────────────────────────
#  실행
# ─────────────────────────────────────────────
def main():
    enable_high_dpi()
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    apply_tk_scaling(root)
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
