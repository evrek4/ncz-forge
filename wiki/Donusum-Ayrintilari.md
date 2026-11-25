# Dönüşüm Ayrıntıları

🇬🇧 *English: [[Conversion Details|Conversion-Details]]*

## NCZ ➔ DXF

| NCZ nesnesi | DXF karşılığı | Not |
|---|---|---|
| Nokta | `POINT` | Kot (Z) korunur |
| Çizgi | `LINE` | |
| Çoklu çizgi / Poligon | `LWPOLYLINE` | Poligonlar kapalı |
| Kutu, üçgen, akıllı nesne | Kapalı `LWPOLYLINE` | |
| Pafta | Kapalı `LWPOLYLINE` + pafta adı yazısı | |
| Yazı | `TEXT` | Yükseklik ve dönüş açısı korunur |
| Daire | `CIRCLE` | |
| Yay | `ARC` | Bkz. sınırlamalar |
| Sembol | `INSERT` (`NCZ_SEMBOL_<kod>` bloğu) | Bkz. sınırlamalar |
| Blok referansı | `INSERT` (`NCZ_BLOK_<ad>` bloğu) | Bkz. sınırlamalar |

### Renkler

- Her **tabakanın rengi** DXF tabakasına aktarılır (24-bit gerçek renk).
- Rengi tabakasından farklı olan nesneler kendi renklerini taşır; aynı olanlar *ByLayer* bırakılır.
- **Siyah ve beyaz**, AutoCAD'in 7 numaralı rengine çevrilir: beyaz arka planda siyah, siyah arka planda beyaz görünür. Böylece hiçbir çizgi arka plan rengi yüzünden kaybolmaz.

### Koordinatlar

Netcad dosyada Yukarı (Northing) değerini önce, Sağa (Easting) değerini sonra saklar. NCZ Forge bunu otomatik olarak CAD standardına (X = Sağa, Y = Yukarı) çevirir.

## DXF ➔ NCZ

- Tabakalar ve renk numaraları aktarılır.
- **Bloklar (`INSERT`) ve ölçülendirmeler (`DIMENSION`) patlatılır**: içlerindeki çizgiler, yazılar vb. gerçek koordinatlarıyla, tabaka/renk mirasıyla yazılır.
- `ARC`, `ELLIPSE`, `SPLINE` gibi eğriler çoklu çizgiye çevrilir.
- `HATCH` (tarama) sınır çizgileri, `SOLID` / `3DFACE` kenarları ve `LEADER` (kılavuz çizgisi) çoklu çizgi olarak yazılır.
- `MTEXT` biçim kodlarından arındırılıp düz yazı olarak yazılır.
- NCZ Forge'un ürettiği `NCZ_SEMBOL_*` / `NCZ_BLOK_*` blokları patlatılmaz; ekleme noktaları **nokta** olarak geri yazılır.
- **Şablon NCZ** verilirse projeksiyon ve stil bilgileri şablondan alınır.

## Bilinen sınırlamalar

- **Sembol şekilleri:** Netcad'in sembol kütüphanesi NCZ dosyasının içinde bulunmaz. Bu yüzden semboller DXF'te doğru yer, boyut ve açıyla, ama **yer tutucu bir işaretle** (daire ve artı) çizilir. AutoCAD'de `NCZ_SEMBOL_<kod>` bloğunu düzenleyerek aynı koddaki tüm sembollerin şeklini tek seferde değiştirebilirsiniz.
- **Blok tanımları:** NCZ blok referanslarının içeriği çözülemediği için yer tutucu (çarpı) çizilir.
- **Yay açıları:** Henüz yay içeren gerçek bir Netcad dosyasıyla doğrulanmadı. Yaylarınız yanlış yönde çiziliyorsa lütfen örnek dosyayla [bildirin](https://github.com/evrek4/ncz-forge/issues).
- **DWG:** Desteklenmez. DWG'yi AutoCAD, BricsCAD, ZWCAD, QGIS veya ücretsiz *ODA File Converter* ile DXF olarak kaydedip kullanın.
- **Öznitelik tabloları** DXF'e aktarılmaz.
