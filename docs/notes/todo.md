# Todo — plan.md'den üretilmiştir

> **Bu dosya elle düzenlenmez.** Kaynak `plan.md`'dir.
> Bir işi tamamlayınca `plan.md`'deki kutuyu `[x]` yap ve
> `python tools/sync_todo.py` çalıştır.

## Agent Instructions

- Work through ALL unchecked tasks sequentially.
- After completing a task, mark it as completed.
- Immediately continue with the next unchecked task.
- Do NOT stop after completing a single task.
- Do NOT ask for confirmation between tasks.
- Stop only when:
  1. All tasks are complete, or
  2. A genuine blocker requires user input.
- Before stopping, re-read this TODO file and verify that no actionable unchecked task remains.

## Autonomous Execution Rule

Work in fully autonomous mode.

- Do not stop to ask the user questions, request confirmation, or present choices when a reasonable recommended/default option exists.
- If multiple implementation options are available, choose the recommended / best-practice option and continue automatically.
- Make reasonable assumptions when information is missing and proceed with the safest, most maintainable choice.
- Only stop if continuing is technically impossible without information that cannot be inferred from the project, codebase, todo.md, or Git history.
- After completing a task, immediately continue with the next unfinished item in todo.md.

**Toplam 655 madde · 507 tamamlandı · 148 kaldı**

`[###################.....]` %77.4

## Özet

| Grup | Tamam | Kalan | Toplam |
| --- | --- | --- | --- |
| Faz 0 — Keşif ve format sözleşmesi | 17 | 0 | 17 |
| Faz 1 — Uygulama iskeleti ve domain modeli | 44 | 0 | 44 |
| Faz 2 — Parser, indeks ve kayıtlı veri | 41 | 0 | 41 |
| Faz 3 — MVP analiz arayüzü | 80 | 0 | 80 |
| Faz 4 — Mockup analiz panosu ve büyük veri performansı | 96 | 0 | 96 |
| Faz 5 — Canlı veri, bağlantı ve kayıt | 41 | 0 | 41 |
| Faz 6 — Windows dağıtımı ve ürünleştirme | 35 | 0 | 35 |
| Faz 7 — Klasör tabanlı Tx/Rx kayıt mimarisi ve TOML şema | 27 | 53 | 80 |
| Faz 8 — Tx/Rx ham veri analizi ve sensör sağlığı | 0 | 76 | 76 |
| Bölüm içi kontrol listeleri | 126 | 19 | 145 |
| **Toplam** | **507** | **148** | **655** |

## A. Bölüm 22 iş tabloları

### Faz 0 — Keşif ve format sözleşmesi (17/17)

| | İş | Sürüm | Süre | Çıktı |
| --- | --- | --- | --- | --- |
| [x] | `F0-001` | `0.1.0` | 15 dk | Git başlangıcını, ignore kurallarını ve VERSION kaynağını hazırla |
| [x] | `F0-002` | `0.2.0` | 15 dk | Üç kullanıcı rolü için ilk beş senaryoyu yaz |
| [x] | `F0-003` | `0.3.0` | 20 dk | Örnek dosya ve format envanterini çıkar |
| [x] | `F0-004` | `0.4.0` | 15 dk | 32 byte örnek header sözleşmesini çıkar |
| [x] | `F0-005` | `0.5.0` | 20 dk | 64 byte örnek Data kayıt sözleşmesini çıkar |
| [x] | `F0-006` | `0.6.0` | 15 dk | 125 ms periyot ve kayıt adı kurallarını belgeye bağla |
| [x] | `F0-007` | `0.7.0` | 20 dk | Mockup kanal gruplarını örnek veri sözlüğüne eşleştir |
| [x] | `F0-008` | `0.8.0` | 20 dk | CRC destekleyen formatın karar kaydını yaz |
| [x] | `F0-009` | `0.9.0` | 15 dk | Küçük geçerli fixture için beklenen sonuçları yaz |
| [x] | `F0-010` | `0.10.0` | 15 dk | Bozuk fixture senaryolarının sonuçlarını yaz |
| [x] | `F0-011` | `0.11.0` | 20 dk | UTC ve cihaz zamanı dönüşüm kararını yaz |
| [x] | `F0-012` | `0.12.0` | 20 dk | Referans mockup'ın dokuz bölgesini yerleşime eşleştir |
| [x] | `F0-013` | `0.13.0` | 20 dk | Mockup etkileşimleri ve görsel kabul listesini yaz |
| [x] | `F0-014` | `0.14.0` | 20 dk | Ölçüm bilgisayarı ve performans bütçesini kaydet |
| [x] | `F0-015` | `0.15.0` | 20 dk | Açık kararları ve dış bağımlılıkları kaydet |
| [x] | `F0-016` | `0.16.0` | 15 dk | ADR listesini iş ve sürüm hedefleriyle eşleştir |
| [x] | `F0-017` | `0.17.0` | 15 dk | Format milestone kabul tutanağını hazırla |

### Faz 1 — Uygulama iskeleti ve domain modeli (44/44)

| | İş | Sürüm | Süre | Çıktı |
| --- | --- | --- | --- | --- |
| [x] | `F1-001` | `0.18.0` | 20 dk | Python paket iskeleti ve bağımlılık kilidini oluştur |
| [x] | `F1-002` | `0.19.0` | 15 dk | Tek komutluk geliştirici kurulumunu yaz |
| [x] | `F1-003` | `0.20.0` | 15 dk | Ruff kontrol yapılandırmasını ekle |
| [x] | `F1-004` | `0.21.0` | 15 dk | Pyright tip kontrolünü ekle |
| [x] | `F1-005` | `0.22.0` | 15 dk | Pytest ve pytest-qt başlangıç düzenini kur |
| [x] | `F1-006` | `0.23.0` | 20 dk | Windows kalite kontrol iş akışını ekle |
| [x] | `F1-007` | `0.24.0` | 20 dk | Uygulama girişini ve temiz kapanışı ekle |
| [x] | `F1-008` | `0.25.0` | 20 dk | Merkezi exception yakalama yolunu ekle |
| [x] | `F1-009` | `0.26.0` | 20 dk | Sürümlü temel ayarları yükle ve kaydet |
| [x] | `F1-010` | `0.27.0` | 20 dk | Dönen log ve session kimliği ekle |
| [x] | `F1-011` | `0.28.0` | 15 dk | ChannelMetadata modelini tanımla |
| [x] | `F1-012` | `0.29.0` | 15 dk | DataChunk ve kalite alanlarını tanımla |
| [x] | `F1-013` | `0.30.0` | 15 dk | TimeRange ve RecordingMetadata modellerini ekle |
| [x] | `F1-014` | `0.31.0` | 15 dk | Event ve BitResult modellerini ekle |
| [x] | `F1-015` | `0.32.0` | 15 dk | TransmissionInterval modelini ekle |
| [x] | `F1-016` | `0.33.0` | 20 dk | RecordingRepository protokolünü tanımla |
| [x] | `F1-017` | `0.34.0` | 15 dk | LiveSource protokolünü tanımla |
| [x] | `F1-018` | `0.35.0` | 15 dk | Deterministik sinüs üretecini ekle |
| [x] | `F1-019` | `0.36.0` | 20 dk | Noise, chirp ve impulse örneklerini ekle |
| [x] | `F1-020` | `0.37.0` | 20 dk | Sahte kanal repository uygulamasını ekle |
| [x] | `F1-021` | `0.38.0` | 15 dk | Sahte BIT, TX ve sistem olaylarını ekle |
| [x] | `F1-022` | `0.39.0` | 20 dk | Mockup'ın üç sütunlu ana pencere düzenini oluştur |
| [x] | `F1-023` | `0.40.0` | 15 dk | Menü ve toolbar eylem iskeletini ekle |
| [x] | `F1-024` | `0.41.0` | 15 dk | Data Explorer dock'unu ekle |
| [x] | `F1-025` | `0.42.0` | 15 dk | Inspector'ı bağlamsal araç sekmesi olarak ekle |
| [x] | `F1-026` | `0.43.0` | 15 dk | Alt Log/Messages alanı ve Events sekmesini ekle |
| [x] | `F1-027` | `0.44.0` | 15 dk | Playback/Time Control şeridini yerleştir |
| [x] | `F1-028` | `0.45.0` | 15 dk | Durum çubuğu alanlarını ekle |
| [x] | `F1-029` | `0.46.0` | 20 dk | Mockup koyu temasını ve mavi vurgularını uygula |
| [x] | `F1-030` | `0.47.0` | 20 dk | Durum ikonları ve kanal paletini ekle |
| [x] | `F1-031` | `0.48.0` | 20 dk | Tek kanallı PlotPanel iskeletini ekle |
| [x] | `F1-032` | `0.49.0` | 20 dk | Mock repository seçimini grafiğe bağla |
| [x] | `F1-033` | `0.50.0` | 15 dk | Boş workspace yönlendirmesini ekle |
| [x] | `F1-034` | `0.51.0` | 15 dk | Open .bin File düğmesi ve dosya özet kartını ekle |
| [x] | `F1-035` | `0.52.0` | 15 dk | Sağ üst BIT/System Status kartını yerleştir |
| [x] | `F1-036` | `0.53.0` | 15 dk | Analysis Tools kartının sekmelerini yerleştir |
| [x] | `F1-037` | `0.54.0` | 15 dk | Sağ alt Data Export kartını yerleştir |
| [x] | `F1-038` | `0.55.0` | 15 dk | Mockup ana analiz sekmelerini yerleştir |
| [x] | `F1-039` | `0.56.0` | 20 dk | Merkez dashboard grafik hücrelerini oluştur |
| [x] | `F1-040` | `0.57.0` | 15 dk | Grafik hızlı araç şeridini yerleştir |
| [x] | `F1-041` | `0.58.0` | 20 dk | Bir ve on milyon noktalık spike girdilerini hazırla |
| [x] | `F1-042` | `0.59.0` | 20 dk | Pan/zoom ve cursor ölçüm koşucusunu ekle |
| [x] | `F1-043` | `0.60.0` | 20 dk | İlk spike sonuçlarını ve darboğazı kaydet |
| [x] | `F1-044` | `0.61.0` | 15 dk | Uygulama iskeleti milestone kontrolünü yap |

### Faz 2 — Parser, indeks ve kayıtlı veri (41/41)

| | İş | Sürüm | Süre | Çıktı |
| --- | --- | --- | --- | --- |
| [x] | `F2-001` | `0.62.0` | 15 dk | Header alan sabitlerini ve veri modelini ekle |
| [x] | `F2-002` | `0.63.0` | 20 dk | Little-endian header okuyucusunu ekle |
| [x] | `F2-003` | `0.64.0` | 15 dk | Magic ve sürüm doğrulamasını ekle |
| [x] | `F2-004` | `0.65.0` | 20 dk | Eksik header ve boyut sınırlarını denetle |
| [x] | `F2-005` | `0.66.0` | 20 dk | Tek Data kaydını çözümle |
| [x] | `F2-006` | `0.67.0` | 20 dk | Ardışık kayıt iterator'unu ekle |
| [x] | `F2-007` | `0.68.0` | 15 dk | 125 ms kayıt zamanını kanonik ns'ye dönüştür |
| [x] | `F2-008` | `0.69.0` | 20 dk | Sıra ve zaman boşluklarını raporla |
| [x] | `F2-009` | `0.70.0` | 15 dk | Kesik son kaydı raporlayarak okumayı bitir |
| [x] | `F2-010` | `0.71.0` | 15 dk | Kayıt adı ve sıra numarası tutarlılığını denetle |
| [x] | `F2-011` | `0.72.0` | 20 dk | Tekrarlı ve sıra dışı kayıtları raporla |
| [x] | `F2-012` | `0.73.0` | 20 dk | Sürüme göre decoder seçimini ekle |
| [x] | `F2-013` | `0.74.0` | 20 dk | Kararlaştırılmış CRC hesaplamasını ekle |
| [x] | `F2-014` | `0.75.0` | 20 dk | CRC alanlı format doğrulamasını bağla |
| [x] | `F2-015` | `0.76.0` | 20 dk | Bilinmeyen paket teşhisini ekle |
| [x] | `F2-016` | `0.77.0` | 20 dk | 32/64 byte örnek fixture yazıcısını ekle |
| [x] | `F2-017` | `0.78.0` | 20 dk | Kesik, bozuk ve sıra boşluklu fixture'ları ekle |
| [x] | `F2-018` | `0.79.0` | 20 dk | CRC destekli format fixture'ını ekle |
| [x] | `F2-019` | `0.80.0` | 20 dk | Sensör alanlarını kanal metadata'sına eşleştir |
| [x] | `F2-020` | `0.81.0` | 20 dk | Scale ve offset dönüşümünü ekle |
| [x] | `F2-021` | `0.82.0` | 20 dk | Calibration seçimini ve kalite eşlemesini ekle |
| [x] | `F2-022` | `0.83.0` | 20 dk | BIT maskesini durum ve değişim olaylarına çevir |
| [x] | `F2-023` | `0.84.0` | 20 dk | TX durumunu başlangıç/bitiş aralıklarına çevir |
| [x] | `F2-024` | `0.85.0` | 15 dk | Parser teşhislerini sistem olaylarına çevir |
| [x] | `F2-025` | `0.86.0` | 20 dk | Cihaz tick dönüşüm adaptörünü ekle |
| [x] | `F2-026` | `0.87.0` | 20 dk | Wraparound ve saat resetini ayırt et |
| [x] | `F2-027` | `0.88.0` | 20 dk | Tanımlı drift düzeltmesini uygula |
| [x] | `F2-028` | `0.89.0` | 20 dk | Kayıt offseti ve zaman indeksini oluştur |
| [x] | `F2-029` | `0.90.0` | 20 dk | Kanal ve olay indekslerini oluştur |
| [x] | `F2-030` | `0.91.0` | 20 dk | Kaynak fingerprint ve parser sürümünü kaydet |
| [x] | `F2-031` | `0.92.0` | 20 dk | İndeks dosyasını atomik kaydet |
| [x] | `F2-032` | `0.93.0` | 20 dk | Geçerli indeksi yeniden kullan |
| [x] | `F2-033` | `0.94.0` | 20 dk | Dosya metadata ve kanal listesini sun |
| [x] | `F2-034` | `0.95.0` | 20 dk | İndeksli zaman aralığı sorgusunu ekle |
| [x] | `F2-035` | `0.96.0` | 20 dk | Zaman ve kategoriye göre olay sorgula |
| [x] | `F2-036` | `0.97.0` | 20 dk | Birden fazla kaydı ayrı kimlikle yönet |
| [x] | `F2-037` | `0.98.0` | 15 dk | Decoded öğeden ham offsete erişim ekle |
| [x] | `F2-038` | `0.99.0` | 15 dk | Okuyucu kaynaklarını güvenli kapat |
| [x] | `F2-039` | `0.100.0` | 20 dk | Bağımsız golden sonuçlarını parser ile karşılaştır |
| [x] | `F2-040` | `0.101.0` | 20 dk | Kaynak dosyanın değişmediğini doğrula |
| [x] | `F2-041` | `0.102.0` | 15 dk | Parser milestone kabulünü kaydet |

