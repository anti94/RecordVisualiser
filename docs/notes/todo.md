# Todo — plan.md'den üretilmiştir

> **Bu dosya elle düzenlenmez.** Kaynak `plan.md`'dir.
> Bir işi tamamlayınca `plan.md`'deki kutuyu `[x]` yap ve
> `python tools/sync_todo.py` çalıştır.

**Toplam 492 madde · 33 tamamlandı · 459 kaldı**

`[##......................]` %6.7

## Özet

| Grup | Tamam | Kalan | Toplam |
| --- | --- | --- | --- |
| Faz 0 — Keşif ve format sözleşmesi | 17 | 0 | 17 |
| Faz 1 — Uygulama iskeleti ve domain modeli | 16 | 28 | 44 |
| Faz 2 — Parser, indeks ve kayıtlı veri | 0 | 41 | 41 |
| Faz 3 — MVP analiz arayüzü | 0 | 80 | 80 |
| Faz 4 — Mockup analiz panosu ve büyük veri performansı | 0 | 90 | 90 |
| Faz 5 — Canlı veri, bağlantı ve kayıt | 0 | 41 | 41 |
| Faz 6 — Windows dağıtımı ve ürünleştirme | 0 | 34 | 34 |
| Bölüm içi kontrol listeleri | 0 | 145 | 145 |
| **Toplam** | **33** | **459** | **492** |

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

### Faz 1 — Uygulama iskeleti ve domain modeli (16/44)

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
| [ ] | `F1-017` | `0.34.0` | 15 dk | LiveSource protokolünü tanımla |
| [ ] | `F1-018` | `0.35.0` | 15 dk | Deterministik sinüs üretecini ekle |
| [ ] | `F1-019` | `0.36.0` | 20 dk | Noise, chirp ve impulse örneklerini ekle |
| [ ] | `F1-020` | `0.37.0` | 20 dk | Sahte kanal repository uygulamasını ekle |
| [ ] | `F1-021` | `0.38.0` | 15 dk | Sahte BIT, TX ve sistem olaylarını ekle |
| [ ] | `F1-022` | `0.39.0` | 20 dk | Mockup'ın üç sütunlu ana pencere düzenini oluştur |
| [ ] | `F1-023` | `0.40.0` | 15 dk | Menü ve toolbar eylem iskeletini ekle |
| [ ] | `F1-024` | `0.41.0` | 15 dk | Data Explorer dock'unu ekle |
| [ ] | `F1-025` | `0.42.0` | 15 dk | Inspector'ı bağlamsal araç sekmesi olarak ekle |
| [ ] | `F1-026` | `0.43.0` | 15 dk | Alt Log/Messages alanı ve Events sekmesini ekle |
| [ ] | `F1-027` | `0.44.0` | 15 dk | Playback/Time Control şeridini yerleştir |
| [ ] | `F1-028` | `0.45.0` | 15 dk | Durum çubuğu alanlarını ekle |
| [ ] | `F1-029` | `0.46.0` | 20 dk | Mockup koyu temasını ve mavi vurgularını uygula |
| [ ] | `F1-030` | `0.47.0` | 20 dk | Durum ikonları ve kanal paletini ekle |
| [ ] | `F1-031` | `0.48.0` | 20 dk | Tek kanallı PlotPanel iskeletini ekle |
| [ ] | `F1-032` | `0.49.0` | 20 dk | Mock repository seçimini grafiğe bağla |
| [ ] | `F1-033` | `0.50.0` | 15 dk | Boş workspace yönlendirmesini ekle |
| [ ] | `F1-034` | `0.51.0` | 15 dk | Open .bin File düğmesi ve dosya özet kartını ekle |
| [ ] | `F1-035` | `0.52.0` | 15 dk | Sağ üst BIT/System Status kartını yerleştir |
| [ ] | `F1-036` | `0.53.0` | 15 dk | Analysis Tools kartının sekmelerini yerleştir |
| [ ] | `F1-037` | `0.54.0` | 15 dk | Sağ alt Data Export kartını yerleştir |
| [ ] | `F1-038` | `0.55.0` | 15 dk | Mockup ana analiz sekmelerini yerleştir |
| [ ] | `F1-039` | `0.56.0` | 20 dk | Merkez dashboard grafik hücrelerini oluştur |
| [ ] | `F1-040` | `0.57.0` | 15 dk | Grafik hızlı araç şeridini yerleştir |
| [ ] | `F1-041` | `0.58.0` | 20 dk | Bir ve on milyon noktalık spike girdilerini hazırla |
| [ ] | `F1-042` | `0.59.0` | 20 dk | Pan/zoom ve cursor ölçüm koşucusunu ekle |
| [ ] | `F1-043` | `0.60.0` | 20 dk | İlk spike sonuçlarını ve darboğazı kaydet |
| [ ] | `F1-044` | `0.61.0` | 15 dk | Uygulama iskeleti milestone kontrolünü yap |

### Faz 2 — Parser, indeks ve kayıtlı veri (0/41)

| | İş | Sürüm | Süre | Çıktı |
| --- | --- | --- | --- | --- |
| [ ] | `F2-001` | `0.62.0` | 15 dk | Header alan sabitlerini ve veri modelini ekle |
| [ ] | `F2-002` | `0.63.0` | 20 dk | Little-endian header okuyucusunu ekle |
| [ ] | `F2-003` | `0.64.0` | 15 dk | Magic ve sürüm doğrulamasını ekle |
| [ ] | `F2-004` | `0.65.0` | 20 dk | Eksik header ve boyut sınırlarını denetle |
| [ ] | `F2-005` | `0.66.0` | 20 dk | Tek Data kaydını çözümle |
| [ ] | `F2-006` | `0.67.0` | 20 dk | Ardışık kayıt iterator'unu ekle |
| [ ] | `F2-007` | `0.68.0` | 15 dk | 125 ms kayıt zamanını kanonik ns'ye dönüştür |
| [ ] | `F2-008` | `0.69.0` | 20 dk | Sıra ve zaman boşluklarını raporla |
| [ ] | `F2-009` | `0.70.0` | 15 dk | Kesik son kaydı raporlayarak okumayı bitir |
| [ ] | `F2-010` | `0.71.0` | 15 dk | Kayıt adı ve sıra numarası tutarlılığını denetle |
| [ ] | `F2-011` | `0.72.0` | 20 dk | Tekrarlı ve sıra dışı kayıtları raporla |
| [ ] | `F2-012` | `0.73.0` | 20 dk | Sürüme göre decoder seçimini ekle |
| [ ] | `F2-013` | `0.74.0` | 20 dk | Kararlaştırılmış CRC hesaplamasını ekle |
| [ ] | `F2-014` | `0.75.0` | 20 dk | CRC alanlı format doğrulamasını bağla |
| [ ] | `F2-015` | `0.76.0` | 20 dk | Bilinmeyen paket teşhisini ekle |
| [ ] | `F2-016` | `0.77.0` | 20 dk | 32/64 byte örnek fixture yazıcısını ekle |
| [ ] | `F2-017` | `0.78.0` | 20 dk | Kesik, bozuk ve sıra boşluklu fixture'ları ekle |
| [ ] | `F2-018` | `0.79.0` | 20 dk | CRC destekli format fixture'ını ekle |
| [ ] | `F2-019` | `0.80.0` | 20 dk | Sensör alanlarını kanal metadata'sına eşleştir |
| [ ] | `F2-020` | `0.81.0` | 20 dk | Scale ve offset dönüşümünü ekle |
| [ ] | `F2-021` | `0.82.0` | 20 dk | Calibration seçimini ve kalite eşlemesini ekle |
| [ ] | `F2-022` | `0.83.0` | 20 dk | BIT maskesini durum ve değişim olaylarına çevir |
| [ ] | `F2-023` | `0.84.0` | 20 dk | TX durumunu başlangıç/bitiş aralıklarına çevir |
| [ ] | `F2-024` | `0.85.0` | 15 dk | Parser teşhislerini sistem olaylarına çevir |
| [ ] | `F2-025` | `0.86.0` | 20 dk | Cihaz tick dönüşüm adaptörünü ekle |
| [ ] | `F2-026` | `0.87.0` | 20 dk | Wraparound ve saat resetini ayırt et |
| [ ] | `F2-027` | `0.88.0` | 20 dk | Tanımlı drift düzeltmesini uygula |
| [ ] | `F2-028` | `0.89.0` | 20 dk | Kayıt offseti ve zaman indeksini oluştur |
| [ ] | `F2-029` | `0.90.0` | 20 dk | Kanal ve olay indekslerini oluştur |
| [ ] | `F2-030` | `0.91.0` | 20 dk | Kaynak fingerprint ve parser sürümünü kaydet |
| [ ] | `F2-031` | `0.92.0` | 20 dk | İndeks dosyasını atomik kaydet |
| [ ] | `F2-032` | `0.93.0` | 20 dk | Geçerli indeksi yeniden kullan |
| [ ] | `F2-033` | `0.94.0` | 20 dk | Dosya metadata ve kanal listesini sun |
| [ ] | `F2-034` | `0.95.0` | 20 dk | İndeksli zaman aralığı sorgusunu ekle |
| [ ] | `F2-035` | `0.96.0` | 20 dk | Zaman ve kategoriye göre olay sorgula |
| [ ] | `F2-036` | `0.97.0` | 20 dk | Birden fazla kaydı ayrı kimlikle yönet |
| [ ] | `F2-037` | `0.98.0` | 15 dk | Decoded öğeden ham offsete erişim ekle |
| [ ] | `F2-038` | `0.99.0` | 15 dk | Okuyucu kaynaklarını güvenli kapat |
| [ ] | `F2-039` | `0.100.0` | 20 dk | Bağımsız golden sonuçlarını parser ile karşılaştır |
| [ ] | `F2-040` | `0.101.0` | 20 dk | Kaynak dosyanın değişmediğini doğrula |
| [ ] | `F2-041` | `0.102.0` | 15 dk | Parser milestone kabulünü kaydet |

