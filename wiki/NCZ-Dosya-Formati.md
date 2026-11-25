# NCZ Dosya Formatı

🇬🇧 *English: [[NCZ File Format|NCZ-File-Format]]*

> Bu sayfa teknik meraklılar ve geliştiriciler içindir. NCZ, Netcad'in belgelenmemiş ikili formatıdır; buradaki bilgiler tersine mühendislikle elde edilmiştir ve tüm Netcad sürümlerini kapsamayabilir.

## Genel yapı

NCZ dosyası sıralı bloklardan meydana gelir. Her bloğun başlığı:
1. `block_type`: 1 bayt (uint8)
2. `payload_length`: 4 bayt (uint32 little-endian)
3. `payload`: `payload_length` kadar bayt

## Temel Blok Tipleri:
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

## 📐 Koordinat Dönüşüm Kuralı (Önemli):
* Uluslararası CAD/GIS standardında (DXF, SHP, QGIS) ilk koordinat **X (Sağa / Easting)**, ikinci koordinat **Y (Yukarı / Northing)** şeklindedir.
* Netcad ikili dosyasında `raw_x` **Yukarı (Northing)**, `raw_y` ise **Sağa (Easting)** olarak depolanır.
* `ncz_writer.py` ve `dxf_to_ncz.py` bu dönüşümü otomatik ve kayıpsız (0.00000000 m hata ile) gerçekleştirir.

## Ayrıştırıcının tanıdığı diğer geometri türleri

`ncz_parser.py` yukarıdakilere ek olarak yay, sembol, blok referansı, kutu, pafta, üçgen ve akıllı nesne (SmartObject) kayıtlarını da okur. Tanınmayan kayıt türleri `unsupported_geometry_types` alanında sayılır:

```python
from ncz_parser import parse_ncz
r = parse_ncz("examples/103_11.NCZ")
print(r["version_name"], r["epsg"], len(r["entities"]))
print(r["unsupported_geometry_types"])   # ör. {14: 1}
```

Kaynak: [`ncz_parser.py`](https://github.com/evrek4/ncz-forge/blob/main/ncz_parser.py), [`ncz_writer.py`](https://github.com/evrek4/ncz-forge/blob/main/ncz_writer.py)
