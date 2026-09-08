# Referans mockup — dokuz bölgenin yerleşim eşlemesi

> `F0-012` çıktısıdır. Kaynak: `SONAR Veri Analiz Panosu Mockup’ı.png` (görsel kabul kaynağı),
> plan Bölüm 5.1. Bu belge, görseldeki bölgeleri **somut pencere yerleşimine** çevirir:
> hangi bölge hangi konteynerde, hangi öntanımlı boyutta ve pencere daraldığında ne yapıyor.
>
> Görselin dışındaki numaralı kutular dokümantasyon katmanıdır, uygulamada yer almaz.
> Görseldeki dosya adı, süre, kanal sayısı ve ölçüm değerleri örnektir; uygulama bunları açılan
> kayıttan alır.

## 1. Pencere iskeleti

Başlangıç penceresi yaklaşık **1520 × 840** mantıksal piksel.

```text
┌───────────────────────────────────────────────────────────────────────────────────┐
│ Başlık çubuğu: "SONAR Data Analyzer" · File View Tools Help ····· ⚙ – □ ×          │
├──────────────┬──────────────────────────────────────────────────┬─────────────────┤
│              │ [6] Sekme çubuğu: Time Series · Spectrum · …     │ [4] BIT /       │
│  [1] Dosya   ├──────────────────────────────────────────────────┤     System      │
│      ve Veri │ [2] Hızlı araçlar  ····  [1 s ▾] [Kanal ▾] ☑Sync │     Status      │
│      Yönetimi├──────────────────────────────────────────────────┤                 │
│              │ [3] Zaman serisi                                 ├─────────────────┤
│  Open .bin   │                                                  │ [5] Analysis    │
│  Dosya özeti ├──────────────────────────────────────────────────┤     Tools       │
│  Channels /  │ [3] Spektrogram                    (+ renk skalası)                │
│  Data Tree   │                                                  ├─────────────────┤
│  Arama       ├─────────────────────────┬────────────────────────┤ [9] Data        │
│  Kanal ağacı │ [3] FFT                 │ [3] İstatistik kartı   │     Export      │
│              │                         │                        │                 │
│              ├─────────────────────────┴────────────────────────┤                 │
│              │ [7] Playback / Time Control                      │                 │
│              ├──────────────────────────────────────────────────┤                 │
│              │ [8] Log / Messages                               │                 │
├──────────────┴──────────────────────────────────────────────────┴─────────────────┤
│ Durum çubuğu: Ready ······················ Memory: 1.2 / 8.0 GB ▓▓▓░░              │
└───────────────────────────────────────────────────────────────────────────────────┘
   200 px sabit-esnek         kalan alan (esner)              300 px sabit-esnek
```

## 2. Dokuz bölge → konteyner eşlemesi

| # | Mockup bölgesi | Görseldeki içerik | Konteyner | Alan | Öntanımlı boyut |
| --- | --- | --- | --- | --- | --- |
| 1 | Dosya ve Veri Yönetimi | `Open .bin File` düğmesi; File / Size / Start / Duration / Platform; `Channels` + `Data Tree` sekmeleri; arama kutusu; onay kutulu kanal ağacı | `DataExplorerDock` | Sol dock | 200 px genişlik |
| 2 | Hızlı Araçlar | Araç düğmeleri (pan, zoom, cursor, ölçüm, seçim, sığdır); zaman penceresi `1 s`; kanal seçici `Acceleration (XYZ)`; `Sync` onay kutusu | `PlotToolBar` | Merkez üstü, sekme çubuğunun altı | 32 px yükseklik |
| 3 | Görselleştirme Alanı | Üstte zaman serisi, ortada spektrogram, altta solda FFT ve sağda istatistik kartı | `PlotWorkspace` (dikey `QSplitter`, alt satır yatay `QSplitter`) | Merkez | Oran 34 / 33 / 33 |
| 4 | Donanım/BIT Durumu | `All Systems Nominal` rozeti; `Run BIT Analysis`; `Last Update`; alt sistem/durum tablosu | `BitStatusDock` | Sağ dock, üst | 300 px genişlik |
| 5 | Hesaplamalar ve Analiz | `Filter` / `FFT` / `Statistics` / `Custom` sekmeleri; parametre alanları; `Apply Filter` | `AnalysisToolsDock` | Sağ dock, orta | Aynı sütun |
| 6 | Çoklu Görünüm | `Time Series`, `Spectrum`, `Spectrogram`, `Cross Analysis`, `BIT / Status`, `Transmission`, `3D View`, `Report` | `ViewTabBar` | Merkezin en üstü | 8 sekme |
| 7 | Zaman Kontrolü | Başa sar / oynat / döngü / ileri / sona; slider; `00:00:00 / 01:24:36`; `Start` `End` `[s]`; `Go` | `PlaybackDock` | Alt dock, üst | 56 px yükseklik |
| 8 | Log / Mesajlar | Zaman damgalı satırlar (`[15:30:12] File loaded: …`) | `LogDock` | Alt dock, alt | 96 px yükseklik |
| 9 | Ayarlar ve Dışa Aktarma | `Export Format` (CSV); `Export selected time range`; `Include metadata`; `Export Data`. Ayarlar dişlisi başlık çubuğunda | `DataExportDock` + başlık çubuğu eylemi | Sağ dock, alt | Aynı sütun |

