# İş günlüğü — süreler, atlanan işler ve notlar

> Bu dosya Bölüm 22 iş tablosunun yerine geçmez. Amaç, **her işin gerçekte ne kadar sürdüğünü** ve
> **yapılamayan veya eksik bilgiyle yapılan işleri** kaybetmeden kaydetmektir. Bir iş burada
> `ATLANDI` ise plan tablosunda `[ ]` olarak kalır ve engeli kalkınca tekrar ele alınır.
>
> Güncel madde listesi: `docs/notes/todo.md` (`python tools/sync_todo.py` ile üretilir).

## 1. Süreler

**Gerçek süre nasıl ölçülüyor:** bir işin commit'i ile bir önceki commit arasındaki zaman farkı.
Commit, o işin bitişidir; dolayısıyla fark, önceki iş bittikten sonra bu işe harcanan süredir.
Ölçüm otomatiktir, tahmin değildir.

Tablo `python tools/worklog_stats.py --update` ile üretilir; **elle düzenlenmez.**

<!-- SURELER:BASLANGIC -->

| İş ID | Hedef | Gerçek | Commit | Konu |
| --- | --- | --- | --- | --- |
| `F0-001` | 15 dk | — | `61e4fca` | git başlangıcını, ignore kurallarını ve VERSION kaynağını hazırla |
| `F0-002` | 15 dk | 1 dk 42 sn | `80c49ac` | üç kullanıcı rolü için ilk beş senaryoyu yaz |
| `F0-003` | 20 dk | 1 dk 44 sn | `985bceb` | örnek dosya ve format envanterini çıkar |
| `-` | — | 26 sn | `7be4fae` | gece koşusu için iş günlüğü ve atlama notlarını başlat |
| `F0-004` | 15 dk | 1 dk 10 sn | `4871335` | 32 byte örnek header sözleşmesini çıkar |
| `F0-005` | 20 dk | 56 sn | `713f6b7` | 64 byte örnek Data kayıt sözleşmesini çıkar |
| `F0-006` | 15 dk | 2 dk 3 sn | `141bdd2` | 125 ms periyot ve kayıt adı kurallarını belgeye bağla |
| `F0-007` | 20 dk | 1 dk 43 sn | `4e3aaa2` | mockup kanal gruplarını örnek veri sözlüğüne eşleştir |
| `F0-008` | 20 dk | 1 dk 38 sn | `e2b33ed` | CRC destekleyen formatın karar kaydını yaz |
| `F0-009` | 15 dk | 1 dk 41 sn | `c50bcb0` | küçük geçerli fixture için beklenen sonuçları yaz |
| `F0-010` | 15 dk | 1 dk 39 sn | `df8cf80` | bozuk fixture senaryolarının sonuçlarını yaz |
| `F0-011` | 20 dk | 3 dk 44 sn | `250bd0c` | UTC ve cihaz zamanı dönüşüm kararını yaz |
| `-` | — | 2 dk 27 sn | `b05a64d` | plan.md'den üretilen todo listesi ve süre kaydı ekle |
| `F0-012` | 20 dk | 2 dk 5 sn | `f144dea` | referans mockup'ın dokuz bölgesini yerleşime eşleştir |
| `F0-013` | 20 dk | 1 dk 45 sn | `35c00df` | mockup etkileşimleri ve görsel kabul listesini yaz |
| `F0-014` | 20 dk | 2 dk 27 sn | `71bbb85` | ölçüm bilgisayarı ve performans bütçesini kaydet |
| `F0-015` | 20 dk | 1 dk 27 sn | `5a833ce` | açık kararları ve dış bağımlılıkları kaydet |
| `F0-016` | 15 dk | 1 dk 28 sn | `86490c3` | ADR listesini iş ve sürüm hedefleriyle eşleştir |
| `F0-017` | 15 dk | 1 dk 26 sn | `35d7f68` | format milestone kabul tutanağını hazırla |
| `F1-001` | 20 dk | 6 dk 50 sn | `6e4a36f` | python paket iskeleti ve bağımlılık kilidini oluştur |
| `F1-002` | 15 dk | 1 dk 57 sn | `d7f0a90` | tek komutluk geliştirici kurulumunu yaz |
| `F1-003` | 15 dk | 1 dk 13 sn | `95a3fb3` | ruff kontrol yapılandırmasını ekle |
| `F1-004` | 15 dk | 2 dk 56 sn | `052a3df` | pyright tip kontrolünü ekle |
| `F1-005` | 15 dk | 4 dk 9 sn | `3b14a71` | pytest ve pytest-qt başlangıç düzenini kur |
| `F1-006` | 20 dk | 1 dk 17 sn | `89f8bec` | Windows kalite kontrol iş akışını ekle |
| `F1-007` | 20 dk | 1 dk 56 sn | `6860120` | uygulama girişini ve temiz kapanışı ekle |
| `F1-006` | 20 dk | 1 dk 17 sn | `dcfe128` | checkout satır sonlarını LF'e sabitle ( düzeltmesi) |
| `F1-008` | 20 dk | 4 dk 1 sn | `5a02e57` | merkezi exception yakalama yolunu ekle |
| `F1-009` | 20 dk | 2 dk 38 sn | `06c4c6b` | sürümlü temel ayarları yükle ve kaydet |
| `F1-010` | 20 dk | 4 dk 33 sn | `991b9c4` | dönen log ve session kimliği ekle |
| `-` | — | 1 dk 40 sn | `b3b3a74` | pyright/ruff sürümlerini sabitle ve default_factory tipini düzelt |
| `F1-011` | 15 dk | 1 dk 15 sn | `87b3c64` | ChannelMetadata modelini tanımla |
| `F1-012` | 15 dk | 1 dk 34 sn | `a01a899` | DataChunk ve kalite alanlarını tanımla |
| `-` | — | 2 dk 34 sn | `9d1a104` | iş sürelerini git geçmişinden otomatik üret |
| `-` | — | 1 dk 22 sn | `0d11b80` | numpy sürümünü sabitle, CI'a sürüm raporlama ekle |
| `F1-013` | 15 dk | 1 dk 30 sn | `074f936` | TimeRange ve RecordingMetadata modellerini ekle |
| `F1-014` | 15 dk | 1 dk 27 sn | `0e21f97` | Event ve BitResult modellerini ekle |
| `F1-015` | 15 dk | 1 dk 27 sn | `3afe5f3` | TransmissionInterval modelini ekle |
| `F1-016` | 20 dk | 3 dk 19 sn | `04534ec` | RecordingRepository protokolünü tanımla |
| `F1-017` | 15 dk | 1 dk 40 sn | `020f243` | LiveSource protokolünü tanımla |
| `F1-018` | 15 dk | 430 dk 17 sn | `36b9809` | deterministik sinüs üretecini ekle |
| `F1-019` | 20 dk | 1 dk 40 sn | `72145e4` | noise, chirp ve impulse örneklerini ekle |
| `F1-020` | 20 dk | 1 dk 55 sn | `48f95dc` | sahte kanal repository uygulamasını ekle |
| `F1-021` | 15 dk | 2 dk 18 sn | `a11d9f3` | sahte BIT, TX ve sistem olaylarını ekle |
| `F1-022` | 20 dk | 2 dk 38 sn | `59ce1b7` | mockup'ın üç sütunlu ana pencere düzenini oluştur |
| `F1-023` | 15 dk | 3 dk 30 sn | `5a20b3e` | menü ve toolbar eylem iskeletini ekle |
| `F1-024` | 15 dk | 7 dk 22 sn | `ea51cac` | Data Explorer dock'unu ekle |
| `F1-025` | 15 dk | 4 dk 43 sn | `b59e723` | Inspector'ı bağlamsal araç sekmesi olarak ekle |
| `F1-026` | 15 dk | 1 dk 59 sn | `d34620a` | alt Log/Messages alanı ve Events sekmesini ekle |
| `F1-013` | 15 dk | 34 sn | `e6832b4` | worklog'a ..F1-026 durumları ve bulunan sorunları ekle |
| `-` | — | 3 dk 25 sn | `720d5de` | pyright pythonVersion sabitini kaldır |
| `-` | — | 2 dk 34 sn | `b905773` | CI'nin 3.12 pyright hatasını açık sorun olarak kaydet |
| `-` | — | 344 dk 17 sn | `5f0d20b` | pyright bulgularını GitHub annotation'a çevir |
| `-` | — | 3 dk 9 sn | `702ec61` | pyright çıkış kodunu yutup annotation adımına ulaş |
| `-` | — | 3 dk 55 sn | `8c930f3` | PySide6 sürümünü sabitle, Qt None kontrollerini geri koy |
| `-` | — | 3 dk 53 sn | `814476a` | CI 3.12 pyright sorununu çözüldü olarak kapat |
| `F1-027` | 15 dk | 2 dk 54 sn | `5f679d9` | Playback/Time Control şeridini yerleştir |
| `F1-028` | 15 dk | 3 dk 21 sn | `18eddb8` | durum çubuğu alanlarını ekle |
| `F1-029` | 20 dk | 242 dk 21 sn | `6a735d1` | mockup koyu temasını ve mavi vurgularını uygula |
| `F1-030` | 20 dk | 2 dk 8 sn | `2bc3f14` | durum ikonları ve kanal paletini ekle |
| `F1-031` | 20 dk | 2 dk 45 sn | `50da59f` | tek kanallı PlotPanel iskeletini ekle |
| `F1-032` | 20 dk | 2 dk 4 sn | `a9eb0be` | mock repository seçimini grafiğe bağla |
| `-` | — | 2 dk 47 sn | `dc3dc18` | ekran görüntüsü aracı ekle, offscreen yazı tipi sorununu çöz |
| `F1-033` | 15 dk | 46 dk 34 sn | `c627589` | boş workspace yönlendirmesini ekle |
| `F1-034` | 15 dk | 1 dk 35 sn | `9cddf2c` | Open .bin File düğmesi ve dosya özet kartını ekle |
| `F1-035` | 15 dk | 2 dk 27 sn | `d0fd7c1` | sağ üst BIT/System Status kartını yerleştir |
| `F1-036` | 15 dk | 2 dk 4 sn | `d27c290` | Analysis Tools kartının sekmelerini yerleştir |
| `F1-037` | 15 dk | 1 dk 26 sn | `9482d61` | sağ alt Data Export kartını yerleştir |
| `F1-038` | 15 dk | 2 dk 10 sn | `ac43dce` | mockup ana analiz sekmelerini yerleştir |
| `F1-039` | 20 dk | 3 dk 23 sn | `6a06651` | merkez dashboard grafik hücrelerini oluştur |
| `F1-040` | 15 dk | 3 dk 57 sn | `6afad9d` | grafik hızlı araç şeridini yerleştir |
| `F1-041` | 20 dk | 5 dk 47 sn | `f1d40e4` | bir ve on milyon noktalık spike girdilerini hazırla |
| `F1-042` | 20 dk | 18 sn | `99a38a6` | pan/zoom ve cursor ölçüm koşucusunu ekle |
| `F1-043` | 20 dk | 2 dk 46 sn | `659f26d` | ilk spike sonuçlarını ve darboğazı kaydet |
| `F1-044` | 15 dk | 8 dk 39 sn | `228f6dd` | uygulama iskeleti milestone kontrolünü yap |
| `F2-001` | 15 dk | 6 dk 21 sn | `7011f27` | header alan sabitlerini ve veri modelini ekle |
| `F2-002` | 20 dk | 1 dk 41 sn | `572b0f1` | little-endian header okuyucusunu ekle |
| `F2-003` | 15 dk | 1 dk 34 sn | `b8a049e` | magic ve sürüm doğrulamasını ekle |
| `F2-004` | 20 dk | 1 dk 56 sn | `d7f4361` | eksik header ve boyut sınırlarını denetle |
| `F2-005` | 20 dk | 2 dk 54 sn | `6063b13` | tek Data kaydını çözümle |
| `F2-006` | 20 dk | 1 dk 15 sn | `6821a9d` | ardışık kayıt iterator'unu ekle |
| `F2-007` | 15 dk | 1 dk 13 sn | `643f92d` | 125 ms kayıt zamanını kanonik ns'ye dönüştür |
| `F2-008` | 20 dk | 2 dk 13 sn | `799b5b7` | sıra ve zaman boşluklarını raporla |
| `F2-009` | 15 dk | 1 dk 42 sn | `c5a0609` | kesik son kaydı raporlayarak okumayı bitir |
| `F2-010` | 15 dk | 3 dk 35 sn | `36dead5` | kayıt adı ve sıra numarası tutarlılığını denetle |
| `F2-011` | 20 dk | 8 dk 6 sn | `9b992de` | tekrarlı ve sıra dışı kayıtları raporla |
| `F2-012` | 20 dk | 3 dk 44 sn | `74088ab` | sürüme göre decoder seçimini ekle |
| `F2-013` | 20 dk | 2 dk 25 sn | `a172271` | kararlaştırılmış CRC hesaplamasını ekle |
| `F2-014` | 20 dk | 2 dk 31 sn | `ded1933` | CRC alanlı format doğrulamasını bağla |
| `F2-015` | 20 dk | 3 dk 10 sn | `cadcb56` | bilinmeyen paket teşhisini ekle |
| `F2-016` | 20 dk | 4 dk 30 sn | `01ffa02` | 32/64 byte örnek fixture yazıcısını ekle |
| `F2-017` | 20 dk | 4 dk 18 sn | `be5e96c` | kesik, bozuk ve sıra boşluklu fixture'ları ekle |
| `F2-018` | 20 dk | 4 dk 18 sn | `2ec1560` | CRC destekli format fixture'ını ekle |
| `F2-019` | 20 dk | 2 dk 22 sn | `8be2bbe` | sensör alanlarını kanal metadata'sına eşleştir |
| `F2-020` | 20 dk | 1 dk 53 sn | `2fb0c87` | scale ve offset dönüşümünü ekle |
| `F2-021` | 20 dk | 1 dk 52 sn | `33ad0ba` | calibration seçimini ve kalite eşlemesini ekle |
| `F2-022` | 20 dk | 2 dk 37 sn | `b61ab4c` | BIT maskesini durum ve değişim olaylarına çevir |
| `F2-023` | 20 dk | 2 dk 2 sn | `7be2eae` | TX durumunu başlangıç/bitiş aralıklarına çevir |
| `F2-024` | 15 dk | 3 dk 16 sn | `42a3abb` | parser teşhislerini sistem olaylarına çevir |
| `F2-025` | 20 dk | 2 dk 26 sn | `85e428d` | cihaz tick dönüşüm adaptörünü ekle |
| `F2-026` | 20 dk | 2 dk 22 sn | `0bd93b5` | wraparound ve saat resetini ayırt et |
| `F2-027` | 20 dk | 2 dk 0 sn | `c088986` | tanımlı drift düzeltmesini uygula |
| `F2-028` | 20 dk | 2 dk 26 sn | `e23f038` | kayıt offseti ve zaman indeksini oluştur |
| `F2-029` | 20 dk | 2 dk 0 sn | `210fc91` | kanal ve olay indekslerini oluştur |
| `F2-030` | 20 dk | 1 dk 54 sn | `adf20e6` | kaynak fingerprint ve parser sürümünü kaydet |
| `F2-031` | 20 dk | 83 dk 18 sn | `a45ae98` | indeks dosyasını atomik kaydet |
| `F2-032` | 20 dk | 3 dk 22 sn | `4516fc7` | geçerli indeksi yeniden kullan |
| `F2-033` | 20 dk | 3 dk 30 sn | `b8799af` | dosya metadata ve kanal listesini sun |
| `F2-034` | 20 dk | 4 dk 0 sn | `2f30c9b` | indeksli zaman aralığı sorgusunu ekle |
| `F2-035` | 20 dk | 5 dk 42 sn | `7cb05e6` | zaman ve kategoriye göre olay sorgula |
| `F2-036` | 20 dk | 3 dk 39 sn | `90652ed` | birden fazla kaydı ayrı kimlikle yönet |
| `F2-037` | 15 dk | 34 sn | `ae0ee1e` | decoded öğeden ham offsete erişim ekle |
| `F2-038` | 15 dk | 15 dk 32 sn | `e072e74` | okuyucu kaynaklarını güvenli kapat |
| `-` | — | 33 sn | `d300caf` | uygulama başlatma betiği ve çalıştırma bölümü ekle |
| `F2-039` | 20 dk | 3 dk 31 sn | `03d0460` | bağımsız golden sonuçlarını parser ile karşılaştır |
| `F2-040` | 20 dk | 2 dk 43 sn | `80823d0` | kaynak dosyanın değişmediğini doğrula |
| `F2-041` | 15 dk | 8 dk 41 sn | `51aea02` | parser milestone kabulünü kaydet |
| `F3-001` | 15 dk | 14 dk 30 sn | `017bb27` | tekli ve çoklu dosya açma seçicisini bağla |
| `F3-002` | 20 dk | 11 dk 52 sn | `b20fdcb` | dosya yükleme worker'ını ekle |
| `F3-003` | 20 dk | 5 dk 13 sn | `567e722` | yükleme ilerlemesi ve iptal eylemini ekle |
| `F3-004` | 20 dk | 3 dk 19 sn | `1b0bbb7` | eski istek sonucunun görünümü ezmesini önle |
| `F3-005` | 20 dk | 3 dk 39 sn | `c1ad33a` | dosya yükleme sonucunu repository ve ekrana bağla |
| `F3-006` | 15 dk | 4 dk 16 sn | `a883737` | format ve dosya erişim hatalarını göster |
| `F3-007` | 20 dk | 6 dk 47 sn | `7bd5001` | dosya kapatma ve bağlı panel temizliğini ekle |
| `F3-008` | 15 dk | 4 dk 17 sn | `f409f35` | son dosyalar ve varsayılan klasörü kaydet |
| `F3-009` | 20 dk | 6 dk 11 sn | `a33d142` | dosya ve kanal ağaç modelini ekle |
| `F3-010` | 20 dk | 6 dk 3 sn | `c3f9162` | kanal ağacında lazy yüklemeyi ekle |
| `F3-011` | 20 dk | 3 dk 24 sn | `f941aef` | ad, ID, birim ve kaynak aramasını ekle |
| `-` | — | 3 dk 32 sn | `60290a4` | todo.md üreticisine otonom çalışma kuralını ekle |
| `F3-012` | 15 dk | 8 dk 37 sn | `0eb8559` | channels/Data Tree sekmeleri ve kategori filtrelerini bağla |
| `F3-013` | 20 dk | 2 dk 34 sn | `9ea53f3` | çift tıkla kanalı grafiğe ekle |
| `F3-014` | 15 dk | 4 dk 45 sn | `a445bc7` | grafikten kanal kaldırmayı ekle |
| `F3-015` | 20 dk | 14 dk 17 sn | `126567a` | kanal sürükle-bırak akışını ekle |
| `F3-016` | 20 dk | 396 dk 38 sn | `0165c36` | çoklu kanal ekleme eylemlerini ekle |
| `F3-017` | 20 dk | 7 dk 5 sn | `cb1a0e4` | favori kanal gruplarını kaydet |
| `F3-018` | 15 dk | 5 dk 25 sn | `c97a676` | kanal sağ tık eylemlerini bağla |
| `F3-019` | 20 dk | 3 dk 56 sn | `cb2cb63` | ortak zaman ekseninde çoklu seri çiz |
| `F3-020` | 20 dk | 5 dk 10 sn | `76520b7` | farklı birimler için ikinci Y ekseni ekle |
| `F3-021` | 15 dk | 3 dk 22 sn | `73b0291` | pan etkileşimini bağla |
| `F3-022` | 15 dk | 64 dk 58 sn | `13e9ba1` | yalnız X zoom modunu ekle |
| `F3-023` | 15 dk | 2 dk 12 sn | `f93a1dc` | yalnız Y zoom modunu ekle |
| `F3-024` | 15 dk | 2 dk 36 sn | `55a0ac1` | XY zoom modunu ekle |
| `F3-025` | 15 dk | 3 dk 38 sn | `8034ec7` | autoscale ve görünüm sıfırlamayı ekle |
| `F3-026` | 20 dk | 3 dk 40 sn | `6e07c85` | crosshair ve cursor okumasını ekle |
| `F3-027` | 20 dk | 3 dk 13 sn | `55937c8` | iki cursor fark ölçümünü ekle |
| `F3-028` | 15 dk | 4 dk 32 sn | `fdd426e` | zaman bölgesi seçimini ekle |
| `F3-029` | 15 dk | 2 dk 56 sn | `66b8035` | seçili bölgeye yakınlaşmayı bağla |
| `F3-030` | 20 dk | 3 dk 38 sn | `34295ab` | legend gizleme ve solo eylemlerini ekle |
| `F3-031` | 15 dk | 3 dk 31 sn | `a4bdf47` | seri rengi, çizgi ve marker ayarını ekle |
| `F3-032` | 20 dk | 3 dk 40 sn | `237ee33` | paneller arasında X senkronizasyonunu ekle |
| `F3-033` | 20 dk | 3 dk 25 sn | `55a3d63` | grafik tabı ve bölünmüş görünüm ekle |
| `F3-034` | 15 dk | 3 dk 45 sn | `c95570c` | panel kaynak sınırını ve kapatma temizliğini ekle |
| `F3-035` | 15 dk | 2 dk 25 sn | `6cbb983` | seçili kanal metadata'sını Inspector'a bağla |
| `F3-036` | 20 dk | 3 dk 43 sn | `3865c71` | Inspector görünüm ayarlarını grafiğe bağla |
| `F3-037` | 20 dk | 2 dk 44 sn | `5897127` | count, min, max ve mean hesabını ekle |
| `F3-038` | 20 dk | 2 dk 27 sn | `9d35ae5` | median, RMS, std ve peak-to-peak ekle |
| `F3-039` | 20 dk | 3 dk 32 sn | `9604fdb` | ROI istatistiklerini dashboard kartına bağla |
| `F3-040` | 20 dk | 5 dk 8 sn | `3adca5e` | geliştirici ham kayıt görünümünü ekle |
| `F3-041` | 20 dk | 4 dk 23 sn | `4647cf3` | görünüm ayarları için undo/redo ekle |
| `F3-042` | 20 dk | 4 dk 29 sn | `f41c2d2` | ortak olay tablo modelini ekle |
| `F3-043` | 20 dk | 4 dk 21 sn | `579445c` | zaman, severity, kaynak ve metin filtrelerini ekle |
| `F3-044` | 15 dk | 5 dk 22 sn | `23198a4` | olay seçimini Inspector detayına bağla |
| `F3-045` | 20 dk | 4 dk 46 sn | `0f4003f` | olay zaman işaretlerini çiz |
| `F3-046` | 20 dk | 3 dk 5 sn | `768cb2f` | olay çift tıklamasını ortak zamana bağla |
| `F3-047` | 20 dk | 3 dk 35 sn | `c719118` | TX aralıklarını gölgeli bölge olarak çiz |
| `F3-048` | 15 dk | 4 dk 50 sn | `0f0f6fb` | transmission sekmesini TX aralıklarına bağla |
| `F3-049` | 20 dk | 5 dk 9 sn | `81e6150` | yakın tekrar olaylarını grupla |
| `F3-050` | 15 dk | 3 dk 42 sn | `5d80e1f` | marker ve TX görünürlüğü kontrollerini ekle |
| `F3-051` | 20 dk | 3 dk 42 sn | `df44b14` | sağ BIT kartını alt sistem durumlarına bağla |
| `F3-052` | 15 dk | 2 dk 38 sn | `d18ff15` | Run BIT Analysis eylemini kayıt analizine bağla |
| `F3-053` | 15 dk | 2 dk 51 sn | `315578f` | yükleme ve analiz mesajlarını alt loga bağla |
| `F3-054` | 20 dk | 4 dk 5 sn | `9e9e65b` | kayıt geneli Timeline özetini çiz |
| `F3-055` | 20 dk | 4 dk 30 sn | `adef90e` | timeline viewport seçimini grafiğe bağla |
| `F3-056` | 20 dk | 4 dk 0 sn | `ad13fd0` | play, pause ve stop durum makinesini ekle |
| `F3-057` | 20 dk | 5 dk 8 sn | `b6f209b` | kayıt zamanına göre ilerleme saatini ekle |
| `F3-058` | 15 dk | 9 dk 20 sn | `22e4fb9` | oynatma hızlarını bağla |
| `F3-059` | 20 dk | 5 dk 50 sn | `7119e52` | zamana ve önceki/sonraki olaya gitmeyi ekle |
| `F3-060` | 20 dk | 8 dk 44 sn | `f226c00` | scrubbing sorgularını debounce et |
| `F3-061` | 15 dk | 6 dk 44 sn | `4bd8868` | UTC, yerel ve geçen süre gösterimini ekle |
| `F3-062` | 20 dk | 41 dk 58 sn | `1d329e5` | seçili grafiği PNG olarak dışa aktar |
| `F3-063` | 20 dk | 5 dk 40 sn | `439cc35` | seçili grafiği SVG olarak dışa aktar |
| `F3-064` | 20 dk | 4 dk 57 sn | `4b6d386` | seçili kanal ve aralığı CSV olarak yaz |
| `F3-065` | 20 dk | 8 dk 19 sn | `0cacfb6` | export hedefi ve üzerine yazma kontrolünü ekle |
| `F3-066` | 20 dk | 23 dk 43 sn | `b456b11` | büyük export için worker ve iptal ekle |
| `F3-067` | 20 dk | 7 dk 5 sn | `ea03959` | sürümlü workspace JSON modelini ekle |
| `F3-068` | 20 dk | 5 dk 46 sn | `3885751` | dock ve grafik düzenini kaydet |
| `F3-069` | 20 dk | 3 dk 36 sn | `c5e9e9c` | workspace dosyasını geri yükle |
| `F3-070` | 20 dk | 4 dk 17 sn | `f429765` | eksik kaynak ve bozuk workspace davranışını ekle |
| `F3-071` | 20 dk | 3 dk 16 sn | `b0d8fd2` | workspace sürüm geçiş yolunu ekle |
| `F3-072` | 20 dk | 5 dk 18 sn | `706ab7d` | bölüm 16 klavye kısayollarını bağla |
| `F3-073` | 20 dk | 6 dk 17 sn | `47591d3` | klavye odak sırasını ve açıklamaları düzenle |
| `F3-074` | 20 dk | 3 dk 53 sn | `540271c` | windows ölçekleme ve kontrast kontrolünü kaydet |
| `F3-075` | 20 dk | 3 dk 28 sn | `d3bc38e` | dosyadan olay gezinmesine entegrasyon senaryosu ekle |
| `F3-076` | 20 dk | 3 dk 28 sn | `3998b47` | kritik plot ve workspace GUI kontrollerini ekle |
| `F3-077` | 20 dk | 5 dk 16 sn | `66f4d3a` | MVP etkileşim bütçesini ölç |
| `F3-078` | 20 dk | 3 dk 50 sn | `51f30fd` | operatör ve mühendis MVP senaryolarını kaydet |
| `F3-079` | 20 dk | 5 dk 4 sn | `439617f` | MVP ekran görüntüsünü ana mockup ile karşılaştır |
| `F3-080` | 15 dk | 6 dk 33 sn | `40a2f7c` | MVP kabulünü kapat ve major sürümü hazırla |
| `F4-001` | 20 dk | 3 dk 48 sn | `8ac0bdb` | işlem adımı ve parametre modelini ekle |
| `F4-002` | 20 dk | 3 dk 40 sn | `b070b05` | sıralı işlem zinciri yürütücüsünü ekle |
| `F4-003` | 20 dk | 3 dk 48 sn | `ee31a2f` | DSP işlerini worker üzerinden çalıştır |
| `F4-004` | 20 dk | 4 dk 2 sn | `11ae172` | DSP iptal ve eski sonuç denetimini ekle |
| `F4-005` | 20 dk | 3 dk 41 sn | `007491a` | NaN ve kalite bayrağı politikasını uygula |
| `F4-006` | 20 dk | 9 dk 42 sn | `79db489` | Analysis Tools işlem listesi editörünü ekle |
| `F4-007` | 20 dk | 5 dk 46 sn | `e941eab` | analiz parametre hatalarını alanlarda göster |
| `F4-008` | 15 dk | 6 dk 1 sn | `9718efa` | seçili kanala uygulama ve filtreli veri görünümünü bağla |
| `F4-009` | 20 dk | 5 dk 58 sn | `17f3ef0` | ham akustik blok formatının ayrı sürümünü tanımla |
| `F4-010` | 20 dk | 6 dk 38 sn | `bcb48d7` | 48 kHz akustik blok fixture üretecini ekle |
| `F4-011` | 20 dk | 6 dk 55 sn | `02ff761` | akustik blok payload decoder'ını ekle |
| `F4-012` | 20 dk | 3 dk 49 sn | `69cdb39` | blok içi örnek zamanlarını üret |
| `F4-013` | 20 dk | 3 dk 41 sn | `fdba8f8` | akustik blokları zaman sorgusuna bağla |
| `F4-014` | 20 dk | 12 dk 50 sn | `73c091e` | akustik boyut ve sample rate sınırlarını doğrula |
| `F4-015` | 20 dk | 5 dk 45 sn | `8df389a` | detrend ve DC kaldırma hesabını ekle |
| `F4-016` | 15 dk | 5 dk 5 sn | `763370b` | detrend türü seçimini işlem editörüne bağla |
| `F4-017` | 20 dk | 6 dk 24 sn | `555b340` | moving average hesabını ekle |
| `F4-018` | 15 dk | 4 dk 7 sn | `9fe0b3e` | moving average pencere kontrolünü bağla |
| `F4-019` | 20 dk | 3 dk 57 sn | `e733e67` | normalize hesabını ekle |
| `F4-020` | 15 dk | 3 dk 14 sn | `7a5ae7d` | normalize seçimini işlem editörüne bağla |
| `F4-021` | 20 dk | 5 dk 43 sn | `f021523` | pencereli RMS ve envelope hesabını ekle |
| `F4-022` | 15 dk | 9 dk 25 sn | `8d661a5` | RMS/envelope pencere kontrollerini bağla |
| `F4-023` | 20 dk | 4 dk 27 sn | `2e15fcd` | phase unwrap hesabını ekle |
| `F4-024` | 15 dk | 3 dk 4 sn | `cc867bf` | phase unwrap parametrelerini bağla |
| `F4-025` | 20 dk | 5 dk 11 sn | `1db9f61` | resample/decimate işlemini ekle |
| `F4-026` | 15 dk | 6 dk 12 sn | `0c72609` | resample hedef frekans kontrolünü bağla |
| `F4-027` | 20 dk | 5 dk 29 sn | `5503651` | low-pass filtre hesabını ekle |
| `F4-028` | 15 dk | 2 dk 59 sn | `4d1828e` | low-pass cutoff ve order sınırlarını doğrula |
| `F4-029` | 15 dk | 5 dk 35 sn | `adfaa03` | low-pass araç alanlarını bağla |
| `F4-030` | 20 dk | 3 dk 53 sn | `591590c` | high-pass filtre hesabını ekle |
| `F4-031` | 15 dk | 3 dk 15 sn | `d11ee8a` | high-pass sınır ve transient davranışını doğrula |
| `F4-032` | 15 dk | 25 dk 36 sn | `2e75269` | high-pass seçimini araç kartına bağla |
| `F4-033` | 20 dk | 4 dk 39 sn | `a8022a9` | band-pass filtre hesabını ekle |
| `F4-034` | 15 dk | 2 dk 31 sn | `233de3d` | band-pass alt/üst sınırlarını doğrula |
| `F4-035` | 15 dk | 4 dk 21 sn | `aef54fb` | band-pass iki cutoff alanını bağla |
| `F4-036` | 20 dk | 4 dk 41 sn | `30c576e` | notch filtre hesabını ekle |
| `F4-037` | 15 dk | 2 dk 39 sn | `d4db9c1` | notch frekans ve Q sınırlarını doğrula |
| `F4-038` | 15 dk | 6 dk 30 sn | `a50d093` | notch frekans ve Q kontrollerini bağla |
| `F4-039` | 20 dk | 4 dk 3 sn | `ac1c6cc` | window üretimi ve normalizasyonunu ekle |
| `F4-040` | 20 dk | 3 dk 53 sn | `4e44bc6` | tek taraflı FFT hesabını ekle |
| `F4-041` | 20 dk | 3 dk 17 sn | `8be5420` | FFT, dB ve Nyquist doğrulamalarını ekle |
| `F4-042` | 20 dk | 8 dk 11 sn | `637ad26` | seçili aralık FFT'sini mockup alt grafiğine bağla |
| `F4-043` | 20 dk | 4 dk 31 sn | `09e47aa` | Welch PSD hesabını ekle |
| `F4-044` | 15 dk | 3 dk 38 sn | `77058be` | PSD pencere, overlap ve birim sınırlarını doğrula |
| `F4-045` | 20 dk | 9 dk 46 sn | `f3e6734` | spectrum sekmesinde PSD görünümünü ekle |
| `F4-046` | 20 dk | 4 dk 24 sn | `f2ac165` | STFT ve spektrogram matrisini hesapla |
| `F4-047` | 20 dk | 3 dk 41 sn | `33a84cd` | STFT kenar, overlap ve eksen eşlemesini doğrula |
| `F4-048` | 20 dk | 10 dk 48 sn | `034eebc` | mockup orta spektrogramını sonuçlara bağla |
| `F4-049` | 15 dk | 6 dk 59 sn | `ec7bc33` | spektrogram renk ölçeği kontrollerini ekle |
| `F4-050` | 20 dk | 4 dk 31 sn | `35e413f` | waterfall zaman dilimi modelini ekle |
| `F4-051` | 20 dk | 8 dk 48 sn | `813ff71` | waterfall görünümünü ekle |
| `F4-052` | 20 dk | 8 dk 12 sn | `f42dd8b` | zaman serisi, STFT, FFT ve istatistiği birlikte bağla |
| `F4-053` | 20 dk | 5 dk 45 sn | `30c9032` | memory mapping üzerinden blok okuma ekle |
| `F4-054` | 20 dk | 23 dk 38 sn | `e107020` | yalnız görünür zaman bloklarını yükle |
| `F4-055` | 20 dk | 22 dk 55 sn | `2957e2d` | piksel bütçesini analiz verisinden ayır |
| `F4-056` | 20 dk | 2 dk 50 sn | `2d10f87` | dar darbeleri koruyan min/max azaltımı ekle |
| `F4-056` | 20 dk | 1 dk 42 sn | `c99e482` | bütçe doğrulaması ve kalite tiplerini netleştir |
| `F4-057` | 20 dk | 55 sn | `f4142eb` | çok seviyeli min/max özet blokları üret |
| `F4-058` | 20 dk | 18 dk 25 sn | `b584eea` | viewport için uygun özet seviyesini seç |
| `F4-059` | 20 dk | 49 dk 16 sn | `fdb48ec` | bellek sınırlı LRU cache ekle |
| `F4-060` | 20 dk | 6 dk 31 sn | `db19ff2` | cache anahtarına kaynak ve işlem sürümünü ekle |
| `F4-061` | 20 dk | 7 dk 45 sn | `d34eb2f` | render sıklığını ve gizli panel güncellemelerini sınırla |
| `F4-062` | 20 dk | 4 dk 10 sn | `3c1ae1d` | sorgu, render ve indeks sürelerini kaydet |
| `F4-063` | 20 dk | 3 dk 47 sn | `fad60f0` | büyük dosya üretim koşusunu hazırla |
| `F4-059` | 20 dk | 44 dk 9 sn | `dd76eed` | bellek sınırlı LRU cache ekle |
| `F4-059` | 20 dk | 5 dk 11 sn | `a7ac0ee` | girdi sınırı, katı boyut denetimi ve ölçülen bütçe raporu |
| `F4-060` | 20 dk | 24 dk 28 sn | `49bee2f` | –F4-063 paralel hattını main ile birleştir |
| `F4-064` | 20 dk | 20 dk 18 sn | `3ce9ff3` | büyük dosya benchmark koşusunu hazırla |
| `F4-065` | 20 dk | 14 dk 39 sn | `a214d49` | büyük dosya koşusunun sonuçlarını değerlendir |
| `F4-066` | 20 dk | 6 dk 5 sn | `ff71532` | indeks kesintisi ve cache kurtarmayı doğrula |
| `F4-067` | 15 dk | 7 dk 59 sn | `f0bacb2` | profil sonucuyla native hızlandırma ADR'sini yaz |
| `F4-068` | 20 dk | 7 dk 5 sn | `d990af8` | derivedChannelDefinition modelini ekle |
| `F4-069` | 20 dk | 6 dk 28 sn | `72d4001` | türetilmiş kanalları repository'ye ekle |
| `F4-070` | 20 dk | 7 dk 13 sn | `903cff9` | sınırlı aritmetik formül ayrıştırıcısını ekle |
| `F4-071` | 20 dk | 6 dk 41 sn | `610252d` | formül değerlendirmesini kanal dizilerine bağla |
| `F4-072` | 20 dk | 8 dk 17 sn | `2fa0bab` | formül ifade ve kaynak sınırlarını doğrula |
| `F4-073` | 20 dk | 185 dk 33 sn | `6055cbe` | custom sekmesine basit formül editörü ekle |
| `F4-074` | 15 dk | 6 dk 33 sn | `26c067c` | annotation ve bookmark modelini ekle |
| `F4-075` | 20 dk | 12 dk 32 sn | `22bb787` | bookmark ekleme, düzenleme ve silmeyi bağla |
| `F4-076` | 20 dk | 10 dk 28 sn | `d776853` | analiz oturumuna zincir ve annotation kaydını ekle |
| `F4-077` | 20 dk | 11 dk 4 sn | `b905a06` | analiz oturumunu ve türetilmiş kanalları yükle |
| `F4-078` | 20 dk | 12 dk 26 sn | `878ac98` | taşınmış kaynaklar için yeniden konumlandırma ekle |
| `F4-079` | 20 dk | 12 dk 2 sn | `41ebcb1` | işlem zinciri ve annotation undo/redo ekle |
| `F4-080` | 20 dk | 54 dk 3 sn | `9c79b9d` | bIT durum süresi ve değişim trendini hesapla |
| `F4-081` | 20 dk | 11 dk 29 sn | `7b23f1d` | bIT/Status trend görünümünü ekle |
| `F4-082` | 20 dk | 6 dk 58 sn | `e31dd09` | grafik penceresini ayırma ve geri takmayı ekle |
| `F4-083` | 20 dk | 8 dk 28 sn | `bf8122f` | çoklu monitör konumlarını kaydet ve sınırla |
| `F4-084` | 20 dk | 13 dk 37 sn | `62075d4` | event/BIT metadata'sını JSON dışa aktar |
| `F4-085` | 15 dk | 13 dk 19 sn | `6160b96` | tSV ayırıcı seçimini CSV akışına ekle |
| `F4-086` | 20 dk | 9 dk 23 sn | `487042b` | statik grafiği PDF olarak dışa aktar |
| `F4-087` | 20 dk | 6 dk 57 sn | `38df9cd` | sinüs, chirp, noise ve impulse referanslarını çalıştır |
| `F4-088` | 20 dk | 10 dk 54 sn | `35a2eb4` | kaydet/aç sonrası analiz tekrarını doğrula |
| `F4-089` | 20 dk | 14 dk 53 sn | `374b0a1` | çalışan analiz panosunu mockup ile karşılaştır |
| `F4-091` | 20 dk | 21 dk 30 sn | `c6f084e` | profil B kayıt indeksini kur |
| `F4-092` | 20 dk | 9 dk 45 sn | `c3f559e` | profil B zaman sorgusunu indeksle sınırla |
| `F4-093` | 20 dk | 10 dk 49 sn | `f7c4bd1` | büyük dosya koşusunu tekrarla ve kararı güncelle |
| `F4-094` | 20 dk | 3 dk 56 sn | `c6d0377` | özet piramidini NumPy blok işlemleriyle hızlandır |
| `F4-095` | 20 dk | 42 dk 12 sn | `aeeaaf6` | büyük çizim aralıklarını sınırlı bellekle indirgeme |
| `F4-096` | 20 dk | 6 dk 57 sn | `a1127c3` | özet ve akış düzeltmeleri sonrası performansı doğrula |
| `F4-090` | 15 dk | 7 dk 10 sn | `587b1c9` | analiz milestone kabulünü kapat ve major sürümü hazırla |
| `F5-001` | 20 dk | 9 dk 43 sn | `1de7d02` | canlı paket ve bağlantı sözleşmesini tamamla |
| `F5-002` | 20 dk | 7 dk 43 sn | `0207c61` | bağlantı durum makinesini ekle |
| `F5-003` | 20 dk | 10 dk 10 sn | `183c36d` | dosyadan LiveSource replay adaptörünü ekle |
| `F5-004` | 20 dk | 8 dk 0 sn | `8ee9f24` | replay zamanlama ve durdurmayı doğrula |
| `F5-005` | 20 dk | 7 dk 33 sn | `c22c585` | uDP alıcı bağlantısını ekle |
| `F5-006` | 20 dk | 12 dk 30 sn | `6e29b08` | uDP paketlerini decoder'a bağla |
| `F5-007` | 20 dk | 6 dk 46 sn | `44530db` | tCP bağlantı ve okuma akışını ekle |
| `F5-008` | 20 dk | 9 dk 6 sn | `7cbad33` | tCP parçalı ve birleşik paket ayrımını ekle |
| `F5-009` | 20 dk | 9 dk 46 sn | `7649b6b` | serial port ayar ve bağlantısını ekle |
| `F5-010` | 20 dk | 11 dk 20 sn | `bec3140` | serial paket sınırı ve timeout işleyişini ekle |
| `F5-011` | 20 dk | 7 dk 59 sn | `afa3a83` | üç adaptör için ortak sözleşme kontrolü ekle |
| `F5-012` | 20 dk | 7 dk 51 sn | `e61f435` | sıra numarasından paket kaybını hesapla |
| `F5-013` | 20 dk | 12 dk 30 sn | `d6a1f5e` | canlı cihaz zamanını kanonik zamana bağla |
| `F5-014` | 20 dk | 7 dk 49 sn | `2419608` | sabit kapasiteli ring buffer ekle |
| `F5-015` | 20 dk | 7 dk 17 sn | `211f407` | zaman penceresine göre buffer sorgula |
| `F5-016` | 20 dk | 8 dk 9 sn | `b083765` | kuyruk sınırı ve drop politikasını uygula |
| `F5-017` | 20 dk | 6 dk 56 sn | `953a1ab` | sınırlı otomatik yeniden bağlanma ekle |
| `F5-018` | 20 dk | 13 dk 15 sn | `3928614` | bağlantı ve buffer ayarlarını kaydet |
| `F5-019` | 20 dk | 13 dk 42 sn | `5f09d0d` | connect ve Disconnect eylemlerini bağla |
| `F5-020` | 20 dk | 37 dk 49 sn | `f56d4f9` | paket kaybı, kuyruk ve buffer durumunu göster |
| `F5-021` | 20 dk | 6 dk 47 sn | `b9acdac` | canlı akışı ortak repository'ye bağla |
| `F5-022` | 20 dk | 14 dk 57 sn | `f038866` | canlı veriyi mevcut grafik panellerine bağla |
| `F5-023` | 15 dk | 9 dk 57 sn | `ed3af4f` | canlı sona takip etme ve sabit aralık seçimini ekle |
| `F5-024` | 20 dk | 6 dk 34 sn | `735858f` | canlı ve playback mod geçişlerini denetle |
| `F5-025` | 20 dk | 8 dk 7 sn | `de1108e` | sürümlü dosya header yazıcısını ekle |
| `F5-026` | 20 dk | 6 dk 40 sn | `fb2985e` | data kayıt serileştirmesini ekle |
| `F5-027` | 20 dk | 8 dk 34 sn | `36ffece` | 125 ms kayıt biriktirme sınırlarını ekle |
| `F5-028` | 20 dk | 8 dk 12 sn | `031b53b` | disk yazma kuyruğunu canlı akıştan ayır |
| `F5-029` | 20 dk | 11 dk 54 sn | `5a30d4b` | flush ve güvenli dosya kapatmayı ekle |
| `F5-030` | 20 dk | 9 dk 49 sn | `c70c883` | disk dolması ve yazma hatasını işle |
| `F5-031` | 20 dk | 8 dk 24 sn | `1b477d1` | boyut ve isim sınırında yeni dosyaya geç |
| `F5-032` | 20 dk | 44 dk 48 sn | `3f7817b` | record ve Stop durumunu ana ekrana bağla |
| `F5-033` | 20 dk | 13 dk 35 sn | `c896ddb` | bağlantı kesilmesinde kayıt davranışını uygula |
| `F5-034` | 20 dk | 15 dk 36 sn | `739dd3f` | canlı BIT ve TX olaylarını panoya bağla |
| `F5-035` | 20 dk | 13 dk 28 sn | `0d3e809` | canlı kayıt dosyasını tekrar açarak karşılaştır |
| `F5-036` | 20 dk | 14 dk 29 sn | `ff78efd` | burst, kayıp ve sıra dışı paket simülatörü ekle |
| `F5-037` | 20 dk | 18 dk 51 sn | `5f70478` | burst ve bağlantı kesintisi sonuçlarını doğrula |
| `F5-038` | 20 dk | 59 dk 50 sn | `55f0352` | uzun süreli canlı kayıt koşusunu hazırla |
| `F5-039` | 20 dk | 18 dk 18 sn | `ef1fd4b` | dayanıklılık koşusu raporunu değerlendir |
| `F5-040` | 20 dk | 16 dk 15 sn | `bd6c68f` | canlı modda mockup pano davranışını kontrol et |
| `F5-041` | 15 dk | 16 dk 59 sn | `552aac4` | canlı veri milestone kabulünü kapat ve major sürümü hazırla |
| `F6-001` | 20 dk | 48 dk 51 sn | `cc7269f` | paketleme aracı ve dağıtım biçimi ADR'sini tamamla |
| `F6-002` | 20 dk | 13 dk 54 sn | `8bcfe9e` | windows paketleme yapılandırmasını ekle |
| `F6-003` | 20 dk | 23 dk 18 sn | `a775408` | qt plugin, tema ve ikon kaynaklarını pakete ekle |
| `F6-004` | 20 dk | 20 dk 35 sn | `5ff0cf9` | tek komutluk paket üretim akışını ekle |
| `F6-005` | 20 dk | 12 dk 11 sn | `c75f5a5` | temiz Windows ortamında paket açılışını kontrol et |
| `F6-006` | 20 dk | 21 dk 25 sn | `4a36a31` | paketli uygulamada BIN ve export akışını kontrol et |
| `F6-007` | 20 dk | 13 dk 56 sn | `917fa72` | ınstaller oluşturma adımını ekle |
| `F6-008` | 20 dk | 12 dk 35 sn | `ff87833` | kurulum, yükseltme ve kaldırmayı kontrol et |
| `F6-009` | 15 dk | 11 dk 27 sn | `8c60e3c` | artefakt checksum ve sürüm manifestini üret |
| `F6-010` | 20 dk | 11 dk 8 sn | `34cd500` | aynı girdilerle paket üretimini karşılaştır |
| `F6-011` | 20 dk | 23 dk 54 sn | `8dc15fd` | offline bağımlılık paketleme akışını hazırla |
| `F6-012` | 20 dk | 10 dk 14 sn | `d7fa44e` | imzalama gereksinimini yayın akışına bağla |
| `F6-013` | 20 dk | 19 dk 31 sn | `4f62dc2` | coverage raporu ve eşiklerini CI'a ekle |
| `F6-013` | 20 dk | 25 sn | `b18fc4e` | plan işaretini düzelt |
| `F6-014` | 20 dk | 11 dk 30 sn | `0646204` | bağımlılık taramasını CI'a ekle |
| `F6-015` | 20 dk | 26 dk 54 sn | `1c510cb` | küçük performans smoke kontrolünü CI'a ekle |
| `F6-016` | 20 dk | 9 dk 3 sn | `2b6a8b6` | windows paket smoke kontrolünü CI'a ekle |
| `F6-017` | 20 dk | 10 dk 22 sn | `0760993` | sürüm artefaktı ve checksum iş akışını ekle |
| `F6-018` | 15 dk | 11 dk 56 sn | `b3fef3a` | merge ve release kalite kapılarını belgeye bağla |
| `F6-019` | 20 dk | 9 dk 39 sn | `74d523b` | tanılama paketi içerik listesini üret |
| `F6-020` | 20 dk | 9 dk 17 sn | `8bdaa32` | tanılama önizleme ve dışa aktarımını ekle |
| `F6-021` | 20 dk | 9 dk 47 sn | `2a169c0` | son geçerli workspace kurtarmasını ekle |
| `F6-022` | 20 dk | 14 dk 6 sn | `07ced64` | tekrarlı aç/kapat ve playback koşusunu hazırla |
| `F6-023` | 20 dk | 9 dk 5 sn | `eb650f2` | aç/kapat dayanıklılık sonuçlarını değerlendir |
| `F6-024` | 20 dk | 9 dk 55 sn | `fcfe6fb` | mockup üzerinden ana ekran kullanım kılavuzunu yaz |
| `F6-025` | 20 dk | 9 dk 9 sn | `9b4cb35` | filtre ve spektral analiz kullanım örneğini yaz |
| `F6-026` | 20 dk | 69 dk 41 sn | `4717142` | canlı bağlantı ve kayıt kullanım örneğini yaz |
| `F6-027` | 20 dk | 14 dk 51 sn | `e7b92eb` | format ve decoder kılavuzunu güncelle |
| `F6-028` | 15 dk | 13 dk 34 sn | `f0060f4` | klavye, mouse ve ölçekleme kılavuzunu tamamla |
| `F6-029` | 15 dk | 14 dk 31 sn | `8f8e50e` | bilinen sorunları ve veri sınırlamalarını yaz |
| `F6-030` | 20 dk | 18 dk 3 sn | `b4855ce` | paketli uygulamada kullanıcı kabul turunu kaydet |
| `F6-031` | 20 dk | 30 dk 4 sn | `d5bf557` | paketli ana ekranı referans mockup ile karşılaştır |
| `F6-032` | 20 dk | 15 dk 57 sn | `953ded5` | release ve geri dönüş prosedürünü yaz |
| `F6-033` | 15 dk | 13 dk 54 sn | `4e11786` | major sürüm notları ve milestone özetini hazırla |
| `F6-035` | 20 dk | 18 dk 43 sn | `b8c7d02` | kalite bayraklarını dışa aktarmaya ve paket denetimine taşı |
| `F6-034` | 15 dk | 12 dk 10 sn | `6e551f6` | dağıtım milestone kabulünü kapat ve major sürümü hazırla |
| `-` | — | 5 dk 4 sn | `3f2074b` | Bölüm 5, 6.4 ve 8.1 kontrol listelerini uygulamaya karşı doğrula |
| `-` | — | 4 dk 26 sn | `d3db794` | kalan bölüm içi kontrol listelerini uygulamaya karşı doğrula |
| `-` | — | 14 dk 8 sn | `83729be` | Profil B kayıt dizisi teşhislerini ekle |
| `-` | — | 27 dk 57 sn | `dc0aef2` | kanal ikonları, sağ tık menüsü ve boş grafik yönlendirmesi |
| `-` | — | 11 dk 30 sn | `bd499f4` | korelasyon toleransını yapılandırılabilir yap |

