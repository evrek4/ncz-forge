"""
dxftoncz_gui.py - NCZ & DXF İki Yönlü Dönüştürücü ve PDF/TIF Dışa Aktarıcı GUI
Copyright (C) 2026.
Terminalsiz, tam sürükle-bırak (Drag & Drop) ve PDF/TIF destekli masaüstü uygulaması.
"""

from __future__ import annotations
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess

try:
    import windnd
except ImportError:
    windnd = None

from dxf_to_ncz import convert_dxf_to_ncz
from ncz_to_dxf import convert_ncz_to_dxf
from batch_convert import collect_files, batch_convert
from cad_export import (
    export_dxf_to_pdf,
    export_dxf_to_tif,
    export_ncz_to_pdf,
    export_ncz_to_tif,
)


# Enable DPI Awareness on Windows
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


class DxfNczConverterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("NCZ Forge - Netcad NCZ & CAD Çevirici ve Dışa Aktarıcı")
        self.root.geometry("760x700")
        self.root.minsize(660, 600)

        # Base dir for bundled assets
        self.base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.argv[0])))

        # Set window icon
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

        # Style configuration
        self.style = ttk.Style()
        try:
            self.style.theme_use("vista")
        except Exception:
            pass

        # Color scheme
        self.bg_color = "#f4f6f9"
        self.card_bg = "#ffffff"
        self.primary_color = "#0066cc"
        self.secondary_color = "#495057"
        self.success_color = "#198754"
        self.pdf_color = "#dc3545"
        self.tif_color = "#6f42c1"
        self.drop_idle_bg = "#f0f5ff"
        self.drop_idle_fg = "#0055b3"
        self.drop_ready_bg = "#eafaf1"
        self.drop_ready_fg = "#146c43"

        self.root.configure(bg=self.bg_color)

        # Tab 1 Variables (DXF -> NCZ)
        self.d2n_dxf_var = tk.StringVar()
        self.d2n_ncz_var = tk.StringVar()
        self.d2n_template_var = tk.StringVar()
        self.d2n_swap_xy_var = tk.BooleanVar(value=False)

        # Tab 2 Variables (NCZ -> DXF)
        self.n2d_ncz_var = tk.StringVar()
        self.n2d_dxf_var = tk.StringVar()
        self.n2d_version_var = tk.StringVar(value="R2010")

        # Tab 3 Variables (Export to PDF/TIF)
        self.exp_input_var = tk.StringVar()
        self.exp_format_var = tk.StringVar(value="PDF")
        self.exp_dpi_var = tk.IntVar(value=300)
        self.exp_bg_var = tk.StringVar(value="white")

        # Tab 4 Variables (Batch / Çoklu)
        self.batch_files: list[str] = []
        self.batch_target_var = tk.StringVar(value="auto")
        self.batch_outdir_var = tk.StringVar()
        self.batch_recursive_var = tk.BooleanVar(value=False)
        self._batch_stop = False

        # Set default template
        cand_template = os.path.join(self.base_dir, "103_11.NCZ")
        if not os.path.exists(cand_template):
            cand_template = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "103_11.NCZ")
        if os.path.exists(cand_template):
            self.d2n_template_var.set(cand_template)

        self._build_ui()

        # Hook Native Windows Drag-and-Drop
        if windnd is not None:
            try:
                windnd.hook_dropfiles(self.root, func=self.on_files_dropped, force_unicode=True)
            except Exception as e:
                print("windnd hook error:", e)

        # Handle Drag-and-Drop onto EXE icon or command line args
        argv_paths = [a for a in sys.argv[1:] if os.path.exists(a)]
        if len(argv_paths) > 1 or (argv_paths and os.path.isdir(argv_paths[0])):
            self.notebook.select(3)
            self.batch_add_paths(argv_paths)
        elif argv_paths:
            self._handle_input_file(argv_paths[0])

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
        paths = [p for p in (self._decode_drop_path(r) for r in file_list) if os.path.exists(p)]
        if not paths:
            return
        # Birden fazla dosya, klasör veya Çoklu sekmesi açıkken -> toplu listeye ekle
        if len(paths) > 1 or os.path.isdir(paths[0]) or self.notebook.index("current") == 3:
            self.notebook.select(3)
            self.batch_add_paths(paths)
        else:
            self._handle_input_file(paths[0])

    def _handle_input_file(self, file_path: str):
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".dxf":
            self.notebook.select(0)
            self.set_d2n_dxf(file_path)
            self._set_d2n_drop_active(file_path)
            self.exp_input_var.set(file_path)
        elif ext == ".ncz":
            self.notebook.select(1)
            self.set_n2d_ncz(file_path)
            self._set_n2d_drop_active(file_path)
            self.exp_input_var.set(file_path)
        else:
            messagebox.showwarning(
                "Desteklenmeyen Dosya",
                f"Lütfen bir .dxf veya .ncz dosyası bırakın.\nSeçilen: {os.path.basename(file_path)}",
            )

    def _build_ui(self):
        # Header banner (Modern dark slate)
        header_frame = tk.Frame(self.root, bg="#0f172a", height=72)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)

        # Load header logo
        logo_path = os.path.join(self.base_dir, "header_logo.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(self.base_dir, "assets", "header_logo.png")

        if os.path.exists(logo_path):
            try:
                self._header_logo_img = tk.PhotoImage(file=logo_path)
                logo_lbl = tk.Label(header_frame, image=self._header_logo_img, bg="#0f172a")
                logo_lbl.pack(side=tk.LEFT, padx=(16, 12), pady=12)
            except Exception:
                pass

        text_container = tk.Frame(header_frame, bg="#0f172a")
        text_container.pack(side=tk.LEFT, fill=tk.Y, pady=12)

        title_lbl = tk.Label(
            text_container,
            text="NCZ Forge",
            font=("Segoe UI", 16, "bold"),
            fg="#38bdf8",
            bg="#0f172a",
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = tk.Label(
            text_container,
            text="Netcad (NCZ) ⮂ AutoCAD (DXF) Dönüştürücü, Vektör PDF & TIF Dışa Aktarımı",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0f172a",
        )
        subtitle_lbl.pack(anchor="w")

        # Main notebook (Tabs)
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: DXF -> NCZ
        self.tab_d2n = tk.Frame(self.notebook, bg=self.bg_color, padx=12, pady=10)
        self.notebook.add(self.tab_d2n, text=" 🔄  DXF ➔ NCZ (Netcad Yap) ")
        self._build_d2n_tab()

        # Tab 2: NCZ -> DXF
        self.tab_n2d = tk.Frame(self.notebook, bg=self.bg_color, padx=12, pady=10)
        self.notebook.add(self.tab_n2d, text=" 🔄  NCZ ➔ DXF (AutoCAD Yap) ")
        self._build_n2d_tab()

        # Tab 3: Export to PDF & TIF
        self.tab_exp = tk.Frame(self.notebook, bg=self.bg_color, padx=12, pady=10)
        self.notebook.add(self.tab_exp, text=" 📄  PDF & TIF Dışa Aktar ")
        self._build_exp_tab()

        # Tab 4: Batch (Çoklu NCZ / DXF)
        self.tab_batch = tk.Frame(self.notebook, bg=self.bg_color, padx=12, pady=10)
        self.notebook.add(self.tab_batch, text=" 📚  Çoklu Dönüştür ")
        self._build_batch_tab()

    # ------------------ TAB 1: DXF -> NCZ ------------------
    def _build_d2n_tab(self):
        # Drop Zone Box
        self.drop_d2n_box = tk.Frame(
            self.tab_d2n,
            bg=self.drop_idle_bg,
            highlightbackground="#99c2ff",
            highlightthickness=2,
            relief=tk.FLAT,
            cursor="hand2",
            pady=10,
        )
        self.drop_d2n_box.pack(fill=tk.X, pady=(0, 8))
        self.drop_d2n_box.bind("<Button-1>", lambda e: self.browse_d2n_dxf())

        self.lbl_drop_d2n_icon = tk.Label(
            self.drop_d2n_box,
            text="📥",
            font=("Segoe UI", 18),
            bg=self.drop_idle_bg,
            fg=self.drop_idle_fg,
            cursor="hand2",
        )
        self.lbl_drop_d2n_icon.pack()
        self.lbl_drop_d2n_icon.bind("<Button-1>", lambda e: self.browse_d2n_dxf())

        self.lbl_drop_d2n_text = tk.Label(
            self.drop_d2n_box,
            text="DXF Dosyasını Buraya Sürükleyip Bırakın\n(veya tıklayarak dosya seçin)",
            font=("Segoe UI", 9, "bold"),
            bg=self.drop_idle_bg,
            fg=self.drop_idle_fg,
            cursor="hand2",
        )
        self.lbl_drop_d2n_text.pack()
        self.lbl_drop_d2n_text.bind("<Button-1>", lambda e: self.browse_d2n_dxf())

        # Inputs
        card1 = tk.LabelFrame(self.tab_d2n, text=" Girdi DXF Dosyası ", font=("Segoe UI", 8, "bold"), bg=self.card_bg, fg="#444444", padx=10, pady=5)
        card1.pack(fill=tk.X, pady=(0, 5))
        f1 = tk.Frame(card1, bg=self.card_bg)
        f1.pack(fill=tk.X)
        ttk.Entry(f1, textvariable=self.d2n_dxf_var, font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        tk.Button(f1, text="Seç...", command=self.browse_d2n_dxf, font=("Segoe UI", 8), bg="#e2e8f0", relief=tk.GROOVE, padx=8).pack(side=tk.RIGHT)

        card2 = tk.LabelFrame(self.tab_d2n, text=" Çıktı NCZ Dosyası ", font=("Segoe UI", 8, "bold"), bg=self.card_bg, fg="#444444", padx=10, pady=5)
        card2.pack(fill=tk.X, pady=(0, 5))
        f2 = tk.Frame(card2, bg=self.card_bg)
        f2.pack(fill=tk.X)
        ttk.Entry(f2, textvariable=self.d2n_ncz_var, font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        tk.Button(f2, text="Hedef...", command=self.browse_d2n_ncz, font=("Segoe UI", 8), bg="#e2e8f0", relief=tk.GROOVE, padx=8).pack(side=tk.RIGHT)

        # Settings
        card3 = tk.LabelFrame(self.tab_d2n, text=" Ayarlar & Şablon ", font=("Segoe UI", 8, "bold"), bg=self.card_bg, fg="#444444", padx=10, pady=5)
        card3.pack(fill=tk.X, pady=(0, 6))
        f3 = tk.Frame(card3, bg=self.card_bg)
        f3.pack(fill=tk.X, pady=(0, 3))
        tk.Label(f3, text="NCZ Şablonu:", font=("Segoe UI", 8), bg=self.card_bg).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(f3, textvariable=self.d2n_template_var, font=("Segoe UI", 8)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        tk.Button(f3, text="Şablon Seç", command=self.browse_d2n_template, font=("Segoe UI", 8), bg="#e2e8f0", relief=tk.GROOVE, padx=6).pack(side=tk.RIGHT)
        ttk.Checkbutton(card3, text="X ve Y koordinatlarını yer değiştir (Swap X/Y)", variable=self.d2n_swap_xy_var).pack(anchor="w")

        # Action Buttons Frame
        btn_box = tk.Frame(self.tab_d2n, bg=self.bg_color)
        btn_box.pack(fill=tk.X, pady=(2, 4))

        self.btn_convert_d2n = tk.Button(
            btn_box,
            text="🚀 DXF'ten NCZ'ye Dönüştür",
            command=self.start_d2n_conversion,
            font=("Segoe UI", 10, "bold"),
            bg=self.primary_color,
            fg="#ffffff",
            activebackground="#0052a3",
            activeforeground="#ffffff",
            relief=tk.RAISED,
            cursor="hand2",
            pady=6,
        )
        self.btn_convert_d2n.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        # Quick Export Buttons for DXF
        self.btn_d2n_pdf = tk.Button(
            btn_box,
            text="📄 PDF Yap",
            command=lambda: self.quick_export_dxf("pdf"),
            font=("Segoe UI", 9, "bold"),
            bg=self.pdf_color,
            fg="#ffffff",
            relief=tk.RAISED,
            cursor="hand2",
            padx=10,
            pady=6,
        )
        self.btn_d2n_pdf.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_d2n_tif = tk.Button(
            btn_box,
            text="🖼️ TIF Yap",
            command=lambda: self.quick_export_dxf("tif"),
            font=("Segoe UI", 9, "bold"),
            bg=self.tif_color,
            fg="#ffffff",
            relief=tk.RAISED,
            cursor="hand2",
            padx=10,
            pady=6,
        )
        self.btn_d2n_tif.pack(side=tk.LEFT)

        # Status & Progress Frame
        prog_frame_1 = tk.Frame(self.tab_d2n, bg=self.bg_color)
        prog_frame_1.pack(fill=tk.X, pady=(6, 2))

        self.status_d2n_lbl = tk.Label(prog_frame_1, text="DXF dosyanızı seçin veya sürükleyin.", font=("Segoe UI", 9), fg="#666666", bg=self.bg_color)
        self.status_d2n_lbl.pack(anchor="w", pady=(0, 2))
        self.prog_d2n = ttk.Progressbar(prog_frame_1, mode="determinate", maximum=100)
        self.prog_d2n.pack(fill=tk.X, pady=(0, 4))

        self.btn_open_folder_d2n = tk.Button(self.tab_d2n, text="📁 Çıktı Klasörünü Aç", command=lambda: self.open_folder(self.d2n_ncz_var.get()), font=("Segoe UI", 8), bg="#e2e8f0", relief=tk.GROOVE, state=tk.DISABLED)
        self.btn_open_folder_d2n.pack(anchor="e")

    def _set_d2n_buttons_state(self, state):
        self.btn_convert_d2n.config(state=state)
        self.btn_d2n_pdf.config(state=state)
        self.btn_d2n_tif.config(state=state)

    def _update_prog_step(self, prog: ttk.Progressbar, lbl: tk.Label, text: str, pct: int):
        prog["value"] = pct
        lbl.config(text=f"[{pct}%] {text}", fg="#0066cc")

    def _on_task_error(self, err_msg: str, title: str, lbl: tk.Label, prog: ttk.Progressbar, state_fn):
        prog["value"] = 0
        state_fn(tk.NORMAL)
        lbl.config(text=f"Hata: {err_msg[:60]}", fg="#cc0000")
        messagebox.showerror("Hata", f"{title} sırasında hata oluştu:\n\n{err_msg}", parent=self.root)

    def _set_d2n_drop_active(self, filename: str):
        size_kb = os.path.getsize(filename) / 1024.0 if os.path.exists(filename) else 0
        name = os.path.basename(filename)
        self.drop_d2n_box.config(bg=self.drop_ready_bg, highlightbackground="#28a745")
        self.lbl_drop_d2n_icon.config(text="✓", fg=self.drop_ready_fg, bg=self.drop_ready_bg)
        self.lbl_drop_d2n_text.config(text=f"DXF Yüklendi: {name} ({size_kb:.1f} KB)\nDönüştürmek için aşağıdaki butonları kullanabilirsiniz.", fg=self.drop_ready_fg, bg=self.drop_ready_bg)

    def browse_d2n_dxf(self):
        f = filedialog.askopenfilename(title="Dönüştürülecek DXF Dosyasını Seçin", filetypes=[("AutoCAD DXF (*.dxf)", "*.dxf"), ("Tüm Dosyalar (*.*)", "*.*")])
        if f:
            self.set_d2n_dxf(f)
            self._set_d2n_drop_active(f)

    def set_d2n_dxf(self, filename: str):
        self.d2n_dxf_var.set(filename)
        base, _ = os.path.splitext(filename)
        self.d2n_ncz_var.set(base + ".NCZ")
        self.exp_input_var.set(filename)
        self.prog_d2n["value"] = 0
        self.status_d2n_lbl.config(text=f"Seçilen dosya: {os.path.basename(filename)} - Hazır.", fg="#0066cc")

    def browse_d2n_ncz(self):
        f = filedialog.asksaveasfilename(title="NCZ Çıktı Dosyasının Kaydedileceği Yer", defaultextension=".NCZ", filetypes=[("Netcad NCZ (*.NCZ)", "*.NCZ"), ("Tüm Dosyalar (*.*)", "*.*")])
        if f:
            self.d2n_ncz_var.set(f)

    def browse_d2n_template(self):
        f = filedialog.askopenfilename(title="Şablon NCZ Dosyası Seçin (İsteğe Bağlı)", filetypes=[("Netcad NCZ (*.NCZ)", "*.NCZ"), ("Tüm Dosyalar (*.*)", "*.*")])
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

        self._set_d2n_buttons_state(tk.DISABLED)
        self._update_prog_step(self.prog_d2n, self.status_d2n_lbl, "NCZ'ye dönüştürme başlatılıyor...", 5)

        def cb(msg, pct):
            self.root.after(0, lambda: self._update_prog_step(self.prog_d2n, self.status_d2n_lbl, msg, pct))

        def worker():
            try:
                cnt = convert_dxf_to_ncz(dxf_path=dxf_path, ncz_path=ncz_path, template_path=template_path, swap_xy=swap_xy, progress_callback=cb)
                size_kb = os.path.getsize(ncz_path) / 1024.0
                self.root.after(0, lambda: self._on_d2n_success(ncz_path, cnt, size_kb))
            except Exception as ex:
                err_msg = str(ex)
                self.root.after(0, lambda: self._on_task_error(err_msg, "DXF ➔ NCZ Dönüştürme", self.status_d2n_lbl, self.prog_d2n, self._set_d2n_buttons_state))

        threading.Thread(target=worker, daemon=True).start()

    def _on_d2n_success(self, ncz_path: str, count: int, size_kb: float):
        self.prog_d2n["value"] = 100
        self._set_d2n_buttons_state(tk.NORMAL)
        self.btn_open_folder_d2n.config(state=tk.NORMAL)
        msg = f"NCZ dosyası başarıyla oluşturuldu!\n\nDosya: {os.path.basename(ncz_path)}\nToplam Obje: {count:,} adet\nBoyut: {size_kb:.1f} KB"
        self.status_d2n_lbl.config(text=f"✓ Dönüştürme başarılı! ({count} obje, {size_kb:.1f} KB)", fg=self.success_color)
        messagebox.showinfo("Dönüştürme Başarılı", msg, parent=self.root)

    def quick_export_dxf(self, fmt: str):
        dxf_path = self.d2n_dxf_var.get().strip()
        if not dxf_path or not os.path.exists(dxf_path):
            messagebox.showwarning("Uyarı", "Lütfen önce geçerli bir DXF dosyası seçin.", parent=self.root)
            return
        base, _ = os.path.splitext(dxf_path)
        out_path = f"{base}.{fmt}"

        self._set_d2n_buttons_state(tk.DISABLED)
        self._update_prog_step(self.prog_d2n, self.status_d2n_lbl, f"{fmt.upper()} işlemi başlatılıyor...", 5)

        def cb(msg, pct):
            self.root.after(0, lambda: self._update_prog_step(self.prog_d2n, self.status_d2n_lbl, msg, pct))

        def worker():
            try:
                if fmt == "pdf":
                    export_dxf_to_pdf(dxf_path, out_path, dpi=300, progress_callback=cb)
                else:
                    export_dxf_to_tif(dxf_path, out_path, dpi=300, progress_callback=cb)
                size_kb = os.path.getsize(out_path) / 1024.0
                self.root.after(0, lambda: self._on_d2n_quick_success(out_path, fmt, size_kb))
            except Exception as ex:
                err_msg = str(ex)
                self.root.after(0, lambda: self._on_task_error(err_msg, f"DXF ➔ {fmt.upper()} Dışa Aktarma", self.status_d2n_lbl, self.prog_d2n, self._set_d2n_buttons_state))

        threading.Thread(target=worker, daemon=True).start()

    def _on_d2n_quick_success(self, out_path: str, fmt: str, size_kb: float):
        self.prog_d2n["value"] = 100
        self._set_d2n_buttons_state(tk.NORMAL)
        self.btn_open_folder_d2n.config(state=tk.NORMAL)
        self.status_d2n_lbl.config(text=f"✓ {fmt.upper()} başarıyla oluşturuldu! ({size_kb:.1f} KB)", fg=self.success_color)
        messagebox.showinfo("Dışa Aktarım Başarılı", f"{fmt.upper()} dosyası oluşturuldu:\n\n{os.path.basename(out_path)}\nBoyut: {size_kb:.1f} KB", parent=self.root)

    # ------------------ TAB 2: NCZ -> DXF ------------------
    def _build_n2d_tab(self):
        # Drop Zone Box
        self.drop_n2d_box = tk.Frame(
            self.tab_n2d,
            bg=self.drop_idle_bg,
            highlightbackground="#99c2ff",
            highlightthickness=2,
            relief=tk.FLAT,
            cursor="hand2",
            pady=10,
        )
        self.drop_n2d_box.pack(fill=tk.X, pady=(0, 8))
        self.drop_n2d_box.bind("<Button-1>", lambda e: self.browse_n2d_ncz())

        self.lbl_drop_n2d_icon = tk.Label(
            self.drop_n2d_box,
            text="📥",
            font=("Segoe UI", 18),
            bg=self.drop_idle_bg,
            fg=self.drop_idle_fg,
            cursor="hand2",
        )
        self.lbl_drop_n2d_icon.pack()
        self.lbl_drop_n2d_icon.bind("<Button-1>", lambda e: self.browse_n2d_ncz())

        self.lbl_drop_n2d_text = tk.Label(
            self.drop_n2d_box,
            text="NCZ Dosyasını Buraya Sürükleyip Bırakın\n(veya tıklayarak dosya seçin)",
            font=("Segoe UI", 9, "bold"),
            bg=self.drop_idle_bg,
            fg=self.drop_idle_fg,
            cursor="hand2",
        )
        self.lbl_drop_n2d_text.pack()
        self.lbl_drop_n2d_text.bind("<Button-1>", lambda e: self.browse_n2d_ncz())

        # Inputs
        card1 = tk.LabelFrame(self.tab_n2d, text=" Girdi Netcad NCZ Dosyası ", font=("Segoe UI", 8, "bold"), bg=self.card_bg, fg="#444444", padx=10, pady=5)
        card1.pack(fill=tk.X, pady=(0, 5))
        f1 = tk.Frame(card1, bg=self.card_bg)
        f1.pack(fill=tk.X)
        ttk.Entry(f1, textvariable=self.n2d_ncz_var, font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        tk.Button(f1, text="Seç...", command=self.browse_n2d_ncz, font=("Segoe UI", 8), bg="#e2e8f0", relief=tk.GROOVE, padx=8).pack(side=tk.RIGHT)

        card2 = tk.LabelFrame(self.tab_n2d, text=" Çıktı AutoCAD DXF Dosyası ", font=("Segoe UI", 8, "bold"), bg=self.card_bg, fg="#444444", padx=10, pady=5)
        card2.pack(fill=tk.X, pady=(0, 5))
        f2 = tk.Frame(card2, bg=self.card_bg)
        f2.pack(fill=tk.X)
        ttk.Entry(f2, textvariable=self.n2d_dxf_var, font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        tk.Button(f2, text="Hedef...", command=self.browse_n2d_dxf, font=("Segoe UI", 8), bg="#e2e8f0", relief=tk.GROOVE, padx=8).pack(side=tk.RIGHT)

        card3 = tk.LabelFrame(self.tab_n2d, text=" DXF Sürüm Ayarları ", font=("Segoe UI", 8, "bold"), bg=self.card_bg, fg="#444444", padx=10, pady=5)
        card3.pack(fill=tk.X, pady=(0, 6))
        f3 = tk.Frame(card3, bg=self.card_bg)
        f3.pack(fill=tk.X)
        tk.Label(f3, text="AutoCAD DXF Sürümü:", font=("Segoe UI", 8), bg=self.card_bg).pack(side=tk.LEFT, padx=(0, 8))
        cb_ver = ttk.Combobox(f3, textvariable=self.n2d_version_var, values=["R2010", "R2018", "R2007", "R2004", "R2000"], state="readonly", width=12)
        cb_ver.pack(side=tk.LEFT)

        # Action Buttons Frame
        btn_box2 = tk.Frame(self.tab_n2d, bg=self.bg_color)
        btn_box2.pack(fill=tk.X, pady=(2, 4))

        self.btn_convert_n2d = tk.Button(
            btn_box2,
            text="🚀 NCZ'den DXF'e Dönüştür",
            command=self.start_n2d_conversion,
            font=("Segoe UI", 10, "bold"),
            bg=self.primary_color,
            fg="#ffffff",
            activebackground="#0052a3",
            activeforeground="#ffffff",
            relief=tk.RAISED,
            cursor="hand2",
            pady=6,
        )
        self.btn_convert_n2d.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        # Quick Export Buttons for NCZ
        self.btn_n2d_pdf = tk.Button(
            btn_box2,
            text="📄 PDF Yap",
            command=lambda: self.quick_export_ncz("pdf"),
            font=("Segoe UI", 9, "bold"),
            bg=self.pdf_color,
            fg="#ffffff",
            relief=tk.RAISED,
            cursor="hand2",
            padx=10,
            pady=6,
        )
        self.btn_n2d_pdf.pack(side=tk.LEFT, padx=(0, 4))

        self.btn_n2d_tif = tk.Button(
            btn_box2,
            text="🖼️ TIF Yap",
            command=lambda: self.quick_export_ncz("tif"),
            font=("Segoe UI", 9, "bold"),
            bg=self.tif_color,
            fg="#ffffff",
            relief=tk.RAISED,
            cursor="hand2",
            padx=10,
            pady=6,
        )
        self.btn_n2d_tif.pack(side=tk.LEFT)

        # Status & Progress Frame
        prog_frame_2 = tk.Frame(self.tab_n2d, bg=self.bg_color)
        prog_frame_2.pack(fill=tk.X, pady=(6, 2))

        self.status_n2d_lbl = tk.Label(prog_frame_2, text="NCZ dosyanızı seçin veya sürükleyin.", font=("Segoe UI", 9), fg="#666666", bg=self.bg_color)
        self.status_n2d_lbl.pack(anchor="w", pady=(0, 2))
        self.prog_n2d = ttk.Progressbar(prog_frame_2, mode="determinate", maximum=100)
        self.prog_n2d.pack(fill=tk.X, pady=(0, 4))

        self.btn_open_folder_n2d = tk.Button(self.tab_n2d, text="📁 Çıktı Klasörünü Aç", command=lambda: self.open_folder(self.n2d_dxf_var.get()), font=("Segoe UI", 8), bg="#e2e8f0", relief=tk.GROOVE, state=tk.DISABLED)
        self.btn_open_folder_n2d.pack(anchor="e")

    def _set_n2d_buttons_state(self, state):
        self.btn_convert_n2d.config(state=state)
        self.btn_n2d_pdf.config(state=state)
        self.btn_n2d_tif.config(state=state)

    def _set_n2d_drop_active(self, filename: str):
        size_kb = os.path.getsize(filename) / 1024.0 if os.path.exists(filename) else 0
        name = os.path.basename(filename)
        self.drop_n2d_box.config(bg=self.drop_ready_bg, highlightbackground="#28a745")
        self.lbl_drop_n2d_icon.config(text="✓", fg=self.drop_ready_fg, bg=self.drop_ready_bg)
        self.lbl_drop_n2d_text.config(text=f"NCZ Yüklendi: {name} ({size_kb:.1f} KB)\nDönüştürmek için aşağıdaki butonları kullanabilirsiniz.", fg=self.drop_ready_fg, bg=self.drop_ready_bg)

    def browse_n2d_ncz(self):
        f = filedialog.askopenfilename(title="Dönüştürülecek NCZ Dosyasını Seçin", filetypes=[("Netcad NCZ (*.NCZ;*.ncz)", "*.NCZ;*.ncz"), ("Tüm Dosyalar (*.*)", "*.*")])
        if f:
            self.set_n2d_ncz(f)
            self._set_n2d_drop_active(f)

    def set_n2d_ncz(self, filename: str):
        self.n2d_ncz_var.set(filename)
        base, _ = os.path.splitext(filename)
        self.n2d_dxf_var.set(base + ".dxf")
        self.exp_input_var.set(filename)
        self.prog_n2d["value"] = 0
        self.status_n2d_lbl.config(text=f"Seçilen dosya: {os.path.basename(filename)} - Hazır.", fg="#0066cc")

    def browse_n2d_dxf(self):
        f = filedialog.asksaveasfilename(title="DXF Çıktı Dosyasının Kaydedileceği Yer", defaultextension=".dxf", filetypes=[("AutoCAD DXF (*.dxf)", "*.dxf"), ("Tüm Dosyalar (*.*)", "*.*")])
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

        self._set_n2d_buttons_state(tk.DISABLED)
        self._update_prog_step(self.prog_n2d, self.status_n2d_lbl, "DXF'e dönüştürme başlatılıyor...", 5)

        def cb(msg, pct):
            self.root.after(0, lambda: self._update_prog_step(self.prog_n2d, self.status_n2d_lbl, msg, pct))

        def worker():
            try:
                cnt = convert_ncz_to_dxf(ncz_path=ncz_path, dxf_path=dxf_path, dxf_version=dxf_version, progress_callback=cb)
                size_kb = os.path.getsize(dxf_path) / 1024.0
                self.root.after(0, lambda: self._on_n2d_success(dxf_path, cnt, size_kb))
            except Exception as ex:
                err_msg = str(ex)
                self.root.after(0, lambda: self._on_task_error(err_msg, "NCZ ➔ DXF Dönüştürme", self.status_n2d_lbl, self.prog_n2d, self._set_n2d_buttons_state))

        threading.Thread(target=worker, daemon=True).start()

    def _on_n2d_success(self, dxf_path: str, count: int, size_kb: float):
        self.prog_n2d["value"] = 100
        self._set_n2d_buttons_state(tk.NORMAL)
        self.btn_open_folder_n2d.config(state=tk.NORMAL)
        msg = f"DXF dosyası başarıyla oluşturuldu!\n\nDosya: {os.path.basename(dxf_path)}\nToplam Obje: {count:,} adet\nBoyut: {size_kb:.1f} KB"
        self.status_n2d_lbl.config(text=f"✓ Dönüştürme başarılı! ({count} obje, {size_kb:.1f} KB)", fg=self.success_color)
        messagebox.showinfo("Dönüştürme Başarılı", msg, parent=self.root)

    def quick_export_ncz(self, fmt: str):
        ncz_path = self.n2d_ncz_var.get().strip()
        if not ncz_path or not os.path.exists(ncz_path):
            messagebox.showwarning("Uyarı", "Lütfen önce geçerli bir NCZ dosyası seçin.", parent=self.root)
            return
        base, _ = os.path.splitext(ncz_path)
        out_path = f"{base}.{fmt}"

        self._set_n2d_buttons_state(tk.DISABLED)
        self._update_prog_step(self.prog_n2d, self.status_n2d_lbl, f"{fmt.upper()} işlemi başlatılıyor...", 5)

        def cb(msg, pct):
            self.root.after(0, lambda: self._update_prog_step(self.prog_n2d, self.status_n2d_lbl, msg, pct))

        def worker():
            try:
                if fmt == "pdf":
                    export_ncz_to_pdf(ncz_path, out_path, dpi=300, progress_callback=cb)
                else:
                    export_ncz_to_tif(ncz_path, out_path, dpi=300, progress_callback=cb)
                size_kb = os.path.getsize(out_path) / 1024.0
                self.root.after(0, lambda: self._on_n2d_quick_success(out_path, fmt, size_kb))
            except Exception as ex:
                err_msg = str(ex)
                self.root.after(0, lambda: self._on_task_error(err_msg, f"NCZ ➔ {fmt.upper()} Dışa Aktarma", self.status_n2d_lbl, self.prog_n2d, self._set_n2d_buttons_state))

        threading.Thread(target=worker, daemon=True).start()

    def _on_n2d_quick_success(self, out_path: str, fmt: str, size_kb: float):
        self.prog_n2d["value"] = 100
        self._set_n2d_buttons_state(tk.NORMAL)
        self.btn_open_folder_n2d.config(state=tk.NORMAL)
        self.status_n2d_lbl.config(text=f"✓ {fmt.upper()} başarıyla oluşturuldu! ({size_kb:.1f} KB)", fg=self.success_color)
        messagebox.showinfo("Dışa Aktarım Başarılı", f"{fmt.upper()} dosyası oluşturuldu:\n\n{os.path.basename(out_path)}\nBoyut: {size_kb:.1f} KB", parent=self.root)

    # ------------------ TAB 3: DEDICATED PDF & TIF EXPORT ------------------
    def _build_exp_tab(self):
        # Drop Zone Box
        self.drop_exp_box = tk.Frame(
            self.tab_exp,
            bg=self.drop_idle_bg,
            highlightbackground="#99c2ff",
            highlightthickness=2,
            relief=tk.FLAT,
            cursor="hand2",
            pady=12,
        )
        self.drop_exp_box.pack(fill=tk.X, pady=(0, 10))
        self.drop_exp_box.bind("<Button-1>", lambda e: self.browse_exp_file())

        lbl_icon = tk.Label(self.drop_exp_box, text="📄", font=("Segoe UI", 20), bg=self.drop_idle_bg, fg=self.drop_idle_fg, cursor="hand2")
        lbl_icon.pack()
        lbl_icon.bind("<Button-1>", lambda e: self.browse_exp_file())

        self.lbl_exp_drop_text = tk.Label(
            self.drop_exp_box,
            text="NCZ veya DXF Dosyasını Buraya Sürükleyip Bırakın\n(veya tıklayarak dosya seçin)",
            font=("Segoe UI", 9, "bold"),
            bg=self.drop_idle_bg,
            fg=self.drop_idle_fg,
            cursor="hand2",
        )
        self.lbl_exp_drop_text.pack()
        self.lbl_exp_drop_text.bind("<Button-1>", lambda e: self.browse_exp_file())

        # 1. File Path
        card1 = tk.LabelFrame(self.tab_exp, text=" 1. Girdi Çizim Dosyası (NCZ veya DXF) ", font=("Segoe UI", 8, "bold"), bg=self.card_bg, fg="#444444", padx=10, pady=6)
        card1.pack(fill=tk.X, pady=(0, 8))
        f1 = tk.Frame(card1, bg=self.card_bg)
        f1.pack(fill=tk.X)
        ttk.Entry(f1, textvariable=self.exp_input_var, font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        tk.Button(f1, text="Dosya Seç...", command=self.browse_exp_file, font=("Segoe UI", 8), bg="#e2e8f0", relief=tk.GROOVE, padx=8).pack(side=tk.RIGHT)

        # 2. Options Card
        card2 = tk.LabelFrame(self.tab_exp, text=" 2. Dışa Aktarım Formatı & Ayarlar ", font=("Segoe UI", 8, "bold"), bg=self.card_bg, fg="#444444", padx=10, pady=8)
        card2.pack(fill=tk.X, pady=(0, 10))

        # Format Radio
        f_fmt = tk.Frame(card2, bg=self.card_bg)
        f_fmt.pack(fill=tk.X, pady=(0, 6))
        tk.Label(f_fmt, text="Hedef Format:", font=("Segoe UI", 9, "bold"), bg=self.card_bg).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(f_fmt, text="📄 PDF (Vektörel Çizim)", value="PDF", variable=self.exp_format_var).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(f_fmt, text="🖼️ TIF (Yüksek Çözünürlüklü Görüntü)", value="TIF", variable=self.exp_format_var).pack(side=tk.LEFT)

        # DPI & Background
        f_opts = tk.Frame(card2, bg=self.card_bg)
        f_opts.pack(fill=tk.X)
        tk.Label(f_opts, text="Çözünürlük (DPI):", font=("Segoe UI", 8), bg=self.card_bg).pack(side=tk.LEFT, padx=(0, 5))
        cb_dpi = ttk.Combobox(f_opts, textvariable=self.exp_dpi_var, values=[150, 300, 600], state="readonly", width=8)
        cb_dpi.pack(side=tk.LEFT, padx=(0, 20))

        tk.Label(f_opts, text="Arka Plan:", font=("Segoe UI", 8), bg=self.card_bg).pack(side=tk.LEFT, padx=(0, 5))
        cb_bg = ttk.Combobox(f_opts, textvariable=self.exp_bg_var, values=["white", "black"], state="readonly", width=8)
        cb_bg.pack(side=tk.LEFT)

        # Action Button
        self.btn_export_dedicated = tk.Button(
            self.tab_exp,
            text="🚀 Seçilen Formatı Dışa Aktar",
            command=self.start_dedicated_export,
            font=("Segoe UI", 11, "bold"),
            bg=self.primary_color,
            fg="#ffffff",
            activebackground="#0052a3",
            activeforeground="#ffffff",
            relief=tk.RAISED,
            cursor="hand2",
            pady=8,
        )
        self.btn_export_dedicated.pack(fill=tk.X, pady=(2, 6))

        # Status & Progress Frame
        prog_frame_3 = tk.Frame(self.tab_exp, bg=self.bg_color)
        prog_frame_3.pack(fill=tk.X, pady=(6, 2))

        self.status_exp_lbl = tk.Label(prog_frame_3, text="NCZ veya DXF dosyanızı seçin veya sürükleyin.", font=("Segoe UI", 9), fg="#666666", bg=self.bg_color)
        self.status_exp_lbl.pack(anchor="w", pady=(0, 2))
        self.prog_exp = ttk.Progressbar(prog_frame_3, mode="determinate", maximum=100)
        self.prog_exp.pack(fill=tk.X, pady=(0, 4))

        self.last_exp_out = ""
        self.btn_open_folder_exp = tk.Button(self.tab_exp, text="📁 Çıktı Klasörünü Aç", command=lambda: self.open_folder(self.last_exp_out), font=("Segoe UI", 8), bg="#e2e8f0", relief=tk.GROOVE, state=tk.DISABLED)
        self.btn_open_folder_exp.pack(anchor="e")

    def _set_exp_buttons_state(self, state):
        self.btn_export_dedicated.config(state=state)

    def browse_exp_file(self):
        f = filedialog.askopenfilename(
            title="Dışa Aktarılacak Çizim Dosyasını Seçin",
            filetypes=[("Çizim Dosyaları (*.ncz;*.dxf)", "*.ncz;*.NCZ;*.dxf;*.DXF"), ("Tüm Dosyalar (*.*)", "*.*")],
        )
        if f:
            self.exp_input_var.set(f)
            size_kb = os.path.getsize(f) / 1024.0
            self.lbl_exp_drop_text.config(text=f"Yüklendi: {os.path.basename(f)} ({size_kb:.1f} KB)\nDışa aktarmak için butona basın.", fg=self.drop_ready_fg)
            self.drop_exp_box.config(bg=self.drop_ready_bg, highlightbackground="#28a745")
            self.prog_exp["value"] = 0
            self.status_exp_lbl.config(text=f"Dosya yüklendi: {os.path.basename(f)}", fg="#0066cc")

    def start_dedicated_export(self):
        inp = self.exp_input_var.get().strip()
        if not inp or not os.path.exists(inp):
            messagebox.showwarning("Uyarı", "Lütfen geçerli bir NCZ veya DXF dosyası seçin.", parent=self.root)
            return

        fmt = self.exp_format_var.get().lower()
        dpi = int(self.exp_dpi_var.get())
        bg = self.exp_bg_var.get()
        base, ext = os.path.splitext(inp)
        ext = ext.lower()
        out_path = f"{base}.{fmt}"
        self.last_exp_out = out_path

        self._set_exp_buttons_state(tk.DISABLED)
        self._update_prog_step(self.prog_exp, self.status_exp_lbl, f"{fmt.upper()} işlemi başlatılıyor...", 5)

        def cb(msg, pct):
            self.root.after(0, lambda: self._update_prog_step(self.prog_exp, self.status_exp_lbl, msg, pct))

        def worker():
            try:
                if ext == ".dxf":
                    if fmt == "pdf":
                        export_dxf_to_pdf(inp, out_path, dpi=dpi, bg=bg, progress_callback=cb)
                    else:
                        export_dxf_to_tif(inp, out_path, dpi=dpi, bg=bg, progress_callback=cb)
                elif ext == ".ncz":
                    if fmt == "pdf":
                        export_ncz_to_pdf(inp, out_path, dpi=dpi, bg=bg, progress_callback=cb)
                    else:
                        export_ncz_to_tif(inp, out_path, dpi=dpi, bg=bg, progress_callback=cb)
                else:
                    raise ValueError(f"Desteklenmeyen dosya uzantısı: {ext}")

                size_kb = os.path.getsize(out_path) / 1024.0
                self.root.after(0, lambda: self._on_dedicated_success(out_path, fmt, size_kb))
            except Exception as ex:
                err_msg = str(ex)
                self.root.after(0, lambda: self._on_task_error(err_msg, f"{fmt.upper()} Dışa Aktarma", self.status_exp_lbl, self.prog_exp, self._set_exp_buttons_state))

        threading.Thread(target=worker, daemon=True).start()

    def _on_dedicated_success(self, out_path: str, fmt: str, size_kb: float):
        self.prog_exp["value"] = 100
        self._set_exp_buttons_state(tk.NORMAL)
        self.btn_open_folder_exp.config(state=tk.NORMAL)
        self.status_exp_lbl.config(text=f"✓ {fmt.upper()} başarıyla oluşturuldu! ({size_kb:.1f} KB)", fg=self.success_color)
        messagebox.showinfo("Dışa Aktarım Başarılı", f"{fmt.upper()} dosyası kaydedildi:\n\n{os.path.basename(out_path)}\nBoyut: {size_kb:.1f} KB", parent=self.root)

    # ------------------ TAB 4: BATCH (ÇOKLU NCZ / DXF) ------------------
    def _build_batch_tab(self):
        # File list
        card_list = tk.LabelFrame(self.tab_batch, text=" Dosya Listesi (NCZ ve DXF karışık olabilir — sürükleyip bırakabilirsiniz) ", font=("Segoe UI", 8, "bold"), bg=self.card_bg, fg="#444444", padx=8, pady=5)
        card_list.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        list_frame = tk.Frame(card_list, bg=self.card_bg)
        list_frame.pack(fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.batch_listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, font=("Consolas", 9), height=8, yscrollcommand=sb.set, activestyle="none")
        sb.config(command=self.batch_listbox.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.batch_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.batch_listbox.bind("<Delete>", lambda e: self.batch_remove_selected())

        btns = tk.Frame(card_list, bg=self.card_bg)
        btns.pack(fill=tk.X, pady=(5, 0))
        for text, cmd in (
            ("➕ Dosya Ekle...", self.batch_browse_files),
            ("📂 Klasör Ekle...", self.batch_browse_folder),
            ("➖ Seçileni Çıkar", self.batch_remove_selected),
            ("🗑️ Listeyi Temizle", self.batch_clear),
        ):
            tk.Button(btns, text=text, command=cmd, font=("Segoe UI", 8), bg="#e2e8f0", relief=tk.GROOVE, padx=6).pack(side=tk.LEFT, padx=(0, 4))
        tk.Checkbutton(btns, text="Alt klasörler dahil", variable=self.batch_recursive_var, font=("Segoe UI", 8), bg=self.card_bg).pack(side=tk.LEFT, padx=(6, 0))
        self.lbl_batch_count = tk.Label(btns, text="0 dosya", font=("Segoe UI", 8, "bold"), bg=self.card_bg, fg="#0066cc")
        self.lbl_batch_count.pack(side=tk.RIGHT)

        # Target + output
        card_opt = tk.LabelFrame(self.tab_batch, text=" Hedef ve Çıktı ", font=("Segoe UI", 8, "bold"), bg=self.card_bg, fg="#444444", padx=10, pady=5)
        card_opt.pack(fill=tk.X, pady=(0, 5))
        f_t = tk.Frame(card_opt, bg=self.card_bg)
        f_t.pack(fill=tk.X, pady=(0, 3))
        tk.Label(f_t, text="Hedef:", font=("Segoe UI", 8, "bold"), bg=self.card_bg).pack(side=tk.LEFT, padx=(0, 8))
        for text, val in (("NCZ ⮂ DXF (otomatik)", "auto"), ("📄 PDF", "pdf"), ("🖼️ TIF", "tif")):
            tk.Radiobutton(f_t, text=text, variable=self.batch_target_var, value=val, font=("Segoe UI", 8), bg=self.card_bg).pack(side=tk.LEFT, padx=(0, 10))

        f_o = tk.Frame(card_opt, bg=self.card_bg)
        f_o.pack(fill=tk.X)
        tk.Label(f_o, text="Çıktı Klasörü:", font=("Segoe UI", 8), bg=self.card_bg).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(f_o, textvariable=self.batch_outdir_var, font=("Segoe UI", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        tk.Button(f_o, text="Seç...", command=self.batch_browse_outdir, font=("Segoe UI", 8), bg="#e2e8f0", relief=tk.GROOVE, padx=8).pack(side=tk.RIGHT)
        tk.Label(card_opt, text="Boş bırakılırsa çıktılar her dosyanın kendi klasörüne kaydedilir. Şablon / DXF sürümü / DPI ayarları diğer sekmelerden alınır.", font=("Segoe UI", 7), fg="#777777", bg=self.card_bg).pack(anchor="w", pady=(3, 0))

        # Action buttons
        act = tk.Frame(self.tab_batch, bg=self.bg_color)
        act.pack(fill=tk.X, pady=(2, 4))
        self.btn_batch_start = tk.Button(act, text="🚀 Tümünü Dönüştür", command=self.start_batch, font=("Segoe UI", 10, "bold"), bg=self.primary_color, fg="#ffffff", activebackground="#0052a3", activeforeground="#ffffff", relief=tk.RAISED, cursor="hand2", pady=6)
        self.btn_batch_start.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.btn_batch_stop = tk.Button(act, text="⏹ Durdur", command=self.stop_batch, font=("Segoe UI", 9, "bold"), bg="#6c757d", fg="#ffffff", relief=tk.RAISED, padx=10, pady=6, state=tk.DISABLED)
        self.btn_batch_stop.pack(side=tk.LEFT)

        prog = tk.Frame(self.tab_batch, bg=self.bg_color)
        prog.pack(fill=tk.X, pady=(4, 2))
        self.status_batch_lbl = tk.Label(prog, text="Birden fazla NCZ / DXF dosyasını veya klasörü ekleyin.", font=("Segoe UI", 9), fg="#666666", bg=self.bg_color)
        self.status_batch_lbl.pack(anchor="w", pady=(0, 2))
        self.prog_batch = ttk.Progressbar(prog, mode="determinate", maximum=100)
        self.prog_batch.pack(fill=tk.X, pady=(0, 4))

        self.last_batch_out = ""
        self.btn_open_folder_batch = tk.Button(self.tab_batch, text="📁 Çıktı Klasörünü Aç", command=lambda: self.open_folder(self.last_batch_out), font=("Segoe UI", 8), bg="#e2e8f0", relief=tk.GROOVE, state=tk.DISABLED)
        self.btn_open_folder_batch.pack(anchor="e")

    def _batch_refresh_list(self):
        self.batch_listbox.delete(0, tk.END)
        for f in self.batch_files:
            tag = "NCZ" if f.lower().endswith(".ncz") else "DXF"
            self.batch_listbox.insert(tk.END, f"[{tag}] {f}")
        n_ncz = sum(1 for f in self.batch_files if f.lower().endswith(".ncz"))
        n_dxf = len(self.batch_files) - n_ncz
        self.lbl_batch_count.config(text=f"{len(self.batch_files)} dosya ({n_ncz} NCZ, {n_dxf} DXF)")

    def batch_add_paths(self, paths):
        before = len(self.batch_files)
        known = {os.path.normcase(f) for f in self.batch_files}
        for f in collect_files(paths, recursive=self.batch_recursive_var.get()):
            if os.path.normcase(f) not in known:
                known.add(os.path.normcase(f))
                self.batch_files.append(f)
        self._batch_refresh_list()
        added = len(self.batch_files) - before
        self.prog_batch["value"] = 0
        if added:
            self.status_batch_lbl.config(text=f"{added} dosya eklendi. Hazır.", fg="#0066cc")
        else:
            self.status_batch_lbl.config(text="Eklenecek yeni .ncz / .dxf dosyası bulunamadı.", fg="#cc6600")

    def batch_browse_files(self):
        files = filedialog.askopenfilenames(
            title="Dönüştürülecek NCZ / DXF Dosyalarını Seçin (çoklu seçim)",
            filetypes=[("Çizim Dosyaları (*.ncz;*.dxf)", "*.ncz;*.NCZ;*.dxf;*.DXF"), ("Netcad NCZ", "*.ncz;*.NCZ"), ("AutoCAD DXF", "*.dxf;*.DXF"), ("Tüm Dosyalar (*.*)", "*.*")],
        )
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
        for idx in reversed(self.batch_listbox.curselection()):
            del self.batch_files[idx]
        self._batch_refresh_list()

    def batch_clear(self):
        self.batch_files = []
        self._batch_refresh_list()
        self.prog_batch["value"] = 0
        self.status_batch_lbl.config(text="Liste temizlendi.", fg="#666666")

    def _set_batch_running(self, running: bool):
        self.btn_batch_start.config(state=tk.DISABLED if running else tk.NORMAL)
        self.btn_batch_stop.config(state=tk.NORMAL if running else tk.DISABLED)

    def stop_batch(self):
        self._batch_stop = True
        self.status_batch_lbl.config(text="Durduruluyor... (mevcut dosya bitince)", fg="#cc6600")

    def start_batch(self):
        files = list(self.batch_files)
        if not files:
            messagebox.showwarning("Uyarı", "Lütfen önce listeye NCZ / DXF dosyası ekleyin.", parent=self.root)
            return
        target = self.batch_target_var.get()
        out_dir = self.batch_outdir_var.get().strip() or None
        template = self.d2n_template_var.get().strip() or None
        if template and not os.path.exists(template):
            template = None
        opts = dict(
            target=target,
            output_dir=out_dir,
            template_path=template,
            swap_xy=self.d2n_swap_xy_var.get(),
            dxf_version=self.n2d_version_var.get().strip() or "R2010",
            dpi=int(self.exp_dpi_var.get()),
            bg=self.exp_bg_var.get(),
        )
        self._batch_stop = False
        self._set_batch_running(True)
        self.prog_batch["value"] = 0

        def cb(i, total, path):
            pct = int(i * 100 / total) if total else 100
            text = f"[{i + 1}/{total}] {os.path.basename(path)} işleniyor..." if path else "Tamamlandı."
            self.root.after(0, lambda: (self.prog_batch.configure(value=pct), self.status_batch_lbl.config(text=text, fg="#0066cc")))

        def worker():
            try:
                summary = batch_convert(files, progress_callback=cb, stop_flag=lambda: self._batch_stop, **opts)
                self.root.after(0, lambda: self._on_batch_done(summary, len(files)))
            except Exception as ex:
                err_msg = str(ex)
                self.root.after(0, lambda: self._on_task_error(err_msg, "Toplu Dönüştürme", self.status_batch_lbl, self.prog_batch, lambda st: self._set_batch_running(False)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_batch_done(self, summary, total: int):
        self._set_batch_running(False)
        ok, bad = summary.succeeded, summary.failed
        skipped = total - len(summary.results)
        self.prog_batch["value"] = 100
        if ok:
            self.last_batch_out = ok[-1].output_path
            self.btn_open_folder_batch.config(state=tk.NORMAL)
        color = self.success_color if not bad else "#cc6600"
        self.status_batch_lbl.config(text=f"✓ Başarılı: {len(ok)}   ✗ Hatalı: {len(bad)}" + (f"   ⏭ Atlanan: {skipped}" if skipped else ""), fg=color)
        msg = f"Toplu dönüştürme bitti.\n\nBaşarılı: {len(ok)}\nHatalı: {len(bad)}"
        if skipped:
            msg += f"\nAtlanan (durduruldu): {skipped}"
        if bad:
            msg += "\n\nHatalı dosyalar:\n" + "\n".join(f"• {os.path.basename(r.input_path)}: {r.error[:80]}" for r in bad[:10])
            if len(bad) > 10:
                msg += f"\n... ve {len(bad) - 10} dosya daha"
            messagebox.showwarning("Toplu Dönüştürme", msg, parent=self.root)
        else:
            messagebox.showinfo("Toplu Dönüştürme", msg, parent=self.root)

    # ------------------ UTILS ------------------
    def open_folder(self, target_path: str):
        p = target_path.strip()
        if p and os.path.exists(p):
            folder = os.path.dirname(os.path.abspath(p))
            subprocess.run(["explorer", folder], shell=True)


def main():
    root = tk.Tk()
    app = DxfNczConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
