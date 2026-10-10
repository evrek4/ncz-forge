"""
cad_export.py - CAD Export Engine for Netcad NCZ and AutoCAD DXF
Exports NCZ & DXF drawings to high-resolution PDF (vector) and TIFF (raster)
Copyright (C) 2026.
"""

from __future__ import annotations
import os
import tempfile
from typing import Optional, Callable

import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy

import matplotlib
matplotlib.use("Agg")  # Headless rendering
import matplotlib.backends.backend_pdf  # Explicitly import for PyInstaller bundling
import matplotlib.backends.backend_agg  # Explicitly import for PyInstaller bundling
import matplotlib.pyplot as plt
from PIL import Image

from ncz_to_dxf import convert_ncz_to_dxf


def _render_dxf_to_figure(
    doc: ezdxf.document.Drawing,
    bg: str = "white",
    figsize=(14, 10),
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> plt.Figure:
    """Render a DXF modelspace layout into a matplotlib Figure."""
    if progress_callback:
        progress_callback("Modelspace ve tabakalar taranıyor...", 45)

    msp = doc.modelspace()
    bg_policy = (
        BackgroundPolicy.WHITE if bg.lower() == "white" else BackgroundPolicy.BLACK
    )
    cfg = Configuration.defaults().with_changes(
        background_policy=bg_policy,
        color_policy=ColorPolicy.COLOR,
    )

    if progress_callback:
        progress_callback("CAD çizim motoru hazırlanıyor...", 60)

    fig = plt.figure(figsize=figsize)
    ax = fig.add_axes([0, 0, 1, 1])
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)

    if progress_callback:
        progress_callback("Geometriler tuvale işleniyor...", 75)

    Frontend(ctx, out, config=cfg).draw_layout(msp, finalize=True)
    return fig


def export_dxf_to_pdf(
    dxf_path: str,
    pdf_path: str,
    dpi: int = 300,
    bg: str = "white",
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> str:
    """Export AutoCAD DXF to high-precision vector PDF."""
    if not os.path.exists(dxf_path):
        raise FileNotFoundError(f"DXF dosyası bulunamadı: {dxf_path}")

    if progress_callback:
        progress_callback("DXF dosyası okunuyor...", 20)

    doc = ezdxf.readfile(dxf_path)
    fig = _render_dxf_to_figure(doc, bg=bg, progress_callback=progress_callback)
    try:
        if progress_callback:
            progress_callback("Vektör PDF dosyası derleniyor...", 88)
        fig.savefig(pdf_path, format="pdf", bbox_inches="tight")
        if progress_callback:
            progress_callback("PDF başarıyla kaydedildi.", 100)
    finally:
        plt.close(fig)
    return pdf_path


def export_dxf_to_tif(
    dxf_path: str,
    tif_path: str,
    dpi: int = 300,
    bg: str = "white",
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> str:
    """Export AutoCAD DXF to high-resolution compressed TIFF."""
    if not os.path.exists(dxf_path):
        raise FileNotFoundError(f"DXF dosyası bulunamadı: {dxf_path}")

    if progress_callback:
        progress_callback("DXF dosyası okunuyor...", 20)

    doc = ezdxf.readfile(dxf_path)
    fig = _render_dxf_to_figure(doc, bg=bg, progress_callback=progress_callback)
    try:
        if progress_callback:
            progress_callback(f"TIFF raster görüntüsü oluşturuluyor ({dpi} DPI)...", 85)
        fig.savefig(
            tif_path,
            format="tiff",
            bbox_inches="tight",
            dpi=dpi,
            pil_kwargs={"compression": "tiff_lzw"},
        )
        if progress_callback:
            progress_callback("TIFF başarıyla kaydedildi.", 100)
    finally:
        plt.close(fig)
    return tif_path


def export_ncz_to_pdf(
    ncz_path: str,
    pdf_path: str,
    dpi: int = 300,
    bg: str = "white",
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> str:
    """Export Netcad NCZ directly to vector PDF."""
    if not os.path.exists(ncz_path):
        raise FileNotFoundError(f"NCZ dosyası bulunamadı: {ncz_path}")

    if progress_callback:
        progress_callback("NCZ ikili verileri ayrıştırılıyor...", 15)

    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp:
        temp_dxf = tmp.name

    try:
        convert_ncz_to_dxf(ncz_path, temp_dxf)
        if progress_callback:
            progress_callback("Ara DXF geometrileri oluşturuldu...", 35)
        return export_dxf_to_pdf(temp_dxf, pdf_path, dpi=dpi, bg=bg, progress_callback=progress_callback)
    finally:
        if os.path.exists(temp_dxf):
            try:
                os.remove(temp_dxf)
            except Exception:
                pass


def export_ncz_to_tif(
    ncz_path: str,
    tif_path: str,
    dpi: int = 300,
    bg: str = "white",
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> str:
    """Export Netcad NCZ directly to high-resolution TIFF."""
    if not os.path.exists(ncz_path):
        raise FileNotFoundError(f"NCZ dosyası bulunamadı: {ncz_path}")

    if progress_callback:
        progress_callback("NCZ ikili verileri ayrıştırılıyor...", 15)

    with tempfile.NamedTemporaryFile(suffix=".dxf", delete=False) as tmp:
        temp_dxf = tmp.name

    try:
        convert_ncz_to_dxf(ncz_path, temp_dxf)
        if progress_callback:
            progress_callback("Ara DXF geometrileri oluşturuldu...", 35)
        return export_dxf_to_tif(temp_dxf, tif_path, dpi=dpi, bg=bg, progress_callback=progress_callback)
    finally:
        if os.path.exists(temp_dxf):
            try:
                os.remove(temp_dxf)
            except Exception:
                pass
