"""
Windows'ta gerçek WM_DROPFILES mesajı göndererek sürükle-bırakı uçtan uca test eder.
(Windows dışında atlanır; GitHub Actions'ta windows-latest üzerinde çalışır.)
"""
import shutil
import sys
import time

import pytest

from conftest import SAMPLE_DXF, SAMPLE_NCZ

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Yalnızca Windows")


def _post_drop(hwnd, paths):
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL

    header = 20  # DROPFILES: pFiles, pt.x, pt.y, fNC, fWide
    data = ("\0".join(paths) + "\0\0").encode("utf-16-le")
    hmem = kernel32.GlobalAlloc(0x0042, header + len(data))  # GHND
    ptr = kernel32.GlobalLock(hmem)
    ctypes.memmove(ptr, (ctypes.c_uint32 * 5)(header, 0, 0, 0, 1), header)
    ctypes.memmove(ptr + header, data, len(data))
    kernel32.GlobalUnlock(hmem)
    assert user32.PostMessageW(hwnd, 0x0233, hmem, 0)


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["nczforge.py"])  # pytest argümanları (ör. "tests" klasörü) bırakılmış dosya sanılmasın
    import tkinter as tk
    from tkinter import messagebox
    import dxftoncz_gui as g

    shown = []
    monkeypatch.setattr(messagebox, "showwarning", lambda *a, **k: shown.append(a))
    monkeypatch.setattr(messagebox, "showerror", lambda *a, **k: shown.append(a))
    root = tk.Tk()
    a = g.DxfNczConverterApp(root)
    a._shown = shown
    root.update()
    yield a
    root.destroy()


def _pump(app, cond, timeout=10):
    end = time.time() + timeout
    while time.time() < end and not cond():
        app.root.update()
        time.sleep(0.02)


@pytest.mark.parametrize("count", [1, 5, 6, 12, 40])
def test_drop_many_files(app, tmp_path, count):
    assert app._drop_target is not None, "sürükle-bırak kurulamadı"
    # uzun yol (260 karakter sınırını aşan) da içeren dosyalar
    deep = tmp_path / ("uzun_klasor_adi_" * 6) / ("alt_klasor_" * 6)
    try:
        deep.mkdir(parents=True)
        shutil.copy(SAMPLE_DXF, deep / "deneme.dxf")
    except OSError:  # Windows'ta uzun yol desteği kapalıysa normal klasör kullan
        deep = tmp_path
    paths = []
    for i in range(count):
        src, ext = (SAMPLE_NCZ, ".NCZ") if i % 3 else (SAMPLE_DXF, ".dxf")
        target = (deep if i == 0 else tmp_path) / f"pafta_{i}{ext}"
        shutil.copy(src, target)
        paths.append(str(target))

    _post_drop(app.root.winfo_id(), paths)
    if count == 1:
        _pump(app, lambda: bool(app.d2n_dxf_var.get()))
    else:
        _pump(app, lambda: len(app.batch_files) == count)

    assert app._drop_target.errors == []
    assert app._shown == []
    if count == 1:
        assert app.d2n_dxf_var.get() == paths[0]  # tek DXF -> DXF➔NCZ sayfası
    else:
        assert app.current_page == "batch"
        assert len(app.batch_files) == count
        assert paths[0] in app.batch_files  # (varsa) 260+ karakterlik yol kesilmeden alındı


def test_drop_then_parallel_batch(app, tmp_path):
    paths = []
    for i in range(7):
        t = tmp_path / f"p{i}.NCZ"
        shutil.copy(SAMPLE_NCZ, t)
        paths.append(str(t))
    _post_drop(app.root.winfo_id(), paths)
    _pump(app, lambda: len(app.batch_files) == 7)
    assert len(app.batch_files) == 7

    app.batch_outdir_var.set(str(tmp_path / "out"))
    app.batch_parallel_var.set(True)
    app.start_batch()
    _pump(app, lambda: str(app.btn_batch_start["state"]) == "normal", timeout=240)
    assert "7 başarılı" in app.ui["batch"]["status"].cget("text"), app.ui["batch"]["status"].cget("text")
    assert len(list((tmp_path / "out").iterdir())) == 7
