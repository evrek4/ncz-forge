"""
batch_convert.py - Çoklu (toplu) NCZ / DXF dönüştürme
Birden fazla NCZ ve DXF dosyasını tek seferde dönüştürür:
  * NCZ -> DXF, DXF -> NCZ (uzantıya göre otomatik yön)
  * NCZ/DXF -> PDF veya TIF
Klasör verilirse içindeki .ncz / .dxf dosyaları (isteğe bağlı alt klasörlerle) toplanır.
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Optional

SUPPORTED_EXTS = (".ncz", ".dxf")

# Hedef türleri
TARGET_AUTO = "auto"  # NCZ -> DXF, DXF -> NCZ
TARGET_PDF = "pdf"
TARGET_TIF = "tif"
TARGETS = (TARGET_AUTO, TARGET_PDF, TARGET_TIF)


@dataclass
class BatchResult:
    input_path: str
    output_path: str
    ok: bool
    entity_count: int = 0
    error: str = ""


@dataclass
class BatchSummary:
    results: List[BatchResult] = field(default_factory=list)

    @property
    def succeeded(self) -> List[BatchResult]:
        return [r for r in self.results if r.ok]

    @property
    def failed(self) -> List[BatchResult]:
        return [r for r in self.results if not r.ok]


def collect_files(paths: Iterable[str], recursive: bool = False) -> List[str]:
    """Verilen dosya/klasör yollarından desteklenen dosyaları (tekrarsız, sıralı) toplar."""
    found: List[str] = []
    seen = set()

    def _add(p: str):
        ap = os.path.abspath(p)
        key = os.path.normcase(ap)
        if key not in seen and os.path.splitext(ap)[1].lower() in SUPPORTED_EXTS:
            seen.add(key)
            found.append(ap)

    for p in paths:
        if os.path.isdir(p):
            if recursive:
                for root, _dirs, files in os.walk(p):
                    for name in sorted(files):
                        _add(os.path.join(root, name))
            else:
                for name in sorted(os.listdir(p)):
                    full = os.path.join(p, name)
                    if os.path.isfile(full):
                        _add(full)
        elif os.path.isfile(p):
            _add(p)
    return found


def output_path_for(input_path: str, target: str, output_dir: Optional[str] = None) -> str:
    base = os.path.splitext(os.path.basename(input_path))[0]
    ext = os.path.splitext(input_path)[1].lower()
    if target == TARGET_AUTO:
        out_ext = ".dxf" if ext == ".ncz" else ".NCZ"
    else:
        out_ext = "." + target
    folder = output_dir or os.path.dirname(os.path.abspath(input_path))
    return os.path.join(folder, base + out_ext)


def _unique_path(path: str, reserved: set) -> str:
    """Girdi dosyalarının ve bu turda üretilen çıktıların üzerine yazmamak için _2, _3 ekler."""
    if os.path.normcase(os.path.abspath(path)) not in reserved:
        return path
    stem, ext = os.path.splitext(path)
    n = 2
    while os.path.normcase(os.path.abspath(f"{stem}_{n}{ext}")) in reserved:
        n += 1
    return f"{stem}_{n}{ext}"


def convert_one(
    input_path: str,
    target: str = TARGET_AUTO,
    output_dir: Optional[str] = None,
    template_path: Optional[str] = None,
    swap_xy: bool = False,
    dxf_version: str = "R2010",
    dpi: int = 300,
    bg: str = "white",
    out_path: Optional[str] = None,
) -> BatchResult:
    out_path = out_path or output_path_for(input_path, target, output_dir)
    ext = os.path.splitext(input_path)[1].lower()
    try:
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        count = 0
        if target == TARGET_AUTO:
            if ext == ".ncz":
                from ncz_to_dxf import convert_ncz_to_dxf
                count = convert_ncz_to_dxf(input_path, out_path, dxf_version=dxf_version)
            else:
                from dxf_to_ncz import convert_dxf_to_ncz
                count = convert_dxf_to_ncz(input_path, out_path, template_path=template_path, swap_xy=swap_xy)
        elif target in (TARGET_PDF, TARGET_TIF):
            import cad_export
            fn_name = f"export_{ext[1:]}_to_{target}"
            getattr(cad_export, fn_name)(input_path, out_path, dpi=dpi, bg=bg)
        else:
            raise ValueError(f"Bilinmeyen hedef format: {target}")
        return BatchResult(input_path, out_path, True, entity_count=count or 0)
    except Exception as ex:  # noqa: BLE001 - her dosyanın hatası ayrı raporlanır
        return BatchResult(input_path, out_path, False, error=str(ex) or ex.__class__.__name__)


def batch_convert(
    files: List[str],
    target: str = TARGET_AUTO,
    output_dir: Optional[str] = None,
    template_path: Optional[str] = None,
    swap_xy: bool = False,
    dxf_version: str = "R2010",
    dpi: int = 300,
    bg: str = "white",
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    stop_flag: Optional[Callable[[], bool]] = None,
) -> BatchSummary:
    """
    Dosyaları sırayla dönüştürür. Bir dosyadaki hata diğerlerini durdurmaz.
    progress_callback(index, total, file_path): her dosya başlamadan önce çağrılır.
    stop_flag(): True dönerse kalan dosyalar atlanır.
    """
    summary = BatchSummary()
    total = len(files)
    reserved = {os.path.normcase(os.path.abspath(f)) for f in files}
    for i, f in enumerate(files):
        if stop_flag and stop_flag():
            break
        if progress_callback:
            progress_callback(i, total, f)
        out_path = _unique_path(output_path_for(f, target, output_dir), reserved)
        reserved.add(os.path.normcase(os.path.abspath(out_path)))
        summary.results.append(
            convert_one(f, target, output_dir, template_path, swap_xy, dxf_version, dpi, bg, out_path)
        )
    if progress_callback:
        progress_callback(total, total, "")
    return summary
