import math
import shutil
from collections import Counter

import ezdxf
import pytest

from conftest import SAMPLE_DXF, SAMPLE_NCZ
from ncz_parser import parse_ncz
from ncz_to_dxf import convert_ncz_to_dxf, _arc_angles_degrees, _color_attribs
from dxf_to_ncz import convert_dxf_to_ncz


def test_parse_sample():
    res = parse_ncz(SAMPLE_NCZ)
    kinds = Counter(e["geometry_kind"] for e in res["entities"])
    assert kinds["Line"] > 400
    assert kinds["Text"] > 200
    assert len(res["layer_names"]) == len(res["layer_colors"]) > 0


def test_ncz_to_dxf_keeps_all_supported_entities(tmp_path):
    out = tmp_path / "out.dxf"
    count = convert_ncz_to_dxf(SAMPLE_NCZ, str(out))
    src = parse_ncz(SAMPLE_NCZ)["entities"]
    assert count == len(src)  # hiçbir nesne atlanmamalı
    types = Counter(e.dxftype() for e in ezdxf.readfile(str(out)).modelspace())
    assert types["INSERT"] == sum(1 for e in src if e["geometry_kind"] == "Symbol")


def test_ncz_to_dxf_layer_colors(tmp_path):
    out = tmp_path / "out.dxf"
    convert_ncz_to_dxf(SAMPLE_NCZ, str(out))
    doc = ezdxf.readfile(str(out))
    res = parse_ncz(SAMPLE_NCZ)
    # 'NOKTA' tabakası kırmızı (0xffff0000)
    idx = res["layer_names"].index("NOKTA")
    assert res["layer_colors"][idx] & 0xFFFFFF == 0xFF0000
    assert doc.layers.get("NOKTA").rgb == (255, 0, 0)


def test_color_attribs():
    assert _color_attribs(0xFFFF0000, 0xFFFF0000) == {}  # tabaka ile aynı -> BYLAYER
    assert _color_attribs(0xFF000000, 0xFFFF0000) == {"color": 7}
    assert _color_attribs(0xFFFFFFFF, None) == {"color": 7}
    assert "true_color" in _color_attribs(0xFF00815C, 0xFFFF0000)


def test_arc_angles():
    assert _arc_angles_degrees(0.0, math.pi / 2) == pytest.approx((0.0, 90.0))
    assert _arc_angles_degrees(0.0, 100.0) == pytest.approx((0.0, 90.0))  # grad


def test_dxf_to_ncz_roundtrip(tmp_path):
    ncz = tmp_path / "out.NCZ"
    count = convert_dxf_to_ncz(SAMPLE_DXF, str(ncz), template_path=SAMPLE_NCZ)
    assert count > 0
    parsed = parse_ncz(str(ncz))["entities"]
    assert len(parsed) >= count * 0.9


def test_ncz_dxf_ncz_roundtrip_keeps_geometry(tmp_path):
    dxf = tmp_path / "a.dxf"
    ncz = tmp_path / "b.NCZ"
    convert_ncz_to_dxf(SAMPLE_NCZ, str(dxf))
    convert_dxf_to_ncz(str(dxf), str(ncz), template_path=SAMPLE_NCZ)
    a = Counter(e["geometry_kind"] for e in parse_ncz(SAMPLE_NCZ)["entities"])
    b = Counter(e["geometry_kind"] for e in parse_ncz(str(ncz))["entities"])
    assert b["Line"] == a["Line"]
    assert b["Text"] == a["Text"]
    assert b["Circle"] == a["Circle"]
    # semboller ekleme noktası olarak (nokta) geri gelir
    assert b["Point"] == a["Point"] + a["Symbol"]
