# SONAR Veri Analiz Panosu — `v1.0.0` (MVP)

**Tarih:** 2026-09-10 · **Milestone:** `ms/04-mvp` · **Kabul tutanağı:**
`docs/release/ms-04-mvp.md`

`v1.0.0`, referans mockup'taki masaüstü analiz panosunun **kod-tam MVP**
sürümüdür: kayıtlı `.bin` veriyi açma, çizme, olaylarla ilişkilendirme,
oynatma ve dışa aktarma akışlarının tamamı çalışır durumdadır.

## Öne çıkanlar

- **Dosya akışı** — bir veya birden fazla `.bin` kaydını arka planda (UI
  donmadan, iptal edilebilir) açma; çoklu kayıt, kapatma, son dosyalar.
- **Kanal ağacı** — arama/filtreleme, sürükle-bırak veya Enter ile çizim.
- **Grafik** — ortak zaman ekseninde çoklu kanal, ikinci Y ekseni, pan,
  X/Y/XY zoom, autoscale, reset, cursor + delta, zaman bölgesi (ROI) ve
  bölgeye yakınlaşma, legend/solo, seri stili, X-ekseni bağlama.
- **Analiz** — seçili aralık için mean/std/RMS/min/max/peak-peak; ham
  örnek denetimi (Inspector).
- **Olaylar** — 8 sütunlu tablo, birleşik filtre (zaman + severity +
  kaynak + metin), tekrar gruplama, grafikte zaman işaretleri ve TX
  bantları, satırdan grafiğe navigasyon (≤ 2 etkileşim).
- **Zaman kontrolü** — play/pause/stop, 0.25x–10x hız, olaya/zamana
  gitme, overview timeline + viewport; UTC / yerel / geçen süre.
- **Dışa aktarma** — grafiği PNG veya SVG (vektörel); seçili kanal/aralığı
  CSV (birim + kaynak + kayıt metadata, ns + UTC zaman; raw/processed).
  Var olan dosya onaysız değişmez; büyük CSV worker'da, iptal yarım dosya
  bırakmaz.
- **Workspace** — açık kayıtlar, paneller, eksen aralıkları, görünüm ve
  filtre durumu sürümlü JSON olarak kaydedilir ve geri yüklenir; eksik
  kaynak bildirilir, bozuk dosya açık oturumu bozmaz, eski sürüm
  dönüştürülür.
- **Erişilebilirlik** — Bölüm 16 klavye kısayolları (Ctrl+O/S, Space,
  Home, X/Y/B, C, R, F4); yalnız klavyeyle tamamlanabilen ana akış;
  %100–200 Windows font ölçeğinde kesilmeyen kontroller; WCAG AA
  kontrast.

## v2.0.0'a bırakılan işlevler

Mockup'taki **FFT**, **spektrogram** ve **analiz araçları** (Filter / FFT /
Statistics / Custom) hücrelerinin yerleşimi hazırdır ancak hesaplama
yapmazlar: pasif ve `v2.0.0 ile kullanilabilir` açıklamalıdırlar. İşlevi
olmayan hiçbir alan gerçek analiz izlenimi veren sahte sonuç göstermez.
Spectrum / Spectrogram / Cross Analysis / 3D View / Report görünüm
sekmeleri de aynı şekilde pasiftir.

## Bilinen sınırlamalar

`v1.0.0` **kod-tam MVP**'dir; "gerçek cihazda kabul edilmiş ürün" değildir.
Ayrıntı ve takip: `docs/release/ms-04-mvp.md` §5.

- **Gerçek cihaz `.bin` kaydıyla doğrulanmadı.** Tüm parser ve veri
  doğrulaması, proje başında yazılan `docs/format/profile-a.md`
  sözleşmesine uyan **sentetik** dosyalarla yapıldı (kısıt D-01). Gerçek
  format farklı çıkarsa decoder değişir.
- **Büyük dosya (Profil B, ~2,6 GiB / 96 kHz) desteklenmez.** MVP Profil
  A ile sınırlıdır; memory-mapping, lazy yükleme ve büyük kayıtta
  metadata/bellek bütçeleri (P-03, P-09) Faz 4'te gelir.
- **Pan/zoom kare hızı (P-04) hedefin altında.** 1M noktalık seride
  offscreen ölçümde ~7 FPS; downsample piramidi (`F4-055`+) ile
  çözülecek. Küçük Profil A kayıtlarında sorun gözlenmez.
- **Performans gerçek ekran / hedef donanımda tekrar edilmedi.** Etkileşim
  bütçesi ölçümleri Qt offscreen yazılım rasterlayıcısında alındı ve
  bütçenin çok altında; GPU hızlandırmalı gerçek bir ekranda tekrar
  edilecektir (hedef ölçüm bilgisayarı bilinmiyor, E-10).
- **Kanal ağacı binlerce kanalla ölçeklenmedi.** Simülasyon 12 kanal
  üretir; büyük katalog performansı Faz 4'te ölçülecek.
- **Windows ölçekleme gerçek DPI ile doğrulanmadı.** Font büyütmeyle
  taklit edildi.
- Geliştirme **simülatörü** kullanıldığında veri kaynağı arayüzde açıkça
  `Simülasyon` olarak görünür.

## Sürüm bilgisi

- Etiketler: `v1.0.0` ve `ms/04-mvp` (aynı commit).
- Faz 3: 80 iş (`F3-001`–`F3-080`), `v0.103.0` → `v1.0.0`.
- Test: 1676 geçti, 0 hata, 0 atlanan. `ruff` + `pyright` strict temiz.
- Hedef platform: Windows 10/11 64-bit. Python 3.9 (plan 3.12 öngörüyor —
  bkz. `docs/notes/worklog.md` ortam notu).