Kabul maddesinin dört köşesi: **sol veri (1)** · **merkez grafikler (2, 3, 6)** ·
**sağ BIT/analiz/export (4, 5, 9)** · **alt playback/log (7, 8)**.

## 3. Merkez alanın iç yerleşimi

```text
ViewTabBar          Time Series | Spectrum | Spectrogram | Cross Analysis |
                    BIT / Status | Transmission | 3D View | Report
PlotToolBar         [araçlar…]            [1 s ▾]  [Acceleration (XYZ) ▾]  ☑ Sync
────────────────────────────────────────────────────────────────────────────
PlotWorkspace (QSplitter, dikey)
  ├─ Satır 1  Zaman serisi      "Acceleration (XYZ)", eksen: Time [s] / Acceleration [g]
  │                             X/Y/Z için mavi / turuncu / yeşil, sağ üstte legend
  ├─ Satır 2  Spektrogram       "Spectrogram - Hydrophone 1", eksen: Time [s] / Frequency [kHz]
  │                             sağda dikey renk skalası, etiket "PSD [dB]"
  └─ Satır 3  (QSplitter, yatay)
       ├─ Sol   FFT             "FFT - Selected Window", log eksen: Magnitude / Frequency [kHz]
       └─ Sağ   İstatistik kartı "Statistics (Acceleration X)":
                                Mean · Std · RMS · Min · Max · Peak-Peak (6 satır, birimli)
```

- Her grafik kartı başlık, kanal adı ve birim gösterir.
- `Sync` işaretliyken zaman ekseni olan tüm kartlar aynı aralığı gösterir; FFT ve istatistik
  seçili zaman penceresini kullanır.
- Zaman penceresi seçici (`1 s`) FFT/istatistiğin çalıştığı pencere uzunluğudur.

## 4. Sağ sütun kartları

| Kart | Alt öğeler | Not |
| --- | --- | --- |
| `BIT / System Status` | Genel durum rozeti; `Run BIT Analysis`; `Last Update: 15:32:10`; `Subsystem` / `Status` tablosu | Rozet ile tablo **çelişemez**: tabloda Warning/FAIL varsa rozet `All Systems Nominal` olamaz |
| `Analysis Tools` | `Filter` (Filter Type, Cutoff Frequency (Hz), Order, `Apply to selected channel`, `Show filtered data`, `Apply Filter`), `FFT`, `Statistics`, `Custom` | MVP'de hesaplanmayan sekmeler pasif ve `v2.0.0 ile kullanılabilir` açıklamalı |
| `Data Export` | `Export Format` (CSV), `Export selected time range`, `Include metadata`, `Export Data` | Dışa aktarma seçili aralığı ve metadata'yı kapsar |

Mockup'taki BIT tablosu **sekiz** alt sistem gösterir: Power Supply, Communication,
Navigation (INS/GPS), Sonar Transceiver, Hydrophones, Thrusters / Transmission,
Thermal Management, Storage. Görselde `Thrusters / Transmission` satırı `Warning`, diğerleri `OK`.

## 5. Alt bölge

