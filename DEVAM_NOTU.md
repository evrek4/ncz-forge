# Devam Notu (Handoff)

**Son güncelleme:** 25 Kasım 2026 · **Yayındaki sürüm:** v1.1.1 · **Kalıcı kurallar:** [`CLAUDE.md`](CLAUDE.md)

Bu not, çalışmayı başka bir Claude hesabında / oturumunda kaldığı yerden sürdürmek içindir.

## Başka bir Claude hesabında nasıl devam edilir?

1. Yeni hesapta GitHub'ı bağlayın ve Claude GitHub uygulamasının `evrek4/ncz-forge` deposuna erişimi olduğundan emin olun.
2. Bu depoyla yeni bir Claude Code oturumu başlatın.
3. İlk mesaj olarak şunu yazın:
   > `DEVAM_NOTU.md` ve `CLAUDE.md` dosyalarını oku, kaldığımız yerden devam et.

Tüm kod, testler, iş akışları, wiki kaynağı ve bu not `main` dalındadır; önceki oturumda kaydedilmemiş bir şey kalmadı.

## Şu ana kadar yapılanlar (özet)

| Sürüm / PR | İçerik |
|---|---|
| v1.0 (10 Eki 2026) | İlk sürüm (kullanıcının kendi yayını) |
| [#1](https://github.com/evrek4/ncz-forge/pull/1) → v1.1.0 | Çoklu/paralel dönüştürme; yeni sol menülü arayüz; önizleme; güncelleme bildirimi; NCZ→DXF'te renkler, yaylar, semboller, bloklar; pytest testleri; GitHub Actions ile exe derleme; depo düzeni (`examples/`, exe depodan çıkarıldı) |
| [#2](https://github.com/evrek4/ncz-forge/pull/2) | `release.yml` elle çalıştırılınca etiket + Release'i kendisi oluşturuyor (bulut ortamı etiket push'una izin vermediği için) |
| [#3](https://github.com/evrek4/ncz-forge/pull/3) → v1.1.1 | 6+ dosya sürükleyince sessiz kapanma düzeltmesi (windnd → `win_dnd.py`); Windows'ta toplu dönüştürmenin %0'da takılması (iş parçacığından Tk çağrısı → kuyruk); hata kaydı `%LOCALAPPDATA%\NCZ Forge\hata_kaydi.log`; testler Windows'ta da çalışıyor |
| [#4](https://github.com/evrek4/ncz-forge/pull/4) | GitHub Wiki (Türkçe, 10 sayfa) + `wiki.yml` ile otomatik yayın |
| (bu değişiklik) | Wiki'ye İngilizce sayfalar (10 sayfa, iki dilli yan menü); `CLAUDE.md` ve bu not |

Wiki: https://github.com/evrek4/ncz-forge/wiki · İngilizce giriş: https://github.com/evrek4/ncz-forge/wiki/English

## Açık konular / bekleyenler

1. **Kullanıcı doğrulaması bekleniyor (öncelikli):** v1.1.1 exe'si gerçek bir kullanıcı bilgisayarında 6+ NCZ sürükleyerek henüz denenmedi (yalnızca GitHub'ın Windows makinesinde otomatik test edildi). Sorun sürerse kullanıcıdan `hata_kaydi.log` istenecek.
2. **Yay açıları doğrulanmadı:** `ncz_to_dxf._arc_angles_degrees` radyan varsayıyor (2π'yi aşarsa grad). Örnek dosyada yay yok. Yay içeren gerçek bir NCZ ile kontrol edilmeli.
3. **Sembol şekilleri:** NCZ'de sembol kütüphanesi yok; DXF'te `NCZ_SEMBOL_<kod>` yer tutucu bloğu (daire + artı) çiziliyor. Gerçek şekiller için Netcad sembol kütüphanesi formatı çözülmeli (büyük iş).
4. **Git geçmişinde 57 MB exe:** Eski commit'lerde `NCZ Forge.exe` duruyor; temizlemek geçmişi yeniden yazmayı (force push) gerektirir. Kullanıcıya sorulmadan yapılmamalı.
5. **Kullanıcının kendisinin yapması gerekenler (araçlarla yapılamıyor):**
   - Depoya konu etiketleri eklemek: GitHub depo sayfası → ⚙️ About → `netcad`, `ncz`, `dxf`, `autocad`, `gis`.
   - İsteğe bağlı: kod imzalama sertifikası (SmartScreen uyarısını kaldırır, ücretli).
6. **Küçük teknik borçlar:**
   - `actions/checkout@v4`, `actions/setup-python@v5` Node 20 uyarısı veriyor; yeni ana sürümlere geçilebilir.
   - Release notları GitHub'ın otomatik İngilizce özetiyle oluşuyor; istenirse `release.yml` `wiki/Surum-Notlari.md`'den not alacak şekilde düzenlenebilir.

## Önerilen sonraki adımlar
- Kullanıcıdan v1.1.1 geri bildirimi al (madde 1).
- Yay içeren bir NCZ örneği iste ve madde 2'yi doğrula; gerekirse düzeltip test ekle.
- İndirme istatistiği sorulursa: Release asset'lerinin `download_count` toplamı (v1.0: 1, v1.1.0 ve v1.1.1 yeni).

## Ortam notları (bulut oturumu)
- Çalışma dalı adı oturuma göre değişir; her iş için dal → PR → `main` akışı kullanıldı.
- Etiket push'u ve wiki deposuna doğrudan push bulut proxy'si tarafından engelleniyor → `release.yml` ve `wiki.yml` kullanın.
- Linux'ta GUI denemek için `python3-tk` ve `xvfb-run` gerekir; önizleme için Pillow'un `ImageTk` modülü olmalı.