### Faz 3 — MVP analiz arayüzü (80/80)

| | İş | Sürüm | Süre | Çıktı |
| --- | --- | --- | --- | --- |
| [x] | `F3-001` | `0.103.0` | 15 dk | Tekli ve çoklu dosya açma seçicisini bağla |
| [x] | `F3-002` | `0.104.0` | 20 dk | Dosya yükleme worker'ını ekle |
| [x] | `F3-003` | `0.105.0` | 20 dk | Yükleme ilerlemesi ve iptal eylemini ekle |
| [x] | `F3-004` | `0.106.0` | 20 dk | Eski istek sonucunun görünümü ezmesini önle |
| [x] | `F3-005` | `0.107.0` | 20 dk | Dosya yükleme sonucunu repository ve ekrana bağla |
| [x] | `F3-006` | `0.108.0` | 15 dk | Format ve dosya erişim hatalarını göster |
| [x] | `F3-007` | `0.109.0` | 20 dk | Dosya kapatma ve bağlı panel temizliğini ekle |
| [x] | `F3-008` | `0.110.0` | 15 dk | Son dosyalar ve varsayılan klasörü kaydet |
| [x] | `F3-009` | `0.111.0` | 20 dk | Dosya ve kanal ağaç modelini ekle |
| [x] | `F3-010` | `0.112.0` | 20 dk | Kanal ağacında lazy yüklemeyi ekle |
| [x] | `F3-011` | `0.113.0` | 20 dk | Ad, ID, birim ve kaynak aramasını ekle |
| [x] | `F3-012` | `0.114.0` | 15 dk | Channels/Data Tree sekmeleri ve kategori filtrelerini bağla |
| [x] | `F3-013` | `0.115.0` | 20 dk | Çift tıkla kanalı grafiğe ekle |
| [x] | `F3-014` | `0.116.0` | 15 dk | Grafikten kanal kaldırmayı ekle |
| [x] | `F3-015` | `0.117.0` | 20 dk | Kanal sürükle-bırak akışını ekle |
| [x] | `F3-016` | `0.118.0` | 20 dk | Çoklu kanal ekleme eylemlerini ekle |
| [x] | `F3-017` | `0.119.0` | 20 dk | Favori kanal gruplarını kaydet |
| [x] | `F3-018` | `0.120.0` | 15 dk | Kanal sağ tık eylemlerini bağla |
| [x] | `F3-019` | `0.121.0` | 20 dk | Ortak zaman ekseninde çoklu seri çiz |
| [x] | `F3-020` | `0.122.0` | 20 dk | Farklı birimler için ikinci Y ekseni ekle |
| [x] | `F3-021` | `0.123.0` | 15 dk | Pan etkileşimini bağla |
| [x] | `F3-022` | `0.124.0` | 15 dk | Yalnız X zoom modunu ekle |
| [x] | `F3-023` | `0.125.0` | 15 dk | Yalnız Y zoom modunu ekle |
| [x] | `F3-024` | `0.126.0` | 15 dk | XY zoom modunu ekle |
| [x] | `F3-025` | `0.127.0` | 15 dk | Autoscale ve görünüm sıfırlamayı ekle |
| [x] | `F3-026` | `0.128.0` | 20 dk | Crosshair ve cursor okumasını ekle |
| [x] | `F3-027` | `0.129.0` | 20 dk | İki cursor fark ölçümünü ekle |
| [x] | `F3-028` | `0.130.0` | 15 dk | Zaman bölgesi seçimini ekle |
| [x] | `F3-029` | `0.131.0` | 15 dk | Seçili bölgeye yakınlaşmayı bağla |
| [x] | `F3-030` | `0.132.0` | 20 dk | Legend gizleme ve solo eylemlerini ekle |
| [x] | `F3-031` | `0.133.0` | 15 dk | Seri rengi, çizgi ve marker ayarını ekle |
| [x] | `F3-032` | `0.134.0` | 20 dk | Paneller arasında X senkronizasyonunu ekle |
| [x] | `F3-033` | `0.135.0` | 20 dk | Grafik tabı ve bölünmüş görünüm ekle |
| [x] | `F3-034` | `0.136.0` | 15 dk | Panel kaynak sınırını ve kapatma temizliğini ekle |
| [x] | `F3-035` | `0.137.0` | 15 dk | Seçili kanal metadata'sını Inspector'a bağla |
| [x] | `F3-036` | `0.138.0` | 20 dk | Inspector görünüm ayarlarını grafiğe bağla |
| [x] | `F3-037` | `0.139.0` | 20 dk | Count, min, max ve mean hesabını ekle |
| [x] | `F3-038` | `0.140.0` | 20 dk | Median, RMS, std ve peak-to-peak ekle |
| [x] | `F3-039` | `0.141.0` | 20 dk | ROI istatistiklerini dashboard kartına bağla |
| [x] | `F3-040` | `0.142.0` | 20 dk | Geliştirici ham kayıt görünümünü ekle |
| [x] | `F3-041` | `0.143.0` | 20 dk | Görünüm ayarları için undo/redo ekle |
| [x] | `F3-042` | `0.144.0` | 20 dk | Ortak olay tablo modelini ekle |
| [x] | `F3-043` | `0.145.0` | 20 dk | Zaman, severity, kaynak ve metin filtrelerini ekle |
| [x] | `F3-044` | `0.146.0` | 15 dk | Olay seçimini Inspector detayına bağla |
| [x] | `F3-045` | `0.147.0` | 20 dk | Olay zaman işaretlerini çiz |
| [x] | `F3-046` | `0.148.0` | 20 dk | Olay çift tıklamasını ortak zamana bağla |
| [x] | `F3-047` | `0.149.0` | 20 dk | TX aralıklarını gölgeli bölge olarak çiz |
| [x] | `F3-048` | `0.150.0` | 15 dk | Transmission sekmesini TX aralıklarına bağla |
| [x] | `F3-049` | `0.151.0` | 20 dk | Yakın tekrar olaylarını grupla |
| [x] | `F3-050` | `0.152.0` | 15 dk | Marker ve TX görünürlüğü kontrollerini ekle |
| [x] | `F3-051` | `0.153.0` | 20 dk | Sağ BIT kartını alt sistem durumlarına bağla |
| [x] | `F3-052` | `0.154.0` | 15 dk | Run BIT Analysis eylemini kayıt analizine bağla |
| [x] | `F3-053` | `0.155.0` | 15 dk | Yükleme ve analiz mesajlarını alt loga bağla |
| [x] | `F3-054` | `0.156.0` | 20 dk | Kayıt geneli Timeline özetini çiz |
| [x] | `F3-055` | `0.157.0` | 20 dk | Timeline viewport seçimini grafiğe bağla |
| [x] | `F3-056` | `0.158.0` | 20 dk | Play, pause ve stop durum makinesini ekle |
| [x] | `F3-057` | `0.159.0` | 20 dk | Kayıt zamanına göre ilerleme saatini ekle |
| [x] | `F3-058` | `0.160.0` | 15 dk | Oynatma hızlarını bağla |
| [x] | `F3-059` | `0.161.0` | 20 dk | Zamana ve önceki/sonraki olaya gitmeyi ekle |
| [x] | `F3-060` | `0.162.0` | 20 dk | Scrubbing sorgularını debounce et |
| [x] | `F3-061` | `0.163.0` | 15 dk | UTC, yerel ve geçen süre gösterimini ekle |
| [x] | `F3-062` | `0.164.0` | 20 dk | Seçili grafiği PNG olarak dışa aktar |
| [x] | `F3-063` | `0.165.0` | 20 dk | Seçili grafiği SVG olarak dışa aktar |
| [x] | `F3-064` | `0.166.0` | 20 dk | Seçili kanal ve aralığı CSV olarak yaz |
| [x] | `F3-065` | `0.167.0` | 20 dk | Export hedefi ve üzerine yazma kontrolünü ekle |
| [x] | `F3-066` | `0.168.0` | 20 dk | Büyük export için worker ve iptal ekle |
| [x] | `F3-067` | `0.169.0` | 20 dk | Sürümlü workspace JSON modelini ekle |
| [x] | `F3-068` | `0.170.0` | 20 dk | Dock ve grafik düzenini kaydet |
| [x] | `F3-069` | `0.171.0` | 20 dk | Workspace dosyasını geri yükle |
| [x] | `F3-070` | `0.172.0` | 20 dk | Eksik kaynak ve bozuk workspace davranışını ekle |
| [x] | `F3-071` | `0.173.0` | 20 dk | Workspace sürüm geçiş yolunu ekle |
| [x] | `F3-072` | `0.174.0` | 20 dk | Bölüm 16 klavye kısayollarını bağla |
| [x] | `F3-073` | `0.175.0` | 20 dk | Klavye odak sırasını ve açıklamaları düzenle |
| [x] | `F3-074` | `0.176.0` | 20 dk | Windows ölçekleme ve kontrast kontrolünü kaydet |
| [x] | `F3-075` | `0.177.0` | 20 dk | Dosyadan olay gezinmesine entegrasyon senaryosu ekle |
| [x] | `F3-076` | `0.178.0` | 20 dk | Kritik plot ve workspace GUI kontrollerini ekle |
| [x] | `F3-077` | `0.179.0` | 20 dk | MVP etkileşim bütçesini ölç |
| [x] | `F3-078` | `0.180.0` | 20 dk | Operatör ve mühendis MVP senaryolarını kaydet |
| [x] | `F3-079` | `0.181.0` | 20 dk | MVP ekran görüntüsünü ana mockup ile karşılaştır |
| [x] | `F3-080` | `1.0.0` | 15 dk | MVP kabulünü kapat ve major sürümü hazırla |

### Faz 4 — Mockup analiz panosu ve büyük veri performansı (96/96)