### Faz 3 — MVP analiz arayüzü (0/80)

| | İş | Sürüm | Süre | Çıktı |
| --- | --- | --- | --- | --- |
| [ ] | `F3-001` | `0.103.0` | 15 dk | Tekli ve çoklu dosya açma seçicisini bağla |
| [ ] | `F3-002` | `0.104.0` | 20 dk | Dosya yükleme worker'ını ekle |
| [ ] | `F3-003` | `0.105.0` | 20 dk | Yükleme ilerlemesi ve iptal eylemini ekle |
| [ ] | `F3-004` | `0.106.0` | 20 dk | Eski istek sonucunun görünümü ezmesini önle |
| [ ] | `F3-005` | `0.107.0` | 20 dk | Dosya yükleme sonucunu repository ve ekrana bağla |
| [ ] | `F3-006` | `0.108.0` | 15 dk | Format ve dosya erişim hatalarını göster |
| [ ] | `F3-007` | `0.109.0` | 20 dk | Dosya kapatma ve bağlı panel temizliğini ekle |
| [ ] | `F3-008` | `0.110.0` | 15 dk | Son dosyalar ve varsayılan klasörü kaydet |
| [ ] | `F3-009` | `0.111.0` | 20 dk | Dosya ve kanal ağaç modelini ekle |
| [ ] | `F3-010` | `0.112.0` | 20 dk | Kanal ağacında lazy yüklemeyi ekle |
| [ ] | `F3-011` | `0.113.0` | 20 dk | Ad, ID, birim ve kaynak aramasını ekle |
| [ ] | `F3-012` | `0.114.0` | 15 dk | Channels/Data Tree sekmeleri ve kategori filtrelerini bağla |
| [ ] | `F3-013` | `0.115.0` | 20 dk | Çift tıkla kanalı grafiğe ekle |
| [ ] | `F3-014` | `0.116.0` | 15 dk | Grafikten kanal kaldırmayı ekle |
| [ ] | `F3-015` | `0.117.0` | 20 dk | Kanal sürükle-bırak akışını ekle |
| [ ] | `F3-016` | `0.118.0` | 20 dk | Çoklu kanal ekleme eylemlerini ekle |
| [ ] | `F3-017` | `0.119.0` | 20 dk | Favori kanal gruplarını kaydet |
| [ ] | `F3-018` | `0.120.0` | 15 dk | Kanal sağ tık eylemlerini bağla |
| [ ] | `F3-019` | `0.121.0` | 20 dk | Ortak zaman ekseninde çoklu seri çiz |
| [ ] | `F3-020` | `0.122.0` | 20 dk | Farklı birimler için ikinci Y ekseni ekle |
| [ ] | `F3-021` | `0.123.0` | 15 dk | Pan etkileşimini bağla |
| [ ] | `F3-022` | `0.124.0` | 15 dk | Yalnız X zoom modunu ekle |
| [ ] | `F3-023` | `0.125.0` | 15 dk | Yalnız Y zoom modunu ekle |
| [ ] | `F3-024` | `0.126.0` | 15 dk | XY zoom modunu ekle |
| [ ] | `F3-025` | `0.127.0` | 15 dk | Autoscale ve görünüm sıfırlamayı ekle |
| [ ] | `F3-026` | `0.128.0` | 20 dk | Crosshair ve cursor okumasını ekle |
| [ ] | `F3-027` | `0.129.0` | 20 dk | İki cursor fark ölçümünü ekle |
| [ ] | `F3-028` | `0.130.0` | 15 dk | Zaman bölgesi seçimini ekle |
| [ ] | `F3-029` | `0.131.0` | 15 dk | Seçili bölgeye yakınlaşmayı bağla |
| [ ] | `F3-030` | `0.132.0` | 20 dk | Legend gizleme ve solo eylemlerini ekle |
| [ ] | `F3-031` | `0.133.0` | 15 dk | Seri rengi, çizgi ve marker ayarını ekle |
| [ ] | `F3-032` | `0.134.0` | 20 dk | Paneller arasında X senkronizasyonunu ekle |
| [ ] | `F3-033` | `0.135.0` | 20 dk | Grafik tabı ve bölünmüş görünüm ekle |
| [ ] | `F3-034` | `0.136.0` | 15 dk | Panel kaynak sınırını ve kapatma temizliğini ekle |
| [ ] | `F3-035` | `0.137.0` | 15 dk | Seçili kanal metadata'sını Inspector'a bağla |
| [ ] | `F3-036` | `0.138.0` | 20 dk | Inspector görünüm ayarlarını grafiğe bağla |
| [ ] | `F3-037` | `0.139.0` | 20 dk | Count, min, max ve mean hesabını ekle |
| [ ] | `F3-038` | `0.140.0` | 20 dk | Median, RMS, std ve peak-to-peak ekle |
| [ ] | `F3-039` | `0.141.0` | 20 dk | ROI istatistiklerini dashboard kartına bağla |
| [ ] | `F3-040` | `0.142.0` | 20 dk | Geliştirici ham kayıt görünümünü ekle |
| [ ] | `F3-041` | `0.143.0` | 20 dk | Görünüm ayarları için undo/redo ekle |
| [ ] | `F3-042` | `0.144.0` | 20 dk | Ortak olay tablo modelini ekle |
| [ ] | `F3-043` | `0.145.0` | 20 dk | Zaman, severity, kaynak ve metin filtrelerini ekle |
| [ ] | `F3-044` | `0.146.0` | 15 dk | Olay seçimini Inspector detayına bağla |
| [ ] | `F3-045` | `0.147.0` | 20 dk | Olay zaman işaretlerini çiz |
| [ ] | `F3-046` | `0.148.0` | 20 dk | Olay çift tıklamasını ortak zamana bağla |
| [ ] | `F3-047` | `0.149.0` | 20 dk | TX aralıklarını gölgeli bölge olarak çiz |
| [ ] | `F3-048` | `0.150.0` | 15 dk | Transmission sekmesini TX aralıklarına bağla |
| [ ] | `F3-049` | `0.151.0` | 20 dk | Yakın tekrar olaylarını grupla |
| [ ] | `F3-050` | `0.152.0` | 15 dk | Marker ve TX görünürlüğü kontrollerini ekle |
| [ ] | `F3-051` | `0.153.0` | 20 dk | Sağ BIT kartını alt sistem durumlarına bağla |
| [ ] | `F3-052` | `0.154.0` | 15 dk | Run BIT Analysis eylemini kayıt analizine bağla |
| [ ] | `F3-053` | `0.155.0` | 15 dk | Yükleme ve analiz mesajlarını alt loga bağla |
| [ ] | `F3-054` | `0.156.0` | 20 dk | Kayıt geneli Timeline özetini çiz |
| [ ] | `F3-055` | `0.157.0` | 20 dk | Timeline viewport seçimini grafiğe bağla |
| [ ] | `F3-056` | `0.158.0` | 20 dk | Play, pause ve stop durum makinesini ekle |
| [ ] | `F3-057` | `0.159.0` | 20 dk | Kayıt zamanına göre ilerleme saatini ekle |
| [ ] | `F3-058` | `0.160.0` | 15 dk | Oynatma hızlarını bağla |
| [ ] | `F3-059` | `0.161.0` | 20 dk | Zamana ve önceki/sonraki olaya gitmeyi ekle |
| [ ] | `F3-060` | `0.162.0` | 20 dk | Scrubbing sorgularını debounce et |
| [ ] | `F3-061` | `0.163.0` | 15 dk | UTC, yerel ve geçen süre gösterimini ekle |
| [ ] | `F3-062` | `0.164.0` | 20 dk | Seçili grafiği PNG olarak dışa aktar |
| [ ] | `F3-063` | `0.165.0` | 20 dk | Seçili grafiği SVG olarak dışa aktar |
| [ ] | `F3-064` | `0.166.0` | 20 dk | Seçili kanal ve aralığı CSV olarak yaz |
| [ ] | `F3-065` | `0.167.0` | 20 dk | Export hedefi ve üzerine yazma kontrolünü ekle |
| [ ] | `F3-066` | `0.168.0` | 20 dk | Büyük export için worker ve iptal ekle |
| [ ] | `F3-067` | `0.169.0` | 20 dk | Sürümlü workspace JSON modelini ekle |
| [ ] | `F3-068` | `0.170.0` | 20 dk | Dock ve grafik düzenini kaydet |
| [ ] | `F3-069` | `0.171.0` | 20 dk | Workspace dosyasını geri yükle |
| [ ] | `F3-070` | `0.172.0` | 20 dk | Eksik kaynak ve bozuk workspace davranışını ekle |
| [ ] | `F3-071` | `0.173.0` | 20 dk | Workspace sürüm geçiş yolunu ekle |
| [ ] | `F3-072` | `0.174.0` | 20 dk | Bölüm 16 klavye kısayollarını bağla |
| [ ] | `F3-073` | `0.175.0` | 20 dk | Klavye odak sırasını ve açıklamaları düzenle |
| [ ] | `F3-074` | `0.176.0` | 20 dk | Windows ölçekleme ve kontrast kontrolünü kaydet |
| [ ] | `F3-075` | `0.177.0` | 20 dk | Dosyadan olay gezinmesine entegrasyon senaryosu ekle |
| [ ] | `F3-076` | `0.178.0` | 20 dk | Kritik plot ve workspace GUI kontrollerini ekle |
| [ ] | `F3-077` | `0.179.0` | 20 dk | MVP etkileşim bütçesini ölç |
| [ ] | `F3-078` | `0.180.0` | 20 dk | Operatör ve mühendis MVP senaryolarını kaydet |
| [ ] | `F3-079` | `0.181.0` | 20 dk | MVP ekran görüntüsünü ana mockup ile karşılaştır |
| [ ] | `F3-080` | `1.0.0` | 15 dk | MVP kabulünü kapat ve major sürümü hazırla |

