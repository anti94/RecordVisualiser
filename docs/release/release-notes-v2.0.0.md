# SONAR Veri Analiz Panosu — `v2.0.0` (Çalışan analiz panosu)

**Tarih:** 2026-09-11 · **Milestone:** `ms/05-analysis` · **Kabul tutanağı:**
`docs/release/ms-05-analysis.md`

`v2.0.0`, `v1.0.0`'da yerleşimi hazır ama pasif bırakılan FFT, spektrogram
ve analiz araçları hücrelerini **gerçek hesaplamayla** doldurur. Mockup'ın
merkezindeki zaman serisi, spektrogram, FFT ve istatistik artık birlikte
ve aynı veriden çalışır.

## Öne çıkanlar

- **İşlem zinciri** — sıralı, worker üzerinde çalışan, iptal edilebilir DSP
  adımları: detrend/DC kaldırma, moving average, normalize, pencereli
  RMS/envelope, phase unwrap, resample/decimate; NaN ve kalite bayrağı
  politikası sessizce geçerli değere dönüşmez.
- **Filtreler** — low-pass, high-pass, band-pass, notch; cutoff/order/Q
  sınırları doğrulanır, tasarım genlik yanıtına `atol=1e-12` içinde uyar.
- **FFT, PSD, spektrogram, waterfall** — pencereleme (rectangular/Hann/
  Hamming), tek taraflı FFT, Welch PSD, STFT/spektrogram matrisi, waterfall
  zaman dilimi görünümü; hepsi mockup'ın Spectrum/Spectrogram sekmelerine
  ve orta panele bağlı.
- **125 ms akustik blok (Profil B)** — 48 kHz yüksek örnek hızlı ham
  akustik veri için ayrı format sözleşmesi, decoder ve zaman sorgusu.
- **Büyük veri performansı** — memory mapping, görünür zaman aralığı
  sorgusu, piksel genişliğine göre `max_points`, çok seviyeli özet
  piramidi, bellek sınırlı LRU cache, akışla tam-kapsam indirgeme. 1 GB
  Profil B dosyasında tam kapsam sorgusu 223,9 saniyeden 5,3 saniyeye,
  pan/zoom hazırlığı 0,24 FPS'ten 130+ FPS'e indi (ayrıntı: Bölüm
  "Performans" altında).
- **Türetilmiş kanal ve formül editörü** — sınırlı aritmetik ifadelerle
  (`ch0 - ch1` gibi) yeni kanal tanımlama; annotation/bookmark ekleme.
- **Analiz oturumu** — işlem zinciri, türetilmiş kanallar, annotation ve
  seri stilleri workspace dosyasıyla kaydedilir/açılır; aynı kaynak ve
  parametreler **bit düzeyinde aynı** analiz sonucunu üretir (FFT, PSD,
  STFT, istatistik); taşınmış kaynaklar için yeniden konumlandırma.
- **BIT trend ve health dashboard** — durum süresi ve değişim trendi,
  özet kart ile ayrıntılı görünüm arasında yapısal olarak tutarlı.
- **Çoklu monitör ve ayrılabilir grafik** — grafik penceresi ayrılıp geri
  takılabilir, veri ve X-eksen senkronizasyonu korunur; monitör
  çıkartılınca pencere görünür alana geri gelir.
- **Ek dışa aktarma** — event/BIT metadata JSON, TSV ayırıcı seçenekli
  CSV, statik grafiğin PDF'i (başlık/kaynak/işlem bilgisiyle, vektörel).

## Performans

`plan.md` §11.1'in dört hedefi de gerçek ölçümle geçiyor
(`docs/perf/results/large-file-streaming-verdict.json`):

| Hedef | Ölçülen |
| --- | --- |
| Metadata görünmesi ≤ 5 s | 0,143 ms |
| Viewport sorgusu çoğu durumda ≤ 150 ms | 12/15 (%80) |
| Pan/zoom hazırlığı ≥ 30 FPS | en az 132,77 FPS |
| Bellek dosya boyutuyla doğrusal büyümemeli | bayt başına tepe **düşüyor** (0,48 → 0,08) |

İlk ölçüm (`F4-065`) bu dört hedeften üçünün saptığını bulmuştu; kök
neden (`query_acoustic_channel` her sorguda kanalın tamamını çözüyordu)
ölçülüp `docs/adr/ADR-010-native-acceleration.md` ile kayda geçti ve
algoritmik düzeltmeyle (kayıt indeksi, vektörleştirilmiş özet piramidi,
akışla tam-kapsam indirgeme) kapatıldı. Native hızlandırmaya **geçilmedi**
— ölçülen darboğaz native hız eksikliği değil, sorgunun sınırsız olmasıydı.

## Analiz doğruluğu

FFT, PSD, STFT ve filtreler dört kanonik sinyalle (sinüs, chirp, beyaz
gürültü, impulse) **SciPy kullanmadan** iki bağımsız referansa (NumPy
`rfft` ve kapalı-form analitik değer) karşı doğrulandı: Parseval eşitliği,
Butterworth kesim noktasında tam `1/√2` kazanç, STFT'in chirp anlık
frekansını yarım bin içinde izlemesi dahil (`docs/release/ms-05-analysis.md`
§4).

## Bilinen sınırlamalar

`v2.0.0` **kod-tam çalışan analiz panosu**dur; "gerçek cihazda kabul
edilmiş ürün" değildir. Ayrıntı ve takip: `docs/release/ms-05-analysis.md`
§8.

- **Gerçek Profil B akustik kaydıyla doğrulanmadı.** Tüm decoder ve analiz
  doğrulaması, proje başında yazılan `docs/format/profile-b.md`
  sözleşmesine uyan **sentetik** dosyalarla yapıldı (kısıt D-01).
- **Performans gerçek ekran / hedef donanımda tekrar edilmedi.** Ölçümler
  bir geliştirme iş istasyonunda (16 çekirdek, 32 GiB RAM) alındı; Qt
  paint süresi dahil değil. Hedef ölçüm bilgisayarı hâlâ bilinmiyor
  (E-10).
- **Çoklu monitör gerçek donanımda doğrulanmadı.** `QGuiApplication.screens()`
  API'siyle test edildi; fiziksel çoklu ekran kurulumunda tekrar
  edilmedi.
- **Windows paketlenmiş sürümde davranış ölçülmedi.** Paketleme Faz 6'da
  gelir (`F6-*`).
- `v1.0.0`'ın bilinen sınırlamaları (gerçek Profil A kaydı, gerçek DPI,
  paketlenmiş uygulama) hâlâ geçerlidir — bkz. `release-notes-v1.0.0.md`.

## Sürüm bilgisi

- Etiketler: `v2.0.0` ve `ms/05-analysis` (aynı commit).
- Faz 4: 96 iş (`F4-001`–`F4-096`), `v1.1.0` → `v1.95.0`.
- Test: 3758 test toplandı; tam koşu yeşil, 0 FAILED. `ruff` + `pyright`
  strict temiz (462 dosya).
- Hedef platform: Windows 10/11 64-bit. Python 3.9 (plan 3.12 öngörüyor —
  bkz. `docs/notes/worklog.md` ortam notu).
