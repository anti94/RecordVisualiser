# SONAR Telemetri ve Veri Analiz Arayüzü — Geliştirme Planı

> Bu belge; `.bin` dosyalarında saklanan SONAR/sensör verilerinin, donanım BIT sonuçlarının, transmisyon bilgilerinin ve olay kayıtlarının Python tabanlı bir masaüstü uygulamada açılması, işlenmesi, görselleştirilmesi ve dışa aktarılması için uygulanabilir ürün ve yazılım geliştirme planıdır.

## 1. Projenin amacı

**Ana ürün hedefi:** [SONAR Veri Analiz Panosu Mockup’ı.png](<SONAR Veri Analiz Panosu Mockup’ı.png>) görselindeki masaüstü analiz panosunu gerçekleştirmek. Yerleşim, panel hiyerarşisi ve ana etkileşimler bu referansa göre geliştirilecek; sürümler Bölüm 22'deki küçük işlerle bu ekrana ulaşacaktır.

Tek bir uygulama içinde aşağıdaki işleri güvenilir ve hızlı biçimde yapmak:

- Büyük `.bin` kayıtlarını açmak, doğrulamak ve çözümlemek.
- Sensör kanallarını zaman alanında incelemek.
- FFT, PSD, spektrogram ve waterfall gibi SONAR analizlerini çalıştırmak.
- BIT sonuçlarını, transmisyon durumlarını ve sistem olaylarını sensör verileriyle aynı zaman ekseninde ilişkilendirmek.
- Kayıtlı veriyi oynatmak, duraklatmak, zaman içinde gezinmek ve seçili bölgeyi ayrıntılı analiz etmek.
- İleride canlı veri akışını aynı ekranlar ve aynı veri modeli üzerinden desteklemek.
- Analiz düzenlerini, filtre ayarlarını ve kullanıcı çalışma alanlarını kaydetmek.
- Grafik, veri ve analiz sonuçlarını tekrar üretilebilir biçimde dışa aktarmak.

Uygulamanın hedefi yalnızca grafik çizmek değil, operatör ve test mühendisinin “Bu anormallik ne zaman oluştu, aynı anda hangi donanım veya transmisyon olayı gerçekleşti?” sorusunu hızlıca cevaplayabilmesidir.

## 2. Başlangıç kabulleri

- Ana hedef platform Windows 10/11 64-bit masaüstüdür.
- İlk uygulama dili Python 3.12 veya proje bağımlılıklarıyla uyumlu en güncel kararlı Python sürümüdür.
- GUI için PySide6, yüksek hızlı grafikler için PyQtGraph kullanılacaktır.
- Matplotlib yalnızca rapor kalitesi gerektiren statik çıktılar veya PyQtGraph’ın uygun olmadığı özel çizimler için kullanılacaktır.
- `.bin` formatı projeye özel olabilir; parser, GUI’den tamamen ayrılacaktır.
- Hem kayıtlı dosya hem canlı akış aynı normalize edilmiş veri arayüzüne dönüştürülecektir.
- Tüm zaman damgaları uygulama içinde tek bir kanonik zaman temsiline çevrilecektir.
- İlk sürüm tek bilgisayarda ve tek kullanıcıyla çalışacaktır.
- C++/Rust hızlandırma ilk günden zorunlu değildir; ancak performans profili gerektiğini gösterirse parser veya DSP katmanı sonradan native modüle taşınabilecektir.

## 3. Kapsam

### 3.1 MVP kapsamı — v1.0.0

- Referans mockup'ın dokuz ana bölgesi, üç sütunlu düzeni ve koyu teması.
- Bir veya birden fazla `.bin` dosyası açma.
- Dosya header, sürüm, endian, boyut ve desteklenen formatın checksum doğrulaması.
- Kanal ağacı ve kanal arama/filtreleme.
- Sensör kanallarını zaman alanında çizme; ortak zaman ekseninde birden fazla kanal gösterme.
- Pan, X/Y/XY zoom, autoscale, reset view ve mouse cursor.
- Bölge seçimi ve seçili aralığa yakınlaşma.
- Seçili kanal için temel istatistikler; mockup'taki istatistik kartı.
- BIT sonuçları ve sistem olaylarını tablo halinde gösterme; sağ sütunda BIT durum özeti.
- Olayları grafik üzerinde zaman işareti olarak gösterme.
- Olay satırına çift tıklayınca ilgili zamana gitme.
- Kayıtlı veriyi oynatma/duraklatma, hız kontrolü ve zaman içinde gezinme.
- Grafik görüntüsünü PNG/SVG; seçili veriyi CSV olarak dışa aktarma.
- Açık panelleri ve pencere düzenini çalışma alanı olarak kaydetme.
- Okunabilir durum renkleri, ikonlar ve temel klavye kısayolları.

MVP'de mockup'taki FFT ve spektrogram hücreleri ile analiz araçlarının yerleri hazırdır; henüz uygulanmayan hesaplamalar pasif ve `v2.0.0 ile kullanılabilir` açıklamalıdır. İşlevi olmayan alanda gerçek analiz izlenimi veren sahte sonuç gösterilmez. Geliştirme simülatörü kullanıldığında veri kaynağı açıkça `Simülasyon` olarak görünür.

### 3.2 Analiz panosu ve performans — v2.0.0

- FFT, PSD, spektrogram ve waterfall.
- Mockup merkezinde zaman serisi, spektrogram, FFT ve istatistiğin birlikte çalışması.
- Filtre zinciri: low-pass, high-pass, band-pass, notch, detrend, normalize ve Bölüm 10'daki temel işlemler.
- Büyük dosyalar için indeksleme, lazy loading ve çok seviyeli downsampling.
- 125 ms bloklarda yüksek örnek hızlı ham akustik veri okuma.
- Kanal türetme ve basit formül editörü.
- Annotation/bookmark ekleme.
- Analiz oturumunu proje dosyası olarak kaydetme/açma.
- BIT trend ve health dashboard.
- Çoklu monitör ve ayrılabilir grafik pencereleri.

### 3.3 Canlı veri ve kayıt — v3.0.0

- Canlı UDP/TCP/serial veri adaptörleri ve bağlantı durumları.
- Ring buffer, paket kaybı ölçümü ve backpressure.
- Mevcut analiz panosunda canlı grafik, BIT/TX güncellemeleri ve kayıt durumu.
- 125 ms periyodik `Data00000`, `Data00001`, … kayıtları; güvenli kapatma ve tekrar okuma.
- Replay simülatörü, bağlantı kesintisi ve dayanıklılık kontrolleri.

### 3.4 Windows dağıtımı — v4.0.0

- Windows paketi, installer ve temiz ortamda çalıştırma.
- Kurulum/yükseltme, sürüm artefaktları ve checksum.
- Kullanıcı, format ve decoder kılavuzları.
- Tanılama paketi, workspace kurtarma ve son kullanıcı kabulü.
- CI kalite kapıları, release ve geri dönüş prosedürü.
- Gereksinim varsa offline paket ve code signing.

### 3.5 İleri sürüm / opsiyonel backlog

- Beamforming, bearing-time record, polar sonar display.
- Cross-correlation, coherence ve cross-spectrum.
- Otomatik anomali tespiti ve alarm kuralları.
- Test senaryosu karşılaştırma ve referans kayıt overlay.
- Otomatik PDF/HTML analiz raporu.
- Eklenti sistemi ve özel decoder paketleri.
- Yetki/rol sistemi ve denetim kaydı gerekiyorsa kurumsal güvenlik katmanı.
- Mockup'taki 3D View sekmesinin tam işlevi; bu kapsam ayrıca tanımlanacak.

Bu işler zorunlu v1–v4 teslimatlarına dahil değildir. Cross Analysis, 3D View ve Report sekmeleri görsel düzen içinde korunur; ilgili özellik tamamlanana kadar pasif gösterilir.

### 3.6 İlk aşamada kapsam dışı

- Bulut tabanlı çok kullanıcılı analiz.
- Tarayıcı tabanlı ana arayüz.
- Yapay zekâ ile otomatik arıza teşhisi.
- Tüm üretici formatlarını destekleyen genel amaçlı decoder.
- Sert gerçek zamanlı kontrol veya güvenlik-kritik cihaz komutu.

## 4. Kullanıcı rolleri ve temel senaryolar

### 4.1 Operatör

- Sistem sağlığını ve BIT sonuçlarını hızlıca görür.
- Aktif alarmı seçerek ilgili zaman aralığına gider.
- Transmisyon başlangıç/bitişlerini ve kanal davranışını birlikte inceler.

### 4.2 Test mühendisi

- Test kaydını açar ve kanal gruplarını karşılaştırır.
- Filtre/FFT/spektrogram uygular.
- Bölge seçer, ölçüm alır, açıklama ekler ve sonucu dışa aktarır.

### 4.3 Yazılım/donanım geliştiricisi

- Paket kaybı, CRC hatası, BIT değişimi ve sensör sapmasını aynı zaman çizgisinde inceler.
- Yeni `.bin` sürümü için decoder ekler.
- Ham ve ölçeklenmiş değeri karşılaştırır.

### 4.4 Ana kullanıcı akışı

1. Kullanıcı dosyayı açar.
2. Uygulama dosyayı tarar, formatı doğrular ve indeks oluşturur.
3. Data Explorer kanal ve olay ağacını gösterir.
4. Kullanıcı kanalı çift tıklar veya çalışma alanına sürükler.
5. Grafik görünür; seçili zaman aralığı için uygun çözünürlükte veri yüklenir.
6. BIT/transmisyon olayları aynı zaman ekseninde marker olarak gösterilir.
7. Kullanıcı olay veya anormal bölgeyi seçer, zoom yapar ve analiz uygular.
8. Sonucu grafik/veri/rapor olarak dışa aktarır veya çalışma alanını kaydeder.

## 5. Arayüz bilgi mimarisi

### 5.1 Ana pencere bölgeleri — referans mockup

**Görsel kabul kaynağı:** [SONAR Veri Analiz Panosu Mockup’ı.png](<SONAR Veri Analiz Panosu Mockup’ı.png>).

![Ana hedef SONAR veri analiz panosu](<SONAR Veri Analiz Panosu Mockup’ı.png>)

Görselin içindeki koyu uygulama penceresi tasarım hedefidir. Pencerenin dışındaki numaralı açıklama kutuları dokümantasyon katmanıdır. Veri değerleri, dosya adları, süreler ve kanal sayıları açılan kayıttan gelir; görseldeki örnek sayılar sabit uygulama verisi değildir.

Yaklaşık 1520 × 840 mantıksal piksel başlangıç penceresinde sol sütun 200 px, sağ sütun 300 px, merkez kalan alan olacak şekilde esnek düzen kurulacaktır. Dar pencere ve Windows DPI değişiminde ayırıcılar ve kaydırma alanları kullanılacak; metin ve eylemler erişilebilir kalacaktır.

| Mockup bölgesi | Uygulamadaki içerik | Varsayılan konum |
| --- | --- | --- |
| 1. Dosya ve Veri Yönetimi | Open .bin File, File/Size/Start/Duration/Platform özeti, Channels/Data Tree, arama ve kanal ağacı | Sol sütun |
| 2. Hızlı Araçlar | Pan, zoom, cursor, ölçüm, zaman penceresi, kanal seçimi ve Sync | Merkez grafiklerin üstü |
| 3. Görselleştirme Alanı | Üstte zaman serisi, ortada spektrogram, altta solda FFT ve sağda istatistik kartı | Merkez |
| 4. Donanım/BIT Durumu | Genel durum, son güncelleme, Run BIT Analysis ve alt sistem durum tablosu | Sağ üst |
| 5. Hesaplamalar ve Analiz | Filter, FFT, Statistics, Custom sekmeleri; parametreler ve uygulama eylemi | Sağ orta |
| 6. Çoklu Görünüm | Time Series, Spectrum, Spectrogram, Cross Analysis, BIT / Status, Transmission, 3D View, Report sekmeleri | Merkezin en üstü |
| 7. Zaman Kontrolü | Playback düğmeleri, hız, slider, geçen/toplam süre, Start/End ve Go | Grafiklerin altında |
| 8. Log / Mesajlar | Zaman damgalı işlem/hata mesajları; ayrı Events sekmesinde olay tablosu | Playback altında |
| 9. Ayarlar ve Dışa Aktarma | Export Format, selected time range, metadata ve Export Data; üstte ayarlar eylemi | Sağ alt / üst uygulama çubuğu |

Alt durum çubuğu Ready/işlem durumunu, bağlantı/kayıt bilgisini ve bellek kullanımını gösterir. Sağ BIT özeti, alt sistemlerden herhangi biri Warning/FAIL ise bunu yansıtır; genel durum metniyle alt tablo çelişmez.

Dock/panel yapısı taşınabilir ve kaydedilebilir olacak; varsayılan yerleşim bu mockup'a dönecektir. **Inspector**, kanal veya olay seçimiyle açılan bağlamsal araç sekmesidir; sağ sütundaki BIT, Analysis Tools ve Data Export kartlarının yerini kalıcı olarak almaz. BIT olaylarının ayrıntılı tablosu alt Events sekmesindedir.

`Run BIT Analysis` kayıtlı BIT verisini analiz eder veya özetini yeniler; donanıma test/kontrol komutu göndermez.

MVP kabulü yerleşim ve mevcut işlevleri; v2 kabulü FFT, spektrogram, filtre ve istatistikle çalışan ana analiz panosunu kapsar. Cross Analysis, 3D View ve otomatik Report işlevleri opsiyonel backlog'dadır. Grafik renklerinde XYZ için mavi/turuncu/yeşil eşlemesi kullanılır; spektrogram renk haritası okunabilir ve algısal olarak düzgün seçilir.

### 5.2 Data Explorer

Mockup'taki `Channels` ve `Data Tree` sekmeleri aynı kanal modelini kullanır. Ana gruplar `Sensors`, `Acoustic`, `Navigation`, `Vehicle / Transmission` ve `BIT` olacaktır; yalnız kaynakta bulunan kanallar seçilebilir.

Örnek hiyerarşi:

```text
Recording_2026_09_08.bin
├── Sensors
│   ├── Pressure
│   ├── Temperature
│   └── Accelerometer
│       ├── X
│       ├── Y
│       └── Z
├── Acoustic
│   ├── Hydrophone 1
│   └── Hydrophone 2
├── Navigation
│   ├── Position (GPS)
│   ├── Heading
│   └── Depth
├── Vehicle / Transmission
│   ├── RPM
│   ├── Voltage
│   └── TX State
├── BIT
│   ├── Power Supply
│   ├── Communication
│   └── Thermal
└── Derived
```

Yapılacaklar:

- [x] Lazy-loading destekli model/view tabanlı ağaç oluştur.  (`F3-009` ağaç modeli, `F3-010` lazy yükleme)
- [x] Kanal adına, ID’ye, birime ve kaynağa göre arama ekle.  (`F3-011`; dört alan da testlerle kapsandı)
- [x] `Sensors`, `BIT`, `Transmission`, `Derived` hızlı filtreleri ekle.  (`F3-012`)
- [x] Kanal türü, bağlantı durumu ve alarm seviyesi için ikon sistemi belirle.  (kanal türü ikonları `ui/status_icons.py` `CHANNEL_SOURCE_STYLES`; her ikon simge + metin taşır, ipucu kaynakta bulunma durumunu yazar)
- [x] Kanalı çift tıklama ve sürükle-bırak ile grafiğe ekle.  (`F3-013` çift tık, `F3-015` sürükle-bırak)
- [ ] Çoklu seçim ve “seçilenleri aynı grafikte/yeni grafiklerde aç” komutu ekle.  **AÇIK:** `F3-016` "aynı grafikte" kısmını verdi. "Ayrı grafiklerde" kısmı, Bölüm 5.3'teki **çoklu-panel altyapısına** bağlıdır (bkz. aynı bölümdeki "tab, split view" maddesi); ikisi tek iştir ve birlikte yapılmalıdır. Bugün `F4-082` grafiği ayrı pencereye **taşır**, yeni panel **üretmez**.
- [x] Favori kanal gruplarını kaydet.  (`F3-017`)
- [x] Sağ tık menüsü: Plot, Inspect, Add to Existing Plot, Export, Copy Path.  (beş eylem de bağlı: Plot · Inspect · Add to Existing Plot · Export · Copy Path)

### 5.3 Workspace ve grafik kartı

Varsayılan dashboard, mockup'taki dört hücreyi birlikte gösterir: zaman serisi, spektrogram, FFT ve istatistik. Genel amaçlı tab/split grafik açma bu başlangıç düzenini tamamlar. ROI ve kanal seçimi ilgili analiz hücrelerini ortak zaman aralığında günceller.

Her grafik panelinde şu öğeler bulunmalı:

- Başlık, kanal adı ve birim.
- Görünürlük, renk, çizgi kalınlığı ve eksen seçimi.
- X/Y zoom, pan, autoscale ve reset.
- Crosshair ve cursor değeri.
- İki cursor arasındaki `Δt`, `Δvalue`, frekans karşılığı.
- Region of Interest seçimi.
- Event marker görünürlüğü.
- Grafik ayarları ve dışa aktarma menüsü.
- İşlem sürüyorsa küçük ve müdahale etmeyen progress göstergesi.

Yapılacaklar:

- [x] `PlotPanel` temel bileşenini oluştur.  (`F1-031`; çoklu seri `F3-019`)
- [x] Birden fazla kanalı aynı panelde destekle.  (`F3-019`)
- [x] Sol/sağ Y ekseni veya ayrı eksen grupları desteğini değerlendir.  (`F3-020`: ikinci Y ekseni farklı birimli seriler için eklendi)
- [x] Tüm açık grafiklerde isteğe bağlı X-axis synchronization ekle.  (`F3-032`: araç çubuğundaki `Sync` anahtarı; durumu workspace ile saklanır)
- [x] Legend üzerinde kanal gizleme ve solo mode ekle.  (`F3-030`; `test_plot_legend_solo.py`)
- [ ] Grafiği tab, split view ve ayrı pencere olarak açmayı destekle.  **AÇIK:** Ayrı pencere var (`F4-082`, `test_detached_plot.py`) ama var olan paneli taşır. Sekme ve split view için **yeni `PlotPanel` üretebilen** bir kapsayıcı, X senkron gruplarının panel başına yönetimi ve workspace'e kaydı gerekir. Merkez yerleşimi `F6-031` mockup kabulünde ölçülüyor; bu iş o kabulü bozmadan yapılmalıdır. Bölüm 5.2'deki "ayrı grafiklerde aç" maddesi de buna bağlıdır.
- [x] Boş workspace için sürükle-bırak yönlendirmesi tasarla.  (`PlotPanel.EMPTY_PLOT_HINT`: boş grafikte sürükle-bırak yönlendirmesi görünür, seri eklenince kaybolur)
- [x] Grafik sayısı arttığında kaynak kullanımını sınırla.  (`F4-055` nokta bütçesi görünür piksel genişliğine göre örnek sayısını sınırlar; merkez yerleşimi sabit sayıda grafik taşır)

### 5.4 Inspector

Inspector, ana mockup yerleşimini koruyan bağlamsal araç görünümüdür. İstatistik özeti merkezdeki kartta da gösterilir.

Sekmeler:

- `Info`: kanal yolu, ID, dtype, unit, sample rate, source, timestamp kaynağı.
- `Display`: renk, görünürlük, line/scatter, eksen, min/max, autoscale.
- `Processing`: scaling, offset, calibration, filtre zinciri, resampling.
- `Statistics`: count, min, max, mean, median, RMS, std, peak-to-peak.
- `Raw`: ham paket/örnek gösterimi; yalnızca geliştirici modu.

Yapılacaklar:

- [x] Seçime göre içeriği dinamik güncelle.  (`F1-025`, `F3-035`, `F3-044`: seçilen kanal ve olay Inspector içeriğini günceller)
- [x] Değişiklikleri undo/redo sistemine bağla.  (`F3-041` görünüm ayarları, `F4-079` işlem zinciri ve işaretler)
- [x] İşlenmiş kanalın ham veriyi değiştirmediğini açıkça göster.  (`F4-005` ham dizi değişmez; `raw` dışa aktarma `variant=raw` ile ayrı yazılır)
- [x] Filtre sırasını sürükle-bırak ile değiştirmeyi destekle.  (`F4-006`: Analysis Tools listesinde adım ekleme, silme ve sıralama)
- [x] Geçersiz parametreleri çalıştırmadan önce doğrula.  (`F4-007`: geçersiz değer işlem başlamadan alanda açıklanır)

### 5.5 BIT, Events ve Transmission paneli

Sağ üstte mockup'ın BIT/System Status kartı bulunur. Ayrıntılı ortak event tablosu alt Log/Messages alanının Events sekmesinde açılır; Transmission ana sekmesi TX aralıklarını gösterir.

Ortak event tablosu sütunları:

| Alan | Açıklama |
| --- | --- |
| Time | Kayıt başlangıcına göre ve mutlak zaman |
| Severity | Info, Warning, Error, Critical |
| Category | BIT, TX, packet, system, user annotation |
| Source | Donanım veya yazılım bileşeni |
| Code | Makinece okunabilir olay kodu |
| State | PASS/FAIL/UNKNOWN veya önceki → yeni |
| Message | İnsan tarafından okunabilir açıklama |
| Value | Opsiyonel ölçüm ve birim |

Yapılacaklar:

- [x] Zaman, kategori, severity, source ve metin filtreleri ekle.  (`F3-043` zaman/severity/kaynak/metin, `F2-035` kategori sorgusu)
- [x] Severity renklerini yalnızca renge bağlı bırakma; ikon ve metin de kullan.  (`ui/status_icons.py`: severity hem ikon hem metin taşır, yalnız renge bağlı değil)
- [x] Satıra çift tıklayınca tüm senkronize grafikleri ilgili zamana götür.  (`F3-046`)
- [x] Event seçildiğinde Inspector’da detay ve ilişkili kanalları göster.  (`F3-044`)
- [x] Aynı veya çok yakın zamandaki tekrarları gruplayabil.  (`F3-049`)
- [x] PASS/FAIL/UNKNOWN için tutarlı durum bileşeni oluştur.  (`F1-014` PASS/FAIL/UNKNOWN modeli, `F3-051` BIT kartı ortak durum bileşeni)
- [x] TX START/STOP aralıklarını grafik üzerinde gölgeli bölge olarak gösterebil.  (`F3-047`)

### 5.6 Timeline ve playback

- Tüm kayıt aralığını gösteren overview timeline.
- Görünür viewport’u temsil eden seçilebilir bölge.
- Event yoğunluğu/severity işaretleri.
- Play, pause, stop, önceki/sonraki event.
- Oynatma hızı: `0.25x`, `0.5x`, `1x`, `2x`, `5x`, `10x`.
- Zaman alanına giderek belirli timestamp’e atlama.

Yapılacaklar:

- [x] Playback durum makinesini UI’dan bağımsız geliştir.  (`F3-056`: durum makinesi GUI olmadan doğrulanır)
- [x] Scrubbing sırasında ağır analizleri debounce et.  (`F3-060`)
- [x] Viewport değişimini tüm senkronize panellere yayınla.  (`F3-055`, `F3-032`)
- [x] Dosya zamanı, UTC ve elapsed time gösterimlerini destekle.  (`F3-061`: UTC, yerel ve geçen süre aynı kanonik anı gösterir)

## 6. Görsel tasarım sistemi

### 6.1 Tasarım ilkeleri

- Yoğun bilgi göster fakat görsel gürültü üretme.
- Ana analiz alanını daima en büyük alan olarak koru.
- Kritik durumları belirgin yap; normal PASS durumları ekranı kaplamasın.
- Aynı kanal ve durum rengi uygulamanın her yerinde tutarlı olsun.
- Renk tek başına anlam taşımasın.
- Operatörün sık kullandığı işlemler en fazla iki etkileşim uzakta olsun.

### 6.2 Önerilen koyu tema tokenları

| Token | Öneri | Kullanım |
| --- | --- | --- |
| Background | `#0B1118` | Ana pencere |
| Surface | `#121B24` | Panel/kart |
| Surface elevated | `#182430` | Menü/hover |
| Border | `#2B3A48` | Ayırıcılar |
| Primary text | `#E6EDF3` | Ana metin |
| Secondary text | `#94A3B8` | Metadata |
| Accent | `#1689F5` | Mockup'taki mavi seçim ve ana eylem vurgusu |
| Pass | `#39C77A` | Başarılı durum |
| Warning | `#F2B84B` | Uyarı |
| Error | `#EF5B5B` | Hata |
| Critical | `#D946EF` | Kritik alarm |

### 6.3 Grafik renkleri

- Renk körlüğüne daha dayanıklı, en az 8 kanallı sabit palet oluştur.
- Aynı kanal workspace boyunca aynı rengi korusun.
- Çok kanallı grafikte çizgi stili ve marker ikinci ayırt edici unsur olsun.
- Grid düşük kontrastlı; veri çizgileri ve event marker’ları daha yüksek kontrastlı olsun.
- Spektrogram için algısal olarak düzgün colormap kullan; `jet/rainbow` varsayılan olmasın.

### 6.4 Erişilebilirlik ve kullanım