### Faz 4 — Mockup analiz panosu ve büyük veri performansı (0/90)

| | İş | Sürüm | Süre | Çıktı |
| --- | --- | --- | --- | --- |
| [ ] | `F4-001` | `1.1.0` | 20 dk | İşlem adımı ve parametre modelini ekle |
| [ ] | `F4-002` | `1.2.0` | 20 dk | Sıralı işlem zinciri yürütücüsünü ekle |
| [ ] | `F4-003` | `1.3.0` | 20 dk | DSP işlerini worker üzerinden çalıştır |
| [ ] | `F4-004` | `1.4.0` | 20 dk | DSP iptal ve eski sonuç denetimini ekle |
| [ ] | `F4-005` | `1.5.0` | 20 dk | NaN ve kalite bayrağı politikasını uygula |
| [ ] | `F4-006` | `1.6.0` | 20 dk | Analysis Tools işlem listesi editörünü ekle |
| [ ] | `F4-007` | `1.7.0` | 20 dk | Analiz parametre hatalarını alanlarda göster |
| [ ] | `F4-008` | `1.8.0` | 15 dk | Seçili kanala uygulama ve filtreli veri görünümünü bağla |
| [ ] | `F4-009` | `1.9.0` | 20 dk | Ham akustik blok formatının ayrı sürümünü tanımla |
| [ ] | `F4-010` | `1.10.0` | 20 dk | 48 kHz akustik blok fixture üretecini ekle |
| [ ] | `F4-011` | `1.11.0` | 20 dk | Akustik blok payload decoder'ını ekle |
| [ ] | `F4-012` | `1.12.0` | 20 dk | Blok içi örnek zamanlarını üret |
| [ ] | `F4-013` | `1.13.0` | 20 dk | Akustik blokları zaman sorgusuna bağla |
| [ ] | `F4-014` | `1.14.0` | 20 dk | Akustik boyut ve sample rate sınırlarını doğrula |
| [ ] | `F4-015` | `1.15.0` | 20 dk | Detrend ve DC kaldırma hesabını ekle |
| [ ] | `F4-016` | `1.16.0` | 15 dk | Detrend türü seçimini işlem editörüne bağla |
| [ ] | `F4-017` | `1.17.0` | 20 dk | Moving average hesabını ekle |
| [ ] | `F4-018` | `1.18.0` | 15 dk | Moving average pencere kontrolünü bağla |
| [ ] | `F4-019` | `1.19.0` | 20 dk | Normalize hesabını ekle |
| [ ] | `F4-020` | `1.20.0` | 15 dk | Normalize seçimini işlem editörüne bağla |
| [ ] | `F4-021` | `1.21.0` | 20 dk | Pencereli RMS ve envelope hesabını ekle |
| [ ] | `F4-022` | `1.22.0` | 15 dk | RMS/envelope pencere kontrollerini bağla |
| [ ] | `F4-023` | `1.23.0` | 20 dk | Phase unwrap hesabını ekle |
| [ ] | `F4-024` | `1.24.0` | 15 dk | Phase unwrap parametrelerini bağla |
| [ ] | `F4-025` | `1.25.0` | 20 dk | Resample/decimate işlemini ekle |
| [ ] | `F4-026` | `1.26.0` | 15 dk | Resample hedef frekans kontrolünü bağla |
| [ ] | `F4-027` | `1.27.0` | 20 dk | Low-pass filtre hesabını ekle |
| [ ] | `F4-028` | `1.28.0` | 15 dk | Low-pass cutoff ve order sınırlarını doğrula |
| [ ] | `F4-029` | `1.29.0` | 15 dk | Low-pass araç alanlarını bağla |
| [ ] | `F4-030` | `1.30.0` | 20 dk | High-pass filtre hesabını ekle |
| [ ] | `F4-031` | `1.31.0` | 15 dk | High-pass sınır ve transient davranışını doğrula |
| [ ] | `F4-032` | `1.32.0` | 15 dk | High-pass seçimini araç kartına bağla |
| [ ] | `F4-033` | `1.33.0` | 20 dk | Band-pass filtre hesabını ekle |
| [ ] | `F4-034` | `1.34.0` | 15 dk | Band-pass alt/üst sınırlarını doğrula |
| [ ] | `F4-035` | `1.35.0` | 15 dk | Band-pass iki cutoff alanını bağla |
| [ ] | `F4-036` | `1.36.0` | 20 dk | Notch filtre hesabını ekle |
| [ ] | `F4-037` | `1.37.0` | 15 dk | Notch frekans ve Q sınırlarını doğrula |
| [ ] | `F4-038` | `1.38.0` | 15 dk | Notch frekans ve Q kontrollerini bağla |
| [ ] | `F4-039` | `1.39.0` | 20 dk | Window üretimi ve normalizasyonunu ekle |
| [ ] | `F4-040` | `1.40.0` | 20 dk | Tek taraflı FFT hesabını ekle |
| [ ] | `F4-041` | `1.41.0` | 20 dk | FFT, dB ve Nyquist doğrulamalarını ekle |
| [ ] | `F4-042` | `1.42.0` | 20 dk | Seçili aralık FFT'sini mockup alt grafiğine bağla |
| [ ] | `F4-043` | `1.43.0` | 20 dk | Welch PSD hesabını ekle |
| [ ] | `F4-044` | `1.44.0` | 15 dk | PSD pencere, overlap ve birim sınırlarını doğrula |
| [ ] | `F4-045` | `1.45.0` | 20 dk | Spectrum sekmesinde PSD görünümünü ekle |
| [ ] | `F4-046` | `1.46.0` | 20 dk | STFT ve spektrogram matrisini hesapla |
| [ ] | `F4-047` | `1.47.0` | 20 dk | STFT kenar, overlap ve eksen eşlemesini doğrula |
| [ ] | `F4-048` | `1.48.0` | 20 dk | Mockup orta spektrogramını sonuçlara bağla |
| [ ] | `F4-049` | `1.49.0` | 15 dk | Spektrogram renk ölçeği kontrollerini ekle |
| [ ] | `F4-050` | `1.50.0` | 20 dk | Waterfall zaman dilimi modelini ekle |
| [ ] | `F4-051` | `1.51.0` | 20 dk | Waterfall görünümünü ekle |
| [ ] | `F4-052` | `1.52.0` | 20 dk | Zaman serisi, STFT, FFT ve istatistiği birlikte bağla |
| [ ] | `F4-053` | `1.53.0` | 20 dk | Memory mapping üzerinden blok okuma ekle |
| [ ] | `F4-054` | `1.54.0` | 20 dk | Yalnız görünür zaman bloklarını yükle |
| [ ] | `F4-055` | `1.55.0` | 20 dk | Piksel genişliğine göre max_points uygula |
| [ ] | `F4-056` | `1.56.0` | 20 dk | Min/max envelope downsampling ekle |
| [ ] | `F4-057` | `1.57.0` | 20 dk | Çok seviyeli özet bloklarını üret |
| [ ] | `F4-058` | `1.58.0` | 20 dk | Viewport için uygun özet seviyesini seç |
| [ ] | `F4-059` | `1.59.0` | 20 dk | Bellek sınırlı LRU cache ekle |
| [ ] | `F4-060` | `1.60.0` | 20 dk | Cache anahtarına kaynak ve işlem sürümünü ekle |
| [ ] | `F4-061` | `1.61.0` | 20 dk | Render sıklığını ve gizli panel güncellemelerini sınırla |
| [ ] | `F4-062` | `1.62.0` | 20 dk | Sorgu, render ve indeks sürelerini kaydet |
| [ ] | `F4-063` | `1.63.0` | 20 dk | Büyük dosya üretim koşusunu hazırla |
| [ ] | `F4-064` | `1.64.0` | 20 dk | Büyük dosya benchmark koşusunu hazırla |
| [ ] | `F4-065` | `1.65.0` | 20 dk | Büyük dosya koşusunun sonuçlarını değerlendir |
| [ ] | `F4-066` | `1.66.0` | 20 dk | İndeks kesintisi ve cache kurtarmayı doğrula |
| [ ] | `F4-067` | `1.67.0` | 15 dk | Profil sonucuyla native hızlandırma ADR'sini yaz |
| [ ] | `F4-068` | `1.68.0` | 20 dk | DerivedChannelDefinition modelini ekle |
| [ ] | `F4-069` | `1.69.0` | 20 dk | Türetilmiş kanalları repository'ye ekle |
| [ ] | `F4-070` | `1.70.0` | 20 dk | Sınırlı aritmetik formül ayrıştırıcısını ekle |
| [ ] | `F4-071` | `1.71.0` | 20 dk | Formül değerlendirmesini kanal dizilerine bağla |
| [ ] | `F4-072` | `1.72.0` | 20 dk | Formül ifade ve kaynak sınırlarını doğrula |
| [ ] | `F4-073` | `1.73.0` | 20 dk | Custom sekmesine basit formül editörü ekle |
| [ ] | `F4-074` | `1.74.0` | 15 dk | Annotation ve bookmark modelini ekle |
| [ ] | `F4-075` | `1.75.0` | 20 dk | Bookmark ekleme, düzenleme ve silmeyi bağla |
| [ ] | `F4-076` | `1.76.0` | 20 dk | Analiz oturumuna zincir ve annotation kaydını ekle |
| [ ] | `F4-077` | `1.77.0` | 20 dk | Analiz oturumunu ve türetilmiş kanalları yükle |
| [ ] | `F4-078` | `1.78.0` | 20 dk | Taşınmış kaynaklar için yeniden konumlandırma ekle |
| [ ] | `F4-079` | `1.79.0` | 20 dk | İşlem zinciri ve annotation undo/redo ekle |
| [ ] | `F4-080` | `1.80.0` | 20 dk | BIT durum süresi ve değişim trendini hesapla |
| [ ] | `F4-081` | `1.81.0` | 20 dk | BIT/Status trend görünümünü ekle |
| [ ] | `F4-082` | `1.82.0` | 20 dk | Grafik penceresini ayırma ve geri takmayı ekle |
| [ ] | `F4-083` | `1.83.0` | 20 dk | Çoklu monitör konumlarını kaydet ve sınırla |
| [ ] | `F4-084` | `1.84.0` | 20 dk | Event/BIT metadata'sını JSON dışa aktar |
| [ ] | `F4-085` | `1.85.0` | 15 dk | TSV ayırıcı seçimini CSV akışına ekle |
| [ ] | `F4-086` | `1.86.0` | 20 dk | Statik grafiği PDF olarak dışa aktar |
| [ ] | `F4-087` | `1.87.0` | 20 dk | Sinüs, chirp, noise ve impulse referanslarını çalıştır |
| [ ] | `F4-088` | `1.88.0` | 20 dk | Kaydet/aç sonrası analiz tekrarını doğrula |
| [ ] | `F4-089` | `1.89.0` | 20 dk | Çalışan analiz panosunu mockup ile karşılaştır |
| [ ] | `F4-090` | `2.0.0` | 15 dk | Analiz milestone kabulünü kapat ve major sürümü hazırla |

