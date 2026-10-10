"""
ncz_to_dxf.py - Convert Netcad (NCZ) Binary files to AutoCAD DXF format
Copyright (C) 2026.
Uses ezdxf and pure Python NCZ parser.
"""

from __future__ import annotations
import argparse
import os
import sys

try:
    import ezdxf
except ImportError:
    print("Error: 'ezdxf' library is required. Install it via 'pip install ezdxf'.")
    sys.exit(1)

from ncz_parser import parse_ncz


def convert_ncz_to_dxf(ncz_path: str, dxf_path: str, dxf_version: str = "R2010") -> int:
    """
    Convert an NCZ drawing into AutoCAD DXF format.
    
    :param ncz_path: Path to input NCZ file.
    :param dxf_path: Path to output DXF file.
    :param dxf_version: DXF standard version (e.g., 'R2010', 'R2018').
    :return: Number of converted entities.
    """
    if not os.path.exists(ncz_path):
        raise FileNotFoundError(f"Input NCZ file not found: {ncz_path}")

    res = parse_ncz(ncz_path)
    doc = ezdxf.new(dxf_version)
    msp = doc.modelspace()

    # Create layers
    for layer_name in res.get("layer_names", []):
        if layer_name and layer_name not in doc.layers:
            doc.layers.add(layer_name)

    entity_count = 0
    for e in res.get("entities", []):
        layer = e.get("layer_name") or "0"
        k = e.get("geometry_kind")
        c = e.get("coordinates", [])

        if k == "Point" and c:
            msp.add_point(
                (c[0]["x"], c[0]["y"], c[0].get("z", 0.0)),
                dxfattribs={"layer": layer},
            )
            entity_count += 1

        elif k == "Line" and len(c) >= 2:
            msp.add_line(
                (c[0]["x"], c[0]["y"], c[0].get("z", 0.0)),
                (c[1]["x"], c[1]["y"], c[1].get("z", 0.0)),
                dxfattribs={"layer": layer},
            )
            entity_count += 1

        elif k in ("Polyline", "Polygon") and len(c) >= 2:
            pts = [(pt["x"], pt["y"]) for pt in c]
            is_closed = e.get("is_closed", False) or (k == "Polygon")
            msp.add_lwpolyline(
                pts,
                close=is_closed,
                dxfattribs={"layer": layer},
            )
            entity_count += 1

        elif k == "Text" and c:
            text_str = e.get("label_text", "")
            height = e.get("text_height", 2.0)
            rotation = e.get("rotation_degrees", 0.0)
            t = msp.add_text(
                text_str,
                dxfattribs={
                    "layer": layer,
                    "height": height,
                    "rotation": rotation,
                },
            )
            t.set_placement((c[0]["x"], c[0]["y"], c[0].get("z", 0.0)))
            entity_count += 1

        elif k == "Circle" and c:
            radius = e.get("radius", 1.0)
            msp.add_circle(
                (c[0]["x"], c[0]["y"], c[0].get("z", 0.0)),
                radius,
                dxfattribs={"layer": layer},
            )
            entity_count += 1

    doc.saveas(dxf_path)
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