| | İş | Sürüm | Süre | Çıktı |
| --- | --- | --- | --- | --- |
| [x] | `F4-001` | `1.1.0` | 20 dk | İşlem adımı ve parametre modelini ekle |
| [x] | `F4-002` | `1.2.0` | 20 dk | Sıralı işlem zinciri yürütücüsünü ekle |
| [x] | `F4-003` | `1.3.0` | 20 dk | DSP işlerini worker üzerinden çalıştır |
| [x] | `F4-004` | `1.4.0` | 20 dk | DSP iptal ve eski sonuç denetimini ekle |
| [x] | `F4-005` | `1.5.0` | 20 dk | NaN ve kalite bayrağı politikasını uygula |
| [x] | `F4-006` | `1.6.0` | 20 dk | Analysis Tools işlem listesi editörünü ekle |
| [x] | `F4-007` | `1.7.0` | 20 dk | Analiz parametre hatalarını alanlarda göster |
| [x] | `F4-008` | `1.8.0` | 15 dk | Seçili kanala uygulama ve filtreli veri görünümünü bağla |
| [x] | `F4-009` | `1.9.0` | 20 dk | Ham akustik blok formatının ayrı sürümünü tanımla |
| [x] | `F4-010` | `1.10.0` | 20 dk | 48 kHz akustik blok fixture üretecini ekle |
| [x] | `F4-011` | `1.11.0` | 20 dk | Akustik blok payload decoder'ını ekle |
| [x] | `F4-012` | `1.12.0` | 20 dk | Blok içi örnek zamanlarını üret |
| [x] | `F4-013` | `1.13.0` | 20 dk | Akustik blokları zaman sorgusuna bağla |
| [x] | `F4-014` | `1.14.0` | 20 dk | Akustik boyut ve sample rate sınırlarını doğrula |
| [x] | `F4-015` | `1.15.0` | 20 dk | Detrend ve DC kaldırma hesabını ekle |
| [x] | `F4-016` | `1.16.0` | 15 dk | Detrend türü seçimini işlem editörüne bağla |
| [x] | `F4-017` | `1.17.0` | 20 dk | Moving average hesabını ekle |
| [x] | `F4-018` | `1.18.0` | 15 dk | Moving average pencere kontrolünü bağla |
| [x] | `F4-019` | `1.19.0` | 20 dk | Normalize hesabını ekle |
| [x] | `F4-020` | `1.20.0` | 15 dk | Normalize seçimini işlem editörüne bağla |
| [x] | `F4-021` | `1.21.0` | 20 dk | Pencereli RMS ve envelope hesabını ekle |
| [x] | `F4-022` | `1.22.0` | 15 dk | RMS/envelope pencere kontrollerini bağla |
| [x] | `F4-023` | `1.23.0` | 20 dk | Phase unwrap hesabını ekle |
| [x] | `F4-024` | `1.24.0` | 15 dk | Phase unwrap parametrelerini bağla |
| [x] | `F4-025` | `1.25.0` | 20 dk | Resample/decimate işlemini ekle |
| [x] | `F4-026` | `1.26.0` | 15 dk | Resample hedef frekans kontrolünü bağla |
| [x] | `F4-027` | `1.27.0` | 20 dk | Low-pass filtre hesabını ekle |
| [x] | `F4-028` | `1.28.0` | 15 dk | Low-pass cutoff ve order sınırlarını doğrula |
| [x] | `F4-029` | `1.29.0` | 15 dk | Low-pass araç alanlarını bağla |
| [x] | `F4-030` | `1.30.0` | 20 dk | High-pass filtre hesabını ekle |
| [x] | `F4-031` | `1.31.0` | 15 dk | High-pass sınır ve transient davranışını doğrula |
| [x] | `F4-032` | `1.32.0` | 15 dk | High-pass seçimini araç kartına bağla |
| [x] | `F4-033` | `1.33.0` | 20 dk | Band-pass filtre hesabını ekle |
| [x] | `F4-034` | `1.34.0` | 15 dk | Band-pass alt/üst sınırlarını doğrula |
| [x] | `F4-035` | `1.35.0` | 15 dk | Band-pass iki cutoff alanını bağla |
| [x] | `F4-036` | `1.36.0` | 20 dk | Notch filtre hesabını ekle |
| [x] | `F4-037` | `1.37.0` | 15 dk | Notch frekans ve Q sınırlarını doğrula |
| [x] | `F4-038` | `1.38.0` | 15 dk | Notch frekans ve Q kontrollerini bağla |
| [x] | `F4-039` | `1.39.0` | 20 dk | Window üretimi ve normalizasyonunu ekle |
| [x] | `F4-040` | `1.40.0` | 20 dk | Tek taraflı FFT hesabını ekle |
| [x] | `F4-041` | `1.41.0` | 20 dk | FFT, dB ve Nyquist doğrulamalarını ekle |
| [x] | `F4-042` | `1.42.0` | 20 dk | Seçili aralık FFT'sini mockup alt grafiğine bağla |
| [x] | `F4-043` | `1.43.0` | 20 dk | Welch PSD hesabını ekle |
| [x] | `F4-044` | `1.44.0` | 15 dk | PSD pencere, overlap ve birim sınırlarını doğrula |
| [x] | `F4-045` | `1.45.0` | 20 dk | Spectrum sekmesinde PSD görünümünü ekle |
| [x] | `F4-046` | `1.46.0` | 20 dk | STFT ve spektrogram matrisini hesapla |
| [x] | `F4-047` | `1.47.0` | 20 dk | STFT kenar, overlap ve eksen eşlemesini doğrula |
| [x] | `F4-048` | `1.48.0` | 20 dk | Mockup orta spektrogramını sonuçlara bağla |
| [x] | `F4-049` | `1.49.0` | 15 dk | Spektrogram renk ölçeği kontrollerini ekle |
| [x] | `F4-050` | `1.50.0` | 20 dk | Waterfall zaman dilimi modelini ekle |
| [x] | `F4-051` | `1.51.0` | 20 dk | Waterfall görünümünü ekle |
| [x] | `F4-052` | `1.52.0` | 20 dk | Zaman serisi, STFT, FFT ve istatistiği birlikte bağla |
| [x] | `F4-053` | `1.53.0` | 20 dk | Memory mapping üzerinden blok okuma ekle |
| [x] | `F4-054` | `1.54.0` | 20 dk | Yalnız görünür zaman bloklarını yükle |
| [x] | `F4-055` | `1.55.0` | 20 dk | Piksel genişliğine göre max_points uygula |
| [x] | `F4-056` | `1.56.0` | 20 dk | Min/max envelope downsampling ekle |
| [x] | `F4-057` | `1.57.0` | 20 dk | Çok seviyeli özet bloklarını üret |
| [x] | `F4-058` | `1.58.0` | 20 dk | Viewport için uygun özet seviyesini seç |
| [x] | `F4-059` | `1.59.0` | 20 dk | Bellek sınırlı LRU cache ekle |
| [x] | `F4-060` | `1.60.0` | 20 dk | Cache anahtarına kaynak ve işlem sürümünü ekle |
| [x] | `F4-061` | `1.61.0` | 20 dk | Render sıklığını ve gizli panel güncellemelerini sınırla |
| [x] | `F4-062` | `1.62.0` | 20 dk | Sorgu, render ve indeks sürelerini kaydet |
| [x] | `F4-063` | `1.63.0` | 20 dk | Büyük dosya üretim koşusunu hazırla |
| [x] | `F4-064` | `1.64.0` | 20 dk | Büyük dosya benchmark koşusunu hazırla |
| [x] | `F4-065` | `1.65.0` | 20 dk | Büyük dosya koşusunun sonuçlarını değerlendir |
| [x] | `F4-066` | `1.66.0` | 20 dk | İndeks kesintisi ve cache kurtarmayı doğrula |
| [x] | `F4-067` | `1.67.0` | 15 dk | Profil sonucuyla native hızlandırma ADR'sini yaz |
| [x] | `F4-068` | `1.68.0` | 20 dk | DerivedChannelDefinition modelini ekle |
| [x] | `F4-069` | `1.69.0` | 20 dk | Türetilmiş kanalları repository'ye ekle |
| [x] | `F4-070` | `1.70.0` | 20 dk | Sınırlı aritmetik formül ayrıştırıcısını ekle |
| [x] | `F4-071` | `1.71.0` | 20 dk | Formül değerlendirmesini kanal dizilerine bağla |
| [x] | `F4-072` | `1.72.0` | 20 dk | Formül ifade ve kaynak sınırlarını doğrula |
| [x] | `F4-073` | `1.73.0` | 20 dk | Custom sekmesine basit formül editörü ekle |
| [x] | `F4-074` | `1.74.0` | 15 dk | Annotation ve bookmark modelini ekle |
| [x] | `F4-075` | `1.75.0` | 20 dk | Bookmark ekleme, düzenleme ve silmeyi bağla |
| [x] | `F4-076` | `1.76.0` | 20 dk | Analiz oturumuna zincir ve annotation kaydını ekle |
| [x] | `F4-077` | `1.77.0` | 20 dk | Analiz oturumunu ve türetilmiş kanalları yükle |
| [x] | `F4-078` | `1.78.0` | 20 dk | Taşınmış kaynaklar için yeniden konumlandırma ekle |
| [x] | `F4-079` | `1.79.0` | 20 dk | İşlem zinciri ve annotation undo/redo ekle |
| [x] | `F4-080` | `1.80.0` | 20 dk | BIT durum süresi ve değişim trendini hesapla |
| [x] | `F4-081` | `1.81.0` | 20 dk | BIT/Status trend görünümünü ekle |
| [x] | `F4-082` | `1.82.0` | 20 dk | Grafik penceresini ayırma ve geri takmayı ekle |
| [x] | `F4-083` | `1.83.0` | 20 dk | Çoklu monitör konumlarını kaydet ve sınırla |
| [x] | `F4-084` | `1.84.0` | 20 dk | Event/BIT metadata'sını JSON dışa aktar |
| [x] | `F4-085` | `1.85.0` | 15 dk | TSV ayırıcı seçimini CSV akışına ekle |
| [x] | `F4-086` | `1.86.0` | 20 dk | Statik grafiği PDF olarak dışa aktar |
| [x] | `F4-087` | `1.87.0` | 20 dk | Sinüs, chirp, noise ve impulse referanslarını çalıştır |
| [x] | `F4-088` | `1.88.0` | 20 dk | Kaydet/aç sonrası analiz tekrarını doğrula |
| [x] | `F4-089` | `1.89.0` | 20 dk | Çalışan analiz panosunu mockup ile karşılaştır |
| [x] | `F4-091` | `1.90.0` | 20 dk | Profil B kayıt indeksini kur |
| [x] | `F4-092` | `1.91.0` | 20 dk | Profil B zaman sorgusunu indeksle sınırla |
| [x] | `F4-093` | `1.92.0` | 20 dk | Büyük dosya koşusunu tekrarla ve kararı güncelle |
| [x] | `F4-094` | `1.93.0` | 20 dk | Özet piramidini NumPy blok işlemleriyle hızlandır |
| [x] | `F4-095` | `1.94.0` | 20 dk | Büyük çizim aralıklarını sınırlı bellekle indirgeme |
| [x] | `F4-096` | `1.95.0` | 20 dk | Özet ve akış düzeltmeleri sonrası performansı doğrula |
| [x] | `F4-090` | `2.0.0` | 15 dk | Analiz milestone kabulünü kapat ve major sürümü hazırla |

### Faz 5 — Canlı veri, bağlantı ve kayıt (41/41)

| | İş | Sürüm | Süre | Çıktı |
| --- | --- | --- | --- | --- |
| [x] | `F5-001` | `2.1.0` | 20 dk | Canlı paket ve bağlantı sözleşmesini tamamla |
| [x] | `F5-002` | `2.2.0` | 20 dk | Bağlantı durum makinesini ekle |
| [x] | `F5-003` | `2.3.0` | 20 dk | Dosyadan LiveSource replay adaptörünü ekle |
| [x] | `F5-004` | `2.4.0` | 20 dk | Replay zamanlama ve durdurmayı doğrula |
| [x] | `F5-005` | `2.5.0` | 20 dk | UDP alıcı bağlantısını ekle |
| [x] | `F5-006` | `2.6.0` | 20 dk | UDP paketlerini decoder'a bağla |
| [x] | `F5-007` | `2.7.0` | 20 dk | TCP bağlantı ve okuma akışını ekle |
| [x] | `F5-008` | `2.8.0` | 20 dk | TCP parçalı ve birleşik paket ayrımını ekle |
| [x] | `F5-009` | `2.9.0` | 20 dk | Serial port ayar ve bağlantısını ekle |
| [x] | `F5-010` | `2.10.0` | 20 dk | Serial paket sınırı ve timeout işleyişini ekle |
| [x] | `F5-011` | `2.11.0` | 20 dk | Üç adaptör için ortak sözleşme kontrolü ekle |
| [x] | `F5-012` | `2.12.0` | 20 dk | Sıra numarasından paket kaybını hesapla |
| [x] | `F5-013` | `2.13.0` | 20 dk | Canlı cihaz zamanını kanonik zamana bağla |
| [x] | `F5-014` | `2.14.0` | 20 dk | Sabit kapasiteli ring buffer ekle |
| [x] | `F5-015` | `2.15.0` | 20 dk | Zaman penceresine göre buffer sorgula |
| [x] | `F5-016` | `2.16.0` | 20 dk | Kuyruk sınırı ve drop politikasını uygula |
| [x] | `F5-017` | `2.17.0` | 20 dk | Sınırlı otomatik yeniden bağlanma ekle |
| [x] | `F5-018` | `2.18.0` | 20 dk | Bağlantı ve buffer ayarlarını kaydet |
| [x] | `F5-019` | `2.19.0` | 20 dk | Connect ve Disconnect eylemlerini bağla |
| [x] | `F5-020` | `2.20.0` | 20 dk | Paket kaybı, kuyruk ve buffer durumunu göster |
| [x] | `F5-021` | `2.21.0` | 20 dk | Canlı akışı ortak repository'ye bağla |
| [x] | `F5-022` | `2.22.0` | 20 dk | Canlı veriyi mevcut grafik panellerine bağla |
| [x] | `F5-023` | `2.23.0` | 15 dk | Canlı sona takip etme ve sabit aralık seçimini ekle |
| [x] | `F5-024` | `2.24.0` | 20 dk | Canlı ve playback mod geçişlerini denetle |
| [x] | `F5-025` | `2.25.0` | 20 dk | Sürümlü dosya header yazıcısını ekle |
| [x] | `F5-026` | `2.26.0` | 20 dk | Data kayıt serileştirmesini ekle |
| [x] | `F5-027` | `2.27.0` | 20 dk | 125 ms kayıt biriktirme sınırlarını ekle |
| [x] | `F5-028` | `2.28.0` | 20 dk | Disk yazma kuyruğunu canlı akıştan ayır |
| [x] | `F5-029` | `2.29.0` | 20 dk | Flush ve güvenli dosya kapatmayı ekle |
| [x] | `F5-030` | `2.30.0` | 20 dk | Disk dolması ve yazma hatasını işle |
| [x] | `F5-031` | `2.31.0` | 20 dk | Boyut ve isim sınırında yeni dosyaya geç |
| [x] | `F5-032` | `2.32.0` | 20 dk | Record ve Stop durumunu ana ekrana bağla |
| [x] | `F5-033` | `2.33.0` | 20 dk | Bağlantı kesilmesinde kayıt davranışını uygula |
| [x] | `F5-034` | `2.34.0` | 20 dk | Canlı BIT ve TX olaylarını panoya bağla |
| [x] | `F5-035` | `2.35.0` | 20 dk | Canlı kayıt dosyasını tekrar açarak karşılaştır |
| [x] | `F5-036` | `2.36.0` | 20 dk | Burst, kayıp ve sıra dışı paket simülatörü ekle |
| [x] | `F5-037` | `2.37.0` | 20 dk | Burst ve bağlantı kesintisi sonuçlarını doğrula |
| [x] | `F5-038` | `2.38.0` | 20 dk | Uzun süreli canlı kayıt koşusunu hazırla |
| [x] | `F5-039` | `2.39.0` | 20 dk | Dayanıklılık koşusu raporunu değerlendir |
| [x] | `F5-040` | `2.40.0` | 20 dk | Canlı modda mockup pano davranışını kontrol et |
| [x] | `F5-041` | `3.0.0` | 15 dk | Canlı veri milestone kabulünü kapat ve major sürümü hazırla |