### Faz 5 — Canlı veri, bağlantı ve kayıt (0/41)

| | İş | Sürüm | Süre | Çıktı |
| --- | --- | --- | --- | --- |
| [ ] | `F5-001` | `2.1.0` | 20 dk | Canlı paket ve bağlantı sözleşmesini tamamla |
| [ ] | `F5-002` | `2.2.0` | 20 dk | Bağlantı durum makinesini ekle |
| [ ] | `F5-003` | `2.3.0` | 20 dk | Dosyadan LiveSource replay adaptörünü ekle |
| [ ] | `F5-004` | `2.4.0` | 20 dk | Replay zamanlama ve durdurmayı doğrula |
| [ ] | `F5-005` | `2.5.0` | 20 dk | UDP alıcı bağlantısını ekle |
| [ ] | `F5-006` | `2.6.0` | 20 dk | UDP paketlerini decoder'a bağla |
| [ ] | `F5-007` | `2.7.0` | 20 dk | TCP bağlantı ve okuma akışını ekle |
| [ ] | `F5-008` | `2.8.0` | 20 dk | TCP parçalı ve birleşik paket ayrımını ekle |
| [ ] | `F5-009` | `2.9.0` | 20 dk | Serial port ayar ve bağlantısını ekle |
| [ ] | `F5-010` | `2.10.0` | 20 dk | Serial paket sınırı ve timeout işleyişini ekle |
| [ ] | `F5-011` | `2.11.0` | 20 dk | Üç adaptör için ortak sözleşme kontrolü ekle |
| [ ] | `F5-012` | `2.12.0` | 20 dk | Sıra numarasından paket kaybını hesapla |
| [ ] | `F5-013` | `2.13.0` | 20 dk | Canlı cihaz zamanını kanonik zamana bağla |
| [ ] | `F5-014` | `2.14.0` | 20 dk | Sabit kapasiteli ring buffer ekle |
| [ ] | `F5-015` | `2.15.0` | 20 dk | Zaman penceresine göre buffer sorgula |
| [ ] | `F5-016` | `2.16.0` | 20 dk | Kuyruk sınırı ve drop politikasını uygula |
| [ ] | `F5-017` | `2.17.0` | 20 dk | Sınırlı otomatik yeniden bağlanma ekle |
| [ ] | `F5-018` | `2.18.0` | 20 dk | Bağlantı ve buffer ayarlarını kaydet |
| [ ] | `F5-019` | `2.19.0` | 20 dk | Connect ve Disconnect eylemlerini bağla |
| [ ] | `F5-020` | `2.20.0` | 20 dk | Paket kaybı, kuyruk ve buffer durumunu göster |
| [ ] | `F5-021` | `2.21.0` | 20 dk | Canlı akışı ortak repository'ye bağla |
| [ ] | `F5-022` | `2.22.0` | 20 dk | Canlı veriyi mevcut grafik panellerine bağla |
| [ ] | `F5-023` | `2.23.0` | 15 dk | Canlı sona takip etme ve sabit aralık seçimini ekle |
| [ ] | `F5-024` | `2.24.0` | 20 dk | Canlı ve playback mod geçişlerini denetle |
| [ ] | `F5-025` | `2.25.0` | 20 dk | Sürümlü dosya header yazıcısını ekle |
| [ ] | `F5-026` | `2.26.0` | 20 dk | Data kayıt serileştirmesini ekle |
| [ ] | `F5-027` | `2.27.0` | 20 dk | 125 ms kayıt biriktirme sınırlarını ekle |
| [ ] | `F5-028` | `2.28.0` | 20 dk | Disk yazma kuyruğunu canlı akıştan ayır |
| [ ] | `F5-029` | `2.29.0` | 20 dk | Flush ve güvenli dosya kapatmayı ekle |
| [ ] | `F5-030` | `2.30.0` | 20 dk | Disk dolması ve yazma hatasını işle |
| [ ] | `F5-031` | `2.31.0` | 20 dk | Boyut ve isim sınırında yeni dosyaya geç |
| [ ] | `F5-032` | `2.32.0` | 20 dk | Record ve Stop durumunu ana ekrana bağla |
| [ ] | `F5-033` | `2.33.0` | 20 dk | Bağlantı kesilmesinde kayıt davranışını uygula |
| [ ] | `F5-034` | `2.34.0` | 20 dk | Canlı BIT ve TX olaylarını panoya bağla |
| [ ] | `F5-035` | `2.35.0` | 20 dk | Canlı kayıt dosyasını tekrar açarak karşılaştır |
| [ ] | `F5-036` | `2.36.0` | 20 dk | Burst, kayıp ve sıra dışı paket simülatörü ekle |
| [ ] | `F5-037` | `2.37.0` | 20 dk | Burst ve bağlantı kesintisi sonuçlarını doğrula |
| [ ] | `F5-038` | `2.38.0` | 20 dk | Uzun süreli canlı kayıt koşusunu hazırla |
| [ ] | `F5-039` | `2.39.0` | 20 dk | Dayanıklılık koşusu raporunu değerlendir |
| [ ] | `F5-040` | `2.40.0` | 20 dk | Canlı modda mockup pano davranışını kontrol et |
| [ ] | `F5-041` | `3.0.0` | 15 dk | Canlı veri milestone kabulünü kapat ve major sürümü hazırla |