**380 commit · olculen toplam 4688 dk 26 sn · olculemeyen 1 (ilk commit)**

<!-- SURELER:BITIS -->

## 2. İşlerin durumu

Durum kodları: `TAMAM` · `ATLANDI` (engel var) · `KISMİ` (varsayımla yapıldı, doğrulama bekliyor)

| İş | Durum | Not |
| --- | --- | --- |
| `F0-001` | TAMAM | `.gitattributes` da eklendi: golden `.bin` fixture'larının satır sonu dönüşümüyle bozulmaması için gerekliydi. |
| `F0-002` | TAMAM | Beş senaryo. |
| `F0-003` | TAMAM | Depoda gerçek `.bin` yok; E-01..E-10 eksik girdiler işaretlendi. |
| `F0-004` | **KISMİ** | Header sözleşmesi Bölüm 8.2 **taslağına** göre yazıldı; gerçek format dokümanı (D-02) gelince karşılaştırılmalı. |
| `F0-005` | **KISMİ** | Aynı gerekçe: 64 byte kayıt sözleşmesi taslak kaynaklı. |
| `F0-006` | TAMAM | Profiller arası ad sarması çelişkisi bulundu ve giderildi. Süreye, commit mesajı ile içerik uyuşmadığı için yapılan düzeltme (amend) dahil. |
| `F0-007` | **KISMİ** | Kanal eşlemesi **öneri**dir; gerçek kanal kataloğu (D-06) ve BIT test kataloğu (D-07) yok. Mockup 8 BIT alt sistemi gösteriyor, öneri harita 3 grup — genişletilmeli. |
| `F0-008` | **KISMİ** | CRC algoritması seçildi (ADR-011) ama donanım onayı yok (D-05). |
| `F0-009` | TAMAM | Beklenen baytlar üretilip doğrulandı; float32 round-trip kayıpsız. |
| `F0-010` | TAMAM | Dört zorunlu senaryoya ek olarak K-05 ve K-06 tanımlandı. |
| `F0-011` | TAMAM | ADR-003. Süre, iki kez başarısız olan kabuk komutunun yeniden yazılmasını içerir. |
| `F0-012` | TAMAM | Mockup görseli okundu; planda olmayan kanallar ve 8 BIT alt sistemi tespit edildi. |
| `F0-013` | TAMAM | Etkileşim ve görsel kabul listesi; maddeler MVP/analiz/canlı aşamasına etiketli. |
| `F0-014` | **KISMİ** | Hedef ölçüm bilgisayarı bilinmiyor (D-15). GUI ölçümleri (P-04/P-05/P-08) iskelet olmadan yapılamadı. |
| `F0-015` | TAMAM | D-01..D-25 kütüğü. |
| `F0-016` | TAMAM | ADR-001..012 iş/sürüm eşlemesi. |
| `F0-017` | TAMAM | Faz 0 kabulü; gerçek veri eksikleri "doğrulanmadı" olarak ayrı bölümde. |
| `F1-001` | TAMAM | `requires-python` geçici olarak `>=3.9` (D-20). Paket kurulumu ve VERSION eşleşmesi doğrulandı. |
| `F1-002` | TAMAM | `-Recreate` ile sıfırdan koşuldu. |
| `F1-003` | TAMAM | Markdown dosyaları biçimlendirici kapsamı dışında tutuldu. |
| `F1-004` | TAMAM | Pyright **strict** modda 0 hata. Kilit dosyası ilk kez gerçekten kullanılabilir hâle geldi (`-Locked`). |
| `F1-005` | TAMAM | Katman kuralı artık testle korunuyor (`test_layering.py`). Kilit dev/gui olarak ikiye ayrıldı. |
| `F1-006` | TAMAM | CI ilk koşuda satır sonu farkı yüzünden düştü; `.gitattributes` `eol=lf` ile düzeltildi. |
| `F1-007` | TAMAM | Pencere yalnız **offscreen** doğrulandı; kullanıcının ekranında görünür pencere açılmadı. |
| `F1-008` | TAMAM | KeyboardInterrupt hata sayılmıyor. |
| `F1-009` | TAMAM | Bozuk ayar dosyası `.bozuk` uzantısıyla saklanıyor, atomik yazma. |
| `F1-010` | TAMAM | Ham sensör verisi filtreyle engelleniyor. Testlerin gerçek AppData'ya yazması da bu iş sırasında bulunup düzeltildi. |
| `F1-011` | TAMAM | Doğrulama kurucuda; geçersiz kanal oluşturulamıyor. |
| `F1-012` | TAMAM | Zaman/değer uzunluk tutarsızlığı kurucuda yakalanıyor. |
| `F1-013` | TAMAM | Ters aralık kurucuda reddediliyor. |
| `F1-014` | TAMAM | Tanınmayan BIT kodu UNKNOWN; PASS varsayılmıyor. |
| `F1-015` | TAMAM | Türetme, fixture beklentisiyle birebir aynı sonucu veriyor (250–750 ms). |
| `F1-016` | TAMAM | Sözleşmeyi karşılayan FakeRepository yazıldı; gerçek repository'ler aynı testlere tabi olacak. |
| `F1-017` | TAMAM | Modülün Qt yüklemediği ayrı süreçte doğrulanıyor. |
| `F1-018` | TAMAM | Nyquist üstü frekans reddediliyor; zaman ekseni tamsayı aritmetiğiyle. |
| `F1-019` | TAMAM | Seed sabit; chirp fazı frekansın integrali olarak hesaplanıyor. |
| `F1-020` | TAMAM | Sorgu sınırları yarı açık; aralık dışı sorgu boş parça döndürüyor. |
| `F1-021` | TAMAM | Olay zamanları sabit ve bilinir; rastgele olay üretilmiyor. |
| `F1-022` | TAMAM | Ölçülen sütunlar 1520 px pencerede tam 200 / 1008 / 300 px. |
| `F1-023` | **KISMİ** | Beş menü kuruldu ama **mockup dört menü gösteriyor** (Analysis yok). Karar bekliyor; `layout-map.md` §9'da kayıtlı. |
| `F1-024` | TAMAM | Ağaç hiyerarşik; arama derin ağaçta çalışıyor. |
| `F1-025` | TAMAM | Qt "tabified dock" yerine gerçek QTabWidget seçildi; gerekçe commit'te. |
| `F1-026` | TAMAM | Log ile Events ayrı; olaylar log'a yazılmıyor. |
| `F1-027`–`F1-044` | TAMAM | Faz 1'in kalan işleri; iş bazında not ve kanıtlar `docs/release/ms-02-app-shell.md` §2–§4'te. `F1-043` P-04 sapmasını ölçtü (1M noktada 7,4 FPS) — hâlâ açık, `F4-056`/`F4-057`'ye bağlı. |
| `F2-001`–`F2-041` | TAMAM | Faz 2'nin tamamı; iş bazında çıktı/commit tablosu ve kabul kanıtları `docs/release/ms-03-bin-reader.md` §2–§4'te. Bu tablo orada tutuluyor, burada tekrarlanmıyor (iki kopya kaçınılmaz olarak birbirinden ayrışır). |
| `F2-013`/`F2-014` | **KISMİ** | CRC hesaplaması ve doğrulaması çalışıyor ama algoritma **bizim kararımız** (ADR-011 durumu "Önerildi", D-05). Gerçek cihaz farklı CRC kullanıyorsa yeniden yazılır. |
| `F2-019` | **KISMİ** | Kanal kataloğu `channel-map.md` §2'deki **öneriyi** kodluyor (D-06). Gerçek katalog gelince slot sırası ve birimler değişecek. |
| `F2-025`–`F2-027` | **KISMİ** | Tick/wraparound/drift yalnız sentetik değerlerle ve ADR-003'ün kendi referans örnekleriyle doğrulandı. Profil A ham sayaç taşımadığı için (`tick_hz = 0`) bu yollar hiçbir gerçek dosyayla çalıştırılmadı; gerçek `tick_hz` bilinmiyor (D-09). |