### Faz 6 — Windows dağıtımı ve ürünleştirme (35/35)

| | İş | Sürüm | Süre | Çıktı |
| --- | --- | --- | --- | --- |
| [x] | `F6-001` | `3.1.0` | 20 dk | Paketleme aracı ve dağıtım biçimi ADR'sini tamamla |
| [x] | `F6-002` | `3.2.0` | 20 dk | Windows paketleme yapılandırmasını ekle |
| [x] | `F6-003` | `3.3.0` | 20 dk | Qt plugin, tema ve ikon kaynaklarını pakete ekle |
| [x] | `F6-004` | `3.4.0` | 20 dk | Tek komutluk paket üretim akışını ekle |
| [x] | `F6-005` | `3.5.0` | 20 dk | Temiz Windows ortamında paket açılışını kontrol et |
| [x] | `F6-006` | `3.6.0` | 20 dk | Paketli uygulamada BIN ve export akışını kontrol et |
| [x] | `F6-007` | `3.7.0` | 20 dk | Installer oluşturma adımını ekle |
| [x] | `F6-008` | `3.8.0` | 20 dk | Kurulum, yükseltme ve kaldırmayı kontrol et |
| [x] | `F6-009` | `3.9.0` | 15 dk | Artefakt checksum ve sürüm manifestini üret |
| [x] | `F6-010` | `3.10.0` | 20 dk | Aynı girdilerle paket üretimini karşılaştır |
| [x] | `F6-011` | `3.11.0` | 20 dk | Offline bağımlılık paketleme akışını hazırla |
| [x] | `F6-012` | `3.12.0` | 20 dk | İmzalama gereksinimini yayın akışına bağla |
| [x] | `F6-013` | `3.13.0` | 20 dk | Coverage raporu ve eşiklerini CI'a ekle |
| [x] | `F6-014` | `3.14.0` | 20 dk | Bağımlılık taramasını CI'a ekle |
| [x] | `F6-015` | `3.15.0` | 20 dk | Küçük performans smoke kontrolünü CI'a ekle |
| [x] | `F6-016` | `3.16.0` | 20 dk | Windows paket smoke kontrolünü CI'a ekle |
| [x] | `F6-017` | `3.17.0` | 20 dk | Sürüm artefaktı ve checksum iş akışını ekle |
| [x] | `F6-018` | `3.18.0` | 15 dk | Merge ve release kalite kapılarını belgeye bağla |
| [x] | `F6-019` | `3.19.0` | 20 dk | Tanılama paketi içerik listesini üret |
| [x] | `F6-020` | `3.20.0` | 20 dk | Tanılama önizleme ve dışa aktarımını ekle |
| [x] | `F6-021` | `3.21.0` | 20 dk | Son geçerli workspace kurtarmasını ekle |
| [x] | `F6-022` | `3.22.0` | 20 dk | Tekrarlı aç/kapat ve playback koşusunu hazırla |
| [x] | `F6-023` | `3.23.0` | 20 dk | Aç/kapat dayanıklılık sonuçlarını değerlendir |
| [x] | `F6-024` | `3.24.0` | 20 dk | Mockup üzerinden ana ekran kullanım kılavuzunu yaz |
| [x] | `F6-025` | `3.25.0` | 20 dk | Filtre ve spektral analiz kullanım örneğini yaz |
| [x] | `F6-026` | `3.26.0` | 20 dk | Canlı bağlantı ve kayıt kullanım örneğini yaz |
| [x] | `F6-027` | `3.27.0` | 20 dk | Format ve decoder kılavuzunu güncelle |
| [x] | `F6-028` | `3.28.0` | 15 dk | Klavye, mouse ve ölçekleme kılavuzunu tamamla |
| [x] | `F6-029` | `3.29.0` | 15 dk | Bilinen sorunları ve veri sınırlamalarını yaz |
| [x] | `F6-030` | `3.30.0` | 20 dk | Paketli uygulamada kullanıcı kabul turunu kaydet |
| [x] | `F6-031` | `3.31.0` | 20 dk | Paketli ana ekranı referans mockup ile karşılaştır |
| [x] | `F6-032` | `3.32.0` | 20 dk | Release ve geri dönüş prosedürünü yaz |
| [x] | `F6-033` | `3.33.0` | 15 dk | Major sürüm notları ve milestone özetini hazırla |
| [x] | `F6-034` | `4.0.0` | 15 dk | Dağıtım milestone kabulünü kapat ve major sürümü hazırla |
| [x] | `F6-035` | `3.35.0` | 20 dk | Kalite bayraklarını dışa aktarmaya ve paket denetimine taşı |

### Faz 7 — Klasör tabanlı Tx/Rx kayıt mimarisi ve TOML şema (27/80)

| | İş | Sürüm | Süre | Çıktı |
| --- | --- | --- | --- | --- |
| [x] | `F7-001` | `4.6.0` | 20 dk | Profil C klasör ve dosya sözleşmesi taslağını yaz |
| [x] | `F7-002` | `4.7.0` | 20 dk | Kullanıcı kararlarını ve kalan açık kararları kayda geç |
| [x] | `F7-003` | `4.8.0` | 20 dk | Bayt bütçesi ve zaman kayması tablosunu belgeye yaz |
| [x] | `F7-004` | `4.9.0` | 20 dk | C++ struct → TOML eşleme sözleşmesini yaz |
| [x] | `F7-005` | `4.10.0` | 20 dk | Zaman ekseninin tek kaynağını sözleşmeye bağla |
| [x] | `F7-006` | `4.11.0` | 20 dk | Örnek TOML şema dosyasını yaz (enum + struct + FrameHeader) |
| [x] | `F7-007` | `4.12.0` | 20 dk | cpp tipi → Python struct kodu → NumPy dtype eşleme tablosunu kur |
| [x] | `F7-008` | `4.13.0` | 20 dk | Şema yükleyicisini ve sürüm alanını ekle |
| [x] | `F7-009` | `4.14.0` | 20 dk | Enum çözümleyicisini ekle |
| [x] | `F7-010` | `4.15.0` | 20 dk | Struct alan çözümleyicisini ekle |
| [x] | `F7-011` | `4.16.0` | 20 dk | Offset çakışması ve boşluk denetimini ekle |
| [x] | `F7-012` | `4.17.0` | 15 dk | Bildirilen boyut ile hesaplanan boyut uyuşmazlığını reddet |
| [x] | `F7-013` | `4.18.0` | 20 dk | Hizalama ihlali denetimini ekle |
| [x] | `F7-014` | `4.19.0` | 20 dk | Şemadan çalışma zamanında `struct.Struct` üret |
| [x] | `F7-015` | `4.20.0` | 20 dk | Şemadan NumPy structured dtype üret |
| [x] | `F7-016` | `4.21.0` | 15 dk | Şema parmak izini hesapla ve kayda yaz |
| [x] | `F7-017` | `4.22.0` | 20 dk | Şema ile kayıt uyuşmazlığını tespit eden kapıyı kur |
| [x] | `F7-018` | `4.23.0` | 20 dk | Şema doğrulama hatalarını kullanıcıya taşıyan mesajları yaz |
| [x] | `F7-019` | `4.24.0` | 20 dk | Profil C dosya header'ını çöz |
| [x] | `F7-020` | `4.25.0` | 20 dk | Frame header'ını şemadan çöz |
| [x] | `F7-021` | `4.26.0` | 20 dk | `complex64` payload'unu kopyasız oku |
| [x] | `F7-022` | `4.27.0` | 20 dk | Sensör × örnek yerleşimini doğrula |
| [x] | `F7-023` | `4.28.0` | 20 dk | Frame CRC doğrulamasını ekle |
| [x] | `F7-024` | `4.29.0` | 20 dk | Kesik dosyayı raporla, tam frame'leri kullan |
| [x] | `F7-025` | `4.30.0` | 15 dk | Frame indeksi ile dosya adı uyuşmazlığını raporla |
| [x] | `F7-026` | `4.31.0` | 20 dk | Timestamp ile frame sayacı arasındaki kaymayı ölç |
| [x] | `F7-027` | `4.32.0` | 20 dk | Sürüm dağıtımına Profil C'yi ekle |
| [ ] | `F7-028` | `4.33.0` | 20 dk | Kayıt klasörü düzenini keşfet |
| [ ] | `F7-029` | `4.34.0` | 20 dk | Dosya sayacı sırasını doğrula ve boşlukları raporla |
| [ ] | `F7-030` | `4.35.0` | 20 dk | Klasör manifestini oku ve yoksa üret |
| [ ] | `F7-031` | `4.36.0` | 20 dk | Klasör seviyesinde indeks yapısını kur |
| [ ] | `F7-032` | `4.37.0` | 20 dk | İndeksi dosya adı, boyut ve değişiklik zamanıyla geçersizle |
| [ ] | `F7-033` | `4.38.0` | 15 dk | İndeksi atomik yaz |
| [ ] | `F7-034` | `4.39.0` | 20 dk | Salt okunur klasörde indeksi bellekte kur |
| [ ] | `F7-035` | `4.40.0` | 20 dk | 1.200 dosyalık kayıtta indeks kurma süresini ölç |
| [ ] | `F7-036` | `4.41.0` | 20 dk | `FolderRecordingRepository` iskeletini kur |
| [ ] | `F7-037` | `4.42.0` | 20 dk | `metadata()` zaman aralığını klasörden üret |
| [ ] | `F7-038` | `4.43.0` | 20 dk | `channels()` ile Tx/Rx × 32 sensörü sun |
| [ ] | `F7-039` | `4.44.0` | 20 dk | `query()` çağrısını dosya sınırlarını aşacak biçimde kur |
| [ ] | `F7-040` | `4.45.0` | 20 dk | Seyreltmeyi dosya sınırlarında tutarlı yap |
| [ ] | `F7-041` | `4.46.0` | 20 dk | Frame header alanlarını metadata olarak sun |
| [ ] | `F7-042` | `4.47.0` | 20 dk | Önden okuma ve bellek bütçesini kur |
| [ ] | `F7-043` | `4.48.0` | 20 dk | Oynatmayı dosya sınırında kesintisiz yap |
| [ ] | `F7-044` | `4.49.0` | 20 dk | Bozuk ve eksik dosyayı oynatmada göster |
| [ ] | `F7-045` | `4.50.0` | 20 dk | Klasör açma diyalogunu ekle |
| [ ] | `F7-046` | `4.51.0` | 15 dk | Son kullanılanlara klasör yolunu ekle |
| [ ] | `F7-047` | `4.52.0` | 20 dk | Data Explorer'da Tx/Rx ağacını kur |
| [ ] | `F7-048` | `4.53.0` | 20 dk | Şema dosyası seçimini ayarlara ekle |
| [ ] | `F7-049` | `4.54.0` | 20 dk | Şema değişince açık kaydı yeniden yükle |
| [ ] | `F7-050` | `4.55.0` | 20 dk | Geçersiz şemayı arayüzde göster |
| [ ] | `F7-051` | `4.56.0` | 15 dk | Sürükle bırakta klasör kabul et |
| [ ] | `F7-052` | `4.57.0` | 20 dk | Kayıt kartında klasör ve şema bilgisini göster |
| [ ] | `F7-053` | `4.58.0` | 20 dk | Profil C sentetik üreteç iskeletini kur |
| [ ] | `F7-054` | `4.59.0` | 20 dk | CW dalga biçimi üretimini ekle |
| [ ] | `F7-055` | `4.60.0` | 20 dk | LFM yukarı ve aşağı cıvıltı üretimini ekle |
| [ ] | `F7-056` | `4.61.0` | 20 dk | HFM ve kodlu dalga biçimi üretimini ekle |
| [ ] | `F7-057` | `4.62.0` | 20 dk | PRI ve darbe uzunluğu parametrelerini ekle |
| [ ] | `F7-058` | `4.63.0` | 20 dk | Tx/Rx bölüşümünü PRI ve darbe süresine göre yap |
| [ ] | `F7-059` | `4.64.0` | 20 dk | Platform ve CIT alanlarını doldur |
| [ ] | `F7-060` | `4.65.0` | 20 dk | Eleman arızası enjeksiyonunu ekle |
| [ ] | `F7-061` | `4.66.0` | 20 dk | I/Q bozulması enjeksiyonunu ekle |
| [ ] | `F7-062` | `4.67.0` | 20 dk | Dosya ve şema bozulma senaryolarını ekle |
| [ ] | `F7-063` | `4.68.0` | 20 dk | On iki senaryonun parametre setini tanımla |
| [ ] | `F7-064` | `4.69.0` | 20 dk | Golden dilim fixture'ını üret ve SHA-256 sabitle |
| [ ] | `F7-065` | `4.70.0` | 15 dk | Büyük senaryoların depoya girmediğini teste bağla |
| [ ] | `F7-066` | `4.71.0` | 20 dk | .mat dışa aktarma hedefini kaydet |
| [ ] | `F7-067` | `4.72.0` | 20 dk | Rx ve Tx için ayrı `.mat` dosyası üret |
| [ ] | `F7-068` | `4.73.0` | 20 dk | Değişken düzenini kur |
| [ ] | `F7-069` | `4.74.0` | 20 dk | Metadata'yı `.mat` içine koy |
| [ ] | `F7-070` | `4.75.0` | 20 dk | MAT v5 boyut sınırını denetle |
| [ ] | `F7-071` | `4.76.0` | 20 dk | İlerleme ve iptal desteğini bağla |
| [ ] | `F7-072` | `4.77.0` | 15 dk | Atomik yazımı kur |
| [ ] | `F7-073` | `4.78.0` | 20 dk | Üretilen `.mat`'i geri okuyarak doğrula |
| [ ] | `F7-074` | `4.79.0` | 20 dk | 10 dakikalık kaydın açılış süresini ölç |
| [ ] | `F7-075` | `4.80.0` | 20 dk | Sorgu ve seyreltme bütçesini ölç |
| [ ] | `F7-076` | `4.81.0` | 20 dk | Tepe bellek kullanımını ölç |
| [ ] | `F7-077` | `4.82.0` | 20 dk | Profil C format belgesini tamamla |
| [ ] | `F7-078` | `4.83.0` | 20 dk | TOML şema kılavuzunu yaz |
| [ ] | `F7-079` | `4.84.0` | 20 dk | MATLAB kullanım notunu yaz |
| [ ] | `F7-080` | `5.0.0` | 20 dk | Faz 7 milestone kabul turunu koştur ve etiketle |

