import os
import shutil

from conftest import SAMPLE_DXF, SAMPLE_NCZ
from batch_convert import batch_convert, collect_files, output_path_for


def _setup(tmp_path):
    src = tmp_path / "in"
    (src / "alt").mkdir(parents=True)
    shutil.copy(SAMPLE_NCZ, src / "103_11.NCZ")
    shutil.copy(SAMPLE_DXF, src / "103_11.dxf")
    shutil.copy(SAMPLE_NCZ, src / "alt" / "diger.ncz")
    (src / "notlar.txt").write_text("x")
    (src / "bozuk.dxf").write_text("bozuk")
    return src


def test_collect_files(tmp_path):
    src = _setup(tmp_path)
    assert len(collect_files([str(src)])) == 3
    assert len(collect_files([str(src)], recursive=True)) == 4
    # tekrar eden yollar tek sayılır
    assert len(collect_files([str(src / "103_11.NCZ"), str(src / "103_11.NCZ")])) == 1


def test_output_path():
    assert output_path_for("/a/b.NCZ", "auto").endswith(os.path.join("a", "b.dxf"))
    assert output_path_for("/a/b.dxf", "auto").endswith("b.NCZ")
    assert output_path_for("/a/b.dxf", "pdf", "/out") == os.path.join("/out", "b.pdf")


def test_batch_in_place_never_overwrites_sources(tmp_path):
    src = _setup(tmp_path)
    before = (src / "103_11.NCZ").read_bytes()
    files = collect_files([str(src)])
    summary = batch_convert(files)
    assert len(summary.succeeded) == 2 and len(summary.failed) == 1  # bozuk.dxf
    assert (src / "103_11.NCZ").read_bytes() == before
    names = sorted(os.listdir(src))
    assert "103_11_2.NCZ" in names and "103_11_2.dxf" in names


def test_batch_parallel_pdf_unique_names(tmp_path):
    src = _setup(tmp_path)
    out = tmp_path / "pdf"
    files = [str(src / "103_11.NCZ"), str(src / "103_11.dxf")]
    summary = batch_convert(files, target="pdf", output_dir=str(out), workers=2)
    assert [r.ok for r in summary.results] == [True, True]
    assert sorted(os.listdir(out)) == ["103_11.pdf", "103_11_2.pdf"]
    assert summary.results[0].input_path == files[0]  # girdi sırası korunur


def test_batch_stop_flag(tmp_path):
    src = _setup(tmp_path)
    files = collect_files([str(src)])
    summary = batch_convert(files, stop_flag=lambda: True)
    assert summary.results == []
