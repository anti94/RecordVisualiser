# Milestone kabul tutanağı — `ms/02-app-shell`

- **Faz:** 1 — Uygulama iskeleti ve domain modeli
- **Sürüm:** `v0.61.0`
- **Etiketler:** `v0.61.0` ve `ms/02-app-shell` (aynı commit)
- **Tarih:** 2026-09-09
- **Kabul işi:** `F1-044`

## 1. Faz kabul ölçütü

Plan Bölüm 22.3: *"Uygulama sahte veriyle açılmalı; dock'lar ve temel zaman
grafiği çalışmalı, başlangıç kontrolleri geçmeli."*

## 2. İşler ve çıktılar (44 iş)

| İş | Çıktı | Commit |
| --- | --- | --- |
| `F1-001` | Paket iskeleti, bağımlılık kilidi | `6e4a36f` |
| `F1-002` | Tek komutluk geliştirici kurulumu | `d7f0a90` |
| `F1-003` | Ruff yapılandırması | `95a3fb3` |
| `F1-004` | Pyright strict tip kontrolü | `052a3df` |
| `F1-005` | pytest / pytest-qt düzeni | `3b14a71` |
| `F1-006` | Windows CI iş akışı (+ satır sonu düzeltmesi) | `89f8bec`, `dcfe128` |
| `F1-007` | Uygulama girişi ve temiz kapanış | `6860120` |
| `F1-008` | Merkezi exception yakalama | `5a02e57` |
| `F1-009` | Sürümlü temel ayarlar | `06c4c6b` |
| `F1-010` | Dönen log ve session kimliği | `991b9c4` |
| `F1-011` | `ChannelMetadata` | `87b3c64` |
| `F1-012` | `DataChunk` ve kalite bayrakları | `a01a899` |
| `F1-013` | `TimeRange`, `RecordingMetadata` | `074f936` |
| `F1-014` | `Event`, `BitResult` | `0e21f97` |
| `F1-015` | `TransmissionInterval` | `3afe5f3` |
| `F1-016` | `RecordingRepository` protokolü | `04534ec` |
| `F1-017` | `LiveSource` protokolü | `020f243` |
| `F1-018` | Deterministik sinüs üreteci | `36b9809` |
| `F1-019` | Noise, chirp, impulse üreteçleri | `72145e4` |
| `F1-020` | Sahte kanal repository'si | `48f95dc` |
| `F1-021` | Sahte BIT/TX/sistem olayları | `a11d9f3` |
| `F1-022` | Üç sütunlu ana pencere düzeni | `59ce1b7` |
| `F1-023` | Menü ve toolbar eylemleri | `5a20b3e` |
| `F1-024` | Data Explorer dock'u | `ea51cac` |
| `F1-025` | Inspector bağlamsal sekmesi | `b59e723` |
| `F1-026` | Log/Messages ve Events sekmesi | `d34620a` |
| `F1-027` | Playback/Time Control şeridi | `5f679d9` |
| `F1-028` | Durum çubuğu alanları | `18eddb8` |
| `F1-029` | Koyu tema ve mavi vurgular | `6a735d1` |
| `F1-030` | Durum ikonları ve kanal paleti | `2bc3f14` |
| `F1-031` | Tek kanallı `PlotPanel` | `50da59f` |
| `F1-032` | Seçim → grafik bağlantısı | `a9eb0be` |
| `F1-033` | Boş workspace yönlendirmesi | `c627589` |
| `F1-034` | Dosya özet kartı | `9cddf2c` |
| `F1-035` | BIT/System Status kartı | `d0fd7c1` |
| `F1-036` | Analysis Tools sekmeleri | `d27c290` |
| `F1-037` | Data Export kartı | `9482d61` |
| `F1-038` | Sekiz ana analiz sekmesi | `ac43dce` |
| `F1-039` | Dashboard grafik hücreleri | `6a06651` |
| `F1-040` | Grafik hızlı araç şeridi | `6afad9d` |
| `F1-041` | 1M/10M nokta spike girdileri | `f1d40e4` |
| `F1-042` | Pan/zoom ve cursor ölçüm koşucusu | `99a38a6` |
| `F1-043` | İlk spike sonuçları ve darboğaz | `659f26d` |
| `F1-044` | Bu tutanak | *(bu commit)* |

