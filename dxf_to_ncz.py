"""
dxf_to_ncz.py - Convert AutoCAD DXF files to Netcad (NCZ) Binary Format
Copyright (C) 2026.
Uses ezdxf and ncz_writer.
"""

from __future__ import annotations
import argparse
import math
import os
import re
import sys
from typing import Optional

try:
    import ezdxf
except ImportError:
    print("Error: 'ezdxf' library is required. Install it via 'pip install ezdxf'.")
    sys.exit(1)

from ncz_writer import NCZWriter


def clean_mtext(raw_text: str) -> str:
    """Strip AutoCAD MText format codes."""
    if not raw_text:
        return ""
    text = re.sub(r"\\[A-Za-z0-9]+;", "", raw_text)
    text = re.sub(r"\\P", " ", text)
    text = re.sub(r"[\{\}]", "", text)
    return text.strip()


from typing import Optional, Callable


def convert_dxf_to_ncz(
    dxf_path: str,
    ncz_path: str,
    template_path: Optional[str] = None,
    swap_xy: bool = False,
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> int:
    """
    Convert a DXF drawing into Netcad NCZ binary format.
    
    :param dxf_path: Path to input DXF file.
    :param ncz_path: Path to output NCZ file.
    :param template_path: Optional template NCZ to inherit projection/styles.
    :param swap_xy: If True, swap X and Y coordinates on import.
    :param progress_callback: Optional callback receiving (step_text, percent).
    :return: Number of converted entities.
    """
    if not os.path.exists(dxf_path):
        raise FileNotFoundError(f"Input DXF file not found: {dxf_path}")

    if progress_callback:
        progress_callback("DXF dosyası okunuyor...", 15)

    # Auto-detect default template if none provided
    if not template_path:
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        local_cand = os.path.join(base_dir, "103_11.NCZ")
        if not os.path.exists(local_cand):
            local_cand = os.path.join(os.path.dirname(dxf_path), "103_11.NCZ")
        if os.path.exists(local_cand):
            template_path = local_cand

    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    writer = NCZWriter(template_path=template_path)

    if progress_callback:
        progress_callback("Tabakalar aktarılıyor...", 30)

    # Register all layers from DXF
    for layer in doc.layers:
        writer.add_layer(layer.dxf.name, color_code=layer.dxf.color)

    if progress_callback:
        progress_callback("CAD objeleri NCZ formatına kodlanıyor...", 60)

    entity_count = 0

    for entity in msp:
        etype = entity.dxftype()
        layer_name = entity.dxf.layer or "0"
        color = entity.dxf.color if hasattr(entity.dxf, "color") else 0

        if etype == "POINT":
            loc = entity.dxf.location
            x, y, z = (loc.y, loc.x, loc.z) if swap_xy else (loc.x, loc.y, loc.z)
            writer.add_point(x, y, z, layer=layer_name, color=color)
            entity_count += 1

        elif etype == "LINE":
            p1 = entity.dxf.start
            p2 = entity.dxf.end
            x1, y1, z1 = (p1.y, p1.x, p1.z) if swap_xy else (p1.x, p1.y, p1.z)
            x2, y2, z2 = (p2.y, p2.x, p2.z) if swap_xy else (p2.x, p2.y, p2.z)
            writer.add_line(x1, y1, x2, y2, z1, z2, layer=layer_name, color=color)
            entity_count += 1

        elif etype == "CIRCLE":
            center = entity.dxf.center
            radius = entity.dxf.radius
            cx, cy, z = (center.y, center.x, center.z) if swap_xy else (center.x, center.y, center.z)
            writer.add_circle(cx, cy, radius, z=z, layer=layer_name, color=color)
            entity_count += 1

        elif etype == "ARC":
            # NCZ represents arcs as circle or segmented polyline
            center = entity.dxf.center
            radius = entity.dxf.radius
            cx, cy, z = (center.y, center.x, center.z) if swap_xy else (center.x, center.y, center.z)
            # Tessellate arc into polyline
            start_angle = math.radians(entity.dxf.start_angle)
            end_angle = math.radians(entity.dxf.end_angle)
            if end_angle < start_angle:
                end_angle += 2 * math.pi
            steps = max(8, int(abs(end_angle - start_angle) / (math.pi / 16)))
            pts = []
            for i in range(steps + 1):
                ang = start_angle + (end_angle - start_angle) * (i / steps)
                pts.append((cx + radius * math.cos(ang), cy + radius * math.sin(ang), z))
            writer.add_polyline(pts, is_closed=False, layer=layer_name, color=color)
            entity_count += 1

        elif etype == "LWPOLYLINE":
            elev = entity.dxf.elevation
            is_closed = entity.closed
            raw_pts = entity.get_points(format="xy")
            pts = []
            for pt in raw_pts:
                px, py = (pt[1], pt[0]) if swap_xy else (pt[0], pt[1])
                pts.append((px, py, elev))
            if is_closed and len(pts) >= 3:
                writer.add_polygon(pts, layer=layer_name, color=color)
            elif len(pts) >= 2:
                writer.add_polyline(pts, is_closed=is_closed, layer=layer_name, color=color)
            entity_count += 1

        elif etype == "POLYLINE":
            is_closed = entity.is_closed
            raw_pts = [v.dxf.location for v in entity.vertices]
            pts = []
            for pt in raw_pts:
                px, py, pz = (pt.y, pt.x, pt.z) if swap_xy else (pt.x, pt.y, pt.z)
                pts.append((px, py, pz))
            if is_closed and len(pts) >= 3:
                writer.add_polygon(pts, layer=layer_name, color=color)
            elif len(pts) >= 2:
                writer.add_polyline(pts, is_closed=is_closed, layer=layer_name, color=color)
            entity_count += 1

        elif etype == "TEXT":
            ins = entity.dxf.insert
            text = entity.dxf.text or ""
            height = entity.dxf.height if hasattr(entity.dxf, "height") else 2.0
            rotation = entity.dxf.rotation if hasattr(entity.dxf, "rotation") else 0.0
            x, y, z = (ins.y, ins.x, ins.z) if swap_xy else (ins.x, ins.y, ins.z)
            writer.add_text(x, y, text, height=height, rotation_deg=rotation, z=z, layer=layer_name, color=color)
            entity_count += 1

        elif etype == "MTEXT":
            ins = entity.dxf.insert
            text = clean_mtext(entity.text)
            height = entity.dxf.char_height if hasattr(entity.dxf, "char_height") else 2.0
            rotation = entity.dxf.rotation if hasattr(entity.dxf, "rotation") else 0.0
            x, y, z = (ins.y, ins.x, ins.z) if swap_xy else (ins.x, ins.y, ins.z)
            writer.add_text(x, y, text, height=height, rotation_deg=rotation, z=z, layer=layer_name, color=color)
            entity_count += 1

    if progress_callback:
        progress_callback("NCZ ikili dosyası derlenip kaydediliyor...", 90)
    file_size = writer.save(ncz_path)
    if progress_callback:
        progress_callback(f"Tamamlandı ({entity_count} obje).", 100)
    return entity_count


def main():
    parser = argparse.ArgumentParser(description="Convert DXF files to Netcad NCZ binary files.")
    parser.add_argument("input_dxf", help="Path to input DXF file")
    parser.add_argument("output_ncz", help="Path to output NCZ file")
    parser.add_argument("--template", "-t", default=None, help="Template NCZ file to inherit header/projections")
    parser.add_argument("--swap-xy", action="store_true", help="Swap X and Y coordinates")

    args = parser.parse_args()
    print(f"Converting '{args.input_dxf}' -> '{args.output_ncz}'...")
    cnt = convert_dxf_to_ncz(args.input_dxf, args.output_ncz, template_path=args.template, swap_xy=args.swap_xy)
    print(f"Successfully converted {cnt} entities into '{args.output_ncz}'.")


if __name__ == "__main__":
    main()
