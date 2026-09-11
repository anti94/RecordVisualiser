# Milestone kabul tutanağı — `ms/05-analysis`

- **Faz:** 4 — Mockup analiz panosu ve büyük veri performansı
- **Sürüm:** `v2.0.0`
- **Etiketler:** `v2.0.0` ve `ms/05-analysis` (aynı commit)
- **Tarih:** 2026-09-11
- **Kabul işi:** `F4-090`

## 1. Faz kabul ölçütü

Plan §22.2 (Faz 4): *"Mockup'taki ana analiz panosu gerçek hesaplamalarla
çalışmalı; analiz doğruluğu, oturum ve performans kontrolleri geçmeli."*

`F4-090` kabul kontrolü: *"Mockup analizi, Bölüm 3.2, doğruluk ve performans
koşulları geçer."*

## 2. İşler ve çıktılar (96 iş: `F4-001`–`F4-096`, kabul `F4-090`)

Her iş kendi commit'i ve `vX.Y.0` etiketiyle kapandı: `v1.1.0` (`F4-001`) –
`v1.95.0` (`F4-096`), ardından bu tutanakla `v2.0.0`. Ayrıntı: `plan.md`
Bölüm 22 Faz 4 tablosu ve `docs/notes/worklog.md`.

Ana yetenek blokları:

| Blok | İşler | Çıktı |
| --- | --- | --- |
| İşlem zinciri | `F4-001`–`F4-008` | Sıralı, worker üzerinde çalışan, iptal edilebilir DSP zinciri; NaN/kalite bayrağı politikası; Analysis Tools editörü |
| 125 ms akustik blok (Profil B) | `F4-009`–`F4-014` | 48 kHz blok formatı, fixture üretici, payload decoder, blok-içi zaman, zaman sorgusu, sınır doğrulaması |
| Temel sayısal işlemler | `F4-015`–`F4-026` | Detrend, moving average, normalize, RMS/envelope, phase unwrap, resample/decimate |
| Filtreler | `F4-027`–`F4-038` | Low/high/band-pass, notch; cutoff/order/Q sınırları ve araç kartı bağlantıları |
| FFT, PSD, spektrogram, waterfall | `F4-039`–`F4-052` | Pencereleme, tek taraflı FFT, Welch PSD, STFT/spektrogram, waterfall; hepsi mockup'a bağlı |
| Büyük veri ve kaynak yönetimi | `F4-053`–`F4-067` | mmap, görünür aralık sorgusu, `max_points`, min/max envelope, çok seviyeli özet, LRU cache, benchmark, ADR-010 |
| Türetilmiş kanal ve analiz oturumu | `F4-068`–`F4-083` | Formül editörü, annotation/bookmark, oturum kaydı, kaynak yeniden konumlandırma, undo/redo, BIT trend, ayrılabilir pencere |
| Ek çıktı ve doğrulama | `F4-084`–`F4-089` | JSON/TSV/PDF export, sentetik sinyal referans testleri, kaydet/aç tekrarı, mockup karşılaştırması |
| Profil B sınırlı okuma (ADR-010 düzeltmesi) | `F4-091`–`F4-096` | Kayıt indeksi, sınırlı sorgu, vektörleştirilmiş özet piramidi, akışla tam-kapsam indirgeme, §11.1 yeniden doğrulama |

## 3. §11.1 performans bütçesi — dört hedef de geçti

`F4-065` ilk ölçümde dört hedeften üçünün saptığını buldu. Kök neden
ölçülüp (`docs/adr/ADR-010-native-acceleration.md`) düzeltildi; `F4-096`
aynı üç dosyayı (64 MB/256 MB/1 GB Profil B, seed 20260910) aynı makinede
tekrar ölçtü:

| Hedef | §11.1 | İlk ölçüm (`F4-065`) | Son ölçüm (`F4-096`) |
| --- | --- | --- | --- |
| Metadata görünmesi | ≤ 5 s | geçti (0,148 ms) | **geçti** (0,143 ms) |
| Viewport sorgusu | çoğu durumda ≤ 150 ms | saptı (0/15) | **geçti** (12/15, %80) |
| Pan/zoom FPS | ≥ 30 FPS | saptı (0,24 FPS) | **geçti** (en az 132,77 FPS) |
| Bellek ölçeklenmesi | dosya boyutuyla doğrusal büyümemeli | saptı (5,11 sabit) | **geçti** (0,48 → 0,08, düşüyor) |

