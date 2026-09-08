# Milestone kabul tutanağı — `ms/01-format-ready`

- **Faz:** 0 — Keşif ve format sözleşmesi
- **Sürüm:** `v0.17.0`
- **Etiketler:** `v0.17.0` ve `ms/01-format-ready` (aynı commit)
- **Tarih:** 2026-09-09
- **Kabul işi:** `F0-017`

## 1. Faz kabul ölçütü

Plan Bölüm 22.3: *"Format taslağı, sentetik/gerçek veri ayrımı, fixture beklentileri ve kabul
ölçütleri belgelenmiş olmalı."*

Bu faz **gerçek cihaz verisiyle doğrulama** talep etmez; taslağın, ayrımın ve beklentilerin
yazılı olmasını talep eder. Gerçek veri doğrulaması Faz 2 kabulüne aittir.

## 2. İşler ve çıktılar

| İş | Çıktı | Kanıt |
| --- | --- | --- |
| `F0-001` | Depo, `.gitignore`, `.gitattributes`, `VERSION` | `61e4fca`, `v0.1.0` |
| `F0-002` | `docs/scenarios.md` — beş senaryo | `80c49ac`, `v0.2.0` |
| `F0-003` | `docs/format/inventory.md` — envanter, E-01..E-10 | `985bceb`, `v0.3.0` |
| `F0-004` | `docs/format/profile-a.md` §2 — 32 B header | `4871335`, `v0.4.0` |
| `F0-005` | `docs/format/profile-a.md` §5 — 64 B kayıt | `713f6b7`, `v0.5.0` |
| `F0-006` | `docs/format/timing-and-naming.md` | `141bdd2`, `v0.6.0` |
| `F0-007` | `docs/format/channel-map.md` | `4e3aaa2`, `v0.7.0` |
| `F0-008` | `docs/adr/ADR-011-crc.md` | `e2b33ed`, `v0.8.0` |
| `F0-009` | `docs/format/fixture-valid-8records.md` | `c50bcb0`, `v0.9.0` |
| `F0-010` | `docs/format/fixture-corrupt.md` — K-01..K-06 | `df8cf80`, `v0.10.0` |
| `F0-011` | `docs/adr/ADR-003-time-base.md` | `250bd0c`, `v0.11.0` |
| `F0-012` | `docs/ui/layout-map.md` | `f144dea`, `v0.12.0` |
| `F0-013` | `docs/ui/acceptance-checklist.md` | `35c00df`, `v0.13.0` |
| `F0-014` | `docs/perf/budget.md` | `71bbb85`, `v0.14.0` |
| `F0-015` | `docs/notes/open-decisions.md` — D-01..D-25 | `5a833ce`, `v0.15.0` |
| `F0-016` | `docs/adr/README.md` | `86490c3`, `v0.16.0` |
| `F0-017` | Bu tutanak | `v0.17.0` |

## 3. Zorunlu kontroller

| # | Kontrol | Sonuç | Dayanak |
| --- | --- | --- | --- |
| 3.1 | Format taslağı iki profil için yazılı ve alan offsetleri tutarlı | **GEÇTİ** | `profile-a.md` (32/64 B), plan §8.3 (Profil B); struct boyutları hesaplanarak doğrulandı |
| 3.2 | 125 ms periyot ve `DataNNNNN` adlandırma kuralı tek kaynakta | **GEÇTİ** | `timing-and-naming.md`; iki profil arasındaki ad sarması çelişkisi giderildi |
| 3.3 | Sentetik / gerçek veri ayrımı belgelenmiş | **GEÇTİ** | `inventory.md` §1'de "depoda hiç `.bin` yok" açıkça yazılı; §3 sentetik listesi ayrı |
| 3.4 | Geçerli fixture beklentileri sayısal olarak tanımlı | **GEÇTİ** | `fixture-valid-8records.md`: 8 kayıt, 0–875 ms, 544 byte, SHA-256, tam hexdump |
| 3.5 | Bozuk fixture senaryoları ayrı ayrı tanımlı | **GEÇTİ** | `fixture-corrupt.md`: kesik header, kesik kayıt, sıra boşluğu, CRC hatası + 2 ek |
| 3.6 | Görsel kabul ölçütleri kontrol edilebilir | **GEÇTİ** | `layout-map.md` dokuz bölge + `acceptance-checklist.md` madde madde |
| 3.7 | Performans hedefleri ve ölçüm yöntemi kayıtlı | **GEÇTİ** | `budget.md` P-01..P-09, ölçüm kuralları, başlangıç ölçümleri |
| 3.8 | Açık kararlar ve dış bağımlılıklar görünür | **GEÇTİ** | `open-decisions.md` D-01..D-25, aciliyet sırası |
| 3.9 | ADR'ler iş ve sürüme bağlanmış | **GEÇTİ** | `adr/README.md` |
| 3.10 | Her iş kendi commit'i ve `vX.Y.0` etiketiyle kapandı | **GEÇTİ** | `v0.1.0` – `v0.17.0`, 17 etiket |

