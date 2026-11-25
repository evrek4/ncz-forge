# Sürüm Notları

🇬🇧 *English: [[Release Notes|Release-Notes]]*

## v1.1.1 — 24 Kasım 2026

**Düzeltmeler**
- Çok sayıda dosya (6+) sürükleyip bırakınca programın sessizce kapanması düzeltildi. Sürükle-bırak baştan yazıldı; 260 karakterden uzun yollar da destekleniyor.
- Windows'ta toplu dönüştürmenin %0'da takılı kalması düzeltildi.

**İyileştirmeler**
- Program artık hata durumunda sessizce kapanmıyor; mesaj gösteriyor ve ayrıntıları `%LOCALAPPDATA%\NCZ Forge\hata_kaydi.log` dosyasına yazıyor.
- Paralel dönüştürmede bir süreç çökerse kalan dosyalar sırayla yeniden deneniyor.

## v1.1.0 — 24 Kasım 2026

**Yeni**
- **Çoklu dönüştürme:** Birden fazla NCZ/DXF dosyasını veya klasörü tek seferde NCZ ⮂ DXF, PDF ya da TIF'e dönüştürme; paralel işleme.
- **Yeni arayüz:** Sol menülü, kart tabanlı tasarım.
- **Önizleme** penceresi (yakınlaştırma / kaydırma).
- Sürüm numarası ve **yeni sürüm bildirimi**.
- Var olan dosyanın üzerine yazmadan önce onay.

**Dönüşüm kalitesi (NCZ ➔ DXF)**
- Tabaka ve nesne **renkleri** aktarılıyor; NCZ'den alınan PDF/TIF çıktıları da renkli.
- Yaylar, semboller, bloklar, üçgenler, paftalar ve akıllı nesneler artık atlanmıyor.

**Diğer**
- Exe boyutu 57 MB'tan 44 MB'a indi; exe artık GitHub Actions'ta otomatik derleniyor.

## v1.0 — 10 Ekim 2026

İlk sürüm: NCZ ⮂ DXF dönüştürme, vektör PDF ve TIF dışa aktarma, sürükle-bırak destekli masaüstü arayüzü.