Kanıt zinciri: `docs/perf/results/large-file.json` (ilk ölçüm) →
`large-file-indexed.json` (`F4-093`, kayıt indeksi sonrası) →
`large-file-streaming.json` (`F4-096`, özet piramidi + akış indirgeme
sonrası) → `large-file-streaming-verdict.json`. Üçü de depoda tarihsel
karşılaştırma olarak durur; karar makine tarafından üretilir ve
`tests/unit/test_large_file_verdict.py` depodaki kararın depodaki
ölçümden **yeniden üretilebilir** olduğunu üç koşu için de denetler.

ADR-010'un geçiş ölçütü 2'si ("sapma düzeltmeden sonra da vardır")
artık sağlanmıyor; native hızlandırma değerlendirmesi **açılmadı**, ADR
kararı ("native'e geçilmez") doğrulandı.

## 4. Analiz doğruluğu — bağımsız referanslarla

`F4-087`, dört kanonik sinyalin (sinüs, chirp, beyaz gürültü, impulse)
analiz yığınının tamamından geçirilip **SciPy'siz** iki bağımsız referansla
(NumPy `rfft` ve kapalı-form analitik değer) karşılaştırıldığı 41 test:

- Sinüs: genlik spektrumu NumPy referansıyla birebir, tepe tam frekans ve
  genlikte, Parseval eşitliği, Welch PSD integre gücü doğru.
- Beyaz gürültü: PSD tabanı analitik `1/(fs/2)` seviyesinde %10 içinde,
  integre güç dizinin varyansına eşit.
- Impulse: spektrum düzlüğü `2/N`, kaydırma yalnız fazı değiştiriyor.
- Chirp: STFT tepe izi analitik anlık frekansa yarım bin içinde.
- Filtreler: dürtü yanıtı spektrumu tasarım genlik yanıtıyla `atol=1e-12`
  içinde, kesimde kazanç tam `1/√2`, `|H_lp|² + |H_hp|² = 1`.

## 5. Oturum tekrar üretilebilirliği

`F4-088`: işlem zinciri + iki türetilmiş kanal + annotation ile donatılmış
bir oturum kaydedilip yeniden açıldığında FFT (üç pencere fonksiyonu),
Welch PSD, STFT matrisi ve istatistik özeti **bit düzeyinde** (`np.array_equal`)
aynı sonucu veriyor; tur iki kez tekrarlandığında da (kaydet/aç/kaydet/aç)
kararlı. Bu, §29 "Aynı analiz, kaydedilmiş workspace ve işlem parametreleriyle
tekrar üretilebilmeli" hedefinin doğrudan kanıtıdır.

## 6. Çalışan mockup panosu

`F4-089`: kayıt açılıp kanal çizildikten ve analiz koştuktan **sonra** da
mockup'ın dokuz bölgesinin hepsi yerinde ve görünür (bölge tanımı
`tests/gui/test_mvp_mockup_regions.py` ile birebir paylaşılıyor); FFT,
spektrogram, istatistik ve filtre hücreleri gerçek veriden bağımsız
hesaplanan referanslarla eşleşiyor; hiçbir yüzeyde yer tutucu etiketi yok.

## 7. Zorunlu kontroller

| # | Kontrol | Sonuç | Dayanak |
| --- | --- | --- | --- |
| 7.1 | Kod kalitesi: lint, biçim, tip | **GEÇTİ** | `ruff check` temiz, `ruff format --check` temiz (462 dosya), `pyright` strict 0 hata |
| 7.2 | Test paketi | **GEÇTİ** | 3758 test toplandı; tam koşu yeşil (çıkış kodu 0, 0 FAILED) |
| 7.3 | §11.1 performans bütçesi | **GEÇTİ** | Bölüm 3 — dört hedefin dördü de geçti (`F4-096`) |
| 7.4 | Analiz doğruluğu (bağımsız referans) | **GEÇTİ** | Bölüm 4 — `F4-087`, 41 test |
| 7.5 | Oturum tekrar üretilebilirliği | **GEÇTİ** | Bölüm 5 — `F4-088` |
| 7.6 | Mockup'ın çalışan hali | **GEÇTİ** | Bölüm 6 — `F4-089`, 25 test |
| 7.7 | Native hızlandırma kararı belgelendi | **GEÇTİ** | `docs/adr/ADR-010-native-acceleration.md`, `F4-096` ile doğrulandı |
| 7.8 | Her iş kendi commit + `vX.Y.0` etiketi | **GEÇTİ** | `v1.1.0` – `v1.95.0` (95 etiket) + `v2.0.0` |

