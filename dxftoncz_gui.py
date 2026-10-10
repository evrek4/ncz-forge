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
        self.root.title("NCZ & DXF Dönüştürücü ve PDF/TIF Aktarıcı v3.0")
        self.root.geometry("700x650")
        self.root.minsize(650, 590)

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

        # Set default template
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.argv[0])))
        cand_template = os.path.join(base_dir, "103_11.NCZ")
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
        if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
            self._handle_input_file(sys.argv[1])

    def on_files_dropped(self, file_list):
        if not file_list:
            return
        raw_path = file_list[0]
        if isinstance(raw_path, bytes):
            try:
                file_path = raw_path.decode("utf-8")
            except UnicodeDecodeError:
                file_path = raw_path.decode("windows-1254", errors="ignore")
        else:
            file_path = str(raw_path)

        file_path = os.path.abspath(file_path.strip(' "'))
        if os.path.exists(file_path):
            self._handle_input_file(file_path)

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
        # Header banner
        header_frame = tk.Frame(self.root, bg=self.primary_color, height=65)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)

        title_lbl = tk.Label(
            header_frame,
            text="NCZ ⮂ DXF Dönüştürücü & PDF/TIF Aktarıcı",
            font=("Segoe UI", 15, "bold"),
            fg="#ffffff",
            bg=self.primary_color,
        )
        title_lbl.pack(anchor="w", padx=20, pady=(10, 0))

        subtitle_lbl = tk.Label(
            header_frame,
            text="Netcad (NCZ) & AutoCAD (DXF) ➔ NCZ, DXF, PDF ve TIF Çıktıları",
            font=("Segoe UI", 9),
            fg="#d0e2ff",
            bg=self.primary_color,
        )
        subtitle_lbl.pack(anchor="w", padx=20, pady=(0, 10))

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
        tk.Button(
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
        ).pack(side=tk.LEFT, padx=(0, 4))

        tk.Button(
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
        ).pack(side=tk.LEFT)

        # Status & Progress
        self.status_d2n_lbl = tk.Label(self.tab_d2n, text="DXF dosyanızı seçin veya sürükleyin.", font=("Segoe UI", 8, "italic"), fg="#666666", bg=self.bg_color)
        self.status_d2n_lbl.pack(fill=tk.X, pady=(0, 2))
        self.prog_d2n = ttk.Progressbar(self.tab_d2n, mode="indeterminate")

        self.btn_open_folder_d2n = tk.Button(self.tab_d2n, text="📁 Çıktı Klasörünü Aç", command=lambda: self.open_folder(self.d2n_ncz_var.get()), font=("Segoe UI", 8), bg="#e2e8f0", relief=tk.GROOVE, state=tk.DISABLED)
        self.btn_open_folder_d2n.pack(anchor="e")

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
            messagebox.showwarning("Uyarı", "Lütfen geçerli bir DXF dosyası seçin veya sürükleyin.")
            return
        if not ncz_path:
            messagebox.showwarning("Uyarı", "Lütfen bir çıktı NCZ dosyası belirleyin.")
            return

        self.btn_convert_d2n.config(state=tk.DISABLED)
        self.prog_d2n.pack(fill=tk.X, pady=(0, 4))
        self.prog_d2n.start(10)
        self.status_d2n_lbl.config(text="NCZ'ye dönüştürülüyor...", fg="#0066cc")

        threading.Thread(target=self._worker_d2n, args=(dxf_path, ncz_path, template_path, swap_xy), daemon=True).start()

    def _worker_d2n(self, dxf_path, ncz_path, template_path, swap_xy):
        try:
            cnt = convert_dxf_to_ncz(dxf_path=dxf_path, ncz_path=ncz_path, template_path=template_path, swap_xy=swap_xy)
            size_kb = os.path.getsize(ncz_path) / 1024.0
            self.root.after(0, self._on_d2n_success, ncz_path, cnt, size_kb)
        except Exception as ex:
            self.root.after(0, self._on_d2n_error, str(ex))

    def _on_d2n_success(self, ncz_path: str, count: int, size_kb: float):
        self.prog_d2n.stop()
        self.prog_d2n.pack_forget()
        self.btn_convert_d2n.config(state=tk.NORMAL)
        self.btn_open_folder_d2n.config(state=tk.NORMAL)
        msg = f"NCZ dosyası başarıyla oluşturuldu!\n\nDosya: {os.path.basename(ncz_path)}\nToplam Obje: {count:,} adet\nBoyut: {size_kb:.1f} KB"
        self.status_d2n_lbl.config(text=f"✓ Dönüştürme başarılı! ({count} obje, {size_kb:.1f} KB)", fg=self.success_color)
        messagebox.showinfo("Dönüştürme Başarılı", msg)

    def _on_d2n_error(self, err_msg: str):
        self.prog_d2n.stop()
        self.prog_d2n.pack_forget()
        self.btn_convert_d2n.config(state=tk.NORMAL)
        self.status_d2n_lbl.config(text="Hata oluştu!", fg="#cc0000")
        messagebox.showerror("Hata", f"Dönüştürme hatası:\n\n{err_msg}")

    def quick_export_dxf(self, fmt: str):
        dxf_path = self.d2n_dxf_var.get().strip()
        if not dxf_path or not os.path.exists(dxf_path):
            messagebox.showwarning("Uyarı", "Lütfen önce bir DXF dosyası seçin.")
            return
        base, _ = os.path.splitext(dxf_path)
        out_path = f"{base}.{fmt}"
        self.status_d2n_lbl.config(text=f"{fmt.upper()} oluşturuluyor...", fg="#0066cc")
        self.prog_d2n.pack(fill=tk.X, pady=(0, 4))
        self.prog_d2n.start(10)

        def worker():
            try:
                if fmt == "pdf":
                    export_dxf_to_pdf(dxf_path, out_path, dpi=300)
                else:
                    export_dxf_to_tif(dxf_path, out_path, dpi=300)
                size_kb = os.path.getsize(out_path) / 1024.0
                self.root.after(0, lambda: self._on_quick_success(out_path, fmt, size_kb, self.status_d2n_lbl, self.prog_d2n, self.btn_open_folder_d2n))
            except Exception as ex:
                self.root.after(0, lambda: messagebox.showerror("Hata", f"{fmt.upper()} oluşturma hatası:\n{ex}"))

        threading.Thread(target=worker, daemon=True).start()

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
        tk.Button(
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
        ).pack(side=tk.LEFT, padx=(0, 4))

        tk.Button(
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
        ).pack(side=tk.LEFT)

        # Status & Progress
        self.status_n2d_lbl = tk.Label(self.tab_n2d, text="NCZ dosyanızı seçin veya sürükleyin.", font=("Segoe UI", 8, "italic"), fg="#666666", bg=self.bg_color)
        self.status_n2d_lbl.pack(fill=tk.X, pady=(0, 2))
        self.prog_n2d = ttk.Progressbar(self.tab_n2d, mode="indeterminate")

        self.btn_open_folder_n2d = tk.Button(self.tab_n2d, text="📁 Çıktı Klasörünü Aç", command=lambda: self.open_folder(self.n2d_dxf_var.get()), font=("Segoe UI", 8), bg="#e2e8f0", relief=tk.GROOVE, state=tk.DISABLED)
        self.btn_open_folder_n2d.pack(anchor="e")

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
            messagebox.showwarning("Uyarı", "Lütfen geçerli bir NCZ dosyası seçin veya sürükleyin.")
            return
        if not dxf_path:
            messagebox.showwarning("Uyarı", "Lütfen bir çıktı DXF dosyası belirleyin.")
            return

        self.btn_convert_n2d.config(state=tk.DISABLED)
        self.prog_n2d.pack(fill=tk.X, pady=(0, 4))
        self.prog_n2d.start(10)
        self.status_n2d_lbl.config(text="DXF'e dönüştürülüyor...", fg="#0066cc")

        threading.Thread(target=self._worker_n2d, args=(ncz_path, dxf_path, dxf_version), daemon=True).start()

    def _worker_n2d(self, ncz_path, dxf_path, dxf_version):
        try:
            cnt = convert_ncz_to_dxf(ncz_path=ncz_path, dxf_path=dxf_path, dxf_version=dxf_version)
            size_kb = os.path.getsize(dxf_path) / 1024.0
            self.root.after(0, self._on_n2d_success, dxf_path, cnt, size_kb)
        except Exception as ex:
            self.root.after(0, self._on_n2d_error, str(ex))

    def _on_n2d_success(self, dxf_path: str, count: int, size_kb: float):
        self.prog_n2d.stop()
        self.prog_d2n.pack_forget()
        self.btn_convert_n2d.config(state=tk.NORMAL)
        self.btn_open_folder_n2d.config(state=tk.NORMAL)
        msg = f"DXF dosyası başarıyla oluşturuldu!\n\nDosya: {os.path.basename(dxf_path)}\nToplam Obje: {count:,} adet\nBoyut: {size_kb:.1f} KB"
        self.status_n2d_lbl.config(text=f"✓ Dönüştürme başarılı! ({count} obje, {size_kb:.1f} KB)", fg=self.success_color)
        messagebox.showinfo("Dönüştürme Başarılı", msg)

    def _on_n2d_error(self, err_msg: str):
        self.prog_n2d.stop()
        self.prog_n2d.pack_forget()
        self.btn_convert_n2d.config(state=tk.NORMAL)
        self.status_n2d_lbl.config(text="Hata oluştu!", fg="#cc0000")
        messagebox.showerror("Hata", f"Dönüştürme hatası:\n\n{err_msg}")

    def quick_export_ncz(self, fmt: str):
        ncz_path = self.n2d_ncz_var.get().strip()
        if not ncz_path or not os.path.exists(ncz_path):
            messagebox.showwarning("Uyarı", "Lütfen önce bir NCZ dosyası seçin.")
            return
        base, _ = os.path.splitext(ncz_path)
        out_path = f"{base}.{fmt}"
        self.status_n2d_lbl.config(text=f"{fmt.upper()} oluşturuluyor...", fg="#0066cc")
        self.prog_n2d.pack(fill=tk.X, pady=(0, 4))
        self.prog_n2d.start(10)

        def worker():
            try:
                if fmt == "pdf":
                    export_ncz_to_pdf(ncz_path, out_path, dpi=300)
                else:
                    export_ncz_to_tif(ncz_path, out_path, dpi=300)
                size_kb = os.path.getsize(out_path) / 1024.0
                self.root.after(0, lambda: self._on_quick_success(out_path, fmt, size_kb, self.status_n2d_lbl, self.prog_n2d, self.btn_open_folder_n2d))
            except Exception as ex:
                self.root.after(0, lambda: messagebox.showerror("Hata", f"{fmt.upper()} oluşturma hatası:\n{ex}"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_quick_success(self, out_path: str, fmt: str, size_kb: float, lbl: tk.Label, prog: ttk.Progressbar, btn_open: tk.Button):
        prog.stop()
        prog.pack_forget()
        btn_open.config(state=tk.NORMAL)
        lbl.config(text=f"✓ {fmt.upper()} başarıyla oluşturuldu! ({size_kb:.1f} KB)", fg=self.success_color)
        messagebox.showinfo("Dışa Aktarım Başarılı", f"{fmt.upper()} dosyası oluşturuldu:\n\n{os.path.basename(out_path)}\nBoyut: {size_kb:.1f} KB")

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

        # Status & Progress
        self.status_exp_lbl = tk.Label(self.tab_exp, text="Bir NCZ veya DXF dosyası seçip dışa aktarın.", font=("Segoe UI", 8, "italic"), fg="#666666", bg=self.bg_color)
        self.status_exp_lbl.pack(fill=tk.X, pady=(0, 3))
        self.prog_exp = ttk.Progressbar(self.tab_exp, mode="indeterminate")

        self.last_exp_out = ""
        self.btn_open_folder_exp = tk.Button(self.tab_exp, text="📁 Çıktı Klasörünü Aç", command=lambda: self.open_folder(self.last_exp_out), font=("Segoe UI", 8), bg="#e2e8f0", relief=tk.GROOVE, state=tk.DISABLED)
        self.btn_open_folder_exp.pack(anchor="e")

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

    def start_dedicated_export(self):
        inp = self.exp_input_var.get().strip()
        if not inp or not os.path.exists(inp):
            messagebox.showwarning("Uyarı", "Lütfen geçerli bir NCZ veya DXF dosyası seçin.")
            return

        fmt = self.exp_format_var.get().lower()
        dpi = int(self.exp_dpi_var.get())
        bg = self.exp_bg_var.get()
        base, ext = os.path.splitext(inp)
        ext = ext.lower()
        out_path = f"{base}.{fmt}"
        self.last_exp_out = out_path

        self.btn_export_dedicated.config(state=tk.DISABLED)
        self.prog_exp.pack(fill=tk.X, pady=(0, 4))
        self.prog_exp.start(10)
        self.status_exp_lbl.config(text=f"{fmt.upper()} dosyası hazırlanıyor...", fg="#0066cc")

        def worker():
            try:
                if ext == ".dxf":
                    if fmt == "pdf":
                        export_dxf_to_pdf(inp, out_path, dpi=dpi, bg=bg)
                    else:
                        export_dxf_to_tif(inp, out_path, dpi=dpi, bg=bg)
                elif ext == ".ncz":
                    if fmt == "pdf":
                        export_ncz_to_pdf(inp, out_path, dpi=dpi, bg=bg)
                    else:
                        export_ncz_to_tif(inp, out_path, dpi=dpi, bg=bg)
                else:
                    raise ValueError(f"Desteklenmeyen uzantı: {ext}")

                size_kb = os.path.getsize(out_path) / 1024.0
                self.root.after(0, lambda: self._on_dedicated_success(out_path, fmt, size_kb))
            except Exception as ex:
                self.root.after(0, lambda: self._on_dedicated_error(str(ex)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_dedicated_success(self, out_path: str, fmt: str, size_kb: float):
        self.prog_exp.stop()
        self.prog_exp.pack_forget()
        self.btn_export_dedicated.config(state=tk.NORMAL)
        self.btn_open_folder_exp.config(state=tk.NORMAL)
        self.status_exp_lbl.config(text=f"✓ {fmt.upper()} başarıyla oluşturuldu! ({size_kb:.1f} KB)", fg=self.success_color)
        messagebox.showinfo("Dışa Aktarım Başarılı", f"{fmt.upper()} dosyası kaydedildi:\n\n{os.path.basename(out_path)}\nBoyut: {size_kb:.1f} KB")

    def _on_dedicated_error(self, err_msg: str):
        self.prog_exp.stop()
        self.prog_exp.pack_forget()
        self.btn_export_dedicated.config(state=tk.NORMAL)
        self.status_exp_lbl.config(text="Hata oluştu!", fg="#cc0000")
        messagebox.showerror("Hata", f"Dışa aktarma hatası:\n\n{err_msg}")

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