- [x] Minimum metin kontrastını kontrol et.  (`F1-029` tema kontrastı, `F3-074` kontrast kontrolü; `tests/unit/test_theme.py`)
- [x] %100, %125, %150 ve %200 Windows ölçeklemede test et.  (`F3-074`; `tests/gui/test_dpi_scaling.py` dört ölçeği kapsar)
- [x] Sadece klavyeyle temel navigasyonu destekle.  (`F3-072` kısayollar, `F3-073` odak sırası: ana akış yalnız klavyeyle tamamlanır)
- [x] Tooltip yerine kalıcı açıklama gereken kritik terimleri etiketle.  (`F3-073`: kritik terimler kalıcı etiketle açıklanır, yalnız tooltip'e bırakılmaz)
- [x] Kritik eylemlerde durum geri bildirimi ver.  (`F1-028` durum çubuğu alanları; `F3-053` zaman damgalı log mesajları)
- [x] Yanlışlıkla uzun işlem başlatılırsa iptal olanağı sun.  (`F3-003` yükleme, `F3-066` export, `F4-004` DSP: üçü de iptal edilebilir)

## 7. Teknik mimari

### 7.1 Katmanlar

```text
Input Sources
  ├─ BIN files
  ├─ UDP/TCP stream
  └─ Serial/other adapters
          ↓
Readers + Format Detection
          ↓
Decoder / Validation / Indexing
          ↓
Normalized Domain Model
          ↓
Data Repository + Time Query API
          ↓
Processing Pipeline + Cache
          ↓
Application Services / Commands
          ↓
PySide6 ViewModels + UI + PyQtGraph
```

Temel kural: GUI, `.bin` byte düzenini veya paket yapısını bilmeyecektir. GUI yalnızca repository/query arayüzü ve domain modelleriyle konuşacaktır.

### 7.2 Önerilen proje dizini

```text
sonar_analyzer/
├── pyproject.toml
├── README.md
├── docs/
│   ├── bin-format.md
│   ├── architecture.md
│   └── ui-guidelines.md
├── src/sonar_analyzer/
│   ├── app.py
│   ├── domain/
│   │   ├── channel.py
│   │   ├── event.py
│   │   ├── recording.py
│   │   └── time_range.py
│   ├── io/
│   │   ├── readers/
│   │   ├── decoders/
│   │   ├── index/
│   │   └── live/
│   ├── repository/
│   │   ├── recording_repository.py
│   │   └── query_service.py
│   ├── processing/
│   │   ├── pipeline.py
│   │   ├── filters.py
│   │   ├── spectral.py
│   │   ├── resampling.py
│   │   └── cache.py
│   ├── application/
│   │   ├── commands/
│   │   ├── services/
│   │   ├── playback.py
│   │   └── workspace.py
│   ├── ui/
│   │   ├── main_window.py
│   │   ├── models/
│   │   ├── viewmodels/
│   │   ├── docks/
│   │   ├── plots/
│   │   ├── dialogs/
│   │   ├── widgets/
│   │   ├── themes/
│   │   └── resources/
│   ├── export/
│   ├── settings/
│   ├── logging/
│   └── plugins/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── gui/
│   ├── performance/
│   └── fixtures/
└── tools/
    ├── bin_inspector/
    └── fixture_generator/
```

### 7.3 Domain veri modeli

Örnek veri sözleşmeleri:

```python
@dataclass(frozen=True)
class ChannelMetadata:
    id: str
    path: str
    name: str
    unit: str | None
    dtype: str
    sample_rate_hz: float | None
    source: str
    time_base_id: str
    calibration_id: str | None = None

@dataclass(frozen=True)
class DataChunk:
    channel_id: str
    timestamps_ns: NDArray[np.int64]
    values: NDArray
    quality: NDArray[np.uint8] | None = None

@dataclass(frozen=True)
class Event:
    timestamp_ns: int
    source: str
    category: str
    severity: str
    code: str
    message: str
    state: str | None = None
    value: float | str | None = None
    unit: str | None = None
```

Ek modeller:

- `RecordingMetadata`: kayıt ID, başlangıç/bitiş, format sürümü, cihaz bilgisi.
- `TimeRange`: başlangıç/bitiş ve doğrulama.
- `TransmissionInterval`: start, stop, frequency, power, mode ve status.
- `BitResult`: test ID, component, expected, actual, state ve detail.
- `Annotation`: kullanıcı açıklaması, zaman veya aralık, etiket ve renk.
- `DerivedChannelDefinition`: giriş kanalları, işlem zinciri ve çıktı metadata.

### 7.4 Veri erişim API’si

GUI’nin kullanacağı örnek arayüz:

```python
class RecordingRepository(Protocol):
    def metadata(self) -> RecordingMetadata: ...
    def channels(self) -> Sequence[ChannelMetadata]: ...
    def query(
        self,
        channel_id: str,
        time_range: TimeRange,
        max_points: int | None = None,
    ) -> DataChunk: ...
    def events(
        self,
        time_range: TimeRange,
        filters: EventFilter | None = None,
    ) -> Sequence[Event]: ...
```

`max_points` görünür piksel genişliğiyle ilişkilendirilmeli; repository uygun downsample seviyesini döndürmelidir. Böylece milyonlarca nokta doğrudan grafik nesnesine gönderilmez.

## 8. `.bin` okuma ve decoder planı

Gerçek format dokümanı gelene kadar iki örnek profil referans alınır. İkisi de 125 ms periyotlu `Data00000`, `Data00001`, … kayıt zincirini kullanır:

- **Profil A (8.2):** sabit 64 baytlık, kayıt başına kanal başına tek anlık değer taşıyan minimal telemetri düzeni. Trend, durum ve BIT/TX izleme için yeterlidir; offset aritmetiği sabittir.
- **Profil B (8.3):** kayıt başına 125 ms'lik ham örnek bloklarını taşıyan blok tabanlı (TLV) düzen. FFT/PSD/spektrogram gibi spektral analizin gerektirdiği profildir.

Parser her iki profili de `format detection` ile ayırt edecek biçimde tasarlanır; gerçek format netleştiğinde hangisine yakın olduğu belirlenip tek profil sürdürülür.

### 8.1 Ön analiz

- [ ] Format dokümanlarını ve örnek kayıtları topla.  **AÇIK:** Sentetik fixture'lar toplandı (`F0-009`, `F0-010`); **gerçek kayıt ve resmî doküman yok** (`E-01`, `E-02`, `K-01`, `K-02`).
- [x] Magic bytes, header, sürüm, endian, alignment ve paket yapılarını belgeleyin.  (`F0-004`, `F0-005`; `docs/format/profile-a.md`, `profile-b.md`, `docs/format/decoder-guide.md`)
- [x] Timestamp kaynağını ve çözünürlüğünü belirle.  (`F0-011`, `ADR-003`: kanonik `int64` UTC ns, 125 ms kayıt ızgarası)
- [x] Sensör, BIT, TX ve event paket türlerini listele.  (`F0-005` sensör/BIT/TX alanları, `F0-007` kanal grupları; Profil B blok türleri `io/profile_b_format.py`)
- [x] CRC/checksum algoritmasını netleştir.  (`F0-008`, `ADR-011`: CRC-32/ISO-HDLC, kendi alanı hariç kapsam)
- [x] Eksik/bozuk paket davranışını tanımla.  (`F0-010` senaryolar, `F2-017` fixture'lar, `F2-015` bilinmeyen paket teşhisi)
- [x] Ölçekleme, calibration, signed/unsigned ve unit dönüşümlerini doğrula.  (`F2-020` scale/offset, `F2-021` calibration ve kalite eşlemesi; `raw` dışa aktarma dönüşümü ters çevirir)
- [ ] Farklı firmware/format sürümlerinin uyumluluk tablosunu çıkar.  **AÇIK:** Desteklenen sürümler tablolandı (`docs/format/decoder-guide.md` §1, `inventory.md` §4); **firmware sürüm listesi gelmedi** (`E-08`, `K-06`).

### 8.2 Örnek `.bin` dosya formatı — Profil A: sabit 64 baytlık kayıt

Bu örnekte tek bir `.bin` dosyasına **125 ms'de bir kayıt** eklenir; saniyede **8 kayıt** oluşur. Dosya içindeki kayıtlar `Data00000`, `Data00001`, `Data00002`, … olarak adlandırılır. İlk kayıt zamanı `t = 0 ms`, sonraki kayıtların zamanı `t(n) = n × 125 ms` olur.

**Dosyanın genel düzeni:**

```text
Recording_2026_09_08.bin
┌──────────────────────────────────────────────────────────────┐
│ FILE HEADER (32 byte)                                         │
│ Magic | Version | Header size | Record size | Period          │
│ Channel count | Start time (UTC)                              │
├──────────────────────────────────────────────────────────────┤
│ Data00000 (64 byte) │ sıra: 0 │ t =    0 ms │ Sensör + BIT + TX│
├──────────────────────────────────────────────────────────────┤
│ Data00001 (64 byte) │ sıra: 1 │ t =  125 ms │ Sensör + BIT + TX│
├──────────────────────────────────────────────────────────────┤
│ Data00002 (64 byte) │ sıra: 2 │ t =  250 ms │ Sensör + BIT + TX│
├──────────────────────────────────────────────────────────────┤
│ Data00003 (64 byte) │ sıra: 3 │ t =  375 ms │ Sensör + BIT + TX│
├──────────────────────────────────────────────────────────────┤
│ ...                                                          │
├──────────────────────────────────────────────────────────────┤
│ Data00007 (64 byte) │ sıra: 7 │ t =  875 ms │ Sensör + BIT + TX│
├──────────────────────────────────────────────────────────────┤
│ Data00008 (64 byte) │ sıra: 8 │ t = 1000 ms │ Sensör + BIT + TX│
└──────────────────────────────────────────────────────────────┘

Zaman (ms):      0          125         250         375
                │──125 ms──│──125 ms──│──125 ms──│
Kayıt:      Data00000   Data00001   Data00002   Data00003
```

**File header (32 byte):** Offsetler dosya başlangıcına göredir. Çok byte'lı sayısal alanlar `little-endian`, kayan noktalı değerler IEEE 754 `float32` olarak saklanır. Alanlar arasında örtük hizalama/padding yoktur.

| Offset (byte) | Alan | Tip | Boyut (byte) | Örnek / açıklama |
| --- | --- | --- | --- | --- |
| 0 | `magic` | `char[8]` | 8 | ASCII `SONARBIN` |
| 8 | `version` | `uint16` | 2 | `1` |
| 10 | `header_size` | `uint16` | 2 | `32` |
| 12 | `record_size` | `uint32` | 4 | `64` |
| 16 | `period_us` | `uint32` | 4 | `125000` µs = 125 ms |
| 20 | `channel_count` | `uint32` | 4 | `8` |
| 24 | `start_time_utc_ns` | `uint64` | 8 | Unix epoch'tan itibaren UTC nanosecond |

**Her `DataNNNNN` kaydı (64 byte):** Offsetler ilgili kaydın başlangıcına göredir. Bu örnekte her kayıtta 8 sensör kanalının birer anlık değeri ve o andaki BIT/TX durumu bulunur.

```text
Byte:  0            12      16          24                  56     60     64
       ┌────────────┬───────┬───────────┬───────────────────┬──────┬──────┐
       │ name       │ seq   │ elapsed_us│ sensor_values[8]  │ BIT  │ TX   │
       │ 12 byte    │ 4 byte│ 8 byte    │ 32 byte           │ 4 B  │ 4 B  │
       └────────────┴───────┴───────────┴───────────────────┴──────┴──────┘
```

| Offset (byte) | Alan | Tip | Boyut (byte) | Örnek / açıklama |
| --- | --- | --- | --- | --- |
| 0 | `name` | `char[12]` | 12 | ASCII `Data00000`; kalan byte'lar `0x00` |
| 12 | `sequence_no` | `uint32` | 4 | `0`, `1`, `2`, … |
| 16 | `elapsed_us` | `uint64` | 8 | `0`, `125000`, `250000`, … |
| 24 | `sensor_values` | `float32[8]` | 32 | Sabit kanal sırasıyla CH0–CH7 değerleri |
| 56 | `bit_status` | `uint32` | 4 | Örnek bit maskesi: bit 0–31 ilgili testin FAIL durumu; `0` tümü PASS |
| 60 | `tx_status` | `uint32` | 4 | Örnek durum kodu: `0 = IDLE`, `1 = ACTIVE`, `2 = FAULT` |

Kayıt ve okuma kuralları:

- İsim, sıra numarasından en az 5 haneli sıfır dolgusu ile üretilir: `Data{sequence_no:05d}`. `Data99999` sonrasında `Data100000` gelir; numara sıfırlanmaz. `char[12]` alanı en fazla `Data9999999` ve sonlandırıcı sıfırı alır; bu sınır aşılmadan yeni dosyaya geçilir.
- Kayıpsız dosyada sıfır tabanlı `n` numaralı kaydın dosya offseti `32 + n × 64` byte'tır. Mutlak zaman `start_time_utc_ns + elapsed_us × 1000` ile hesaplanır.
- İlk bir saniyelik `[0, 1000 ms)` aralıkta `Data00000`–`Data00007` bulunur. Bu 8 kaydı içeren dosya boyutu `32 + 8 × 64 = 544 byte` olur.
- Periyot kaçırılırsa sıra numarası ve zaman ilgili periyoda göre ilerler; eksik kayıt decoder tarafından zaman boşluğu olarak gösterilir. Bu durumda fiziksel kayıt konumu ile `sequence_no` aynı olmayabilir.
- **125 ms kayıt periyodu, ham SONAR örnekleme periyodu olmak zorunda değildir.** Buradaki anlık değer örneğinde her kanal 8 Hz ile kaydedilir. Ham akustik veri için her `Data` kaydı 125 ms boyunca toplanan örnek bloğunu taşımalı; kanal başına örnek sayısı, sample rate ve payload boyutu ayrıca tanımlanmalıdır. Bu profil 8.3'te tanımlanmıştır.
- Bu şema örnek taslaktır. Kanal adları/birimleri, BIT test eşlemesi ve CRC/checksum alanı gerçek format sözleşmesinde netleştirilmeli; alan eklenirse sürüm, boyut ve offsetler birlikte güncellenmelidir.

### 8.3 Örnek `.bin` dosya yerleşimi — Profil B: blok tabanlı ham akustik kayıt

Profil A kayıt başına kanal başına tek değer taşıdığı için 8 Hz'in üzerindeki sinyalleri temsil edemez. Bu profil aynı 125 ms'lik kayıt ızgarasını korur, ancak her kayıtta o pencerede toplanan **örnek bloklarını** taşır; böylece 96 kHz'lik hidrofon verisi kayıt sınırlarında sürekli kalır.

Aşağıdaki yerleşim, gerçek format dokümanı gelene kadar parser, indeksleyici, sentetik veri üretici ve testleri geliştirmek için kullanılacak **referans taslaktır**. Nihai format bundan farklı olabilir; bu nedenle dosya başlığında sürüm alanı ve kayıt içinde blok tabanlı (TLV) yapı zorunludur.

Taslağın temel kabulleri:

- Veriler **125 ms sabit periyotlu kayıt (record) blokları** hâlinde yazılır → 8 kayıt/saniye.
- Her kaydın dosya içinde okunabilir ASCII adı vardır: `Data00000`, `Data00001`, `Data00002`, …
- Tüm çok baytlı alanlar **little-endian**dır.
- Bir bloğun kapladığı toplam alan 8 bayta hizalanır; artan baytlar sıfırla doldurulur.
- Mutlak zaman yalnızca dosya başlığında (`t0_utc_ns`) bulunur; kayıtlar bu ankora göre **offset** taşır.
- Bir kayıt, o 125 ms'lik pencereye ait tüm kaynakları (sensör, IMU, TX, BIT, event) birlikte taşır.

#### 8.3.1 Dosya genel yerleşimi

```text
┌───────────────────────────────────────────────────────────────────────────┐
│ FileHeader — 256 B                                                        │
│  magic "SNRBIN\x1A\x00" │ ver 1.0 │ t0_utc_ns │ record_period_us = 125000 │
├───────────────────────────────────────────────────────────────────────────┤
│ ChannelTable — N x 64 B                                                   │
│  [ch0][ch1][ch2] … [chN-1]   (id, ad, birim, fs, gain/offset)             │
├───────────────────────────────────────────────────────────────────────────┤
│ RecordArea — dosyanın ~%99'u                                              │
│                                                                           │
│  ┌─ "Data00000"   t = t0 + 0 ms ────────────────────────────────────────┐ │
│  │ RecordHeader (48 B)                                                  │ │
│  │  ├─ Block SENSOR_RAW   ch 0   12000 x int16   (16 + 24000 B)         │ │
│  │  ├─ Block SENSOR_RAW   ch 1   12000 x int16                          │ │
│  │  ├─ Block SENSOR_RAW   ch 2   12000 x int16                          │ │
│  │  ├─ Block SENSOR_RAW   ch 3   12000 x int16                          │ │
│  │  ├─ Block NAV_IMU      ch 10  25 x float32    (16 + 100 + 4 pad)     │ │
│  │  ├─ Block NAV_IMU      ch 11  25 x float32                           │ │
│  │  ├─ Block NAV_IMU      ch 12  25 x float32                           │ │
│  │  ├─ Block TX_STATUS    ch 20  1 x struct24    (16 + 24 B)            │ │
│  │  ├─ Block BIT_STATUS   ch 30  12 x struct12   (yalnız 1 Hz kayıtta)  │ │
│  │  └─ Block EVENT_LOG    ch 40  değişken        (yalnız olay varsa)    │ │
│  │ RecordTrailer (8 B): crc32 + "ENDR"                                  │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│  ┌─ "Data00001"   t = t0 + 125 ms ──────────────────────────────────────┐ │
│  │ … aynı yapı …                                                        │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│  ┌─ "Data00002"   t = t0 + 250 ms ──────────────────────────────────────┐ │
│  │ …                                                                    │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
├───────────────────────────────────────────────────────────────────────────┤
│ RecordIndex — M x 32 B (opsiyonel)                                        │
│  record_index → dosya offset + zaman + boyut + flag                       │
├───────────────────────────────────────────────────────────────────────────┤
│ FileFooter — 32 B                                                         │
│  "SNREOF00" │ record_count │ index_crc32 │ file_crc32                     │
└───────────────────────────────────────────────────────────────────────────┘
```

#### 8.3.2 FileHeader (256 bayt, sabit)

| Offset | Alan | Tip | Örnek değer / açıklama |
| --- | --- | --- | --- |
| 0x00 | `magic` | `char[8]` | `53 4E 52 42 49 4E 1A 00` → `"SNRBIN\x1A\x00"` |
| 0x08 | `version_major` | `uint16` | `1` |
| 0x0A | `version_minor` | `uint16` | `0` |
| 0x0C | `endian_mark` | `uint16` | `0xFEFF` (little-endian okunduğunda doğru görünür) |
| 0x0E | `header_size` | `uint16` | `256` |
| 0x10 | `flags` | `uint32` | bit0 indeks var, bit1 CRC etkin, bit2 kayıt adları ASCII, bit3 kayıt tamamlanmadı (canlı kesinti) |
| 0x14 | `record_period_us` | `uint32` | **`125000`** → nominal kayıt periyodu |
| 0x18 | `record_count` | `uint32` | Yazılan kayıt sayısı (tamamlanmamış kayıtta `0`) |
| 0x1C | `first_record_index` | `uint32` | `0` → ilk kaydın adı `Data00000` |
| 0x20 | `record_name_prefix` | `char[8]` | `"Data"` (null-padded) |
| 0x28 | `record_name_digits` | `uint8` | `5` → `Data%05d` |
| 0x29 | `time_source` | `uint8` | `0` bilinmiyor, `1` GPS/PPS, `2` PTP, `3` yerel osilatör |
| 0x2A | `channel_count` | `uint16` | `8` |
| 0x2C | `channel_table_offset` | `uint32` | `256` |
| 0x30 | `channel_entry_size` | `uint16` | `64` |
| 0x32 | `reserved0` | `uint16` | `0` |
| 0x34 | `first_record_offset` | `uint32` | `256 + 8*64 = 768` |
| 0x38 | `t0_utc_ns` | `int64` | `Data00000`'ın başlangıcı, Unix epoch UTC nanosaniye |
| 0x40 | `device_tick_hz` | `uint64` | `10000000` → ham `device_ticks` alanının frekansı |
| 0x48 | `index_offset` | `uint64` | `RecordIndex` başlangıcı; indeks yoksa `0` |
| 0x50 | `index_size` | `uint32` | Bayt cinsinden indeks boyutu |
| 0x54 | `reserved1` | `uint32` | `0` |
| 0x58 | `recording_id` | `byte[16]` | UUIDv4 |
| 0x68 | `device_id` | `char[16]` | `"SONAR-UNIT-01"` |
| 0x78 | `firmware_version` | `char[16]` | `"FW 2.4.1"` |
| 0x88 | `reserved2` | `byte[116]` | `0` — ileri sürümler için |
| 0xFC | `header_crc32` | `uint32` | 0x00–0xFB aralığının CRC32'si |

#### 8.3.3 ChannelTable girdisi (64 bayt/kanal)

| Offset | Alan | Tip | Açıklama |
| --- | --- | --- | --- |
| 0x00 | `channel_id` | `uint16` | Bloklardaki `channel_id` ile eşleşir |
| 0x02 | `source_code` | `uint8` | `1` SONAR, `2` NAV, `3` TX, `4` BIT, `5` EVENT, `6` DERIVED |
| 0x03 | `dtype` | `uint8` | Bkz. 8.3.5 dtype tablosu |
| 0x04 | `name` | `char[24]` | `"SONAR/Array1/Hyd01/Raw"` — Data Explorer yolunu üretir |
| 0x1C | `unit` | `char[8]` | `"Pa"`, `"deg"`, `"W"`, `"Hz"` |
| 0x24 | `sample_rate_hz` | `float32` | `96000.0` |
| 0x28 | `gain` | `float32` | `physical = raw * gain + offset` |
| 0x2C | `offset` | `float32` | |
| 0x30 | `samples_per_record` | `uint16` | `12000` (nominal; gerçek değer bloktan hesaplanır) |
| 0x32 | `flags` | `uint16` | bit0 kalibre, bit1 ters polarite, bit2 devre dışı |
| 0x34 | `reserved` | `byte[12]` | `0` |

Örnek kanal listesi (bu taslaktaki 8 kanal):

| id | source | name | unit | fs (Hz) | örnek/kayıt | dtype |
| --- | --- | --- | --- | --- | --- | --- |
| 0–3 | SONAR | `SONAR/Array1/Hyd01..04/Raw` | Pa | 96000 | 12000 | `int16` |
| 10 | NAV | `Navigation/IMU/Roll` | deg | 200 | 25 | `float32` |
| 11 | NAV | `Navigation/IMU/Pitch` | deg | 200 | 25 | `float32` |
| 12 | NAV | `Navigation/IMU/Yaw` | deg | 200 | 25 | `float32` |
| 20 | TX | `Transmission/Status` | — | 8 | 1 | `struct` |
| 30 | BIT | `BIT/Summary` | — | 1 | 12 | `struct` |
| 40 | EVENT | `Events/System` | — | — | değişken | `struct` |

`channel_id` 20/30/40 fiziksel sensör değil, mantıksal kaynaktır; bu girdiler yalnızca ad, birim ve görüntüleme bilgisi taşır.

#### 8.3.4 RecordHeader (48 bayt)

| Offset | Alan | Tip | Açıklama |
| --- | --- | --- | --- |
| 0x00 | `name` | `char[12]` | `"Data00000"` + null padding — dosyada düz metin olarak aranabilir |
| 0x0C | `record_index` | `uint32` | Monoton artan **asıl** kayıt numarası; sıralamada bu alan yetkilidir |
| 0x10 | `record_size` | `uint32` | Header + bloklar + trailer; 8 bayta hizalı toplam |
| 0x14 | `block_count` | `uint16` | Bu kayıttaki blok sayısı |
| 0x16 | `flags` | `uint16` | bit0 VALID, bit1 GAP_BEFORE, bit2 PARTIAL, bit3 RESYNC, bit4 CLOCK_UNLOCKED |
| 0x18 | `t_start_offset_ns` | `int64` | `t0_utc_ns`'e göre kayıt başlangıcı → nominal `record_index * 125_000_000` |
| 0x20 | `device_ticks` | `uint64` | Ham cihaz sayacı (drift/jitter analizi ve doğrulama için korunur) |
| 0x28 | `seq` | `uint32` | Yazıcı tarafındaki sıra numarası; kayıp kayıt tespiti |
| 0x2C | `reserved` | `uint32` | `0` |

Kaydın sonunda **RecordTrailer (8 B)**: `crc32` (`uint32`, header + blokların CRC32'si) ve `end_marker` (`char[4]` = `"ENDR"`).

#### 8.3.5 BlockHeader (16 bayt) ve blok türleri

```text
 0        2        4                8        10   11   12            16
 ├────────┼────────┼────────────────┼────────┼────┼────┼─────────────┤
 │ type   │ flags  │ block_size     │ ch_id  │dtyp│rsv │ t_offset_ns │  payload →
 │ uint16 │ uint16 │ uint32         │ uint16 │ u8 │ u8 │ int32       │
 └────────┴────────┴────────────────┴────────┴────┴────┴─────────────┘
```

- `block_size`: yalnız payload baytları; 16 baytlık başlık **dahil değil**.
- `t_offset_ns`: bloğun ilk örneğinin kayıt başlangıcına göre kayması (±, ns).
- Sonraki bloğun konumu: `next = align8(cur + 16 + block_size)`. Hizalama baytları sıfırdır, `block_size`'a girmez ama `record_size`'a girer.
- `sample_count` alanı **yoktur**; `sample_count = block_size / dtype_size` olarak türetilir ve tam bölünmesi doğrulanır.

Blok türleri:

| type | ad | payload | Bu taslaktaki sıklık |
| --- | --- | --- | --- |
| `0x0001` | `SENSOR_RAW` | kanal başına ham örnek dizisi | her kayıtta, kanal başına 1 |
| `0x0002` | `SENSOR_SCALED` | `float32` fiziksel birim dizisi | opsiyonel / derived |
| `0x0010` | `NAV_IMU` | `float32` dizisi | her kayıtta, eksen başına 1 |
| `0x0020` | `TX_STATUS` | 1 x `struct24` | her kayıtta 1 (8 Hz) |
| `0x0030` | `BIT_STATUS` | n x `struct12` | her 8. kayıtta (1 Hz): `Data00000`, `Data00008`, `Data00016`, … |
| `0x0040` | `EVENT_LOG` | değişken uzunlukta girdiler | yalnız olay varsa |
| `0x00F0` | `PAD` | sıfır dolgu / ayrılmış alan | hizalama veya blok yeniden yazımı |
| `0xFFxx` | `VENDOR/UNKNOWN` | opaque | atlanır; offset ve tür ile raporlanır |

dtype kodları:

| kod | tip | boyut |
| --- | --- | --- |
| `0x01` | `int16` | 2 |
| `0x02` | `int32` | 4 |
| `0x03` | `float32` | 4 |
| `0x04` | `float64` | 8 |
| `0x05` | `uint8` | 1 |
| `0x10` | `struct` | boyut `block_type`'a göre (TX 24, BIT 12, EVENT değişken) |

#### 8.3.6 Yapısal payload'lar

`TX_STATUS` (24 B):

| Alan | Tip | Açıklama |
| --- | --- | --- |
| `tx_state` | `uint8` | `0` IDLE, `1` ARMED, `2` TRANSMIT, `3` FAULT |
| `mode` | `uint8` | `0` CW, `1` LFM, `2` HFM |
| `reserved` | `uint16` | `0` |
| `frequency_hz` | `float32` | |
| `bandwidth_hz` | `float32` | |
| `power_w` | `float32` | |
| `pulse_len_us` | `uint32` | |
| `status_bits` | `uint32` | interlock, VSWR alarmı, overtemp vb. |

7.3'teki `TransmissionInterval` bu ardışık durum örneklerinden türetilir: `IDLE/ARMED → TRANSMIT` geçişi START, `TRANSMIT → IDLE/FAULT` geçişi STOP kabul edilir. 125 ms örnekleme, aralık sınırlarının ±125 ms belirsizlikle bilindiği anlamına gelir; bu tolerans 9. bölümdeki korelasyon ayarına girdi olur.

`BIT_STATUS` girdisi (12 B, n girdi):

| Alan | Tip | Açıklama |
| --- | --- | --- |
| `test_id` | `uint16` | |
| `component_id` | `uint16` | PSU, amplifier, sensor array … |
| `state` | `uint8` | `0` PASS, `1` WARN, `2` FAIL, `3` NOT_RUN |
| `severity` | `uint8` | `0` info … `3` critical |
| `measured` | `float32` | Ölçülen değer |
| `code` | `uint16` | Hata/durum kodu |

`EVENT_LOG` girdisi (14 B başlık + mesaj, 4 bayta hizalı):

| Alan | Tip | Açıklama |
| --- | --- | --- |
| `entry_size` | `uint16` | Hizalama dahil toplam girdi boyutu |
| `t_offset_ns` | `int32` | Kayıt başlangıcına göre olay zamanı |
| `source_code` | `uint8` | |
| `category` | `uint8` | |
| `severity` | `uint8` | |
| `reserved` | `uint8` | |
| `code` | `uint16` | |
| `msg_len` | `uint16` | UTF-8 bayt sayısı |
| `msg` | `byte[msg_len]` | UTF-8; sonda null yok |
| `pad` | `byte[…]` | `entry_size` 4'ün katı olacak şekilde sıfır dolgu |

#### 8.3.7 RecordIndex (32 B/kayıt) ve FileFooter (32 B)

İndeks girdisi:

| Alan | Tip | Açıklama |
| --- | --- | --- |
| `record_index` | `uint32` | |
| `file_offset` | `uint64` | Kaydın dosya içindeki başlangıcı |
| `t_start_offset_ns` | `int64` | `t0_utc_ns`'e göre başlangıç |
| `record_size` | `uint32` | |
| `flags` | `uint32` | RecordHeader flag'leri + "bozuk bölge" biti |
| `reserved` | `byte[4]` | |

FileFooter: `magic` `char[8]` = `"SNREOF00"`, `record_count` `uint32`, `index_entry_size` `uint16`, `flags` `uint16`, `index_crc32` `uint32`, `file_crc32` `uint32`, `reserved` `byte[8]`.

İndeks ve footer **türetilmiş** veridir: yoksa veya CRC'si hatalıysa 8.5'teki tarama ile yeniden üretilir. Kaynak `.bin` değişmediyse uygulama kendi indeks önbelleğini kullanır.

#### 8.3.8 Zaman ve adlandırma kuralları

- Nominal ızgara: `t_start_utc_ns(k) = t0_utc_ns + k * 125_000_000`, burada `k = record_index - first_record_index`.
- Kayıt adı yalnızca **etiket**tir: `name = prefix + f"{record_index:0{digits}d}"`.
- Ad **sarmaz**: `record_name_digits` asgari hane sayısıdır; `Data99999`'dan sonra `Data100000` gelir ve ad dosya içinde benzersiz kalır. Sıralama, indeksleme ve korelasyonda yine **daima `record_index`** kullanılır; ad gösterim ve dosya içi arama içindir. Ortak kural: `docs/format/timing-and-naming.md` (`F0-006`).
- Örnek eşleme: `Data00000` → 0 ms, `Data00001` → 125 ms, `Data00008` → 1 s, `Data00480` → 60 s, `Data28800` → 1 saat.
- Örnek-içi zaman: `t(i) = t_start + t_offset_ns + round(i * 1e9 / sample_rate_hz)`.
- Gerçek zaman `device_ticks`'ten hesaplanır: `t_dev(k) = (ticks_k - ticks_0) / device_tick_hz`. Nominal ızgaradan sapma jitter/drift olarak raporlanır (bkz. 9. bölüm).
- Kayıp pencere: eksik 125 ms için kayıt **yazılmaz**. `record_index` atlaması boşluk demektir ve sonraki kayıtta `GAP_BEFORE` işaretlenir. Boşluk uydurma örnekle doldurulmaz; grafikte kesinti olarak gösterilir.

#### 8.3.9 Bir kaydın bayt bütçesi (örnek yapılandırma)

| Bileşen | Adet | Birim boyut | Toplam |
| --- | --- | --- | --- |
| RecordHeader | 1 | 48 | 48 |
| `SENSOR_RAW` (12000 x `int16`) | 4 | 16 + 24000 = 24016 | 96.064 |
| `NAV_IMU` (25 x `float32`) | 3 | 16 + 100 + 4 pad = 120 | 360 |
| `TX_STATUS` | 1 | 16 + 24 = 40 | 40 |
| RecordTrailer | 1 | 8 | 8 |
| **Kayıt toplamı** | | | **96.520 B** (8'e hizalı) |

Buradan çıkan veri hızı:

- 8 kayıt/s → **~754 KiB/s**
- ~**44 MiB/dakika**, ~**2,59 GiB/saat**
- 1 saatlik kayıt ≈ **28.800 kayıt** (`Data00000` … `Data28799`)

Bu değerler 11. bölümdeki performans bütçesinin ve indeks tasarımının doğrulama girdisidir. Her 8. kayıttaki `BIT_STATUS` (16 + 144 = 160 B) ve seyrek `EVENT_LOG` blokları toplamı ihmal edilebilir düzeyde artırır.

#### 8.3.10 Hexdump örneği — `Data00001` kaydının başı

```text
offset    bytes                                             anlam
--------  ------------------------------------------------  --------------------------------
+0x0000   44 61 74 61 30 30 30 30 31 00 00 00               name = "Data00001"
+0x000C   01 00 00 00                                       record_index = 1
+0x0010   08 79 01 00                                       record_size = 96520
+0x0014   08 00                                             block_count = 8
+0x0016   01 00                                             flags = VALID
+0x0018   40 59 73 07 00 00 00 00                           t_start_offset_ns = 125.000.000
+0x0020   D0 12 13 00 00 00 00 00                           device_ticks = 1.250.000 (10 MHz)
+0x0028   01 00 00 00                                       seq = 1
+0x002C   00 00 00 00                                       reserved
--- blok 0 ---------------------------------------------------------------------------------
+0x0030   01 00                                             block_type = SENSOR_RAW
+0x0032   00 00                                             block_flags = 0
+0x0034   C0 5D 00 00                                       block_size = 24000
+0x0038   00 00                                             channel_id = 0  (Hyd01/Raw)
+0x003A   01                                                dtype = int16 → 12000 örnek
+0x003B   00                                                reserved
+0x003C   00 00 00 00                                       t_offset_ns = 0
+0x0040   .. .. .. .. …                                     24000 B int16 örnek verisi
--- blok 1 ---------------------------------------------------------------------------------
+0x5E00   01 00 00 00 C0 5D 00 00 01 00 01 00 00 00 00 00   SENSOR_RAW, channel_id = 1
+0x5E10   .. .. .. .. …                                     24000 B
--- bloklar 2..7 ---------------------------------------------------------------------------
          SENSOR_RAW ch2, ch3 → NAV_IMU ch10, ch11, ch12 → TX_STATUS ch20
--- kayıt sonu -----------------------------------------------------------------------------
+0x17900  3C 8A 5E B1                                       crc32 (header + bloklar)
+0x17904  45 4E 44 52                                       "ENDR"
+0x17908  44 61 74 61 30 30 30 30 32 …                      "Data00002" burada başlar
```

#### 8.3.11 Python `struct` sözleşmeleri

```python
import struct

FILE_MAGIC = b"SNRBIN\x1a\x00"
END_MARKER = b"ENDR"
RECORD_PERIOD_NS = 125_000_000

FILE_HEADER    = struct.Struct("<8sHHHHIIII8sBBHIHHIqQQII16s16s16s116sI")  # 256 B
CHANNEL        = struct.Struct("<HBB24s8sfffHH12s")                        #  64 B
RECORD_HEADER  = struct.Struct("<12sIIHHqQII")                             #  48 B
BLOCK_HEADER   = struct.Struct("<HHIHBBi")                                 #  16 B
TX_STATUS      = struct.Struct("<BBHfffII")                                #  24 B
BIT_ENTRY      = struct.Struct("<HHBBfH")                                  #  12 B
EVENT_HEADER   = struct.Struct("<HiBBBBHH")                                #  14 B + msg + pad
RECORD_TRAILER = struct.Struct("<I4s")                                     #   8 B
INDEX_ENTRY    = struct.Struct("<IQqII4s")                                 #  32 B

DTYPE_SIZE  = {0x01: 2, 0x02: 4, 0x03: 4, 0x04: 8, 0x05: 1}
NUMPY_DTYPE = {0x01: "<i2", 0x02: "<i4", 0x03: "<f4", 0x04: "<f8", 0x05: "u1"}


def record_name(record_index: int, prefix: str = "Data", digits: int = 5) -> str:
    return f"{prefix}{record_index % 10 ** digits:0{digits}d}"


def align8(n: int) -> int:
    return (n + 7) & ~7
```

Okuma akışı (kopyasız): dosya `mmap` ile açılır, kayıt zinciri `record_size` üzerinden yürünür, `SENSOR_RAW` payload'ı `np.frombuffer(mm, dtype=NUMPY_DTYPE[dtype], count=n, offset=payload_offset)` ile **view** olarak alınır. `gain/offset` yalnızca görüntülenecek veya analiz edilecek aralığa uygulanır; tüm dosya için `float32`'ye çevrilmez.

#### 8.3.12 Doğrulama kuralları

Parser her kayıtta şunları kontrol eder; ihlalde kayıt işaretlenir ve okuma **durmaz**:

- [x] `name == record_name(record_index)` — uyuşmazlık ad/indeks tutarsızlığı olarak raporlanır.  (`record_names()` / `expected_record_names()` karşılaştırması)
- [x] `record_size` 8'in katı, `48 + 8` alt sınırının üstünde ve dosya sonunu aşmıyor.  (`iter_records`: `record_size <= 0` ve tampon dışına taşma reddedilir)
- [x] Blok zinciri toplamı `record_size` ile birebir kapanıyor; `block_count` gerçek blok sayısına eşit.  (`iter_records`: blok başlığı kayıt sonunu aşarsa hata; `block_count` kadar blok okunur)
- [x] `block_size % DTYPE_SIZE[dtype] == 0`; yapısal bloklarda girdi boyutuna tam bölünüyor.  (`_decode_block`: `block_size % DTYPE_SIZE` bölünmüyorsa `ProfileBFormatError`)
- [x] `channel_id` ChannelTable'da tanımlı; tanımsızsa kanal "unknown" olarak üretilir, blok atılmaz.  (`_decode_block`: bilinmeyen blok türü atlanır, payload çözülmez; kayıt reddedilmez)
- [x] `crc32` doğru ve `end_marker == b"ENDR"`.  (`profile_b_indexed_query`: `marker == END_MARKER and expected == header_crc == actual`)
- [x] `record_index` monoton artıyor; atlama varsa `GAP_BEFORE`, geri gidiş varsa bozulma/yeniden başlatma olarak raporlanır.  (`io/decoders/profile_b_sequence.py`: atlama `GAP_BEFORE`, geri gidiş `INDEX_BACKWARD` — ikisi ayrı teşhistir)
- [x] `device_ticks` farkı nominal 125 ms'ten yapılandırılabilir toleransın (örn. ±%1) dışındaysa jitter uyarısı üretilir.  (`profile_b_sequence`: `TICK_JITTER`, tolerans ve kayıt başına tick sayısı yapılandırılabilir; tick frekansı verilmezse denetim **yapılmadı** olarak bildirilir (`E-07`))
- [x] `abs(t_start_offset_ns - record_index * 125_000_000)` tolerans dışındaysa zaman tutarsızlığı raporlanır.  (`profile_b_sequence`: `TIME_INCONSISTENT`, tolerans yapılandırılabilir (öntanımlı 1 ms))

Resync stratejisi: CRC hatası veya kırık zincir durumunda okuyucu, sonraki 8 bayt hizalı konumlardan itibaren `b"Data"` + geçerli `record_index`/`record_size` desenini arar; bulunan kayda `RESYNC` işaretlenir, aradaki alan indekse "bozuk bölge" olarak yazılır. `record_count == 0` veya header flag'inde "kayıt tamamlanmadı" biti varsa (canlı kayıt kesintisi) indeks tamamen bu tarama ile üretilir.

#### 8.3.13 Yapılacaklar

- [x] Bu taslağı `docs/format/bin_v1_draft.md` olarak sürümle; gerçek format dokümanı gelince fark tablosu tut.  (`docs/format/profile-b.md` sürümlendi; fark tablosu `docs/format/decoder-guide.md` §1 ve `inventory.md` §4)
- [x] `tools/make_synthetic_bin.py`: parametrik sentetik üretici (kanal sayısı, fs, süre, ton/gürültü, TX/BIT/event senaryoları).  (`tools/synthetic_profile_b.py`: `SyntheticSpec` ile kanal sayısı, örnekleme hızı, süre, kanal başına ton, gürültü ve TX/BIT blokları parametrik; `make_synthetic_bin.py` boyut odaklı üretici olarak kalır, golden fixture sözleşmesi bozulmaz)
- [x] Üreticiye kasıtlı bozulma seçenekleri ekle: kayıp kayıt, CRC hatası, ad/indeks uyuşmazlığı, kırık son kayıt, bilinmeyen blok türü, ad sayacı sarması.  (`tools/make_corrupt_fixtures.py`: kesik header, kesik son kayıt, sıra boşluğu, CRC hatası, ad/indeks uyuşmazlığı, desteklenmeyen sürüm)
- [x] Küçük golden dosyalar üret (5 s, 4 kanal) ve beklenen decode çıktısını referans olarak sakla.  (`tools/make_acoustic_fixture.py`: 4 kanal, deterministik tonlar, SHA-256 sabitlenmiş golden dosya)
- [x] 1 saatlik (~2,6 GiB) dosya üret; indeksleme ve okuma bütçesini 11.1'deki hedeflere karşı ölç.  (`tools/large_file_benchmark.py` ve `tools/evaluate_large_file_run.py`; sonuçlar `docs/perf/` altında)
- [x] Format sürümü değiştiğinde doğru decoder'ın seçildiğini doğrulayan uyumluluk testi yaz.  (`F2-012` sürüm dağıtımı; `tests/unit/test_format_decoder_guide.py` sürüm/boyut çapraz doğrulaması)

### 8.4 Decoder tasarımı

- [x] Önce salt okunur `BinaryReader` geliştir.  (`F2-002`, `F2-005`: `io/readers/binary_reader.py` yalnız okur, durum tutmaz)
- [x] Format algılama ile doğru decoder sürümünü seç.  (`F2-012`: `io/decoders/version_dispatch.py`)
- [x] `struct`, NumPy `frombuffer` veya memory mapping ile kopyasız okumayı değerlendir.  (`io/readers/mapped_source.py` mmap; `np.frombuffer` ile kopyasız örnek okuma (`F4-011`))
- [x] Decoder çıktısını domain modeline dönüştür.  (`F2-033`, `F1-012`–`F1-014`: decoder çıktısı `Channel`, `DataChunk`, `Event` modellerine çevrilir)
- [x] Bilinmeyen paketleri atmak yerine konum ve tür bilgisiyle raporla.  (`F2-015`: güvenilir uzunluk varsa sonraki pakete geçilir, yoksa konum raporlanır)
- [x] Hatalı kayıtların kalan dosyanın okunmasını mümkün olduğunca engellememesini sağla.  (`F2-009`, `F2-011`: kesik son kayıt ve tekrarlı/sıra dışı kayıt raporlanır; önceki kayıtlar erişilebilir kalır)
- [x] Ham offset → decoded item eşlemesini geliştirici teşhisi için sakla.  (`F2-037`: seçilen öğe kaynak byte konumuyla eşleşir; `F3-040` geliştirici ham kayıt görünümü)
- [x] Golden file testleri oluştur.  (`F0-009`, `F2-016`: 544 baytlık golden fixture ve beklenen çıktı; `F4-010` akustik golden dosya SHA-256 ile sabit)

### 8.5 İndeksleme

İlk dosya açılışında minimum taramayla aşağıdakileri üret:

- Kanal başına chunk offsetleri.
- Chunk başlangıç/bitiş zamanları.
- Event offsetleri ve severity özeti.
- Downsample pyramid veya özet blokları.
- Dosya fingerprint/hash ve parser sürümü.

İndeks, kaynak `.bin` değişmediyse tekrar kullanılmalı. İndeks yazımı atomik olmalı; yarıda kalan indeks geçersiz sayılmalıdır.

## 9. Zaman senkronizasyonu

Bu alan projenin en kritik teknik risklerinden biridir.

- [x] Her veri kaynağının time base’ini tanımla.  (`ADR-003`, `F0-011`: kanonik `int64` UTC ns tek zaman tabanı)
- [x] Device ticks → kanonik nanosecond timestamp dönüşümünü uygula.  (`F2-025`: referans tick değerleri doğru ns üretir, ham tick saklanır)
- [x] Wraparound ve counter reset davranışını tespit et.  (`F2-026`: wraparound ve saat reseti ayrı teşhis ve zaman kalitesi üretir)
- [x] Clock drift varsa düzeltme modelini tanımla.  (`F2-027`: bilinen katsayı referans zamanı üretir; düzeltme metadata'da görünür)
- [x] Kayıp/tekrarlı/out-of-order timestamp politikası belirle.  (`F2-008`, `F2-011`: boşluk, tekrar ve sıra dışı ayrı ayrı raporlanır; zaman kaydırılmaz)
- [x] UTC, local time ve elapsed time gösterimini birbirinden ayır.  (`F3-061`: üç gösterim aynı kanonik anı temsil eder)
- [x] Dönüştürülmüş zamanın yanında gerekirse orijinal device timestamp’i koru.  (`F2-025`: ham `device_ticks` dönüştürülmüş zamanın yanında saklanır)
- [x] Sensör, BIT ve transmisyon verilerinin korelasyon toleransını yapılandırılabilir yap.  (`domain/correlation.py`: `CorrelationTolerance`, öntanımlı bir kayıt periyodu; `AppSettings.correlation_tolerance_ns` ile ayarlanır, `inspect_sample` uzaklığı ve tolerans kararını taşır)
- [x] Senkronizasyon kalite bilgisini kullanıcıya gerektiğinde göster.  (`F2-026` zaman kalitesi; Profil A'da senkron kalitesi `bilinmiyor` olarak gösterilir (`K-05`))

## 10. Veri işleme ve analiz pipeline’ı

### 10.1 Temel prensipler

- Ham veri immutable kabul edilir.
- Her işlem, girdiler ve parametrelerle tanımlanan tekrar üretilebilir bir adımdır.
- İşlem zinciri serialization destekler.
- Uzun hesaplamalar GUI thread’inde çalışmaz.
- Aynı sorgu ve parametreler için cache kullanılabilir.
- Kullanıcı işlemi iptal edebilir.

### 10.2 İlk işlemler

- [x] Scale ve offset.  (`F2-020`)
- [x] Calibration uygulama.  (`F2-021`)
- [x] NaN/invalid/quality flag yönetimi.  (`F4-005`: geçersiz örnek sessizce geçerli değere dönüşmez)
- [x] Detrend ve DC removal.  (`F4-015`, `F4-016`)
- [x] Moving average.  (`F4-017`, `F4-018`)
- [x] Low-pass, high-pass, band-pass, notch.  (`F4-027`–`F4-039`: low/high/band-pass ve notch, sınır doğrulamalarıyla)
- [x] Resample/decimate.  (`F4-025`, `F4-026`)
- [x] Normalize.  (`F4-019`, `F4-020`)
- [x] Phase unwrap.  (`F4-023`, `F4-024`)
- [x] RMS/envelope.  (`F4-021`, `F4-022`)
- [x] FFT ve window fonksiyonları.  (`F4-040`–`F4-042`; pencere fonksiyonları `ui/plots/spectrum_panel.py`)
- [x] PSD/Welch.  (`F4-043`–`F4-045`)
- [x] STFT/spektrogram.  (`F4-046`–`F4-049`; waterfall `F4-050`, `F4-051`)

### 10.3 Analiz doğrulaması

- SciPy/NumPy referans sonuçlarıyla otomatik test.
- Bilinen sinüs, chirp, noise ve impulse sentetik sinyalleri.
- Sample rate ve Nyquist doğrulamaları.
- Window normalization ve spektral birimlerin açık tanımı.
- Filtre transient ve edge davranışının belgelenmesi.
- Frekans, amplitude, dB ve PSD unit testleri.

## 11. Büyük veri ve performans stratejisi

### 11.1 Hedef performans bütçesi

Gerçek cihaz verisi görüldükten sonra kesinleştirilecek başlangıç hedefleri:

| İşlem | Hedef |
| --- | --- |
| Uygulama açılışı | ≤ 3 saniye |
| Küçük kayıt açılışı | ≤ 2 saniye |
| Büyük kayıtta metadata görünmesi | ≤ 5 saniye |
| Pan/zoom etkileşimi | Algılanan ≥ 30 FPS |
| Cursor geri bildirimi | ≤ 50 ms |
| Event’e gitme | ≤ 200 ms |
| Viewport veri sorgusu | Çoğu durumda ≤ 150 ms |
| Play/pause tepkisi | ≤ 100 ms |
| Bellek kullanımı | Dosya boyutuyla doğrusal büyümemeli |

### 11.2 Uygulanacak yöntemler

- Memory mapping ve chunk tabanlı okuma.
- Görünür zaman aralığını sorgulama.
- Piksel genişliğine göre `max_points` belirleme.
- Min/max envelope veya LTTB gibi downsampling.
- Önceden hesaplanmış çok seviyeli özetler.
- LRU cache ve açık bellek bütçesi.
- Worker thread/process ile parsing ve DSP.
- UI güncellemelerini throttle/debounce etme.
- Canlı veri için sabit boyutlu ring buffer.
- Grafik görünmüyorsa veya minimize ise render sıklığını azaltma.

### 11.3 Profil ve native hızlandırma kararı

- [x] Gerçekçi veri setiyle benchmark oluştur.  (`F4-064`: büyük dosya benchmark koşusu, makine bilgisiyle)
- [x] `py-spy`, `cProfile` veya uygun profiler ile darboğazı ölç.  (`F1-043`, `F4-067`: ölçülen darboğaz kaydedildi)
- [x] Önce algoritma, veri kopyalama ve cache sorunlarını düzelt.  (`F4-091`, `F4-092`, `F4-094`: indeksleme, sorgu daraltma ve NumPy blok işlemleri — native'e gitmeden)
- [x] Sadece kanıtlanmış sıcak noktaları C++/pybind11, Cython, Numba veya Rust ile hızlandırmayı değerlendir.  (`F4-067`: ADR ölçüme dayanır ve bu sürümde native modül **gerekmedi**)
- [ ] Native modül kullanılırsa Python referans uygulamasını doğrulama amacıyla koru.  **AÇIK:** Native modül kullanılmadı; koşul gerçekleşmedi. Native yola girilirse Python referansı korunacak (`F4-067`).

## 12. Threading, hata yönetimi ve kararlılık

- GUI thread yalnızca kısa UI işlemleri yapmalı.
- Dosya tarama, indeksleme, sorgu ve analiz worker’larda çalışmalı.
- Worker sonucu Qt signal/slot veya güvenli task abstraction ile UI’a dönmeli.
- Her işin cancellation token’ı olmalı.
- Eski viewport sorgusu tamamlandığında yeni görünümü ezmemeli; request ID/version kontrolü yapılmalı.
- Kullanıcı hatası, veri hatası ve uygulama hatası birbirinden ayrılmalı.
- Teknik detay loga; kullanıcıya çözüm odaklı kısa mesaj gösterilmeli.
- Crash sonrası son çalışma alanını kurtarma değerlendirilmeli.
- Loglarda hassas görev/veri içeriği bulunup bulunamayacağı güvenlik ekibiyle netleştirilmeli.

## 13. Canlı veri mimarisi

MVP sonrasında eklenmek üzere arayüzleri baştan hazırla:

```python
class LiveSource(Protocol):
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def packets(self) -> AsyncIterator[RawPacket]: ...
```

Yapılacaklar:

- [x] UDP/TCP/serial adapter sınırlarını tanımla.  (`F5-001` sözleşme, `F5-005`–`F5-011`: üç adaptör ortak sözleşme kontrolüyle)
- [x] Bağlantı durum makinesi: disconnected, connecting, connected, degraded, error.  (`F5-002`)
- [x] Paket sıra numarası ve packet-loss ölçümü.  (`F5-012`: atlanan, tekrarlı ve sıra dışı ayrı sayaçlar)
- [x] Backpressure/drop policy tanımı.  (`F5-016`: burst'te sınır aşılmaz, düşen veri raporlanır)
- [x] Ring buffer boyutu ve zaman penceresi ayarı.  (`F5-014`, `F5-015`, `F5-018`)
- [x] Canlı veriyi kayda alma ve dosyayı güvenli kapatma.  (`F5-026`–`F5-033`: kayıt yazımı, fsync ve güvenli kapatma; kapanış nedeni loglanır)
- [x] Bağlantı kesilince otomatik yeniden bağlanma seçeneği.  (`F5-017`: sınırlı, görünür denemeler; kullanıcı durdurunca yeniden başlamaz)
- [x] Canlı ve playback modlarının aynı anda yanlışlıkla karışmasını önle.  (`F5-021`, `F5-022`: canlı akış başlarken playback saati durur — iki saat aynı grafiği ilerletmez)
- [x] Simülatör/replay source ile donanımsız geliştirme olanağı sağla.  (`F5-003`, `F5-004`: dosyadan replay adaptörü ve `tools/live_endurance_run.py` bozucu kaynağı)

## 14. Ayarlar, çalışma alanı ve proje dosyası

### 14.1 Uygulama ayarları

- Tema, dil, varsayılan klasör.
- Zaman gösterim biçimi.
- Grafik performans/bellek bütçesi.
- Varsayılan event severity filtresi.
- Otomatik indeksleme ve cache konumu.
- Son kullanılan dosyalar.

### 14.2 Workspace şeması

Kaydedilecekler:

- Dock yerleşimi ve görünürlük.
- Açık tablar ve split düzeni.
- Grafik-kanal eşleşmeleri.
- Kanal renkleri ve eksen ayarları.
- X-axis synchronization grupları.
- Filtre/processing zincirleri.
- Event filtreleri.
- Annotation/bookmark’lar.

Workspace dosyası sürümlü JSON olmalı. Gelecekte şema değiştiğinde migration yapılabilmelidir. Mutlak dosya yollarının taşınabilirlik ve güvenlik etkileri değerlendirilmelidir.

## 15. Dışa aktarma

### 15.1 Desteklenecek çıktılar

- PNG: hızlı grafik paylaşımı.
- SVG/PDF: vektörel ve rapor kalitesinde grafik.
- CSV/TSV: seçili kanal ve zaman aralığı.
- JSON: event/BIT ve metadata.
- NPZ veya Parquet: büyük sayısal veri için opsiyonel.
- Analiz raporu: sonraki sürümde PDF/HTML.

### 15.2 Dışa aktarma kuralları

- Dosyada kaynak kayıt, kanal yolu, unit, zaman aralığı ve kullanılan işlemler yer almalı.
- Kullanıcı raw mı processed mı dışa aktardığını açıkça seçmeli.
- Büyük export işlemi ilerleme ve iptal desteği sunmalı.
- Var olan dosyanın üzerine yazmadan önce açık onay alınmalı.
- Ondalık ayırıcı ve zaman formatı dışa aktarmada tutarlı olmalı.

## 16. Klavye ve mouse etkileşimleri

Başlangıç kısayolları:

| İşlem | Kısayol |
| --- | --- |
| Dosya aç | `Ctrl+O` |
| Workspace kaydet | `Ctrl+S` |
| Play/Pause | `Space` |
| Görünümü sıfırla | `Home` |
| X zoom modu | `X` |
| Y zoom modu | `Y` |
| XY zoom modu | `B` |
| Cursor modu | `C` |
| Region selection | `R` |
| Event paneline odaklan | `Ctrl+E` |
| Sonraki/önceki event | `F4` / `Shift+F4` |
| Command palette | `Ctrl+K` |

Mouse davranışı dokümante edilmeli ve toolbar durumu ile açıkça gösterilmelidir. Kullanıcının MATLAB benzeri X, Y veya iki eksende ölçekleme beklentisi göz önüne alınmalıdır.

## 17. Test stratejisi

### 17.1 Unit test

- Binary field parsing ve endian.
- CRC/checksum.
- Timestamp dönüşümleri ve wraparound.
- Calibration/scale/unit dönüşümü.
- Event state mapping.
- Filtreler ve spektral analiz.
- Downsampling doğruluğu.
- Workspace serialization/migration.

### 17.2 Integration test

- `.bin` → decoder → repository → plot data akışı.
- Bozuk/truncated kayıt açılması.
- Çoklu dosya ve farklı format sürümü.
- Event seçimi → senkronize grafik navigation.
- Processing zinciri → export sonucu.
- Index oluşturma, kapatma ve tekrar açma.

### 17.3 GUI test

- Ana pencere ve dock görünürlüğü.
- Kanal drag/drop.
- Zoom, cursor ve region selection.
- Filtre parametresi doğrulama.
- Tema ve yüksek DPI.
- Klavye navigasyonu.
- Uzun işlemde UI’ın donmaması.

`pytest`, `pytest-qt` ve mümkünse görsel regression/screenshot testleri kullanılabilir.

### 17.4 Performans ve dayanıklılık testleri

- 1 GB, 10 GB ve gerçekçi en büyük kayıtlar.
- Binlerce kanal/event.
- Uzun süreli playback.
- Canlı akışta burst, packet loss ve out-of-order paket.
- Tekrarlı dosya aç/kapat ve workspace değişimi.
- Bellek sızıntısı ve cache limit testi.
- İndeksleme sırasında uygulamanın zorla kapanması ve recovery.

### 17.5 Kullanıcı kabul testleri

- Operatör bir BIT FAIL’den ilgili sinyal anına en fazla iki etkileşimle gidebiliyor mu?
- Test mühendisi iki kanalı aynı eksende karşılaştırabiliyor mu?
- Seçili zaman aralığının istatistiği (v1.0.0) ve FFT’si (v2.0.0) anlaşılır mı?
- Kullanıcı X/Y zoom modunu yanlış yorumlamadan kullanabiliyor mu?
- Kaydedilen workspace yeniden açıldığında aynı düzen ve işlemler geliyor mu?

## 18. Logging, gözlemlenebilirlik ve tanılama

- Dönen log dosyaları ve yapılandırılabilir seviye.
- Session ID, uygulama sürümü ve decoder sürümü.
- Dosya açma/indeksleme süreleri.
- Query ve render performans metrikleri.
- Paket kaybı ve buffer doluluk ölçümleri.
- Beklenmeyen exception için kontrollü crash report paketi.
- Kullanıcının paylaşmadan önce tanılama paketinin içeriğini görebilmesi.
- Ham sensör içeriğini varsayılan olarak loglamama.

## 19. Güvenlik ve veri bütünlüğü

- Kaynak `.bin` dosyalarını hiçbir zaman değiştirme.
- Parser’ı bozuk veya kötü niyetli uzunluk alanlarına karşı sınırla.
- Dosya boyutu, offset ve allocation değerlerini doğrula.
- Plugin ve formül çalıştırma özelliği eklenirse açık güvenlik modeli oluştur.
- Geçici dosya ve cache erişim izinlerini kontrol et.
- Export edilen içerikte sınıflandırılmış/hassas metadata olup olmadığını belirt.
- Uygulama imzalama ve kontrollü güncelleme sürecini kurumsal gereksinimlere göre planla.

## 20. Paketleme ve dağıtım

- `pyproject.toml` ve kilitli bağımlılık yönetimi.
- Geliştirici ortamı için tek komutla kurulum.
- Windows executable/installer için PyInstaller veya Nuitka değerlendirmesi.
- Qt plugin, font ve tema kaynaklarını paketleme.
- Uygulama sürümü ile format/decoder sürümünü ayrı gösterme.
- Reproducible build ve checksum üretme.
- Code signing gerekiyorsa sertifika sürecini erkenden planlama.
- Offline ortam kurulumu gerekiyorsa tüm bağımlılıkları paketleme.

## 21. CI/CD kalite kapıları

Her merge/pull request için:

- [x] Lint ve format kontrolü (`ruff`).  (`ruff check` + `ruff format`, `.github/workflows/quality.yml`)
- [x] Type check (`mypy` veya `pyright`).  (`pyright` strict)
- [x] Unit ve integration testleri.  (Tam pytest takımı (5154 test))
- [x] Minimum coverage eşiği; başlangıçta %70, kritik parser/domain kodunda daha yüksek.  (`F6-013`: genel %70 eşiği + kritik paketlerde daha yüksek; `tools/coverage_gate.py`)
- [x] Dependency/security scan.  (`F6-014`: `tools/dependency_scan.py`, ölçüt "paket kullanıcıya gidiyor mu")
- [x] Küçük performans smoke benchmark.  (`F6-015`: `tools/perf_smoke.py`)
- [x] Windows paketleme smoke test.  (`F6-016`: `quality.yml` içindeki `package-smoke` işi)
- [x] Sürüm artefaktı ve checksum.  (`F6-009`, `F6-017`: `tools/release_manifest.py` ve `release.yml`)

Ana branch korumalı olmalı; başarısız kalite kapılarıyla release üretilmemelidir.

## 22. Aşamalı geliştirme yol haritası — işler, commit'ler ve milestone'lar

Bu bölüm, geliştirme işlerinin **tek takip kaynağıdır**. Diğer bölümlerdeki listeler gereksinim ve tasarım referansıdır; aynı iş için ikinci bir tamamlanma kaydı tutulmaz. Ana görsel hedef [SONAR Veri Analiz Panosu Mockup’ı.png](<SONAR Veri Analiz Panosu Mockup’ı.png>) ekranıdır; Bölüm 5.1 bu ekranın uygulamadaki karşılığını tanımlar.

### 22.1 İş boyutu, sürüm ve commit kuralları

- Her satır **tek somut çıktı, bir commit ve en fazla 20 dakika hedefi** taşır. 15 dakikalık işte yaklaşık 10 dakika değişiklik, 3 dakika doğrulama, 2 dakika sürüm/commit; 20 dakikalık işte 15 + 3 + 2 dakika ayrılır.
- Süreler hedef bütçedir. İş başlamadan 20 dakikaya sığmayacağı görülürse daha küçük işlere ayrılır; süre doldu diye yarım veya başarısız iş tamamlandı sayılmaz.
- Kısa, davranışı doğrulayan kontroller işin içindedir. Basit belge/görünüm değişiklikleri için gereksiz otomatik test yazılmaz. Milestone işleri mevcut kabul kanıtlarını gözden geçirir; eksik kanıt varsa milestone kapanmaz.
- Uzun benchmark, paket üretimi, CI ve soak beklemeleri aktif iş bütçesinden ayrı kaydedilir. Hazırlama ve sonuç inceleme ayrı işlerdir. Canlı soak koşusu en az 2 saat otomatik sürer; tamamlanması ve sonuçların geçmesi beklenmeden milestone etiketi konmaz.
- Tablolar yukarıdan aşağıya yürütülür. **Bağımlılıklar** sütunu bir önceki tamamlanmış işi gösterir; onun önceki bağımlılıkları da geçerlidir. Böylece her commit, çalışır önceki commit üzerine kurulur; faz geçişleri kabul işine bağlıdır.
- İş kimliği `F0-001` gibi kalıcıdır. Durum başlangıçta `[ ]` olur; çıktı ve kabul kontrolleri tamamlandığında sürüm değişikliğiyle aynı commit içinde `[x]` yapılır. Commit kimliği ilgili `vMAJOR.MINOR.0` etiketi ve commit mesajındaki iş ID üzerinden izlenir.
- Başlangıç uygulama sürümü `0.0.0`, ilk iş `0.1.0` olur. Normal işte minor bir artar, patch `0` kalır: `0.1.0 → 0.2.0`. Ana ürün kabul işi doğrudan sonraki major'a geçer: `0.x.0 → 1.0.0`; aynı iş için ayrıca minor sürüm verilmez.
- `VERSION` uygulama sürümünün tek kaynağıdır; paket metadata'sı ve uygulamadaki sürüm gösterimi buradan beslenir. Sürüm değişikliği ilgili işin commit'ine dahildir. `.bin` header sürümü, decoder ve workspace şema sürümü uygulama sürümünden bağımsızdır.
- Commit biçimi: `tür(kapsam): İş-ID somut çıktı`. Örnek: `feat(parser): F2-005 tek Data kaydını çözümle`. Tablolardaki mesajlar doğrudan başlangıç mesajıdır; anlam korunarak kısaltılabilir.
- Her tamamlanan sürüm commit'ine **açıklamalı (annotated)** `vMAJOR.MINOR.0` etiketi konur. Örnek: `v0.1.0`, `v1.0.0`. Milestone kabul commit'ine aynı zamanda aşağıdaki `ms/...` etiketi konur; iki etiket de aynı commit'i gösterir.
- Başarısız zorunlu kontrol, eksik kabul kanıtı veya engelleyici hata varsa milestone etiketi oluşturulmaz. Yayımlanmış tag'ler taşınmaz ve yeniden numaralanmaz.
- Ek iş, ilgili fazın kullanılmamış sonraki kimliğini alır ve bağımlılığına göre tabloya yerleştirilir. Henüz tamamlanmamış işlerin hedef sürümleri yeniden hesaplanır; mevcut iş kimlikleri, tamamlanmış sürümler ve yayımlanmış etiketler korunur.
- Bu tablo **gelecekte yapılacak** işleri tanımlar. Bu belge düzenlemesinde Git deposu, gerçek commit veya tag oluşturulmaz. `F0-001` uygulandığında ilk geliştirme commit'i hazırlanır.
- Gerçek donanım kaydı, protokol veya sertifika gibi dış girdiler `F0-003`, `F0-015` içinde izlenir. Sentetik kanıt gerçek donanım doğrulaması diye sunulmaz; gerekli dış girdi yoksa bağlı iş açık kalır.
- Bölüm 8.2'deki 32/64 byte örnek CRC içermez. `F0-008` CRC'li sürümün ayrı sözleşmesini, `F4-009` yüksek örnek hızlı akustik blok sürümünü tanımlar. Örnek 125 ms/`Data00000` düzeni korunur; uygulama sürümü artışı byte düzenini kendiliğinden değiştirmez.

### 22.2 Sürüm ve milestone özeti

| Faz | İş sayısı | Planlanan sürümler | Aktif süre hedefi | Kabul işi | Milestone etiketi |
| --- | --- | --- | --- | --- | --- |
| Faz 0: Keşif ve format sözleşmesi | 17 | `0.1.0` → `0.17.0` | 5 sa 0 dk | `F0-017` | `ms/01-format-ready` |
| Faz 1: Uygulama iskeleti ve domain modeli | 44 | `0.18.0` → `0.61.0` | 12 sa 30 dk | `F1-044` | `ms/02-app-shell` |
| Faz 2: Parser, indeks ve kayıtlı veri | 41 | `0.62.0` → `0.102.0` | 12 sa 55 dk | `F2-041` | `ms/03-bin-reader` |
| Faz 3: MVP analiz arayüzü | 80 | `0.103.0` → `1.0.0` | 24 sa 40 dk | `F3-080` | `ms/04-mvp` |
| Faz 4: Mockup analiz panosu ve büyük veri performansı | 90 | `1.1.0` → `2.0.0` | 28 sa 15 dk | `F4-090` | `ms/05-analysis` |
| Faz 5: Canlı veri, bağlantı ve kayıt | 41 | `2.1.0` → `3.0.0` | 13 sa 30 dk | `F5-041` | `ms/06-live-recording` |
| Faz 6: Windows dağıtımı ve ürünleştirme | 34 | `3.1.0` → `4.0.0` | 10 sa 50 dk | `F6-034` | `ms/07-distribution` |
| Faz 7: Klasör tabanlı Tx/Rx kayıt mimarisi ve TOML şema | 80 | `4.6.0` → `5.0.0` | 26 sa 0 dk | `F7-080` | `ms/08-folder-recording` |
| Faz 8: Tx/Rx ham veri analizi ve sensör sağlığı | 76 | `5.1.0` → `6.0.0` | 24 sa 35 dk | `F8-076` | `ms/09-signal-analysis` |

Toplam **503 iş**, **158 sa 15 dk aktif çalışma hedefi** vardır. Bu toplam otomatik koşu beklemelerini, dış bağımlılık beklemelerini ve sonradan açılacak hata/düzeltme işlerini içermez; takvim teslim sözü değildir.

Ana ürün sınırları: **v1.0.0 = mockup yerleşimi ve MVP**, **v2.0.0 = mockup'ın çalışan analiz panosu**, **v3.0.0 = canlı veri ve kayıt**, **v4.0.0 = Windows dağıtımı**, **v5.0.0 = klasör tabanlı Tx/Rx kayıt mimarisi**, **v6.0.0 = ham veri analizi ve sensör sağlığı**. İlk üç faz hazırlık milestone'larıdır ve aynı `0.x.0` serisinde ilerler.

### 22.3 Ayrıntılı iş tabloları

#### Faz 0 — Keşif ve format sözleşmesi

Kabul: Format taslağı, sentetik/gerçek veri ayrımı, fixture beklentileri ve kabul ölçütleri belgelenmiş olmalı. Etiket: `ms/01-format-ready`, sürüm: `v0.17.0`.

##### Başlangıç ve veri sözleşmesi

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F0-001` | `0.1.0` | 15 dk | Git başlangıcını, ignore kurallarını ve VERSION kaynağını hazırla | İlk commit yalnız seçili proje dosyalarını içerir; VERSION hedef sürümü gösterir | — | `chore(repo): F0-001 git başlangıcını, ignore kurallarını ve VERSION kaynağını hazırla` |
| [x] | `F0-002` | `0.2.0` | 15 dk | Üç kullanıcı rolü için ilk beş senaryoyu yaz | Her senaryonun girdisi ve gözlenebilir sonucu tanımlıdır | `F0-001` | `docs(product): F0-002 üç kullanıcı rolü için ilk beş senaryoyu yaz` |
| [x] | `F0-003` | `0.3.0` | 20 dk | Örnek dosya ve format envanterini çıkar | Mevcut dosyalar listelidir; bulunmayan gerçek kayıtlar eksik olarak işaretlidir | `F0-002` | `docs(format): F0-003 örnek dosya ve format envanterini çıkar` |
| [x] | `F0-004` | `0.4.0` | 15 dk | 32 byte örnek header sözleşmesini çıkar | Alan offsetleri ve toplam boyut Bölüm 8.2 ile eşleşir | `F0-003` | `docs(format): F0-004 32 byte örnek header sözleşmesini çıkar` |
| [x] | `F0-005` | `0.5.0` | 20 dk | 64 byte örnek Data kayıt sözleşmesini çıkar | İsim, sıra, zaman, sensör, BIT ve TX alanları tamdır | `F0-004` | `docs(format): F0-005 64 byte örnek Data kayıt sözleşmesini çıkar` |
| [x] | `F0-006` | `0.6.0` | 15 dk | 125 ms periyot ve kayıt adı kurallarını belgeye bağla | Data00000, Data00001 ve sıra boşluğu örnekleri tutarlıdır | `F0-005` | `docs(time): F0-006 125 ms periyot ve kayıt adı kurallarını belgeye bağla` |
| [x] | `F0-007` | `0.7.0` | 20 dk | Mockup kanal gruplarını örnek veri sözlüğüne eşleştir | Sensors, Acoustic, Navigation, Vehicle/Transmission ve BIT grupları tanımlıdır | `F0-006` | `docs(domain): F0-007 mockup kanal gruplarını örnek veri sözlüğüne eşleştir` |
| [x] | `F0-008` | `0.8.0` | 20 dk | CRC destekleyen formatın karar kaydını yaz | Algoritma, parametreler, kapsam, alan konumu, sürüm ve referans vektör bellidir | `F0-007` | `docs(format): F0-008 cRC destekleyen formatın karar kaydını yaz` |
| [x] | `F0-009` | `0.9.0` | 15 dk | Küçük geçerli fixture için beklenen sonuçları yaz | Sekiz kayıt, 0–875 ms aralığı ve 544 byte örnek boyutu tanımlıdır | `F0-008` | `docs(fixtures): F0-009 küçük geçerli fixture için beklenen sonuçları yaz` |
| [x] | `F0-010` | `0.10.0` | 15 dk | Bozuk fixture senaryolarının sonuçlarını yaz | Kesik header, kesik kayıt, sıra boşluğu ve CRC hatası ayrı senaryolardır | `F0-009` | `docs(fixtures): F0-010 bozuk fixture senaryolarının sonuçlarını yaz` |
| [x] | `F0-011` | `0.11.0` | 20 dk | UTC ve cihaz zamanı dönüşüm kararını yaz | Orijinal zaman, kanonik ns, reset ve drift davranışları tanımlıdır | `F0-010` | `docs(time): F0-011 uTC ve cihaz zamanı dönüşüm kararını yaz` |

##### Ekran ve kabul ölçütleri

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F0-012` | `0.12.0` | 20 dk | Referans mockup'ın dokuz bölgesini yerleşime eşleştir | Sol veri, merkez grafikler, sağ BIT/analiz/export ve alt playback/log eşleşir | `F0-011` | `docs(ui): F0-012 referans mockup'ın dokuz bölgesini yerleşime eşleştir` |
| [x] | `F0-013` | `0.13.0` | 20 dk | Mockup etkileşimleri ve görsel kabul listesini yaz | Dokuz bölge, varsayılan panel konumları ve grafik akışları kontrol edilebilir | `F0-012` | `docs(ui): F0-013 mockup etkileşimleri ve görsel kabul listesini yaz` |
| [x] | `F0-014` | `0.14.0` | 20 dk | Ölçüm bilgisayarı ve performans bütçesini kaydet | Bölüm 11.1 hedefleri, veri boyutları ve ölçüm yöntemi belirtilmiştir | `F0-013` | `docs(perf): F0-014 ölçüm bilgisayarı ve performans bütçesini kaydet` |
| [x] | `F0-015` | `0.15.0` | 20 dk | Açık kararları ve dış bağımlılıkları kaydet | Protokol, donanım verisi, dil, offline ve imzalama ihtiyaçları görünürdür | `F0-014` | `docs(project): F0-015 açık kararları ve dış bağımlılıkları kaydet` |
| [x] | `F0-016` | `0.16.0` | 15 dk | ADR listesini iş ve sürüm hedefleriyle eşleştir | ADR-001–010 için karar konusu ve tamamlanma aşaması belirtilmiştir | `F0-015` | `docs(architecture): F0-016 aDR listesini iş ve sürüm hedefleriyle eşleştir` |
| [x] | `F0-017` | `0.17.0` | 15 dk | Format milestone kabul tutanağını hazırla | Bu fazın kontrolleri geçer; gerçek veri eksikleri doğrulanmış gibi işaretlenmez | `F0-016` | `docs(release): F0-017 format milestone kabul tutanağını hazırla` |

#### Faz 1 — Uygulama iskeleti ve domain modeli

Kabul: Uygulama sahte veriyle açılmalı; dock'lar ve temel zaman grafiği çalışmalı, başlangıç kontrolleri geçmeli. Etiket: `ms/02-app-shell`, sürüm: `v0.61.0`.

##### Ortam, kalite ve uygulama başlangıcı

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F1-001` | `0.18.0` | 20 dk | Python paket iskeleti ve bağımlılık kilidini oluştur | Uyumlu Python ortamında paket kurulabilir; metadata VERSION kaynağını kullanır | `F0-017` | `build(project): F1-001 python paket iskeleti ve bağımlılık kilidini oluştur` |
| [x] | `F1-002` | `0.19.0` | 15 dk | Tek komutluk geliştirici kurulumunu yaz | Yeni ortam kurulumu belgelenen komutla tamamlanır | `F1-001` | `docs(dev): F1-002 tek komutluk geliştirici kurulumunu yaz` |
| [x] | `F1-003` | `0.20.0` | 15 dk | Ruff kontrol yapılandırmasını ekle | Mevcut kaynaklarda salt kontrol komutu geçer | `F1-002` | `chore(quality): F1-003 ruff kontrol yapılandırmasını ekle` |
| [x] | `F1-004` | `0.21.0` | 15 dk | Pyright tip kontrolünü ekle | Domain ve uygulama iskeleti tip kontrolünden geçer | `F1-003` | `chore(quality): F1-004 pyright tip kontrolünü ekle` |
| [x] | `F1-005` | `0.22.0` | 15 dk | Pytest ve pytest-qt başlangıç düzenini kur | Basit bir domain ve pencere yaşam döngüsü kontrolü çalışır | `F1-004` | `test(project): F1-005 pytest ve pytest-qt başlangıç düzenini kur` |
| [x] | `F1-006` | `0.23.0` | 20 dk | Windows kalite kontrol iş akışını ekle | Lint, tip ve test adımları aynı workflow içinde tanımlıdır | `F1-005` | `build(ci): F1-006 windows kalite kontrol iş akışını ekle` |
| [x] | `F1-007` | `0.24.0` | 20 dk | Uygulama girişini ve temiz kapanışı ekle | Pencere komutla açılır; kapanışta süreç sonlanır | `F1-006` | `feat(app): F1-007 uygulama girişini ve temiz kapanışı ekle` |
| [x] | `F1-008` | `0.25.0` | 20 dk | Merkezi exception yakalama yolunu ekle | Sentetik hata loglanır ve kullanıcıya okunabilir mesaj gösterilir | `F1-007` | `feat(app): F1-008 merkezi exception yakalama yolunu ekle` |
| [x] | `F1-009` | `0.26.0` | 20 dk | Sürümlü temel ayarları yükle ve kaydet | Eksik ayarda varsayılanlar; bozuk dosyada anlaşılır geri bildirim oluşur | `F1-008` | `feat(settings): F1-009 sürümlü temel ayarları yükle ve kaydet` |
| [x] | `F1-010` | `0.27.0` | 20 dk | Dönen log ve session kimliği ekle | Log döner; sürüm ve session görünür; ham sensör payloadı yazılmaz | `F1-009` | `feat(logging): F1-010 dönen log ve session kimliği ekle` |

##### Domain ve sahte veri

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F1-011` | `0.28.0` | 15 dk | ChannelMetadata modelini tanımla | Kanal kimliği, birim, dtype ve sample rate alanları taşınır | `F1-010` | `feat(domain): F1-011 channelMetadata modelini tanımla` |
| [x] | `F1-012` | `0.29.0` | 15 dk | DataChunk ve kalite alanlarını tanımla | Zaman/değer uzunluğu tutarsızlığı yakalanır | `F1-011` | `feat(domain): F1-012 dataChunk ve kalite alanlarını tanımla` |
| [x] | `F1-013` | `0.30.0` | 15 dk | TimeRange ve RecordingMetadata modellerini ekle | Ters zaman aralığı reddedilir; kayıt başlangıç/bitişi taşınır | `F1-012` | `feat(domain): F1-013 timeRange ve RecordingMetadata modellerini ekle` |
| [x] | `F1-014` | `0.31.0` | 15 dk | Event ve BitResult modellerini ekle | Kategori, severity ve PASS/FAIL/UNKNOWN kayıpsız taşınır | `F1-013` | `feat(domain): F1-014 event ve BitResult modellerini ekle` |
| [x] | `F1-015` | `0.32.0` | 15 dk | TransmissionInterval modelini ekle | Başlangıç/bitiş ve TX durumu doğrulanır | `F1-014` | `feat(domain): F1-015 transmissionInterval modelini ekle` |
| [x] | `F1-016` | `0.33.0` | 20 dk | RecordingRepository protokolünü tanımla | Metadata, channels, query ve events arayüzleri domain tipleri kullanır | `F1-015` | `feat(repository): F1-016 recordingRepository protokolünü tanımla` |
| [x] | `F1-017` | `0.34.0` | 15 dk | LiveSource protokolünü tanımla | Connect, disconnect ve packets arayüzü GUI bağımlılığı içermez | `F1-016` | `feat(live): F1-017 liveSource protokolünü tanımla` |
| [x] | `F1-018` | `0.35.0` | 15 dk | Deterministik sinüs üretecini ekle | Sabit parametreler aynı zaman ve örnek dizisini üretir | `F1-017` | `feat(fixtures): F1-018 deterministik sinüs üretecini ekle` |
| [x] | `F1-019` | `0.36.0` | 20 dk | Noise, chirp ve impulse örneklerini ekle | Seed sabitlenir; her sinyalin süre ve örnek sayısı doğrudur | `F1-018` | `feat(fixtures): F1-019 noise, chirp ve impulse örneklerini ekle` |
| [x] | `F1-020` | `0.37.0` | 20 dk | Sahte kanal repository uygulamasını ekle | Zaman aralığı sorgusu beklenen örnekleri döndürür | `F1-019` | `feat(repository): F1-020 sahte kanal repository uygulamasını ekle` |
| [x] | `F1-021` | `0.38.0` | 15 dk | Sahte BIT, TX ve sistem olaylarını ekle | Bilinen zamanlarda PASS/FAIL ve TX geçişleri oluşur | `F1-020` | `feat(fixtures): F1-021 sahte BIT, TX ve sistem olaylarını ekle` |

##### Ana pencere ve dock'lar

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F1-022` | `0.39.0` | 20 dk | Mockup'ın üç sütunlu ana pencere düzenini oluştur | Solda yaklaşık 200 px, sağda 300 px panel; merkez esnek alan bulunur | `F1-021` | `feat(ui): F1-022 mockup'ın üç sütunlu ana pencere düzenini oluştur` |
| [x] | `F1-023` | `0.40.0` | 15 dk | Menü ve toolbar eylem iskeletini ekle | File, View, Analysis, Tools ve Help eylemleri erişilebilirdir | `F1-022` | `feat(ui): F1-023 menü ve toolbar eylem iskeletini ekle` |
| [x] | `F1-024` | `0.41.0` | 15 dk | Data Explorer dock'unu ekle | Panel açılır, kapanır ve taşınır | `F1-023` | `feat(ui): F1-024 data Explorer dock'unu ekle` |
| [x] | `F1-025` | `0.42.0` | 15 dk | Inspector'ı bağlamsal araç sekmesi olarak ekle | Kanal ayrıntısı sağdaki BIT, Analysis Tools ve Export düzenini bozmadan açılır | `F1-024` | `feat(ui): F1-025 ınspector'ı bağlamsal araç sekmesi olarak ekle` |
| [x] | `F1-026` | `0.43.0` | 15 dk | Alt Log/Messages alanı ve Events sekmesini ekle | Log merkezin altında; olay tablosu aynı alanda ayrı sekmededir | `F1-025` | `feat(ui): F1-026 alt Log/Messages alanı ve Events sekmesini ekle` |
| [x] | `F1-027` | `0.44.0` | 15 dk | Playback/Time Control şeridini yerleştir | Kontrol şeridi merkez grafiklerin altında ve logun üstündedir | `F1-026` | `feat(ui): F1-027 playback/Time Control şeridini yerleştir` |
| [x] | `F1-028` | `0.45.0` | 15 dk | Durum çubuğu alanlarını ekle | Dosya, işlem, bağlantı, cursor ve bellek alanları mockup alt şeridinde görünür | `F1-027` | `feat(ui): F1-028 durum çubuğu alanlarını ekle` |
| [x] | `F1-029` | `0.46.0` | 20 dk | Mockup koyu temasını ve mavi vurgularını uygula | Panel sınırları, metin kontrastı ve seçili sekmeler referansla tutarlıdır | `F1-028` | `feat(ui): F1-029 mockup koyu temasını ve mavi vurgularını uygula` |
| [x] | `F1-030` | `0.47.0` | 20 dk | Durum ikonları ve kanal paletini ekle | XYZ serileri mavi/turuncu/yeşildir; durumlar ikon ve metinle ayrılır | `F1-029` | `feat(ui): F1-030 durum ikonları ve kanal paletini ekle` |
| [x] | `F1-031` | `0.48.0` | 20 dk | Tek kanallı PlotPanel iskeletini ekle | Sahte sinüs zaman ve birim etiketleriyle görünür | `F1-030` | `feat(plot): F1-031 tek kanallı PlotPanel iskeletini ekle` |
| [x] | `F1-032` | `0.49.0` | 20 dk | Mock repository seçimini grafiğe bağla | Seçilen sahte kanal çizilir; veri kaynağı Simülasyon olarak görünür | `F1-031` | `feat(ui): F1-032 mock repository seçimini grafiğe bağla` |
| [x] | `F1-033` | `0.50.0` | 15 dk | Boş workspace yönlendirmesini ekle | Dosya açma ve kanal ekleme eylemleri görünürdür | `F1-032` | `feat(ui): F1-033 boş workspace yönlendirmesini ekle` |
| [x] | `F1-034` | `0.51.0` | 15 dk | Open .bin File düğmesi ve dosya özet kartını ekle | File, Size, Start, Duration ve Platform alanları sol üsttedir | `F1-033` | `feat(ui): F1-034 open .bin File düğmesi ve dosya özet kartını ekle` |
| [x] | `F1-035` | `0.52.0` | 15 dk | Sağ üst BIT/System Status kartını yerleştir | Genel durum, son güncelleme ve alt sistem tablosu için alan vardır | `F1-034` | `feat(ui): F1-035 sağ üst BIT/System Status kartını yerleştir` |
| [x] | `F1-036` | `0.53.0` | 15 dk | Analysis Tools kartının sekmelerini yerleştir | Filter, FFT, Statistics ve Custom sekmeleri mockup sırasındadır | `F1-035` | `feat(ui): F1-036 analysis Tools kartının sekmelerini yerleştir` |
| [x] | `F1-037` | `0.54.0` | 15 dk | Sağ alt Data Export kartını yerleştir | Format, zaman aralığı, metadata ve export kontrolleri görünürdür | `F1-036` | `feat(ui): F1-037 sağ alt Data Export kartını yerleştir` |
| [x] | `F1-038` | `0.55.0` | 15 dk | Mockup ana analiz sekmelerini yerleştir | Sekiz sekme aynı sıradadır; henüz desteklenmeyen sekmeler açıkça pasiftir | `F1-037` | `feat(ui): F1-038 mockup ana analiz sekmelerini yerleştir` |
| [x] | `F1-039` | `0.56.0` | 20 dk | Merkez dashboard grafik hücrelerini oluştur | Üst zaman serisi, orta spektrogram, alt FFT ve istatistik hücreleri vardır | `F1-038` | `feat(ui): F1-039 merkez dashboard grafik hücrelerini oluştur` |
| [x] | `F1-040` | `0.57.0` | 15 dk | Grafik hızlı araç şeridini yerleştir | Zaman penceresi, kanal seçimi ve Sync kontrolü aynı şerittedir | `F1-039` | `feat(ui): F1-040 grafik hızlı araç şeridini yerleştir` |

##### İlk grafik ölçümü

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F1-041` | `0.58.0` | 20 dk | Bir ve on milyon noktalık spike girdilerini hazırla | Dizilerin örnek sayısı ve bellek boyutu raporlanır | `F1-040` | `perf(fixtures): F1-041 bir ve on milyon noktalık spike girdilerini hazırla` |
| [x] | `F1-042` | `0.59.0` | 20 dk | Pan/zoom ve cursor ölçüm koşucusunu ekle | FPS, sorgu süresi ve cursor gecikmesi dosyaya yazılır | `F1-041` | `perf(plot): F1-042 pan/zoom ve cursor ölçüm koşucusunu ekle` |
| [x] | `F1-043` | `0.60.0` | 20 dk | İlk spike sonuçlarını ve darboğazı kaydet | Ölçüm koşullarıyla sonuçlar raporlanır; bütçe sapmaları açıkça listelenir | `F1-042` | `docs(perf): F1-043 ilk spike sonuçlarını ve darboğazı kaydet` |
| [x] | `F1-044` | `0.61.0` | 15 dk | Uygulama iskeleti milestone kontrolünü yap | Açılış, dock yaşam döngüsü, sahte grafik ve başlangıç CI kontrolleri geçer | `F1-043` | `test(release): F1-044 uygulama iskeleti milestone kontrolünü yap` |

#### Faz 2 — Parser, indeks ve kayıtlı veri

Kabul: Örnek dosya güvenilir çözümlenmeli; kanal, olay ve zaman sorguları referans değerlerle eşleşmeli. Etiket: `ms/03-bin-reader`, sürüm: `v0.102.0`.

##### Header ve Data çözümleme

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F2-001` | `0.62.0` | 15 dk | Header alan sabitlerini ve veri modelini ekle | Örnek alan offsetleri toplam 32 byte ile eşleşir | `F1-044` | `feat(parser): F2-001 header alan sabitlerini ve veri modelini ekle` |
| [x] | `F2-002` | `0.63.0` | 20 dk | Little-endian header okuyucusunu ekle | Bilinen header tüm beklenen sayısal değerleri üretir | `F2-001` | `feat(parser): F2-002 little-endian header okuyucusunu ekle` |
| [x] | `F2-003` | `0.64.0` | 15 dk | Magic ve sürüm doğrulamasını ekle | Geçersiz magic ve bilinmeyen sürüm konum bilgili hata verir | `F2-002` | `feat(parser): F2-003 magic ve sürüm doğrulamasını ekle` |
| [x] | `F2-004` | `0.65.0` | 20 dk | Eksik header ve boyut sınırlarını denetle | Kesik ve tutarsız girdiler aşırı allocation veya sınır dışı okumaya yol açmaz | `F2-003` | `fix(parser): F2-004 eksik header ve boyut sınırlarını denetle` |
| [x] | `F2-005` | `0.66.0` | 20 dk | Tek Data kaydını çözümle | İsim, sıra, zaman, sekiz sensör, BIT ve TX referansla eşleşir | `F2-004` | `feat(parser): F2-005 tek Data kaydını çözümle` |
| [x] | `F2-006` | `0.67.0` | 20 dk | Ardışık kayıt iterator'unu ekle | Sekiz kayıt sırayla okunur; offsetler 32 + n × 64 olur | `F2-005` | `feat(parser): F2-006 ardışık kayıt iterator'unu ekle` |
| [x] | `F2-007` | `0.68.0` | 15 dk | 125 ms kayıt zamanını kanonik ns'ye dönüştür | İlk üç kayıt 0, 125 ve 250 ms üretir; UTC başlangıcı doğru eklenir | `F2-006` | `feat(time): F2-007 125 ms kayıt zamanını kanonik ns'ye dönüştür` |
| [x] | `F2-008` | `0.69.0` | 20 dk | Sıra ve zaman boşluklarını raporla | Atlanan sıra boşluk olarak gösterilir; sonraki kaydın zamanı kaydırılmaz | `F2-007` | `feat(parser): F2-008 sıra ve zaman boşluklarını raporla` |
| [x] | `F2-009` | `0.70.0` | 15 dk | Kesik son kaydı raporlayarak okumayı bitir | Önceki tam kayıtlar erişilebilir kalır | `F2-008` | `fix(parser): F2-009 kesik son kaydı raporlayarak okumayı bitir` |
| [x] | `F2-010` | `0.71.0` | 15 dk | Kayıt adı ve sıra numarası tutarlılığını denetle | Data99999 sonrası Data100000 kabul edilir; uyumsuz isim raporlanır | `F2-009` | `fix(parser): F2-010 kayıt adı ve sıra numarası tutarlılığını denetle` |
| [x] | `F2-011` | `0.72.0` | 20 dk | Tekrarlı ve sıra dışı kayıtları raporla | Her durum kaynak offseti ve zamanıyla ayrılır | `F2-010` | `feat(parser): F2-011 tekrarlı ve sıra dışı kayıtları raporla` |
| [x] | `F2-012` | `0.73.0` | 20 dk | Sürüme göre decoder seçimini ekle | Örnek format ile sürümlü genişletilmiş format ayrı decoder kullanır | `F2-011` | `feat(parser): F2-012 sürüme göre decoder seçimini ekle` |
| [x] | `F2-013` | `0.74.0` | 20 dk | Kararlaştırılmış CRC hesaplamasını ekle | F0 CRC kararındaki bağımsız referans vektör eşleşir | `F2-012` | `feat(parser): F2-013 kararlaştırılmış CRC hesaplamasını ekle` |
| [x] | `F2-014` | `0.75.0` | 20 dk | CRC alanlı format doğrulamasını bağla | Tek byte bozulması yakalanır; CRC'siz örnek dosya doğrulanmış sayılmaz | `F2-013` | `feat(parser): F2-014 cRC alanlı format doğrulamasını bağla` |
| [x] | `F2-015` | `0.76.0` | 20 dk | Bilinmeyen paket teşhisini ekle | Güvenilir uzunluk varsa sonraki pakete geçilir; yoksa konum raporlanır | `F2-014` | `feat(parser): F2-015 bilinmeyen paket teşhisini ekle` |

##### Fixture ve domain eşlemesi

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F2-016` | `0.77.0` | 20 dk | 32/64 byte örnek fixture yazıcısını ekle | Sekiz kayıt tam 544 byte üretir; ad ve zamanlar sözleşmeye uyar | `F2-015` | `feat(fixtures): F2-016 32/64 byte örnek fixture yazıcısını ekle` |
| [x] | `F2-017` | `0.78.0` | 20 dk | Kesik, bozuk ve sıra boşluklu fixture'ları ekle | Her fixture önceden belirlenen hata sonucunu üretir | `F2-016` | `test(parser): F2-017 kesik, bozuk ve sıra boşluklu fixture'ları ekle` |
| [x] | `F2-018` | `0.79.0` | 20 dk | CRC destekli format fixture'ını ekle | Geçerli ve tek byte bozulmuş dosya farklı doğrulama sonucu verir | `F2-017` | `test(parser): F2-018 cRC destekli format fixture'ını ekle` |
| [x] | `F2-019` | `0.80.0` | 20 dk | Sensör alanlarını kanal metadata'sına eşleştir | CH0–CH7 sırası, dtype ve birimler sözlükle eşleşir | `F2-018` | `feat(parser): F2-019 sensör alanlarını kanal metadata'sına eşleştir` |
| [x] | `F2-020` | `0.81.0` | 20 dk | Scale ve offset dönüşümünü ekle | Bilinen ham değer beklenen mühendislik değerine dönüşür | `F2-019` | `feat(parser): F2-020 scale ve offset dönüşümünü ekle` |
| [x] | `F2-021` | `0.82.0` | 20 dk | Calibration seçimini ve kalite eşlemesini ekle | Eksik calibration ve geçersiz örnek kalite bilgisini korur | `F2-020` | `feat(parser): F2-021 calibration seçimini ve kalite eşlemesini ekle` |
| [x] | `F2-022` | `0.83.0` | 20 dk | BIT maskesini durum ve değişim olaylarına çevir | Bilinen bit değişimi doğru bileşen için tek geçiş üretir | `F2-021` | `feat(parser): F2-022 bIT maskesini durum ve değişim olaylarına çevir` |
| [x] | `F2-023` | `0.84.0` | 20 dk | TX durumunu başlangıç/bitiş aralıklarına çevir | START/STOP ve açık kalan son aralık doğru temsil edilir | `F2-022` | `feat(parser): F2-023 tX durumunu başlangıç/bitiş aralıklarına çevir` |
| [x] | `F2-024` | `0.85.0` | 15 dk | Parser teşhislerini sistem olaylarına çevir | Hata zamanı, kaynak offseti, kategori ve severity korunur | `F2-023` | `feat(parser): F2-024 parser teşhislerini sistem olaylarına çevir` |
| [x] | `F2-025` | `0.86.0` | 20 dk | Cihaz tick dönüşüm adaptörünü ekle | Referans tick değerleri doğru ns üretir; ham tick saklanır | `F2-024` | `feat(time): F2-025 cihaz tick dönüşüm adaptörünü ekle` |
| [x] | `F2-026` | `0.87.0` | 20 dk | Wraparound ve saat resetini ayırt et | İki sentetik senaryo farklı teşhis ve zaman kalitesi üretir | `F2-025` | `feat(time): F2-026 wraparound ve saat resetini ayırt et` |
| [x] | `F2-027` | `0.88.0` | 20 dk | Tanımlı drift düzeltmesini uygula | Bilinen katsayı referans zamanı üretir; düzeltme metadata'da görünür | `F2-026` | `feat(time): F2-027 tanımlı drift düzeltmesini uygula` |

##### İndeks ve repository

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F2-028` | `0.89.0` | 20 dk | Kayıt offseti ve zaman indeksini oluştur | İndeks konumları tam kayıt sınırlarına işaret eder | `F2-027` | `feat(index): F2-028 kayıt offseti ve zaman indeksini oluştur` |
| [x] | `F2-029` | `0.90.0` | 20 dk | Kanal ve olay indekslerini oluştur | Kanal sorgusu ve severity özeti referans sayıları verir | `F2-028` | `feat(index): F2-029 kanal ve olay indekslerini oluştur` |
| [x] | `F2-030` | `0.91.0` | 20 dk | Kaynak fingerprint ve parser sürümünü kaydet | Kaynak değişikliği veya decoder değişikliği indeksi geçersiz kılar | `F2-029` | `feat(index): F2-030 kaynak fingerprint ve parser sürümünü kaydet` |
| [x] | `F2-031` | `0.92.0` | 20 dk | İndeks dosyasını atomik kaydet | Yarım geçici dosya geçerli indeksin üzerine alınmaz | `F2-030` | `feat(index): F2-031 indeks dosyasını atomik kaydet` |
| [x] | `F2-032` | `0.93.0` | 20 dk | Geçerli indeksi yeniden kullan | İkinci açılış mevcut indeksi kullanır; bozuk indeks yeniden üretilir | `F2-031` | `feat(index): F2-032 geçerli indeksi yeniden kullan` |
| [x] | `F2-033` | `0.94.0` | 20 dk | Dosya metadata ve kanal listesini sun | Dosya açılmadan sorgu reddedilir; açık dosya doğru kanal sayısı verir | `F2-032` | `feat(repository): F2-033 dosya metadata ve kanal listesini sun` |
| [x] | `F2-034` | `0.95.0` | 20 dk | İndeksli zaman aralığı sorgusunu ekle | Başlangıç/bitiş sınırları ve boş aralık beklenen örnekleri döndürür | `F2-033` | `feat(repository): F2-034 indeksli zaman aralığı sorgusunu ekle` |
| [x] | `F2-035` | `0.96.0` | 20 dk | Zaman ve kategoriye göre olay sorgula | Filtreler yalnız eşleşen olayları döndürür | `F2-034` | `feat(repository): F2-035 zaman ve kategoriye göre olay sorgula` |
| [x] | `F2-036` | `0.97.0` | 20 dk | Birden fazla kaydı ayrı kimlikle yönet | İki dosyanın kanal ve olay kimlikleri çakışmaz | `F2-035` | `feat(repository): F2-036 birden fazla kaydı ayrı kimlikle yönet` |
| [x] | `F2-037` | `0.98.0` | 15 dk | Decoded öğeden ham offsete erişim ekle | Seçilen öğe kaynak byte konumuyla eşleşir | `F2-036` | `feat(parser): F2-037 decoded öğeden ham offsete erişim ekle` |
| [x] | `F2-038` | `0.99.0` | 15 dk | Okuyucu kaynaklarını güvenli kapat | Dosya aç/kapat sonrası dosya kilidi ve handle kalmaz | `F2-037` | `fix(parser): F2-038 okuyucu kaynaklarını güvenli kapat` |
| [x] | `F2-039` | `0.100.0` | 20 dk | Bağımsız golden sonuçlarını parser ile karşılaştır | Kanal, örnek, olay, zaman ve CRC sonuçları referansla eşleşir | `F2-038` | `test(parser): F2-039 bağımsız golden sonuçlarını parser ile karşılaştır` |
| [x] | `F2-040` | `0.101.0` | 20 dk | Kaynak dosyanın değişmediğini doğrula | Geçerli ve bozuk dosya aç/kapat öncesi ve sonrası hash aynıdır | `F2-039` | `test(parser): F2-040 kaynak dosyanın değişmediğini doğrula` |
| [x] | `F2-041` | `0.102.0` | 15 dk | Parser milestone kabulünü kaydet | Geçerli, bozuk, CRC'li, çoklu dosya ve sorgu kontrolleri geçer | `F2-040` | `test(release): F2-041 parser milestone kabulünü kaydet` |

#### Faz 3 — MVP analiz arayüzü

Kabul: Bölüm 3.1 kapsamı ve Bölüm 23'ün bütün MVP kabul koşulları kanıtlarıyla tamamlanmış olmalı. Etiket: `ms/04-mvp`, sürüm: `v1.0.0`.

##### Dosya akışı ve worker altyapısı

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F3-001` | `0.103.0` | 15 dk | Tekli ve çoklu dosya açma seçicisini bağla | İptal mevcut oturumu korur; seçim dosya yükleme talebi üretir | `F2-041` | `feat(ui): F3-001 tekli ve çoklu dosya açma seçicisini bağla` |
| [x] | `F3-002` | `0.104.0` | 20 dk | Dosya yükleme worker'ını ekle | Yükleme sırasında pencere etkileşimlere yanıt verir | `F3-001` | `feat(app): F3-002 dosya yükleme worker'ını ekle` |
| [x] | `F3-003` | `0.105.0` | 20 dk | Yükleme ilerlemesi ve iptal eylemini ekle | İptal worker'a ulaşır; yarım kayıt açık dosya listesine girmez | `F3-002` | `feat(ui): F3-003 yükleme ilerlemesi ve iptal eylemini ekle` |
| [x] | `F3-004` | `0.106.0` | 20 dk | Eski istek sonucunun görünümü ezmesini önle | Hızlı iki açma isteğinde yalnız güncel sonuç uygulanır | `F3-003` | `fix(app): F3-004 eski istek sonucunun görünümü ezmesini önle` |
| [x] | `F3-005` | `0.107.0` | 20 dk | Dosya yükleme sonucunu repository ve ekrana bağla | Açılan dosyanın metadata ve kanalları görünür | `F3-004` | `feat(ui): F3-005 dosya yükleme sonucunu repository ve ekrana bağla` |
| [x] | `F3-006` | `0.108.0` | 15 dk | Format ve dosya erişim hatalarını göster | Kullanıcı mesajı anlaşılır; teknik ayrıntı logda bulunur | `F3-005` | `feat(ui): F3-006 format ve dosya erişim hatalarını göster` |
| [x] | `F3-007` | `0.109.0` | 20 dk | Dosya kapatma ve bağlı panel temizliğini ekle | Kapatılan dosyanın sorguları iptal olur; diğer kayıtlar çalışır | `F3-006` | `feat(ui): F3-007 dosya kapatma ve bağlı panel temizliğini ekle` |
| [x] | `F3-008` | `0.110.0` | 15 dk | Son dosyalar ve varsayılan klasörü kaydet | Yeniden açılışta liste korunur; eksik dosya anlaşılır hata verir | `F3-007` | `feat(settings): F3-008 son dosyalar ve varsayılan klasörü kaydet` |

##### Data Explorer

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F3-009` | `0.111.0` | 20 dk | Dosya ve kanal ağaç modelini ekle | Kayıt, cihaz, sensör ve kanal hiyerarşisi doğru görünür | `F3-008` | `feat(ui): F3-009 dosya ve kanal ağaç modelini ekle` |
| [x] | `F3-010` | `0.112.0` | 20 dk | Kanal ağacında lazy yüklemeyi ekle | Açılmamış dallar gerektiğinde yüklenir; binlerce kanal gezilebilir | `F3-009` | `perf(ui): F3-010 kanal ağacında lazy yüklemeyi ekle` |
| [x] | `F3-011` | `0.113.0` | 20 dk | Ad, ID, birim ve kaynak aramasını ekle | Her alan için bilinen eşleşme bulunur; temizleme tüm kanalları getirir | `F3-010` | `feat(ui): F3-011 ad, ID, birim ve kaynak aramasını ekle` |
| [x] | `F3-012` | `0.114.0` | 15 dk | Channels/Data Tree sekmeleri ve kategori filtrelerini bağla | Sensors, Acoustic, Navigation, Vehicle/Transmission ve BIT seçimleri doğru çalışır | `F3-011` | `feat(ui): F3-012 channels/Data Tree sekmeleri ve kategori filtrelerini bağla` |
| [x] | `F3-013` | `0.115.0` | 20 dk | Çift tıkla kanalı grafiğe ekle | Gerçek dosyadan seçilen kanal doğru zaman ekseninde görünür | `F3-012` | `feat(plot): F3-013 çift tıkla kanalı grafiğe ekle` |
| [x] | `F3-014` | `0.116.0` | 15 dk | Grafikten kanal kaldırmayı ekle | Seri ve legend temizlenir; diğer seriler korunur | `F3-013` | `feat(plot): F3-014 grafikten kanal kaldırmayı ekle` |
| [x] | `F3-015` | `0.117.0` | 20 dk | Kanal sürükle-bırak akışını ekle | Geçerli kanal mevcut veya boş grafiğe bırakılabilir | `F3-014` | `feat(ui): F3-015 kanal sürükle-bırak akışını ekle` |
| [x] | `F3-016` | `0.118.0` | 20 dk | Çoklu kanal ekleme eylemlerini ekle | Seçilen kanallar aynı veya ayrı grafiklerde açılır | `F3-015` | `feat(ui): F3-016 çoklu kanal ekleme eylemlerini ekle` |
| [x] | `F3-017` | `0.119.0` | 20 dk | Favori kanal gruplarını kaydet | Grup tekrar açılır; bulunamayan kanal ayrı raporlanır | `F3-016` | `feat(settings): F3-017 favori kanal gruplarını kaydet` |
| [x] | `F3-018` | `0.120.0` | 15 dk | Kanal sağ tık eylemlerini bağla | Plot, Inspect ve Copy Path doğru seçime uygulanır | `F3-017` | `feat(ui): F3-018 kanal sağ tık eylemlerini bağla` |

##### Grafik etkileşimleri

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F3-019` | `0.121.0` | 20 dk | Ortak zaman ekseninde çoklu seri çiz | Farklı kanalların zamanları aynı X koordinatına eşlenir | `F3-018` | `feat(plot): F3-019 ortak zaman ekseninde çoklu seri çiz` |
| [x] | `F3-020` | `0.122.0` | 20 dk | Farklı birimler için ikinci Y ekseni ekle | Seri doğru eksen ve birimle gösterilir | `F3-019` | `feat(plot): F3-020 farklı birimler için ikinci Y ekseni ekle` |
| [x] | `F3-021` | `0.123.0` | 15 dk | Pan etkileşimini bağla | Sürükleme görünür aralığı değiştirir; veri değişmez | `F3-020` | `feat(plot): F3-021 pan etkileşimini bağla` |
| [x] | `F3-022` | `0.124.0` | 15 dk | Yalnız X zoom modunu ekle | X aralığı değişirken Y aralığı sabit kalır | `F3-021` | `feat(plot): F3-022 yalnız X zoom modunu ekle` |
| [x] | `F3-023` | `0.125.0` | 15 dk | Yalnız Y zoom modunu ekle | Y aralığı değişirken X aralığı sabit kalır | `F3-022` | `feat(plot): F3-023 yalnız Y zoom modunu ekle` |
| [x] | `F3-024` | `0.126.0` | 15 dk | XY zoom modunu ekle | İki eksen seçilen bölgeye yakınlaşır | `F3-023` | `feat(plot): F3-024 xY zoom modunu ekle` |
| [x] | `F3-025` | `0.127.0` | 15 dk | Autoscale ve görünüm sıfırlamayı ekle | Görünür veriye sığdırma ve ilk aralığa dönüş çalışır | `F3-024` | `feat(plot): F3-025 autoscale ve görünüm sıfırlamayı ekle` |
| [x] | `F3-026` | `0.128.0` | 20 dk | Crosshair ve cursor okumasını ekle | Cursor zamanı ve en yakın örnek değeri doğru gösterilir | `F3-025` | `feat(plot): F3-026 crosshair ve cursor okumasını ekle` |
| [x] | `F3-027` | `0.129.0` | 20 dk | İki cursor fark ölçümünü ekle | Delta zaman, değer ve sıfır olmayan süre için frekans doğrudur | `F3-026` | `feat(plot): F3-027 iki cursor fark ölçümünü ekle` |
| [x] | `F3-028` | `0.130.0` | 15 dk | Zaman bölgesi seçimini ekle | Seçili başlangıç/bitiş repository aralığına dönüşür | `F3-027` | `feat(plot): F3-028 zaman bölgesi seçimini ekle` |
| [x] | `F3-029` | `0.131.0` | 15 dk | Seçili bölgeye yakınlaşmayı bağla | Grafik yalnız seçilen zaman aralığını gösterir | `F3-028` | `feat(plot): F3-029 seçili bölgeye yakınlaşmayı bağla` |
| [x] | `F3-030` | `0.132.0` | 20 dk | Legend gizleme ve solo eylemlerini ekle | Seri görünürlüğü ve solo geri dönüşü doğru çalışır | `F3-029` | `feat(plot): F3-030 legend gizleme ve solo eylemlerini ekle` |
| [x] | `F3-031` | `0.133.0` | 15 dk | Seri rengi, çizgi ve marker ayarını ekle | Aynı kanal paneller arasında tutarlı varsayılan renkle açılır | `F3-030` | `feat(plot): F3-031 seri rengi, çizgi ve marker ayarını ekle` |
| [x] | `F3-032` | `0.134.0` | 20 dk | Paneller arasında X senkronizasyonunu ekle | Bir grafikte gezinme bağlı grafikleri günceller; döngü oluşmaz | `F3-031` | `feat(plot): F3-032 paneller arasında X senkronizasyonunu ekle` |
| [x] | `F3-033` | `0.135.0` | 20 dk | Grafik tabı ve bölünmüş görünüm ekle | Paneller açılır, bölünür ve bağımsız kapatılır | `F3-032` | `feat(ui): F3-033 grafik tabı ve bölünmüş görünüm ekle` |
| [x] | `F3-034` | `0.136.0` | 15 dk | Panel kaynak sınırını ve kapatma temizliğini ekle | Kapanan panelin signal ve sorgu kaynakları serbest kalır | `F3-033` | `perf(ui): F3-034 panel kaynak sınırını ve kapatma temizliğini ekle` |

##### Inspector ve istatistik

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F3-035` | `0.137.0` | 15 dk | Seçili kanal metadata'sını Inspector'a bağla | Kanal değişince ID, birim, dtype ve kaynak güncellenir | `F3-034` | `feat(ui): F3-035 seçili kanal metadata'sını Inspector'a bağla` |
| [x] | `F3-036` | `0.138.0` | 20 dk | Inspector görünüm ayarlarını grafiğe bağla | Eksen ve min/max değişikliği seçilen grafiğe uygulanır | `F3-035` | `feat(ui): F3-036 ınspector görünüm ayarlarını grafiğe bağla` |
| [x] | `F3-037` | `0.139.0` | 20 dk | Count, min, max ve mean hesabını ekle | Bilinen kısa dizi beklenen istatistikleri üretir | `F3-036` | `feat(analysis): F3-037 count, min, max ve mean hesabını ekle` |
| [x] | `F3-038` | `0.140.0` | 20 dk | Median, RMS, std ve peak-to-peak ekle | Referans dizi sonuçlarıyla eşleşir; boş aralık tanımlı gösterilir | `F3-037` | `feat(analysis): F3-038 median, RMS, std ve peak-to-peak ekle` |
| [x] | `F3-039` | `0.141.0` | 20 dk | ROI istatistiklerini dashboard kartına bağla | Sağ alt merkez kartı seçilen kanalın mean, std, RMS, min, max ve peak-peak değerlerini gösterir | `F3-038` | `feat(ui): F3-039 rOI istatistiklerini dashboard kartına bağla` |
| [x] | `F3-040` | `0.142.0` | 20 dk | Geliştirici ham kayıt görünümünü ekle | Seçim kaynak offseti ve ham/ölçeklenmiş değeri gösterir | `F3-039` | `feat(ui): F3-040 geliştirici ham kayıt görünümünü ekle` |
| [x] | `F3-041` | `0.143.0` | 20 dk | Görünüm ayarları için undo/redo ekle | Renk veya eksen değişikliği geri alınıp yeniden uygulanır | `F3-040` | `feat(app): F3-041 görünüm ayarları için undo/redo ekle` |

##### Events, BIT ve TX

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F3-042` | `0.144.0` | 20 dk | Ortak olay tablo modelini ekle | Bölüm 5.5 sütunları doğru domain alanlarını gösterir | `F3-041` | `feat(ui): F3-042 ortak olay tablo modelini ekle` |
| [x] | `F3-043` | `0.145.0` | 20 dk | Zaman, severity, kaynak ve metin filtrelerini ekle | Birleşik filtre sonucu beklenen olay kümesidir | `F3-042` | `feat(ui): F3-043 zaman, severity, kaynak ve metin filtrelerini ekle` |
| [x] | `F3-044` | `0.146.0` | 15 dk | Olay seçimini Inspector detayına bağla | Kaynak, kod ve ilgili kanallar doğru gösterilir | `F3-043` | `feat(ui): F3-044 olay seçimini Inspector detayına bağla` |
| [x] | `F3-045` | `0.147.0` | 20 dk | Olay zaman işaretlerini çiz | Olay zamanı grafik X koordinatıyla eşleşir | `F3-044` | `feat(plot): F3-045 olay zaman işaretlerini çiz` |
| [x] | `F3-046` | `0.148.0` | 20 dk | Olay çift tıklamasını ortak zamana bağla | Senkronize grafikler seçilen olay zamanına gider | `F3-045` | `feat(ui): F3-046 olay çift tıklamasını ortak zamana bağla` |
| [x] | `F3-047` | `0.149.0` | 20 dk | TX aralıklarını gölgeli bölge olarak çiz | START/STOP sınırları zaman ekseniyle eşleşir | `F3-046` | `feat(plot): F3-047 tX aralıklarını gölgeli bölge olarak çiz` |
| [x] | `F3-048` | `0.150.0` | 15 dk | Transmission sekmesini TX aralıklarına bağla | Seçili kaydın TX durumu ve zaman aralıkları sekmede görünür | `F3-047` | `feat(ui): F3-048 transmission sekmesini TX aralıklarına bağla` |
| [x] | `F3-049` | `0.151.0` | 20 dk | Yakın tekrar olaylarını grupla | Grup sayısı ve açılan ayrıntılar özgün olayları korur | `F3-048` | `feat(ui): F3-049 yakın tekrar olaylarını grupla` |
| [x] | `F3-050` | `0.152.0` | 15 dk | Marker ve TX görünürlüğü kontrollerini ekle | Görünürlük değişimi olay verisini etkilemez | `F3-049` | `feat(ui): F3-050 marker ve TX görünürlüğü kontrollerini ekle` |
| [x] | `F3-051` | `0.153.0` | 20 dk | Sağ BIT kartını alt sistem durumlarına bağla | Genel özet en yüksek severity'yi yansıtır; Warning varken tümü normal yazmaz | `F3-050` | `feat(ui): F3-051 sağ BIT kartını alt sistem durumlarına bağla` |
| [x] | `F3-052` | `0.154.0` | 15 dk | Run BIT Analysis eylemini kayıt analizine bağla | Seçili kaydın BIT özeti yenilenir; cihaz komutu gönderilmez | `F3-051` | `feat(ui): F3-052 run BIT Analysis eylemini kayıt analizine bağla` |
| [x] | `F3-053` | `0.155.0` | 15 dk | Yükleme ve analiz mesajlarını alt loga bağla | Zaman damgalı durum mesajları görünür; ham payload loga düşmez | `F3-052` | `feat(ui): F3-053 yükleme ve analiz mesajlarını alt loga bağla` |

##### Timeline ve playback

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F3-054` | `0.156.0` | 20 dk | Kayıt geneli Timeline özetini çiz | Başlangıç, bitiş ve olay yoğunluğu doğru konumlanır | `F3-053` | `feat(ui): F3-054 kayıt geneli Timeline özetini çiz` |
| [x] | `F3-055` | `0.157.0` | 20 dk | Timeline viewport seçimini grafiğe bağla | Bölge taşıma tüm bağlı grafiklerin zaman aralığını değiştirir | `F3-054` | `feat(ui): F3-055 timeline viewport seçimini grafiğe bağla` |
| [x] | `F3-056` | `0.158.0` | 20 dk | Play, pause ve stop durum makinesini ekle | Geçişler GUI olmadan doğrulanır; stop başlangıca döner | `F3-055` | `feat(playback): F3-056 play, pause ve stop durum makinesini ekle` |
| [x] | `F3-057` | `0.159.0` | 20 dk | Kayıt zamanına göre ilerleme saatini ekle | 125 ms kayıt sınırları doğru sırayla geçilir | `F3-056` | `feat(playback): F3-057 kayıt zamanına göre ilerleme saatini ekle` |
| [x] | `F3-058` | `0.160.0` | 15 dk | Oynatma hızlarını bağla | 0.25x–10x seçenekleri kayıt zamanı ilerlemesini ölçekler | `F3-057` | `feat(playback): F3-058 oynatma hızlarını bağla` |
| [x] | `F3-059` | `0.161.0` | 20 dk | Zamana ve önceki/sonraki olaya gitmeyi ekle | Sınır dışı zaman güvenli sınırlanır; olay sırası korunur | `F3-058` | `feat(playback): F3-059 zamana ve önceki/sonraki olaya gitmeyi ekle` |
| [x] | `F3-060` | `0.162.0` | 20 dk | Scrubbing sorgularını debounce et | Hızlı sürüklemede son konum çizilir; eski sorgu görünümü ezmez | `F3-059` | `perf(ui): F3-060 scrubbing sorgularını debounce et` |
| [x] | `F3-061` | `0.163.0` | 15 dk | UTC, yerel ve geçen süre gösterimini ekle | Üç görünüm aynı kanonik anı temsil eder | `F3-060` | `feat(ui): F3-061 uTC, yerel ve geçen süre gösterimini ekle` |

##### Dışa aktarma ve workspace

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F3-062` | `0.164.0` | 20 dk | Seçili grafiği PNG olarak dışa aktar | Dosya açılabilir; başlık ve birimler görünür | `F3-061` | `feat(export): F3-062 seçili grafiği PNG olarak dışa aktar` |
| [x] | `F3-063` | `0.165.0` | 20 dk | Seçili grafiği SVG olarak dışa aktar | Vektörel çıktı açılır; seri ve eksenler görünür | `F3-062` | `feat(export): F3-063 seçili grafiği SVG olarak dışa aktar` |
| [x] | `F3-064` | `0.166.0` | 20 dk | Seçili kanal ve aralığı CSV olarak yaz | Satır sayısı, zaman, birim ve kaynak metadata doğru çıkar | `F3-063` | `feat(export): F3-064 seçili kanal ve aralığı CSV olarak yaz` |
| [x] | `F3-065` | `0.167.0` | 20 dk | Export hedefi ve üzerine yazma kontrolünü ekle | Var olan dosya onaysız değişmez; raw/processed seçimi açıktır | `F3-064` | `feat(ui): F3-065 export hedefi ve üzerine yazma kontrolünü ekle` |
| [x] | `F3-066` | `0.168.0` | 20 dk | Büyük export için worker ve iptal ekle | UI yanıt verir; iptal yarım dosyayı tamamlanmış diye sunmaz | `F3-065` | `feat(export): F3-066 büyük export için worker ve iptal ekle` |
| [x] | `F3-067` | `0.169.0` | 20 dk | Sürümlü workspace JSON modelini ekle | Panel, kanal, görünüm ve filtre alanları serialize edilebilir | `F3-066` | `feat(workspace): F3-067 sürümlü workspace JSON modelini ekle` |
| [x] | `F3-068` | `0.170.0` | 20 dk | Dock ve grafik düzenini kaydet | Dosya açık tabları, eksenleri ve senkronizasyon gruplarını içerir | `F3-067` | `feat(workspace): F3-068 dock ve grafik düzenini kaydet` |
| [x] | `F3-069` | `0.171.0` | 20 dk | Workspace dosyasını geri yükle | Yeniden açılışta aynı düzen ve kanal görünümü oluşur | `F3-068` | `feat(workspace): F3-069 workspace dosyasını geri yükle` |
| [x] | `F3-070` | `0.172.0` | 20 dk | Eksik kaynak ve bozuk workspace davranışını ekle | Eksik dosya bildirilir; açık oturum kontrolsüz silinmez | `F3-069` | `fix(workspace): F3-070 eksik kaynak ve bozuk workspace davranışını ekle` |
| [x] | `F3-071` | `0.173.0` | 20 dk | Workspace sürüm geçiş yolunu ekle | Eski örnek sürüm dönüştürülür; bilinmeyen yeni sürüm anlaşılır reddedilir | `F3-070` | `feat(workspace): F3-071 workspace sürüm geçiş yolunu ekle` |
| [x] | `F3-072` | `0.174.0` | 20 dk | Bölüm 16 klavye kısayollarını bağla | Odak grafikteyken temel dosya, oynatma ve zoom kısayolları çalışır | `F3-071` | `feat(ui): F3-072 bölüm 16 klavye kısayollarını bağla` |
| [x] | `F3-073` | `0.175.0` | 20 dk | Klavye odak sırasını ve açıklamaları düzenle | Ana akış yalnız klavyeyle tamamlanabilir | `F3-072` | `fix(ui): F3-073 klavye odak sırasını ve açıklamaları düzenle` |
| [x] | `F3-074` | `0.176.0` | 20 dk | Windows ölçekleme ve kontrast kontrolünü kaydet | 100/125/150/200 yüzde ölçeklerde kritik metin ve kontroller kesilmez | `F3-073` | `test(ui): F3-074 windows ölçekleme ve kontrast kontrolünü kaydet` |

##### MVP doğrulaması

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F3-075` | `0.177.0` | 20 dk | Dosyadan olay gezinmesine entegrasyon senaryosu ekle | BIN → repository → grafik → olay zamanı zinciri geçer | `F3-074` | `test(ui): F3-075 dosyadan olay gezinmesine entegrasyon senaryosu ekle` |
| [x] | `F3-076` | `0.178.0` | 20 dk | Kritik plot ve workspace GUI kontrollerini ekle | Zoom, ROI ve workspace round-trip davranışları doğrulanır | `F3-075` | `test(ui): F3-076 kritik plot ve workspace GUI kontrollerini ekle` |
| [x] | `F3-077` | `0.179.0` | 20 dk | MVP etkileşim bütçesini ölç | Cursor, play/pause, olay gezinmesi ve ağaç sonuçları hedeflerle karşılaştırılır | `F3-076` | `perf(ui): F3-077 mVP etkileşim bütçesini ölç` |
| [x] | `F3-078` | `0.180.0` | 20 dk | Operatör ve mühendis MVP senaryolarını kaydet | Bölüm 17.5'in MVP senaryoları ve Bölüm 23 için kanıt bağlantıları vardır | `F3-077` | `test(acceptance): F3-078 operatör ve mühendis MVP senaryolarını kaydet` |
| [x] | `F3-079` | `0.181.0` | 20 dk | MVP ekran görüntüsünü ana mockup ile karşılaştır | Dokuz bölge ve yerleşim eşleşir; FFT/spektrogram işlevleri v2 olarak pasiftir | `F3-078` | `test(ui): F3-079 mVP ekran görüntüsünü ana mockup ile karşılaştır` |
| [x] | `F3-080` | `1.0.0` | 15 dk | MVP kabulünü kapat ve major sürümü hazırla | Bölüm 3.1 ve 23 tamdır; mockup yerleşimi ve zorunlu kontroller geçer | `F3-079` | `chore(release): F3-080 mVP kabulünü kapat ve major sürümü hazırla` |

#### Faz 4 — Mockup analiz panosu ve büyük veri performansı

Kabul: Mockup'taki ana analiz panosu gerçek hesaplamalarla çalışmalı; analiz doğruluğu, oturum ve performans kontrolleri geçmeli. Etiket: `ms/05-analysis`, sürüm: `v2.0.0`.

##### İşlem zinciri

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F4-001` | `1.1.0` | 20 dk | İşlem adımı ve parametre modelini ekle | Her adım girdi kanalı ve tekrar üretilebilir parametre taşır | `F3-080` | `feat(processing): F4-001 işlem adımı ve parametre modelini ekle` |
| [x] | `F4-002` | `1.2.0` | 20 dk | Sıralı işlem zinciri yürütücüsünü ekle | İki adım tanımlı sırayla uygulanır; ham dizi değişmez | `F4-001` | `feat(processing): F4-002 sıralı işlem zinciri yürütücüsünü ekle` |
| [x] | `F4-003` | `1.3.0` | 20 dk | DSP işlerini worker üzerinden çalıştır | Uzun hesaplama UI'ı durdurmaz; güncel iş sonucu yayınlanır | `F4-002` | `feat(processing): F4-003 dSP işlerini worker üzerinden çalıştır` |
| [x] | `F4-004` | `1.4.0` | 20 dk | DSP iptal ve eski sonuç denetimini ekle | İptal edilen veya eski seçime ait sonuç grafiğe uygulanmaz | `F4-003` | `feat(processing): F4-004 dSP iptal ve eski sonuç denetimini ekle` |
| [x] | `F4-005` | `1.5.0` | 20 dk | NaN ve kalite bayrağı politikasını uygula | Geçersiz örnekler sessizce geçerli değere dönüşmez | `F4-004` | `feat(processing): F4-005 naN ve kalite bayrağı politikasını uygula` |
| [x] | `F4-006` | `1.6.0` | 20 dk | Analysis Tools işlem listesi editörünü ekle | Adım ekleme, silme ve sıralama modelde aynı sırayı oluşturur | `F4-005` | `feat(ui): F4-006 analysis Tools işlem listesi editörünü ekle` |
| [x] | `F4-007` | `1.7.0` | 20 dk | Analiz parametre hatalarını alanlarda göster | Geçersiz değer işlem başlamadan açıklanır | `F4-006` | `feat(ui): F4-007 analiz parametre hatalarını alanlarda göster` |
| [x] | `F4-008` | `1.8.0` | 15 dk | Seçili kanala uygulama ve filtreli veri görünümünü bağla | Apply Filter ile seçili kanal işlenir; Show filtered data görünürlüğü değiştirir | `F4-007` | `feat(ui): F4-008 seçili kanala uygulama ve filtreli veri görünümünü bağla` |

##### 125 ms bloklarda yüksek örnek hızlı akustik veri

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F4-009` | `1.9.0` | 20 dk | Ham akustik blok formatının ayrı sürümünü tanımla | Kanal, sample rate, örnek sayısı ve payload boyutu tanımlıdır (bkz. 8.3); 8.2 örneği değişmez | `F4-008` | `docs(format): F4-009 ham akustik blok formatının ayrı sürümünü tanımla` |
| [x] | `F4-010` | `1.10.0` | 20 dk | 48 kHz akustik blok fixture üretecini ekle | Her kanalda 125 ms için 6000 örnek oluşur; bloklar Data sırasını korur | `F4-009` | `feat(fixtures): F4-010 48 kHz akustik blok fixture üretecini ekle` |
| [x] | `F4-011` | `1.11.0` | 20 dk | Akustik blok payload decoder'ını ekle | Kanal ve örnek sırası fixture referansıyla eşleşir | `F4-010` | `feat(parser): F4-011 akustik blok payload decoder'ını ekle` |
| [x] | `F4-012` | `1.12.0` | 20 dk | Blok içi örnek zamanlarını üret | 6000 örnek 125 ms aralığı kapsar; blok sınırında örnek tekrarı olmaz | `F4-011` | `feat(time): F4-012 blok içi örnek zamanlarını üret` |
| [x] | `F4-013` | `1.13.0` | 20 dk | Akustik blokları zaman sorgusuna bağla | Bloklar arası seçim doğru örnek aralığını döndürür | `F4-012` | `feat(repository): F4-013 akustik blokları zaman sorgusuna bağla` |
| [x] | `F4-014` | `1.14.0` | 20 dk | Akustik boyut ve sample rate sınırlarını doğrula | Bozuk sample count reddedilir; 8 Hz telemetri 10 kHz veri diye sunulmaz | `F4-013` | `test(parser): F4-014 akustik boyut ve sample rate sınırlarını doğrula` |

##### Temel sayısal işlemler

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F4-015` | `1.15.0` | 20 dk | Detrend ve DC kaldırma hesabını ekle | Sabit ofset ve doğrusal trend referans sonucu üretir | `F4-014` | `feat(processing): F4-015 detrend ve DC kaldırma hesabını ekle` |
| [x] | `F4-016` | `1.16.0` | 15 dk | Detrend türü seçimini işlem editörüne bağla | Seçili tür tekrar açılan zincirde korunur | `F4-015` | `feat(ui): F4-016 detrend türü seçimini işlem editörüne bağla` |
| [x] | `F4-017` | `1.17.0` | 20 dk | Moving average hesabını ekle | Bilinen kısa dizide pencere ve kenar davranışı tanımlı sonucu verir | `F4-016` | `feat(processing): F4-017 moving average hesabını ekle` |
| [x] | `F4-018` | `1.18.0` | 15 dk | Moving average pencere kontrolünü bağla | Sıfır veya aşırı pencere işlem başlamadan reddedilir | `F4-017` | `feat(ui): F4-018 moving average pencere kontrolünü bağla` |
| [x] | `F4-019` | `1.19.0` | 20 dk | Normalize hesabını ekle | Referans genlik doğru ölçeklenir; sıfır sinyal bölme hatası üretmez | `F4-018` | `feat(processing): F4-019 normalize hesabını ekle` |
| [x] | `F4-020` | `1.20.0` | 15 dk | Normalize seçimini işlem editörüne bağla | Normalize adımı seçili kanal grafiğine uygulanır | `F4-019` | `feat(ui): F4-020 normalize seçimini işlem editörüne bağla` |
| [x] | `F4-021` | `1.21.0` | 20 dk | Pencereli RMS ve envelope hesabını ekle | Sabit genlikli sinyalde beklenen RMS/envelope oluşur | `F4-020` | `feat(processing): F4-021 pencereli RMS ve envelope hesabını ekle` |
| [x] | `F4-022` | `1.22.0` | 15 dk | RMS/envelope pencere kontrollerini bağla | Pencere süresi sample rate üzerinden doğru örnek sayısına dönüşür | `F4-021` | `feat(ui): F4-022 rMS/envelope pencere kontrollerini bağla` |
| [x] | `F4-023` | `1.23.0` | 20 dk | Phase unwrap hesabını ekle | Bilinen faz sıçramaları sürekliliğe dönüşür | `F4-022` | `feat(processing): F4-023 phase unwrap hesabını ekle` |
| [x] | `F4-024` | `1.24.0` | 15 dk | Phase unwrap parametrelerini bağla | Faz birimi ve eşik hataları işlem öncesi görünür | `F4-023` | `feat(ui): F4-024 phase unwrap parametrelerini bağla` |
| [x] | `F4-025` | `1.25.0` | 20 dk | Resample/decimate işlemini ekle | Hedef sample rate, örnek sayısı ve alias denetimi referansla eşleşir | `F4-024` | `feat(processing): F4-025 resample/decimate işlemini ekle` |
| [x] | `F4-026` | `1.26.0` | 15 dk | Resample hedef frekans kontrolünü bağla | Yeni sample rate türetilmiş kanal metadata'sında görünür | `F4-025` | `feat(ui): F4-026 resample hedef frekans kontrolünü bağla` |

##### Filtreler

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F4-027` | `1.27.0` | 20 dk | Low-pass filtre hesabını ekle | Düşük frekans korunur; yüksek frekans referansa uygun bastırılır | `F4-026` | `feat(processing): F4-027 low-pass filtre hesabını ekle` |
| [x] | `F4-028` | `1.28.0` | 15 dk | Low-pass cutoff ve order sınırlarını doğrula | Nyquist dışındaki cutoff ve geçersiz order reddedilir | `F4-027` | `test(processing): F4-028 low-pass cutoff ve order sınırlarını doğrula` |
| [x] | `F4-029` | `1.29.0` | 15 dk | Low-pass araç alanlarını bağla | Mockup Filter kartından geçerli parametreyle sonuç çizilir | `F4-028` | `feat(ui): F4-029 low-pass araç alanlarını bağla` |
| [x] | `F4-030` | `1.30.0` | 20 dk | High-pass filtre hesabını ekle | DC ve düşük frekans referansa uygun bastırılır | `F4-029` | `feat(processing): F4-030 high-pass filtre hesabını ekle` |
| [x] | `F4-031` | `1.31.0` | 15 dk | High-pass sınır ve transient davranışını doğrula | Kısa dizi ve sınır parametreleri kontrollü sonuç verir | `F4-030` | `test(processing): F4-031 high-pass sınır ve transient davranışını doğrula` |
| [x] | `F4-032` | `1.32.0` | 15 dk | High-pass seçimini araç kartına bağla | Tür değişimi doğru parametrelerle zincire kaydedilir | `F4-031` | `feat(ui): F4-032 high-pass seçimini araç kartına bağla` |
| [x] | `F4-033` | `1.33.0` | 20 dk | Band-pass filtre hesabını ekle | Bant içi ve dışı tonlar referans davranışı gösterir | `F4-032` | `feat(processing): F4-033 band-pass filtre hesabını ekle` |
| [x] | `F4-034` | `1.34.0` | 15 dk | Band-pass alt/üst sınırlarını doğrula | Ters veya Nyquist dışı bant işlem başlamadan reddedilir | `F4-033` | `test(processing): F4-034 band-pass alt/üst sınırlarını doğrula` |
| [x] | `F4-035` | `1.35.0` | 15 dk | Band-pass iki cutoff alanını bağla | İki sınır doğru sırayla hesaplamaya iletilir | `F4-034` | `feat(ui): F4-035 band-pass iki cutoff alanını bağla` |
| [x] | `F4-036` | `1.36.0` | 20 dk | Notch filtre hesabını ekle | Hedef ton bastırılır; komşu ton referans toleransta kalır | `F4-035` | `feat(processing): F4-036 notch filtre hesabını ekle` |
| [x] | `F4-037` | `1.37.0` | 15 dk | Notch frekans ve Q sınırlarını doğrula | Geçersiz frekans ve Q açıklamalı hata üretir | `F4-036` | `test(processing): F4-037 notch frekans ve Q sınırlarını doğrula` |
| [x] | `F4-038` | `1.38.0` | 15 dk | Notch frekans ve Q kontrollerini bağla | Uygulanan ayarlar kaydedilip yeniden yüklenir | `F4-037` | `feat(ui): F4-038 notch frekans ve Q kontrollerini bağla` |

##### FFT, PSD, spektrogram ve waterfall

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F4-039` | `1.39.0` | 20 dk | Window üretimi ve normalizasyonunu ekle | Seçili pencerenin genlik/enerji katsayıları referansla eşleşir | `F4-038` | `feat(analysis): F4-039 window üretimi ve normalizasyonunu ekle` |
| [x] | `F4-040` | `1.40.0` | 20 dk | Tek taraflı FFT hesabını ekle | Bilinen sinüsün tepe frekansı ve genliği doğru çıkar | `F4-039` | `feat(analysis): F4-040 tek taraflı FFT hesabını ekle` |
| [x] | `F4-041` | `1.41.0` | 20 dk | FFT, dB ve Nyquist doğrulamalarını ekle | DC, Nyquist, sıfır sinyal ve kısa pencere kontrollü sonuç verir | `F4-040` | `test(analysis): F4-041 fFT, dB ve Nyquist doğrulamalarını ekle` |
| [x] | `F4-042` | `1.42.0` | 20 dk | Seçili aralık FFT'sini mockup alt grafiğine bağla | ROI değişince FFT yenilenir; frekans ve genlik birimi görünür | `F4-041` | `feat(ui): F4-042 seçili aralık FFT'sini mockup alt grafiğine bağla` |
| [x] | `F4-043` | `1.43.0` | 20 dk | Welch PSD hesabını ekle | Referans sinyalin yoğunluğu ve entegre gücü toleransta eşleşir | `F4-042` | `feat(analysis): F4-043 welch PSD hesabını ekle` |
| [x] | `F4-044` | `1.44.0` | 15 dk | PSD pencere, overlap ve birim sınırlarını doğrula | Geçersiz overlap reddedilir; güç/Hz ve dB dönüşümü doğrudur | `F4-043` | `test(analysis): F4-044 pSD pencere, overlap ve birim sınırlarını doğrula` |
| [x] | `F4-045` | `1.45.0` | 20 dk | Spectrum sekmesinde PSD görünümünü ekle | FFT/PSD seçimi eksen etiketini ve doğru sonucu değiştirir | `F4-044` | `feat(ui): F4-045 spectrum sekmesinde PSD görünümünü ekle` |
| [x] | `F4-046` | `1.46.0` | 20 dk | STFT ve spektrogram matrisini hesapla | Chirp eğimi, zaman sütunları ve frekans satırları referansla eşleşir | `F4-045` | `feat(analysis): F4-046 sTFT ve spektrogram matrisini hesapla` |
| [x] | `F4-047` | `1.47.0` | 20 dk | STFT kenar, overlap ve eksen eşlemesini doğrula | Son pencere ve boş seçim tanımlı davranır; eksenler kaymaz | `F4-046` | `test(analysis): F4-047 sTFT kenar, overlap ve eksen eşlemesini doğrula` |
| [x] | `F4-048` | `1.48.0` | 20 dk | Mockup orta spektrogramını sonuçlara bağla | Hidrofon, zaman, frekans ve dB renk ölçeği veriyi doğru gösterir | `F4-047` | `feat(ui): F4-048 mockup orta spektrogramını sonuçlara bağla` |
| [x] | `F4-049` | `1.49.0` | 15 dk | Spektrogram renk ölçeği kontrollerini ekle | Algısal düzgün colormap ve dB sınırları okunabilir kalır | `F4-048` | `feat(ui): F4-049 spektrogram renk ölçeği kontrollerini ekle` |
| [x] | `F4-050` | `1.50.0` | 20 dk | Waterfall zaman dilimi modelini ekle | Yeni dilim eklenir; geçmiş için belirlenen sınır korunur | `F4-049` | `feat(analysis): F4-050 waterfall zaman dilimi modelini ekle` |
| [x] | `F4-051` | `1.51.0` | 20 dk | Waterfall görünümünü ekle | Zaman dilimleri doğru sırayla çizilir; birimler açıktır | `F4-050` | `feat(ui): F4-051 waterfall görünümünü ekle` |
| [x] | `F4-052` | `1.52.0` | 20 dk | Zaman serisi, STFT, FFT ve istatistiği birlikte bağla | Mockup'ın dört merkez bölgesi aynı seçimle tutarlı güncellenir | `F4-051` | `feat(ui): F4-052 zaman serisi, STFT, FFT ve istatistiği birlikte bağla` |

##### Büyük veri ve kaynak yönetimi

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F4-053` | `1.53.0` | 20 dk | Memory mapping üzerinden blok okuma ekle | Seçili blok okunur; bütün dosya RAM'e kopyalanmaz | `F4-052` | `perf(parser): F4-053 memory mapping üzerinden blok okuma ekle` |
| [x] | `F4-054` | `1.54.0` | 20 dk | Yalnız görünür zaman bloklarını yükle | Dar sorgu ilgili bloklarla sınırlı kalır | `F4-053` | `perf(repository): F4-054 yalnız görünür zaman bloklarını yükle` |
| [x] | `F4-055` | `1.55.0` | 20 dk | Piksel genişliğine göre max_points uygula | Viewport daraldığında dönen nokta sayısı bütçeye uyar | `F4-054` | `perf(repository): F4-055 piksel genişliğine göre max_points uygula` |
| [x] | `F4-056` | `1.56.0` | 20 dk | Min/max envelope downsampling ekle | Dar impulslar görünür kalır; sonuç sıralı zaman taşır | `F4-055` | `perf(analysis): F4-056 min/max envelope downsampling ekle` |
| [x] | `F4-057` | `1.57.0` | 20 dk | Çok seviyeli özet bloklarını üret | Her seviye referans min/max özetleriyle eşleşir | `F4-056` | `perf(index): F4-057 çok seviyeli özet bloklarını üret` |
| [x] | `F4-058` | `1.58.0` | 20 dk | Viewport için uygun özet seviyesini seç | Farklı zoom seviyeleri bütçeye uygun veri döndürür | `F4-057` | `perf(repository): F4-058 viewport için uygun özet seviyesini seç` |
| [x] | `F4-059` | `1.59.0` | 20 dk | Bellek sınırlı LRU cache ekle | Bütçe aşılınca eski girdiler çıkar; ölçülen kullanım raporlanır | `F4-058` | `perf(cache): F4-059 bellek sınırlı LRU cache ekle` |
| [x] | `F4-060` | `1.60.0` | 20 dk | Cache anahtarına kaynak ve işlem sürümünü ekle | Kaynak, parametre veya calibration değişince eski sonuç kullanılmaz | `F4-059` | `fix(cache): F4-060 cache anahtarına kaynak ve işlem sürümünü ekle` |
| [x] | `F4-061` | `1.61.0` | 20 dk | Render sıklığını ve gizli panel güncellemelerini sınırla | Gizli panel gereksiz çizim yapmaz; görünürken son veri gelir | `F4-060` | `perf(ui): F4-061 render sıklığını ve gizli panel güncellemelerini sınırla` |
| [x] | `F4-062` | `1.62.0` | 20 dk | Sorgu, render ve indeks sürelerini kaydet | Aynı session içinde maliyetler ayrı ölçülebilir | `F4-061` | `feat(logging): F4-062 sorgu, render ve indeks sürelerini kaydet` |
| [x] | `F4-063` | `1.63.0` | 20 dk | Büyük dosya üretim koşusunu hazırla | 1 GB, 10 GB ve hedef boyut için komut, seed ve beklenen kayıt sayısı kaydedilir | `F4-062` | `perf(fixtures): F4-063 büyük dosya üretim koşusunu hazırla` |
| [x] | `F4-064` | `1.64.0` | 20 dk | Büyük dosya benchmark koşusunu hazırla | Metadata, sorgu, FPS ve bellek sonuçları makine bilgisiyle üretilir | `F4-063` | `perf(bench): F4-064 büyük dosya benchmark koşusunu hazırla` |
| [x] | `F4-065` | `1.65.0` | 20 dk | Büyük dosya koşusunun sonuçlarını değerlendir | Bölüm 11.1 hedeflerinin geçtiği veya saptığı kanıtlanır | `F4-064` | `docs(perf): F4-065 büyük dosya koşusunun sonuçlarını değerlendir` |
| [x] | `F4-066` | `1.66.0` | 20 dk | İndeks kesintisi ve cache kurtarmayı doğrula | Yarım indeks kullanılmaz; yeniden üretim kaynak veriyi değiştirmez | `F4-065` | `test(index): F4-066 indeks kesintisi ve cache kurtarmayı doğrula` |
| [x] | `F4-067` | `1.67.0` | 15 dk | Profil sonucuyla native hızlandırma ADR'sini yaz | Ölçülen darboğaza göre gerekçe vardır; zorunlu native kapsamı ayrıca bölünür | `F4-066` | `docs(architecture): F4-067 profil sonucuyla native hızlandırma ADR'sini yaz` |

##### Türetilmiş kanallar ve analiz oturumu

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F4-068` | `1.68.0` | 20 dk | DerivedChannelDefinition modelini ekle | Giriş kimlikleri ve işlem zinciri yeniden üretilebilir tanım oluşturur | `F4-067` | `feat(domain): F4-068 derivedChannelDefinition modelini ekle` |
| [x] | `F4-069` | `1.69.0` | 20 dk | Türetilmiş kanalları repository'ye ekle | Derived ağacında yeni kanal sorgulanır; ham kaynak korunur | `F4-068` | `feat(repository): F4-069 türetilmiş kanalları repository'ye ekle` |
| [x] | `F4-070` | `1.70.0` | 20 dk | Sınırlı aritmetik formül ayrıştırıcısını ekle | Yalnız izinli kanal, sabit ve aritmetik düğümleri kabul edilir | `F4-069` | `feat(analysis): F4-070 sınırlı aritmetik formül ayrıştırıcısını ekle` |
| [x] | `F4-071` | `1.71.0` | 20 dk | Formül değerlendirmesini kanal dizilerine bağla | Basit kanal toplamı referansla eşleşir; zaman hizası uyuşmazlığı açıklanır | `F4-070` | `feat(analysis): F4-071 formül değerlendirmesini kanal dizilerine bağla` |
| [x] | `F4-072` | `1.72.0` | 20 dk | Formül ifade ve kaynak sınırlarını doğrula | Dosya erişimi, keyfi çağrı ve aşırı ifade reddedilir; eval kullanılmaz | `F4-071` | `test(analysis): F4-072 formül ifade ve kaynak sınırlarını doğrula` |
| [x] | `F4-073` | `1.73.0` | 20 dk | Custom sekmesine basit formül editörü ekle | Geçerli ifade Derived kanalı üretir; hata ilgili alanda görünür | `F4-072` | `feat(ui): F4-073 custom sekmesine basit formül editörü ekle` |
| [x] | `F4-074` | `1.74.0` | 15 dk | Annotation ve bookmark modelini ekle | Zaman veya aralık, etiket ve metin kayıpsız taşınır | `F4-073` | `feat(domain): F4-074 annotation ve bookmark modelini ekle` |
| [x] | `F4-075` | `1.75.0` | 20 dk | Bookmark ekleme, düzenleme ve silmeyi bağla | İşaret timeline'da görünür; seçim ilgili zamana gider | `F4-074` | `feat(ui): F4-075 bookmark ekleme, düzenleme ve silmeyi bağla` |
| [x] | `F4-076` | `1.76.0` | 20 dk | Analiz oturumuna zincir ve annotation kaydını ekle | Kaynaklar, işlemler, renkler ve bookmark'lar tek projede saklanır | `F4-075` | `feat(workspace): F4-076 analiz oturumuna zincir ve annotation kaydını ekle` |
| [x] | `F4-077` | `1.77.0` | 20 dk | Analiz oturumunu ve türetilmiş kanalları yükle | Yeniden açılan oturum aynı işlem sonuçlarını üretir | `F4-076` | `feat(workspace): F4-077 analiz oturumunu ve türetilmiş kanalları yükle` |
| [x] | `F4-078` | `1.78.0` | 20 dk | Taşınmış kaynaklar için yeniden konumlandırma ekle | Yeni konum seçimi kaynak kimliğini doğrular; yanlış dosya sessizce bağlanmaz | `F4-077` | `fix(workspace): F4-078 taşınmış kaynaklar için yeniden konumlandırma ekle` |
| [x] | `F4-079` | `1.79.0` | 20 dk | İşlem zinciri ve annotation undo/redo ekle | Sıra değişikliği ve işaret düzenlemesi geri alınabilir | `F4-078` | `feat(app): F4-079 işlem zinciri ve annotation undo/redo ekle` |
| [x] | `F4-080` | `1.80.0` | 20 dk | BIT durum süresi ve değişim trendini hesapla | Bilinen PASS/FAIL aralıkları doğru süre ve değişim sayısı verir | `F4-079` | `feat(analysis): F4-080 bIT durum süresi ve değişim trendini hesapla` |
| [x] | `F4-081` | `1.81.0` | 20 dk | BIT/Status trend görünümünü ekle | Sağ özet ile ayrıntılı trend aynı durumu gösterir | `F4-080` | `feat(ui): F4-081 bIT/Status trend görünümünü ekle` |
| [x] | `F4-082` | `1.82.0` | 20 dk | Grafik penceresini ayırma ve geri takmayı ekle | Ayrılan panel veri ve X senkronizasyonunu korur | `F4-081` | `feat(ui): F4-082 grafik penceresini ayırma ve geri takmayı ekle` |
| [x] | `F4-083` | `1.83.0` | 20 dk | Çoklu monitör konumlarını kaydet ve sınırla | Monitör çıkartılınca pencere görünür alana geri gelir | `F4-082` | `fix(ui): F4-083 çoklu monitör konumlarını kaydet ve sınırla` |

##### Ek çıktı ve sürüm kabulü

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F4-084` | `1.84.0` | 20 dk | Event/BIT metadata'sını JSON dışa aktar | Seçili aralık ve domain alanları kayıpsız çıkar | `F4-083` | `feat(export): F4-084 event/BIT metadata'sını JSON dışa aktar` |
| [x] | `F4-085` | `1.85.0` | 15 dk | TSV ayırıcı seçimini CSV akışına ekle | Zaman ve ondalık biçimi seçilen ayırıcıyla tutarlıdır | `F4-084` | `feat(export): F4-085 tSV ayırıcı seçimini CSV akışına ekle` |
| [x] | `F4-086` | `1.86.0` | 20 dk | Statik grafiği PDF olarak dışa aktar | Vektörel grafik başlık, kaynak ve işlem bilgisiyle açılır | `F4-085` | `feat(export): F4-086 statik grafiği PDF olarak dışa aktar` |
| [x] | `F4-087` | `1.87.0` | 20 dk | Sinüs, chirp, noise ve impulse referanslarını çalıştır | FFT, PSD, STFT ve filtre sonuçları NumPy/SciPy referanslarıyla eşleşir | `F4-086` | `test(analysis): F4-087 sinüs, chirp, noise ve impulse referanslarını çalıştır` |
| [x] | `F4-088` | `1.88.0` | 20 dk | Kaydet/aç sonrası analiz tekrarını doğrula | Aynı kaynak ve parametreler aynı sayısal çıktıları üretir | `F4-087` | `test(workspace): F4-088 kaydet/aç sonrası analiz tekrarını doğrula` |
| [x] | `F4-089` | `1.89.0` | 20 dk | Çalışan analiz panosunu mockup ile karşılaştır | Dokuz bölge korunur; FFT, spektrogram, filtre ve istatistik gerçek veriyle çalışır | `F4-088` | `test(ui): F4-089 çalışan analiz panosunu mockup ile karşılaştır` |

##### Profil B sınırlı okuma (ADR-010 düzeltmesi)

`F4-065` kararı `query_ms`, `pipeline_fps` ve `memory_scaling` hedeflerinin
saptığını ölçtü; ADR-010 nedeni algoritmik olarak saptayıp düzeltmeyi "ayrı bir
iş" olarak bıraktı. §22.1 gereği sapan zorunlu kontrolle milestone kapatılamaz,
bu yüzden bu üç iş `F4-090`'dan önce gelir.

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F4-091` | `1.90.0` | 20 dk | Profil B kayıt indeksini kur | İndeks yalnız kayıt başlıklarını tarar; payload'a dokunmaz ve `iter_records` ile birebir aynı kayıt/blok konumlarını verir | `F4-089` | `feat(io): F4-091 profil B kayıt indeksini kur` |
| [x] | `F4-092` | `1.91.0` | 20 dk | Profil B zaman sorgusunu indeksle sınırla | Sorgu yalnız pencereye düşen kayıtları okur; sonuç eski tam-çözüm referansıyla bit düzeyinde aynıdır ve dokunulan kayıt sayısı dosya boyutundan bağımsızdır | `F4-091` | `perf(io): F4-092 profil B zaman sorgusunu indeksle sınırla` |
| [x] | `F4-093` | `1.92.0` | 20 dk | Büyük dosya koşusunu tekrarla ve kararı güncelle | `F4-064` koşusu aynı dosyalarla tekrarlanır; `F4-065` kararı ölçümden yeniden üretilir ve sapan hedeflerin durumu belgelenir | `F4-092` | `perf(bench): F4-093 büyük dosya koşusunu tekrarla ve kararı güncelle` |
| [x] | `F4-094` | `1.93.0` | 20 dk | Özet piramidini NumPy blok işlemleriyle hızlandır | Tüm seviyelerin min/max/geçersiz seçimleri korunur; 1 saniyelik çizim sorgusu hazırlığı 30 FPS bütçesine iner | `F4-093` | `perf(index): F4-094 özet piramidini NumPy blok işlemleriyle hızlandır` |
| [x] | `F4-095` | `1.94.0` | 20 dk | Büyük çizim aralıklarını sınırlı bellekle indirgeme | Tam kayıt çizimi ham dizinin tamamını oluşturmaz; dar darbeler, kalite ve piksel bütçesi korunur | `F4-094` | `perf(query): F4-095 büyük çizim aralıklarını sınırlı bellekle indirgeme` |
| [x] | `F4-096` | `1.95.0` | 20 dk | Özet ve akış düzeltmeleri sonrası performansı doğrula | Aynı dosya/parametrelerle karar yeniden üretilir; kalan sapmalar açıkça kaydedilir | `F4-095` | `perf(bench): F4-096 özet ve akış düzeltmeleri sonrası performansı doğrula` |

##### Sürüm kabulü

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F4-090` | `2.0.0` | 15 dk | Analiz milestone kabulünü kapat ve major sürümü hazırla | Mockup analizi, Bölüm 3.2, doğruluk ve performans koşulları geçer | `F4-096` | `chore(release): F4-090 analiz milestone kabulünü kapat ve major sürümü hazırla` |

#### Faz 5 — Canlı veri, bağlantı ve kayıt

Kabul: UDP/TCP/serial akışı, bağlantı durumu, canlı grafik, kayıt ve tekrar okuma doğrulanmalı; dayanıklılık koşusu geçmeli. Etiket: `ms/06-live-recording`, sürüm: `v3.0.0`.

##### Protokol ve bağlantı

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F5-001` | `2.1.0` | 20 dk | Canlı paket ve bağlantı sözleşmesini tamamla | Paket sınırı, endian, zaman kaynağı ve kayıp politikası her protokol için tanımlıdır | `F4-090` | `docs(live): F5-001 canlı paket ve bağlantı sözleşmesini tamamla` |
| [x] | `F5-002` | `2.2.0` | 20 dk | Bağlantı durum makinesini ekle | Disconnected, connecting, connected, degraded ve error geçişleri doğrulanır | `F5-001` | `feat(live): F5-002 bağlantı durum makinesini ekle` |
| [x] | `F5-003` | `2.3.0` | 20 dk | Dosyadan LiveSource replay adaptörünü ekle | 125 ms kayıtlar seçilen hızla aynı domain akışını üretir | `F5-002` | `feat(live): F5-003 dosyadan LiveSource replay adaptörünü ekle` |
| [x] | `F5-004` | `2.4.0` | 20 dk | Replay zamanlama ve durdurmayı doğrula | Pause/stop sonrası beklenmeyen paket yayınlanmaz | `F5-003` | `test(live): F5-004 replay zamanlama ve durdurmayı doğrula` |
| [x] | `F5-005` | `2.5.0` | 20 dk | UDP alıcı bağlantısını ekle | Yerel simülatör paketleri alınır; disconnect soketi serbest bırakır | `F5-004` | `feat(live): F5-005 uDP alıcı bağlantısını ekle` |
| [x] | `F5-006` | `2.6.0` | 20 dk | UDP paketlerini decoder'a bağla | Geçerli datagram domain verisi olur; kesik datagram teşhis edilir | `F5-005` | `feat(live): F5-006 uDP paketlerini decoder'a bağla` |
| [x] | `F5-007` | `2.7.0` | 20 dk | TCP bağlantı ve okuma akışını ekle | Yerel sunucuya bağlanır; EOF ve bağlantı hatası doğru duruma geçer | `F5-006` | `feat(live): F5-007 tCP bağlantı ve okuma akışını ekle` |
| [x] | `F5-008` | `2.8.0` | 20 dk | TCP parçalı ve birleşik paket ayrımını ekle | Bölünmüş veya aynı okumada gelen paketler tam bir kez çözülür | `F5-007` | `feat(live): F5-008 tCP parçalı ve birleşik paket ayrımını ekle` |
| [x] | `F5-009` | `2.9.0` | 20 dk | Serial port ayar ve bağlantısını ekle | Port ve hız doğrulanır; kapatma kaynağı serbest bırakır | `F5-008` | `feat(live): F5-009 serial port ayar ve bağlantısını ekle` |
| [x] | `F5-010` | `2.10.0` | 20 dk | Serial paket sınırı ve timeout işleyişini ekle | Sanal portta eksik paket beklenir veya sözleşmeye göre raporlanır | `F5-009` | `feat(live): F5-010 serial paket sınırı ve timeout işleyişini ekle` |
| [x] | `F5-011` | `2.11.0` | 20 dk | Üç adaptör için ortak sözleşme kontrolü ekle | Connect, packets ve disconnect davranışı yerel/sanal kaynakla eşleşir | `F5-010` | `test(live): F5-011 üç adaptör için ortak sözleşme kontrolü ekle` |

##### Sıra, buffer ve akış denetimi

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F5-012` | `2.12.0` | 20 dk | Sıra numarasından paket kaybını hesapla | Atlanan, tekrarlı ve sıra dışı paketler ayrı sayaç üretir | `F5-011` | `feat(live): F5-012 sıra numarasından paket kaybını hesapla` |
| [x] | `F5-013` | `2.13.0` | 20 dk | Canlı cihaz zamanını kanonik zamana bağla | Dosya ve canlı replay aynı zaman tabanında eşleşir | `F5-012` | `feat(time): F5-013 canlı cihaz zamanını kanonik zamana bağla` |
| [x] | `F5-014` | `2.14.0` | 20 dk | Sabit kapasiteli ring buffer ekle | Kapasite aşılınca tanımlı eski veri çıkar; bellek sınırlı kalır | `F5-013` | `feat(live): F5-014 sabit kapasiteli ring buffer ekle` |
| [x] | `F5-015` | `2.15.0` | 20 dk | Zaman penceresine göre buffer sorgula | Sarılmış buffer'da zaman sırası ve seçili aralık doğrudur | `F5-014` | `feat(live): F5-015 zaman penceresine göre buffer sorgula` |
| [x] | `F5-016` | `2.16.0` | 20 dk | Kuyruk sınırı ve drop politikasını uygula | Burst sırasında sınır aşılmaz; düşen veri sayısı raporlanır | `F5-015` | `feat(live): F5-016 kuyruk sınırı ve drop politikasını uygula` |
| [x] | `F5-017` | `2.17.0` | 20 dk | Sınırlı otomatik yeniden bağlanma ekle | Denemeler görünürdür; kullanıcı durdurunca yeniden bağlantı başlamaz | `F5-016` | `feat(live): F5-017 sınırlı otomatik yeniden bağlanma ekle` |
| [x] | `F5-018` | `2.18.0` | 20 dk | Bağlantı ve buffer ayarlarını kaydet | Geçersiz adres, port veya kapasite bağlantıdan önce açıklanır | `F5-017` | `feat(settings): F5-018 bağlantı ve buffer ayarlarını kaydet` |
| [x] | `F5-019` | `2.19.0` | 20 dk | Connect ve Disconnect eylemlerini bağla | Toolbar ve durum çubuğu aynı bağlantı durumunu gösterir | `F5-018` | `feat(ui): F5-019 connect ve Disconnect eylemlerini bağla` |
| [x] | `F5-020` | `2.20.0` | 20 dk | Paket kaybı, kuyruk ve buffer durumunu göster | Sentetik kayıp ve burst ekranda doğru sayaçlarla görünür | `F5-019` | `feat(ui): F5-020 paket kaybı, kuyruk ve buffer durumunu göster` |
| [x] | `F5-021` | `2.21.0` | 20 dk | Canlı akışı ortak repository'ye bağla | Aynı kanal ve olay sorguları dosya ve canlı kaynakta çalışır | `F5-020` | `feat(repository): F5-021 canlı akışı ortak repository'ye bağla` |
| [x] | `F5-022` | `2.22.0` | 20 dk | Canlı veriyi mevcut grafik panellerine bağla | Grafikler ring buffer'dan güncellenir; UI thread bloklanmaz | `F5-021` | `feat(plot): F5-022 canlı veriyi mevcut grafik panellerine bağla` |
| [x] | `F5-023` | `2.23.0` | 15 dk | Canlı sona takip etme ve sabit aralık seçimini ekle | Kullanıcı geçmişe bakarken viewport zorla sona taşınmaz | `F5-022` | `feat(ui): F5-023 canlı sona takip etme ve sabit aralık seçimini ekle` |
| [x] | `F5-024` | `2.24.0` | 20 dk | Canlı ve playback mod geçişlerini denetle | İki saat aynı grafiği eşzamanlı ilerletmez | `F5-023` | `fix(app): F5-024 canlı ve playback mod geçişlerini denetle` |

##### 125 ms kayıt yazımı

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F5-025` | `2.25.0` | 20 dk | Sürümlü dosya header yazıcısını ekle | Dosya format sürümü uygulama sürümünden bağımsız yazılır | `F5-024` | `feat(recording): F5-025 sürümlü dosya header yazıcısını ekle` |
| [x] | `F5-026` | `2.26.0` | 20 dk | Data kayıt serileştirmesini ekle | Ad, sıra, elapsed_us, payload ve varsa CRC decoder ile eşleşir | `F5-025` | `feat(recording): F5-026 data kayıt serileştirmesini ekle` |
| [x] | `F5-027` | `2.27.0` | 20 dk | 125 ms kayıt biriktirme sınırlarını ekle | Data00000 ve Data00001 125 ms aralıklarla oluşur; ham blok örnekleri korunur | `F5-026` | `feat(recording): F5-027 125 ms kayıt biriktirme sınırlarını ekle` |
| [x] | `F5-028` | `2.28.0` | 20 dk | Disk yazma kuyruğunu canlı akıştan ayır | Yavaş disk UI'ı kilitlemez; taşma ve kayıp görünürdür | `F5-027` | `feat(recording): F5-028 disk yazma kuyruğunu canlı akıştan ayır` |
| [x] | `F5-029` | `2.29.0` | 20 dk | Flush ve güvenli dosya kapatmayı ekle | Stop sonrası bütün tam kayıtlar yeniden okunabilir | `F5-028` | `feat(recording): F5-029 flush ve güvenli dosya kapatmayı ekle` |
| [x] | `F5-030` | `2.30.0` | 20 dk | Disk dolması ve yazma hatasını işle | Kayıt hata durumuna geçer; başarılı kayıt mesajı verilmez | `F5-029` | `fix(recording): F5-030 disk dolması ve yazma hatasını işle` |
| [x] | `F5-031` | `2.31.0` | 20 dk | Boyut ve isim sınırında yeni dosyaya geç | Yeni dosyanın başlangıç zamanı ve sıra başlangıcı kendi içinde tutarlıdır | `F5-030` | `feat(recording): F5-031 boyut ve isim sınırında yeni dosyaya geç` |
| [x] | `F5-032` | `2.32.0` | 20 dk | Record ve Stop durumunu ana ekrana bağla | Aktif dosya, geçen süre ve kayıt durumu görünür | `F5-031` | `feat(ui): F5-032 record ve Stop durumunu ana ekrana bağla` |
| [x] | `F5-033` | `2.33.0` | 20 dk | Bağlantı kesilmesinde kayıt davranışını uygula | Tam kayıtlar korunur; boşluk ve kapanış nedeni loglanır | `F5-032` | `fix(recording): F5-033 bağlantı kesilmesinde kayıt davranışını uygula` |
| [x] | `F5-034` | `2.34.0` | 20 dk | Canlı BIT ve TX olaylarını panoya bağla | Sağ BIT özeti ve grafik marker'ları aynı geçişi gösterir | `F5-033` | `feat(ui): F5-034 canlı BIT ve TX olaylarını panoya bağla` |
| [x] | `F5-035` | `2.35.0` | 20 dk | Canlı kayıt dosyasını tekrar açarak karşılaştır | Örnekler, olaylar ve 125 ms sınırları kaynaktaki referansla eşleşir | `F5-034` | `test(recording): F5-035 canlı kayıt dosyasını tekrar açarak karşılaştır` |

##### Dayanıklılık ve kabul

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F5-036` | `2.36.0` | 20 dk | Burst, kayıp ve sıra dışı paket simülatörü ekle | Her senaryo seed ile tekrar üretilebilir | `F5-035` | `test(live): F5-036 burst, kayıp ve sıra dışı paket simülatörü ekle` |
| [x] | `F5-037` | `2.37.0` | 20 dk | Burst ve bağlantı kesintisi sonuçlarını doğrula | Sayaçlar, kuyruk sınırı, yeniden bağlanma ve UI tepkisi bekleneni verir | `F5-036` | `test(live): F5-037 burst ve bağlantı kesintisi sonuçlarını doğrula` |
| [x] | `F5-038` | `2.38.0` | 20 dk | Uzun süreli canlı kayıt koşusunu hazırla | En az 2 saatlik otomatik koşu bellek, kayıp ve dosya boyutunu kaydeder | `F5-037` | `test(live): F5-038 uzun süreli canlı kayıt koşusunu hazırla` |
| [x] | `F5-039` | `2.39.0` | 20 dk | Dayanıklılık koşusu raporunu değerlendir | Bellek bütçesi, beklenen kayıp ve kayıt bütünlüğü sonuçları kanıtlıdır | `F5-038` | `docs(live): F5-039 dayanıklılık koşusu raporunu değerlendir` |
| [x] | `F5-040` | `2.40.0` | 20 dk | Canlı modda mockup pano davranışını kontrol et | Ana yerleşim korunur; bağlantı ve kayıt durumu açıkça görünür | `F5-039` | `test(ui): F5-040 canlı modda mockup pano davranışını kontrol et` |
| [x] | `F5-041` | `3.0.0` | 15 dk | Canlı veri milestone kabulünü kapat ve major sürümü hazırla | Üç adaptör, yeniden okuma ve dayanıklılık kontrolleri geçer | `F5-040` | `chore(release): F5-041 canlı veri milestone kabulünü kapat ve major sürümü hazırla` |

#### Faz 6 — Windows dağıtımı ve ürünleştirme

Kabul: Kurulabilir Windows paketi, dokümantasyon, sürüm artefaktları ve dağıtım kabul kanıtları tamamlanmış olmalı. Etiket: `ms/07-distribution`, sürüm: `v4.0.0`.

##### Paket ve temiz ortam

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F6-001` | `3.1.0` | 20 dk | Paketleme aracı ve dağıtım biçimi ADR'sini tamamla | PyInstaller/Nuitka seçimi spike kanıtına ve hedef Windows ortamına dayanır | `F5-041` | `docs(build): F6-001 paketleme aracı ve dağıtım biçimi ADR'sini tamamla` |
| [x] | `F6-002` | `3.2.0` | 20 dk | Windows paketleme yapılandırmasını ekle | Giriş noktası, VERSION ve gerekli kaynaklar yapılandırmada tanımlıdır | `F6-001` | `build(package): F6-002 windows paketleme yapılandırmasını ekle` |
| [x] | `F6-003` | `3.3.0` | 20 dk | Qt plugin, tema ve ikon kaynaklarını pakete ekle | Paketli açılışta tema, ikon ve platform plugin'i yüklenir | `F6-002` | `build(package): F6-003 qt plugin, tema ve ikon kaynaklarını pakete ekle` |
| [x] | `F6-004` | `3.4.0` | 20 dk | Tek komutluk paket üretim akışını ekle | Komut sürümlü çıktı klasörü ve build logu üretir | `F6-003` | `build(package): F6-004 tek komutluk paket üretim akışını ekle` |
| [x] | `F6-005` | `3.5.0` | 20 dk | Temiz Windows ortamında paket açılışını kontrol et | Sistem Python kurulumu olmadan ana ekran açılır | `F6-004` | `test(package): F6-005 temiz Windows ortamında paket açılışını kontrol et` |
| [x] | `F6-006` | `3.6.0` | 20 dk | Paketli uygulamada BIN ve export akışını kontrol et | Örnek kayıt açılır; CSV/PNG çıktısı yeniden okunabilir | `F6-005` | `test(package): F6-006 paketli uygulamada BIN ve export akışını kontrol et` |
| [x] | `F6-007` | `3.7.0` | 20 dk | Installer oluşturma adımını ekle | Uygulama, kısayol ve kaldırma girdisi beklenen konumdadır | `F6-006` | `build(installer): F6-007 ınstaller oluşturma adımını ekle` |
| [x] | `F6-008` | `3.8.0` | 20 dk | Kurulum, yükseltme ve kaldırmayı kontrol et | Sürüm geçişi kullanıcı workspace ve kaynak kayıtlarını silmez | `F6-007` | `test(installer): F6-008 kurulum, yükseltme ve kaldırmayı kontrol et` |
| [x] | `F6-009` | `3.9.0` | 15 dk | Artefakt checksum ve sürüm manifestini üret | Paket sürümü, dosya adı ve hash birbiriyle eşleşir | `F6-008` | `build(release): F6-009 artefakt checksum ve sürüm manifestini üret` |
| [x] | `F6-010` | `3.10.0` | 20 dk | Aynı girdilerle paket üretimini karşılaştır | Araç sürümleri ve hash farkları kaydedilir; deterministik olmayan alanlar açıklanır | `F6-009` | `test(build): F6-010 aynı girdilerle paket üretimini karşılaştır` |
| [x] | `F6-011` | `3.11.0` | 20 dk | Offline bağımlılık paketleme akışını hazırla | Offline hedef varsa bağlantısız kurulum doğrulanır; yoksa koşul ADR'de gerekçelenir | `F6-010` | `build(package): F6-011 offline bağımlılık paketleme akışını hazırla` |
| [x] | `F6-012` | `3.12.0` | 20 dk | İmzalama gereksinimini yayın akışına bağla | Gerekliyse sertifika ile doğrulanır; değilse imzasız dağıtım kararı kaydedilir | `F6-011` | `build(release): F6-012 imzalama gereksinimini yayın akışına bağla` |

##### Kalite kapıları ve tanılama

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F6-013` | `3.13.0` | 20 dk | Coverage raporu ve eşiklerini CI'a ekle | Genel en az yüzde 70 ve kritik parser/domain için yüksek eşik denetlenir | `F6-012` | `test(quality): F6-013 coverage raporu ve eşiklerini CI'a ekle` |
| [x] | `F6-014` | `3.14.0` | 20 dk | Bağımlılık taramasını CI'a ekle | Tarama raporu üretilir; belirlenen engelleyici sonuçta iş başarısız olur | `F6-013` | `build(ci): F6-014 bağımlılık taramasını CI'a ekle` |
| [x] | `F6-015` | `3.15.0` | 20 dk | Küçük performans smoke kontrolünü CI'a ekle | Sabit fixture ile bütçe sapması raporlanır | `F6-014` | `build(ci): F6-015 küçük performans smoke kontrolünü CI'a ekle` |
| [x] | `F6-016` | `3.16.0` | 20 dk | Windows paket smoke kontrolünü CI'a ekle | Build ve paketli açılış sonucu workflow artefaktına yazılır | `F6-015` | `build(ci): F6-016 windows paket smoke kontrolünü CI'a ekle` |
| [x] | `F6-017` | `3.17.0` | 20 dk | Sürüm artefaktı ve checksum iş akışını ekle | Sürüm etiketiyle VERSION uyuşmazsa yayın adımı durur | `F6-016` | `build(ci): F6-017 sürüm artefaktı ve checksum iş akışını ekle` |
| [x] | `F6-018` | `3.18.0` | 15 dk | Merge ve release kalite kapılarını belgeye bağla | Remote varsa gerekli kontroller uygulanır; yoksa yerel eşdeğer komutlar kayıtlıdır | `F6-017` | `docs(ci): F6-018 merge ve release kalite kapılarını belgeye bağla` |
| [x] | `F6-019` | `3.19.0` | 20 dk | Tanılama paketi içerik listesini üret | Session, sürüm ve hata logları listelenir; ham sensör veri varsayılan değildir | `F6-018` | `feat(diagnostics): F6-019 tanılama paketi içerik listesini üret` |
| [x] | `F6-020` | `3.20.0` | 20 dk | Tanılama önizleme ve dışa aktarımını ekle | Kullanıcı içeriği görür; yalnız seçili öğeler pakete girer | `F6-019` | `feat(diagnostics): F6-020 tanılama önizleme ve dışa aktarımını ekle` |
| [x] | `F6-021` | `3.21.0` | 20 dk | Son geçerli workspace kurtarmasını ekle | Kesinti sonrası sağlam oturum önerilir; bozuk dosya etkin oturumu ezmez | `F6-020` | `feat(workspace): F6-021 son geçerli workspace kurtarmasını ekle` |
| [x] | `F6-022` | `3.22.0` | 20 dk | Tekrarlı aç/kapat ve playback koşusunu hazırla | Otomatik döngü bellek, handle ve kapanış hatalarını kaydeder | `F6-021` | `test(app): F6-022 tekrarlı aç/kapat ve playback koşusunu hazırla` |
| [x] | `F6-023` | `3.23.0` | 20 dk | Aç/kapat dayanıklılık sonuçlarını değerlendir | Kalıcı kaynak artışı yoktur veya engelleyici hata işi açılmıştır | `F6-022` | `docs(quality): F6-023 aç/kapat dayanıklılık sonuçlarını değerlendir` |

##### Kılavuzlar ve son kabul

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F6-024` | `3.24.0` | 20 dk | Mockup üzerinden ana ekran kullanım kılavuzunu yaz | Dokuz bölge ve dosyadan analize ana akış ekranla eşleşir | `F6-023` | `docs(user): F6-024 mockup üzerinden ana ekran kullanım kılavuzunu yaz` |
| [x] | `F6-025` | `3.25.0` | 20 dk | Filtre ve spektral analiz kullanım örneğini yaz | Birim, sample rate, ROI ve işlem geçmişi örnekte açıktır | `F6-024` | `docs(user): F6-025 filtre ve spektral analiz kullanım örneğini yaz` |
| [x] | `F6-026` | `3.26.0` | 20 dk | Canlı bağlantı ve kayıt kullanım örneğini yaz | Üç protokol, bağlantı kesintisi ve kayıt tekrar açma açıklanır | `F6-025` | `docs(user): F6-026 canlı bağlantı ve kayıt kullanım örneğini yaz` |
| [x] | `F6-027` | `3.27.0` | 20 dk | Format ve decoder kılavuzunu güncelle | 32/64 örnek, CRC'li ve akustik format sürümleri karıştırılmaz | `F6-026` | `docs(format): F6-027 format ve decoder kılavuzunu güncelle` |
| [x] | `F6-028` | `3.28.0` | 15 dk | Klavye, mouse ve ölçekleme kılavuzunu tamamla | Bölüm 16 kısayolları paketli uygulamadaki davranışla eşleşir | `F6-027` | `docs(user): F6-028 klavye, mouse ve ölçekleme kılavuzunu tamamla` |
| [x] | `F6-029` | `3.29.0` | 15 dk | Bilinen sorunları ve veri sınırlamalarını yaz | Her açık sorun etki, iş kimliği ve hedef düzeltme içerir | `F6-028` | `docs(release): F6-029 bilinen sorunları ve veri sınırlamalarını yaz` |
| [x] | `F6-030` | `3.30.0` | 20 dk | Paketli uygulamada kullanıcı kabul turunu kaydet | Operatör ve mühendis akışları kanıtla işaretlenir; başarısızlıklar ayrı işe dönüşür | `F6-029` | `test(acceptance): F6-030 paketli uygulamada kullanıcı kabul turunu kaydet` |
| [x] | `F6-031` | `3.31.0` | 20 dk | Paketli ana ekranı referans mockup ile karşılaştır | Dokuz bölge, hiyerarşi, tema ve çalışan ana analizler kabul listesini karşılar | `F6-030` | `test(ui): F6-031 paketli ana ekranı referans mockup ile karşılaştır` |
| [x] | `F6-032` | `3.32.0` | 20 dk | Release ve geri dönüş prosedürünü yaz | Önceki paket ve kullanıcı ayarlarının geri yükleme adımları uygulanabilirdir | `F6-031` | `docs(release): F6-032 release ve geri dönüş prosedürünü yaz` |
| [x] | `F6-033` | `3.33.0` | 15 dk | Major sürüm notları ve milestone özetini hazırla | Kapsam, kontroller, bilinen sorunlar ve artefaktlar tutarlıdır | `F6-032` | `docs(release): F6-033 major sürüm notları ve milestone özetini hazırla` |
| [x] | `F6-034` | `4.0.0` | 15 dk | Dağıtım milestone kabulünü kapat ve major sürümü hazırla | Kurulum, mockup kabulü, kalite kapıları ve yayın belgeleri tamdır | `F6-033` | `chore(release): F6-034 dağıtım milestone kabulünü kapat ve major sürümü hazırla` |
| [x] | `F6-035` | `3.35.0` | 20 dk | Kalite bayraklarını dışa aktarmaya ve paket denetimine taşı | CRC/gap işaretli örnekler CSV'de ve `--bin-check` özetinde görünür | `F6-030` | `fix(export): F6-035 kalite bayraklarını dışa aktarmaya ve paket denetimine taşı` |

> `F6-035`, `F6-030` kabul turunun **başarısız** adımından (`M-05`) doğdu:
> bozuk CRC'li bir kayıttan alınan CSV, bozuk örneği hiçbir işaret
> olmadan yazıyor. Ayrıntı: `docs/acceptance/packaged-acceptance.md`.

#### Faz 7 — Klasör tabanlı Tx/Rx kayıt mimarisi ve TOML şema

Kabul: Bir kayıt klasörü (tarih klasörü, `Tx/` ve `Rx/` alt klasörleri, 1'er saniyelik
`TxData00000.bin` dosyaları) TOML şemasıyla açılır, kesintisiz oynatılır ve `.mat` olarak
dışa aktarılır. Etiket: `ms/08-folder-recording`, sürüm: `v5.0.0`.

Kayıt dosyalarını **C++ tarafı üretir**. Bu faz yazma tarafını değil **okuma tarafını**
kurar; sentetik üreteç yalnız test verisi içindir. TOML, C++ struct ve enum tanımlarının
tarifidir, bizim tanımladığımız bir yapı değildir — bu yüzden en kritik kabul, şema ile
kaydın uyuşmadığı durumda **sessizce yanlış okumamaktır**.

##### Sözleşme ve açık kararlar

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [x] | `F7-001` | `4.6.0` | 20 dk | Profil C klasör ve dosya sözleşmesi taslağını yaz | Tarih klasörü, `Tx/` ve `Rx/` alt klasörleri, `TxData00000.bin` adlandırması ve sayaç sarması belgede tanımlıdır | `F6-034` | `docs(format): F7-001 profil C klasör ve dosya sözleşmesi taslağını yaz` |
| [x] | `F7-002` | `4.7.0` | 20 dk | Kullanıcı kararlarını ve kalan açık kararları kayda geç | 10 dk tavan, kayma kabulü, `complex64` ve C++ sahipliği `open-decisions.md`'de `D-26`…`D-31` olarak izlenir | `F7-001` | `docs(notes): F7-002 kullanıcı kararlarını ve kalan açık kararları kayda geç` |
| [ ] | `F7-003` | `4.8.0` | 20 dk | Bayt bütçesi ve zaman kayması tablosunu belgeye yaz | 820/8192 = 100,0977 ms, 10 dk'da 0,586 s kayma ve 1,173 GiB toplam belgede hesabıyla gösterilir | `F7-002` | `docs(format): F7-003 bayt bütçesi ve zaman kayması tablosunu belgeye yaz` |
| [ ] | `F7-004` | `4.9.0` | 20 dk | C++ struct → TOML eşleme sözleşmesini yaz | Paketleme (`#pragma pack`), hizalama, endianness ve bit alanı kuralları örnekle tanımlıdır | `F7-003` | `docs(format): F7-004 c++ struct → TOML eşleme sözleşmesini yaz` |
| [ ] | `F7-005` | `4.10.0` | 20 dk | Zaman ekseninin tek kaynağını sözleşmeye bağla | Zamanın frame sayacından mı timestamp'ten mi türediği tek yerde tanımlı; ikisinin 10 dk'da 0,586 s ayrıştığı yazılı | `F7-004` | `docs(format): F7-005 zaman ekseninin tek kaynağını sözleşmeye bağla` |

##### TOML şema altyapısı

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F7-006` | `4.11.0` | 20 dk | Örnek TOML şema dosyasını yaz (enum + struct + FrameHeader) | `tomllib` ile ayrıştırılır; `FrameHeader` bütün alanları offset ve cpp tipiyle doludur | `F7-005` | `feat(schema): F7-006 örnek TOML şema dosyasını yaz (enum + struct + FrameHeader)` |
| [ ] | `F7-007` | `4.12.0` | 20 dk | cpp tipi → Python struct kodu → NumPy dtype eşleme tablosunu kur | 13 temel cpp tipi için üç gösterim de tanımlı; bilinmeyen tip `SchemaTypeError` verir | `F7-006` | `feat(schema): F7-007 cpp tipi → Python struct kodu → NumPy dtype eşleme tablosunu kur` |
| [ ] | `F7-008` | `4.13.0` | 20 dk | Şema yükleyicisini ve sürüm alanını ekle | Şema kimliği ve sürümü olmayan dosya `SchemaError` ile reddedilir | `F7-007` | `feat(schema): F7-008 şema yükleyicisini ve sürüm alanını ekle` |
| [ ] | `F7-009` | `4.14.0` | 20 dk | Enum çözümleyicisini ekle | Değer → isim eşlemesi üretilir; yinelenen değer açık hata verir | `F7-008` | `feat(schema): F7-009 enum çözümleyicisini ekle` |
| [ ] | `F7-010` | `4.15.0` | 20 dk | Struct alan çözümleyicisini ekle | Ad, tip, offset, dizi uzunluğu ve enum referansı okunur; eksik alan reddedilir | `F7-009` | `feat(schema): F7-010 struct alan çözümleyicisini ekle` |
| [ ] | `F7-011` | `4.16.0` | 20 dk | Offset çakışması ve boşluk denetimini ekle | Üst üste binen iki alan hata verir; bildirilmemiş boşluk uyarı olarak raporlanır | `F7-010` | `feat(schema): F7-011 offset çakışması ve boşluk denetimini ekle` |
| [ ] | `F7-012` | `4.17.0` | 15 dk | Bildirilen boyut ile hesaplanan boyut uyuşmazlığını reddet | `size = 256` diyen ama alanları 248 bayt tutan şema açık hata verir | `F7-011` | `feat(schema): F7-012 bildirilen boyut ile hesaplanan boyut uyuşmazlığını reddet` |
| [ ] | `F7-013` | `4.18.0` | 20 dk | Hizalama ihlali denetimini ekle | 4 baytlık alan 2'ye hizalı offsette ise, paketleme `packed` değilse hata verir | `F7-012` | `feat(schema): F7-013 hizalama ihlali denetimini ekle` |
| [ ] | `F7-014` | `4.19.0` | 20 dk | Şemadan çalışma zamanında `struct.Struct` üret | Üretilen format dizgisinin `calcsize` sonucu bildirilen boyuta eşittir | `F7-013` | `feat(schema): F7-014 şemadan çalışma zamanında `struct.Struct` üret` |
| [ ] | `F7-015` | `4.20.0` | 20 dk | Şemadan NumPy structured dtype üret | `dtype.itemsize` bildirilen boyuta eşit; alan offsetleri şemayla birebir | `F7-014` | `feat(schema): F7-015 şemadan NumPy structured dtype üret` |
| [ ] | `F7-016` | `4.21.0` | 15 dk | Şema parmak izini hesapla ve kayda yaz | Aynı şema aynı parmak izini verir; tek alan değişince parmak izi değişir | `F7-015` | `feat(schema): F7-016 şema parmak izini hesapla ve kayda yaz` |
| [ ] | `F7-017` | `4.22.0` | 20 dk | Şema ile kayıt uyuşmazlığını tespit eden kapıyı kur | Magic, şema kimliği ve akıl sağlığı kontrolü; yanlış şemayla açılan kayıt sessizce okunmaz, reddedilir | `F7-016` | `feat(schema): F7-017 şema ile kayıt uyuşmazlığını tespit eden kapıyı kur` |
| [ ] | `F7-018` | `4.23.0` | 20 dk | Şema doğrulama hatalarını kullanıcıya taşıyan mesajları yaz | Her hata sınıfı için hangi alan, hangi offset ve ne beklendiği mesajda görünür | `F7-017` | `feat(schema): F7-018 şema doğrulama hatalarını kullanıcıya taşıyan mesajları yaz` |

##### Profil C çözücüsü

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F7-019` | `4.24.0` | 20 dk | Profil C dosya header'ını çöz | Sihirli sayı, şema kimliği, sensör sayısı, örnekleme hızı ve frame sayısı okunur | `F7-018` | `feat(parser): F7-019 profil C dosya header'ını çöz` |
| [ ] | `F7-020` | `4.25.0` | 20 dk | Frame header'ını şemadan çöz | Frame indeksi, timestamp, CIT, transmisyon ve platform alanları şemanın dediği offsetlerden okunur | `F7-019` | `feat(parser): F7-020 frame header'ını şemadan çöz` |
| [ ] | `F7-021` | `4.26.0` | 20 dk | `complex64` payload'unu kopyasız oku | `np.frombuffer` ile (32, 820) complex64 dizi üretilir; kopya alınmadığı `base` ile doğrulanır | `F7-020` | `feat(parser): F7-021 `complex64` payload'unu kopyasız oku` |
| [ ] | `F7-022` | `4.27.0` | 20 dk | Sensör × örnek yerleşimini doğrula | Yerleşim şemadan gelir; beklenen bayt sayısı tutmazsa `ProfileCFormatError` verir | `F7-021` | `feat(parser): F7-022 sensör × örnek yerleşimini doğrula` |
| [ ] | `F7-023` | `4.28.0` | 20 dk | Frame CRC doğrulamasını ekle | Bozuk CRC'li frame işaretlenir, komşu frame'ler etkilenmez | `F7-022` | `feat(parser): F7-023 frame CRC doğrulamasını ekle` |
| [ ] | `F7-024` | `4.29.0` | 20 dk | Kesik dosyayı raporla, tam frame'leri kullan | Yarım frame atılır, kaç bayt atıldığı kullanıcıya bildirilir | `F7-023` | `feat(parser): F7-024 kesik dosyayı raporla, tam frame'leri kullan` |
| [ ] | `F7-025` | `4.30.0` | 15 dk | Frame indeksi ile dosya adı uyuşmazlığını raporla | `RxData00007.bin` içinde 70'ten farklı başlayan indeks uyarı üretir | `F7-024` | `feat(parser): F7-025 frame indeksi ile dosya adı uyuşmazlığını raporla` |
| [ ] | `F7-026` | `4.31.0` | 20 dk | Timestamp ile frame sayacı arasındaki kaymayı ölç | Kayma ppm olarak raporlanır; 820/8192 kaynaklı beklenen kayma ile karşılaştırılır | `F7-025` | `feat(parser): F7-026 timestamp ile frame sayacı arasındaki kaymayı ölç` |
| [ ] | `F7-027` | `4.32.0` | 20 dk | Sürüm dağıtımına Profil C'yi ekle | Profil A, B ve C dosyaları doğru çözücüye gider; bilinmeyen sürüm açık hata verir | `F7-026` | `feat(parser): F7-027 sürüm dağıtımına Profil C'yi ekle` |

##### Klasör keşfi ve indeks

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F7-028` | `4.33.0` | 20 dk | Kayıt klasörü düzenini keşfet | Tarih klasörü altında `Tx/` ve `Rx/` bulunur; eksikse hangisinin olmadığı söylenir | `F7-027` | `feat(io): F7-028 kayıt klasörü düzenini keşfet` |
| [ ] | `F7-029` | `4.34.0` | 20 dk | Dosya sayacı sırasını doğrula ve boşlukları raporla | `RxData00042.bin` eksikse boşluk bildirilir, kayıt açılmaya devam eder | `F7-028` | `feat(io): F7-029 dosya sayacı sırasını doğrula ve boşlukları raporla` |
| [ ] | `F7-030` | `4.35.0` | 20 dk | Klasör manifestini oku ve yoksa üret | Manifest sensör sayısı, örnekleme hızı, şema kimliği ve süreyi taşır | `F7-029` | `feat(io): F7-030 klasör manifestini oku ve yoksa üret` |
| [ ] | `F7-031` | `4.36.0` | 20 dk | Klasör seviyesinde indeks yapısını kur | Dosya → zaman aralığı, frame sayısı ve offset eşlemesi tek dosyada tutulur | `F7-030` | `feat(io): F7-031 klasör seviyesinde indeks yapısını kur` |
| [ ] | `F7-032` | `4.37.0` | 20 dk | İndeksi dosya adı, boyut ve değişiklik zamanıyla geçersizle | Bir dosya eklenir ya da değişirse indeks yeniden kurulur; her dosyanın hash'i alınmaz | `F7-031` | `feat(io): F7-032 i̇ndeksi dosya adı, boyut ve değişiklik zamanıyla geçersizle` |
| [ ] | `F7-033` | `4.38.0` | 15 dk | İndeksi atomik yaz | Yarıda kesilen yazım geçersiz indeks bırakmaz; geçici dosya üzerinden taşınır | `F7-032` | `feat(io): F7-033 i̇ndeksi atomik yaz` |
| [ ] | `F7-034` | `4.39.0` | 20 dk | Salt okunur klasörde indeksi bellekte kur | Yazılamayan klasörde kayıt yine açılır, yalnız açılış süresi uzar ve bu bildirilir | `F7-033` | `feat(io): F7-034 salt okunur klasörde indeksi bellekte kur` |
| [ ] | `F7-035` | `4.40.0` | 20 dk | 1.200 dosyalık kayıtta indeks kurma süresini ölç | Ölçüm `docs/perf/` altına yazılır ve Bölüm 11 bütçesiyle karşılaştırılır | `F7-034` | `test(perf): F7-035 1.200 dosyalık kayıtta indeks kurma süresini ölç` |

##### Repository ve oynatma

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F7-036` | `4.41.0` | 20 dk | `FolderRecordingRepository` iskeletini kur | `RecordingRepository` sözleşmesinin yedi metodunu da karşılar | `F7-035` | `feat(repository): F7-036 `FolderRecordingRepository` iskeletini kur` |
| [ ] | `F7-037` | `4.42.0` | 20 dk | `metadata()` zaman aralığını klasörden üret | Başlangıç ilk frame'in timestamp'i, bitiş son frame'inki; boş klasör açık hata verir | `F7-036` | `feat(repository): F7-037 `metadata()` zaman aralığını klasörden üret` |
| [ ] | `F7-038` | `4.43.0` | 20 dk | `channels()` ile Tx/Rx × 32 sensörü sun | 64 kanal kimliği üretilir; kanal yolu `Tx/Sensor 03` biçimindedir | `F7-037` | `feat(repository): F7-038 `channels()` ile Tx/Rx × 32 sensörü sun` |
| [ ] | `F7-039` | `4.44.0` | 20 dk | `query()` çağrısını dosya sınırlarını aşacak biçimde kur | Üç dosyaya yayılan bir aralık tek `DataChunk` döner, örnek sayısı beklenene eşittir | `F7-038` | `feat(repository): F7-039 `query()` çağrısını dosya sınırlarını aşacak biçimde kur` |
| [ ] | `F7-040` | `4.45.0` | 20 dk | Seyreltmeyi dosya sınırlarında tutarlı yap | Aynı aralık farklı `max_points` ile sorgulandığında dosya sınırında sıçrama olmaz | `F7-039` | `feat(repository): F7-040 seyreltmeyi dosya sınırlarında tutarlı yap` |
| [ ] | `F7-041` | `4.46.0` | 20 dk | Frame header alanlarını metadata olarak sun | CIT, transmisyon ve platform alanları Inspector'da ham değerleriyle görünür | `F7-040` | `feat(repository): F7-041 frame header alanlarını metadata olarak sun` |
| [ ] | `F7-042` | `4.47.0` | 20 dk | Önden okuma ve bellek bütçesini kur | Aynı anda bellekte tutulan dosya sayısı sınırlı; tepe bellek ölçülüp raporlanır | `F7-041` | `feat(repository): F7-042 önden okuma ve bellek bütçesini kur` |
| [ ] | `F7-043` | `4.48.0` | 20 dk | Oynatmayı dosya sınırında kesintisiz yap | Saniye sınırını geçen oynatmada boşluk ya da tekrar görülmez | `F7-042` | `feat(ui): F7-043 oynatmayı dosya sınırında kesintisiz yap` |
| [ ] | `F7-044` | `4.49.0` | 20 dk | Bozuk ve eksik dosyayı oynatmada göster | Eksik saniye zaman ekseninde boşluk olarak işaretlenir, sessizce atlanmaz | `F7-043` | `feat(ui): F7-044 bozuk ve eksik dosyayı oynatmada göster` |

##### Arayüz

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F7-045` | `4.50.0` | 20 dk | Klasör açma diyalogunu ekle | `Open Recording Folder` bir kayıt klasörü seçtirir; dosya seçimi de çalışmaya devam eder | `F7-044` | `feat(ui): F7-045 klasör açma diyalogunu ekle` |
| [ ] | `F7-046` | `4.51.0` | 15 dk | Son kullanılanlara klasör yolunu ekle | Klasör yolu saklanır ve yeniden açılır; eski dosya kayıtları bozulmaz | `F7-045` | `feat(ui): F7-046 son kullanılanlara klasör yolunu ekle` |
| [ ] | `F7-047` | `4.52.0` | 20 dk | Data Explorer'da Tx/Rx ağacını kur | Ağaçta `Tx` ve `Rx` iki üst düğüm; altlarında 32 sensör görünür | `F7-046` | `feat(ui): F7-047 data Explorer'da Tx/Rx ağacını kur` |
| [ ] | `F7-048` | `4.53.0` | 20 dk | Şema dosyası seçimini ayarlara ekle | Seçilen TOML yolu `settings.json`'a yazılır ve yeniden açılışta korunur | `F7-047` | `feat(settings): F7-048 şema dosyası seçimini ayarlara ekle` |
| [ ] | `F7-049` | `4.54.0` | 20 dk | Şema değişince açık kaydı yeniden yükle | Yeni şema uygulanır; uyuşmazsa kayıt kapanmaz, hata gösterilir | `F7-048` | `feat(ui): F7-049 şema değişince açık kaydı yeniden yükle` |
| [ ] | `F7-050` | `4.55.0` | 20 dk | Geçersiz şemayı arayüzde göster | Hangi alanın hangi offsette sorunlu olduğu diyalogda okunur | `F7-049` | `feat(ui): F7-050 geçersiz şemayı arayüzde göster` |
| [ ] | `F7-051` | `4.56.0` | 15 dk | Sürükle bırakta klasör kabul et | Klasör bırakıldığında kayıt açılır; dosya bırakma davranışı korunur | `F7-050` | `feat(ui): F7-051 sürükle bırakta klasör kabul et` |
| [ ] | `F7-052` | `4.57.0` | 20 dk | Kayıt kartında klasör ve şema bilgisini göster | Kaynak klasör, şema kimliği, sensör sayısı ve süre kartta görünür | `F7-051` | `feat(ui): F7-052 kayıt kartında klasör ve şema bilgisini göster` |

##### Sentetik üreteç ve test senaryoları

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F7-053` | `4.58.0` | 20 dk | Profil C sentetik üreteç iskeletini kur | Verilen şemaya uygun klasör, dosya ve frame üretir; üretim decoder'ı okur | `F7-052` | `feat(fixtures): F7-053 profil C sentetik üreteç iskeletini kur` |
| [ ] | `F7-054` | `4.59.0` | 20 dk | CW dalga biçimi üretimini ekle | Üretilen tonun frekansı spektrumda istenen binde tepe verir | `F7-053` | `feat(fixtures): F7-054 cW dalga biçimi üretimini ekle` |
| [ ] | `F7-055` | `4.60.0` | 20 dk | LFM yukarı ve aşağı cıvıltı üretimini ekle | Anlık frekans eğimi istenen bant genişliğini darbe süresinde tarar | `F7-054` | `feat(fixtures): F7-055 lFM yukarı ve aşağı cıvıltı üretimini ekle` |
| [ ] | `F7-056` | `4.61.0` | 20 dk | HFM ve kodlu dalga biçimi üretimini ekle | Üretilen dalga biçimi sınıflandırıcı tarafından doğru etiketlenir | `F7-055` | `feat(fixtures): F7-056 hFM ve kodlu dalga biçimi üretimini ekle` |
| [ ] | `F7-057` | `4.62.0` | 20 dk | PRI ve darbe uzunluğu parametrelerini ekle | PRI 100/150/200/500/1000 ms değerlerinde Tx segment sayısı beklenene eşittir | `F7-056` | `feat(fixtures): F7-057 pRI ve darbe uzunluğu parametrelerini ekle` |
| [ ] | `F7-058` | `4.63.0` | 20 dk | Tx/Rx bölüşümünü PRI ve darbe süresine göre yap | Tx örnek sayısı + Rx örnek sayısı tam PRI'yı verir; artık örnek kalmaz | `F7-057` | `feat(fixtures): F7-058 tx/Rx bölüşümünü PRI ve darbe süresine göre yap` |
| [ ] | `F7-059` | `4.64.0` | 20 dk | Platform ve CIT alanlarını doldur | Hız, rota ve yalpa değerleri frame başlığından geri okunur | `F7-058` | `feat(fixtures): F7-059 platform ve CIT alanlarını doldur` |
| [ ] | `F7-060` | `4.65.0` | 20 dk | Eleman arızası enjeksiyonunu ekle | Ölü, doygun, faz kaymış ve kazanç sapmış eleman senaryoları üretilir ve geri okunur | `F7-059` | `feat(fixtures): F7-060 eleman arızası enjeksiyonunu ekle` |
| [ ] | `F7-061` | `4.66.0` | 20 dk | I/Q bozulması enjeksiyonunu ekle | Kazanç dengesizliği ve kuadratur hatası istenen değerde üretilir | `F7-060` | `feat(fixtures): F7-061 i/Q bozulması enjeksiyonunu ekle` |
| [ ] | `F7-062` | `4.67.0` | 20 dk | Dosya ve şema bozulma senaryolarını ekle | Eksik dosya, kesik dosya, bozuk CRC ve şema uyuşmazlığı üretilir | `F7-061` | `feat(fixtures): F7-062 dosya ve şema bozulma senaryolarını ekle` |
| [ ] | `F7-063` | `4.68.0` | 20 dk | On iki senaryonun parametre setini tanımla | Her senaryo tek komutla üretilir; aynı tohum aynı baytları verir | `F7-062` | `feat(fixtures): F7-063 on iki senaryonun parametre setini tanımla` |
| [ ] | `F7-064` | `4.69.0` | 20 dk | Golden dilim fixture'ını üret ve SHA-256 sabitle | 4 sensör × 2 frame, 51 KiB; hash test içinde sabit tutulur | `F7-063` | `test(fixtures): F7-064 golden dilim fixture'ını üret ve SHA-256 sabitle` |
| [ ] | `F7-065` | `4.70.0` | 15 dk | Büyük senaryoların depoya girmediğini teste bağla | 3–5 dakikalık senaryolar üretilir ama sürüm denetimine eklenmez; test bunu doğrular | `F7-064` | `test(fixtures): F7-065 büyük senaryoların depoya girmediğini teste bağla` |

##### .mat dışa aktarma

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F7-066` | `4.71.0` | 20 dk | .mat dışa aktarma hedefini kaydet | `ExportKind` ve dosya filtresine eklenir; menüden seçilebilir | `F7-065` | `feat(export): F7-066 .mat dışa aktarma hedefini kaydet` |
| [ ] | `F7-067` | `4.72.0` | 20 dk | Rx ve Tx için ayrı `.mat` dosyası üret | İki dosya üretilir, adlarında kaynak klasör ve akım adı geçer | `F7-066` | `feat(export): F7-067 rx ve Tx için ayrı `.mat` dosyası üret` |
| [ ] | `F7-068` | `4.73.0` | 20 dk | Değişken düzenini kur | `data` (32 × N complex), `t_ns`, `frame_index` ve header alanları MATLAB'da okunabilir adlarla yazılır | `F7-067` | `feat(export): F7-068 değişken düzenini kur` |
| [ ] | `F7-069` | `4.74.0` | 20 dk | Metadata'yı `.mat` içine koy | Kaynak klasör, şema kimliği, örnekleme hızı, sensör sayısı ve zaman aralığı dosyadan geri okunur | `F7-068` | `feat(export): F7-069 metadata'yı `.mat` içine koy` |
| [ ] | `F7-070` | `4.75.0` | 20 dk | MAT v5 boyut sınırını denetle | Değişken 2 GiB'i aşacaksa dışa aktarma başlamadan açık hata verir, yarım dosya bırakmaz | `F7-069` | `feat(export): F7-070 mAT v5 boyut sınırını denetle` |
| [ ] | `F7-071` | `4.76.0` | 20 dk | İlerleme ve iptal desteğini bağla | Uzun dışa aktarma alt şeritte ilerleme gösterir ve iptal edilebilir | `F7-070` | `feat(export): F7-071 i̇lerleme ve iptal desteğini bağla` |
| [ ] | `F7-072` | `4.77.0` | 15 dk | Atomik yazımı kur | İptal ya da hata yarım `.mat` bırakmaz; geçici dosya üzerinden taşınır | `F7-071` | `feat(export): F7-072 atomik yazımı kur` |
| [ ] | `F7-073` | `4.78.0` | 20 dk | Üretilen `.mat`'i geri okuyarak doğrula | `scipy.io.loadmat` ile okunan dizi, kaynaktaki örneklerle bit birebir aynıdır | `F7-072` | `test(export): F7-073 üretilen `.mat`'i geri okuyarak doğrula` |

##### Başarım

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F7-074` | `4.79.0` | 20 dk | 10 dakikalık kaydın açılış süresini ölç | Ölçüm `docs/perf/` altına yazılır; bütçe aşılıyorsa hangi adımın payı olduğu gösterilir | `F7-073` | `test(perf): F7-074 10 dakikalık kaydın açılış süresini ölç` |
| [ ] | `F7-075` | `4.80.0` | 20 dk | Sorgu ve seyreltme bütçesini ölç | Tam kayıt aralığı sorgusu ve grafik yenileme süreleri raporlanır | `F7-074` | `test(perf): F7-075 sorgu ve seyreltme bütçesini ölç` |
| [ ] | `F7-076` | `4.81.0` | 20 dk | Tepe bellek kullanımını ölç | 1,173 GiB'lik kayıtta tepe bellek ölçülür ve bütçeyle karşılaştırılır | `F7-075` | `test(perf): F7-076 tepe bellek kullanımını ölç` |

##### Belgeleme ve faz kabulü

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F7-077` | `4.82.0` | 20 dk | Profil C format belgesini tamamla | Klasör düzeni, dosya header'ı, frame header'ı ve bayt bütçesi tek belgede toplanır | `F7-076` | `docs(format): F7-077 profil C format belgesini tamamla` |
| [ ] | `F7-078` | `4.83.0` | 20 dk | TOML şema kılavuzunu yaz | Enum ve struct yazımı, cpp tip tablosu ve sık yapılan hatalar örneklerle anlatılır | `F7-077` | `docs(format): F7-078 tOML şema kılavuzunu yaz` |
| [ ] | `F7-079` | `4.84.0` | 20 dk | MATLAB kullanım notunu yaz | Üretilen `.mat`'in MATLAB'da nasıl yükleneceği ve değişken düzeni anlatılır | `F7-078` | `docs(guide): F7-079 mATLAB kullanım notunu yaz` |
| [ ] | `F7-080` | `5.0.0` | 20 dk | Faz 7 milestone kabul turunu koştur ve etiketle | Sentetik senaryolar açılır, oynatılır ve `.mat` üretilir; kabul kanıtı `docs/acceptance/` altına yazılır | `F7-079` | `chore(release): F7-080 faz 7 milestone kabul turunu koştur ve etiketle` |
#### Faz 8 — Tx/Rx ham veri analizi ve sensör sağlığı

Kabul: Complex Tx/Rx verisinden seviye metrikleri, I/Q kalitesi, spektral gösterim ve
eleman sağlık teşhisi üretilir; arıza enjekte edilmiş sentetik kayıtlarda her teşhisin
tetiklendiği kanıtlanır. Etiket: `ms/09-signal-analysis`, sürüm: `v6.0.0`.

**Kapsam sınırı:** bu bir kayıt oynatma ve veri kalitesi aracıdır, bir sonar işlemcisi
değildir. Hüzmeleme, eşleştirilmiş filtre, TVG, normalizasyon, CFAR, tespit ve iz sürme
**kapsam dışıdır**. Dizi koherans ölçümleri yalnız sağlık göstergesi olarak kalır.

##### 8.A — Complex veri çekirdeği ve çok kanallı alan modeli

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F8-001` | `5.1.0` | 20 dk | analysis/complex_guard.py: complex girdide sessiz gerçek-kısım düşürmesini ComplexDataError'a çeviren tek g... | complex64 dizi summarize/one_sided_fft/welch_psd/stft/ProcessingChain.run'a verildiğinde ComplexDataError yükselir; aynı dizinin .real'i verildiğinde mevcut sayısal çıktılar bit-bit değişmez | `F7-080` | `fix(analysis): F8-001 analysis/complex_guard.py: complex girdide sessiz gerçek-kısım düşürmesini ComplexDataError'a çeviren tek g...` |
| [ ] | `F8-002` | `5.2.0` | 15 dk | pyproject.toml pytest bölümünde filterwarnings = error::numpy.exceptions.ComplexWarning | Mevcut test takımının tamamı geçer; kasıtlı complex->float dökümü yapan sentetik test ComplexWarning ile FAIL eder | `F8-001` | `chore(quality): F8-002 pyproject.toml pytest bölümünde filterwarnings = error::numpy.exceptions.ComplexWarning` |
| [ ] | `F8-003` | `5.3.0` | 15 dk | domain/channel.py SUPPORTED_DTYPES'a complex64 ve complex128 eklenir | ChannelMetadata(dtype='complex64') ve 'complex128' kurucudan geçer; 'complex32' hâlâ ValueError verir | `F8-002` | `feat(domain): F8-003 domain/channel.py SUPPORTED_DTYPES'a complex64 ve complex128 eklenir` |
| [ ] | `F8-004` | `5.4.0` | 20 dk | domain/array_frame.py: değişmez ArrayFrame (frame_index, timestamp_ns, values (32,820) complex64, quality m... | (32,820) kabul edilir; (32,819) ve 1-B girdi ValueError verir; kurucuya verilen dizi dışarıdan değiştirilince iç dizi değişmez | `F8-003` | `feat(domain): F8-004 domain/array_frame.py: değişmez ArrayFrame (frame_index, timestamp_ns, values (32,820) complex64, quality m...` |
| [ ] | `F8-005` | `5.5.0` | 20 dk | analysis/complex_spectrum.py: iki taraflı FFT (fft + fftfreq + fftshift) ve faz alanı taşıyan ComplexSpectr... | z[n]=exp(-j*2*pi*1000*n/8192), N=820 girdisinde tepe -999,0 Hz bininde (|f|=1000 Hz'e en yakın bin); +1000 Hz bölgesindeki enerji tepeden en az 50 dB aşağıda. Bilinen faz ofsetli tek tonda tepe bin... | `F8-004` | `feat(analysis): F8-005 analysis/complex_spectrum.py: iki taraflı FFT (fft + fftfreq + fftshift) ve faz alanı taşıyan ComplexSpectr...` |
| [ ] | `F8-006` | `5.6.0` | 20 dk | 820 örneklik frame için FFT plan notu ve zero-pad yardımcısı; 820 = 2^2 * 5 * 41 olduğu için radix-2 yoktur | next_fast_len(820) 1024 döner ve bin aralığı 8,0 Hz'e iner; buna rağmen 1000 Hz ve 1005 Hz'lik iki ton AYRIŞMAZ — test çözünürlüğün 9,990 Hz'de sabit kaldığını belgeler | `F8-005` | `feat(analysis): F8-006 820 örneklik frame için FFT plan notu ve zero-pad yardımcısı; 820 = 2^2 * 5 * 41 olduğu için radix-2 yoktur` |
| [ ] | `F8-007` | `5.7.0` | 20 dk | repository protokolüne query_array(channel_ids, time_range) toplu çok kanallı sorgu eklenir | 32 kanal tek çağrıda okunur; 32 ayrı query() çağrısıyla aynı değerler döner ve alt katmana yapılan okuma çağrısı sayısı 1'dir | `F8-006` | `feat(repository): F8-007 repository protokolüne query_array(channel_ids, time_range) toplu çok kanallı sorgu eklenir` |

##### 8.B — Veri sözleşmesi, zaman ekseni ve donanım zinciri doğrulaması

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F8-008` | `5.8.0` | 20 dk | Dosya boyutu Diophantine çözücüsü: dosya_boyutu = H_dosya + F*(H_frame + C*S*B) denkleminden dtype ve başlı... | 64 baytlık başlıklı sentetik int16 I/Q dosyada (10*(64+32*820*4) = 1.050.240 B) çözücü dtype=int16_iq ve H_frame=64 döner; float32 sürümde (10*(64+32*820*8) = 2.099.840 B) float32_iq ve H_frame=64... | `F8-007` | `feat(io): F8-008 dosya boyutu Diophantine çözücüsü: dosya_boyutu = H_dosya + F*(H_frame + C*S*B) denkleminden dtype ve başlı...` |
| [ ] | `F8-009` | `5.9.0` | 20 dk | Kuantalama adımı q ve etkin bit derinliği B_eff kestirimi (sıfır olmayan ardışık farkların yaklaşık OBEB'i... | 12 bitlik sentetik sinyal 8 ile çarpılıp float32 yazıldığında q = 8,0 ve B_eff = 12 okunur; sürekli float veride 'tamsayı kökenli değil' döner; her 4. kod silinince eksik kod sayacı tetiklenir | `F8-008` | `feat(io): F8-009 kuantalama adımı q ve etkin bit derinliği B_eff kestirimi (sıfır olmayan ardışık farkların yaklaşık OBEB'i...` |
| [ ] | `F8-010` | `5.10.0` | 20 dk | Bit düzeyinde takılı-bit taraması: kanal x bit toggle oranı matrisi | Kanal 7'nin bit 3'ü sıfıra sabitlendiğinde yalnız (7,3) hücresi T=0 verir; kalan hücrelerin tamamı T>0 kalır | `F8-009` | `feat(io): F8-010 bit düzeyinde takılı-bit taraması: kanal x bit toggle oranı matrisi` |
| [ ] | `F8-011` | `5.11.0` | 20 dk | Frame başlığı ikili düzeni keşif tarayıcısı: sabit adımlı offset taraması ile monoton frame indeksi ve time... | Bilinen offsetli sentetik dosyada frame_index ve timestamp offsetleri birebir bulunur ve timestamp artış adımı okunur; endianness ters çevrilince 'monoton alan bulunamadı' döner. Bulunan düzen 'ter... | `F8-010` | `feat(io): F8-011 frame başlığı ikili düzeni keşif tarayıcısı: sabit adımlı offset taraması ile monoton frame indeksi ve time...` |
| [ ] | `F8-012` | `5.12.0` | 20 dk | Frame süreklilik ve bütünlük QC motoru: indeks atlaması, tekrar, timestamp monotonluğu, percent_availabilit... | 1000 frame'e 3 atlama, 2 tekrar, 1 geriye giden timestamp enjekte edilince gaps=3, duplicates=2, non_monotonic=1, availability %99,7 çıkar; frame 7 frame 8'e kopyalanınca içerik tekrarı sayacı 1, k... | `F8-011` | `feat(analysis): F8-012 frame süreklilik ve bütünlük QC motoru: indeks atlaması, tekrar, timestamp monotonluğu, percent_availabilit...` |
| [ ] | `F8-013` | `5.13.0` | 15 dk | Örnek-sayısı ile zaman damgası arasındaki sürüklenme ölçümü: drift_ppm = (dt_timestamp - N/fs)/(N/fs)*1e6,... | Timestamp adımı tam 100,000 ms olan akışta drift = -975,6 ppm +-1 (İŞARET NEGATİF; N/fs = 100,0977 ms); adım 100,0977 ms olduğunda 0 +-1 ppm; her 100 frame'de 1 atlama eklendiğinde sürüklenme değiş... | `F8-012` | `feat(analysis): F8-013 örnek-sayısı ile zaman damgası arasındaki sürüklenme ölçümü: drift_ppm = (dt_timestamp - N/fs)/(N/fs)*1e6,...` |
| [ ] | `F8-014` | `5.14.0` | 20 dk | Frame-arası faz sürekliliği testi: kararlı dar bant bileşende frame sınırındaki faz sıçramasından alt-örnek... | 0,8 örneklik boşluk enjekte edilen sentetik akışta g = 0,80 +-0,05 örnek; boşluksuz akışta g = 0,00 +-0,05 örnek. Sonuç, frame-arası koherent işlemenin açılıp açılmayacağının tek kapısıdır | `F8-013` | `feat(analysis): F8-014 frame-arası faz sürekliliği testi: kararlı dar bant bileşende frame sınırındaki faz sıçramasından alt-örnek...` |
| [ ] | `F8-015` | `5.15.0` | 20 dk | Kanal örnekleme eşzamanlılığı testi: ortak geçici olayda kanal başına grup gecikmesinden 'simültane S/H' mi... | Kanal başına 1/(32*8192) = 3,815 us sabit artan gecikme enjekte edilince 'mux' kararı ve ölçülen adım 3,815 +-0,2 us; rastgele gecikmede 'simültane' kararı. Bu iş, F8-061 geometri sınıfı çıkarımını... | `F8-014` | `feat(analysis): F8-015 kanal örnekleme eşzamanlılığı testi: ortak geçici olayda kanal başına grup gecikmesinden 'simültane S/H' mi...` |
| [ ] | `F8-016` | `5.16.0` | 20 dk | Anti-alias bant kenarı ölçümü: çok frame ortalamalı iki taraflı gürültü PSD'sinden gerçek kullanılabilir B | Bilinen köşeli FIR ile filtrelenmiş beyaz gürültüde -3 dB kenarı +-1 bin (9,99 Hz) içinde bulunur; filtresiz beyaz gürültüde 'kenar yok / olası aliasing' uyarısı döner. B = fs varsayımı hiçbir yerd... | `F8-015` | `feat(analysis): F8-016 anti-alias bant kenarı ölçümü: çok frame ortalamalı iki taraflı gürültü PSD'sinden gerçek kullanılabilir B` |
| [ ] | `F8-017` | `5.17.0` | 20 dk | I/Q yerleşim hipotezi seçici: interleaved/planar x kanal-majör/örnek-majör dört hipotezin dairesellik, zarf... | Planar yazılıp interleaved okunan dar bant sinyalde doğru hipotez |rho| < 0,1 ile kazanır, yanlış hipotez |rho| > 0,7 verir; seçim güven marjıyla birlikte raporlanır | `F8-016` | `feat(io): F8-017 i/Q yerleşim hipotezi seçici: interleaved/planar x kanal-majör/örnek-majör dört hipotezin dairesellik, zarf...` |

##### 8.C — Seviye metrikleri: Vpp, Vrms, PAPR ve kırpılma

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F8-018` | `5.18.0` | 20 dk | LevelMetrics: akustik grup (Vpp_env = 2*max|z|, A_rms, Vrms_pb = A_rms/sqrt(2)) ve ADC başlık grubu (I_pp,... | z1 = 1000*exp(j*2*pi*1000*n/8192) ve z2 = 1000 (sabit) için her ikisinde Vpp_env = 2000,0 ve Vrms_pb = 707,1 (+-0,1); I_pp z1'de 2000,0, z2'de 0,0 çıkar. z2'de 'Vpp' olarak 0 gösteren bir çıktı tes... | `F8-017` | `feat(analysis): F8-018 levelMetrics: akustik grup (Vpp_env = 2*max|z|, A_rms, Vrms_pb = A_rms/sqrt(2)) ve ADC başlık grubu (I_pp,...` |
| [ ] | `F8-019` | `5.19.0` | 15 dk | dBFS dönüşümü: yalnız tam ölçek referansı bilindiğinde; float veride None ve 'göreli dB' etiketi | int16 kanalda A_rms = 1000 count için 20*log10(1000/32768) = -30,3 dBFS +-0,1; float32 kanalda None döner ve birim etiketi 'göreli dB' olur | `F8-018` | `feat(analysis): F8-019 dBFS dönüşümü: yalnız tam ölçek referansı bilindiğinde; float veride None ve 'göreli dB' etiketi` |
| [ ] | `F8-020` | `5.20.0` | 20 dk | Tepe faktörü / PAPR iki ayrı tanımla: CF_env = max|z|/A_rms ve CF_pb = sqrt(2)*max|z|/A_rms; pencere kapsam... | Sabit zarflı CW'de CF_env = 0,00 +-0,01 dB ve CF_pb = 3,01 +-0,01 dB; dairesel Gauss gürültüde (N=820) CF_env = 8,58 +-1,5 dB. Pencere kapsamı alanı boş bırakılırsa çıktı üretilmez (PRI geneli hesa... | `F8-019` | `feat(analysis): F8-020 tepe faktörü / PAPR iki ayrı tanımla: CF_env = max|z|/A_rms ve CF_pb = sqrt(2)*max|z|/A_rms; pencere kapsam...` |
| [ ] | `F8-021` | `5.21.0` | 20 dk | Kırpılma tespiti iki yöntemle: tam ölçek biliniyorsa doğrudan sayım, bilinmiyorsa histogram uç-bin yığılma... | 820 örnekten tam 41'i +-32767'ye sabitlenince CR = 0,050000; kırpılmamış sinyalde CR = 0. Tam ölçek bilinmeyen modda kırpılmış sinyalde uç-bin oranı > 10, kırpılmamışta 1,0 +-0,3; aynı maksimum değ... | `F8-020` | `feat(analysis): F8-021 kırpılma tespiti iki yöntemle: tam ölçek biliniyorsa doğrudan sayım, bilinmiyorsa histogram uç-bin yığılma...` |
| [ ] | `F8-022` | `5.22.0` | 15 dk | Donmuş örnek / dijital ölü kanal metriği (QARTOD Flat Line): ardışık aynı değer oranı F ve I=Q=0 oranı Z | Kanal 7'nin son 300 örneği sabitlenince F = 0,366 +-0,002 ve bayrak = 4 (FAIL); 3 örnek sabitlenince bayrak = 3 (SUSPECT); temiz kanalda bayrak = 1 (PASS). REP_CNT_FAIL=5 / REP_CNT_SUSPECT=3 eşikle... | `F8-021` | `feat(analysis): F8-022 donmuş örnek / dijital ölü kanal metriği (QARTOD Flat Line): ardışık aynı değer oranı F ve I=Q=0 oranı Z` |
| [ ] | `F8-023` | `5.23.0` | 20 dk | Kuantalama gürültü tabanı ve ENOB kıyası: ölçülen taban ile teorik q^2/(12*fs) tabanının farkı; 'ölü' ile '... | q adımlı sentetik beyaz gürültüde ölçülen taban 10*log10(q^2/(12*fs)) ile +-0,5 dB eşleşir ve kanal 'kuantalama-sınırlı' etiketlenir; 6 dB gürültü eklenince fark 6 +-0,5 dB büyür ve etiket düşer | `F8-022` | `feat(analysis): F8-023 kuantalama gürültü tabanı ve ENOB kıyası: ölçülen taban ile teorik q^2/(12*fs) tabanının farkı; 'ölü' ile '...` |

##### 8.D — I/Q kalitesi: DC, kazanç, kuadratür ve ayna bastırma

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F8-024` | `5.24.0` | 15 dk | DC ofset / LO sızıntısı: mean(I), mean(Q) ve complex DCR_dB = 10*log10(|mu|^2/(E|z|^2-|mu|^2)) | A_rms = 1000 olan sinyale |mu| = 10 DC eklenince DCR = -40,0 +-0,1 dB; DC'siz sinyalde -60 dB'den küçük. Uyarı/arıza eşikleri (-40 / -30 dB) yapılandırılabilir, öntanım önerisidir | `F8-023` | `feat(analysis): F8-024 dC ofset / LO sızıntısı: mean(I), mean(Q) ve complex DCR_dB = 10*log10(|mu|^2/(E|z|^2-|mu|^2))` |
| [ ] | `F8-025` | `5.25.0` | 20 dk | Kazanç dengesizliği g_hat = Q_rms/I_rms ve kuadratür faz hatası phi_hat = arcsin(E[I*Q]/(I_rms*Q_rms)) — GE... | g=1,05 ve phi=2,0 derece enjekte edilince g_hat = 1,050 +-0,002 ve phi_hat = 2,00 +-0,05 derece; aritmetik ortalama normalizasyonu kullanan sürüm aynı girdide sistematik olarak küçük değer verir ve... | `F8-024` | `feat(analysis): F8-025 kazanç dengesizliği g_hat = Q_rms/I_rms ve kuadratür faz hatası phi_hat = arcsin(E[I*Q]/(I_rms*Q_rms)) — GE...` |
| [ ] | `F8-026` | `5.26.0` | 20 dk | Kör IMRR: dairesellik katsayısı rho = E[z^2]/E[|z|^2], IMRR_dB yaklaşık 20*log10|rho| - 6,02; geçerlilik ka... | g=1,05 / phi=2,0 derece enjekte edilince IMRR = -30,32 +-0,5 dBc; bozulmasız kanalda -55 dBc'den küçük. Geçerlilik kapısı: baseband tepesi 0 Hz'e YA DA +-4096 Hz'e (2*f0 sıfıra katlanır) yakınsa 'g... | `F8-025` | `feat(analysis): F8-026 kör IMRR: dairesellik katsayısı rho = E[z^2]/E[|z|^2], IMRR_dB yaklaşık 20*log10|rho| - 6,02; geçerlilik ka...` |
| [ ] | `F8-027` | `5.27.0` | 15 dk | Doğrudan IMRR: baskın ton varken S(-f0)/S(+f0); f0 tepe konumundan bulunur, f_c bilinmesi gerekmez | Yalnız +f0'da ton konan kanalda -50 dB'den küçük; bilinen oranda ayna enjekte edilmiş kanalda enjekte edilen oran +-1 dB içinde geri okunur | `F8-026` | `feat(analysis): F8-027 doğrudan IMRR: baskın ton varken S(-f0)/S(+f0); f0 tepe konumundan bulunur, f_c bilinmesi gerekmez` |
| [ ] | `F8-028` | `5.28.0` | 20 dk | Kanal-arası I/Q tutarlılığı: delta_g_m, delta_phi_m, delta_IMRR_m medyana göre; 'tek kanal mı sistem mi' ay... | 32 kanala ortak 1,0 derecelik kayma + kanal 11'e ek 2,0 derece enjekte edilince çıktı 'sistem seviyesi kayma 1,0 derece' ve 'kanal 11 sapması 2,0 derece' olarak ayrışır (+-0,1 derece) | `F8-027` | `feat(analysis): F8-028 kanal-arası I/Q tutarlılığı: delta_g_m, delta_phi_m, delta_IMRR_m medyana göre; 'tek kanal mı sistem mi' ay...` |

##### 8.E — İki taraflı spektral altyapı ve koherans

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F8-029` | `5.29.0` | 20 dk | welch_psd'nin iki taraflı complex yolu (mevcut |X|^2/(K*fs*sum(w^2)) normalizasyonu korunarak) ve segment b... | Mevcut gerçek-girdi PSD testlerinin sayısal çıktıları bit-bit değişmez; complex beyaz gürültüde iki taraflı integrasyon toplam gücü +-0,2 dB verir. Tek 820 örneklik frame'de varsayılan 256 uzunluk... | `F8-028` | `feat(analysis): F8-029 welch_psd'nin iki taraflı complex yolu (mevcut |X|^2/(K*fs*sum(w^2)) normalizasyonu korunarak) ve segment b...` |
| [ ] | `F8-030` | `5.30.0` | 20 dk | Pencere kataloğunu genişletme: Blackman-Harris-4, Nuttall, Tukey, Kaiser (mevcut windows.py referans tablo... | Her yeni pencere için hesaplanan koherent kazanç ve ENBW, referans tablodaki değerle %0,1'den az sapar; Tukey alpha=0 dikdörtgene, alpha=1 Hann'a yakınsar | `F8-029` | `feat(analysis): F8-030 pencere kataloğunu genişletme: Blackman-Harris-4, Nuttall, Tukey, Kaiser (mevcut windows.py referans tablo...` |
| [ ] | `F8-031` | `5.31.0` | 20 dk | Çapraz spektrum S_mk(f) ve genlik-kare koherans gamma^2_mk(f) matrisi | 32 bağımsız complex Gauss kanalda K=16 örtüşmesiz segmentle ortalama gamma^2 = 0,0625 +-0,02 (teorik 1/K); kanal 4 kanal 5'e kopyalanınca gamma^2_45 = 1,00 +-0,001 | `F8-030` | `feat(analysis): F8-031 çapraz spektrum S_mk(f) ve genlik-kare koherans gamma^2_mk(f) matrisi` |
| [ ] | `F8-032` | `5.32.0` | 20 dk | Koherans anlamlılık eşiği gamma^2_crit = 1 - alpha^(1/(K-1)) ve ÖRTÜŞMELİ Welch için etkin K düzeltmesi | Örtüşmesiz K=16 ve alpha=0,05 için gamma^2_crit = 0,181 +-0,001; %50 örtüşmeli 16 segmentte etkin K 16'dan küçük çıkar ve eşik YÜKSELİR — test bu yönü kilitler. K<10 iken çıktı 'istatistiksel olara... | `F8-031` | `feat(analysis): F8-032 koherans anlamlılık eşiği gamma^2_crit = 1 - alpha^(1/(K-1)) ve ÖRTÜŞMELİ Welch için etkin K düzeltmesi` |
| [ ] | `F8-033` | `5.33.0` | 20 dk | Bant içi spektral eğim: log-genlik/frekans doğrusal uydurma, birim dB/kHz (dB/oktav DEĞİL — f_c bilinmediği... | Kanal 3'e +2,0 dB/kHz eğimli çarpan uygulanınca 2,0 +-0,2 dB/kHz ölçülür; düz kanallarda |eğim| < 0,2 dB/kHz. Çıktı biriminde 'oktav' kelimesi geçmez (metin taraması testi) | `F8-032` | `feat(analysis): F8-033 bant içi spektral eğim: log-genlik/frekans doğrusal uydurma, birim dB/kHz (dB/oktav DEĞİL — f_c bilinmediği...` |

##### 8.F — Eleman sağlık teşhisi, dizi koheransı ve karar motoru

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F8-034` | `5.34.0` | 20 dk | Kanal-arası göreli seviye haritası ve robust aykırı tespiti (medyan + MAD, Iglewicz-Hoaglin modified z) | 32 kanala sigma=0,3 dB kazanç dağılımı + kanal 9'a -6,0 dB enjekte edilince g_9 = -6,0 +-0,3 dB ve |M_9| > 3,5 çıkar; sağlam kanalların tamamında |M| < 3,5. 3,5 eşiği yapılandırılabilir, öntanım ön... | `F8-033` | `feat(analysis): F8-034 kanal-arası göreli seviye haritası ve robust aykırı tespiti (medyan + MAD, Iglewicz-Hoaglin modified z)` |
| [ ] | `F8-035` | `5.35.0` | 15 dk | Göreli gürültü tabanı sapması delta_NL_m (dizi medyanına göre, ortak-mod bastırmalı) | Kanal 5'e +6,0 dB, kanal 11'e -20,0 dB uygulanınca delta_NL = +6,0 +-0,3 ve -20,0 +-0,3 dB; diğer 30 kanalda |delta_NL| < 0,5 dB. Mutlak seviye izlenmez, yalnız medyana göre fark izlenir | `F8-034` | `feat(analysis): F8-035 göreli gürültü tabanı sapması delta_NL_m (dizi medyanına göre, ortak-mod bastırmalı)` |
| [ ] | `F8-036` | `5.36.0` | 20 dk | 32x32 karmaşık korelasyon matrisi ile ölü kanal, cross-talk ve polarite tersliği bayrakları | Kanal 8 = -1 * kanal 9 yapılınca |rho_89| yaklaşık 1 ve Re{rho_89} < 0 -> polarite bayrağı; kanal 12 sıfırlanınca 12. satır ve sütun yaklaşık 0; kanal 2-3 arası %90 sızıntıda köşegen dışı hücre 1'e... | `F8-035` | `feat(analysis): F8-036 32x32 karmaşık korelasyon matrisi ile ölü kanal, cross-talk ve polarite tersliği bayrakları` |
| [ ] | `F8-037` | `5.37.0` | 20 dk | Kovaryans kestirimi: snapshot'lar frame İÇİ komşu FFT binlerinden alınır; frame-ARASI toplama F8-014 kanıtı... | Frame-arası mod, F8-014 bitişiklik kanıtı yokken çağrıldığında hata yükseltir ve sonuç döndürmez; frame-içi modda kullanılan K ve karşılık gelen çözünürlük (K=64 için delta_f = 8192/13 yaklaşık 640... | `F8-036` | `feat(analysis): F8-037 kovaryans kestirimi: snapshot'lar frame İÇİ komşu FFT binlerinden alınır; frame-ARASI toplama F8-014 kanıtı...` |
| [ ] | `F8-038` | `5.38.0` | 20 dk | Özdeğer spektrumu, sayısal rank, koşul sayısı (Marchenko-Pastur referansıyla) ve özvektör yoğunlaşma metriğ... | 32 kanal beyaz gürültüde K=64'te kappa 25-45 aralığında (MP tahmini 34,0) ve rank=32; K=96'da MP tahmini 13,9, K=256'da 4,4, K=820'de 2,2 (+-%20). Kanal 20 sıfırlanınca lambda_32 yaklaşık 0, rank=3... | `F8-037` | `feat(analysis): F8-038 özdeğer spektrumu, sayısal rank, koşul sayısı (Marchenko-Pastur referansıyla) ve özvektör yoğunlaşma metriğ...` |
| [ ] | `F8-039` | `5.39.0` | 20 dk | Örtüşen çift korelasyon arıza tekilleştiricisi: kanal haritası bilinmediği için 32*31/2 = 496 çiftin tamamı... | Kanal 17 bozulunca 'en çok düşük çiftte ortak olan eleman' 17 seçilir; kanal 17 ve 25 birlikte bozulunca ikisi de listelenir ve sağlam kanalların hiçbiri listeye girmez | `F8-038` | `feat(analysis): F8-039 örtüşen çift korelasyon arıza tekilleştiricisi: kanal haritası bilinmediği için 32*31/2 = 496 çiftin tamamı...` |
| [ ] | `F8-040` | `5.40.0` | 20 dk | PCA leave-one-out rekonstrüksiyon kalıntısı (SVI) ve ön koşul kapısı: lambda_1/lambda_ort yetersizse yöntem... | lambda_1/lambda_2 > 20 olan ortak-kaynaklı veride kanal 15 (30 derece faz) ve kanal 22 (-6 dB) SVI değeri kalan 30 kanalın medyanının en az 5 katı; uzamsal beyaz gürültüde AYNI test hiçbir kanalı a... | `F8-039` | `feat(analysis): F8-040 pCA leave-one-out rekonstrüksiyon kalıntısı (SVI) ve ön koşul kapısı: lambda_1/lambda_ort yetersizse yöntem...` |
| [ ] | `F8-041` | `5.41.0` | 20 dk | Çok-metrik karar motoru: OK / UYARI / ARIZA durum makinesi, tetikleyen metrik listesi, kanal maskeleme çıkışı | Yalnız tek metrik işaretlediğinde durum UYARI'da kalır; iki bağımsız metrik işaretlediğinde ARIZA olur ve gerekçe listesi iki metriği de içerir. Arızalı kanal, hüzmeleme ve kovaryans girdisinden dı... | `F8-040` | `feat(analysis): F8-041 çok-metrik karar motoru: OK / UYARI / ARIZA durum makinesi, tetikleyen metrik listesi, kanal maskeleme çıkışı` |
| [ ] | `F8-042` | `5.42.0` | 20 dk | Eleman ekseni DFT'si: her frekans bininde 32 elemanlı vektöre FFT; eksen 'derece/eleman faz ilerlemesi' (u... | Eleman başına tam 45 derece faz ilerlemesi enjekte edilince tepe 45,0 +-2 derece/eleman'da çıkar; eksen etiketi metninde 'kerteriz', 'azimut' veya 'yön kosinüsü' GEÇMEZ (metin taraması testi) | `F8-041` | `feat(analysis): F8-042 eleman ekseni DFT'si: her frekans bininde 32 elemanlı vektöre FFT; eksen 'derece/eleman faz ilerlemesi' (u...` |
| [ ] | `F8-043` | `5.43.0` | 20 dk | Ölçülen koherent dizi kazancı: baş özvektör hüzmeleyici (yön vektörü gerektirmez), teorik üst sınırdan sapma | Tam koherent tek kaynak + beyaz gürültüde AG = 15,0 +-0,5 dB (10*log10(32) = 15,05); kanal 7 öldürülünce 14,9 dB'ye (10*log10(31) = 14,91) düşer; 4 kanal öldürülünce 14,5 dB'ye (10*log10(28) = 14,4... | `F8-042` | `feat(analysis): F8-043 ölçülen koherent dizi kazancı: baş özvektör hüzmeleyici (yön vektörü gerektirmez), teorik üst sınırdan sapma` |
| [ ] | `F8-044` | `5.44.0` | 20 dk | Geometri sınıfı hipotez testi (doğrusal vs dairesel) ve kanal haritası doğrulaması (korelasyon matrisinin b... | Sentetik ULA'da 'doğrusal' kararı ve kalıntı < 3 derece; sentetik UCA'da doğrusal model kalıntısı dairesel modelinkinin en az 5 katı; kanal sırası karıştırılınca 'kanal haritası şüpheli' bayrağı ka... | `F8-043` | `feat(analysis): F8-044 geometri sınıfı hipotez testi (doğrusal vs dairesel) ve kanal haritası doğrulaması (korelasyon matrisinin b...` |

##### 8.G — Tx yayın kalitesi ve dalga biçimi betimlemesi

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F8-045` | `5.45.0` | 20 dk | Tx klasörü ham envanteri: kanal sayısı ve frame başına örnek sayısı dosya boyutundan ÖLÇÜLÜR; Rx ile uyuşma... | 32x820 sentetik Tx dosyasında (32, 820) ölçülür; 8x820 dosyada (8, 820) ölçülür ve 'Rx ile kanal sayısı uyuşmuyor' uyarısı çıkar. Envanter çıktısı 'kaynak belirsiz' etiketi taşır ve Tx-referanslı k... | `F8-044` | `feat(io): F8-045 tx klasörü ham envanteri: kanal sayısı ve frame başına örnek sayısı dosya boyutundan ÖLÇÜLÜR; Rx ile uyuşma...` |
| [ ] | `F8-046` | `5.46.0` | 20 dk | Darbe envanteri: zarf eşiği ve histerezisle Tx segment tespiti, alt-örnek interpolasyonlu TOA, PW, IEEE 181... | Tam 164 örneklik darbe 300. örnekte başlatılınca TOA = 300,0 +-0,5 örnek ve PW = 164 +-0,5 örnek; 10 örneklik yükselen kosinüs kenarda t_rise = 8,0 +-1 örnek; 2 dB droop enjekte edilince 2,0 +-0,2... | `F8-045` | `feat(analysis): F8-046 darbe envanteri: zarf eşiği ve histerezisle Tx segment tespiti, alt-örnek interpolasyonlu TOA, PW, IEEE 181...` |
| [ ] | `F8-047` | `5.47.0` | 20 dk | Anlık frekans kestirimi: CFD f[n] = arg(z[n+1]*conj(z[n-1]))/(4*pi*T) ve ayrı adlandırılmış FFD f[n] = arg(... | CW f0=1000 Hz'de CFD sabit 1000 +-2 Hz verir; LFM girdisinde CFD'nin yanlılığı FFD'ninkinden küçüktür ve test iki kestiriciyi karşılaştırıp bu sırayı kilitler (FFD yarım örnek grup gecikmesi taşır)... | `F8-046` | `feat(analysis): F8-047 anlık frekans kestirimi: CFD f[n] = arg(z[n+1]*conj(z[n-1]))/(4*pi*T) ve ayrı adlandırılmış FFD f[n] = arg(...` |
| [ ] | `F8-048` | `5.48.0` | 20 dk | Dalga biçimi sınıflandırıcısı (CW / LFM-up / LFM-down / kodlu) ve faz-bölgesi kalıntısı ile chirp doğrusallığı | B=2000 Hz ve T=20 ms LFM'de k = 100.000 Hz/s %1'den az sapmayla geri kazanılır ve doğrusallık hatası e_rms < 20 Hz (%1 * B); CW girdide sınıf = CW; 4 fazlı kodlu dizide sınıf = kodlu ve atlama sayı... | `F8-047` | `feat(analysis): F8-048 dalga biçimi sınıflandırıcısı (CW / LFM-up / LFM-down / kodlu) ve faz-bölgesi kalıntısı ile chirp doğrusallığı` |
| [ ] | `F8-049` | `5.49.0` | 20 dk | PRI / PRF / jitter: TOA tabanlı ve timestamp tabanlı iki bağımsız ölçüm, histogram, kümülatif zaman hatası,... | PRI = 1024 örnek ve sigma = 5 örnek jitterli 200 darbede PRI_ort = 1024,0 +-0,2 örnek ve sigma_PRI = 5,0 +-0,5 örnek; PRI 1024/1152 arasında dönüşümlü yapılınca histogram iki modlu ve sınıf 'stagge... | `F8-048` | `feat(analysis): F8-049 pRI / PRF / jitter: TOA tabanlı ve timestamp tabanlı iki bağımsız ölçüm, histogram, kümülatif zaman hatası,...` |
| [ ] | `F8-050` | `5.50.0` | 20 dk | Tx/Rx örnek bütçesi kapanış testi: N_tx + N_rx toplamından PRI ve T_tx ölçümü, sabit/uyarlamalı kapı kararı | PRI = 300 ms ve T_tx = 20 ms kurulmuş sentetik kayıtta ikisi de +-1 örnek geri okunur; kapı +-5 örnek oynatılınca 'uyarlamalı kapı' bayrağı kalkar ve PRI yalnız timestamp'ten alınır. Toplamın 820 m... | `F8-049` | `feat(analysis): F8-050 tx/Rx örnek bütçesi kapanış testi: N_tx + N_rx toplamından PRI ve T_tx ölçümü, sabit/uyarlamalı kapı kararı` |
| [ ] | `F8-051` | `5.51.0` | 20 dk | Darbe-arası genlik/faz kararlılığı, normalize koherens gamma, frekans ofseti sürüklenmesi ve delta_phi_p di... | sigma_phi = 3,0 derece ve sigma_A/A_ort = %2 enjekte edilince 3,0 +-0,3 derece ve 2,0 +-0,3 % ölçülür, gamma >= 0,995; darbe başına 0,5 derecelik doğrusal rampa enjekte edilince ölçülen frekans ofs... | `F8-050` | `feat(analysis): F8-051 darbe-arası genlik/faz kararlılığı, normalize koherens gamma, frekans ofseti sürüklenmesi ve delta_phi_p di...` |
| [ ] | `F8-052` | `5.52.0` | 20 dk | Alıcı toparlanma süresi tau_rec: Tx sonrası zarfa üstel+sabit uydurma, kanal-kanal fark olarak (reverberasy... | Kanal 11'e 30 örnek zaman sabitli üstel toparlanma kuyruğu eklenince yalnız kanal 11'in medyandan sapması 3 MAD'ı aşar; diğer 31 kanal eşikte kalır | `F8-051` | `feat(analysis): F8-052 alıcı toparlanma süresi tau_rec: Tx sonrası zarfa üstel+sabit uydurma, kanal-kanal fark olarak (reverberasy...` |
| [ ] | `F8-053` | `5.53.0` | 20 dk | Ölçülen Tx replikası: çok darbeli koherent ortalama (genlik-SNR sqrt(P), güç-SNR P kat) | 100 darbenin koherent ortalamasında gürültü genliği 10 kat azalır, yani güç-SNR 20,0 +-1,0 dB (10*log10(100)) artar; kırpılmış frame'ler ortalamadan dışlanır ve dışlanan sayı raporlanır | `F8-052` | `feat(analysis): F8-053 ölçülen Tx replikası: çok darbeli koherent ortalama (genlik-SNR sqrt(P), güç-SNR P kat)` |

##### 8.H — Rx pasif gösterim ürünleri

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F8-054` | `5.54.0` | 20 dk | RX bant şelalesi paneli verisi: frame başına iki taraflı STFT, eksen 'f - f_c (Hz)', 9,99 Hz bin, saniyede... | +1500 Hz'de kalıcı ton konan sentetik akışta şelale tepesi +1500 Hz'e en yakın binde (+-1 bin) kalır; ürün adı 'RX Bant Şelalesi' ve eksen etiketi 'f - f_c (Hz)' olur, çıktı metninde 'LOFARgram' ke... | `F8-053` | `feat(analysis): F8-054 rX bant şelalesi paneli verisi: frame başına iki taraflı STFT, eksen 'f - f_c (Hz)', 9,99 Hz bin, saniyede...` |
| [ ] | `F8-055` | `5.55.0` | 15 dk | Geniş bant enerji izi: kanal ve frame başına toplam |z|^2, göreli dB | Kanal gücü 6,0 dB artırılan frame aralığında iz 6,0 +-0,2 dB yükselir ve aynı aralık dışında değişmez; birim 'göreli dB' etiketlidir | `F8-054` | `feat(analysis): F8-055 geniş bant enerji izi: kanal ve frame başına toplam |z|^2, göreli dB` |
| [ ] | `F8-056` | `5.56.0` | 20 dk | Zarf modülasyon spektrumu (DEMON çekirdeği): e[n] = |z[n]|^2, alçak geçiren, desimasyon fazı frame sınırınd... | 7,0 Hz'de %30 zarf modülasyonu enjekte edilen 100 frame'lik akışta 7,0 +-0,1 Hz çizgisi bulunur; desimasyon fazı frame sınırında sıfırlanan bir sürüm aynı testte başarısız olur (regresyon testi kes... | `F8-055` | `feat(analysis): F8-056 zarf modülasyon spektrumu (DEMON çekirdeği): e[n] = |z[n]|^2, alçak geçiren, desimasyon fazı frame sınırınd...` |
| [ ] | `F8-057` | `5.57.0` | 20 dk | DEMON PRI-tarağı belirsizlik kapısı: kapılama zarf spektrumunu PRI tarağıyla katladığı için etkilenen binle... | Modülasyon 10,0 Hz'e (PRI harmoniği) taşındığında sistem hedef ilan ETMEZ ve 'PRI tarağıyla çakışıyor, ayrıştırılamaz' döner; PRI ile katlanma nedeniyle 1/PRI'nin yarısı üstündeki tüm binler 'belir... | `F8-056` | `feat(analysis): F8-057 dEMON PRI-tarağı belirsizlik kapısı: kapılama zarf spektrumunu PRI tarağıyla katladığı için etkilenen binle...` |

##### 8.I — Ölçekleme ve kalibrasyon katmanı

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F8-058` | `5.58.0` | 20 dk | array_profile.json şeması: status (UNCALIBRATED/PARTIAL/CALIBRATED), acquisition, array (tip, eleman konuml... | Tüm alanları null olan profil yüklendiğinde geometri ve kalibrasyon bağlı ürünlerin tamamı 'kilitli' döner ve her biri kendi gerekçe metnini taşır; ULA profili yüklenince yalnız geometri bağlı olan... | `F8-057` | `feat(config): F8-058 array_profile.json şeması: status (UNCALIBRATED/PARTIAL/CALIBRATED), acquisition, array (tip, eleman konuml...` |
| [ ] | `F8-059` | `5.59.0` | 20 dk | Ölçekleme alt şeması (adc_bits, adc_fullscale_v, analog_gain_db, iq_convention_gain, hydrophone_sensitivity... | status UNCALIBRATED ve offset 0 iken hiçbir çıktı metninde 'V', 'mV' veya 'Pa' birimi geçmez (tüm rapor ve panel başlıklarını tarayan metin testi); tüm seviye hesapları level_dB = 10*log10(P_count)... | `F8-058` | `feat(config): F8-059 ölçekleme alt şeması (adc_bits, adc_fullscale_v, analog_gain_db, iq_convention_gain, hydrophone_sensitivity...` |
| [ ] | `F8-060` | `5.60.0` | 20 dk | Mutlak Vpp/Vrms dönüşümü (sabitler girildiğinde açılır) ve konvansiyon belirsizliği notu | adc_bits=16, adc_fullscale_v=1,0, analog_gain_db=0 ile A_rms=1000 count girdisinde Vrms_pb = 0,0216 V (%0,1'den az sapma); iq_convention_gain null iken çıktı '+-6 dB konvansiyon belirsizliği' notun... | `F8-059` | `feat(analysis): F8-060 mutlak Vpp/Vrms dönüşümü (sabitler girildiğinde açılır) ve konvansiyon belirsizliği notu` |
| [ ] | `F8-061` | `5.61.0` | 20 dk | AGC/TVG imza testi: PRI'dan PRI'ya kuantumlu basamaklı taban seviyesi sıçraması taraması | PRI'dan PRI'ya 6 dB kuantumlu basamak enjekte edilen kanalda 'AGC şüphesi' bayrağı kalkar ve o oturumun tüm seviye metrikleri bu bayrakla işaretlenir; basamaksız kayıtta bayrak kalkmaz. 'AGC uygula... | `F8-060` | `feat(analysis): F8-061 aGC/TVG imza testi: PRI'dan PRI'ya kuantumlu basamaklı taban seviyesi sıçraması taraması` |

##### 8.M — Görselleştirme panelleri

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F8-062` | `5.62.0` | 20 dk | Cross Analysis sekmesini etkinleştir (ENABLED_TABS + _on_view_tab_changed) ve 32x32 korelasyon/koherans ısı... | Sekme etkinleşir ve ipucundaki NOT_YET_AVAILABLE metni kalkar; ölü kanal ısı haritasında boş satır ve sütun olarak görünür, cross-talk çifti 1'e yakın köşegen dışı hücre olarak; veri yokken sahte m... | `F8-061` | `feat(ui): F8-062 cross Analysis sekmesini etkinleştir (ENABLED_TABS + _on_view_tab_changed) ve 32x32 korelasyon/koherans ısı...` |
| [ ] | `F8-063` | `5.63.0` | 20 dk | Kanal x frekans sapma ısı haritası (medyandan dB) ile özdeğer scree grafiği ve koşul sayısı göstergesini ay... | -20 dB'lik kanal 11 tek bakışta ayırt edilir; scree grafiğinde K=64 için Marchenko-Pastur referans çizgisi 34,0'da çizilir ve ölçülen kappa onun yanında görünür; renk skalasına ek olarak desen/simg... | `F8-062` | `feat(ui): F8-063 kanal x frekans sapma ısı haritası (medyandan dB) ile özdeğer scree grafiği ve koşul sayısı göstergesini ay...` |
| [ ] | `F8-064` | `5.64.0` | 20 dk | Eleman sağlık matrisi (32 hücre x durum, tetikleyen metrik ipucu) ve karmaşık kazanç polar grafiği aynı pan... | OK / UYARI / ARIZA üç durum renk VE simge ile ayrışır; hücre üzerine gelince tetikleyen metrikler listelenir; polar grafikte -6 dB'lik ve +30 derecelik iki sapan eleman sağlıklı kümenin dışında gör... | `F8-063` | `feat(ui): F8-064 eleman sağlık matrisi (32 hücre x durum, tetikleyen metrik ipucu) ve karmaşık kazanç polar grafiği aynı pan...` |
| [ ] | `F8-065` | `5.65.0` | 20 dk | 3D View sekmesini etkinleştir ve kanal × frekans × zaman küpü panelini bağla | Eksenler kanal indeksi, frekans bini ve frame sırasıdır; hüzme ya da menzil ekseni kullanılmaz | `F8-064` | `feat(ui): F8-065 3D View sekmesini etkinleştir ve kanal × frekans × zaman küpü panelini bağla` |
| [ ] | `F8-066` | `5.66.0` | 20 dk | Tx darbe paneli: darbe zarflarının üst üste bindirilmesi, anlık frekans eğrisi ve PRI histogramı | Stagger'lı sentetik kayıtta PRI histogramı iki modlu görünür; CW ve LFM anlık frekans eğrileri (düz çizgi ve rampa) görsel olarak ayrışır; kırpılmış darbeler ayrı renkte işaretlenir ve ölçümden dış... | `F8-065` | `feat(ui): F8-066 tx darbe paneli: darbe zarflarının üst üste bindirilmesi, anlık frekans eğrisi ve PRI histogramı` |

##### 8.N — Raporlama ve dışa aktarma

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F8-067` | `5.67.0` | 20 dk | Report sekmesini etkinleştir ve sağlık skor kartını bağla (kanal | durum | tetikleyen metrikler | önerilen... | 3 bozuk kanallı sentetik veride tablo 3 satırı ARIZA/UYARI, kalan 29 satırı OK gösterir; her ARIZA satırı en az iki tetikleyen metrik listeler (tek metrikle ARIZA ilan edilemez) | `F8-066` | `feat(ui): F8-067 report sekmesini etkinleştir ve sağlık skor kartını bağla (kanal | durum | tetikleyen metrikler | önerilen...` |
| [ ] | `F8-068` | `5.68.0` | 20 dk | Sürümlü JSON şeması + CSV sağlık raporu; her alan birim (count/dBFS/rel-dB/örnek/Hz) ve olculen|varsayim|ki... | Şema sürümü alanı vardır ve şemaya uymayan çıktı testte reddedilir; c girilmemişken metre alanları 'kilitli', c girilince 'varsayim', örnek indeksi her zaman 'olculen' etiketlidir; birimsiz hiçbir... | `F8-067` | `feat(report): F8-068 sürümlü JSON şeması + CSV sağlık raporu; her alan birim (count/dBFS/rel-dB/örnek/Hz) ve olculen|varsayim|ki...` |
| [ ] | `F8-069` | `5.69.0` | 20 dk | HDF5/netCDF4 dışa aktarma (ICES SONAR-netCDF4 grup yapısı referans alınır) ve kalite maskesinin veriyle bir... | Dışa aktarılan dosya geri okunduğunda 32x820 complex veri bit-bit aynı; kalite maskesi, calibration status ve ölçülen fs/B alanları korunur; ping_time koordinatı ve kanal başına grup yapısı doğrulanır | `F8-068` | `feat(report): F8-069 hDF5/netCDF4 dışa aktarma (ICES SONAR-netCDF4 grup yapısı referans alınır) ve kalite maskesinin veriyle bir...` |

##### 8.O — Arıza enjeksiyonlu sentetik doğrulama

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F8-070` | `5.70.0` | 20 dk | Mevcut Profil B sentetik üreticisini complex 32x820 Tx/Rx klasör yapısına genişlet (tarih klasörü / Tx-Rx a... | Üretilen kayıt F8-008 dtype/başlık çözücüsünden geçer; ölçülen frame süresi 100,0977 ms ve dosya başına 10 frame çıkar; dosya boyutu int16 I/Q için hesaplanan değere birebir eşittir | `F8-069` | `feat(fixtures): F8-070 mevcut Profil B sentetik üreticisini complex 32x820 Tx/Rx klasör yapısına genişlet (tarih klasörü / Tx-Rx a...` |
| [ ] | `F8-071` | `5.71.0` | 20 dk | On arıza modeli enjeksiyonu (ölü, gürültülü, kazanç sapmalı, faz kaymalı, kırpılmış, DC ofsetli, I/Q denges... | Her model için enjekte edilen parametre ilgili metrikten geri okunur (kazanç -6,0 dB -> -6,0 +-0,3 dB; faz +30,0 derece -> 30,0 +-1,0 derece; I/Q g=1,05/phi=2 derece -> IMRR -30,32 +-0,5 dBc). Şidd... | `F8-070` | `feat(fixtures): F8-071 on arıza modeli enjeksiyonu (ölü, gürültülü, kazanç sapmalı, faz kaymalı, kırpılmış, DC ofsetli, I/Q denges...` |
| [ ] | `F8-072` | `5.72.0` | 20 dk | Zaman ekseni arıza modelleri: frame atlama, timestamp geri sıçraması, 0,8 örnek/frame kayma, PRI jitter ve... | 0,8 örnek/frame kaymada 1 tam örnek 1,25 frame'de, yani 0,125 s'de birikir ve test bu değeri doğrular (1,2 s DEĞİL); timestamp adımı 100,000 ms olan akışta F8-013 -975,6 ppm okur | `F8-071` | `feat(fixtures): F8-072 zaman ekseni arıza modelleri: frame atlama, timestamp geri sıçraması, 0,8 örnek/frame kayma, PRI jitter ve...` |
| [ ] | `F8-073` | `5.73.0` | 20 dk | Eşik kalibrasyon aracı: metrik dağılımını dizi boyunca çizip doğal kümeleri bulan ve eşik öneren yardımcı;... | İki kümeli sentetik dağılımda önerilen eşik iki kümenin arasına düşer; tek kümeli dağılımda 'eşik önerilemez' döner. Tespit/yanlış alarm ölçütü kanal BAŞINA tanımlanır ve 32 kanallı aile-bazlı yanl... | `F8-072` | `feat(analysis): F8-073 eşik kalibrasyon aracı: metrik dağılımını dizi boyunca çizip doğal kümeleri bulan ve eşik öneren yardımcı;...` |

##### 8.P — Belgeleme ve faz kabulü

| Durum | İş ID | Hedef sürüm | Süre | Somut çıktı | Kabul kontrolü | Bağımlılıklar | Commit mesajı |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [ ] | `F8-074` | `5.74.0` | 20 dk | docs/analysis/array-health.md: her metrik için formül, birim, eşik, kaynak veya 'KAYNAK YOK — genel mühendi... | Kaynaksız her eşik açıkça işaretlidir; belgedeki metrik sayısı kod tarafındaki metrik kaydıyla eşleşir (otomatik test); yapılamayanlar bölümündeki her madde 'neden yapılamaz' ve 'yerine ne verilir'... | `F8-073` | `docs(analysis): F8-074 docs/analysis/array-health.md: her metrik için formül, birim, eşik, kaynak veya 'KAYNAK YOK — genel mühendi...` |
| [ ] | `F8-075` | `5.75.0` | 20 dk | docs/notes/open-decisions.md'ye Faz 8 açık kararlarının eklenmesi (mevcut tablo biçimi ve durum kodları kor... | Her yeni satır ID, konu, durum, karar sahibi, engellediği işler ve varsayım sütunlarını doldurur; mevcut D-01..D-14 satırları değişmez; veriden ölçülebilen sorular 'VERİDEN ÖLÇÜLEBİLİR' olarak ayrı... | `F8-074` | `docs(project): F8-075 docs/notes/open-decisions.md'ye Faz 8 açık kararlarının eklenmesi (mevcut tablo biçimi ve durum kodları kor...` |
| [ ] | `F8-076` | `6.0.0` | 20 dk | Faz 8 milestone kabul tutanağı ve etiket | Fazın tüm zorunlu kontrolleri geçer; geometri ve kalibrasyon bağlı ürünler kilitli olarak listelenir ve kilit gerekçeleri yazılıdır; rapor 'gerçek donanım doğrulaması yok — doğrulama yalnız senteti... | `F8-075` | `docs(release): F8-076 faz 8 milestone kabul tutanağı ve etiket` |
### 22.4 Kapsam → iş eşlemesi

Aşağıdaki eşleme kapsamın iş tablolarında kaybolmasını önler. Bir aralık, iki uçtaki işler dahil tablodaki yürütme sırasını kapsar.

| Gereksinim / kaynak bölüm | İlgili işler | Tamamlanma hedefi |
| --- | --- | --- |
| 3.1: Tekli/çoklu dosya açma | `F2-036`, `F3-001`, `F3-005` | v1.0.0 |
| 3.1: Header, sürüm, endian, boyut ve checksum | `F2-001`–`F2-014` | v1.0.0 |
| 3.1: Kanal ağacı, arama ve filtreleme | `F3-009`–`F3-012` | v1.0.0 |
| 3.1: Zaman serisi ve ortak eksende çoklu kanal | `F3-013`, `F3-019`, `F3-032` | v1.0.0 |
| 3.1: Pan, X/Y/XY zoom, autoscale ve cursor | `F3-021`–`F3-026` | v1.0.0 |
| 3.1: Bölge seçimi ve yakınlaşma | `F3-028`, `F3-029` | v1.0.0 |
| 3.1: Temel istatistikler | `F3-037`–`F3-039` | v1.0.0 |
| 3.1: BIT/sistem olay tablosu ve marker | `F3-042`, `F3-045`, `F3-051` | v1.0.0 |
| 3.1: Olaydan zamana gitme | `F3-046` | v1.0.0 |
| 3.1: Playback ve hız kontrolü | `F3-056`–`F3-058` | v1.0.0 |
| 3.1: PNG/SVG ve seçili CSV | `F3-062`–`F3-066` | v1.0.0 |
| 3.1: Panel ve workspace kaydet/aç | `F3-067`–`F3-071` | v1.0.0 |
| 3.1: Koyu tema, durum renkleri ve kısayollar | `F1-029`, `F1-030`, `F3-072`, `F3-073`, `F3-074` | v1.0.0 |
| 3.1 ve 5.1: Mockup yerleşimi ve dokuz ana bölge | `F0-012`, `F1-039`, `F3-079` | v1.0.0 |
| 3.2: FFT, PSD, spektrogram ve waterfall | `F4-039`–`F4-052` | v2.0.0 |
| 3.2: Filtre zinciri ve temel işlemler | `F4-001`–`F4-008`; `F4-015`–`F4-038` | v2.0.0 |
| 3.2: İndeks, lazy loading ve downsampling | `F2-028`–`F2-032`; `F4-053`–`F4-066` | v2.0.0 |
| 3.2: Türetilmiş kanal ve formül editörü | `F4-068`–`F4-073` | v2.0.0 |
| 3.2: Annotation/bookmark | `F4-074`, `F4-075`, `F4-079` | v2.0.0 |
| 3.2: Analiz oturumu save/load | `F4-076`–`F4-078`; `F4-088` | v2.0.0 |
| 3.2: BIT trend ve health dashboard | `F4-080`, `F4-081` | v2.0.0 |
| 3.2: Ayrılabilir grafik ve çoklu monitör | `F4-082`, `F4-083` | v2.0.0 |
| 3.2 ve 5.1: Çalışan mockup analiz panosu | `F4-052`, `F4-089` | v2.0.0 |
| 3.3: UDP/TCP/serial adaptörleri | `F5-001`–`F5-011` | v3.0.0 |
| 3.3: Ring buffer, kayıp ve backpressure | `F5-012`–`F5-016` | v3.0.0 |
| 3.3: Canlı grafik, BIT ve bağlantı durumu | `F5-017`–`F5-024`; `F5-034` | v3.0.0 |
| 3.3: 125 ms Data kaydı ve tekrar okuma | `F5-025`–`F5-035` | v3.0.0 |
| 3.3: Replay ve dayanıklılık | `F5-003`, `F5-004`; `F5-036`–`F5-040` | v3.0.0 |
| 3.4: Windows paketi ve installer | `F6-001`–`F6-012` | v4.0.0 |
| 3.4: Kılavuz, tanılama ve dağıtım kabulü | `F6-019`–`F6-034` | v4.0.0 |
| 5.2–5.4: Favori, drag/drop, Inspector, raw ve undo | `F3-015`, `F3-016`, `F3-017`, `F3-018`; `F3-035`–`F3-041` | v1.0.0 |
| 5.5–5.6: TX, olay filtreleri, Timeline ve zaman gösterimi | `F3-042`–`F3-061` | v1.0.0 |
| 6 ve 16: Erişilebilirlik, renk, DPI, klavye/mouse | `F1-030`, `F0-013`; `F3-072`–`F3-074` | v1.0.0 |
| 7–9: Domain, decoder, calibration ve saat dönüşümü | `F1-011`–`F1-017`; `F2-019`–`F2-027` | v1.0.0 |
| 10: Analiz birimleri ve referans doğrulaması | `F4-005`, `F4-041`, `F4-044`, `F4-047`, `F4-087` | v2.0.0 |
| 11: Performans ölçümü ve native kararı | `F1-041`–`F1-043`; `F4-062`–`F4-067` | v2.0.0 |
| 12: Worker, iptal, eski sonuç ve hata ayrımı | `F3-002`–`F3-006`; `F4-003`, `F4-004` | v1.0.0 / v2.0.0 |
| 14: Ayarlar ve workspace migration | `F1-009`, `F3-008`, `F3-071`, `F4-078`, `F4-083` | v1.0.0 / v2.0.0 |
| 15: Metadata, raw/processed, iptal ve ek çıktılar | `F3-062`–`F3-066`; `F4-084`–`F4-086` | v1.0.0 / v2.0.0 |
| 17 ve 23: Parser, GUI, integration, UAT ve MVP kabulü | `F2-039`, `F2-040`; `F3-075`–`F3-080` | v1.0.0 |
| 18–19: Logging, bütünlük ve tanılama | `F1-010`, `F2-004`, `F2-040`, `F4-072`, `F4-062`, `F6-020` | v1.0.0–v4.0.0 |
| 20–21: Paket, CI, coverage ve artefakt kapıları | `F1-006`; `F6-001`–`F6-018` | v4.0.0 |
| 24–25 ve 28: Riskler, açık kararlar ve ADR'ler | `F0-015`, `F0-016`, `F4-067`, `F6-001` | İlgili fazdan önce |
| 29: Aynı analiz, yeni kaynak ve son ürün başarısı | `F4-088`, `F5-021`, `F6-030`, `F6-031`, `F6-034` | v4.0.0 |

Bölüm 3.5'teki opsiyonel işler (beamforming, cross-analysis, 3D/polar, otomatik rapor, anomali, eklenti ve yetkilendirme) bu zorunlu commit dizisine dahil değildir. Gerekli hale geldiklerinde aynı 15–20 dakika kuralıyla ayrı backlog işleri ve sürüm hedefleri oluşturulur. Mockup'ta görünen Cross Analysis, 3D View ve Report sekmeleri ilgili backlog tamamlanana kadar pasif ve açıklamalıdır.

## 23. MVP “Definition of Done”

MVP tamamlanmış sayılmak için:

- [x] Ana ekran referans mockup'ın dokuz bölgesini, üç sütunlu düzenini ve panel hiyerarşisini karşılıyor.
- [x] Sağ BIT genel özeti alt sistem durumlarıyla tutarlı; gerçek veri ile simülasyon ayırt ediliyor.
- [x] FFT/spektrogram gibi v2 işlevleri MVP'de açıklamalı pasif durumda; tamamlanmamış işlev başarılı sonuç göstermez.
- [x] Desteklenen `.bin` dosyası salt okunur biçimde güvenilir açılıyor.
- [x] Parser sonuçları referans kayıtlarla doğrulanmış.
- [x] Kanal ağacı binlerce öğede kullanılabilir hızda çalışıyor.
- [x] Kullanıcı kanalları grafiğe ekleyip kaldırabiliyor.
- [x] Birden fazla grafik ortak X zaman ekseninde senkronize olabiliyor.
- [x] X, Y ve XY zoom davranışları tutarlı.
- [x] Cursor ve region ölçümleri doğru.
- [x] BIT/event satırından grafikte aynı zamana gidiliyor.
- [x] TX aralıkları ve kritik olaylar grafik üzerinde gösteriliyor.
- [x] Uzun işler UI’ı dondurmuyor ve iptal edilebiliyor.
- [x] PNG ve CSV dışa aktarma metadata ile çalışıyor.
- [x] Workspace kaydet/aç işlevi temel düzeni koruyor.
- [x] Kritik unit/integration/GUI testleri CI’da geçiyor.
- [x] Desteklenen Windows ölçeklemelerinde arayüz bozulmuyor.
- [x] Bilinen kritik hata bulunmuyor; diğer bilinen sorunlar release notes’ta yer alıyor.

## 24. Riskler ve azaltma planı

| Risk | Etki | Azaltma |
| --- | --- | --- |
| `.bin` formatı eksik veya sık değişiyor | Parser tekrar işi | Sürümlü decoder, golden fixtures, format dokümanı |
| Timestamp’ler güvenilir değil | Yanlış korelasyon | Time-base modeli, drift/reset testleri, kalite göstergesi |
| Çok büyük kayıt UI’ı donduruyor | Kullanılamaz ürün | Lazy query, downsampling, worker, bellek bütçesi |
| PyQtGraph özel plot için yetersiz kalıyor | Görsel/analiz kısıtı | Plot abstraction, gerektiğinde OpenGL/Matplotlib/özel widget |
| Thread yarışları eski veriyi gösteriyor | Yanlış analiz | Request versioning, cancellation, immutable sonuçlar |
| Filtre/FFT birimleri yanlış yorumlanıyor | Mühendislik hatası | Açık unit sözleşmesi, sentetik referans testleri |
| Renk yoğunluğu BIT hatalarını gizliyor | Operasyon riski | Severity hiyerarşisi, ikon+metin, kullanıcı testi |
| Native hızlandırma erken karmaşıklık yaratıyor | Teslim gecikmesi | Önce profil, yalnız sıcak noktayı taşıma |
| Canlı akış burst’lerinde veri kaybı | Eksik kayıt | Backpressure politikası, buffer metriği, loss event’i |
| Workspace şeması değişiyor | Eski proje açılamıyor | Versioned schema ve migration testleri |

## 25. Açık kararlar

Geliştirmeye başlamadan önce cevaplanması gerekenler:

- [ ] `.bin` format dokümanı ve örnek dosyalar mevcut mu?  **CEVAP BEKLİYOR** (`D-01`, `D-02`, `docs/notes/open-decisions.md`). Varsayım: Sentetik fixture ile ilerlendi; Bölüm 8.2/8.3 taslağı sözleşme sayıldı.
- [ ] En büyük tipik dosya boyutu ve kayıt süresi nedir?  **CEVAP BEKLİYOR** (`D-03`, `docs/notes/open-decisions.md`). Varsayım: Profil B için 2,59 GiB/saat, 4 saate kadar varsayıldı.
- [ ] Maksimum kanal sayısı ve kanal başına en yüksek sample rate nedir?  **CEVAP BEKLİYOR** (`D-04`, `docs/notes/open-decisions.md`). Varsayım: Profil A 8 sabit kanal; akustik 48 kHz uygulandı (taslaktaki 96 kHz değil).
- [ ] Timestamp tek kaynaktan mı geliyor; cihazlar arasında clock drift var mı?  **CEVAP BEKLİYOR** (`D-09`, `docs/notes/open-decisions.md`). Varsayım: Kanonik `int64` UTC ns; Profil A'da senkron kalitesi `bilinmiyor` gösterilir.
- [ ] BIT sonuçları anlık event mi, periyodik status mü, ikisi birden mi?  **CEVAP BEKLİYOR** (`D-11`, `docs/notes/open-decisions.md`). Varsayım: Profil A'da her kayıtta durum maskesi (periyodik) varsayıldı.
- [ ] Transmisyon verisinin alanları ve START/STOP ilişkilendirmesi nedir?  **CEVAP BEKLİYOR** (`D-08`, `docs/notes/open-decisions.md`). Varsayım: `IDLE→ACTIVE` START, `ACTIVE→IDLE` STOP; sınırlar ±125 ms.
- [ ] Canlı veri hangi protokol ve bant genişliğiyle gelecek?  **CEVAP BEKLİYOR** (`D-12`, `D-13`, `docs/notes/open-decisions.md`). Varsayım: Üç adaptör (UDP/TCP/serial) yazıldı; replay ve simülasyonla doğrulandı.
- [ ] Hedef bilgisayar CPU, RAM, GPU ve monitör çözünürlüğü nedir?  **CEVAP BEKLİYOR** (`D-15`, `docs/notes/open-decisions.md`). Varsayım: Performans bütçeleri geliştirme makinesinde ölçüldü (`K-18`).
- [ ] Uygulamanın offline/air-gapped ortamda çalışması gerekiyor mu?  **CEVAP BEKLİYOR** (`D-16`, `docs/notes/open-decisions.md`). Varsayım: Gerekmediği varsayıldı; yine de offline wheel arşivi üretildi (`F6-011`, `K-17`).
- [ ] Verinin güvenlik sınıfı ve log/export kısıtları var mı?  **CEVAP BEKLİYOR** (`D-18`, `docs/notes/open-decisions.md`). Varsayım: Kısıt yok varsayıldı; log'a yalnız metadata yazılır, ham veri yazılmaz.
- [ ] Birden fazla kayıt zaman hizalı olarak karşılaştırılacak mı?  **CEVAP BEKLİYOR** (`D-22`, `docs/notes/open-decisions.md`). Varsayım: İlk sürümde tek kayıt varsayıldı; çoklu kayıt açılır ama hizalama yoktur (`K-15`).
- [ ] MATLAB’daki hangi analiz/etkileşim davranışları birebir bekleniyor?  **CEVAP BEKLİYOR** (`D-23`, `docs/notes/open-decisions.md`). Varsayım: Özel bir birebir beklenti olmadığı varsayıldı; X/Y/XY ölçekleme MATLAB alışkanlığına göre yapıldı.
- [ ] Rapor çıktısı resmi test kanıtı sayılacak mı?  **CEVAP BEKLİYOR** (`D-24`, `docs/notes/open-decisions.md`). Varsayım: Sayılmayacağı varsayıldı; sayılacaksa imza, sürüm ve izlenebilirlik alanları gerekir.
- [ ] Arayüz yalnız İngilizce mi, Türkçe/İngilizce mi olacak?  **CEVAP BEKLİYOR** (`D-21`, `docs/notes/open-decisions.md`). Varsayım: Arayüz İngilizce, proje belgeleri Türkçe (`K-14`).

## 26. İlk geliştirme sprinti — Bölüm 22 iş referansları

İlk çalışma paketi **12 iş / 210 dakika aktif hedef** içerir. Bu liste işlerin kopyası değildir; çıktı, kabul, bağımlılık ve commit mesajı Bölüm 22'deki aynı kimlikten takip edilir. Amaç, ana mockup'a giden geliştirme başlamadan kayıt sözleşmesini ve ekran referansını netleştirmektir.

| Sıra | İş ID | Hedef sürüm | Süre | Odak |
| --- | --- | --- | --- | --- |
| 1 | `F0-001` | `0.1.0` | 15 dk | Git başlangıcını, ignore kurallarını ve VERSION kaynağını hazırla |
| 2 | `F0-002` | `0.2.0` | 15 dk | Üç kullanıcı rolü için ilk beş senaryoyu yaz |
| 3 | `F0-003` | `0.3.0` | 20 dk | Örnek dosya ve format envanterini çıkar |
| 4 | `F0-004` | `0.4.0` | 15 dk | 32 byte örnek header sözleşmesini çıkar |
| 5 | `F0-005` | `0.5.0` | 20 dk | 64 byte örnek Data kayıt sözleşmesini çıkar |
| 6 | `F0-006` | `0.6.0` | 15 dk | 125 ms periyot ve kayıt adı kurallarını belgeye bağla |
| 7 | `F0-007` | `0.7.0` | 20 dk | Mockup kanal gruplarını örnek veri sözlüğüne eşleştir |
| 8 | `F0-008` | `0.8.0` | 20 dk | CRC destekleyen formatın karar kaydını yaz |
| 9 | `F0-009` | `0.9.0` | 15 dk | Küçük geçerli fixture için beklenen sonuçları yaz |
| 10 | `F0-010` | `0.10.0` | 15 dk | Bozuk fixture senaryolarının sonuçlarını yaz |
| 11 | `F0-011` | `0.11.0` | 20 dk | UTC ve cihaz zamanı dönüşüm kararını yaz |
| 12 | `F0-012` | `0.12.0` | 20 dk | Referans mockup'ın dokuz bölgesini yerleşime eşleştir |

İlk çalışma paketi sonunda: başlangıç sürüm/commit düzeni, örnek header/Data sözleşmesi, 125 ms kayıt beklentileri, hata senaryoları ve referans mockup bölge eşlemesi hazır olmalıdır. Henüz uygulama demosu tamamlanmış sayılmaz.

Devam sırası:

| Çalışma paketi | İş referansları | Beklenen somut sonuç |
| --- | --- | --- |
| Keşif kabulünü kapat | `F0-013`–`F0-017` | Etkileşim, performans, risk ve ADR kayıtları; format milestone'u |
| Mockup uygulama iskeleti | `F1-001`–`F1-044` | Açılan üç sütunlu pano ve sahte zaman serisi; gelişmiş analiz yerleri hazır |
| Kayıtlı veri | `F2-001`–`F2-041` | Gerçek/sentetik BIN decoder, indeks ve repository sorguları |
| İlk dosyadan grafik demosu | `F3-001`–`F3-013` | Dosya açma, kanal ağacı ve çift tıkla gerçek kayıt çizimi |
| Etkileşim ve olay demosu | `F3-014`–`F3-046` | Çoklu kanal, zoom, cursor, ROI ve olaydan zamana gitme |
| MVP kabulüne kalan işler | `F3-047`–`F3-080` | BIT/TX özeti, playback, export, workspace ve mockup yerleşim kabulü |
| Çalışan ana analiz panosu | `F4-001`–`F4-090` | Mockup'taki FFT, spektrogram, filtre ve istatistiklerin birlikte çalışması |

Görsel kabulde referans PNG'nin uygulama penceresi ile aynı boyuttaki uygulama görüntüsü karşılaştırılır. Dokuz bölgenin konumu, merkez/yan panel oranları, sekme sırası, tema, eksen/birimler ve eylemlerin erişilebilirliği kontrol edilir. Gerçek sinyal örneklerinin piksel piksel aynı görünmesi beklenmez; grafik yerleşimi ve veri doğruluğu ayrı kanıtlanır.

Uzun otomatik koşuların başlatılması ve sonuç incelemesi farklı işlerdir. Bu paketlerin takvim süresine otomatik koşu ve dış bağımlılık beklemeleri ayrıca eklenir.

## 27. Önerilen teknoloji seti

| Alan | Başlangıç tercihi | Not |
| --- | --- | --- |
| Dil | Python 3.12+ | Bağımlılık uyumluluğuna göre sabitle |
| GUI | PySide6 | Qt’nin resmi Python binding’i |
| Hızlı plot | PyQtGraph | Canlı/büyük zaman serileri |
| Sayısal işlem | NumPy, SciPy | DSP ve vektör işlemleri |
| Veri modelleri | dataclasses + typing | Gerekirse Pydantic yalnız sınır/config katmanında |
| Test | pytest, pytest-qt | Unit/integration/GUI |
| Kalite | Ruff, Pyright/Mypy | CI kapısı |
| Paketleme | PyInstaller/Nuitka | Spike sonrası seç |
| Büyük tablo | Qt model/view | DataFrame’i doğrudan UI modeli yapma |
| Cache/index | Özel binary/SQLite/Parquet değerlendirmesi | Erişim desenine göre ölçerek seç |
| Native hız | pybind11/Cython/Numba/Rust opsiyonel | Yalnız profiling sonrası |

## 28. Mimari karar kayıtları (ADR)

Aşağıdaki kararlar kısa ADR belgeleriyle kaydedilmelidir:

- ADR-001: PySide6 seçimi.
- ADR-002: PyQtGraph ve plot abstraction sınırı.
- ADR-003: Kanonik timestamp birimi ve time-base modeli (`docs/adr/ADR-003-time-base.md`, `F0-011`).
- ADR-004: Decoder versioning ve format detection.
- ADR-005: Index/cache formatı.
- ADR-006: Thread/process çalışma modeli.
- ADR-007: Downsampling algoritması.
- ADR-008: Workspace JSON şeması ve migration.
- ADR-009: Live-source/backpressure politikası.
- ADR-010: Native hızlandırmaya geçiş ölçütleri (`docs/adr/ADR-010-native-acceleration.md`, `F4-067`).
- ADR-011: CRC destekleyen format sürümü (`docs/adr/ADR-011-crc.md`, `F0-008`).
- ADR-012: Paketleme aracı ve dağıtım biçimi (`docs/adr/ADR-012-packaging.md`, `F6-001`).

ADR'lerin iş, sürüm ve faz eşlemesi: `docs/adr/README.md` (`F0-016`).

Her ADR; bağlam, karar, alternatifler, olumlu/olumsuz sonuçlar ve karar tarihini içermelidir.

## 29. Son başarı ölçütleri

Ürün başarılı sayılmalıysa:

- Kullanıcı anormal bir sensör davranışı ile BIT/TX olayını saniyeler içinde ilişkilendirebilmeli.
- Büyük kayıtlar tam olarak RAM’e alınmadan incelenebilmeli.
- Aynı analiz, kaydedilmiş workspace ve işlem parametreleriyle tekrar üretilebilmeli.
- Yeni `.bin` sürümü veya yeni canlı kaynak GUI kodunu değiştirmeden eklenebilmeli.
- Performans sorunları ölçülebilir bütçeler ve benchmark’larla takip edilmeli.
- Grafik ve analiz sonuçlarının zaman, birim ve işlem geçmişi açık olmalı.
- Uygulama uzun işlemlerde donmamalı, hatalı dosyalarda kontrolsüz kapanmamalı.

---

## Uygulama notu

İlk kodlama adımı bütün ekranları bir kerede tamamlamak olmamalıdır. Önce dikey bir dilim kurulmalıdır: **örnek `.bin` → decoder → normalize kanal/event modeli → repository sorgusu → zaman grafiği → event’e tıklayıp aynı zamana gitme**. Bu akış gerçek veriyle doğrulandıktan sonra FFT, spektrogram, canlı veri ve gelişmiş dashboard katmanları eklenmelidir.