### Faz 6 — Windows dağıtımı ve ürünleştirme (0/34)

| | İş | Sürüm | Süre | Çıktı |
| --- | --- | --- | --- | --- |
| [ ] | `F6-001` | `3.1.0` | 20 dk | Paketleme aracı ve dağıtım biçimi ADR'sini tamamla |
| [ ] | `F6-002` | `3.2.0` | 20 dk | Windows paketleme yapılandırmasını ekle |
| [ ] | `F6-003` | `3.3.0` | 20 dk | Qt plugin, tema ve ikon kaynaklarını pakete ekle |
| [ ] | `F6-004` | `3.4.0` | 20 dk | Tek komutluk paket üretim akışını ekle |
| [ ] | `F6-005` | `3.5.0` | 20 dk | Temiz Windows ortamında paket açılışını kontrol et |
| [ ] | `F6-006` | `3.6.0` | 20 dk | Paketli uygulamada BIN ve export akışını kontrol et |
| [ ] | `F6-007` | `3.7.0` | 20 dk | Installer oluşturma adımını ekle |
| [ ] | `F6-008` | `3.8.0` | 20 dk | Kurulum, yükseltme ve kaldırmayı kontrol et |
| [ ] | `F6-009` | `3.9.0` | 15 dk | Artefakt checksum ve sürüm manifestini üret |
| [ ] | `F6-010` | `3.10.0` | 20 dk | Aynı girdilerle paket üretimini karşılaştır |
| [ ] | `F6-011` | `3.11.0` | 20 dk | Offline bağımlılık paketleme akışını hazırla |
| [ ] | `F6-012` | `3.12.0` | 20 dk | İmzalama gereksinimini yayın akışına bağla |
| [ ] | `F6-013` | `3.13.0` | 20 dk | Coverage raporu ve eşiklerini CI'a ekle |
| [ ] | `F6-014` | `3.14.0` | 20 dk | Bağımlılık taramasını CI'a ekle |
| [ ] | `F6-015` | `3.15.0` | 20 dk | Küçük performans smoke kontrolünü CI'a ekle |
| [ ] | `F6-016` | `3.16.0` | 20 dk | Windows paket smoke kontrolünü CI'a ekle |
| [ ] | `F6-017` | `3.17.0` | 20 dk | Sürüm artefaktı ve checksum iş akışını ekle |
| [ ] | `F6-018` | `3.18.0` | 15 dk | Merge ve release kalite kapılarını belgeye bağla |
| [ ] | `F6-019` | `3.19.0` | 20 dk | Tanılama paketi içerik listesini üret |
| [ ] | `F6-020` | `3.20.0` | 20 dk | Tanılama önizleme ve dışa aktarımını ekle |
| [ ] | `F6-021` | `3.21.0` | 20 dk | Son geçerli workspace kurtarmasını ekle |
| [ ] | `F6-022` | `3.22.0` | 20 dk | Tekrarlı aç/kapat ve playback koşusunu hazırla |
| [ ] | `F6-023` | `3.23.0` | 20 dk | Aç/kapat dayanıklılık sonuçlarını değerlendir |
| [ ] | `F6-024` | `3.24.0` | 20 dk | Mockup üzerinden ana ekran kullanım kılavuzunu yaz |
| [ ] | `F6-025` | `3.25.0` | 20 dk | Filtre ve spektral analiz kullanım örneğini yaz |
| [ ] | `F6-026` | `3.26.0` | 20 dk | Canlı bağlantı ve kayıt kullanım örneğini yaz |
| [ ] | `F6-027` | `3.27.0` | 20 dk | Format ve decoder kılavuzunu güncelle |
| [ ] | `F6-028` | `3.28.0` | 15 dk | Klavye, mouse ve ölçekleme kılavuzunu tamamla |
| [ ] | `F6-029` | `3.29.0` | 15 dk | Bilinen sorunları ve veri sınırlamalarını yaz |
| [ ] | `F6-030` | `3.30.0` | 20 dk | Paketli uygulamada kullanıcı kabul turunu kaydet |
| [ ] | `F6-031` | `3.31.0` | 20 dk | Paketli ana ekranı referans mockup ile karşılaştır |
| [ ] | `F6-032` | `3.32.0` | 20 dk | Release ve geri dönüş prosedürünü yaz |
| [ ] | `F6-033` | `3.33.0` | 15 dk | Major sürüm notları ve milestone özetini hazırla |
| [ ] | `F6-034` | `4.0.0` | 15 dk | Dağıtım milestone kabulünü kapat ve major sürümü hazırla |

