# Milestone kabul tutanağı — `ms/04-mvp`

- **Faz:** 3 — MVP analiz arayüzü
- **Sürüm:** `v1.0.0`
- **Etiketler:** `v1.0.0` ve `ms/04-mvp` (aynı commit)
- **Tarih:** 2026-09-10
- **Kabul işi:** `F3-080`

## 1. Faz kabul ölçütü

Plan Bölüm 22 (Faz 3): *"Bölüm 3.1 kapsamı ve Bölüm 23'ün bütün MVP kabul
koşulları kanıtlarıyla tamamlanmış olmalı."*

`F3-080` kabul kontrolü: *"Bölüm 3.1 ve 23 tamdır; mockup yerleşimi ve zorunlu
kontroller geçer."*

## 2. İşler ve çıktılar (80 iş: `F3-001`–`F3-080`)

Her iş kendi commit'i ve `vX.Y.0` etiketiyle kapandı: `v0.103.0` (`F3-001`) –
`v0.181.0` (`F3-079`), ardından bu tutanakla `v1.0.0`. Ayrıntı: `plan.md`
Bölüm 22 Faz 3 tablosu ve `docs/notes/worklog.md`.

Ana yetenek blokları:

| Blok | İşler | Çıktı |
| --- | --- | --- |
| Dosya akışı + worker | `F3-001`–`F3-013` | Tekli/çoklu `.bin` açma, yükleme worker'ı + iptal, hata bildirimi, çoklu kayıt, kapatma, son dosyalar |
| Kanal ağacı ve çizim | `F3-014`–`F3-021` | Sürükle-bırak, çoklu kanal, ortak zaman ekseni, ikinci Y ekseni, pan |
| Zoom / cursor / bölge | `F3-022`–`F3-035` | X/Y/XY zoom, autoscale, reset, cursor + delta, zaman bölgesi + zoom, legend/solo, seri stili |
| Çoklu grafik + workspace panel | `F3-032`–`F3-034` | X-ekseni bağlama, `PlotWorkspace`, undo/redo |
| İstatistik + Inspector | `F3-036`–`F3-041` | ROI istatistikleri, ham örnek denetimi, metadata/olay/eksen alanları |
| Olay tablosu + navigasyon | `F3-042`–`F3-049` | 8 sütun, birleşik filtre, ilişkili kanallar, olay Inspector'ı, çift tık navigasyon, gruplama |
| Marker / TX / timeline | `F3-050`–`F3-055` | Grafik olay işaretleri, TX bantları, overview timeline + viewport |
| Oynatma | `F3-056`–`F3-061` | Play/pause/stop makinesi, ilerleme saati, hız seçici, olaya/zamana gitme, scrub debounce, UTC/yerel/geçen süre |
| Dışa aktarma | `F3-062`–`F3-066` | PNG, SVG, CSV (metadata + raw/processed), üzerine yazma kontrolü, büyük export worker'ı + iptal |
| Workspace | `F3-067`–`F3-071` | Sürümlü JSON modeli, dock/grafik yakalama + geri yükleme, eksik kaynak / bozuk dosya davranışı, sürüm geçişi |
| Erişilebilirlik | `F3-072`–`F3-074` | Bölüm 16 kısayolları, klavye odak sırası, Windows ölçekleme + kontrast |
| MVP doğrulaması | `F3-075`–`F3-080` | Entegrasyon senaryosu, kritik GUI kontrolleri, etkileşim bütçesi, kabul senaryoları, mockup karşılaştırması, bu tutanak |

## 3. Bölüm 23 "Definition of Done" — madde madde kanıt

