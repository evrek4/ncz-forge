# CLAUDE.md — NCZ Forge

Bu dosya, bu depoda çalışan Claude oturumları için kalıcı kurallardır. Güncel durum ve yapılacaklar için **`DEVAM_NOTU.md`** dosyasını okuyun.

## Proje
NCZ Forge: Netcad `.NCZ` ⮂ AutoCAD `.dxf` dönüştürücü, PDF/TIF dışa aktarıcı, toplu dönüştürme. Windows masaüstü uygulaması (tkinter, PyInstaller ile tek exe) + komut satırı (`ncz_tool.py`). Python 3.12, bağımlılıklar `requirements.txt` (ezdxf, matplotlib, Pillow).

## İletişim ve dil
- Kullanıcıyla **Türkçe** konuşun. Kullanıcı "manuel iş yaptırma" dedi: GitHub dahil her şeyi mümkün olduğunca kendiniz yapın; yalnızca gerçekten elinizde olmayan adımları isteyin.
- Arayüz metinleri, CLI mesajları, wiki (Türkçe sayfalar) ve commit mesajları Türkçedir. Commit mesajlarında Türkçe karakter kullanılmıyor (ASCII), PR başlık/açıklamaları Türkçe karakterli olabilir.

## Mimari (dosya → görev)
| Dosya | Görev |
|---|---|
| `nczforge.py` | Exe giriş noktası; `multiprocessing.freeze_support()` GUI içe aktarılmadan ÖNCE çağrılmalı |
| `dxftoncz_gui.py` | Arayüz. Sol menü + 4 sayfa (d2n, n2d, exp, batch); `_run_task` ortak görev çalıştırıcı |
| `win_dnd.py` | Windows sürükle-bırak (WM_DROPFILES). windnd'nin yerine yazıldı |
| `ncz_parser.py` / `ncz_writer.py` | NCZ okuma / yazma (tersine mühendislik) |
| `ncz_to_dxf.py` / `dxf_to_ncz.py` | Dönüştürücüler |
| `cad_export.py` | PDF/TIF/önizleme (ezdxf drawing + matplotlib) |
| `batch_convert.py` | Toplu + paralel (ProcessPoolExecutor) dönüştürme |
| `version.py` | `__version__` ve GitHub'dan güncelleme kontrolü |
| `wiki/` | GitHub Wiki kaynağı (TR + EN sayfalar) |

## Uyulması gereken kurallar (geçmiş hatalardan)
1. **Arka plan iş parçacıkları Tk'ye asla dokunmaz.** Arayüz güncellemesi için `self._ui(lambda: ...)` kullanın (kuyruk + `_drain_ui`). `root.after(...)` başka iş parçacığından çağrılınca Windows'ta "main thread is not in main loop" hatasıyla toplu dönüştürme %0'da kalıyordu (v1.1.1'de düzeltildi).
2. **Windows mesaj işleyicisinde (win_dnd wndproc) Tk işlemi yapılmaz, hata sızdırılmaz.** Yollar kuyruğa konur, `_poll` ile işlenir. Sızan hata süreci sessizce kapatır.
3. **Kaynak dosyanın üzerine asla yazılmaz.** Toplu dönüştürmede çakışan çıktılar `_2`, `_3` eki alır (`_unique_path`). Tekli işlemlerde var olan dosya için onay sorulur (`_confirm_overwrite`).
4. Yeni GUI testleri `sys.argv`'yi sabitlemeli (pytest argümanları bırakılmış dosya sanılır) — bkz. `tests/test_win_dnd.py` fixture.
5. Paralel kod değişirse Windows'ta test edilmeden yayınlanmaz (spawn davranışı Linux'tan farklı).

## Test
```bash
pip install -r requirements-dev.txt
python -m pytest -q tests
```
- Linux'ta Windows'a özgü testler atlanır (skip). Gerçek doğrulama GitHub Actions `tests.yml`'de **windows-latest + ubuntu-latest** matrisiyle yapılır; Windows testi gerçek WM_DROPFILES mesajıyla arayüzü uçtan uca dener.
- Arayüzü Linux'ta denemek için: `xvfb-run -s "-screen 0 1040x700x24" python3 nczforge.py` (python3-tk gerekir).

## GitHub iş akışları (.github/workflows)
- `tests.yml` — her push/PR'da testler (Windows + Linux).
- `release.yml` — **"Windows Exe Derle ve Yayınla"**. Elle çalıştırma (`workflow_dispatch`, `yayinla=true`): `version.py`'deki sürümle `v<sürüm>` etiketi + Release oluşturur, `NCZ.Forge.exe` ekler. Etiket push'u da tetikler.
- `wiki.yml` — **"Wiki'yi Yayınla"**. `main`'de `wiki/**` değişince wiki deposuna kopyalar. Wiki'yi GitHub web arayüzünden düzenlemeyin; üzerine yazılır.

## Sürüm yayınlama
1. `version.py` → `__version__` artır.
2. `wiki/Surum-Notlari.md` ve `wiki/Release-Notes.md`'ye notları ekle.
3. Dalı `main`'e PR ile birleştir (testler yeşil olmalı).
4. `release.yml`'yi `main` üzerinde `yayinla=true` ile çalıştır; Release'i ve exe'yi doğrula.

## Claude Code bulut ortamı kısıtları (bilinen)
- Git proxy yalnızca bu oturuma atanan dala push'a izin verir; **etiket push'u ve wiki deposuna doğrudan push 403/erişilemez**. Bu yüzden etiket/Release `release.yml` ile, wiki `wiki.yml` ile oluşturulur.
- GitHub işlemleri (PR açma/birleştirme, workflow çalıştırma, log okuma) GitHub MCP araçlarıyla yapılır. Kullanıcı bu projede PR açma, `main`'e birleştirme ve sürüm yayınlamanın Claude tarafından yapılmasını istedi; yine de büyük/geri alınamaz işlemlerden (ör. force push, geçmiş yeniden yazma) önce sorun.
- Depo ziyaretçi istatistikleri (Insights → Traffic) API ile alınamıyor; indirme sayıları Release asset'lerinin `download_count` alanından okunur.
