"""
ncz_tool.py - All-in-one Netcad NCZ & AutoCAD DXF Swiss Army Knife
Supports:
  1. dxf2ncz:  Convert AutoCAD DXF to Netcad NCZ binary format
  2. ncz2dxf:  Convert Netcad NCZ to AutoCAD DXF format
  3. ncz2pdf:  Export Netcad NCZ directly to high-precision vector PDF
  4. ncz2tif:  Export Netcad NCZ directly to high-resolution TIFF image
  5. dxf2pdf:  Export AutoCAD DXF directly to vector PDF
  6. dxf2tif:  Export AutoCAD DXF directly to high-resolution TIFF image
  7. info:     Inspect NCZ file structure, version, layers, bounding box, entities
  8. reencode: Re-encode an NCZ file for validation and optimization

Usage:
  python ncz_tool.py info 103_11.NCZ
  python ncz_tool.py dxf2ncz drawing.dxf output.NCZ [--template 103_11.NCZ]
  python ncz_tool.py ncz2dxf input.NCZ output.dxf
  python ncz_tool.py ncz2pdf input.NCZ output.pdf
  python ncz_tool.py ncz2tif input.NCZ output.tif
  python ncz_tool.py dxf2pdf drawing.dxf output.pdf
  python ncz_tool.py dxf2tif drawing.dxf output.tif
"""

from __future__ import annotations
import argparse
import os
import sys
from collections import Counter

from ncz_parser import parse_ncz
from ncz_to_dxf import convert_ncz_to_dxf
from dxf_to_ncz import convert_dxf_to_ncz
from cad_export import export_ncz_to_pdf, export_ncz_to_tif, export_dxf_to_pdf, export_dxf_to_tif


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


def cmd_ncz2pdf(args):
    print(f"NCZ -> PDF Dışa Aktarılıyor: '{args.input_ncz}' -> '{args.output_pdf}'")
    export_ncz_to_pdf(args.input_ncz, args.output_pdf, dpi=args.dpi, bg=args.bg)
    print(f"PDF başarıyla oluşturuldu: '{args.output_pdf}' ({os.path.getsize(args.output_pdf)/1024:.1f} KB)")
    return 0


def cmd_ncz2tif(args):
    print(f"NCZ -> TIF Dışa Aktarılıyor: '{args.input_ncz}' -> '{args.output_tif}'")
    export_ncz_to_tif(args.input_ncz, args.output_tif, dpi=args.dpi, bg=args.bg)
    print(f"TIFF başarıyla oluşturuldu: '{args.output_tif}' ({os.path.getsize(args.output_tif)/1024:.1f} KB)")
    return 0


def cmd_dxf2pdf(args):
    print(f"DXF -> PDF Dışa Aktarılıyor: '{args.input_dxf}' -> '{args.output_pdf}'")
    export_dxf_to_pdf(args.input_dxf, args.output_pdf, dpi=args.dpi, bg=args.bg)
    print(f"PDF başarıyla oluşturuldu: '{args.output_pdf}' ({os.path.getsize(args.output_pdf)/1024:.1f} KB)")
    return 0


def cmd_dxf2tif(args):
    print(f"DXF -> TIF Dışa Aktarılıyor: '{args.input_dxf}' -> '{args.output_tif}'")
    export_dxf_to_tif(args.input_dxf, args.output_tif, dpi=args.dpi, bg=args.bg)
    print(f"TIFF başarıyla oluşturuldu: '{args.output_tif}' ({os.path.getsize(args.output_tif)/1024:.1f} KB)")
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
        description="NCZ & DXF Dönüştürücü ve PDF/TIF Dışa Aktarım Aracı"
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

    # ncz2pdf
    p_n2p = subparsers.add_parser("ncz2pdf", help="Netcad NCZ dosyasını vektör PDF olarak dışa aktar")
    p_n2p.add_argument("input_ncz", help="Girdi NCZ dosya yolu")
    p_n2p.add_argument("output_pdf", help="Çıktı PDF dosya yolu")
    p_n2p.add_argument("--dpi", type=int, default=300, help="Çözünürlük DPI (varsayılan: 300)")
    p_n2p.add_argument("--bg", default="white", choices=["white", "black"], help="Arka plan rengi")

    # ncz2tif
    p_n2t = subparsers.add_parser("ncz2tif", help="Netcad NCZ dosyasını yüksek çözünürlüklü TIFF olarak dışa aktar")
    p_n2t.add_argument("input_ncz", help="Girdi NCZ dosya yolu")
    p_n2t.add_argument("output_tif", help="Çıktı TIFF dosya yolu")
    p_n2t.add_argument("--dpi", type=int, default=300, help="Çözünürlük DPI (varsayılan: 300)")
    p_n2t.add_argument("--bg", default="white", choices=["white", "black"], help="Arka plan rengi")

    # dxf2pdf
    p_d2p = subparsers.add_parser("dxf2pdf", help="AutoCAD DXF dosyasını vektör PDF olarak dışa aktar")
    p_d2p.add_argument("input_dxf", help="Girdi DXF dosya yolu")
    p_d2p.add_argument("output_pdf", help="Çıktı PDF dosya yolu")
    p_d2p.add_argument("--dpi", type=int, default=300, help="Çözünürlük DPI (varsayılan: 300)")
    p_d2p.add_argument("--bg", default="white", choices=["white", "black"], help="Arka plan rengi")

    # dxf2tif
    p_d2t = subparsers.add_parser("dxf2tif", help="AutoCAD DXF dosyasını TIFF olarak dışa aktar")
    p_d2t.add_argument("input_dxf", help="Girdi DXF dosya yolu")
    p_d2t.add_argument("output_tif", help="Çıktı TIFF dosya yolu")
    p_d2t.add_argument("--dpi", type=int, default=300, help="Çözünürlük DPI (varsayılan: 300)")
    p_d2t.add_argument("--bg", default="white", choices=["white", "black"], help="Arka plan rengi")

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
    elif args.command == "ncz2pdf":
        sys.exit(cmd_ncz2pdf(args))
    elif args.command == "ncz2tif":
        sys.exit(cmd_ncz2tif(args))
    elif args.command == "dxf2pdf":
        sys.exit(cmd_dxf2pdf(args))
    elif args.command == "dxf2tif":
        sys.exit(cmd_dxf2tif(args))
    elif args.command == "reencode":
        sys.exit(cmd_reencode(args))


if __name__ == "__main__":
    main()
