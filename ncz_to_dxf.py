"""
ncz_to_dxf.py - Convert Netcad (NCZ) Binary files to AutoCAD DXF format
Copyright (C) 2026.
Uses ezdxf and pure Python NCZ parser.

Aktarılanlar:
  * Point, Line, Polyline, Polygon, Triangle, MapSheet, SmartObject (çoklu çizgi olarak)
  * Text, Circle, Arc
  * Symbol ve Block referansları (DXF blok + INSERT olarak)
  * Tabaka renkleri ve nesne renkleri (true color; siyah/beyaz -> ACI 7, arka plana uyumlu)
"""

from __future__ import annotations
import argparse
import math
import os
import re
import sys
from typing import Callable, Optional

try:
    import ezdxf
    from ezdxf import colors as ezcolors
except ImportError:
    print("Error: 'ezdxf' library is required. Install it via 'pip install ezdxf'.")
    sys.exit(1)

from ncz_parser import parse_ncz

# Çoklu çizgi olarak aktarılan geometri türleri
POLY_KINDS = ("Polyline", "Polygon", "Triangle", "MapSheet", "SmartObject")
# Her zaman kapalı kabul edilen türler
CLOSED_KINDS = ("Polygon", "Triangle", "MapSheet", "SmartObject")

_INVALID_NAME_CHARS = re.compile(r'[<>/\\":;?*|=`,]')


def _rgb(argb: Optional[int]):
    if argb is None:
        return None
    return (argb >> 16) & 255, (argb >> 8) & 255, argb & 255


def _is_black_or_white(rgb) -> bool:
    return rgb in ((0, 0, 0), (255, 255, 255))


def _color_attribs(argb: Optional[int], layer_argb: Optional[int]) -> dict:
    """
    Nesne rengi tabaka rengiyle aynıysa BYLAYER bırakılır.
    Siyah/beyaz -> ACI 7 (beyaz arka planda siyah, siyah arka planda beyaz görünür).
    Diğer renkler -> 24-bit true color.
    """
    rgb = _rgb(argb)
    if rgb is None or (layer_argb is not None and _rgb(layer_argb) == rgb):
        return {}
    if _is_black_or_white(rgb):
        return {"color": 7}
    return {"true_color": ezcolors.rgb2int(rgb)}


def _layer_color_attribs(argb: Optional[int]) -> dict:
    rgb = _rgb(argb)
    if rgb is None or _is_black_or_white(rgb):
        return {"color": 7}
    return {"color": 7, "true_color": ezcolors.rgb2int(rgb)}


def _safe_block_name(name: str) -> str:
    name = _INVALID_NAME_CHARS.sub("_", (name or "").strip())
    return name or "BLOK"


def _arc_angles_degrees(start: float, end: float):
    """
    NCZ yay açıları radyan olarak saklanır (metin açılarıyla aynı birim).
    Değerler 2π'yi belirgin şekilde aşıyorsa grad (400) kabul edilir.
    """
    if not (math.isfinite(start) and math.isfinite(end)):
        return 0.0, 360.0
    limit = 2 * math.pi + 1e-6
    if abs(start) <= limit and abs(end) <= limit:
        return math.degrees(start) % 360.0, math.degrees(end) % 360.0
    return (start * 0.9) % 360.0, (end * 0.9) % 360.0


def _ensure_symbol_block(doc, code: str) -> str:
    """Netcad sembol kütüphanesi NCZ içinde olmadığından birim boyutlu bir yer tutucu blok oluşturur."""
    name = _safe_block_name(f"NCZ_SEMBOL_{code}")
    if name not in doc.blocks:
        blk = doc.blocks.new(name=name)
        blk.add_circle((0, 0), 0.5)
        blk.add_line((-0.5, 0), (0.5, 0))
        blk.add_line((0, -0.5), (0, 0.5))
    return name


def _ensure_reference_block(doc, label: str) -> str:
    """NCZ blok referansları için (blok tanımı NCZ'de çözülemediğinden) işaretli yer tutucu blok."""
    name = _safe_block_name(f"NCZ_BLOK_{label}" if label else "NCZ_BLOK")
    if name not in doc.blocks:
        blk = doc.blocks.new(name=name)
        blk.add_point((0, 0))
        blk.add_line((-0.5, -0.5), (0.5, 0.5))
        blk.add_line((-0.5, 0.5), (0.5, -0.5))
    return name