## B. Bölüm içi kontrol listeleri


### 5.2 Data Explorer

- [ ] Lazy-loading destekli model/view tabanlı ağaç oluştur.  <sub>plan.md:205</sub>
- [ ] Kanal adına, ID’ye, birime ve kaynağa göre arama ekle.  <sub>plan.md:206</sub>
- [ ] `Sensors`, `BIT`, `Transmission`, `Derived` hızlı filtreleri ekle.  <sub>plan.md:207</sub>
- [ ] Kanal türü, bağlantı durumu ve alarm seviyesi için ikon sistemi belirle.  <sub>plan.md:208</sub>
- [ ] Kanalı çift tıklama ve sürükle-bırak ile grafiğe ekle.  <sub>plan.md:209</sub>
- [ ] Çoklu seçim ve “seçilenleri aynı grafikte/yeni grafiklerde aç” komutu ekle.  <sub>plan.md:210</sub>
- [ ] Favori kanal gruplarını kaydet.  <sub>plan.md:211</sub>
- [ ] Sağ tık menüsü: Plot, Inspect, Add to Existing Plot, Export, Copy Path.  <sub>plan.md:212</sub>

### 5.3 Workspace ve grafik kartı

- [ ] `PlotPanel` temel bileşenini oluştur.  <sub>plan.md:232</sub>
- [ ] Birden fazla kanalı aynı panelde destekle.  <sub>plan.md:233</sub>
- [ ] Sol/sağ Y ekseni veya ayrı eksen grupları desteğini değerlendir.  <sub>plan.md:234</sub>
- [ ] Tüm açık grafiklerde isteğe bağlı X-axis synchronization ekle.  <sub>plan.md:235</sub>
- [ ] Legend üzerinde kanal gizleme ve solo mode ekle.  <sub>plan.md:236</sub>
- [ ] Grafiği tab, split view ve ayrı pencere olarak açmayı destekle.  <sub>plan.md:237</sub>
- [ ] Boş workspace için sürükle-bırak yönlendirmesi tasarla.  <sub>plan.md:238</sub>
- [ ] Grafik sayısı arttığında kaynak kullanımını sınırla.  <sub>plan.md:239</sub>

### 5.4 Inspector

- [ ] Seçime göre içeriği dinamik güncelle.  <sub>plan.md:255</sub>
- [ ] Değişiklikleri undo/redo sistemine bağla.  <sub>plan.md:256</sub>
- [ ] İşlenmiş kanalın ham veriyi değiştirmediğini açıkça göster.  <sub>plan.md:257</sub>
- [ ] Filtre sırasını sürükle-bırak ile değiştirmeyi destekle.  <sub>plan.md:258</sub>
- [ ] Geçersiz parametreleri çalıştırmadan önce doğrula.  <sub>plan.md:259</sub>

### 5.5 BIT, Events ve Transmission paneli

- [ ] Zaman, kategori, severity, source ve metin filtreleri ekle.  <sub>plan.md:280</sub>
- [ ] Severity renklerini yalnızca renge bağlı bırakma; ikon ve metin de kullan.  <sub>plan.md:281</sub>
- [ ] Satıra çift tıklayınca tüm senkronize grafikleri ilgili zamana götür.  <sub>plan.md:282</sub>
- [ ] Event seçildiğinde Inspector’da detay ve ilişkili kanalları göster.  <sub>plan.md:283</sub>
- [ ] Aynı veya çok yakın zamandaki tekrarları gruplayabil.  <sub>plan.md:284</sub>
- [ ] PASS/FAIL/UNKNOWN için tutarlı durum bileşeni oluştur.  <sub>plan.md:285</sub>
- [ ] TX START/STOP aralıklarını grafik üzerinde gölgeli bölge olarak gösterebil.  <sub>plan.md:286</sub>

### 5.6 Timeline ve playback

- [ ] Playback durum makinesini UI’dan bağımsız geliştir.  <sub>plan.md:299</sub>
- [ ] Scrubbing sırasında ağır analizleri debounce et.  <sub>plan.md:300</sub>
- [ ] Viewport değişimini tüm senkronize panellere yayınla.  <sub>plan.md:301</sub>
- [ ] Dosya zamanı, UTC ve elapsed time gösterimlerini destekle.  <sub>plan.md:302</sub>

