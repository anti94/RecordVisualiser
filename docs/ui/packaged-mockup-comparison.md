# Paketli ana ekran ↔ referans mockup karşılaştırması — `F6-031`

Kabul: **Dokuz bölge, hiyerarşi, tema ve çalışan ana analizler kabul
listesini karşılar.**

Karşılaştırma **paketli uygulama üzerinde** yapıldı. Kaynak ağacındaki
testler yerleşimi zaten denetliyor (`F3-079`); buradaki değer, aynı
şeyin **pakette de** doğru olduğunu göstermesidir. Paketlemede kaybolan
bir tema dosyası ya da gelmeyen bir panel yalnız burada görünür.

Araç: `tools/mockup_compare.py` ·
Ölçüm: `docs/ui/results/packaged-layout.json` ·
Sonuç: `docs/ui/results/packaged-mockup-comparison.json`

## 1. Künye

| | |
| --- | --- |
| Çalıştırılan | `dist/sonar-analyzer-3.35.0/sonar-analyzer.exe` |
| Sürüm | `3.35.0` |
| Pencere | 1520 × 1201 mantıksal piksel |
| Madde sayısı | **7** |
| Geçen | **7** |
| Başarısız | **0** |

## 2. Nasıl ölçüldü

Paketli uygulama `--layout-report` ile çalıştırılır. Bu kip ana ekranı
**gerçekten gösterir**, öntanımlı yerleşimi uygular ve sonra ölçer.
Gösterilmemiş bir pencerede dock alanları ve boyutlar henüz yerleşmemiş
olur; ölçülen şey kullanıcının gördüğü ekran olmazdı.

Her bölge, pencerenin **kendi yerleşiminden** bulunur: gerecin ata
zinciri yukarı yürünür ve ilk karşılaşılan dock/araç çubuğu/merkez
konteyneri o bölgenin alanıdır. Bir listeden kopyalanmaz.

## 3. Sonuçlar

| Madde | Kontrol | Sonuç | Ölçüm |
| --- | --- | --- | --- |
| 1.1 | Dokuz bölgenin tamamı görünür ve `layout-map.md` §2'deki alanda | **TAMAM** | 9/9 doğru |
| 1.1h | Hiyerarşi: 1 sol · 3 merkez · 3 sağ · 2 alt | **TAMAM** | `{left: 1, center: 3, right: 3, bottom: 2}` |
| 1.2 | Sol sütun ~200 px, sağ sütun ~300 px | **TAMAM** | sol **200 px**, sağ **319 px** |
| 1.3 | Sekiz sekme, `Time Series` seçili açılır | **TAMAM** | 8 sekme, seçili `Time Series` |
| 1.3b | Çalışmayan görünümler pasif (v2) | **TAMAM** | etkin 5, pasif 3 |
| 1.7 | Koyu tema uygulanmış | **TAMAM** | 3216 karakter stil, arka plan `#0b1118` (aydınlık 18) |
| 3.14 | Ana analiz çalışıyor | **TAMAM** | 8 örnek → 5 noktalı spektrum eğrisi |

### 3.1 Dokuz bölge

| # | Bölge | Nesne | Alan |
| --- | --- | --- | --- |
| 1 | Dosya ve Veri Yönetimi | `dock_data_explorer` | sol |
| 2 | Hızlı Araçlar | `toolbar_quick_tools` | merkez |
| 3 | Görselleştirme Alanı | `center_stack` | merkez |
| 4 | Donanım/BIT Durumu | `card_bit_status` | sağ |
| 5 | Hesaplamalar ve Analiz | `card_analysis_tools` | sağ |
| 6 | Çoklu Görünüm | `view_tab_bar` | merkez |
| 7 | Zaman Kontrolü | `dock_playback` | alt |
| 8 | Log / Mesajlar | `dock_bottom_panel` | alt |
| 9 | Ayarlar ve Dışa Aktarma | `card_data_export` | sağ |

Dokuzunun tamamı bulundu, görünür durumda ve beklenen alanda.

### 3.2 Sütun genişlikleri

Sol sütun **200 px**, sağ sütun **319 px**. `layout-map.md` §1 sol için
200, sağ için 300 px diyor ve sütunları "sabit-esnek" olarak tanımlıyor.

Ölçüt bu yüzden **tam eşitlik değil, toleranslıdır** (sol ±120, sağ
±150). Sabit bir piksele bağlanmak farklı DPI ve pencere boyutlarında
yanlış alarm üretirdi; asıl aranan, mockup'ın üç sütunlu oranının
bozulmamasıdır.

### 3.3 Tema

Stil sayfası **pakete girmiş ve uygulanmış**: 3216 karakter, pencere
arka planı `#0b1118` (aydınlık 18/255). Koyu tema ölçütü, renk adına
değil **ölçülen aydınlığa** bağlıdır — tema dosyası pakete girmezse Qt
varsayılan açık paletiyle açılır ve bu ölçüt düşer.

### 3.4 Çalışan ana analizler

Sekmenin etkin görünmesi, arkasındaki hesabın çalıştığını göstermez.
Bu yüzden ölçüm bir adım daha ileri gider: gerçek bir kayıt
(`valid_8records_v2.bin`) paketli uygulama içinde açılır, bir kanalın
sekiz örneği **üretim spektrum paneline** verilir ve panelin eğri
üretip üretmediğine bakılır.

Sonuç: 8 örnek → **5 noktalı** spektrum eğrisi (tek taraflı FFT'de
beklenen nokta sayısı). Eksen etiketleri kanalın biriminden türüyor:
`Frequency (Hz)` ve `Amplitude (bar)`.

Etkin görünümler: `Time Series`, `Spectrum`, `Spectrogram`,
`Transmission`, `BIT / Status`. Pasif olanlar: `Cross Analysis`,
`3D View`, `Report` — üçü de `v2.0.0 ile kullanilabilir` ipucuyla
işaretli (`K-12`).

## 4. Bu karşılaştırmanın kapsamadıkları

- **Piksel düzeyinde görsel karşılaştırma yapılmaz.** Mockup bir
  tasarım görseli, uygulama ise gerçek bir Qt penceresidir; yazı tipi
  ve platform metrikleri farklıdır. Ölçülen şey yerleşim, hiyerarşi,
  tema ve işlevdir.
- **%150 DPI ölçeklemesi** ayrıca ölçülmedi (kabul listesi 1.9); DPI
  testleri kaynak ağacında yürütülüyor.
- Mockup'taki örnek dosya adları ve ölçüm değerleri **örnektir**;
  uygulama bunları açılan kayıttan alır.

## 5. İlgili belgeler

- Yerleşim eşlemesi: `docs/ui/layout-map.md`
- Kabul listesi: `docs/ui/acceptance-checklist.md`
- Paketli kabul turu: `docs/acceptance/packaged-acceptance.md`
- Bilinen sorunlar: `docs/release/known-issues.md`