## 3. Zorunlu kontroller

| # | Kontrol | Sonuç | Dayanak |
| --- | --- | --- | --- |
| 3.1 | Açılış: uygulama sahte veriyle hatasız açılır | **GEÇTİ** | `python -m sonar_analyzer --no-window` çıkış kodu 0; `MainWindow` + `MockRecordingRepository` entegrasyon testleri |
| 3.2 | Dock yaşam döngüsü: paneller açılır/kapanır/taşınır/yüzer | **GEÇTİ** | `test_data_explorer.py`, `test_inspector.py`, `test_main_window_layout.py` — kapatma, yüzdürme, sağ alana taşıma test edildi |
| 3.3 | Sahte grafik: seçilen kanal gerçek eğriyle çizilir | **GEÇTİ** | `test_channel_to_plot.py`: seçim → `PlotPanel.set_channel` → istatistik kartı, hepsi gerçek veriyle |
| 3.4 | Başlangıç CI kontrolleri geçer | **GEÇTİ** | CI koşusu #50 (commit `659f26d`): `Windows / Python 3.9` başarılı, `Windows / Python 3.12` başarılı, `todo.md güncel mi` başarılı |
| 3.5 | Kod kalitesi: lint, biçim, tip | **GEÇTİ** | `ruff check` temiz, `ruff format --check` temiz, `pyright strict` 0 hata |
| 3.6 | Test paketi | **GEÇTİ** | 453 test, 0 hata, 0 atlanan (bkz. §5 not) |
| 3.7 | Her iş kendi commit'i ve `vX.Y.0` etiketiyle kapandı | **GEÇTİ** | `v0.18.0` – `v0.60.0`, 43 sürüm etiketi doğrulandı |
| 3.8 | Mockup'la görsel uyum | **GEÇTİ** | `tools/screenshot.py` ile üretilen görüntüler (`F1-032`, `F1-039`, `F1-040`) dokuz bölgeyi, koyu temayı, hiyerarşik kanal ağacını ve dashboard düzenini mockup'la örtüşür şekilde gösteriyor |

**Zorunlu kontrollerin tamamı geçti.**

## 4. Gerçek veri ve donanımla doğrulanmayan maddeler

> Faz 0 tutanağındaki kuralın devamı: aşağıdakiler "doğrulandı" sayılmaz.

| Konu | Durum | Neden |
| --- | --- | --- |
| Gerçek `.bin` kaydından açılış | **DOĞRULANMADI** | Elde gerçek kayıt yok (D-01); tüm akış `MockRecordingRepository` ile |
| Pan/zoom performans hedefi (P-04) | **SAPMA TESPİT EDİLDİ** | `F1-043`: 1M noktada 7,4 FPS, 10M'de 0,8 FPS (hedef ≥ 30). Darboğaz kanıtlı: downsample piramidi olmadan (`F4-056`/`F4-057`) kapanmayacak |
| Cursor/açılış/olay performans hedefleri (P-05, P-01, P-06) | **KISMEN/HİÇ ÖLÇÜLMEDİ** | P-05 yalnız koordinat dönüşümü ölçüldü, crosshair zinciri yok (`F3-026`); P-01/P-06 henüz ölçülmedi |
| Görsel kabul (gerçek ekranda) | **KISMİ** | Tüm ölçüm ve ekran görüntüleri `offscreen` Qt platformunda; gerçek ekranda doğrulanmadı |
| Python 3.12 yerel geliştirme ortamı | **AÇIK** | Yalnız CI'da doğrulanıyor (D-20); yerel makinede hâlâ 3.9.13 |

## 5. Düzeltme: yanlış test sayısı iddiası