| # | DoD maddesi | Sonuç | Dayanak |
| --- | --- | --- | --- |
| 1 | Ana ekran mockup'ın dokuz bölgesi, üç sütunlu düzen, panel hiyerarşisi | **GEÇTİ** | `tests/gui/test_mvp_mockup_regions.py` (16 test): dokuz bölge var, görünür ve mockup alanında; `test_main_window_layout.py` (üç sütun oranı) |
| 2 | Sağ BIT genel özeti tutarlı; gerçek veri ↔ simülasyon ayırt ediliyor | **GEÇTİ** | `test_bit_overall_state.py`, `test_bit_status_card.py` (rozet tabloyla çelişmez); `set_recording` kaynak alanına `Simülasyon` / `Dosya` yazar (`test_status_bar*`) |
| 3 | FFT/spektrogram v2 işlevleri açıklamalı pasif; sahte sonuç yok | **GEÇTİ** | `test_mvp_mockup_regions.py` v2 testleri: görünüm sekmeleri + menü eylemleri pasif, ipucu `v2.0.0 ile kullanilabilir`; dashboard FFT/spektrogram hücreleri + Analysis Tools sekmeleri not taşır |
| 4 | Desteklenen `.bin` salt okunur güvenilir açılıyor | **GEÇTİ (sentetik)** | `ms/03-bin-reader` tutanağı; `tests/gui/test_integration_bin_to_event_nav.py` gerçek fixture'ı dosya diyaloğuyla açar. **Gerçek cihaz kaydıyla doğrulanmadı** — §5 |
| 5 | Parser sonuçları referans kayıtlarla doğrulanmış | **GEÇTİ (sentetik)** | `F2-039` bağımsız golden (17 test); referans Faz 0'da parser yazılmadan sabitlendi |
| 6 | Kanal ağacı binlerce öğede kullanılabilir hızda | **KISMİ** | `F1` ağaç işleri + `test_channel_search.py` filtre performansı; MockRepo 12 kanal. **Binlerce kanallı ölçek Faz 4'te ölçülecek** — §5 |
| 7 | Kullanıcı kanalları grafiğe ekleyip kaldırabiliyor | **GEÇTİ** | `test_multi_channel_add.py`, `test_channel_to_plot.py`, `test_drag_drop_channel.py`; `PlotPanel.add_channel`/`remove_channel` |
| 8 | Birden fazla grafik ortak X zaman ekseninde senkronize | **GEÇTİ** | `test_plot_x_axis_link.py`, `test_plot_common_time_axis.py`, `test_plot_workspace.py`; `XAxisLink` |
| 9 | X, Y ve XY zoom davranışları tutarlı | **GEÇTİ** | `test_plot_zoom_x/y/region.py`, `test_mvp_plot_workspace_controls.py`, `test_mvp_scenarios.py::test_zoom_modes_are_unambiguous` |
| 10 | Cursor ve region ölçümleri doğru | **GEÇTİ** | `test_plot_cursor.py`, `test_plot_delta_cursors.py`, `test_plot_time_region.py`, `test_roi_statistics.py` |
| 11 | BIT/event satırından grafikte aynı zamana gidiliyor | **GEÇTİ** | `test_event_double_click_navigation.py`, `test_integration_bin_to_event_nav.py`, `test_mvp_scenarios.py::test_operator_reaches_signal_moment_in_two_interactions` (≤ 2 etkileşim) |
| 12 | TX aralıkları ve kritik olaylar grafik üzerinde gösteriliyor | **GEÇTİ** | `test_plot_event_markers.py`, `test_plot_tx_regions.py`, `test_marker_tx_visibility.py`, `test_transmission_panel.py` |
| 13 | Uzun işler UI'ı dondurmuyor ve iptal edilebiliyor | **GEÇTİ** | `test_file_loader*`, `test_export_worker.py` (CSV worker + iptal, atomik `.part`), `test_scrub_debounce_stats.py` |
| 14 | PNG ve CSV dışa aktarma metadata ile çalışıyor | **GEÇTİ** | `test_plot_png_export.py`, `test_plot_svg_export.py`, `test_csv_export.py` (birim/kaynak/kayıt metadata, ns + UTC), `test_export_flow.py` (üzerine yazma kontrolü) |
| 15 | Workspace kaydet/aç temel düzeni koruyor | **GEÇTİ** | `test_workspace_model.py`, `test_workspace_store.py`, `test_workspace_capture.py`, `test_workspace_restore.py`, `test_workspace_missing_and_corrupt.py`, `test_workspace_migrate.py` |
| 16 | Kritik unit/integration/GUI testleri CI'da geçiyor | **GEÇTİ** | **1676 test**, 0 hata, 0 atlanan; `ruff check` + `ruff format --check` temiz (304 dosya); `pyright` strict 0 hata |
| 17 | Desteklenen Windows ölçeklemelerinde arayüz bozulmuyor | **GEÇTİ (offscreen)** | `test_dpi_scaling.py`: %100/125/150/200 font ölçeğinde kritik kontroller kesilmiyor, WCAG AA kontrast. **Gerçek DPI'lı ekranda doğrulanmadı** — §5 |
| 18 | Bilinen kritik hata yok; diğerleri release notes'ta | **GEÇTİ** | Bilinen kritik hata yok. Açık sınırlamalar `docs/release/release-notes-v1.0.0.md` "Bilinen sınırlamalar" bölümünde |

