"""
dxf_to_ncz.py - Convert AutoCAD DXF files to Netcad (NCZ) Binary Format
Copyright (C) 2026.
Uses ezdxf and ncz_writer. Supports full recursive block explosion (INSERT, DIMENSION, etc.)
"""

from __future__ import annotations
import argparse
import math
import os
import re
import sys
from typing import Optional, Callable, Generator, Tuple, Any

try:
    import ezdxf
    from ezdxf import path
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


def iter_flattened_entities(
    entities,
    parent_layer: Optional[str] = None,
    parent_color: Optional[int] = None,
    depth: int = 0,
    max_depth: int = 10,
) -> Generator[Tuple[Any, str, int], None, None]:
    """
    Recursively iterate and explode compound DXF entities (INSERT block references,
    DIMENSION objects, etc.) into world-coordinate primitive entities with proper
    AutoCAD layer and color inheritance.
    """
    for entity in entities:
        etype = entity.dxftype()
        
        # Resolve layer inheritance (entities on layer "0" inherit parent block layer)
        layer = entity.dxf.layer if hasattr(entity.dxf, "layer") else "0"
        if layer == "0" and parent_layer:
            layer = parent_layer

        # Resolve color inheritance (color 0 is BYBLOCK)
        color = entity.dxf.color if hasattr(entity.dxf, "color") else 256
        if color == 0 and parent_color is not None:
            color = parent_color

        # Explode blocks (INSERT) and DIMENSION entities into primitives
        if etype in ("INSERT", "DIMENSION") and depth < max_depth:
            try:
                children = entity.explode()
                yield from iter_flattened_entities(
                    children,
                    parent_layer=layer,
                    parent_color=color,
                    depth=depth + 1,
                    max_depth=max_depth,
                )
                continue
            except Exception:
                # If explode fails (e.g. empty or non-explodable), fall through
                pass

        yield (entity, layer, color)


