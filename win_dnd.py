"""
win_dnd.py - Windows için güvenli sürükle-bırak (WM_DROPFILES) desteği.

windnd kütüphanesinin yerine geçer. Farklar:
  * 64-bit Windows'ta pencere yordamı işaretçisi doğru (64-bit) türlerle saklanır.
  * Dosya yolu uzunluğu sınırı yoktur (260 karakterden uzun yollar da okunur).
  * Windows mesaj işleyicisinin içinde hiçbir arayüz (Tk) işlemi yapılmaz ve hiçbir
    hata dışarı sızmaz; bırakılan yollar bir kuyruğa konur, arayüz bunları kendi
    döngüsünde (root.after ile) işler. Böylece hata olsa bile program kapanmaz.
"""

from __future__ import annotations
import queue
import sys
from typing import Callable, List

WM_DROPFILES = 0x0233
GWLP_WNDPROC = -4


class DropTarget:
    def __init__(self, tk_widget, on_drop: Callable[[List[str]], None], poll_ms: int = 100):
        self._widget = tk_widget
        self._on_drop = on_drop
        self._poll_ms = poll_ms
        self._queue: "queue.Queue[List[str]]" = queue.Queue()
        self._old_proc = None
        self._new_proc = None  # ctypes geri çağırma nesnesi; çöp toplanmaması için referans tutulur
        self.errors: List[str] = []
        if sys.platform != "win32":
            raise OSError("Sürükle-bırak yalnızca Windows'ta desteklenir")
        self._install()
        self._widget.after(self._poll_ms, self._poll)

    def _install(self):
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)

        LRESULT = ctypes.c_ssize_t
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

        if ctypes.sizeof(ctypes.c_void_p) == 8:
            set_long = user32.SetWindowLongPtrW
        else:
            set_long = user32.SetWindowLongW
        set_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        set_long.restype = ctypes.c_void_p

        call_proc = user32.CallWindowProcW
        call_proc.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        call_proc.restype = LRESULT

        query = shell32.DragQueryFileW
        query.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
        query.restype = wintypes.UINT
        shell32.DragFinish.argtypes = [wintypes.HANDLE]
        shell32.DragFinish.restype = None
        shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
        shell32.DragAcceptFiles.restype = None

        def wndproc(hwnd, msg, wparam, lparam):
            if msg == WM_DROPFILES:
                hdrop = wintypes.HANDLE(wparam)
                try:
                    count = query(hdrop, 0xFFFFFFFF, None, 0)
                    files = []
                    for i in range(count):
                        length = query(hdrop, i, None, 0)
                        buf = ctypes.create_unicode_buffer(length + 1)
                        query(hdrop, i, buf, length + 1)
                        files.append(buf.value)
                    self._queue.put(files)
                except BaseException as ex:  # mesaj işleyicisinden hata sızarsa süreç çöker
                    self.errors.append(repr(ex))
                finally:
                    try:
                        shell32.DragFinish(hdrop)
                    except BaseException:
                        pass
                return 0
            return call_proc(self._old_proc, hwnd, msg, wparam, lparam)

        hwnd = self._widget.winfo_id()
        self._new_proc = WNDPROC(wndproc)
        shell32.DragAcceptFiles(hwnd, True)
        self._old_proc = set_long(hwnd, GWLP_WNDPROC, ctypes.cast(self._new_proc, ctypes.c_void_p))
        if not self._old_proc:
            raise OSError(f"Pencere yordamı değiştirilemedi (hata {ctypes.get_last_error()})")

    def _poll(self):
        try:
            while True:
                files = self._queue.get_nowait()
                self._on_drop(files)
        except queue.Empty:
            pass
        finally:
            self._widget.after(self._poll_ms, self._poll)