### 6.4 Erişilebilirlik ve kullanım

- [ ] Minimum metin kontrastını kontrol et.  <sub>plan.md:341</sub>
- [ ] %100, %125, %150 ve %200 Windows ölçeklemede test et.  <sub>plan.md:342</sub>
- [ ] Sadece klavyeyle temel navigasyonu destekle.  <sub>plan.md:343</sub>
- [ ] Tooltip yerine kalıcı açıklama gereken kritik terimleri etiketle.  <sub>plan.md:344</sub>
- [ ] Kritik eylemlerde durum geri bildirimi ver.  <sub>plan.md:345</sub>
- [ ] Yanlışlıkla uzun işlem başlatılırsa iptal olanağı sun.  <sub>plan.md:346</sub>

### 8.1 Ön analiz

- [ ] Format dokümanlarını ve örnek kayıtları topla.  <sub>plan.md:516</sub>
- [ ] Magic bytes, header, sürüm, endian, alignment ve paket yapılarını belgeleyin.  <sub>plan.md:517</sub>
- [ ] Timestamp kaynağını ve çözünürlüğünü belirle.  <sub>plan.md:518</sub>
- [ ] Sensör, BIT, TX ve event paket türlerini listele.  <sub>plan.md:519</sub>
- [ ] CRC/checksum algoritmasını netleştir.  <sub>plan.md:520</sub>
- [ ] Eksik/bozuk paket davranışını tanımla.  <sub>plan.md:521</sub>
- [ ] Ölçekleme, calibration, signed/unsigned ve unit dönüşümlerini doğrula.  <sub>plan.md:522</sub>
- [ ] Farklı firmware/format sürümlerinin uyumluluk tablosunu çıkar.  <sub>plan.md:523</sub>

### 8.3.12 Doğrulama kuralları

- [ ] `name == record_name(record_index)` — uyuşmazlık ad/indeks tutarsızlığı olarak raporlanır.  <sub>plan.md:931</sub>
- [ ] `record_size` 8'in katı, `48 + 8` alt sınırının üstünde ve dosya sonunu aşmıyor.  <sub>plan.md:932</sub>
- [ ] Blok zinciri toplamı `record_size` ile birebir kapanıyor; `block_count` gerçek blok sayısına eşit.  <sub>plan.md:933</sub>
- [ ] `block_size % DTYPE_SIZE[dtype] == 0`; yapısal bloklarda girdi boyutuna tam bölünüyor.  <sub>plan.md:934</sub>
- [ ] `channel_id` ChannelTable'da tanımlı; tanımsızsa kanal "unknown" olarak üretilir, blok atılmaz.  <sub>plan.md:935</sub>
- [ ] `crc32` doğru ve `end_marker == b"ENDR"`.  <sub>plan.md:936</sub>
- [ ] `record_index` monoton artıyor; atlama varsa `GAP_BEFORE`, geri gidiş varsa bozulma/yeniden başlatma olarak raporlanır.  <sub>plan.md:937</sub>
- [ ] `device_ticks` farkı nominal 125 ms'ten yapılandırılabilir toleransın (örn. ±%1) dışındaysa jitter uyarısı üretilir.  <sub>plan.md:938</sub>
- [ ] `abs(t_start_offset_ns - record_index * 125_000_000)` tolerans dışındaysa zaman tutarsızlığı raporlanır.  <sub>plan.md:939</sub>

### 8.3.13 Yapılacaklar

- [ ] Bu taslağı `docs/format/bin_v1_draft.md` olarak sürümle; gerçek format dokümanı gelince fark tablosu tut.  <sub>plan.md:945</sub>
- [ ] `tools/make_synthetic_bin.py`: parametrik sentetik üretici (kanal sayısı, fs, süre, ton/gürültü, TX/BIT/event senaryoları).  <sub>plan.md:946</sub>
- [ ] Üreticiye kasıtlı bozulma seçenekleri ekle: kayıp kayıt, CRC hatası, ad/indeks uyuşmazlığı, kırık son kayıt, bilinmeyen blok türü, ad sayacı sarması.  <sub>plan.md:947</sub>
- [ ] Küçük golden dosyalar üret (5 s, 4 kanal) ve beklenen decode çıktısını referans olarak sakla.  <sub>plan.md:948</sub>
- [ ] 1 saatlik (~2,6 GiB) dosya üret; indeksleme ve okuma bütçesini 11.1'deki hedeflere karşı ölç.  <sub>plan.md:949</sub>
- [ ] Format sürümü değiştiğinde doğru decoder'ın seçildiğini doğrulayan uyumluluk testi yaz.  <sub>plan.md:950</sub>

### 8.4 Decoder tasarımı

- [ ] Önce salt okunur `BinaryReader` geliştir.  <sub>plan.md:954</sub>
- [ ] Format algılama ile doğru decoder sürümünü seç.  <sub>plan.md:955</sub>
- [ ] `struct`, NumPy `frombuffer` veya memory mapping ile kopyasız okumayı değerlendir.  <sub>plan.md:956</sub>
- [ ] Decoder çıktısını domain modeline dönüştür.  <sub>plan.md:957</sub>
- [ ] Bilinmeyen paketleri atmak yerine konum ve tür bilgisiyle raporla.  <sub>plan.md:958</sub>
- [ ] Hatalı kayıtların kalan dosyanın okunmasını mümkün olduğunca engellememesini sağla.  <sub>plan.md:959</sub>
- [ ] Ham offset → decoded item eşlemesini geliştirici teşhisi için sakla.  <sub>plan.md:960</sub>
- [ ] Golden file testleri oluştur.  <sub>plan.md:961</sub>

### 9. Zaman senkronizasyonu

- [ ] Her veri kaynağının time base’ini tanımla.  <sub>plan.md:979</sub>
- [ ] Device ticks → kanonik nanosecond timestamp dönüşümünü uygula.  <sub>plan.md:980</sub>
- [ ] Wraparound ve counter reset davranışını tespit et.  <sub>plan.md:981</sub>
- [ ] Clock drift varsa düzeltme modelini tanımla.  <sub>plan.md:982</sub>
- [ ] Kayıp/tekrarlı/out-of-order timestamp politikası belirle.  <sub>plan.md:983</sub>
- [ ] UTC, local time ve elapsed time gösterimini birbirinden ayır.  <sub>plan.md:984</sub>
- [ ] Dönüştürülmüş zamanın yanında gerekirse orijinal device timestamp’i koru.  <sub>plan.md:985</sub>
- [ ] Sensör, BIT ve transmisyon verilerinin korelasyon toleransını yapılandırılabilir yap.  <sub>plan.md:986</sub>
- [ ] Senkronizasyon kalite bilgisini kullanıcıya gerektiğinde göster.  <sub>plan.md:987</sub>

### 10.2 İlk işlemler

- [ ] Scale ve offset.  <sub>plan.md:1002</sub>
- [ ] Calibration uygulama.  <sub>plan.md:1003</sub>
- [ ] NaN/invalid/quality flag yönetimi.  <sub>plan.md:1004</sub>
- [ ] Detrend ve DC removal.  <sub>plan.md:1005</sub>
- [ ] Moving average.  <sub>plan.md:1006</sub>
- [ ] Low-pass, high-pass, band-pass, notch.  <sub>plan.md:1007</sub>
- [ ] Resample/decimate.  <sub>plan.md:1008</sub>
- [ ] Normalize.  <sub>plan.md:1009</sub>
- [ ] Phase unwrap.  <sub>plan.md:1010</sub>
- [ ] RMS/envelope.  <sub>plan.md:1011</sub>
- [ ] FFT ve window fonksiyonları.  <sub>plan.md:1012</sub>
- [ ] PSD/Welch.  <sub>plan.md:1013</sub>
- [ ] STFT/spektrogram.  <sub>plan.md:1014</sub>