def convert_dxf_to_ncz(
    dxf_path: str,
    ncz_path: str,
    template_path: Optional[str] = None,
    swap_xy: bool = False,
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> int:
    """
    Convert a DXF drawing into Netcad NCZ binary format, recursively exploding
    all block references (INSERT), dimensions, hatches, and polylines.
    
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
        progress_callback("DXF dosyası ve blok tabloları okunuyor...", 15)

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
        progress_callback("Tabakalar aktarılıyor...", 25)

    # Register all layers from DXF
    for layer in doc.layers:
        writer.add_layer(layer.dxf.name, color_code=layer.dxf.color)

    if progress_callback:
        progress_callback("CAD blokları ve çizim objeleri çözümleniyor...", 35)

    entity_count = 0
    raw_entities = list(msp)

    for entity, layer_name, raw_color in iter_flattened_entities(raw_entities):
        etype = entity.dxftype()
        # 256 = ByLayer in AutoCAD -> pass 0 to let NCZ use layer default color
        col = raw_color if (raw_color is not None and raw_color != 256) else 0

        if etype == "POINT":
            loc = entity.dxf.location
            x, y, z = (loc.y, loc.x, loc.z) if swap_xy else (loc.x, loc.y, loc.z)
            writer.add_point(x, y, z, layer=layer_name, color=col)
            entity_count += 1

        elif etype == "LINE":
            p1 = entity.dxf.start
            p2 = entity.dxf.end
            x1, y1, z1 = (p1.y, p1.x, p1.z) if swap_xy else (p1.x, p1.y, p1.z)
            x2, y2, z2 = (p2.y, p2.x, p2.z) if swap_xy else (p2.x, p2.y, p2.z)
            writer.add_line(x1, y1, x2, y2, z1, z2, layer=layer_name, color=col)
            entity_count += 1

        elif etype == "CIRCLE":
            center = entity.dxf.center
            radius = entity.dxf.radius
            cx, cy, z = (center.y, center.x, center.z) if swap_xy else (center.x, center.y, center.z)
            writer.add_circle(cx, cy, radius, z=z, layer=layer_name, color=col)
            entity_count += 1

        elif etype == "ARC":
            center = entity.dxf.center
            radius = entity.dxf.radius
            cx, cy, z = (center.y, center.x, center.z) if swap_xy else (center.x, center.y, center.z)
            start_angle = math.radians(entity.dxf.start_angle)
            end_angle = math.radians(entity.dxf.end_angle)
            if end_angle < start_angle:
                end_angle += 2 * math.pi
            steps = max(8, int(abs(end_angle - start_angle) / (math.pi / 16)))
            pts = []
            for i in range(steps + 1):
                ang = start_angle + (end_angle - start_angle) * (i / steps)
                pts.append((cx + radius * math.cos(ang), cy + radius * math.sin(ang), z))
            writer.add_polyline(pts, is_closed=False, layer=layer_name, color=col)
            entity_count += 1

        elif etype == "LWPOLYLINE":
            elev = getattr(entity.dxf, "elevation", 0.0)
            is_closed = entity.closed
            if getattr(entity, "has_arc", False):
                try:
                    p_path = path.make_path(entity)
                    pts = [
                        (v.y, v.x, elev) if swap_xy else (v.x, v.y, elev)
                        for v in p_path.flattening(0.5)
                    ]
                except Exception:
                    raw_pts = entity.get_points(format="xy")
                    pts = [(pt[1], pt[0], elev) if swap_xy else (pt[0], pt[1], elev) for pt in raw_pts]
            else:
                raw_pts = entity.get_points(format="xy")
                pts = [(pt[1], pt[0], elev) if swap_xy else (pt[0], pt[1], elev) for pt in raw_pts]

            if is_closed and len(pts) >= 3:
                writer.add_polygon(pts, layer=layer_name, color=col)
            elif len(pts) >= 2:
                writer.add_polyline(pts, is_closed=is_closed, layer=layer_name, color=col)
            entity_count += 1

        elif etype == "POLYLINE":
            is_closed = getattr(entity, "is_closed", False)
            raw_pts = [v.dxf.location for v in entity.vertices]
            pts = [(pt.y, pt.x, pt.z) if swap_xy else (pt.x, pt.y, pt.z) for pt in raw_pts]
            if is_closed and len(pts) >= 3:
                writer.add_polygon(pts, layer=layer_name, color=col)
            elif len(pts) >= 2:
                writer.add_polyline(pts, is_closed=is_closed, layer=layer_name, color=col)
            entity_count += 1

        elif etype == "TEXT":
            ins = entity.dxf.insert
            text = entity.dxf.text or ""
            height = getattr(entity.dxf, "height", 2.0)
            rotation = getattr(entity.dxf, "rotation", 0.0)
            x, y, z = (ins.y, ins.x, ins.z) if swap_xy else (ins.x, ins.y, ins.z)
            writer.add_text(x, y, text, height=height, rotation_deg=rotation, z=z, layer=layer_name, color=col)
            entity_count += 1

        elif etype == "MTEXT":
            ins = entity.dxf.insert
            text = clean_mtext(getattr(entity, "text", ""))
            height = getattr(entity.dxf, "char_height", 2.0)
            rotation = getattr(entity.dxf, "rotation", 0.0)
            x, y, z = (ins.y, ins.x, ins.z) if swap_xy else (ins.x, ins.y, ins.z)
            writer.add_text(x, y, text, height=height, rotation_deg=rotation, z=z, layer=layer_name, color=col)
            entity_count += 1

        elif etype == "HATCH":
            try:
                p_path = path.make_path(entity)
                pts = [
                    (v.y, v.x, 0.0) if swap_xy else (v.x, v.y, 0.0)
                    for v in p_path.flattening(0.5)
                ]
                if len(pts) >= 3:
                    writer.add_polygon(pts, layer=layer_name, color=col)
                    entity_count += 1
                elif len(pts) >= 2:
                    writer.add_polyline(pts, is_closed=False, layer=layer_name, color=col)
                    entity_count += 1
            except Exception:
                pass

        elif etype in ("SOLID", "3DFACE"):
            try:
                p0 = entity.dxf.vtx0
                p1 = entity.dxf.vtx1
                p2 = entity.dxf.vtx2
                p3 = getattr(entity.dxf, "vtx3", p2)
                v0 = (p0.y, p0.x, p0.z) if swap_xy else (p0.x, p0.y, p0.z)
                v1 = (p1.y, p1.x, p1.z) if swap_xy else (p1.x, p1.y, p1.z)
                v2 = (p2.y, p2.x, p2.z) if swap_xy else (p2.x, p2.y, p2.z)
                v3 = (p3.y, p3.x, p3.z) if swap_xy else (p3.x, p3.y, p3.z)
                if p2 == p3:
                    pts = [v0, v1, v2]
                else:
                    pts = [v0, v1, v3, v2]
                writer.add_polygon(pts, layer=layer_name, color=col)
                entity_count += 1
            except Exception:
                pass

        elif etype == "LEADER":
            try:
                raw_pts = getattr(entity, "vertices", [])
                pts = [(v.y, v.x, v.z) if swap_xy else (v.x, v.y, v.z) for v in raw_pts]
                if len(pts) >= 2:
                    writer.add_polyline(pts, is_closed=False, layer=layer_name, color=col)
                    entity_count += 1
            except Exception:
                pass

        elif etype in ("SPLINE", "ELLIPSE"):
            try:
                raw_pts = list(entity.flattening(0.5))
                pts = [(v.y, v.x, v.z) if swap_xy else (v.x, v.y, v.z) for v in raw_pts]
                if len(pts) >= 2:
                    writer.add_polyline(pts, is_closed=False, layer=layer_name, color=col)
                    entity_count += 1
            except Exception:
                pass

        if progress_callback and entity_count % 10000 == 0:
            progress_callback(f"NCZ objeleri derleniyor ({entity_count:,} obje)...", 70)

    if progress_callback:
        progress_callback(f"NCZ ikili dosyası kaydediliyor ({entity_count:,} obje)...", 88)

    file_size = writer.save(ncz_path)

    if progress_callback:
        progress_callback(f"Tamamlandı ({entity_count:,} obje).", 100)

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