**Zorunlu kontrollerin tamamı geçti.**

## 4. Gerçek veriyle doğrulanmayan maddeler

> Bu bölüm kasıtlı olarak ayrıdır. Aşağıdakilerin hiçbiri "doğrulandı" sayılmaz ve hiçbiri
> zorunlu kontrol olarak işaretlenmemiştir.

| Konu | Durum | Neden doğrulanamadı |
| --- | --- | --- |
| `.bin` byte düzeni, endian, alan sırası | **DOĞRULANMADI** | Elde hiç gerçek kayıt yok (D-01) |
| Format sürümleri ve uyumluluk | **DOĞRULANMADI** | Resmî format dokümanı yok (D-02) |
| CRC algoritması ve kapsamı | **ÖNERİ** | Cihazın CRC kullanıp kullanmadığı bilinmiyor (D-05) |
| Kanal adları, birimler, gain/offset | **ÖNERİ** | Kanal kataloğu yok (D-06) |
| BIT test kodları ve alt sistem eşlemesi | **ÖNERİ** | BIT kataloğu yok (D-07); mockup 8 alt sistem gösteriyor, öneri harita 3 grup |
| Cihaz tick frekansı, drift, GPS/PPS | **DOĞRULANMADI** | Zaman kaynağı bilgisi yok (D-09) |
| Performans hedeflerinin karşılanması | **ÖLÇÜLMEDİ** | Hedef makine bilinmiyor (D-15); GUI yok, P-04/P-05/P-08 ölçülemez |
| Görsel kabul | **UYGULANMADI** | Uygulama penceresi henüz yok; liste Faz 3'te işaretlenecek |

`KISMİ` sayılan işler: `F0-004`, `F0-005`, `F0-007`, `F0-008` — tamamı Bölüm 8.2/8.3 taslağına
dayanır (bkz. `docs/notes/worklog.md`). Gerçek doküman geldiğinde bu işler yeniden açılır.

## 5. Bu fazda bulunan ve düzeltilen tutarsızlıklar

| Bulgu | Nerede | Çözüm |
| --- | --- | --- |
| Profil A adı sarmıyor, Profil B 5 hanede sarıyordu | plan §8.2 ve §8.3.8 | Sarma kaldırıldı, tek kural `timing-and-naming.md`'de (`F0-006`) |
| Mockup'ta plan §5.2'de olmayan kanallar var (Gyro, Magnetometer, Hydrophone 3, Speed, Current, Gear Status) | mockup PNG | `layout-map.md` §9'da kayıtlı; `F0-007` çıktısı genişletilmeli |
| Mockup BIT tablosu 8 alt sistem, öneri harita 3 grup | mockup PNG | Aynı yerde kayıtlı; D-07 ile izleniyor |
| Boşluklu dosyada `32 + n × 64` offset formülü yanlış kayda gider | analiz | `timing-and-naming.md` §4.2'de açıkça uyarı; K-03 fixture'ı bunu yakalıyor |
| İndeks olmadan 2,6 GiB dosyada 5 s açılış hedefi tutmuyor | ölçüm | `budget.md` §4.1: `RecordIndex` ön koşul ilan edildi |

## 6. Sonraki faza taşınan açık işler

| Konu | Takip |
| --- | --- |
| Kanal sözlüğünün mockup'a göre genişletilmesi | `F0-007` yeniden açılacak veya Faz 1 kanal işlerine bağlanacak |
| BIT bit haritasının 8 alt sisteme çıkarılması | D-07 cevabıyla |
| Python 3.12 kurulumu | **D-20 — `F1-001` bunu bekliyor** |
| Gerçek `.bin` ve format dokümanı | D-01, D-02 |
| Hedef ölçüm bilgisayarı | D-15 |
| Code signing sertifikası (tedarik süresi uzun) | D-17 |

## 7. Karar

**Milestone `ms/01-format-ready` kapatılır.**

Gerekçe: fazın kabul ölçütü *belgeleme*dir ve on zorunlu kontrolün tamamı geçmiştir. Gerçek veri
eksikleri gizlenmemiş, §4'te ayrı ayrı ve "doğrulanmadı/öneri" etiketiyle kaydedilmiştir.
Hiçbir sentetik sonuç gerçek donanım kanıtı olarak sunulmamıştır.

**Uyarı:** Faz 2 (`ms/03-bin-reader`) kabulü, gerçek `.bin` kaydı olmadan **kapatılamaz**.
D-01 ve D-02 cevaplanmazsa Faz 2 sonunda decoder yalnız sentetik veriyle çalıştığı için
milestone açık kalır.

| | |
| --- | --- |
| Hazırlayan | Geliştirme (otomatik koşu, 2026-09-08/09) |
| Onay | ☐ Proje sahibi ☐ Test mühendisliği |