### Faz 8 — Tx/Rx ham veri analizi ve sensör sağlığı (0/76)

| | İş | Sürüm | Süre | Çıktı |
| --- | --- | --- | --- | --- |
| [ ] | `F8-001` | `5.1.0` | 20 dk | analysis/complex_guard.py: complex girdide sessiz gerçek-kısım düşürmesini ComplexDataError'a çeviren tek g... |
| [ ] | `F8-002` | `5.2.0` | 15 dk | pyproject.toml pytest bölümünde filterwarnings = error::numpy.exceptions.ComplexWarning |
| [ ] | `F8-003` | `5.3.0` | 15 dk | domain/channel.py SUPPORTED_DTYPES'a complex64 ve complex128 eklenir |
| [ ] | `F8-004` | `5.4.0` | 20 dk | domain/array_frame.py: değişmez ArrayFrame (frame_index, timestamp_ns, values (32,820) complex64, quality m... |
| [ ] | `F8-005` | `5.5.0` | 20 dk | analysis/complex_spectrum.py: iki taraflı FFT (fft + fftfreq + fftshift) ve faz alanı taşıyan ComplexSpectr... |
| [ ] | `F8-006` | `5.6.0` | 20 dk | 820 örneklik frame için FFT plan notu ve zero-pad yardımcısı; 820 = 2^2 * 5 * 41 olduğu için radix-2 yoktur |
| [ ] | `F8-007` | `5.7.0` | 20 dk | repository protokolüne query_array(channel_ids, time_range) toplu çok kanallı sorgu eklenir |
| [ ] | `F8-008` | `5.8.0` | 20 dk | Dosya boyutu Diophantine çözücüsü: dosya_boyutu = H_dosya + F*(H_frame + C*S*B) denkleminden dtype ve başlı... |
| [ ] | `F8-009` | `5.9.0` | 20 dk | Kuantalama adımı q ve etkin bit derinliği B_eff kestirimi (sıfır olmayan ardışık farkların yaklaşık OBEB'i... |
| [ ] | `F8-010` | `5.10.0` | 20 dk | Bit düzeyinde takılı-bit taraması: kanal x bit toggle oranı matrisi |
| [ ] | `F8-011` | `5.11.0` | 20 dk | Frame başlığı ikili düzeni keşif tarayıcısı: sabit adımlı offset taraması ile monoton frame indeksi ve time... |
| [ ] | `F8-012` | `5.12.0` | 20 dk | Frame süreklilik ve bütünlük QC motoru: indeks atlaması, tekrar, timestamp monotonluğu, percent_availabilit... |
| [ ] | `F8-013` | `5.13.0` | 15 dk | Örnek-sayısı ile zaman damgası arasındaki sürüklenme ölçümü: drift_ppm = (dt_timestamp - N/fs)/(N/fs)*1e6,... |
| [ ] | `F8-014` | `5.14.0` | 20 dk | Frame-arası faz sürekliliği testi: kararlı dar bant bileşende frame sınırındaki faz sıçramasından alt-örnek... |
| [ ] | `F8-015` | `5.15.0` | 20 dk | Kanal örnekleme eşzamanlılığı testi: ortak geçici olayda kanal başına grup gecikmesinden 'simültane S/H' mi... |
| [ ] | `F8-016` | `5.16.0` | 20 dk | Anti-alias bant kenarı ölçümü: çok frame ortalamalı iki taraflı gürültü PSD'sinden gerçek kullanılabilir B |
| [ ] | `F8-017` | `5.17.0` | 20 dk | I/Q yerleşim hipotezi seçici: interleaved/planar x kanal-majör/örnek-majör dört hipotezin dairesellik, zarf... |
| [ ] | `F8-018` | `5.18.0` | 20 dk | LevelMetrics: akustik grup (Vpp_env = 2*max |
| [ ] | `F8-019` | `5.19.0` | 15 dk | dBFS dönüşümü: yalnız tam ölçek referansı bilindiğinde; float veride None ve 'göreli dB' etiketi |
| [ ] | `F8-020` | `5.20.0` | 20 dk | Tepe faktörü / PAPR iki ayrı tanımla: CF_env = max |
| [ ] | `F8-021` | `5.21.0` | 20 dk | Kırpılma tespiti iki yöntemle: tam ölçek biliniyorsa doğrudan sayım, bilinmiyorsa histogram uç-bin yığılma... |
| [ ] | `F8-022` | `5.22.0` | 15 dk | Donmuş örnek / dijital ölü kanal metriği (QARTOD Flat Line): ardışık aynı değer oranı F ve I=Q=0 oranı Z |
| [ ] | `F8-023` | `5.23.0` | 20 dk | Kuantalama gürültü tabanı ve ENOB kıyası: ölçülen taban ile teorik q^2/(12*fs) tabanının farkı; 'ölü' ile '... |
| [ ] | `F8-024` | `5.24.0` | 15 dk | DC ofset / LO sızıntısı: mean(I), mean(Q) ve complex DCR_dB = 10*log10( |
| [ ] | `F8-025` | `5.25.0` | 20 dk | Kazanç dengesizliği g_hat = Q_rms/I_rms ve kuadratür faz hatası phi_hat = arcsin(E[I*Q]/(I_rms*Q_rms)) — GE... |
| [ ] | `F8-026` | `5.26.0` | 20 dk | Kör IMRR: dairesellik katsayısı rho = E[z^2]/E[ |
| [ ] | `F8-027` | `5.27.0` | 15 dk | Doğrudan IMRR: baskın ton varken S(-f0)/S(+f0); f0 tepe konumundan bulunur, f_c bilinmesi gerekmez |
| [ ] | `F8-028` | `5.28.0` | 20 dk | Kanal-arası I/Q tutarlılığı: delta_g_m, delta_phi_m, delta_IMRR_m medyana göre; 'tek kanal mı sistem mi' ay... |
| [ ] | `F8-029` | `5.29.0` | 20 dk | welch_psd'nin iki taraflı complex yolu (mevcut |
| [ ] | `F8-030` | `5.30.0` | 20 dk | Pencere kataloğunu genişletme: Blackman-Harris-4, Nuttall, Tukey, Kaiser (mevcut windows.py referans tablo... |
| [ ] | `F8-031` | `5.31.0` | 20 dk | Çapraz spektrum S_mk(f) ve genlik-kare koherans gamma^2_mk(f) matrisi |
| [ ] | `F8-032` | `5.32.0` | 20 dk | Koherans anlamlılık eşiği gamma^2_crit = 1 - alpha^(1/(K-1)) ve ÖRTÜŞMELİ Welch için etkin K düzeltmesi |
| [ ] | `F8-033` | `5.33.0` | 20 dk | Bant içi spektral eğim: log-genlik/frekans doğrusal uydurma, birim dB/kHz (dB/oktav DEĞİL — f_c bilinmediği... |
| [ ] | `F8-034` | `5.34.0` | 20 dk | Kanal-arası göreli seviye haritası ve robust aykırı tespiti (medyan + MAD, Iglewicz-Hoaglin modified z) |
| [ ] | `F8-035` | `5.35.0` | 15 dk | Göreli gürültü tabanı sapması delta_NL_m (dizi medyanına göre, ortak-mod bastırmalı) |
| [ ] | `F8-036` | `5.36.0` | 20 dk | 32x32 karmaşık korelasyon matrisi ile ölü kanal, cross-talk ve polarite tersliği bayrakları |
| [ ] | `F8-037` | `5.37.0` | 20 dk | Kovaryans kestirimi: snapshot'lar frame İÇİ komşu FFT binlerinden alınır; frame-ARASI toplama F8-014 kanıtı... |
| [ ] | `F8-038` | `5.38.0` | 20 dk | Özdeğer spektrumu, sayısal rank, koşul sayısı (Marchenko-Pastur referansıyla) ve özvektör yoğunlaşma metriğ... |
| [ ] | `F8-039` | `5.39.0` | 20 dk | Örtüşen çift korelasyon arıza tekilleştiricisi: kanal haritası bilinmediği için 32*31/2 = 496 çiftin tamamı... |
| [ ] | `F8-040` | `5.40.0` | 20 dk | PCA leave-one-out rekonstrüksiyon kalıntısı (SVI) ve ön koşul kapısı: lambda_1/lambda_ort yetersizse yöntem... |
| [ ] | `F8-041` | `5.41.0` | 20 dk | Çok-metrik karar motoru: OK / UYARI / ARIZA durum makinesi, tetikleyen metrik listesi, kanal maskeleme çıkışı |
| [ ] | `F8-042` | `5.42.0` | 20 dk | Eleman ekseni DFT'si: her frekans bininde 32 elemanlı vektöre FFT; eksen 'derece/eleman faz ilerlemesi' (u... |
| [ ] | `F8-043` | `5.43.0` | 20 dk | Ölçülen koherent dizi kazancı: baş özvektör hüzmeleyici (yön vektörü gerektirmez), teorik üst sınırdan sapma |
| [ ] | `F8-044` | `5.44.0` | 20 dk | Geometri sınıfı hipotez testi (doğrusal vs dairesel) ve kanal haritası doğrulaması (korelasyon matrisinin b... |
| [ ] | `F8-045` | `5.45.0` | 20 dk | Tx klasörü ham envanteri: kanal sayısı ve frame başına örnek sayısı dosya boyutundan ÖLÇÜLÜR; Rx ile uyuşma... |
| [ ] | `F8-046` | `5.46.0` | 20 dk | Darbe envanteri: zarf eşiği ve histerezisle Tx segment tespiti, alt-örnek interpolasyonlu TOA, PW, IEEE 181... |
| [ ] | `F8-047` | `5.47.0` | 20 dk | Anlık frekans kestirimi: CFD f[n] = arg(z[n+1]*conj(z[n-1]))/(4*pi*T) ve ayrı adlandırılmış FFD f[n] = arg(... |
| [ ] | `F8-048` | `5.48.0` | 20 dk | Dalga biçimi sınıflandırıcısı (CW / LFM-up / LFM-down / kodlu) ve faz-bölgesi kalıntısı ile chirp doğrusallığı |
| [ ] | `F8-049` | `5.49.0` | 20 dk | PRI / PRF / jitter: TOA tabanlı ve timestamp tabanlı iki bağımsız ölçüm, histogram, kümülatif zaman hatası,... |
| [ ] | `F8-050` | `5.50.0` | 20 dk | Tx/Rx örnek bütçesi kapanış testi: N_tx + N_rx toplamından PRI ve T_tx ölçümü, sabit/uyarlamalı kapı kararı |
| [ ] | `F8-051` | `5.51.0` | 20 dk | Darbe-arası genlik/faz kararlılığı, normalize koherens gamma, frekans ofseti sürüklenmesi ve delta_phi_p di... |
| [ ] | `F8-052` | `5.52.0` | 20 dk | Alıcı toparlanma süresi tau_rec: Tx sonrası zarfa üstel+sabit uydurma, kanal-kanal fark olarak (reverberasy... |
| [ ] | `F8-053` | `5.53.0` | 20 dk | Ölçülen Tx replikası: çok darbeli koherent ortalama (genlik-SNR sqrt(P), güç-SNR P kat) |
| [ ] | `F8-054` | `5.54.0` | 20 dk | RX bant şelalesi paneli verisi: frame başına iki taraflı STFT, eksen 'f - f_c (Hz)', 9,99 Hz bin, saniyede... |
| [ ] | `F8-055` | `5.55.0` | 15 dk | Geniş bant enerji izi: kanal ve frame başına toplam |
| [ ] | `F8-056` | `5.56.0` | 20 dk | Zarf modülasyon spektrumu (DEMON çekirdeği): e[n] = |
| [ ] | `F8-057` | `5.57.0` | 20 dk | DEMON PRI-tarağı belirsizlik kapısı: kapılama zarf spektrumunu PRI tarağıyla katladığı için etkilenen binle... |
| [ ] | `F8-058` | `5.58.0` | 20 dk | array_profile.json şeması: status (UNCALIBRATED/PARTIAL/CALIBRATED), acquisition, array (tip, eleman konuml... |
| [ ] | `F8-059` | `5.59.0` | 20 dk | Ölçekleme alt şeması (adc_bits, adc_fullscale_v, analog_gain_db, iq_convention_gain, hydrophone_sensitivity... |
| [ ] | `F8-060` | `5.60.0` | 20 dk | Mutlak Vpp/Vrms dönüşümü (sabitler girildiğinde açılır) ve konvansiyon belirsizliği notu |
| [ ] | `F8-061` | `5.61.0` | 20 dk | AGC/TVG imza testi: PRI'dan PRI'ya kuantumlu basamaklı taban seviyesi sıçraması taraması |
| [ ] | `F8-062` | `5.62.0` | 20 dk | Cross Analysis sekmesini etkinleştir (ENABLED_TABS + _on_view_tab_changed) ve 32x32 korelasyon/koherans ısı... |
| [ ] | `F8-063` | `5.63.0` | 20 dk | Kanal x frekans sapma ısı haritası (medyandan dB) ile özdeğer scree grafiği ve koşul sayısı göstergesini ay... |
| [ ] | `F8-064` | `5.64.0` | 20 dk | Eleman sağlık matrisi (32 hücre x durum, tetikleyen metrik ipucu) ve karmaşık kazanç polar grafiği aynı pan... |
| [ ] | `F8-065` | `5.65.0` | 20 dk | 3D View sekmesini etkinleştir ve kanal × frekans × zaman küpü panelini bağla |
| [ ] | `F8-066` | `5.66.0` | 20 dk | Tx darbe paneli: darbe zarflarının üst üste bindirilmesi, anlık frekans eğrisi ve PRI histogramı |
| [ ] | `F8-067` | `5.67.0` | 20 dk | Report sekmesini etkinleştir ve sağlık skor kartını bağla (kanal |
| [ ] | `F8-068` | `5.68.0` | 20 dk | Sürümlü JSON şeması + CSV sağlık raporu; her alan birim (count/dBFS/rel-dB/örnek/Hz) ve olculen |
| [ ] | `F8-069` | `5.69.0` | 20 dk | HDF5/netCDF4 dışa aktarma (ICES SONAR-netCDF4 grup yapısı referans alınır) ve kalite maskesinin veriyle bir... |
| [ ] | `F8-070` | `5.70.0` | 20 dk | Mevcut Profil B sentetik üreticisini complex 32x820 Tx/Rx klasör yapısına genişlet (tarih klasörü / Tx-Rx a... |
| [ ] | `F8-071` | `5.71.0` | 20 dk | On arıza modeli enjeksiyonu (ölü, gürültülü, kazanç sapmalı, faz kaymalı, kırpılmış, DC ofsetli, I/Q denges... |
| [ ] | `F8-072` | `5.72.0` | 20 dk | Zaman ekseni arıza modelleri: frame atlama, timestamp geri sıçraması, 0,8 örnek/frame kayma, PRI jitter ve... |
| [ ] | `F8-073` | `5.73.0` | 20 dk | Eşik kalibrasyon aracı: metrik dağılımını dizi boyunca çizip doğal kümeleri bulan ve eşik öneren yardımcı;... |
| [ ] | `F8-074` | `5.74.0` | 20 dk | docs/analysis/array-health.md: her metrik için formül, birim, eşik, kaynak veya 'KAYNAK YOK — genel mühendi... |
| [ ] | `F8-075` | `5.75.0` | 20 dk | docs/notes/open-decisions.md'ye Faz 8 açık kararlarının eklenmesi (mevcut tablo biçimi ve durum kodları kor... |
| [ ] | `F8-076` | `6.0.0` | 20 dk | Faz 8 milestone kabul tutanağı ve etiket |

## B. Bölüm içi kontrol listeleri


### 5.2 Data Explorer

- [x] Lazy-loading destekli model/view tabanlı ağaç oluştur.  (`F3-009` ağaç modeli, `F3-010` lazy yükleme)  <sub>plan.md:205</sub>
- [x] Kanal adına, ID’ye, birime ve kaynağa göre arama ekle.  (`F3-011`; dört alan da testlerle kapsandı)  <sub>plan.md:206</sub>
- [x] `Sensors`, `BIT`, `Transmission`, `Derived` hızlı filtreleri ekle.  (`F3-012`)  <sub>plan.md:207</sub>
- [x] Kanal türü, bağlantı durumu ve alarm seviyesi için ikon sistemi belirle.  (kanal türü ikonları `ui/status_icons.py` `CHANNEL_SOURCE_STYLES`; her ikon simge + metin taşır, ipucu kaynakta bulunma durumunu yazar)  <sub>plan.md:208</sub>
- [x] Kanalı çift tıklama ve sürükle-bırak ile grafiğe ekle.  (`F3-013` çift tık, `F3-015` sürükle-bırak)  <sub>plan.md:209</sub>
- [ ] Çoklu seçim ve “seçilenleri aynı grafikte/yeni grafiklerde aç” komutu ekle.  **AÇIK:** `F3-016` "aynı grafikte" kısmını verdi. "Ayrı grafiklerde" kısmı, Bölüm 5.3'teki **çoklu-panel altyapısına** bağlıdır (bkz. aynı bölümdeki "tab, split view" maddesi); ikisi tek iştir ve birlikte yapılmalıdır. Bugün `F4-082` grafiği ayrı pencereye **taşır**, yeni panel **üretmez**.  <sub>plan.md:210</sub>
- [x] Favori kanal gruplarını kaydet.  (`F3-017`)  <sub>plan.md:211</sub>
- [x] Sağ tık menüsü: Plot, Inspect, Add to Existing Plot, Export, Copy Path.  (beş eylem de bağlı: Plot · Inspect · Add to Existing Plot · Export · Copy Path)  <sub>plan.md:212</sub>

### 5.3 Workspace ve grafik kartı

- [x] `PlotPanel` temel bileşenini oluştur.  (`F1-031`; çoklu seri `F3-019`)  <sub>plan.md:232</sub>
- [x] Birden fazla kanalı aynı panelde destekle.  (`F3-019`)  <sub>plan.md:233</sub>
- [x] Sol/sağ Y ekseni veya ayrı eksen grupları desteğini değerlendir.  (`F3-020`: ikinci Y ekseni farklı birimli seriler için eklendi)  <sub>plan.md:234</sub>
- [x] Tüm açık grafiklerde isteğe bağlı X-axis synchronization ekle.  (`F3-032`: araç çubuğundaki `Sync` anahtarı; durumu workspace ile saklanır)  <sub>plan.md:235</sub>
- [x] Legend üzerinde kanal gizleme ve solo mode ekle.  (`F3-030`; `test_plot_legend_solo.py`)  <sub>plan.md:236</sub>
- [ ] Grafiği tab, split view ve ayrı pencere olarak açmayı destekle.  **AÇIK:** Ayrı pencere var (`F4-082`, `test_detached_plot.py`) ama var olan paneli taşır. Sekme ve split view için **yeni `PlotPanel` üretebilen** bir kapsayıcı, X senkron gruplarının panel başına yönetimi ve workspace'e kaydı gerekir. Merkez yerleşimi `F6-031` mockup kabulünde ölçülüyor; bu iş o kabulü bozmadan yapılmalıdır. Bölüm 5.2'deki "ayrı grafiklerde aç" maddesi de buna bağlıdır.  <sub>plan.md:237</sub>
- [x] Boş workspace için sürükle-bırak yönlendirmesi tasarla.  (`PlotPanel.EMPTY_PLOT_HINT`: boş grafikte sürükle-bırak yönlendirmesi görünür, seri eklenince kaybolur)  <sub>plan.md:238</sub>
- [x] Grafik sayısı arttığında kaynak kullanımını sınırla.  (`F4-055` nokta bütçesi görünür piksel genişliğine göre örnek sayısını sınırlar; merkez yerleşimi sabit sayıda grafik taşır)  <sub>plan.md:239</sub>

### 5.4 Inspector

- [x] Seçime göre içeriği dinamik güncelle.  (`F1-025`, `F3-035`, `F3-044`: seçilen kanal ve olay Inspector içeriğini günceller)  <sub>plan.md:255</sub>
- [x] Değişiklikleri undo/redo sistemine bağla.  (`F3-041` görünüm ayarları, `F4-079` işlem zinciri ve işaretler)  <sub>plan.md:256</sub>
- [x] İşlenmiş kanalın ham veriyi değiştirmediğini açıkça göster.  (`F4-005` ham dizi değişmez; `raw` dışa aktarma `variant=raw` ile ayrı yazılır)  <sub>plan.md:257</sub>
- [x] Filtre sırasını sürükle-bırak ile değiştirmeyi destekle.  (`F4-006`: Analysis Tools listesinde adım ekleme, silme ve sıralama)  <sub>plan.md:258</sub>
- [x] Geçersiz parametreleri çalıştırmadan önce doğrula.  (`F4-007`: geçersiz değer işlem başlamadan alanda açıklanır)  <sub>plan.md:259</sub>

### 5.5 BIT, Events ve Transmission paneli

- [x] Zaman, kategori, severity, source ve metin filtreleri ekle.  (`F3-043` zaman/severity/kaynak/metin, `F2-035` kategori sorgusu)  <sub>plan.md:280</sub>
- [x] Severity renklerini yalnızca renge bağlı bırakma; ikon ve metin de kullan.  (`ui/status_icons.py`: severity hem ikon hem metin taşır, yalnız renge bağlı değil)  <sub>plan.md:281</sub>
- [x] Satıra çift tıklayınca tüm senkronize grafikleri ilgili zamana götür.  (`F3-046`)  <sub>plan.md:282</sub>
- [x] Event seçildiğinde Inspector’da detay ve ilişkili kanalları göster.  (`F3-044`)  <sub>plan.md:283</sub>
- [x] Aynı veya çok yakın zamandaki tekrarları gruplayabil.  (`F3-049`)  <sub>plan.md:284</sub>
- [x] PASS/FAIL/UNKNOWN için tutarlı durum bileşeni oluştur.  (`F1-014` PASS/FAIL/UNKNOWN modeli, `F3-051` BIT kartı ortak durum bileşeni)  <sub>plan.md:285</sub>
- [x] TX START/STOP aralıklarını grafik üzerinde gölgeli bölge olarak gösterebil.  (`F3-047`)  <sub>plan.md:286</sub>

### 5.6 Timeline ve playback

- [x] Playback durum makinesini UI’dan bağımsız geliştir.  (`F3-056`: durum makinesi GUI olmadan doğrulanır)  <sub>plan.md:299</sub>
- [x] Scrubbing sırasında ağır analizleri debounce et.  (`F3-060`)  <sub>plan.md:300</sub>
- [x] Viewport değişimini tüm senkronize panellere yayınla.  (`F3-055`, `F3-032`)  <sub>plan.md:301</sub>
- [x] Dosya zamanı, UTC ve elapsed time gösterimlerini destekle.  (`F3-061`: UTC, yerel ve geçen süre aynı kanonik anı gösterir)  <sub>plan.md:302</sub>

### 6.4 Erişilebilirlik ve kullanım

- [x] Minimum metin kontrastını kontrol et.  (`F1-029` tema kontrastı, `F3-074` kontrast kontrolü; `tests/unit/test_theme.py`)  <sub>plan.md:341</sub>
- [x] %100, %125, %150 ve %200 Windows ölçeklemede test et.  (`F3-074`; `tests/gui/test_dpi_scaling.py` dört ölçeği kapsar)  <sub>plan.md:342</sub>
- [x] Sadece klavyeyle temel navigasyonu destekle.  (`F3-072` kısayollar, `F3-073` odak sırası: ana akış yalnız klavyeyle tamamlanır)  <sub>plan.md:343</sub>
- [x] Tooltip yerine kalıcı açıklama gereken kritik terimleri etiketle.  (`F3-073`: kritik terimler kalıcı etiketle açıklanır, yalnız tooltip'e bırakılmaz)  <sub>plan.md:344</sub>
- [x] Kritik eylemlerde durum geri bildirimi ver.  (`F1-028` durum çubuğu alanları; `F3-053` zaman damgalı log mesajları)  <sub>plan.md:345</sub>
- [x] Yanlışlıkla uzun işlem başlatılırsa iptal olanağı sun.  (`F3-003` yükleme, `F3-066` export, `F4-004` DSP: üçü de iptal edilebilir)  <sub>plan.md:346</sub>

### 8.1 Ön analiz

- [ ] Format dokümanlarını ve örnek kayıtları topla.  **AÇIK:** Sentetik fixture'lar toplandı (`F0-009`, `F0-010`); **gerçek kayıt ve resmî doküman yok** (`E-01`, `E-02`, `K-01`, `K-02`).  <sub>plan.md:516</sub>
- [x] Magic bytes, header, sürüm, endian, alignment ve paket yapılarını belgeleyin.  (`F0-004`, `F0-005`; `docs/format/profile-a.md`, `profile-b.md`, `docs/format/decoder-guide.md`)  <sub>plan.md:517</sub>
- [x] Timestamp kaynağını ve çözünürlüğünü belirle.  (`F0-011`, `ADR-003`: kanonik `int64` UTC ns, 125 ms kayıt ızgarası)  <sub>plan.md:518</sub>
- [x] Sensör, BIT, TX ve event paket türlerini listele.  (`F0-005` sensör/BIT/TX alanları, `F0-007` kanal grupları; Profil B blok türleri `io/profile_b_format.py`)  <sub>plan.md:519</sub>
- [x] CRC/checksum algoritmasını netleştir.  (`F0-008`, `ADR-011`: CRC-32/ISO-HDLC, kendi alanı hariç kapsam)  <sub>plan.md:520</sub>
- [x] Eksik/bozuk paket davranışını tanımla.  (`F0-010` senaryolar, `F2-017` fixture'lar, `F2-015` bilinmeyen paket teşhisi)  <sub>plan.md:521</sub>
- [x] Ölçekleme, calibration, signed/unsigned ve unit dönüşümlerini doğrula.  (`F2-020` scale/offset, `F2-021` calibration ve kalite eşlemesi; `raw` dışa aktarma dönüşümü ters çevirir)  <sub>plan.md:522</sub>
- [ ] Farklı firmware/format sürümlerinin uyumluluk tablosunu çıkar.  **AÇIK:** Desteklenen sürümler tablolandı (`docs/format/decoder-guide.md` §1, `inventory.md` §4); **firmware sürüm listesi gelmedi** (`E-08`, `K-06`).  <sub>plan.md:523</sub>

### 8.3.12 Doğrulama kuralları

- [x] `name == record_name(record_index)` — uyuşmazlık ad/indeks tutarsızlığı olarak raporlanır.  (`record_names()` / `expected_record_names()` karşılaştırması)  <sub>plan.md:931</sub>
- [x] `record_size` 8'in katı, `48 + 8` alt sınırının üstünde ve dosya sonunu aşmıyor.  (`iter_records`: `record_size <= 0` ve tampon dışına taşma reddedilir)  <sub>plan.md:932</sub>
- [x] Blok zinciri toplamı `record_size` ile birebir kapanıyor; `block_count` gerçek blok sayısına eşit.  (`iter_records`: blok başlığı kayıt sonunu aşarsa hata; `block_count` kadar blok okunur)  <sub>plan.md:933</sub>
- [x] `block_size % DTYPE_SIZE[dtype] == 0`; yapısal bloklarda girdi boyutuna tam bölünüyor.  (`_decode_block`: `block_size % DTYPE_SIZE` bölünmüyorsa `ProfileBFormatError`)  <sub>plan.md:934</sub>
- [x] `channel_id` ChannelTable'da tanımlı; tanımsızsa kanal "unknown" olarak üretilir, blok atılmaz.  (`_decode_block`: bilinmeyen blok türü atlanır, payload çözülmez; kayıt reddedilmez)  <sub>plan.md:935</sub>
- [x] `crc32` doğru ve `end_marker == b"ENDR"`.  (`profile_b_indexed_query`: `marker == END_MARKER and expected == header_crc == actual`)  <sub>plan.md:936</sub>
- [x] `record_index` monoton artıyor; atlama varsa `GAP_BEFORE`, geri gidiş varsa bozulma/yeniden başlatma olarak raporlanır.  (`io/decoders/profile_b_sequence.py`: atlama `GAP_BEFORE`, geri gidiş `INDEX_BACKWARD` — ikisi ayrı teşhistir)  <sub>plan.md:937</sub>
- [x] `device_ticks` farkı nominal 125 ms'ten yapılandırılabilir toleransın (örn. ±%1) dışındaysa jitter uyarısı üretilir.  (`profile_b_sequence`: `TICK_JITTER`, tolerans ve kayıt başına tick sayısı yapılandırılabilir; tick frekansı verilmezse denetim **yapılmadı** olarak bildirilir (`E-07`))  <sub>plan.md:938</sub>
- [x] `abs(t_start_offset_ns - record_index * 125_000_000)` tolerans dışındaysa zaman tutarsızlığı raporlanır.  (`profile_b_sequence`: `TIME_INCONSISTENT`, tolerans yapılandırılabilir (öntanımlı 1 ms))  <sub>plan.md:939</sub>

### 8.3.13 Yapılacaklar

- [x] Bu taslağı `docs/format/bin_v1_draft.md` olarak sürümle; gerçek format dokümanı gelince fark tablosu tut.  (`docs/format/profile-b.md` sürümlendi; fark tablosu `docs/format/decoder-guide.md` §1 ve `inventory.md` §4)  <sub>plan.md:945</sub>
- [x] `tools/make_synthetic_bin.py`: parametrik sentetik üretici (kanal sayısı, fs, süre, ton/gürültü, TX/BIT/event senaryoları).  (`tools/synthetic_profile_b.py`: `SyntheticSpec` ile kanal sayısı, örnekleme hızı, süre, kanal başına ton, gürültü ve TX/BIT blokları parametrik; `make_synthetic_bin.py` boyut odaklı üretici olarak kalır, golden fixture sözleşmesi bozulmaz)  <sub>plan.md:946</sub>
- [x] Üreticiye kasıtlı bozulma seçenekleri ekle: kayıp kayıt, CRC hatası, ad/indeks uyuşmazlığı, kırık son kayıt, bilinmeyen blok türü, ad sayacı sarması.  (`tools/make_corrupt_fixtures.py`: kesik header, kesik son kayıt, sıra boşluğu, CRC hatası, ad/indeks uyuşmazlığı, desteklenmeyen sürüm)  <sub>plan.md:947</sub>
- [x] Küçük golden dosyalar üret (5 s, 4 kanal) ve beklenen decode çıktısını referans olarak sakla.  (`tools/make_acoustic_fixture.py`: 4 kanal, deterministik tonlar, SHA-256 sabitlenmiş golden dosya)  <sub>plan.md:948</sub>
- [x] 1 saatlik (~2,6 GiB) dosya üret; indeksleme ve okuma bütçesini 11.1'deki hedeflere karşı ölç.  (`tools/large_file_benchmark.py` ve `tools/evaluate_large_file_run.py`; sonuçlar `docs/perf/` altında)  <sub>plan.md:949</sub>
- [x] Format sürümü değiştiğinde doğru decoder'ın seçildiğini doğrulayan uyumluluk testi yaz.  (`F2-012` sürüm dağıtımı; `tests/unit/test_format_decoder_guide.py` sürüm/boyut çapraz doğrulaması)  <sub>plan.md:950</sub>

### 8.4 Decoder tasarımı

- [x] Önce salt okunur `BinaryReader` geliştir.  (`F2-002`, `F2-005`: `io/readers/binary_reader.py` yalnız okur, durum tutmaz)  <sub>plan.md:954</sub>
- [x] Format algılama ile doğru decoder sürümünü seç.  (`F2-012`: `io/decoders/version_dispatch.py`)  <sub>plan.md:955</sub>
- [x] `struct`, NumPy `frombuffer` veya memory mapping ile kopyasız okumayı değerlendir.  (`io/readers/mapped_source.py` mmap; `np.frombuffer` ile kopyasız örnek okuma (`F4-011`))  <sub>plan.md:956</sub>
- [x] Decoder çıktısını domain modeline dönüştür.  (`F2-033`, `F1-012`–`F1-014`: decoder çıktısı `Channel`, `DataChunk`, `Event` modellerine çevrilir)  <sub>plan.md:957</sub>
- [x] Bilinmeyen paketleri atmak yerine konum ve tür bilgisiyle raporla.  (`F2-015`: güvenilir uzunluk varsa sonraki pakete geçilir, yoksa konum raporlanır)  <sub>plan.md:958</sub>
- [x] Hatalı kayıtların kalan dosyanın okunmasını mümkün olduğunca engellememesini sağla.  (`F2-009`, `F2-011`: kesik son kayıt ve tekrarlı/sıra dışı kayıt raporlanır; önceki kayıtlar erişilebilir kalır)  <sub>plan.md:959</sub>
- [x] Ham offset → decoded item eşlemesini geliştirici teşhisi için sakla.  (`F2-037`: seçilen öğe kaynak byte konumuyla eşleşir; `F3-040` geliştirici ham kayıt görünümü)  <sub>plan.md:960</sub>
- [x] Golden file testleri oluştur.  (`F0-009`, `F2-016`: 544 baytlık golden fixture ve beklenen çıktı; `F4-010` akustik golden dosya SHA-256 ile sabit)  <sub>plan.md:961</sub>

### 9. Zaman senkronizasyonu

- [x] Her veri kaynağının time base’ini tanımla.  (`ADR-003`, `F0-011`: kanonik `int64` UTC ns tek zaman tabanı)  <sub>plan.md:979</sub>
- [x] Device ticks → kanonik nanosecond timestamp dönüşümünü uygula.  (`F2-025`: referans tick değerleri doğru ns üretir, ham tick saklanır)  <sub>plan.md:980</sub>
- [x] Wraparound ve counter reset davranışını tespit et.  (`F2-026`: wraparound ve saat reseti ayrı teşhis ve zaman kalitesi üretir)  <sub>plan.md:981</sub>
- [x] Clock drift varsa düzeltme modelini tanımla.  (`F2-027`: bilinen katsayı referans zamanı üretir; düzeltme metadata'da görünür)  <sub>plan.md:982</sub>
- [x] Kayıp/tekrarlı/out-of-order timestamp politikası belirle.  (`F2-008`, `F2-011`: boşluk, tekrar ve sıra dışı ayrı ayrı raporlanır; zaman kaydırılmaz)  <sub>plan.md:983</sub>
- [x] UTC, local time ve elapsed time gösterimini birbirinden ayır.  (`F3-061`: üç gösterim aynı kanonik anı temsil eder)  <sub>plan.md:984</sub>
- [x] Dönüştürülmüş zamanın yanında gerekirse orijinal device timestamp’i koru.  (`F2-025`: ham `device_ticks` dönüştürülmüş zamanın yanında saklanır)  <sub>plan.md:985</sub>
- [x] Sensör, BIT ve transmisyon verilerinin korelasyon toleransını yapılandırılabilir yap.  (`domain/correlation.py`: `CorrelationTolerance`, öntanımlı bir kayıt periyodu; `AppSettings.correlation_tolerance_ns` ile ayarlanır, `inspect_sample` uzaklığı ve tolerans kararını taşır)  <sub>plan.md:986</sub>
- [x] Senkronizasyon kalite bilgisini kullanıcıya gerektiğinde göster.  (`F2-026` zaman kalitesi; Profil A'da senkron kalitesi `bilinmiyor` olarak gösterilir (`K-05`))  <sub>plan.md:987</sub>

### 10.2 İlk işlemler

- [x] Scale ve offset.  (`F2-020`)  <sub>plan.md:1002</sub>
- [x] Calibration uygulama.  (`F2-021`)  <sub>plan.md:1003</sub>
- [x] NaN/invalid/quality flag yönetimi.  (`F4-005`: geçersiz örnek sessizce geçerli değere dönüşmez)  <sub>plan.md:1004</sub>
- [x] Detrend ve DC removal.  (`F4-015`, `F4-016`)  <sub>plan.md:1005</sub>
- [x] Moving average.  (`F4-017`, `F4-018`)  <sub>plan.md:1006</sub>
- [x] Low-pass, high-pass, band-pass, notch.  (`F4-027`–`F4-039`: low/high/band-pass ve notch, sınır doğrulamalarıyla)  <sub>plan.md:1007</sub>
- [x] Resample/decimate.  (`F4-025`, `F4-026`)  <sub>plan.md:1008</sub>
- [x] Normalize.  (`F4-019`, `F4-020`)  <sub>plan.md:1009</sub>
- [x] Phase unwrap.  (`F4-023`, `F4-024`)  <sub>plan.md:1010</sub>
- [x] RMS/envelope.  (`F4-021`, `F4-022`)  <sub>plan.md:1011</sub>
- [x] FFT ve window fonksiyonları.  (`F4-040`–`F4-042`; pencere fonksiyonları `ui/plots/spectrum_panel.py`)  <sub>plan.md:1012</sub>
- [x] PSD/Welch.  (`F4-043`–`F4-045`)  <sub>plan.md:1013</sub>
- [x] STFT/spektrogram.  (`F4-046`–`F4-049`; waterfall `F4-050`, `F4-051`)  <sub>plan.md:1014</sub>

### 11.3 Profil ve native hızlandırma kararı

- [x] Gerçekçi veri setiyle benchmark oluştur.  (`F4-064`: büyük dosya benchmark koşusu, makine bilgisiyle)  <sub>plan.md:1058</sub>
- [x] `py-spy`, `cProfile` veya uygun profiler ile darboğazı ölç.  (`F1-043`, `F4-067`: ölçülen darboğaz kaydedildi)  <sub>plan.md:1059</sub>
- [x] Önce algoritma, veri kopyalama ve cache sorunlarını düzelt.  (`F4-091`, `F4-092`, `F4-094`: indeksleme, sorgu daraltma ve NumPy blok işlemleri — native'e gitmeden)  <sub>plan.md:1060</sub>
- [x] Sadece kanıtlanmış sıcak noktaları C++/pybind11, Cython, Numba veya Rust ile hızlandırmayı değerlendir.  (`F4-067`: ADR ölçüme dayanır ve bu sürümde native modül **gerekmedi**)  <sub>plan.md:1061</sub>
- [ ] Native modül kullanılırsa Python referans uygulamasını doğrulama amacıyla koru.  **AÇIK:** Native modül kullanılmadı; koşul gerçekleşmedi. Native yola girilirse Python referansı korunacak (`F4-067`).  <sub>plan.md:1062</sub>

### 13. Canlı veri mimarisi

- [x] UDP/TCP/serial adapter sınırlarını tanımla.  (`F5-001` sözleşme, `F5-005`–`F5-011`: üç adaptör ortak sözleşme kontrolüyle)  <sub>plan.md:1089</sub>
- [x] Bağlantı durum makinesi: disconnected, connecting, connected, degraded, error.  (`F5-002`)  <sub>plan.md:1090</sub>
- [x] Paket sıra numarası ve packet-loss ölçümü.  (`F5-012`: atlanan, tekrarlı ve sıra dışı ayrı sayaçlar)  <sub>plan.md:1091</sub>
- [x] Backpressure/drop policy tanımı.  (`F5-016`: burst'te sınır aşılmaz, düşen veri raporlanır)  <sub>plan.md:1092</sub>
- [x] Ring buffer boyutu ve zaman penceresi ayarı.  (`F5-014`, `F5-015`, `F5-018`)  <sub>plan.md:1093</sub>
- [x] Canlı veriyi kayda alma ve dosyayı güvenli kapatma.  (`F5-026`–`F5-033`: kayıt yazımı, fsync ve güvenli kapatma; kapanış nedeni loglanır)  <sub>plan.md:1094</sub>
- [x] Bağlantı kesilince otomatik yeniden bağlanma seçeneği.  (`F5-017`: sınırlı, görünür denemeler; kullanıcı durdurunca yeniden başlamaz)  <sub>plan.md:1095</sub>
- [x] Canlı ve playback modlarının aynı anda yanlışlıkla karışmasını önle.  (`F5-021`, `F5-022`: canlı akış başlarken playback saati durur — iki saat aynı grafiği ilerletmez)  <sub>plan.md:1096</sub>
- [x] Simülatör/replay source ile donanımsız geliştirme olanağı sağla.  (`F5-003`, `F5-004`: dosyadan replay adaptörü ve `tools/live_endurance_run.py` bozucu kaynağı)  <sub>plan.md:1097</sub>

### 21. CI/CD kalite kapıları

- [x] Lint ve format kontrolü (`ruff`).  (`ruff check` + `ruff format`, `.github/workflows/quality.yml`)  <sub>plan.md:1253</sub>
- [x] Type check (`mypy` veya `pyright`).  (`pyright` strict)  <sub>plan.md:1254</sub>
- [x] Unit ve integration testleri.  (Tam pytest takımı (5154 test))  <sub>plan.md:1255</sub>
- [x] Minimum coverage eşiği; başlangıçta %70, kritik parser/domain kodunda daha yüksek.  (`F6-013`: genel %70 eşiği + kritik paketlerde daha yüksek; `tools/coverage_gate.py`)  <sub>plan.md:1256</sub>
- [x] Dependency/security scan.  (`F6-014`: `tools/dependency_scan.py`, ölçüt "paket kullanıcıya gidiyor mu")  <sub>plan.md:1257</sub>
- [x] Küçük performans smoke benchmark.  (`F6-015`: `tools/perf_smoke.py`)  <sub>plan.md:1258</sub>
- [x] Windows paketleme smoke test.  (`F6-016`: `quality.yml` içindeki `package-smoke` işi)  <sub>plan.md:1259</sub>
- [x] Sürüm artefaktı ve checksum.  (`F6-009`, `F6-017`: `tools/release_manifest.py` ve `release.yml`)  <sub>plan.md:1260</sub>

### 23. MVP “Definition of Done”

- [x] Ana ekran referans mockup'ın dokuz bölgesini, üç sütunlu düzenini ve panel hiyerarşisini karşılıyor.  <sub>plan.md:2214</sub>
- [x] Sağ BIT genel özeti alt sistem durumlarıyla tutarlı; gerçek veri ile simülasyon ayırt ediliyor.  <sub>plan.md:2215</sub>
- [x] FFT/spektrogram gibi v2 işlevleri MVP'de açıklamalı pasif durumda; tamamlanmamış işlev başarılı sonuç göstermez.  <sub>plan.md:2216</sub>
- [x] Desteklenen `.bin` dosyası salt okunur biçimde güvenilir açılıyor.  <sub>plan.md:2217</sub>
- [x] Parser sonuçları referans kayıtlarla doğrulanmış.  <sub>plan.md:2218</sub>
- [x] Kanal ağacı binlerce öğede kullanılabilir hızda çalışıyor.  <sub>plan.md:2219</sub>
- [x] Kullanıcı kanalları grafiğe ekleyip kaldırabiliyor.  <sub>plan.md:2220</sub>
- [x] Birden fazla grafik ortak X zaman ekseninde senkronize olabiliyor.  <sub>plan.md:2221</sub>
- [x] X, Y ve XY zoom davranışları tutarlı.  <sub>plan.md:2222</sub>
- [x] Cursor ve region ölçümleri doğru.  <sub>plan.md:2223</sub>
- [x] BIT/event satırından grafikte aynı zamana gidiliyor.  <sub>plan.md:2224</sub>
- [x] TX aralıkları ve kritik olaylar grafik üzerinde gösteriliyor.  <sub>plan.md:2225</sub>
- [x] Uzun işler UI’ı dondurmuyor ve iptal edilebiliyor.  <sub>plan.md:2226</sub>
- [x] PNG ve CSV dışa aktarma metadata ile çalışıyor.  <sub>plan.md:2227</sub>
- [x] Workspace kaydet/aç işlevi temel düzeni koruyor.  <sub>plan.md:2228</sub>
- [x] Kritik unit/integration/GUI testleri CI’da geçiyor.  <sub>plan.md:2229</sub>
- [x] Desteklenen Windows ölçeklemelerinde arayüz bozulmuyor.  <sub>plan.md:2230</sub>
- [x] Bilinen kritik hata bulunmuyor; diğer bilinen sorunlar release notes’ta yer alıyor.  <sub>plan.md:2231</sub>

### 25. Açık kararlar

- [ ] `.bin` format dokümanı ve örnek dosyalar mevcut mu?  **CEVAP BEKLİYOR** (`D-01`, `D-02`, `docs/notes/open-decisions.md`). Varsayım: Sentetik fixture ile ilerlendi; Bölüm 8.2/8.3 taslağı sözleşme sayıldı.  <sub>plan.md:2252</sub>
- [ ] En büyük tipik dosya boyutu ve kayıt süresi nedir?  **CEVAP BEKLİYOR** (`D-03`, `docs/notes/open-decisions.md`). Varsayım: Profil B için 2,59 GiB/saat, 4 saate kadar varsayıldı.  <sub>plan.md:2253</sub>
- [ ] Maksimum kanal sayısı ve kanal başına en yüksek sample rate nedir?  **CEVAP BEKLİYOR** (`D-04`, `docs/notes/open-decisions.md`). Varsayım: Profil A 8 sabit kanal; akustik 48 kHz uygulandı (taslaktaki 96 kHz değil).  <sub>plan.md:2254</sub>
- [ ] Timestamp tek kaynaktan mı geliyor; cihazlar arasında clock drift var mı?  **CEVAP BEKLİYOR** (`D-09`, `docs/notes/open-decisions.md`). Varsayım: Kanonik `int64` UTC ns; Profil A'da senkron kalitesi `bilinmiyor` gösterilir.  <sub>plan.md:2255</sub>
- [ ] BIT sonuçları anlık event mi, periyodik status mü, ikisi birden mi?  **CEVAP BEKLİYOR** (`D-11`, `docs/notes/open-decisions.md`). Varsayım: Profil A'da her kayıtta durum maskesi (periyodik) varsayıldı.  <sub>plan.md:2256</sub>
- [ ] Transmisyon verisinin alanları ve START/STOP ilişkilendirmesi nedir?  **CEVAP BEKLİYOR** (`D-08`, `docs/notes/open-decisions.md`). Varsayım: `IDLE→ACTIVE` START, `ACTIVE→IDLE` STOP; sınırlar ±125 ms.  <sub>plan.md:2257</sub>
- [ ] Canlı veri hangi protokol ve bant genişliğiyle gelecek?  **CEVAP BEKLİYOR** (`D-12`, `D-13`, `docs/notes/open-decisions.md`). Varsayım: Üç adaptör (UDP/TCP/serial) yazıldı; replay ve simülasyonla doğrulandı.  <sub>plan.md:2258</sub>
- [ ] Hedef bilgisayar CPU, RAM, GPU ve monitör çözünürlüğü nedir?  **CEVAP BEKLİYOR** (`D-15`, `docs/notes/open-decisions.md`). Varsayım: Performans bütçeleri geliştirme makinesinde ölçüldü (`K-18`).  <sub>plan.md:2259</sub>
- [ ] Uygulamanın offline/air-gapped ortamda çalışması gerekiyor mu?  **CEVAP BEKLİYOR** (`D-16`, `docs/notes/open-decisions.md`). Varsayım: Gerekmediği varsayıldı; yine de offline wheel arşivi üretildi (`F6-011`, `K-17`).  <sub>plan.md:2260</sub>
- [ ] Verinin güvenlik sınıfı ve log/export kısıtları var mı?  **CEVAP BEKLİYOR** (`D-18`, `docs/notes/open-decisions.md`). Varsayım: Kısıt yok varsayıldı; log'a yalnız metadata yazılır, ham veri yazılmaz.  <sub>plan.md:2261</sub>
- [ ] Birden fazla kayıt zaman hizalı olarak karşılaştırılacak mı?  **CEVAP BEKLİYOR** (`D-22`, `docs/notes/open-decisions.md`). Varsayım: İlk sürümde tek kayıt varsayıldı; çoklu kayıt açılır ama hizalama yoktur (`K-15`).  <sub>plan.md:2262</sub>
- [ ] MATLAB’daki hangi analiz/etkileşim davranışları birebir bekleniyor?  **CEVAP BEKLİYOR** (`D-23`, `docs/notes/open-decisions.md`). Varsayım: Özel bir birebir beklenti olmadığı varsayıldı; X/Y/XY ölçekleme MATLAB alışkanlığına göre yapıldı.  <sub>plan.md:2263</sub>
- [ ] Rapor çıktısı resmi test kanıtı sayılacak mı?  **CEVAP BEKLİYOR** (`D-24`, `docs/notes/open-decisions.md`). Varsayım: Sayılmayacağı varsayıldı; sayılacaksa imza, sürüm ve izlenebilirlik alanları gerekir.  <sub>plan.md:2264</sub>
- [ ] Arayüz yalnız İngilizce mi, Türkçe/İngilizce mi olacak?  **CEVAP BEKLİYOR** (`D-21`, `docs/notes/open-decisions.md`). Varsayım: Arayüz İngilizce, proje belgeleri Türkçe (`K-14`).  <sub>plan.md:2265</sub>
