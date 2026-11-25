# Sorun Giderme ve SSS

🇬🇧 *English: [[Troubleshooting]]*

## Program bir hata verdi / beklenmedik şekilde davrandı

v1.1.1 ve sonrasında tüm hatalar şu dosyaya kaydedilir:

```
%LOCALAPPDATA%\NCZ Forge\hata_kaydi.log
```

Bu yolu Dosya Gezgini'nin adres çubuğuna yapıştırıp Enter'a basın. Bir [hata bildirimi](https://github.com/evrek4/ncz-forge/issues/new) açarken bu dosyayı ve mümkünse sorunlu NCZ/DXF dosyasını ekleyin.

## Sık sorulan sorular

**"Windows bilgisayarınızı korudu" diyor.**
Exe imzalı olmadığı için normaldir. **Ek bilgi → Yine de çalıştır**. Bkz. [[Kurulum]].

**Çok sayıda dosya sürükleyince program kapanıyordu.**
v1.1.0 ve öncesinde kullanılan sürükle-bırak kütüphanesinden kaynaklanıyordu; **v1.1.1'de düzeltildi** (Windows'ta 40 dosyaya kadar test edildi). [Son sürümü](https://github.com/evrek4/ncz-forge/releases/latest) indirin.

**Toplu dönüştürme %0'da kalıyor.**
v1.1.0'da Windows'a özgü bir sorundu; **v1.1.1'de düzeltildi**. Sorun sürerse *Paralel işle* işaretini kaldırıp deneyin ve hata kaydını gönderin.

**Netcad'de çizim yan yatmış / ters görünüyor.**
DXF ➔ NCZ sayfasında **X ve Y koordinatlarını yer değiştir** seçeneğini işaretleyip yeniden dönüştürün.

**DXF'te semboller daire ve artı olarak görünüyor.**
Netcad sembol şekilleri NCZ dosyasında bulunmaz; yer tutucu çizilir. Bkz. [Dönüşüm Ayrıntıları → Bilinen sınırlamalar](https://github.com/evrek4/ncz-forge/wiki/Donusum-Ayrintilari#bilinen-sınırlamalar).

**AutoCAD'im DXF'i açmıyor.**
NCZ ➔ DXF sayfasında **DXF sürümü** olarak R2000 veya R2004 seçin.

**PDF'te bazı çizgiler görünmüyor.**
Arka planı değiştirip (Beyaz/Siyah) deneyin. Sorun sürerse dosyayla birlikte bildirin.

**DWG dosyasını açabilir miyim?**
Hayır; önce DXF olarak kaydedin. Bkz. [[Dönüşüm Ayrıntıları|Donusum-Ayrintilari]].

**Mac veya Linux'ta çalışır mı?**
Hazır exe yalnızca Windows içindir. Diğer sistemlerde kaynak koddan çalıştırabilirsiniz (sürükle-bırak hariç). Bkz. [[Kurulum]].

**Programın çevrimdışı çalışması mümkün mü?**
Evet. İnternet yalnızca açılışta yeni sürüm kontrolü için kullanılır; bağlantı yoksa sessizce atlanır. Dosyalarınız hiçbir yere gönderilmez.