**Zorunlu kontrollerin tamamı geçti.**

## 8. Gerçek veri ve donanımla doğrulanmayan maddeler

> `ms/04-mvp` §5'teki kural sürüyor: sentetik fixture ile geçen test, gerçek
> donanım doğrulaması değildir. Aşağıdaki maddeler **açık** kalır.

| Konu | Durum | Takip |
| --- | --- | --- |
| Gerçek cihaz kaydıyla Profil B açma ve analiz | **DOĞRULANMADI** | Elde gerçek akustik kayıt yok (D-01); tüm doğrulama Faz 0'da yazılan `docs/format/profile-b.md` sözleşmesine karşı |
| §11.1 performans, gerçek ekran ve hedef donanımda | **OFFSCREEN/BENCHMARK ÖLÇÜLDÜ** | `large-file-streaming.json` bir masaüstü iş istasyonunda (16 çekirdek, 32 GiB RAM); Qt paint süresi `pipeline_fps`'e dahil değil; hedef ölçüm bilgisayarı hâlâ bilinmiyor (E-10) |
| Çoklu monitör (`F4-083`) gerçek çoklu ekranda | **OFFSCREEN** | `QGuiApplication.screens()` API'siyle test edildi; fiziksel çoklu monitör donanımında doğrulanmadı |
| Paketlenmiş uygulamada davranış | **YAPILMADI** | Paketleme Faz 6 (`F6-*`); kabul turu `F6-030` |

## 9. Sonraki faza taşınan açık işler

| Konu | Takip |
| --- | --- |
| Gerçek Profil B kaydıyla format/CRC/kanal kataloğu doğrulaması | E-03, E-04, E-05, E-07 |
| Canlı veri paketleri, bağlantı ve 125 ms Data kaydı | `F5-001`+ |
| Gerçek ekran ve hedef donanımda §11.1 tekrar ölçümü | E-10 çözülünce |
| Windows paketleme ve paketli kabul turu | `F6-*`, `F6-030` |

## 10. Karar

**Milestone `ms/05-analysis` kapatılır; `v2.0.0` etiketlenir.**

Gerekçe: Bölüm 3.2 kapsamının tamamı (işlem zinciri, FFT/PSD/spektrogram/
waterfall, filtreler, türetilmiş kanal, annotation, analiz oturumu,
BIT trend, ayrılabilir pencere) kodda uygulandı; mockup'ın çalışan hali
dokuz bölgeyi korur ve dört analiz yüzeyi bağımsız referanslarla doğrulandı;
oturum tekrar üretilebilirliği bit düzeyinde kanıtlandı; §11.1'in dört
performans hedefinin dördü de gerçek ölçümle geçti — ilk ölçümde saptayan
üç hedef, kök neden ölçülüp (ADR-010) algoritmik düzeltmeyle (kayıt indeksi,
vektörleştirilmiş özet piramidi, akışla tam-kapsam indirgeme) kapatıldı.

Fazın sınırı `ms/04-mvp` ile aynı ilkeyle nettir: doğrulama gerçek cihaz
formatı yerine **kendi yazdığımız sözleşmeye** karşıdır; gerçek Profil B
kaydı ve hedef donanımda ölçüm envanter E-10/D-01 çözülünce tekrarlanacaktır.
Bu maddeler `v2.0.0`'ın "kod-tam çalışan analiz panosu" olduğunu, "gerçek
cihazda kabul edilmiş ürün" olmadığını belirtir ve
`release-notes-v2.0.0.md` bunu kullanıcıya açık yazar.

| | |
| --- | --- |
| Hazırlayan | Geliştirme (otomatik koşu, 2026-09-11) |
| Onay | ☐ Proje sahibi ☐ Test mühendisliği |