### 11.3 Profil ve native hızlandırma kararı

- [ ] Gerçekçi veri setiyle benchmark oluştur.  <sub>plan.md:1058</sub>
- [ ] `py-spy`, `cProfile` veya uygun profiler ile darboğazı ölç.  <sub>plan.md:1059</sub>
- [ ] Önce algoritma, veri kopyalama ve cache sorunlarını düzelt.  <sub>plan.md:1060</sub>
- [ ] Sadece kanıtlanmış sıcak noktaları C++/pybind11, Cython, Numba veya Rust ile hızlandırmayı değerlendir.  <sub>plan.md:1061</sub>
- [ ] Native modül kullanılırsa Python referans uygulamasını doğrulama amacıyla koru.  <sub>plan.md:1062</sub>

### 13. Canlı veri mimarisi

- [ ] UDP/TCP/serial adapter sınırlarını tanımla.  <sub>plan.md:1089</sub>
- [ ] Bağlantı durum makinesi: disconnected, connecting, connected, degraded, error.  <sub>plan.md:1090</sub>
- [ ] Paket sıra numarası ve packet-loss ölçümü.  <sub>plan.md:1091</sub>
- [ ] Backpressure/drop policy tanımı.  <sub>plan.md:1092</sub>
- [ ] Ring buffer boyutu ve zaman penceresi ayarı.  <sub>plan.md:1093</sub>
- [ ] Canlı veriyi kayda alma ve dosyayı güvenli kapatma.  <sub>plan.md:1094</sub>
- [ ] Bağlantı kesilince otomatik yeniden bağlanma seçeneği.  <sub>plan.md:1095</sub>
- [ ] Canlı ve playback modlarının aynı anda yanlışlıkla karışmasını önle.  <sub>plan.md:1096</sub>
- [ ] Simülatör/replay source ile donanımsız geliştirme olanağı sağla.  <sub>plan.md:1097</sub>

### 21. CI/CD kalite kapıları

- [ ] Lint ve format kontrolü (`ruff`).  <sub>plan.md:1253</sub>
- [ ] Type check (`mypy` veya `pyright`).  <sub>plan.md:1254</sub>
- [ ] Unit ve integration testleri.  <sub>plan.md:1255</sub>
- [ ] Minimum coverage eşiği; başlangıçta %70, kritik parser/domain kodunda daha yüksek.  <sub>plan.md:1256</sub>
- [ ] Dependency/security scan.  <sub>plan.md:1257</sub>
- [ ] Küçük performans smoke benchmark.  <sub>plan.md:1258</sub>
- [ ] Windows paketleme smoke test.  <sub>plan.md:1259</sub>
- [ ] Sürüm artefaktı ve checksum.  <sub>plan.md:1260</sub>

### 23. MVP “Definition of Done”

- [ ] Ana ekran referans mockup'ın dokuz bölgesini, üç sütunlu düzenini ve panel hiyerarşisini karşılıyor.  <sub>plan.md:1896</sub>
- [ ] Sağ BIT genel özeti alt sistem durumlarıyla tutarlı; gerçek veri ile simülasyon ayırt ediliyor.  <sub>plan.md:1897</sub>
- [ ] FFT/spektrogram gibi v2 işlevleri MVP'de açıklamalı pasif durumda; tamamlanmamış işlev başarılı sonuç göstermez.  <sub>plan.md:1898</sub>
- [ ] Desteklenen `.bin` dosyası salt okunur biçimde güvenilir açılıyor.  <sub>plan.md:1899</sub>
- [ ] Parser sonuçları referans kayıtlarla doğrulanmış.  <sub>plan.md:1900</sub>
- [ ] Kanal ağacı binlerce öğede kullanılabilir hızda çalışıyor.  <sub>plan.md:1901</sub>
- [ ] Kullanıcı kanalları grafiğe ekleyip kaldırabiliyor.  <sub>plan.md:1902</sub>
- [ ] Birden fazla grafik ortak X zaman ekseninde senkronize olabiliyor.  <sub>plan.md:1903</sub>
- [ ] X, Y ve XY zoom davranışları tutarlı.  <sub>plan.md:1904</sub>
- [ ] Cursor ve region ölçümleri doğru.  <sub>plan.md:1905</sub>
- [ ] BIT/event satırından grafikte aynı zamana gidiliyor.  <sub>plan.md:1906</sub>
- [ ] TX aralıkları ve kritik olaylar grafik üzerinde gösteriliyor.  <sub>plan.md:1907</sub>
- [ ] Uzun işler UI’ı dondurmuyor ve iptal edilebiliyor.  <sub>plan.md:1908</sub>
- [ ] PNG ve CSV dışa aktarma metadata ile çalışıyor.  <sub>plan.md:1909</sub>
- [ ] Workspace kaydet/aç işlevi temel düzeni koruyor.  <sub>plan.md:1910</sub>
- [ ] Kritik unit/integration/GUI testleri CI’da geçiyor.  <sub>plan.md:1911</sub>
- [ ] Desteklenen Windows ölçeklemelerinde arayüz bozulmuyor.  <sub>plan.md:1912</sub>
- [ ] Bilinen kritik hata bulunmuyor; diğer bilinen sorunlar release notes’ta yer alıyor.  <sub>plan.md:1913</sub>

### 25. Açık kararlar

- [ ] `.bin` format dokümanı ve örnek dosyalar mevcut mu?  <sub>plan.md:1934</sub>
- [ ] En büyük tipik dosya boyutu ve kayıt süresi nedir?  <sub>plan.md:1935</sub>
- [ ] Maksimum kanal sayısı ve kanal başına en yüksek sample rate nedir?  <sub>plan.md:1936</sub>
- [ ] Timestamp tek kaynaktan mı geliyor; cihazlar arasında clock drift var mı?  <sub>plan.md:1937</sub>
- [ ] BIT sonuçları anlık event mi, periyodik status mü, ikisi birden mi?  <sub>plan.md:1938</sub>
- [ ] Transmisyon verisinin alanları ve START/STOP ilişkilendirmesi nedir?  <sub>plan.md:1939</sub>
- [ ] Canlı veri hangi protokol ve bant genişliğiyle gelecek?  <sub>plan.md:1940</sub>
- [ ] Hedef bilgisayar CPU, RAM, GPU ve monitör çözünürlüğü nedir?  <sub>plan.md:1941</sub>
- [ ] Uygulamanın offline/air-gapped ortamda çalışması gerekiyor mu?  <sub>plan.md:1942</sub>
- [ ] Verinin güvenlik sınıfı ve log/export kısıtları var mı?  <sub>plan.md:1943</sub>
- [ ] Birden fazla kayıt zaman hizalı olarak karşılaştırılacak mı?  <sub>plan.md:1944</sub>
- [ ] MATLAB’daki hangi analiz/etkileşim davranışları birebir bekleniyor?  <sub>plan.md:1945</sub>
- [ ] Rapor çıktısı resmi test kanıtı sayılacak mı?  <sub>plan.md:1946</sub>
- [ ] Arayüz yalnız İngilizce mi, Türkçe/İngilizce mi olacak?  <sub>plan.md:1947</sub>
