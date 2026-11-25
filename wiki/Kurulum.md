# Kurulum

🇬🇧 *English: [[Installation]]*

## Windows (önerilen)

NCZ Forge **kurulum gerektirmez** (portable). Tek bir `.exe` dosyasıdır.

1. [Son sürüm sayfasından](https://github.com/evrek4/ncz-forge/releases/latest) **NCZ.Forge.exe** dosyasını indirin.
2. İstediğiniz bir klasöre koyun (ör. Masaüstü) ve çift tıklayın.

> İlk açılış birkaç saniye sürebilir; program kendini geçici bir klasöre açar.

### "Windows bilgisayarınızı korudu" uyarısı

Exe dijital olarak imzalı olmadığı için Windows SmartScreen bu uyarıyı gösterebilir.

1. Uyarıdaki **Ek bilgi** bağlantısına tıklayın.
2. **Yine de çalıştır** düğmesine basın.

Bu yalnızca ilk çalıştırmada sorulur. Exe, bu depodaki kaynak koddan **GitHub Actions** üzerinde otomatik derlenir; derleme kayıtları [Actions](https://github.com/evrek4/ncz-forge/actions) sekmesinde herkese açıktır.

### Güncelleme

Yeni bir sürüm çıktığında program sol menünün altında **"⬆ Yeni sürüm hazır"** bildirimi gösterir (v1.1.0 ve sonrası). Tıklayınca indirme sayfası açılır; yeni exe'yi eskisinin yerine koymanız yeterlidir. Ayarlar dosyası olmadığından hiçbir şey kaybolmaz.

### Kaldırma

Exe dosyasını silmeniz yeterlidir. Hata kaydı tutulduysa `%LOCALAPPDATA%\NCZ Forge` klasörünü de silebilirsiniz.

## Kaynak koddan çalıştırma (Windows / Linux / macOS)

Python 3.10 veya üzeri gerekir.

```bash
git clone https://github.com/evrek4/ncz-forge.git
cd ncz-forge
pip install -r requirements.txt
python nczforge.py          # arayüz
python ncz_tool.py --help   # komut satırı
```

> Sürükle-bırak yalnızca Windows'ta çalışır; diğer sistemlerde dosyaları **Gözat** düğmeleriyle seçin.

Sonraki adım: [[Kullanım Kılavuzu|Kullanim-Kilavuzu]]