`F1-042` ve `F1-043` commit mesajlarında "476 test geçti" yazıyor. Bu tutanak
hazırlanırken `pytest` yeniden çalıştırıldı ve gerçek sayı **453**'tür (0 hata,
0 atlanan). Aradaki fark muhtemelen o iki commit sırasında test paketinin
tekrar çalıştırılmadan önceki bir sayının yanlış aktarılmasından kaynaklandı;
yayımlanmış commit mesajları geriye dönük değiştirilmedi, ama bu tutanak doğru
sayıyı taşıyan referanstır.

## 6. Bu fazda bulunan ve düzeltilen tutarsızlıklar

| Bulgu | Nerede | Çözüm |
| --- | --- | --- |
| CI yalnız Python 3.12 ayağında satır sonu farkından düşüyordu | `F1-006` | `.gitattributes` `eol=lf` |
| CI yalnız 3.12 ayağında pyright'ta düşüyordu (numpy sürüm kayması) | `F1-012` sonrası CI | numpy `>=1.26,<2.1`'e sabitlendi |
| CI yalnız 3.12 ayağında pyright'ta düşüyordu (PySide6 taslak farkı) | `F1-024` sonrası CI | PySide6 `==6.10.3` sabitlendi; pyright annotation adımı eklendi |
| Testler kullanıcının gerçek `%LOCALAPPDATA%`/`%APPDATA%` yollarına yazıyordu | `F1-010` | Ortam değişkeni yönlendirmesi + conftest |
| Offscreen Qt'de hiç yazı tipi yok; ekran görüntüsünde tüm metinler kutu çıkıyordu | Görsel doğrulama | `QT_QPA_FONTDIR` conftest'te ve `tools/screenshot.py`'de ayarlandı |
| Kanal yolunda `/` hem ayraç hem ad parçasıydı, ağaç bozuk grup üretiyordu | `F1-024` | Yol düzeltildi, gösterim etiketi eşlendi |
| `set_recording` yeni kanalları toolbar'a doldurduktan hemen sonra siliyordu | `F1-040` | Hatalı `clear_channels()` çağrısı kaldırıldı |
| PyQtGraph'ın hazır downsampling/clip bayrakları pan/zoom darboğazını çözmüyor | `F1-043` | Kanıtlandı; planın downsample piramidi kararı (`F4-056`/`F4-057`) doğrulandı |

## 7. Sonraki faza taşınan açık işler

| Konu | Takip |
| --- | --- |
| Downsample piramidi (P-04 sapmasını kapatacak) | `F4-056`, `F4-057` |
| Crosshair/cursor değer okuma zinciri | `F3-026` |
| Gerçek `.bin` parser ve gerçek veri doğrulaması | Faz 2 (`ms/03-bin-reader`) |
| Python 3.12 yerel kurulum | D-20 |
| Dört kanallı P-04 senaryosu ve 5 tekrar/medyan ölçüm kuralı | Faz 4 performans işleri |
| Mockup'ta olmayan `Analysis` menüsü farkı | D-07 civarı, karar bekliyor |

## 8. Karar

**Milestone `ms/02-app-shell` kapatılır.**

Gerekçe: fazın kabul ölçütü karşılanmıştır — uygulama sahte veriyle açılıyor,
dock'lar yaşam döngüsünü tam destekliyor, temel zaman grafiği gerçek veriyle
çiziliyor, başlangıç CI kontrolleri (lint, biçim, tip, test, todo senkronu)
üç işte de yeşil. Gerçek donanım ve performans hedefleriyle ilgili eksikler
gizlenmemiş, §4'te ayrı ayrı listelenmiştir; P-04 sapması özellikle **somut
ölçümle** belgelenmiş ve sıradaki faza net bir iş olarak (downsample
piramidi) bağlanmıştır.

**Uyarı:** Faz 3 (`ms/04-mvp`) kabulü, gerçek `.bin` kaydı ve P-04/P-05/P-06/
P-08 hedeflerinin gerçek ekranda doğrulanması olmadan kapatılamaz.

| | |
| --- | --- |
| Hazırlayan | Geliştirme (otomatik koşu, 2026-09-08/09) |
| Onay | ☐ Proje sahibi ☐ Test mühendisliği |