def convert_ncz_to_dxf(
    ncz_path: str,
    dxf_path: str,
    dxf_version: str = "R2010",
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> int:
    """
    Convert an NCZ drawing into AutoCAD DXF format.

    :param ncz_path: Path to input NCZ file.
    :param dxf_path: Path to output DXF file.
    :param dxf_version: DXF standard version (e.g., 'R2010', 'R2018').
    :param progress_callback: Optional callback receiving (step_text, percent).
    :return: Number of converted entities.
    """
    if not os.path.exists(ncz_path):
        raise FileNotFoundError(f"Input NCZ file not found: {ncz_path}")

    if progress_callback:
        progress_callback("NCZ ikili formatı okunuyor...", 20)

    res = parse_ncz(ncz_path)
    doc = ezdxf.new(dxf_version)
    msp = doc.modelspace()

    # Tabakalar ve renkleri
    layer_argb = {}
    names = res.get("layer_names", [])
    colors = res.get("layer_colors", [])
    for idx, layer_name in enumerate(names):
        if not layer_name:
            continue
        argb = colors[idx] if idx < len(colors) else None
        if argb is not None:
            # parser ile aynı normalizasyon: neredeyse siyah -> siyah
            r, g, b = _rgb(argb)
            if r == 0 and g == 0 and b <= 1:
                argb = 0xFF000000
        layer_argb.setdefault(layer_name, argb)
        if layer_name not in doc.layers:
            doc.layers.add(layer_name, **_layer_color_attribs(argb))

    if progress_callback:
        progress_callback("Objeler DXF'e aktarılıyor...", 60)

    entity_count = 0
    for e in res.get("entities", []):
        layer = e.get("layer_name") or "0"
        if layer not in doc.layers:
            doc.layers.add(layer)
        k = e.get("geometry_kind")
        c = e.get("coordinates", [])
        attribs = {"layer": layer}
        attribs.update(_color_attribs(e.get("color_argb"), layer_argb.get(layer)))

        if not c:
            continue
        p0 = (c[0]["x"], c[0]["y"], c[0].get("z", 0.0))

        if k == "Point":
            msp.add_point(p0, dxfattribs=attribs)

        elif k == "Line" and len(c) >= 2:
            msp.add_line(p0, (c[1]["x"], c[1]["y"], c[1].get("z", 0.0)), dxfattribs=attribs)

        elif k in POLY_KINDS and len(c) >= 2:
            pts = [(pt["x"], pt["y"]) for pt in c]
            is_closed = e.get("is_closed", False) or k in CLOSED_KINDS
            if is_closed and len(pts) > 2 and pts[0] == pts[-1]:
                pts = pts[:-1]
            msp.add_lwpolyline(pts, close=is_closed, dxfattribs=attribs)
            label = e.get("label_text") or ""
            if k == "MapSheet" and label:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                h = max((max(ys) - min(ys)) / 40.0, 0.5)
                msp.add_text(label, dxfattribs={**attribs, "height": h}).set_placement(
                    (min(xs) + h, max(ys) - 2 * h)
                )

        elif k == "Text":
            text_str = e.get("label_text", "")
            if not text_str:
                continue
            t = msp.add_text(
                text_str,
                dxfattribs={
                    **attribs,
                    "height": e.get("text_height") or 2.0,
                    "rotation": e.get("rotation_degrees", 0.0),
                },
            )
            t.set_placement(p0)

        elif k == "Circle":
            radius = e.get("radius") or 1.0
            msp.add_circle(p0, radius, dxfattribs=attribs)

        elif k == "Arc":
            radius = e.get("radius") or 0.0
            if not (math.isfinite(radius) and radius > 0):
                continue
            start, end = _arc_angles_degrees(e.get("start_angle", 0.0), e.get("end_angle", 0.0))
            if abs(start - end) < 1e-9:
                msp.add_circle(p0, radius, dxfattribs=attribs)
            else:
                msp.add_arc(p0, radius, start, end, dxfattribs=attribs)

        elif k == "Symbol":
            code = (e.get("label_text") or "S0").lstrip("S") or "0"
            size = e.get("text_height") or 1.0
            name = _ensure_symbol_block(doc, code)
            msp.add_blockref(
                name,
                p0,
                dxfattribs={
                    **attribs,
                    "xscale": size,
                    "yscale": size,
                    "rotation": e.get("rotation_degrees", 0.0),
                },
            )

        elif k == "Block":
            name = _ensure_reference_block(doc, e.get("label_text", ""))
            msp.add_blockref(name, p0, dxfattribs={**attribs, "rotation": e.get("rotation_degrees", 0.0)})

        else:
            continue
        entity_count += 1

    if progress_callback:
        progress_callback("DXF dosyası kaydediliyor...", 95)
    doc.saveas(dxf_path)
    if progress_callback:
        progress_callback(f"Tamamlandı ({entity_count} obje).", 100)
    return entity_count


def main():
    parser = argparse.ArgumentParser(description="Convert Netcad NCZ files to AutoCAD DXF format.")
    parser.add_argument("input_ncz", help="Path to input NCZ file")
    parser.add_argument("output_dxf", help="Path to output DXF file")
    parser.add_argument("--dxf-version", default="R2010", help="AutoCAD DXF version (default: R2010)")

    args = parser.parse_args()
    print(f"Converting '{args.input_ncz}' -> '{args.output_dxf}'...")
    cnt = convert_ncz_to_dxf(args.input_ncz, args.output_dxf, dxf_version=args.dxf_version)
    print(f"Successfully converted {cnt} entities into '{args.output_dxf}'.")


if __name__ == "__main__":
    main()
