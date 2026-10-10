# Netcad NCZ Encoder / Decoder & DXF Çevirici Kütüphanesi

Bu kütüphane ve araç seti, Netcad'in tescilli ikili (binary) formatı olan **.NCZ** dosyalarını okumak, ayrıştırmak (parse), sıfırdan oluşturmak ve **AutoCAD DXF / DWG dosyalarını NCZ formatına dönüştürmek (encode)** amacıyla geliştirilmiştir.

---

## 🚀 Hızlı Başlangıç

### 🖥️ 1. Masaüstü Uygulaması (Terminalsiz - İki Yönlü)
Klasördeki **`dxftoncz.exe`** dosyasına çift tıklayarak modern pencereli arayüzü açabilirsiniz:
* **Sekme 1 (DXF ➔ NCZ):** AutoCAD DXF çiziminizi Netcad NCZ formatına dönüştürür.
* **Sekme 2 (NCZ ➔ DXF):** Netcad NCZ dosyanızı AutoCAD DXF formatına dönüştürür.
* **Sürükle & Bırak:** Bir `.dxf` dosyasını `dxftoncz.exe` üzerine bıraktığınızda otomatik olarak **DXF ➔ NCZ** sekmesi; bir `.ncz` dosyasını bıraktığınızda ise **NCZ ➔ DXF** sekmesi açılır ve dosya yüklenir.
```bash
python ncz_tool.py info 103_11.NCZ
```
Çıktı; Netcad sürümünü, projeksiyon/dilim bilgisini, tabakaları, obje türlerini ve sınır koordinatlarını listeler.

### 2. DXF Dosyasını NCZ'ye Dönüştürme (DXF to NCZ - Encoder)
```bash
python ncz_tool.py dxf2ncz 103_11.dxf 103_11_yeni.NCZ
```
*İsteğe bağlı olarak mevcut bir NCZ dosyasını şablon (projeksiyon, sembol, stil mirası için) olarak verebilirsiniz:*
```bash
python ncz_tool.py dxf2ncz girdi.dxf cikti.NCZ --template 103_11.NCZ
```

### 3. NCZ Dosyasını DXF'e Dönüştürme (NCZ to DXF - Decoder)
```bash
python ncz_tool.py ncz2dxf 103_11.NCZ 103_11.dxf
```

### 4. NCZ Dosyasını Yeniden Encode Etme (Re-encode)
```bash
python ncz_tool.py reencode 103_11.NCZ 103_11_reencoded.NCZ
```

---

## 🛠️ Python Kütüphanesi Olarak Kullanım (`ncz_writer.py`)

Kendi kodunuzda CAD objeleri oluşturup doğrudan `.NCZ` olarak kaydetmek için:

```python
from ncz_writer import NCZWriter

# Şablonlu veya sıfırdan bir writer başlatın:
writer = NCZWriter(template_path="103_11.NCZ")

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

---

## 🔬 NCZ Dosya Formatının İkili (Binary) Yapısı

NCZ dosyası sıralı bloklardan meydana gelir. Her bloğun başlığı:
1. `block_type`: 1 bayt (uint8)
2. `payload_length`: 4 bayt (uint32 little-endian)
3. `payload`: `payload_length` kadar bayt

### Temel Blok Tipleri:
* **Blok 1 (Dosya Başlığı / Master Index):** Toplam dosya boyutunu, diğer ana blokların (Blok 2, 6, 8, 11, 12, 14, 13, 23) dosya içindeki kesin bayt ofsetlerini, çizimin genel sınır kutusunu (Bounding Box: MinX, MinY, MaxX, MaxY) ve toplam geometri sayısını içerir.
* **Blok 2 (UserInfo):** Netcad dosya başlığı ve kullanıcı bilgisi (`\x06netcad...`).
* **Blok 4 (Visible Extents):** Çizim penceresinin varsayılan görünür limitleri.
* **Blok 6 (Layer Table):** Çizimdeki tüm tabakaların isimleri (`windows-1254` kodlamalı Pascal string), renk indisleri ve durum bayrakları (her kayıt 29 bayttır).
* **Blok 21 (Standart Geometri):** Çizimdeki tüm vektör objelerini tutar:
  * **Tip 1 (Point):** Koordinat, kot, tabaka, renk ve nokta adı.
  * **Tip 2 (Line):** Başlangıç ve bitiş koordinatları (X1, Y1, Z1, X2, Y2, Z2) ve Bounding Box.
  * **Tip 3 (Circle):** Merkez koordinatı ve yarıçap.
  * **Tip 5 (Text):** Ekleme noktası, yazı yüksekliği, radyan cinsinden dönüş açısı ve Türkçe karakter uyumlu (`CP1254`) metin içeriği.
  * **Tip 7 (Multiline / Polyline / Polygon):** Tepe noktası sayısı kadar 24 baytlık `(X, Y, Z)` double kayıtları ve poligon etiketi.

### 📐 Koordinat Dönüşüm Kuralı (Önemli):
* Uluslararası CAD/GIS standardında (DXF, SHP, QGIS) ilk koordinat **X (Sağa / Easting)**, ikinci koordinat **Y (Yukarı / Northing)** şeklindedir.
* Netcad ikili dosyasında `raw_x` **Yukarı (Northing)**, `raw_y` ise **Sağa (Easting)** olarak depolanır.
* `ncz_writer.py` ve `dxf_to_ncz.py` bu dönüşümü otomatik ve kayıpsız (0.00000000 m hata ile) gerçekleştirir.

---

## 📂 DWG Dosyaları Hakkında Not:
DWG Autodesk'in kapalı formatıdır. DWG dosyalarınızı AutoCAD, BricsCAD, ZWCAD, QGIS veya ücretsiz ODA File Converter ile **DXF** formatında kaydedip doğrudan `dxf_to_ncz.py` ile NCZ'ye dönüştürebilirsiniz.