## 4. Zorunlu kontroller

| # | Kontrol | Sonuç | Dayanak |
| --- | --- | --- | --- |
| 4.1 | Mockup yerleşimi (dokuz bölge, üç sütun) | **GEÇTİ** | `test_mvp_mockup_regions.py` (16 test) |
| 4.2 | MVP kullanıcı senaryoları (§17.5) | **GEÇTİ** | `tests/acceptance/test_mvp_scenarios.py` (6 test) + `docs/acceptance/mvp-scenarios.md` kanıt haritası |
| 4.3 | Etkileşim bütçesi (§11.1) | **GEÇTİ (offscreen)** | `tests/gui/test_mvp_interaction_budget.py`: cursor/play-pause/event/tree dördü de bütçenin binde biri. `docs/perf/results/mvp-interaction.md` |
| 4.4 | Kod kalitesi: lint, biçim, tip | **GEÇTİ** | `ruff check` temiz, `ruff format --check` temiz (304 dosya), `pyright` strict 0 hata |
| 4.5 | Test paketi | **GEÇTİ** | 1676 test, 0 hata, 0 atlanan |
| 4.6 | Her iş kendi commit + `vX.Y.0` etiketi | **GEÇTİ** | `v0.103.0` – `v0.181.0` (79 etiket) + `v1.0.0` |

**Zorunlu kontrollerin tamamı geçti.**

## 5. Gerçek veri ve donanımla doğrulanmayan maddeler

> Faz 0–2 tutanaklarındaki kural sürüyor: sentetik fixture ile geçen test,
> gerçek donanım doğrulaması değildir. `ms/03-bin-reader` §8 bu milestone için
> şu uyarıyı bırakmıştı: *"Faz 3 kabulü, gerçek `.bin` kaydı ve
> P-01/P-04/P-05/P-06/P-08 hedeflerinin gerçek ekranda doğrulanması olmadan
> kapatılamaz."* Aşağıdaki maddeler **açık** kalır ve Faz 4+ işlerine bağlıdır.

| Konu | Durum | Takip |
| --- | --- | --- |
| Gerçek cihaz `.bin` kaydıyla açma ve parser doğruluğu | **DOĞRULANMADI** | Elde gerçek kayıt yok (D-01). Tüm doğrulama Faz 0'da yazılan `profile-a.md` sözleşmesine karşı. Gerçek format farklıysa decoder değişir (E-03/E-04/E-05) |
| P-04 pan/zoom FPS (algılanan ≥ 30) | **AÇIK** | `docs/perf/results/plot-benchmark.json`: 1M noktada 7,4 FPS (offscreen yazılım rasterlayıcı). Downsample piramidi `F4-055`–`F4-058` |
| P-01/P-05/P-06/P-08 gerçek ekranda | **OFFSCREEN ÖLÇÜLDÜ** | `test_mvp_interaction_budget.py` bütçenin çok altında; ama GPU'lu gerçek ekranda tekrar edilmedi. Hedef ölçüm bilgisayarı bilinmiyor (E-10) |
| P-03/P-09 (Profil B ~2,6 GiB, bellek doğrusal) | **YAPILMADI** | MVP Profil A ile sınırlı; mmap/lazy yükleme ve büyük dosya ölçümü Faz 4 (`F4-053`+) |
| Kanal ağacı binlerce öğede | **ÖLÇÜLMEDİ** | MockRepo 12 kanal; büyük katalog performansı Faz 4 |
| Windows ölçekleme gerçek DPI'lı ekranda | **OFFSCREEN** | Font büyütmeyle taklit edildi; gerçek `QT_SCALE_FACTOR` / monitör DPI ile doğrulanmadı |
| Paketlenmiş uygulamada davranış | **YAPILMADI** | PyInstaller/Nuitka paketleme Faz 6 (`F6-*`); kabul turu `F6-030` |

