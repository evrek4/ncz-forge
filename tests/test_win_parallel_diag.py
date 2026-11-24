"""
Windows'ta paralel toplu dönüştürmenin hangi koşulda takıldığını bulmak için tanı testleri.
Takılırsa 90 sn sonra tüm iş parçacıklarının yığın izi yazdırılır.
"""
import faulthandler
import shutil
import sys
import threading
import time

import pytest

from conftest import SAMPLE_NCZ

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Yalnızca Windows")


def _files(tmp_path, n=4):
    out = []
    for i in range(n):
        t = tmp_path / f"d{i}.NCZ"
        shutil.copy(SAMPLE_NCZ, t)
        out.append(str(t))
    return out


def _run_in_thread(files, outdir, pump=None, timeout=90):
    from batch_convert import batch_convert

    box = {}

    def work():
        box["s"] = batch_convert(files, output_dir=outdir, workers=3)

    faulthandler.dump_traceback_later(timeout, exit=False)
    try:
        t = threading.Thread(target=work, daemon=True)
        t.start()
        end = time.time() + timeout + 5
        while t.is_alive() and time.time() < end:
            if pump:
                pump()
            time.sleep(0.02)
    finally:
        faulthandler.cancel_dump_traceback_later()
    assert "s" in box, "takıldı"
    assert len(box["s"].succeeded) == len(files)


def test_diag_thread_only(tmp_path):
    _run_in_thread(_files(tmp_path), str(tmp_path / "o"))


def test_diag_thread_with_tk(tmp_path):
    import tkinter as tk
    root = tk.Tk()
    try:
        _run_in_thread(_files(tmp_path), str(tmp_path / "o"), pump=root.update)
    finally:
        root.destroy()


def test_diag_thread_with_gui_modules(tmp_path):
    import tkinter as tk
    import dxftoncz_gui  # noqa: F401  (cad_export/matplotlib içe aktarımı)
    root = tk.Tk()
    try:
        _run_in_thread(_files(tmp_path), str(tmp_path / "o"), pump=root.update)
    finally:
        root.destroy()


def test_diag_thread_with_droptarget(tmp_path):
    import tkinter as tk
    from win_dnd import DropTarget
    root = tk.Tk()
    DropTarget(root, lambda f: None)
    try:
        _run_in_thread(_files(tmp_path), str(tmp_path / "o"), pump=root.update)
    finally:
        root.destroy()
