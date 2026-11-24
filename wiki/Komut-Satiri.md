# Komut Satırı (CLI)

Tüm işlemler `ncz_tool.py` ile terminalden de yapılabilir. Kaynak koddan çalıştırma için bkz. [[Kurulum]].

```bash
python ncz_tool.py --help
python ncz_tool.py --version
```

## Komutlar

| Komut | Ne yapar |
|---|---|
| `info` | NCZ dosyasının sürümünü, projeksiyonunu, tabakalarını, nesne sayılarını ve sınırlarını gösterir |
| `ncz2dxf` | NCZ ➔ DXF |
| `dxf2ncz` | DXF ➔ NCZ |
| `ncz2pdf` / `ncz2tif` | NCZ ➔ PDF / TIF |
| `dxf2pdf` / `dxf2tif` | DXF ➔ PDF / TIF |
| `batch` | Çok sayıda dosya veya klasör |
| `reencode` | NCZ'yi okuyup yeniden yazar (doğrulama için) |

### info
```bash
python ncz_tool.py info examples/103_11.NCZ
```

### ncz2dxf
```bash
python ncz_tool.py ncz2dxf girdi.NCZ cikti.dxf [--version R2010]
```

### dxf2ncz
```bash
python ncz_tool.py dxf2ncz girdi.dxf cikti.NCZ [--template sablon.NCZ] [--swap-xy]
```

### PDF ve TIF
```bash
python ncz_tool.py ncz2pdf girdi.NCZ cikti.pdf [--bg white|black]
python ncz_tool.py ncz2tif girdi.NCZ cikti.tif [--dpi 300] [--bg white|black]
python ncz_tool.py dxf2pdf girdi.dxf cikti.pdf
python ncz_tool.py dxf2tif girdi.dxf cikti.tif --dpi 600
```

### batch (çoklu dönüştürme)
```bash
python ncz_tool.py batch GİRDİ [GİRDİ ...] [seçenekler]
```
`GİRDİ` dosya ya da klasör olabilir; birden fazla verilebilir.

| Seçenek | Varsayılan | Açıklama |
|---|---|---|
| `--to auto\|pdf\|tif` | `auto` | `auto`: NCZ ➔ DXF, DXF ➔ NCZ |
| `--out`, `-o` | kaynak klasör | Çıktı klasörü |
| `--recursive`, `-r` | kapalı | Alt klasörleri de tara |
| `--jobs`, `-j` | `0` | Paralel süreç sayısı (`0` = otomatik, `1` = sıralı) |
| `--template`, `-t` | — | DXF ➔ NCZ şablonu |
| `--swap-xy` | kapalı | DXF ➔ NCZ'de X/Y yer değiştir |
| `--version` | `R2010` | NCZ ➔ DXF için DXF sürümü |
| `--dpi` | `300` | PDF/TIF çözünürlüğü |
| `--bg` | `white` | PDF/TIF arka planı |

Örnekler:
```bash
# Bir klasör ve alt klasörlerindeki her şeyi PDF yap
python ncz_tool.py batch D:\Projeler --recursive --to pdf --out D:\PDF

# Üç dosyayı sırayla (paralel olmadan) dönüştür
python ncz_tool.py batch a.NCZ b.NCZ c.dxf --jobs 1
```

**Çıkış kodu:** Tüm dosyalar başarılıysa `0`, en az biri hatalıysa `2`, hiç dosya bulunamazsa `1`. Toplu betiklerde (`.bat`) hata kontrolü için kullanılabilir.

### reencode
```bash
python ncz_tool.py reencode girdi.NCZ yeniden.NCZ
```
