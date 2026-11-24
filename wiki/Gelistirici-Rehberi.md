# Geliştirici Rehberi

## Proje yapısı

| Dosya | Görev |
|---|---|
| `nczforge.py` | Exe'nin giriş noktası |
| `dxftoncz_gui.py` | Masaüstü arayüzü (tkinter) |
| `win_dnd.py` | Windows sürükle-bırak desteği |
| `ncz_parser.py` | NCZ okuyucu |
| `ncz_writer.py` | NCZ yazıcı |
| `ncz_to_dxf.py` / `dxf_to_ncz.py` | Dönüştürücüler |
| `cad_export.py` | PDF / TIF / önizleme çizimi (ezdxf + matplotlib) |
| `batch_convert.py` | Çoklu ve paralel dönüştürme |
| `ncz_tool.py` | Komut satırı |
| `version.py` | Sürüm numarası ve güncelleme kontrolü |
| `tests/` | pytest testleri |
| `wiki/` | Bu wiki'nin kaynağı |

## Geliştirme ortamı

```bash
pip install -r requirements-dev.txt
python -m pytest -q tests
python nczforge.py
```

Testler her gönderimde GitHub Actions'ta **Windows ve Linux** üzerinde çalışır. Windows testleri gerçek bir sürükle-bırak mesajı göndererek arayüzü uçtan uca dener.

## Python kütüphanesi olarak kullanım

### NCZ okuma
```python
from ncz_parser import parse_ncz

r = parse_ncz("examples/103_11.NCZ")
for e in r["entities"][:5]:
    print(e["geometry_kind"], e["layer_name"], e["coordinates"][0])
```

### Dönüştürme
```python
from ncz_to_dxf import convert_ncz_to_dxf
from dxf_to_ncz import convert_dxf_to_ncz
from batch_convert import collect_files, batch_convert

convert_ncz_to_dxf("girdi.NCZ", "cikti.dxf")
convert_dxf_to_ncz("girdi.dxf", "cikti.NCZ", template_path="examples/103_11.NCZ")

ozet = batch_convert(collect_files(["proje_klasoru"]), target="pdf", workers=4)
print(len(ozet.succeeded), len(ozet.failed))
```

### Sıfırdan NCZ oluşturma (`ncz_writer.py`)
```python
from ncz_writer import NCZWriter

# Şablonlu veya sıfırdan bir writer başlatın:
writer = NCZWriter(template_path="examples/103_11.NCZ")

# Tabaka ekleme:
writer.add_layer("PARSEL", color_code=251)
writer.add_layer("BINA", color_code=4)

# Nokta ekleme (X=Sağa/Easting, Y=Yukarı/Northing):
writer.add_point(x=472500.0, y=4108000.0, z=0.0, layer="NOKTA", name="P1")

# Çizgi ekleme:
writer.add_line(x1=472500.0, y1=4108000.0, x2=472600.0, y2=4108050.0, layer="PARSEL")

# Çoklu çizgi / Poligon ekleme:
writer.add_polygon([
    (472500.0, 4108000.0, 0.0),
    (472600.0, 4108000.0, 0.0),
    (472600.0, 4108100.0, 0.0),
    (472500.0, 4108100.0, 0.0),
], layer="BINA")

# Yazı ekleme:
writer.add_text(x=472550.0, y=4108050.0, text="103/11", height=2.5, rotation_deg=0.0, layer="YAZI")

# Çember ekleme:
writer.add_circle(cx=472550.0, cy=4108050.0, radius=5.0, layer="0")

# NCZ dosyasını derleyip kaydetme:
writer.save("yeni_cizim.NCZ")
```

## Yeni sürüm yayınlama

1. `version.py` içindeki `__version__` değerini artırın (ör. `1.1.2`).
2. [[Sürüm Notları|Surum-Notlari]] sayfasına (`wiki/Surum-Notlari.md`) değişiklikleri ekleyin.
3. Değişiklikleri `main` dalına birleştirin.
4. GitHub'da **Actions → Windows Exe Derle ve Yayınla → Run workflow** deyin.

İş akışı testleri Windows'ta çalıştırır, exe'yi PyInstaller ile derler, `v<sürüm>` etiketini ve Release'i oluşturup **NCZ.Forge.exe**'yi ekler. Kullanıcılar programda güncelleme bildirimi görür.

## Wiki'yi düzenleme

Wiki sayfaları depodaki `wiki/` klasöründe tutulur. `main` dalında bu klasör değiştiğinde **Wiki'yi Yayınla** iş akışı sayfaları GitHub Wiki'ye otomatik kopyalar. Wiki'yi doğrudan GitHub arayüzünden düzenlemeyin; değişiklikler bir sonraki yayında üzerine yazılır.
