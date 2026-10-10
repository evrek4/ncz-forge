"""
ncz_tool.py - All-in-one Netcad NCZ Swiss Army Knife
Supports:
  1. dxf2ncz: Convert AutoCAD DXF to Netcad NCZ binary format
  2. ncz2dxf: Convert Netcad NCZ to AutoCAD DXF format
  3. info:    Inspect NCZ file structure, version, layers, bounding box, entities
  4. reencode: Re-encode an NCZ file for validation and optimization

Usage:
  python ncz_tool.py info 103_11.NCZ
  python ncz_tool.py dxf2ncz drawing.dxf output.NCZ [--template 103_11.NCZ]
  python ncz_tool.py ncz2dxf input.NCZ output.dxf
  python ncz_tool.py reencode input.NCZ output.NCZ
"""

from __future__ import annotations
import argparse
import os
import sys
from collections import Counter

from ncz_parser import parse_ncz
from ncz_to_dxf import convert_ncz_to_dxf
from dxf_to_ncz import convert_dxf_to_ncz


def cmd_info(args):
    path = args.input_file
    if not os.path.exists(path):
        print(f"Hata: Dosya bulunamadı -> {path}")
        return 1

    print(f"\n{'='*60}")
    print(f"NCZ DOSYA ANALİZİ: {os.path.basename(path)}")
    print(f"{'='*60}")
    size = os.path.getsize(path)
    print(f"Dosya Boyutu     : {size:,} bayt ({size/1024:.1f} KB)")

    res = parse_ncz(path)
    print(f"Netcad Sürümü    : {res.get('version_name', 'Bilinmiyor')}")
    print(f"Projeksiyon/Datum: {res.get('projection_text', 'Bilinmiyor')} (EPSG: {res.get('epsg', '-')})")

    layers = res.get("layer_names", [])
    print(f"Toplam Tabaka (Layer): {len(layers)}")
    if layers:
        sample_layers = layers[:15]
        print(f"  Tabakalar: {', '.join(sample_layers)}{' ...' if len(layers) > 15 else ''}")

    entities = res.get("entities", [])
    print(f"\nToplam Obje/Geometri : {len(entities)}")
    counts = Counter(e["geometry_kind"] for e in entities)
    for kind, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  - {kind:<15}: {cnt:5d} adet")

    # Bounding box
    coords_x = []
    coords_y = []
    for e in entities:
        for c in e.get("coordinates", []):
            coords_x.append(c["x"])
            coords_y.append(c["y"])

    if coords_x and coords_y:
        print(f"\nSınırlar (CAD Koordinatları - Easting/Northing):")
        print(f"  X (Sağa/Easting)   : {min(coords_x):.3f} -> {max(coords_x):.3f}")
        print(f"  Y (Yukarı/Northing): {min(coords_y):.3f} -> {max(coords_y):.3f}")
    print(f"{'='*60}\n")
    return 0


def cmd_dxf2ncz(args):
    print(f"DXF -> NCZ Dönüştürülüyor: '{args.input_dxf}' -> '{args.output_ncz}'")
    count = convert_dxf_to_ncz(
        args.input_dxf,
        args.output_ncz,
        template_path=args.template,
        swap_xy=args.swap_xy,
    )
    print(f"Dönüştürme tamamlandı! {count} adet obje '{args.output_ncz}' dosyasına yazıldı.")
    return 0


def cmd_ncz2dxf(args):
    print(f"NCZ -> DXF Dönüştürülüyor: '{args.input_ncz}' -> '{args.output_dxf}'")
    count = convert_ncz_to_dxf(args.input_ncz, args.output_dxf, dxf_version=args.version)
    print(f"Dönüştürme tamamlandı! {count} adet obje '{args.output_dxf}' dosyasına aktarıldı.")
    return 0


def cmd_reencode(args):
    print(f"NCZ Re-encode ediliyor: '{args.input_ncz}' -> '{args.output_ncz}'")
    temp_dxf = args.output_ncz + ".tmp.dxf"
    try:
        cnt1 = convert_ncz_to_dxf(args.input_ncz, temp_dxf)
        cnt2 = convert_dxf_to_ncz(temp_dxf, args.output_ncz, template_path=args.input_ncz)
        print(f"Re-encode başarıyla tamamlandı! {cnt2} obje yazıldı.")
    finally:
        if os.path.exists(temp_dxf):
            os.remove(temp_dxf)
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="NCZ & DXF İki Yönlü Dönüştürücü ve NCZ Encoder Aracı"
    )
    subparsers = parser.add_subparsers(dest="command", help="Komutlar")

    # info
    p_info = subparsers.add_parser("info", help="NCZ dosya detaylarını ve istatistiklerini görüntüle")
    p_info.add_argument("input_file", help="İncelenecek NCZ dosyası")

    # dxf2ncz
    p_d2n = subparsers.add_parser("dxf2ncz", help="AutoCAD DXF dosyasını Netcad NCZ formatına dönüştür")
    p_d2n.add_argument("input_dxf", help="Girdi DXF dosya yolu")
    p_d2n.add_argument("output_ncz", help="Çıktı NCZ dosya yolu")
    p_d2n.add_argument("--template", "-t", default=None, help="Projeksiyon/şablon alınacak NCZ dosyası")
    p_d2n.add_argument("--swap-xy", action="store_true", help="X ve Y koordinatlarını yer değiştir")

    # ncz2dxf
    p_n2d = subparsers.add_parser("ncz2dxf", help="Netcad NCZ dosyasını AutoCAD DXF formatına dönüştür")
    p_n2d.add_argument("input_ncz", help="Girdi NCZ dosya yolu")
    p_n2d.add_argument("output_dxf", help="Çıktı DXF dosya yolu")
    p_n2d.add_argument("--version", default="R2010", help="AutoCAD DXF versiyonu (varsayılan: R2010)")

    # reencode
    p_re = subparsers.add_parser("reencode", help="Bir NCZ dosyasını parse edip yeniden encode et")
    p_re.add_argument("input_ncz", help="Girdi NCZ dosyası")
    p_re.add_argument("output_ncz", help="Çıktı NCZ dosyası")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "info":
        sys.exit(cmd_info(args))
    elif args.command == "dxf2ncz":
        sys.exit(cmd_dxf2ncz(args))
    elif args.command == "ncz2dxf":
        sys.exit(cmd_ncz2dxf(args))
    elif args.command == "reencode":
        sys.exit(cmd_reencode(args))


if __name__ == "__main__":
    main()