## 3. Bu koşuda bulunan ve düzeltilen sorunlar

Hiçbiri plan işi değildi; çalışırken ortaya çıktı.

| Sorun | Nerede bulundu | Çözüm |
| --- | --- | --- |
| İki profil arasında kayıt adı sarma çelişkisi | `F0-006` | Sarma kaldırıldı, tek kural `timing-and-naming.md` |
| Boşluklu dosyada `32 + n*64` offset formülü yanlış kayda gidiyor | `F0-006` analiz | Uyarı yazıldı; K-03 fixture'ı bunu yakalıyor |
| İndeks olmadan 2,6 GiB dosyada 5 s açılış hedefi tutmuyor | `F0-014` ölçüm | `RecordIndex` ön koşul ilan edildi |
| Mockup'ta planda olmayan kanallar ve 8 BIT alt sistemi | `F0-012` | `layout-map.md` §9'a kaydedildi, D-06/D-07'ye bağlandı |
| Bağımlılık kilidi hiçbir akış tarafından kullanılmıyordu | `F1-004` | `setup-dev.ps1 -Locked` eklendi |
| CI'da `ruff format` düşüyor, yerelde geçiyordu (satır sonu) | `F1-006` CI | `.gitattributes` `eol=lf` |
| CI'da `pyright` düşüyor, yerelde geçiyordu (sürüm kayması) | `F1-009` CI | ruff ve pyright sabit sürüme çekildi |
| Testler kullanıcının gerçek `%LOCALAPPDATA%` ve `%APPDATA%` yollarına yazıyordu | `F1-010` | Ortam değişkeni yönlendirmesi + conftest; oluşan klasör silindi |
| Bir GUI testinden sonra `caplog` testleri sessizce bozuluyordu | `F1-010` | conftest her testten sonra logger durumunu geri koyuyor |
| CI'da `pyright` 3.12 ayağında düşüyor, 3.9'da geçiyordu (numpy sürümü) | `F1-012` CI | numpy `>=1.26,<2.1`'e sabitlendi; CI'a sürüm raporlama adımı eklendi |
| Sarmalanmayan `QLabel` panelin asgari genişliğini şişiriyordu (sağ sütun 300 yerine 424 px) | `F1-022` | Yer tutucu etiketler word-wrap edildi |
| Menülere Python referansı tutulmayınca PySide nesneyi serbest bırakıyordu ("C++ object already deleted") | `F1-023` | Menüler pencerede saklanıyor |
| Kanal yolunda `/` hem ayraç hem ad parçasıydı; ağaçta `"Vehicle "` diye bozuk grup çıkıyordu | `F1-024` | Yol `Vehicle/Voltage` yapıldı, gösterim etiketi `GROUP_LABELS` ile eşlendi |
| Qt tabified dock'ta aynı anda tek dock görünür sayıldığı için "kartlar duruyor mu" doğrulanamıyordu | `F1-025` | Sağ sütunda gerçek `QTabWidget` kullanıldı |
| CI'da `pyright` yalnız 3.12 ayağında düşüyordu (PySide6 taslak farkı) | CI #26–#30 | PySide6 sabitlendi, `None` kontrolleri geri kondu; teşhis için pyright annotation adımı eklendi |
| Offscreen Qt'de hiç yazı tipi yok; ekran görüntüsünde **tüm metinler kutu** çıkıyordu | `F1-032` görsel doğrulama | `QT_QPA_FONTDIR` conftest'te ve `tools/screenshot.py` içinde ayarlanıyor. Metin genişliği asgari widget boyutunu belirlediği için bu yerleşim testlerini de etkiliyordu. |
| Kabuk aracı heredoc içindeki `\xNN` kaçış dizilerini kendisi yorumlayıp kaynak dosyaya gerçek NUL bayt yazıyordu | `F2-010` fixture üreticisi | `\x00` yerine `bytes(3)`; dosya içeriği Write/Edit araçlarıyla yazılıyor |
| `X \| Y` tip birleşimi Python 3.9'da çalışma anında kurulamıyor (takma ad gövdede değerlendiriliyor) | `F2-011` | `typing.Union` kullanıldı; `from __future__ import annotations` yalnız açıklamaları erteliyor |
| Geçerli fixture formülü test yardımcısı ile araçta iki kez yazılmıştı | `F2-016`, `F2-018` | Formül `tools/make_fixture.py`'ye taşındı; `tests/golden_bytes.py` oradan içe aktarıyor |
| `Event` modeli parser teşhislerinin bayt offsetini taşıyamıyordu | `F2-024` | `Event.source_offset` eklendi (geriye dönük uyumlu, negatif değer reddediliyor) |
| Belge BIT grubunu `Thermal` yazıyor, kataloğun adı `Thermal Management` | `F2-039` | Test bit numarası ve durumu tam eşleştiriyor, ad için önek kontrolü yapıyor; fark tutanakta |
| Milestone testinde son kaydın offseti `dosya_boyutu - 64` varsayılmıştı; v2 (68 byte) ve kesik kuyruklu dosyada yanlış | `F2-041` | İlk kaydın offseti (= header boyutu) kullanılıyor |

