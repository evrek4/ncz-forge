"""
dxftoncz_gui.py - NCZ Forge masaüstü arayüzü
Netcad NCZ ⮂ AutoCAD DXF dönüştürme, PDF/TIF dışa aktarma, önizleme ve çoklu (toplu) dönüştürme.
Copyright (C) 2026.
"""

from __future__ import annotations
import os
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk, filedialog, messagebox

import faulthandler
import queue
import traceback
from datetime import datetime

from batch_convert import collect_files, batch_convert, default_workers
from cad_export import (
    export_dxf_to_pdf,
    export_dxf_to_tif,
    export_ncz_to_pdf,
    export_ncz_to_tif,
)
from dxf_to_ncz import convert_dxf_to_ncz
from ncz_to_dxf import convert_ncz_to_dxf
from version import __version__, RELEASES_URL, REPO, check_for_update


# Enable DPI Awareness on Windows
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


FONT = "Segoe UI"


# ================== HATA GÜNLÜĞÜ ==================
def _log_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "NCZ Forge")
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        path = os.path.expanduser("~")
    return path


LOG_PATH = os.path.join(_log_dir(), "hata_kaydi.log")


def log_error(title: str, details: str):
    """Hataları kullanıcının bilgisayarında bir günlük dosyasına yazar (exe'de konsol olmadığı için)."""
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}] v{__version__} - {title}\n{details}\n")
    except Exception:
        pass


def install_error_handlers(root: tk.Tk):
    """Yakalanmayan hataların programı sessizce kapatmasını önler; günlüğe yazar ve kullanıcıya gösterir."""
    # Yerel (C seviyesinde) çökmelerde bile iz kalsın
    try:
        root._fault_log = open(LOG_PATH, "a", encoding="utf-8")
        faulthandler.enable(file=root._fault_log, all_threads=True)
    except Exception:
        pass

    def show(title, exc_type, exc, tb):
        details = "".join(traceback.format_exception(exc_type, exc, tb))
        log_error(title, details)
        try:
            messagebox.showerror(
                "Beklenmeyen Hata",
                f"{exc_type.__name__}: {exc}\n\nProgram çalışmaya devam ediyor.\nAyrıntılar şu dosyaya kaydedildi:\n{LOG_PATH}",
                parent=root,
            )
        except Exception:
            pass

    root.report_callback_exception = lambda et, ev, tb: show("Arayüz hatası", et, ev, tb)
    sys.excepthook = lambda et, ev, tb: log_error("Yakalanmayan hata", "".join(traceback.format_exception(et, ev, tb)))
    threading.excepthook = lambda a: log_error(
        f"İş parçacığı hatası ({a.thread.name if a.thread else '?'})",
        "".join(traceback.format_exception(a.exc_type, a.exc_value, a.exc_traceback)),
    )

# Renk paleti
C = {
    "side": "#0f172a",
    "side_hover": "#1e293b",
    "side_active": "#1e293b",
    "side_text": "#cbd5e1",
    "side_muted": "#64748b",
    "accent": "#38bdf8",
    "bg": "#f1f5f9",
    "card": "#ffffff",
    "border": "#e2e8f0",
    "text": "#0f172a",
    "sub": "#64748b",
    "primary": "#2563eb",
    "primary_hover": "#1d4ed8",
    "ghost": "#eef2f7",
    "ghost_hover": "#e2e8f0",
    "success": "#16a34a",
    "warn": "#d97706",
    "danger": "#dc2626",
    "pdf": "#dc2626",
    "pdf_hover": "#b91c1c",
    "tif": "#7c3aed",
    "tif_hover": "#6d28d9",
    "drop": "#f8fafc",
    "drop_border": "#93c5fd",
    "drop_ok": "#f0fdf4",
    "drop_ok_border": "#86efac",
}

NCZ_TYPES = [("Netcad NCZ (*.ncz)", "*.ncz;*.NCZ"), ("Tüm Dosyalar (*.*)", "*.*")]
DXF_TYPES = [("AutoCAD DXF (*.dxf)", "*.dxf;*.DXF"), ("Tüm Dosyalar (*.*)", "*.*")]
CAD_TYPES = [("Çizim Dosyaları (*.ncz;*.dxf)", "*.ncz;*.NCZ;*.dxf;*.DXF"), ("Tüm Dosyalar (*.*)", "*.*")]

PAGES = (
    ("d2n", "⇄", "DXF ➔ NCZ", "AutoCAD DXF çizimini Netcad NCZ formatına dönüştürün."),
    ("n2d", "⇄", "NCZ ➔ DXF", "Netcad NCZ dosyasını AutoCAD DXF formatına dönüştürün."),
    ("exp", "▤", "PDF & TIF", "NCZ veya DXF çizimini vektör PDF ya da yüksek çözünürlüklü TIF olarak dışa aktarın."),
    ("batch", "☰", "Çoklu Dönüştür", "Birden fazla NCZ / DXF dosyasını veya bir klasörü tek seferde dönüştürün."),
)


class DxfNczConverterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"NCZ Forge v{__version__}")
        self.root.geometry("1040x700")
        self.root.minsize(900, 620)
        self.root.configure(bg=C["bg"])

        self.base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.argv[0])))
        self._load_icons()
        self._setup_styles()

        # DXF -> NCZ
        self.d2n_dxf_var = tk.StringVar()
        self.d2n_ncz_var = tk.StringVar()
        self.d2n_template_var = tk.StringVar()
        self.d2n_swap_xy_var = tk.BooleanVar(value=False)
        # NCZ -> DXF
        self.n2d_ncz_var = tk.StringVar()
        self.n2d_dxf_var = tk.StringVar()
        self.n2d_version_var = tk.StringVar(value="R2010")
        # PDF / TIF
        self.exp_input_var = tk.StringVar()
        self.exp_format_var = tk.StringVar(value="PDF")
        self.exp_dpi_var = tk.IntVar(value=300)
        self.exp_bg_var = tk.StringVar(value="white")
        # Çoklu
        self.batch_files: list[str] = []
        self.batch_target_var = tk.StringVar(value="auto")
        self.batch_outdir_var = tk.StringVar()
        self.batch_recursive_var = tk.BooleanVar(value=False)
        self.batch_parallel_var = tk.BooleanVar(value=True)
        self._batch_stop = False

        self._find_default_template()

        # Arka plan iş parçacıkları arayüze doğrudan dokunmaz; yapılacak güncellemeleri
        # bu kuyruğa koyar, ana iş parçacığı _drain_ui ile uygular (Tk iş parçacığı güvenli değildir).
        self._ui_queue: "queue.Queue" = queue.Queue()
        self.root.after(50, self._drain_ui)

        self.ui: dict[str, dict] = {}  # sayfa başına widget/durum kaydı
        self.pages: dict[str, tk.Frame] = {}
        self.nav: dict[str, dict] = {}
        self.current_page = "d2n"
        self._build_ui()
        self.show_page("d2n")

        self._drop_target = None
        if sys.platform == "win32":
            try:
                from win_dnd import DropTarget
                self._drop_target = DropTarget(self.root, self.on_files_dropped)
            except Exception:
                log_error("Sürükle-bırak başlatılamadı", traceback.format_exc())

        # EXE simgesine sürüklenen / komut satırından verilen dosyalar
        argv_paths = [a for a in sys.argv[1:] if os.path.exists(a)]
        if len(argv_paths) > 1 or (argv_paths and os.path.isdir(argv_paths[0])):
            self.show_page("batch")
            self.batch_add_paths(argv_paths)
        elif argv_paths:
            self._handle_input_file(argv_paths[0])

        threading.Thread(target=self._check_update_worker, daemon=True).start()

    def _ui(self, fn):
        """Herhangi bir iş parçacığından çağrılabilir: fn ana iş parçacığında çalıştırılır."""
        self._ui_queue.put(fn)

    def _drain_ui(self):
        try:
            for _ in range(200):
                fn = self._ui_queue.get_nowait()
                try:
                    fn()
                except Exception:
                    self.root.report_callback_exception(*sys.exc_info())
        except queue.Empty:
            pass
        try:
            self.root.after(50, self._drain_ui)
        except tk.TclError:
            pass  # pencere kapatıldı

    # ================== KURULUM ==================
    def _load_icons(self):
        ico_path = os.path.join(self.base_dir, "app_icon.ico")
        png_path = os.path.join(self.base_dir, "app_icon.png")
        if os.path.exists(ico_path):
            try:
                self.root.iconbitmap(ico_path)
            except Exception:
                pass
        if os.path.exists(png_path):
            try:
                self._app_icon_img = tk.PhotoImage(file=png_path)
                self.root.iconphoto(True, self._app_icon_img)
            except Exception:
                pass

    def _setup_styles(self):
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure("TEntry", fieldbackground="#ffffff", bordercolor=C["border"], lightcolor=C["border"], darkcolor=C["border"], padding=6)
        st.map("TEntry", bordercolor=[("focus", C["primary"])], lightcolor=[("focus", C["primary"])])
        st.configure("TCombobox", fieldbackground="#ffffff", background="#ffffff", bordercolor=C["border"], lightcolor=C["border"], darkcolor=C["border"], arrowcolor=C["sub"], padding=4)
        st.map("TCombobox", fieldbackground=[("readonly", "#ffffff")], bordercolor=[("focus", C["primary"])])
        st.configure("Accent.Horizontal.TProgressbar", troughcolor=C["border"], background=C["primary"], bordercolor=C["border"], lightcolor=C["primary"], darkcolor=C["primary"], thickness=8)
        st.configure("Ok.Horizontal.TProgressbar", troughcolor=C["border"], background=C["success"], bordercolor=C["border"], lightcolor=C["success"], darkcolor=C["success"], thickness=8)
        st.configure("Vertical.TScrollbar", background=C["ghost"], troughcolor=C["card"], bordercolor=C["card"], arrowcolor=C["sub"])
        st.configure("Card.TCheckbutton", background=C["card"], foreground=C["text"], font=(FONT, 9))
        st.map("Card.TCheckbutton", background=[("active", C["card"])])

    def _find_default_template(self):
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        for cand in (
            os.path.join(self.base_dir, "103_11.NCZ"),
            os.path.join(self.base_dir, "examples", "103_11.NCZ"),
            os.path.join(script_dir, "103_11.NCZ"),
            os.path.join(script_dir, "examples", "103_11.NCZ"),
        ):
            if os.path.exists(cand):
                self.d2n_template_var.set(cand)
                return

    # ================== ORTAK BİLEŞENLER ==================
    def _button(self, parent, text, command, kind="primary", **kw):
        colors = {
            "primary": (C["primary"], C["primary_hover"], "#ffffff"),
            "pdf": (C["pdf"], C["pdf_hover"], "#ffffff"),
            "tif": (C["tif"], C["tif_hover"], "#ffffff"),
            "ghost": (C["ghost"], C["ghost_hover"], C["text"]),
            "dark": ("#475569", "#334155", "#ffffff"),
        }[kind]
        bg, hover, fg = colors
        size = kw.pop("size", 9)
        b = tk.Button(
            parent, text=text, command=command, bg=bg, fg=fg, activebackground=hover, activeforeground=fg,
            relief=tk.FLAT, bd=0, cursor="hand2", font=(FONT, size, "bold" if kind != "ghost" else "normal"),
            padx=kw.pop("padx", 14), pady=kw.pop("pady", 7), disabledforeground="#cbd5e1" if kind != "ghost" else "#94a3b8",
            highlightthickness=0, **kw,
        )
        b.bind("<Enter>", lambda e: b.config(bg=hover) if str(b["state"]) != "disabled" else None)
        b.bind("<Leave>", lambda e: b.config(bg=bg))
        return b

    def _card(self, parent, title=None, expand=False):
        outer = tk.Frame(parent, bg=C["card"], highlightthickness=1, highlightbackground=C["border"])
        outer.pack(fill=tk.BOTH if expand else tk.X, expand=expand, pady=(0, 10))
        inner = tk.Frame(outer, bg=C["card"], padx=14, pady=10)
        inner.pack(fill=tk.BOTH, expand=True)
        if title:
            tk.Label(inner, text=title.upper(), font=(FONT, 8, "bold"), fg=C["sub"], bg=C["card"]).pack(anchor="w", pady=(0, 6))
        return inner

    def _file_row(self, parent, label, var, command, btn_text="Gözat"):
        row = tk.Frame(parent, bg=C["card"])
        row.pack(fill=tk.X, pady=3)
        tk.Label(row, text=label, font=(FONT, 9), fg=C["text"], bg=C["card"], width=14, anchor="w").pack(side=tk.LEFT)
        ttk.Entry(row, textvariable=var, font=(FONT, 9)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self._button(row, btn_text, command, kind="ghost", padx=12, pady=4).pack(side=tk.RIGHT)
        return row

    def _drop_zone(self, page, parent, icon, text, on_click):
        zone = tk.Frame(parent, bg=C["drop"], highlightthickness=2, highlightbackground=C["drop_border"], cursor="hand2", pady=14)
        zone.pack(fill=tk.X, pady=(0, 10))
        lbl_icon = tk.Label(zone, text=icon, font=(FONT, 20), bg=C["drop"], fg=C["primary"], cursor="hand2")
        lbl_icon.pack()
        lbl_text = tk.Label(zone, text=text, font=(FONT, 10, "bold"), bg=C["drop"], fg=C["text"], cursor="hand2")
        lbl_text.pack()
        lbl_hint = tk.Label(zone, text="veya tıklayarak dosya seçin", font=(FONT, 8), bg=C["drop"], fg=C["sub"], cursor="hand2")
        lbl_hint.pack()
        for w in (zone, lbl_icon, lbl_text, lbl_hint):
            w.bind("<Button-1>", lambda e: on_click())
        self.ui[page]["drop"] = (zone, lbl_icon, lbl_text, lbl_hint)

    def _set_drop_loaded(self, page, path):
        zone, lbl_icon, lbl_text, lbl_hint = self.ui[page]["drop"]
        size_kb = os.path.getsize(path) / 1024.0 if os.path.exists(path) else 0
        zone.config(bg=C["drop_ok"], highlightbackground=C["drop_ok_border"])
        lbl_icon.config(text="✓", fg=C["success"], bg=C["drop_ok"])
        lbl_text.config(text=os.path.basename(path), bg=C["drop_ok"])
        lbl_hint.config(text=f"{size_kb:,.1f} KB  ·  başka bir dosya için tıklayın veya sürükleyin", bg=C["drop_ok"])

    def _status_area(self, page, parent, idle_text, open_cmd):
        box = tk.Frame(parent, bg=C["bg"])
        box.pack(fill=tk.X, side=tk.BOTTOM, pady=(6, 0))
        top = tk.Frame(box, bg=C["bg"])
        top.pack(fill=tk.X)
        lbl = tk.Label(top, text=idle_text, font=(FONT, 9), fg=C["sub"], bg=C["bg"], anchor="w")
        lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        btn_open = self._button(top, "📁 Klasörü Aç", open_cmd, kind="ghost", padx=10, pady=3, size=8)
        btn_open.pack(side=tk.RIGHT)
        btn_open.config(state=tk.DISABLED)
        prog = ttk.Progressbar(box, mode="determinate", maximum=100, style="Accent.Horizontal.TProgressbar")
        prog.pack(fill=tk.X, pady=(6, 0))
        self.ui[page].update(status=lbl, prog=prog, open_btn=btn_open)

    def _progress(self, page, text, pct):
        u = self.ui[page]
        u["prog"].config(style="Accent.Horizontal.TProgressbar", value=pct)
        u["status"].config(text=f"{text}  ({pct}%)", fg=C["primary"])

    def _set_status(self, page, text, color=None):
        self.ui[page]["status"].config(text=text, fg=color or C["sub"])

    def _set_busy(self, page, busy):
        for b in self.ui[page].get("buttons", []):
            b.config(state=tk.DISABLED if busy else tk.NORMAL)

    def _confirm_overwrite(self, out_path: str) -> bool:
        if not os.path.exists(out_path):
            return True
        return messagebox.askyesno(
            "Dosya zaten var",
            f"{os.path.basename(out_path)} zaten var.\n\nÜzerine yazılsın mı?",
            parent=self.root,
        )

    def _run_task(self, page, start_text, title, work):
        """work(cb) -> (çıktı_yolu, özet_metni). Arka planda çalışır, sonucu durum çubuğuna yazar."""
        self._set_busy(page, True)
        self._progress(page, start_text, 5)

        def cb(msg, pct):
            self._ui(lambda: self._progress(page, msg, pct))

        def worker():
            try:
                out_path, summary = work(cb)
                self._ui(lambda: self._task_done(page, out_path, summary))
            except Exception as ex:
                err = str(ex) or ex.__class__.__name__
                self._ui(lambda: self._task_failed(page, title, err))

        threading.Thread(target=worker, daemon=True).start()

    def _task_done(self, page, out_path, summary):
        u = self.ui[page]
        self._set_busy(page, False)
        u["prog"].config(style="Ok.Horizontal.TProgressbar", value=100)
        u["last_out"] = out_path
        u["open_btn"].config(state=tk.NORMAL)
        self._set_status(page, f"✓ {summary}", C["success"])

    def _task_failed(self, page, title, err):
        u = self.ui[page]
        self._set_busy(page, False)
        u["prog"].config(value=0)
        self._set_status(page, f"✗ Hata: {err[:90]}", C["danger"])
        messagebox.showerror("Hata", f"{title} sırasında hata oluştu:\n\n{err}", parent=self.root)

    def _open_last(self, page):
        self.open_folder(self.ui[page].get("last_out", ""))

    # ================== ANA YERLEŞİM ==================
    def _build_ui(self):
        # --- Kenar çubuğu ---
        side = tk.Frame(self.root, bg=C["side"], width=230)
        side.pack(side=tk.LEFT, fill=tk.Y)
        side.pack_propagate(False)

        brand = tk.Frame(side, bg=C["side"])
        brand.pack(fill=tk.X, padx=18, pady=(20, 24))
        logo_path = os.path.join(self.base_dir, "header_logo.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(self.base_dir, "assets", "header_logo.png")
        if os.path.exists(logo_path):
            try:
                self._header_logo_img = tk.PhotoImage(file=logo_path)
                tk.Label(brand, image=self._header_logo_img, bg=C["side"]).pack(side=tk.LEFT, padx=(0, 10))
            except Exception:
                pass
        tb = tk.Frame(brand, bg=C["side"])
        tb.pack(side=tk.LEFT)
        tk.Label(tb, text="NCZ Forge", font=(FONT, 15, "bold"), fg="#ffffff", bg=C["side"]).pack(anchor="w")
        tk.Label(tb, text=f"Sürüm {__version__}", font=(FONT, 8), fg=C["side_muted"], bg=C["side"]).pack(anchor="w")

        tk.Label(side, text="İŞLEMLER", font=(FONT, 8, "bold"), fg=C["side_muted"], bg=C["side"]).pack(anchor="w", padx=20, pady=(0, 6))
        for key, icon, title, _desc in PAGES:
            self._nav_item(side, key, icon, title)

        # Alt kısım: güncelleme + bağlantı
        bottom = tk.Frame(side, bg=C["side"])
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=18, pady=16)
        self.lbl_update = tk.Label(bottom, text="", font=(FONT, 9, "bold"), fg="#facc15", bg=C["side"], cursor="hand2", justify=tk.LEFT, wraplength=190)
        self.lbl_update.pack(anchor="w", pady=(0, 6))
        self.lbl_update.bind("<Button-1>", lambda e: webbrowser.open(RELEASES_URL))
        gh = tk.Label(bottom, text="GitHub'da görüntüle ↗", font=(FONT, 8), fg=C["side_muted"], bg=C["side"], cursor="hand2")
        gh.pack(anchor="w")
        gh.bind("<Button-1>", lambda e: webbrowser.open(f"https://github.com/{REPO}"))
        tk.Label(bottom, text="Dosyaları pencereye sürükleyip\nbırakabilirsiniz.", font=(FONT, 8), fg=C["side_muted"], bg=C["side"], justify=tk.LEFT).pack(anchor="w", pady=(8, 0))

        # --- İçerik ---
        self.content = tk.Frame(self.root, bg=C["bg"])
        self.content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        for key, _icon, title, desc in PAGES:
            page = tk.Frame(self.content, bg=C["bg"], padx=28, pady=22)
            self.pages[key] = page
            self.ui[key] = {"buttons": []}
            tk.Label(page, text=title, font=(FONT, 18, "bold"), fg=C["text"], bg=C["bg"]).pack(anchor="w")
            tk.Label(page, text=desc, font=(FONT, 9), fg=C["sub"], bg=C["bg"]).pack(anchor="w", pady=(0, 14))

        self._build_d2n_page(self.pages["d2n"])
        self._build_n2d_page(self.pages["n2d"])
        self._build_exp_page(self.pages["exp"])
        self._build_batch_page(self.pages["batch"])

    def _nav_item(self, parent, key, icon, title):
        row = tk.Frame(parent, bg=C["side"], cursor="hand2")
        row.pack(fill=tk.X, padx=10, pady=1)
        bar = tk.Frame(row, bg=C["side"], width=3)
        bar.pack(side=tk.LEFT, fill=tk.Y)
        lbl_i = tk.Label(row, text=icon, font=(FONT, 11), fg=C["side_text"], bg=C["side"], width=2, cursor="hand2")
        lbl_i.pack(side=tk.LEFT, padx=(10, 6), pady=9)
        lbl_t = tk.Label(row, text=title, font=(FONT, 10), fg=C["side_text"], bg=C["side"], anchor="w", cursor="hand2")
        lbl_t.pack(side=tk.LEFT, fill=tk.X, expand=True)
        widgets = (row, lbl_i, lbl_t)
        for w in widgets:
            w.bind("<Button-1>", lambda e, k=key: self.show_page(k))
            w.bind("<Enter>", lambda e, k=key: self._nav_paint(k, hover=True))
            w.bind("<Leave>", lambda e, k=key: self._nav_paint(k))
        self.nav[key] = {"widgets": widgets, "bar": bar, "title": lbl_t}

    def _nav_paint(self, key, hover=False):
        n = self.nav[key]
        active = key == self.current_page
        bg = C["side_active"] if active else (C["side_hover"] if hover else C["side"])
        for w in n["widgets"]:
            w.config(bg=bg)
        n["bar"].config(bg=C["accent"] if active else bg)
        n["title"].config(fg="#ffffff" if active else C["side_text"], font=(FONT, 10, "bold" if active else "normal"))

    def show_page(self, key):
        self.current_page = key
        for k, p in self.pages.items():
            if k == key:
                p.pack(fill=tk.BOTH, expand=True)
            else:
                p.pack_forget()
        for k in self.nav:
            self._nav_paint(k)

    # ================== SÜRÜKLE & BIRAK ==================
    @staticmethod
    def _decode_drop_path(raw_path) -> str:
        if isinstance(raw_path, bytes):
            try:
                file_path = raw_path.decode("utf-8")
            except UnicodeDecodeError:
                file_path = raw_path.decode("windows-1254", errors="ignore")
        else:
            file_path = str(raw_path)
        return os.path.abspath(file_path.strip(' "'))

    def on_files_dropped(self, file_list):
        if not file_list:
            return
        paths = [p for p in (self._decode_drop_path(r) for r in file_list) if p and os.path.exists(p)]
        if not paths:
            return
        if len(paths) > 1 or os.path.isdir(paths[0]) or self.current_page == "batch":
            self.show_page("batch")
            self.batch_add_paths(paths)
        else:
            self._handle_input_file(paths[0])

    def _handle_input_file(self, file_path: str):
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in (".dxf", ".ncz"):
            messagebox.showwarning("Desteklenmeyen Dosya", f"Lütfen bir .dxf veya .ncz dosyası bırakın.\nSeçilen: {os.path.basename(file_path)}")
            return
        self.set_exp_input(file_path)
        if self.current_page == "exp":
            return
        if ext == ".dxf":
            self.set_d2n_dxf(file_path)
            self.show_page("d2n")
        else:
            self.set_n2d_ncz(file_path)
            self.show_page("n2d")

    # ================== DXF ➔ NCZ ==================
    def _build_d2n_page(self, page):
        key = "d2n"
        self._drop_zone(key, page, "⬇", "DXF dosyasını buraya sürükleyin", self.browse_d2n_dxf)

        files = self._card(page, "Dosyalar")
        self._file_row(files, "Girdi (DXF)", self.d2n_dxf_var, self.browse_d2n_dxf)
        self._file_row(files, "Çıktı (NCZ)", self.d2n_ncz_var, self.browse_d2n_ncz, "Kaydet...")

        opts = self._card(page, "Ayarlar")
        self._file_row(opts, "NCZ şablonu", self.d2n_template_var, self.browse_d2n_template)
        tk.Label(opts, text="Şablon; projeksiyon, sembol ve stil bilgilerini taşır (isteğe bağlı).", font=(FONT, 8), fg=C["sub"], bg=C["card"]).pack(anchor="w", padx=(0, 0))
        ttk.Checkbutton(opts, text="X ve Y koordinatlarını yer değiştir (Sağa/Yukarı ters ise)", variable=self.d2n_swap_xy_var, style="Card.TCheckbutton").pack(anchor="w", pady=(6, 0))

        self._status_area(key, page, "DXF dosyanızı seçin veya sürükleyin.", lambda: self._open_last(key))

        actions = tk.Frame(page, bg=C["bg"])
        actions.pack(fill=tk.X, pady=(2, 0))
        b1 = self._button(actions, "NCZ'ye Dönüştür  →", self.start_d2n_conversion, size=10, pady=9)
        b1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        b2 = self._button(actions, "PDF", lambda: self.quick_export("d2n", self.d2n_dxf_var.get(), "pdf"), kind="pdf", pady=9)
        b2.pack(side=tk.LEFT, padx=(0, 6))
        b3 = self._button(actions, "TIF", lambda: self.quick_export("d2n", self.d2n_dxf_var.get(), "tif"), kind="tif", pady=9)
        b3.pack(side=tk.LEFT, padx=(0, 6))
        b4 = self._button(actions, "👁 Önizle", lambda: self.open_preview(self.d2n_dxf_var.get()), kind="ghost", pady=9)
        b4.pack(side=tk.LEFT)
        self.ui[key]["buttons"] = [b1, b2, b3, b4]

    def browse_d2n_dxf(self):
        f = filedialog.askopenfilename(title="Dönüştürülecek DXF dosyasını seçin", filetypes=DXF_TYPES)
        if f:
            self.set_d2n_dxf(f)

    def set_d2n_dxf(self, filename: str):
        self.d2n_dxf_var.set(filename)
        self.d2n_ncz_var.set(os.path.splitext(filename)[0] + ".NCZ")
        self.set_exp_input(filename)
        self._set_drop_loaded("d2n", filename)
        self.ui["d2n"]["prog"].config(value=0)
        self._set_status("d2n", f"Hazır: {os.path.basename(filename)}", C["primary"])

    def browse_d2n_ncz(self):
        f = filedialog.asksaveasfilename(title="NCZ çıktısının kaydedileceği yer", defaultextension=".NCZ", filetypes=NCZ_TYPES)
        if f:
            self.d2n_ncz_var.set(f)

    def browse_d2n_template(self):
        f = filedialog.askopenfilename(title="Şablon NCZ dosyası seçin (isteğe bağlı)", filetypes=NCZ_TYPES)
        if f:
            self.d2n_template_var.set(f)

    def start_d2n_conversion(self):
        dxf_path = self.d2n_dxf_var.get().strip()
        ncz_path = self.d2n_ncz_var.get().strip()
        template_path = self.d2n_template_var.get().strip() or None
        swap_xy = self.d2n_swap_xy_var.get()
        if not dxf_path or not os.path.exists(dxf_path):
            messagebox.showwarning("Uyarı", "Lütfen geçerli bir DXF dosyası seçin veya sürükleyin.", parent=self.root)
            return
        if not ncz_path:
            messagebox.showwarning("Uyarı", "Lütfen bir çıktı NCZ dosyası belirleyin.", parent=self.root)
            return
        if template_path and not os.path.exists(template_path):
            template_path = None
        if not self._confirm_overwrite(ncz_path):
            return

        def work(cb):
            cnt = convert_dxf_to_ncz(dxf_path=dxf_path, ncz_path=ncz_path, template_path=template_path, swap_xy=swap_xy, progress_callback=cb)
            size_kb = os.path.getsize(ncz_path) / 1024.0
            return ncz_path, f"{os.path.basename(ncz_path)} oluşturuldu — {cnt:,} obje, {size_kb:,.1f} KB"

        self._run_task("d2n", "NCZ'ye dönüştürme başlatılıyor...", "DXF ➔ NCZ dönüştürme", work)

    # ================== NCZ ➔ DXF ==================
    def _build_n2d_page(self, page):
        key = "n2d"
        self._drop_zone(key, page, "⬇", "NCZ dosyasını buraya sürükleyin", self.browse_n2d_ncz)

        files = self._card(page, "Dosyalar")
        self._file_row(files, "Girdi (NCZ)", self.n2d_ncz_var, self.browse_n2d_ncz)
        self._file_row(files, "Çıktı (DXF)", self.n2d_dxf_var, self.browse_n2d_dxf, "Kaydet...")

        opts = self._card(page, "Ayarlar")
        row = tk.Frame(opts, bg=C["card"])
        row.pack(fill=tk.X)
        tk.Label(row, text="DXF sürümü", font=(FONT, 9), fg=C["text"], bg=C["card"], width=14, anchor="w").pack(side=tk.LEFT)
        ttk.Combobox(row, textvariable=self.n2d_version_var, values=["R2018", "R2013", "R2010", "R2007", "R2004", "R2000"], state="readonly", width=12).pack(side=tk.LEFT)
        tk.Label(opts, text="Renkler, yaylar, semboller ve bloklar da aktarılır. Eski AutoCAD sürümleri için R2000 / R2004 seçin.", font=(FONT, 8), fg=C["sub"], bg=C["card"]).pack(anchor="w", pady=(6, 0))

        self._status_area(key, page, "NCZ dosyanızı seçin veya sürükleyin.", lambda: self._open_last(key))

        actions = tk.Frame(page, bg=C["bg"])
        actions.pack(fill=tk.X, pady=(2, 0))
        b1 = self._button(actions, "DXF'e Dönüştür  →", self.start_n2d_conversion, size=10, pady=9)
        b1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        b2 = self._button(actions, "PDF", lambda: self.quick_export("n2d", self.n2d_ncz_var.get(), "pdf"), kind="pdf", pady=9)
        b2.pack(side=tk.LEFT, padx=(0, 6))
        b3 = self._button(actions, "TIF", lambda: self.quick_export("n2d", self.n2d_ncz_var.get(), "tif"), kind="tif", pady=9)
        b3.pack(side=tk.LEFT, padx=(0, 6))
        b4 = self._button(actions, "👁 Önizle", lambda: self.open_preview(self.n2d_ncz_var.get()), kind="ghost", pady=9)
        b4.pack(side=tk.LEFT)
        self.ui[key]["buttons"] = [b1, b2, b3, b4]

    def browse_n2d_ncz(self):
        f = filedialog.askopenfilename(title="Dönüştürülecek NCZ dosyasını seçin", filetypes=NCZ_TYPES)
        if f:
            self.set_n2d_ncz(f)

    def set_n2d_ncz(self, filename: str):
        self.n2d_ncz_var.set(filename)
        self.n2d_dxf_var.set(os.path.splitext(filename)[0] + ".dxf")
        self.set_exp_input(filename)
        self._set_drop_loaded("n2d", filename)
        self.ui["n2d"]["prog"].config(value=0)
        self._set_status("n2d", f"Hazır: {os.path.basename(filename)}", C["primary"])

    def browse_n2d_dxf(self):
        f = filedialog.asksaveasfilename(title="DXF çıktısının kaydedileceği yer", defaultextension=".dxf", filetypes=DXF_TYPES)
        if f:
            self.n2d_dxf_var.set(f)

    def start_n2d_conversion(self):
        ncz_path = self.n2d_ncz_var.get().strip()
        dxf_path = self.n2d_dxf_var.get().strip()
        dxf_version = self.n2d_version_var.get().strip() or "R2010"
        if not ncz_path or not os.path.exists(ncz_path):
            messagebox.showwarning("Uyarı", "Lütfen geçerli bir NCZ dosyası seçin veya sürükleyin.", parent=self.root)
            return
        if not dxf_path:
            messagebox.showwarning("Uyarı", "Lütfen bir çıktı DXF dosyası belirleyin.", parent=self.root)
            return
        if not self._confirm_overwrite(dxf_path):
            return

        def work(cb):
            cnt = convert_ncz_to_dxf(ncz_path=ncz_path, dxf_path=dxf_path, dxf_version=dxf_version, progress_callback=cb)
            size_kb = os.path.getsize(dxf_path) / 1024.0
            return dxf_path, f"{os.path.basename(dxf_path)} oluşturuldu — {cnt:,} obje, {size_kb:,.1f} KB"

        self._run_task("n2d", "DXF'e dönüştürme başlatılıyor...", "NCZ ➔ DXF dönüştürme", work)

    # ================== HIZLI PDF / TIF ==================
    def quick_export(self, page, src, fmt):
        src = (src or "").strip()
        if not src or not os.path.exists(src):
            messagebox.showwarning("Uyarı", "Lütfen önce geçerli bir dosya seçin.", parent=self.root)
            return
        self._export(page, src, os.path.splitext(src)[0] + "." + fmt, fmt, 300, "white")

    def _export(self, page, src, out_path, fmt, dpi, bg):
        ext = os.path.splitext(src)[1].lower()
        funcs = {
            (".dxf", "pdf"): export_dxf_to_pdf,
            (".dxf", "tif"): export_dxf_to_tif,
            (".ncz", "pdf"): export_ncz_to_pdf,
            (".ncz", "tif"): export_ncz_to_tif,
        }
        fn = funcs.get((ext, fmt))
        if fn is None:
            messagebox.showwarning("Uyarı", f"Desteklenmeyen dosya: {os.path.basename(src)}", parent=self.root)
            return
        if not self._confirm_overwrite(out_path):
            return

        def work(cb):
            fn(src, out_path, dpi=dpi, bg=bg, progress_callback=cb)
            size_kb = os.path.getsize(out_path) / 1024.0
            return out_path, f"{os.path.basename(out_path)} oluşturuldu — {size_kb:,.1f} KB"

        self._run_task(page, f"{fmt.upper()} hazırlanıyor...", f"{fmt.upper()} dışa aktarma", work)

    # ================== PDF & TIF SAYFASI ==================
    def _build_exp_page(self, page):
        key = "exp"
        self._drop_zone(key, page, "⬇", "NCZ veya DXF dosyasını buraya sürükleyin", self.browse_exp_file)

        files = self._card(page, "Girdi")
        self._file_row(files, "Çizim dosyası", self.exp_input_var, self.browse_exp_file)

        opts = self._card(page, "Çıktı ayarları")
        r1 = tk.Frame(opts, bg=C["card"])
        r1.pack(fill=tk.X, pady=(0, 8))
        tk.Label(r1, text="Format", font=(FONT, 9), fg=C["text"], bg=C["card"], width=14, anchor="w").pack(side=tk.LEFT)
        self._segmented(r1, self.exp_format_var, [("PDF  ·  vektör", "PDF"), ("TIF  ·  raster", "TIF")])

        r2 = tk.Frame(opts, bg=C["card"])
        r2.pack(fill=tk.X)
        tk.Label(r2, text="Çözünürlük", font=(FONT, 9), fg=C["text"], bg=C["card"], width=14, anchor="w").pack(side=tk.LEFT)
        ttk.Combobox(r2, textvariable=self.exp_dpi_var, values=[150, 300, 600], state="readonly", width=8).pack(side=tk.LEFT)
        tk.Label(r2, text="DPI", font=(FONT, 9), fg=C["sub"], bg=C["card"]).pack(side=tk.LEFT, padx=(6, 24))
        tk.Label(r2, text="Arka plan", font=(FONT, 9), fg=C["text"], bg=C["card"]).pack(side=tk.LEFT, padx=(0, 8))
        self._segmented(r2, self.exp_bg_var, [("Beyaz", "white"), ("Siyah", "black")])

        self._status_area(key, page, "NCZ veya DXF dosyanızı seçin veya sürükleyin.", lambda: self._open_last(key))

        actions = tk.Frame(page, bg=C["bg"])
        actions.pack(fill=tk.X, pady=(2, 0))
        b1 = self._button(actions, "Dışa Aktar  →", self.start_dedicated_export, size=10, pady=9)
        b1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        b2 = self._button(actions, "👁 Önizle", lambda: self.open_preview(self.exp_input_var.get()), kind="ghost", pady=9)
        b2.pack(side=tk.LEFT)
        self.ui[key]["buttons"] = [b1, b2]

    def _segmented(self, parent, var, options):
        box = tk.Frame(parent, bg=C["border"], padx=1, pady=1)
        box.pack(side=tk.LEFT)
        btns = []

        def paint(*_):
            for b, val in btns:
                on = str(var.get()) == str(val)
                b.config(bg=C["primary"] if on else "#ffffff", fg="#ffffff" if on else C["text"])

        for text, val in options:
            b = tk.Label(box, text=text, font=(FONT, 9), padx=12, pady=4, cursor="hand2")
            b.pack(side=tk.LEFT, padx=(0 if not btns else 1, 0))
            b.bind("<Button-1>", lambda e, v=val: var.set(v))
            btns.append((b, val))
        var.trace_add("write", paint)
        paint()

    def set_exp_input(self, filename: str):
        self.exp_input_var.set(filename)
        if "exp" in self.ui and "drop" in self.ui["exp"]:
            self._set_drop_loaded("exp", filename)
            self.ui["exp"]["prog"].config(value=0)
            self._set_status("exp", f"Hazır: {os.path.basename(filename)}", C["primary"])

    def browse_exp_file(self):
        f = filedialog.askopenfilename(title="Dışa aktarılacak çizim dosyasını seçin", filetypes=CAD_TYPES)
        if f:
            self.set_exp_input(f)

    def start_dedicated_export(self):
        inp = self.exp_input_var.get().strip()
        if not inp or not os.path.exists(inp):
            messagebox.showwarning("Uyarı", "Lütfen geçerli bir NCZ veya DXF dosyası seçin.", parent=self.root)
            return
        fmt = self.exp_format_var.get().lower()
        self._export("exp", inp, os.path.splitext(inp)[0] + "." + fmt, fmt, int(self.exp_dpi_var.get()), self.exp_bg_var.get())

    # ================== ÇOKLU DÖNÜŞTÜR ==================
    def _build_batch_page(self, page):
        key = "batch"
        self._status_area(key, page, "Dosya veya klasör ekleyin ya da pencereye sürükleyin.", lambda: self._open_last(key))

        actions = tk.Frame(page, bg=C["bg"])
        actions.pack(fill=tk.X, side=tk.BOTTOM, pady=(8, 0))
        self.btn_batch_start = self._button(actions, "Tümünü Dönüştür  →", self.start_batch, size=10, pady=9)
        self.btn_batch_start.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.btn_batch_stop = self._button(actions, "■ Durdur", self.stop_batch, kind="dark", pady=9)
        self.btn_batch_stop.pack(side=tk.LEFT)
        self.btn_batch_stop.config(state=tk.DISABLED)

        opts = self._card(page, "Hedef ve çıktı")
        r1 = tk.Frame(opts, bg=C["card"])
        r1.pack(fill=tk.X, pady=(0, 8))
        tk.Label(r1, text="Hedef", font=(FONT, 9), fg=C["text"], bg=C["card"], width=14, anchor="w").pack(side=tk.LEFT)
        self._segmented(r1, self.batch_target_var, [("NCZ ⮂ DXF (otomatik)", "auto"), ("PDF", "pdf"), ("TIF", "tif")])
        self._file_row(opts, "Çıktı klasörü", self.batch_outdir_var, self.batch_browse_outdir, "Seç...")
        r3 = tk.Frame(opts, bg=C["card"])
        r3.pack(fill=tk.X, pady=(4, 0))
        ttk.Checkbutton(r3, text="Alt klasörleri de tara", variable=self.batch_recursive_var, style="Card.TCheckbutton").pack(side=tk.LEFT, padx=(0, 16))
        ttk.Checkbutton(r3, text=f"Paralel işle ({default_workers()} çekirdek)", variable=self.batch_parallel_var, style="Card.TCheckbutton").pack(side=tk.LEFT)
        tk.Label(opts, text="Çıktı klasörü boşsa her dosya kendi klasörüne kaydedilir. Aynı isimli çıktılar _2, _3 ekiyle ayrılır; kaynak dosyaların üzerine yazılmaz.\nŞablon, DXF sürümü, DPI ve arka plan ayarları diğer sayfalardan alınır.", font=(FONT, 8), fg=C["sub"], bg=C["card"], justify=tk.LEFT).pack(anchor="w", pady=(6, 0))

        lst = self._card(page, None, expand=True)
        head = tk.Frame(lst, bg=C["card"])
        head.pack(fill=tk.X, pady=(0, 6))
        tk.Label(head, text="DOSYA LİSTESİ", font=(FONT, 8, "bold"), fg=C["sub"], bg=C["card"]).pack(side=tk.LEFT)
        self.lbl_batch_count = tk.Label(head, text="", font=(FONT, 8, "bold"), fg=C["primary"], bg=C["card"])
        self.lbl_batch_count.pack(side=tk.LEFT, padx=(8, 0))
        for text, cmd in (
            ("Temizle", self.batch_clear),
            ("Seçileni çıkar", self.batch_remove_selected),
            ("+ Klasör", self.batch_browse_folder),
            ("+ Dosya", self.batch_browse_files),
        ):
            self._button(head, text, cmd, kind="ghost", padx=10, pady=3, size=8).pack(side=tk.RIGHT, padx=(4, 0))

        list_frame = tk.Frame(lst, bg=C["card"], highlightthickness=1, highlightbackground=C["border"])
        list_frame.pack(fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.batch_listbox = tk.Listbox(
            list_frame, selectmode=tk.EXTENDED, font=(FONT, 9), yscrollcommand=sb.set, activestyle="none",
            relief=tk.FLAT, bd=0, highlightthickness=0, selectbackground="#dbeafe", selectforeground=C["text"], fg=C["text"],
        )
        sb.config(command=self.batch_listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.batch_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=4)
        self.batch_listbox.bind("<Delete>", lambda e: self.batch_remove_selected())
        self._batch_refresh_list()

    def _batch_refresh_list(self):
        self.batch_listbox.delete(0, tk.END)
        if not self.batch_files:
            self.batch_listbox.insert(tk.END, "   Liste boş — dosyaları veya bir klasörü buraya sürükleyin.")
            self.batch_listbox.itemconfig(0, fg=C["sub"])
        for f in self.batch_files:
            tag = "NCZ" if f.lower().endswith(".ncz") else "DXF"
            self.batch_listbox.insert(tk.END, f"  {tag}   {os.path.basename(f)}   —   {os.path.dirname(f)}")
        n_ncz = sum(1 for f in self.batch_files if f.lower().endswith(".ncz"))
        n_dxf = len(self.batch_files) - n_ncz
        self.lbl_batch_count.config(text=f"{len(self.batch_files)} dosya · {n_ncz} NCZ · {n_dxf} DXF" if self.batch_files else "")

    def batch_add_paths(self, paths):
        before = len(self.batch_files)
        known = {os.path.normcase(f) for f in self.batch_files}
        for f in collect_files(paths, recursive=self.batch_recursive_var.get()):
            if os.path.normcase(f) not in known:
                known.add(os.path.normcase(f))
                self.batch_files.append(f)
        self._batch_refresh_list()
        added = len(self.batch_files) - before
        self.ui["batch"]["prog"].config(value=0)
        if added:
            self._set_status("batch", f"{added} dosya eklendi. Hazır.", C["primary"])
        else:
            self._set_status("batch", "Eklenecek yeni .ncz / .dxf dosyası bulunamadı.", C["warn"])

    def batch_browse_files(self):
        files = filedialog.askopenfilenames(title="NCZ / DXF dosyalarını seçin (çoklu seçim)", filetypes=CAD_TYPES)
        if files:
            self.batch_add_paths(list(files))

    def batch_browse_folder(self):
        d = filedialog.askdirectory(title="NCZ / DXF dosyalarının bulunduğu klasörü seçin")
        if d:
            self.batch_add_paths([d])

    def batch_browse_outdir(self):
        d = filedialog.askdirectory(title="Çıktı klasörünü seçin")
        if d:
            self.batch_outdir_var.set(d)

    def batch_remove_selected(self):
        if not self.batch_files:
            return
        for idx in reversed(self.batch_listbox.curselection()):
            if idx < len(self.batch_files):
                del self.batch_files[idx]
        self._batch_refresh_list()

    def batch_clear(self):
        self.batch_files = []
        self._batch_refresh_list()
        self.ui["batch"]["prog"].config(value=0)
        self._set_status("batch", "Liste temizlendi.")

    def _set_batch_running(self, running: bool):
        self.btn_batch_start.config(state=tk.DISABLED if running else tk.NORMAL)
        self.btn_batch_stop.config(state=tk.NORMAL if running else tk.DISABLED)

    def stop_batch(self):
        self._batch_stop = True
        self._set_status("batch", "Durduruluyor... (işlenmekte olan dosyalar bitince)", C["warn"])

    def start_batch(self):
        files = list(self.batch_files)
        if not files:
            messagebox.showwarning("Uyarı", "Lütfen önce listeye NCZ / DXF dosyası ekleyin.", parent=self.root)
            return
        template = self.d2n_template_var.get().strip() or None
        if template and not os.path.exists(template):
            template = None
        opts = dict(
            target=self.batch_target_var.get(),
            output_dir=self.batch_outdir_var.get().strip() or None,
            template_path=template,
            swap_xy=self.d2n_swap_xy_var.get(),
            dxf_version=self.n2d_version_var.get().strip() or "R2010",
            dpi=int(self.exp_dpi_var.get()),
            bg=self.exp_bg_var.get(),
            workers=default_workers() if self.batch_parallel_var.get() else 1,
        )
        self._batch_stop = False
        self._set_batch_running(True)
        self._progress("batch", f"{len(files)} dosya işleniyor...", 0)

        def cb(i, total, path):
            pct = int(i * 100 / total) if total else 100
            text = f"{min(i + 1, total) if i < total else total}/{total}  ·  {os.path.basename(path)}" if path else "Tamamlanıyor..."
            self._ui(lambda: self._progress("batch", text, pct))

        def worker():
            try:
                summary = batch_convert(files, progress_callback=cb, stop_flag=lambda: self._batch_stop, **opts)
                self._ui(lambda: self._on_batch_done(summary, len(files)))
            except Exception as ex:
                err = str(ex) or ex.__class__.__name__
                self._ui(lambda: (self._set_batch_running(False), self._task_failed("batch", "Toplu dönüştürme", err)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_batch_done(self, summary, total: int):
        self._set_batch_running(False)
        ok, bad = summary.succeeded, summary.failed
        skipped = total - len(summary.results)
        u = self.ui["batch"]
        u["prog"].config(style="Ok.Horizontal.TProgressbar" if not bad else "Accent.Horizontal.TProgressbar", value=100)
        if ok:
            u["last_out"] = ok[-1].output_path
            u["open_btn"].config(state=tk.NORMAL)
        text = f"✓ {len(ok)} başarılı   ✗ {len(bad)} hatalı" + (f"   ⏭ {skipped} atlandı" if skipped else "")
        self._set_status("batch", text, C["success"] if not bad else C["warn"])
        if bad:
            msg = f"Başarılı: {len(ok)}\nHatalı: {len(bad)}\n\nHatalı dosyalar:\n" + "\n".join(
                f"• {os.path.basename(r.input_path)}: {r.error[:80]}" for r in bad[:10]
            )
            if len(bad) > 10:
                msg += f"\n... ve {len(bad) - 10} dosya daha"
            messagebox.showwarning("Toplu Dönüştürme", msg, parent=self.root)

    # ================== ÖNİZLEME & GÜNCELLEME ==================
    def _check_update_worker(self):
        tag = check_for_update()
        if tag:
            self._ui(lambda: self.lbl_update.config(text=f"⬆ Yeni sürüm hazır: {tag}\nİndirmek için tıklayın"))

    def open_preview(self, path: str):
        path = (path or "").strip()
        if not path or not os.path.exists(path):
            messagebox.showwarning("Uyarı", "Önizleme için önce geçerli bir NCZ veya DXF dosyası seçin.", parent=self.root)
            return
        win = tk.Toplevel(self.root)
        win.title(f"Önizleme — {os.path.basename(path)}")
        win.geometry("1000x720")
        win.configure(bg=C["bg"])
        lbl = tk.Label(win, text="Çizim hazırlanıyor...", font=(FONT, 11), bg=C["bg"], fg=C["primary"])
        lbl.pack(expand=True)

        def worker():
            try:
                from cad_export import render_preview_figure
                fig = render_preview_figure(path)
                self._ui(lambda: self._show_preview(win, lbl, fig))
            except Exception as ex:
                err = str(ex)
                self._ui(lambda: lbl.winfo_exists() and lbl.config(text=f"Önizleme hatası: {err[:120]}", fg=C["danger"]))

        threading.Thread(target=worker, daemon=True).start()

    def _show_preview(self, win, lbl, fig):
        import matplotlib.pyplot as plt
        if not win.winfo_exists():
            plt.close(fig)
            return
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
        lbl.destroy()
        canvas = FigureCanvasTkAgg(fig, master=win)
        toolbar = NavigationToolbar2Tk(canvas, win)
        toolbar.update()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        canvas.draw()

        def on_close():
            plt.close(fig)
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)

    # ================== YARDIMCI ==================
    def open_folder(self, target_path: str):
        p = (target_path or "").strip()
        if p and os.path.exists(p):
            folder = os.path.dirname(os.path.abspath(p))
            if sys.platform == "win32":
                subprocess.run(["explorer", folder], shell=True)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder])
            else:
                subprocess.run(["xdg-open", folder])


def main():
    root = tk.Tk()
    install_error_handlers(root)
    DxfNczConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