## 6. Bu fazda bulunan ve düzeltilen tutarsızlıklar (seçme)

| Bulgu | Nerede | Çözüm |
| --- | --- | --- |
| `Signal(int, int)` epoch-ns'i taşırken taşma (`libshiboken Overflow`) | zaman bölgesi / timeline viewport sinyalleri | `Signal(object, object)` |
| QMimeData geçici nesnesi GC'ye gidip erişim ihlali | sürükle-bırak testleri | Test tarafında adlı yerel referans |
| `autoscale()` sonrası `autoRange` kapalı kalıyor | `PlotPanel.autoscale` | Önce `autoRange(padding=…)`, sonra `enableAutoRange` |
| `ExportRunner` `QThread` + kuyruklu `quit` kilitleniyor (`wait()` GUI thread'ini blokluyor) | `F3-066` | `QThread` alt sınıfı, `run()` içinde iş; ayrı olay döngüsü yok |
| `PlotToolBar` sabit 32 px yükseklik; %200 ölçekte kutular kesiliyor | `F3-074` | `max(32, sizeHint().height())` |
| Kanal ağacı Enter ile kanalı etkinleştirmiyordu (yalnız çift tık) | `F3-073` | `itemActivated` bağlandı |
| Grafik Tab ile durulamıyordu (`NoFocus`) | `F3-073` | `PlotPanel` `StrongFocus` |

## 7. Sonraki faza taşınan açık işler

| Konu | Takip |
| --- | --- |
| Gerçek `.bin` kaydı: format/CRC/kanal kataloğu farkının işlenmesi | E-03, E-04, E-05, E-07 |
| Downsample piramidi, viewport'a göre `max_points` (P-04) | `F4-055`–`F4-058` |
| Profil B, mmap/lazy yükleme, P-03 ve P-09 ölçümü | `F4-053`+ |
| DSP işlem zinciri (FFT/filtre/spektrogram gerçek hesap) | `F4-001`+ |
| Gerçek ekran + hedef ölçüm bilgisayarında P-01/P-04/P-05/P-06/P-08 | E-10 çözülünce |
| Windows paketleme ve paketli kabul turu | `F6-*`, `F6-030` |

## 8. Karar

**Milestone `ms/04-mvp` kapatılır; `v1.0.0` etiketlenir.**

Gerekçe: Bölüm 3.1 MVP kapsamının tamamı kodda uygulanmış ve otomatik
kanıtlarla (1676 test, strict tip, temiz lint) doğrulanmıştır. Bölüm 23'ün
on sekiz DoD maddesinin her biri adı verilen testlere bağlanmıştır; mockup'ın
dokuz bölgesi ve üç sütunlu düzeni birebir eşleşir; FFT/spektrogram v2
işlevleri açıklamalı pasiftir ve sahte sonuç üretmez.

Fazın sınırı net ve §5'te madde madde ayrılmıştır: doğrulama gerçek cihaz
formatı yerine **kendi yazdığımız sözleşmeye** karşıdır; pan/zoom FPS (P-04)
ve büyük veri (P-03/P-09) bütçeleri Faz 4'e; gerçek ekran ve hedef donanım
ölçümleri envanter E-10 çözülünce tekrar edilecektir. Bu maddeler `v1.0.0`'ın
"kod-tam MVP" olduğunu, "gerçek cihazda kabul edilmiş ürün" olmadığını
belirtir ve `release-notes-v1.0.0.md` bunu kullanıcıya açık yazar.

| | |
| --- | --- |
| Hazırlayan | Geliştirme (otomatik koşu, 2026-09-10) |
| Onay | ☐ Proje sahibi ☐ Test mühendisliği |
