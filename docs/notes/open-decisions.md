# Açık kararlar ve dış bağımlılıklar

> `F0-015` çıktısıdır. Plan Bölüm 25'teki sorular ile `docs/format/inventory.md` §2'deki eksik
> dış girdileri **tek izlenebilir kütüğe** toplar.
>
> Her satır: kimin karar vereceği, hangi işleri engellediği ve **cevap gelmezse hangi varsayımla
> ilerlendiği**. Varsayımla ilerlenen iş `KISMİ` sayılır; gerçek cevap geldiğinde geri dönülür.
>
> Son güncelleme: 2026-09-08 · Depo sürümü `v0.15.0`

## Durum kodları

`AÇIK` — cevap yok · `VARSAYIM` — geçici karar verildi, onay bekliyor · `KAPALI` — cevaplandı

---

## 1. Donanım verisi ve format

| ID | Konu | Durum | Karar sahibi | Engellediği işler | Varsayım / geçici karar |
| --- | --- | --- | --- | --- | --- |
| D-01 | Gerçek `.bin` kaydı var mı, ne zaman alınabilir? (E-01) | **AÇIK** | Donanım/test ekibi | `F0-017`, tüm `F2` gerçek veri kabulü | Sentetik fixture ile ilerleniyor; gerçek veri kanıtı sayılmıyor |
| D-02 | Resmî `.bin` format dokümanı (E-02) | **AÇIK** | Firmware ekibi | `F0-004`, `F0-005`, `F0-008` | Bölüm 8.2/8.3 taslağı sözleşme kabul edildi (`docs/format/profile-a.md`) |
| D-03 | En büyük tipik dosya boyutu ve kayıt süresi | **AÇIK** | Proje sahibi | `F0-014`, `F4` performans işleri | Profil B için 2,59 GiB/saat, 4 saate kadar (~10,4 GiB) varsayıldı |
| D-04 | Maksimum kanal sayısı ve kanal başına en yüksek sample rate | **VARSAYIM** | Sistem mühendisliği | `F0-007`, `F1-011`, `F4` | Mockup log'u `48 channels found` diyor; örnek sözlük 8/12 kanal, akustik 96 kHz varsayıldı |
| D-05 | CRC/checksum algoritması (E-03) | **VARSAYIM** | Firmware ekibi | `F0-010`, `F2` doğrulama | CRC-32/ISO-HDLC seçildi — `docs/adr/ADR-011-crc.md` |
| D-06 | Kanal kataloğu: ad, birim, sample rate, gain/offset (E-04) | **AÇIK** | Sistem mühendisliği | `F0-007`, `F1-011` | `docs/format/channel-map.md` öneri sözlüğü |
| D-07 | BIT test kataloğu: `test_id` / kod → anlam (E-05) | **AÇIK** | Donanım ekibi | `F3` BIT paneli | 12 bitlik öneri harita; mockup **8 alt sistem** gösteriyor, harita genişletilmeli |
| D-08 | Transmisyon alanları ve START/STOP ilişkilendirme (E-06) | **VARSAYIM** | Sistem mühendisliği | `F1-015`, `F3-050` | `IDLE→ACTIVE` START, `ACTIVE→IDLE` STOP; sınırlar ±125 ms |
| D-09 | Zaman kaynağı, tick frekansı, GPS/PPS, drift (E-07) | **AÇIK** | Donanım ekibi | `F0-011` doğrulaması | `docs/adr/ADR-003-time-base.md`; Profil A'da senkron kalitesi `bilinmiyor` |
| D-10 | Firmware/format sürüm listesi (E-08) | **AÇIK** | Firmware ekibi | `F2` sürüm testi | Yalnız `version = 1` (ve CRC'li `2`) destekleniyor; bilinmeyen sürüm reddediliyor |
| D-11 | BIT sonuçları anlık olay mı, periyodik durum mu? | **VARSAYIM** | Donanım ekibi | `F3` BIT paneli, olay tablosu | Profil A'da her kayıtta durum maskesi (periyodik); Profil B'de 1 Hz blok |

## 2. Canlı veri ve protokol

| ID | Konu | Durum | Karar sahibi | Engellediği işler | Varsayım / geçici karar |
| --- | --- | --- | --- | --- | --- |
| D-12 | Canlı veri hangi protokolle gelecek? (taşıma, port, paket yapısı) (E-09) | **AÇIK** | Sistem/yazılım ekibi | Tüm `F5` | Faz 5'e kadar bloke değil. `F5-003` dosyadan replay ile ilerlenecek |
| D-13 | Canlı akışın bant genişliği ve tepe hızı | **AÇIK** | Sistem ekibi | `F5` backpressure tasarımı | Kayıtla aynı mertebe (Profil B ~754 KiB/s) varsayıldı |
| D-14 | Canlı veri kaydedilecek mi, hangi biçimde? | **AÇIK** | Proje sahibi | `F5` kayıt işleri | Aynı `.bin` profiliyle yazılacağı varsayıldı |

## 3. Ortam, dağıtım ve güvenlik

| ID | Konu | Durum | Karar sahibi | Engellediği işler | Varsayım / geçici karar |
| --- | --- | --- | --- | --- | --- |
| D-15 | Hedef ölçüm bilgisayarı: CPU, RAM, GPU, ekran (E-10) | **AÇIK** | Proje sahibi | `F0-014` kapanışı, `F4` performans kabulü | Geliştirme makinesi ölçümleri geçici referans (`docs/perf/budget.md` §1) |
| D-16 | **Offline / air-gapped** ortamda çalışması gerekiyor mu? | **AÇIK** | Proje sahibi / BT | `F6-011` | Gerekmediği varsayıldı; gerekirse tüm bağımlılıklar önceden paketlenmeli (wheel arşivi) — bu, bağımlılık seçimini de kısıtlar |
| D-17 | **Code signing** gerekli mi, sertifika süreci nedir? | **AÇIK** | Proje sahibi / BT | `F6-012` | Gerekmediği varsayıldı; imzasız dağıtım kararı ADR'ye yazılacak. **Sertifika tedariki uzun sürer**, cevap Faz 6'dan çok önce gerekir |
| D-18 | Verinin güvenlik sınıfı; log/export kısıtı var mı? | **AÇIK** | Proje sahibi | Bölüm 19, `F6` | Kısıt yok varsayıldı; kayıt içeriği log'a yazılmıyor, yalnız metadata yazılıyor |
| D-19 | Kontrollü güncelleme / dağıtım kanalı | **AÇIK** | BT | `F6` | Elle kurulum varsayıldı |
| D-20 | Python 3.12 hedef makinede kurulabilir mi? | **AÇIK** | Proje sahibi | `F1-001` ve sonrası | Geliştirme makinesinde şu an **3.9.13** var; Faz 1 öncesi 3.12 gerekiyor |

## 4. Ürün ve arayüz

| ID | Konu | Durum | Karar sahibi | Engellediği işler | Varsayım / geçici karar |
| --- | --- | --- | --- | --- | --- |
| D-21 | **Arayüz dili**: yalnız İngilizce mi, TR/EN mi? | **VARSAYIM** | Proje sahibi | `F1` arayüz metinleri, `F6` yerelleştirme | Referans mockup'ın **tüm arayüz metinleri İngilizce** (`Open .bin File`, `Playback / Time Control`, `Export Data`). Bu nedenle **arayüz İngilizce**, proje belgeleri Türkçe varsayıldı. Çift dil istenirse metinler baştan `tr()` ile sarılmalı — sonradan eklemek pahalı |
| D-22 | Birden fazla kayıt zaman hizalı karşılaştırılacak mı? | **AÇIK** | Test mühendisliği | Faz 4 kapsamı | İlk sürümde tek kayıt varsayıldı (plan Bölüm 2) |
| D-23 | MATLAB'daki hangi davranışlar birebir bekleniyor? | **AÇIK** | Test mühendisliği | `F3`/`F4` etkileşim kabulü | Özel bir birebir beklenti olmadığı varsayıldı |
| D-24 | Rapor çıktısı resmî test kanıtı sayılacak mı? | **AÇIK** | Kalite / proje sahibi | `F4` rapor işleri | Sayılmayacağı varsayıldı; sayılacaksa imza, sürüm ve izlenebilirlik alanları gerekir |
| D-25 | `Cross Analysis`, `3D View`, otomatik `Report` kapsamda mı? | **VARSAYIM** | Proje sahibi | Faz 4 backlog | Opsiyonel backlog; MVP'de sekme görünür ama `v2.0.0 ile kullanılabilir` durumunda |

---

## 5. Aciliyet sırası

Cevabı **en erken** gereken üç madde:

1. **D-20 (Python 3.12)** — `F1-001` bunu bekliyor; Faz 1 başlayamaz.
2. **D-01 / D-02 (gerçek kayıt ve format dokümanı)** — Faz 0 kabulü (`F0-017`) bunlar olmadan
   "gerçek veri doğrulandı" diyemez; Faz 2'nin tamamı taslak üzerine kuruluyor.
3. **D-17 (code signing)** — sertifika tedarik süresi uzundur; Faz 6'da sorulursa geç kalınır.

Sonra gelenler: D-15 (hedef makine, performans kabulü için), D-06/D-07 (kanal ve BIT katalogları,
arayüzün gerçek adları gösterebilmesi için), D-21 (arayüz dili, metinler yazılmadan önce).

## 6. Güncelleme kuralı

- Cevap geldiğinde satır `KAPALI` yapılır; cevap, tarih ve kaynak yazılır.
- Varsayım gerçekle çelişirse: ilgili belgeler güncellenir, etkilenen işler `plan.md`'de yeniden
  `[ ]` yapılır ve `docs/notes/worklog.md`'ye gerekçe düşülür.
- Bu kütük `F0-017` (format milestone kabulü) ve her faz kabulünde gözden geçirilir.