| Öğe | İçerik |
| --- | --- |
| `Playback / Time Control` | Başa sar · oynat · döngü · ileri sar · sona git; zaman slider'ı; `geçen / toplam` (`00:00:00 / 01:24:36`); `Start` ve `End` sayısal alanları, birim `[s]`, `Go` |
| `Log / Messages` | Zaman damgalı satırlar; görselde: dosya yüklendi, ayrıştırılıyor, veri hazır (kanal sayısıyla), FFT tamamlandı |

Olayların ayrıntılı tablosu Log değil, ayrı `Events` sekmesidir (plan Bölüm 5.5).

## 6. Durum çubuğu

| Konum | İçerik |
| --- | --- |
| Sol | İşlem durumu — `Ready`, `Parsing…`, `Indexing…` |
| Sağ | Bellek kullanımı: `Memory: 1.2 / 8.0 GB` + doluluk çubuğu |

Bağlantı/kayıt göstergesi Faz 5'te aynı çubuğa eklenir.

## 7. Ölçü ve esneme kuralları

| Kural | Değer |
| --- | --- |
| Başlangıç pencere | ~1520 × 840 mantıksal piksel |
| Sol sütun | 200 px öntanımlı; kullanıcı ayırıcıyla değiştirebilir; asgari 160 px |
| Sağ sütun | 300 px öntanımlı; asgari 260 px (parametre alanları sığmalı) |
| Merkez | Kalan tüm alan; pencere büyürken **tek büyüyen** sütun |
| Dikey öncelik | Pencere kısalırsa önce Log, sonra Playback küçülür; grafik alanı en son küçülür |
| Dar pencere | Sol ve sağ dock'lar katlanabilir; kartlar kendi içinde kaydırılabilir |
| DPI | %100–%200 ölçekte metin kırpılmaz; ikon ve dokunma hedefleri ölçeklenir |

Dock yerleşimi taşınabilir ve workspace ile kaydedilir; `View → Reset Layout` bu mockup düzenine döner.

## 8. Görsel kabul kontrol listesi

- [ ] Dokuz bölgenin tamamı, tablodaki alanlarda görünür.
- [ ] Sol sütun 200 px, sağ sütun 300 px öntanımlı; merkez kalan alanı doldurur.
- [ ] Sekme sırası mockup ile aynı (8 sekme, `Time Series` seçili).
- [ ] Merkez üç satır; alt satır solda FFT, sağda istatistik.
- [ ] İstatistik kartı altı ölçüyü birimiyle gösterir.
- [ ] Zaman serisi legend'ı X/Y/Z için mavi/turuncu/yeşil.
- [ ] Spektrogramın sağında `PSD [dB]` etiketli renk skalası var.
- [ ] Playback grafiklerin altında, Log playback'in altında.
- [ ] Durum çubuğunda solda durum, sağda bellek göstergesi var.
- [ ] Koyu tema; eksen, birim ve etiketler okunabilir.
- [ ] Karşılaştırma, referans PNG ile **aynı pencere boyutunda** alınmış uygulama görüntüsüyle yapılır.

Sinyal örneklerinin piksel piksel aynı görünmesi beklenmez; yerleşim ile veri doğruluğu ayrı kanıtlanır.

## 9. Mockup ile plan arasında bulunan farklar

Bu farklar `F0-013` ve `F0-007` takibine girer; kaynak olarak **mockup esas alınmalıdır**.

| Konu | Plan Bölüm 5.2 | Mockup | Etki |
| --- | --- | --- | --- |
| `Sensors` | Pressure, Temperature, Accelerometer (X/Y/Z) | + **Gyro**, **Magnetometer** | Kanal sözlüğü eksik |
| `Acoustic` | Hydrophone 1, 2 | + **Hydrophone 3** | Kanal sözlüğü eksik |
| `Navigation` | Position (GPS), Heading, Depth | + **Speed** | Kanal sözlüğü eksik |
| `Vehicle / Transmission` | RPM, Voltage, TX State | + **Current**, **Gear Status** | Kanal sözlüğü eksik |
| `BIT` | Power Supply, Communication, Thermal (3) | **8 alt sistem** (+ Navigation (INS/GPS), Sonar Transceiver, Hydrophones, Thrusters / Transmission, Storage) | `channel-map.md` BIT bit haritası 3 gruba göre yazıldı; 8 gruba genişletilmeli |
| Kanal sayısı | Örnek sözlükte 8/12 | Görselde log `48 channels found` diyor | Örnek sözlük ölçeği küçük; gerçek katalog gelince (E-04) güncellenecek |