## 3b. ÇÖZÜLDÜ: CI'nin Python 3.12 ayağında pyright hatası

**Durum: KAPALI.** CI üç işte de yeşil (koşu #31).

**Kök neden:** PySide6 tip taslakları sürüme göre değişiyor. Bir sürümde
`QTreeWidgetItem.child()` / `.parent()` `QTreeWidgetItem`, diğerinde
`QTreeWidgetItem | None` dönüyor. `F1-024`'te 3.9 ortamındaki taslağa uyup
`is not None` kontrollerini kaldırmıştım; aynı kod 3.12 ayağında
`reportOptionalMemberAccess` ve `reportArgumentType` hataları verdi. Kontroller
runtime açısından **doğruydu** — Qt üst düzey öğede `parent()` için gerçekten
null döndürüyor.

**Çözüm:** PySide6 `==6.10.3` olarak sabitlendi ve `None` kontrolleri geri kondu.
Taslak yanlış olduğunda doğru kontrolü hataya çeviren `reportUnnecessaryComparison`
stil kuralı kapatıldı; güvenlik kuralları açık bırakıldı.

**Teşhisi mümkün kılan adım:** CI job log'ları kimlik doğrulaması istiyor, ama
**annotations API'si istemiyor**. Bu yüzden `tools/pyright_annotations.py` eklendi:
pyright'ın JSON çıktısını `::error file=...,line=...` komutlarına çeviriyor.
İlk denemede annotation üretilmedi çünkü adım `bash -e` ile koşuyordu ve pyright
hata bulunca 1 döndürüp betiği durduruyordu; çıkış kodu yutulunca hata metni
okunabildi. Kalıcı fayda: pyright bulguları artık PR'larda satır satır görünüyor.

**Ders:** denetleyici davranışını değiştiren her bağımlılık (ruff, pyright, numpy,
PySide6) sabit sürümde tutulur; aralık bırakmak "bende geçti, CI'da kaldı"
farkını üretiyor.

## 3c. Takip edilen küçük iş

- **XYZ renk eşlemesi tek kanallı panelde uygulanmıyor.** `F1-030` kabulü
  "XYZ serileri mavi/turuncu/yeşil" diyor ve bu kural, üç ekseni **aynı grafikte**
  çizerken geçerli (mockup'taki `Acceleration (XYZ)` kartı). Tek kanallı
  `PlotPanel` şu an kanal kimliğinden kararlı bir renk seçiyor; ekran
  görüntüsünde `Accel X` mavi değil camgöbeği çıkıyor. Çok serili grafik işine
  (`F3-*`) geldiğinde seri sırasına göre renk atanmalı. Kural
  `ui/status_icons.py` `channel_color(..., index=...)` ile hâlihazırda test
  edilmiş durumda.

## 4. Açık engeller

Ayrıntı: `docs/notes/open-decisions.md` (D-01..D-25) ve `docs/format/inventory.md` §2.

- **D-01/D-02 — gerçek `.bin` kaydı ve resmî format dokümanı yok.** Faz 0'ın format işleri
  taslağa göre yazıldı ve `KISMİ` sayıldı. Sentetik doğrulama gerçek donanım kanıtı sayılmaz.
- **D-05 — CRC tanımı yok.** ADR-011 öneri; donanım onayı bekliyor.
- **D-06/D-07 — kanal ve BIT test katalogları yok.**
- **D-09 — cihaz zaman kaynağı bilinmiyor.**
- **D-15 — hedef ölçüm bilgisayarı bilinmiyor.**
- **D-20 — Python 3.12 bu makinede kurulu değil** (yalnız 3.9.13 var). Kurulum sistem
  değişikliği olduğu için yapılmadı. **Kod 3.12'de doğrulanıyor:** CI matrisi hem 3.9 hem
  3.12 ile koşuyor ve geçiyor. Eksik olan yalnız yerel geliştirme ortamı.

## 5. Ortam notları

- **Python:** yerel `python` → 3.9.13. `requires-python` geçici olarak `>=3.9`; CI 3.12'yi de
  doğruluyor.
- **Sanal ortam:** `.venv` (3.9.13). PySide6 6.10.3 + Qt 6.10.3 kurulu; GUI testleri
  `QT_QPA_PLATFORM=offscreen` ile koşuyor.
- **Uzak depo:** `origin` → `https://github.com/anti94/RecordVisualiser`. Her iş commit'i ve
  sürüm etiketi push ediliyor.

## 6. Kullanıcıya sorulacaklar

- `.claude/settings.local.json` izlenmiyor ve `.gitignore` içinde de yok. Yerel izin ayarlarının
  yanlışlıkla commit edilmemesi için ignore kuralına eklenmesi öneriliyor.
- `SONAR Veri Analiz Panosu Mockup’ı.7z` arşivi izlenmiyor; kaynak PNG depoda olduğu için gerekli
  görülmedi. Silinsin mi, kalsın mı?
- Python 3.12 yerel kuruluma ne zaman eklenebilir? (D-20)
- Faz 1'in kalan işleri plan sırasıyla mı ilerlesin, yoksa parser/fixture (Faz 2) öne mi alınsın?
