# Açık kararlar ve dış bağımlılıklar

> `F0-015` çıktısıdır. Plan Bölüm 25'teki sorular ile `docs/format/inventory.md` §2'deki eksik
> dış girdileri **tek izlenebilir kütüğe** toplar.
>
> Her satır: kimin karar vereceği, hangi işleri engellediği ve **cevap gelmezse hangi varsayımla
> ilerlendiği**. Varsayımla ilerlenen iş `KISMİ` sayılır; gerçek cevap geldiğinde geri dönülür.
>
> Son güncelleme: 2026-09-12 · Depo sürümü `v4.7.0`

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

## 5. Profil C kayıt mimarisi ve ham veri analizi

`F7-002` çıktısı. Faz 7 ve Faz 8'in dayandığı kararlar. Dördü proje sahibi tarafından
cevaplandı ve **KAPALI**; kalanlar açık ve varsayımla ilerleniyor.

### 5.1 Kayıt yapısı (Faz 7)

| ID | Konu | Durum | Karar sahibi | Engellediği işler | Cevap / varsayım |
| --- | --- | --- | --- | --- | --- |
| D-26 | **Azami kayıt süresi** nedir? | **KAPALI** | Proje sahibi | `F7-003`, `F7-032`, `F7-074` | **10 dakika.** Akım başına 600 dosya, toplam ≤ 1.200. 4 saatlik varsayımda 28.800 dosya çıkıyordu; tavan bunu 24 kat küçülttü |
| D-27 | 8192 Hz ile **820 örnek/100 ms** aynı anda doğru olamaz; hangisi bağlayıcı? | **KAPALI** | Proje sahibi | `F7-005`, `F7-026` | **820 örnek bağlayıcı, kayma kabul edildi.** Frame süresi 100,0977 ms; 10 dakikada 0,586 s birikir |
| D-28 | **Complex örnek tipi** nedir? | **KAPALI** | Proje sahibi | `F7-021`, `F7-070` | **`complex64`** (float32 I/Q, 8 bayt). 10 dakikalık kayıt 1,173 GiB eder ve MAT v5'in 2 GiB sınırının %59'unda kalır. `complex128` çıksaydı 2,346 GiB olurdu, sınır aşılır ve `h5py` bağımlılığı gerekirdi |
| D-29 | Kayıt dosyalarını **kim yazıyor**? | **KAPALI** | Proje sahibi | Faz 7'nin bütün çerçevesi | **C++ tarafı.** Python yalnız okur. TOML, C++ struct ve enum tanımlarının tarifidir; bizim tanımladığımız bir yapı değildir. Sentetik üreteç yalnız test içindir |
| D-30 | **CIT** tam olarak nedir, hangi alanları var? | **AÇIK** | Sonar sistem ekibi | `F7-020` frame başlığı çözümü | Ham alan olarak saklanır, **yorumlanmaz** ve hiçbir hesaba girdi olmaz. Inspector'da ham gösterilir. "Coherent Integration Time" olduğu **varsayılmaz** |
| D-31 | **PRI değeri ve Tx süresi** nedir? | **AÇIK** | Sonar sistem ekibi | `F7-059`, `F7-060` | Üreteç PRI'yı **parametre** alır; belgeye ve koda sabit bir değer yazılmaz. Gerçek kayıt geldiğinde ölçülür |
| D-32 | Bir frame'in 820 örneği **tam PRI'yı mı** kapsıyor? | **AÇIK** | Sonar sistem ekibi | `F7-022`, `F7-060` | İki olasılık var: ya 820 örnek tam PRI'dır ve Tx/Rx parçaları ayrı dosyalara yazılır — bu durumda Tx ve Rx frame boyutları **değişkendir** — ya da her akımın kendi 820 örneklik frame'i vardır. Üreteç ikisini de üretebilecek biçimde kurulur |
| D-33 | Zaman ekseni **frame sayacından mı timestamp'ten mi** türeyecek? | **VARSAYIM** | Bu proje | `F7-005` | İkisi 10 dakikanın sonunda 0,586 s ayrışır. Seçim kodda **tek bir yerde** tanımlanmalı; iki panel iki kaynaktan türetirse aynı kayıt için iki farklı zaman gösterir. `F7-005` ile karara bağlanacak |

### 5.2 Ham veri analizi (Faz 8)

| ID | Konu | Durum | Karar sahibi | Engellediği işler | Cevap / varsayım |
| --- | --- | --- | --- | --- | --- |
| D-34 | **ADC bit derinliği, tam ölçek gerilimi ve analog kazanç** nedir? | **AÇIK** | Donanım ekibi | Mutlak seviye ürünleri | Ham sayılar **Volt değildir**. Sabitler girilene kadar birim `count`; arayüzde `V` ve `mV` kelimesi hiç geçmez. Tamsayı dtype'ta `dBFS` verilebilir; float veride tam ölçek kayıp olduğu için `dBFS` bile tanımsızdır |
| D-35 | **Hidrofon duyarlılığı** (dB re 1 V/µPa) sertifikası var mı? | **AÇIK** | Donanım ekibi | Mutlak akustik seviye | Basınç birimi (`Pa`, `dB re 1 µPa`) **hiç kullanılmaz**. Kanal farkları sağlık göstergesi olarak raporlanır; dizi medyanından sapma ve zaman içindeki değişim vurgulanır |
| D-36 | **Temel banda indirme konvansiyonu** nedir (2cos/−2sin mi, cos/sin mi)? | **AÇIK** | Sonar sistem ekibi | Mutlak genlik ürünleri | Kanal-kanal **göreli** karşılaştırmada ortak çarpan olarak sadeleşir, etkisizdir. Mutlak genlik ürünleri `±6 dB konvansiyon belirsizliği` notuyla yayımlanır |
| D-37 | 32 kanalın **hepsi hidrofon mu**, bazıları monitör/referans mı? | **AÇIK** | Sonar sistem ekibi | Eleman sağlık karar motoru | Hepsi hidrofon varsayılır ve bu varsayım her seviye raporunun başına yazılır. Monitör kanalı varsa maskelenebilmesi için kanal dışlama arayüzü hazır tutulur |
| D-38 | Kanallar **eşzamanlı mı** örnekleniyor, yoksa sıralı multipleks mi? | **AÇIK** | Donanım ekibi | Kanal-arası faz metrikleri | Eşzamanlı varsayılır. Multipleks çıkarsa kanal-kanal faz metriklerinden önce sabit gecikme çıkarılmalıdır; bu, bütün göreli faz ölçümlerini kaydırır |
| D-39 | **Tx klasöründeki veri tam olarak nedir**: verici sürüş geri okuması mı, monitör hidrofonu mu, alıcı dizinin yayın anındaki kaydı mı? | **AÇIK** | Sonar sistem ekibi | Tx envanteri ve yorumu | Kanal ve örnek sayısı dosya boyutundan **ölçülür**, varsayılmaz. Cevap gelene kadar ölçümler `kaynak belirsiz` etiketiyle sunulur; "projektör sağlığı" ya da "alıcı kanal arızası" gibi nedensel ifade kullanılmaz |
| D-40 | Kayıt zincirinde **AGC/TVG** uygulanıyor mu? Uygulanıyorsa anlık kazanç frame başlığında mı? | **AÇIK** | Sonar sistem ekibi | Bütün seviye analizi | "Uygulanmamıştır" **varsayılmaz**; veriden test edilir. PRI'dan PRI'ya kuantumlu basamaklı taban sıçraması AGC imzasıdır. İmza bulunursa seviye metrikleri `AGC şüphesi` bayrağıyla işaretlenir |
| D-41 | **Tx ve Rx aynı saatten mi** besleniyor? Timestamp kaynağı ve çözünürlüğü nedir? | **AÇIK** | Sonar sistem ekibi | Darbe-arası faz kararlılığı | Ölçülen kararsızlığın sistem kararsızlığı mı, iki bağımsız saatin serbest koşusu mu olduğu bu cevap olmadan **yorumlanamaz**; çıktı bu uyarıyla yayımlanır |

### 5.3 Dış girdiler

| ID | Konu | Durum | Karar sahibi | Engellediği işler | Varsayım |
| --- | --- | --- | --- | --- | --- |
| E-11 | **Gerçek bir Profil C kaydı** ve onu üreten C++ struct/enum tanımları | **AÇIK** | Sonar sistem ekibi | `F7-080` kabul turu | Sentetik senaryolarla ilerleniyor. Sentetik kanıt gerçek donanım doğrulaması sayılmaz; gerçek kayıt geldiğinde TOML şeması onunla karşılaştırılacak |

### 5.4 Kapsam dışına çıkan sorular

Aşağıdaki sorular ilk tasarımda açık karar olarak duruyordu. Proje sahibinin kapsam
kararıyla — hüzmeleme, eşleştirilmiş filtre, TVG, normalizasyon, CFAR, tespit ve iz sürme
**kapsam dışıdır** — bu soruların cevabına artık ihtiyaç yoktur:

| Soru | Neden artık gerekmiyor |
| --- | --- |
| Dizi geometrisi (sınıf, eleman aralığı, açıklık) | Yalnız hüzmeleme ve derece cinsinden yön için gerekliydi |
| Ses hızı ve SVP profili | Yalnız menzil ekseni ve hüzmeleme gecikmeleri için gerekliydi |
| Taşıyıcı frekans | Yalnız mutlak frekans ekseni ve Doppler'den hıza dönüşüm için gerekliydi |
| Menzil ekseninin sıfır noktası | Yalnız A-scan ve B-scan menzil ekseni için gerekliydi |

Bu sorular kapsam genişlerse yeniden açılır. Kayıt altında tutulmalarının nedeni budur.

---

## 6. Aciliyet sırası

Cevabı **en erken** gereken üç madde:

1. **D-20 (Python 3.12)** — `F1-001` bunu bekliyor; Faz 1 başlayamaz.
2. **D-01 / D-02 (gerçek kayıt ve format dokümanı)** — Faz 0 kabulü (`F0-017`) bunlar olmadan
   "gerçek veri doğrulandı" diyemez; Faz 2'nin tamamı taslak üzerine kuruluyor.
3. **D-17 (code signing)** — sertifika tedarik süresi uzundur; Faz 6'da sorulursa geç kalınır.

Sonra gelenler: D-15 (hedef makine, performans kabulü için), D-06/D-07 (kanal ve BIT katalogları,
arayüzün gerçek adları gösterebilmesi için), D-21 (arayüz dili, metinler yazılmadan önce).

**Faz 7 ve Faz 8 için en erken gereken üçü:**

1. **D-32 (frame 820 örnek tam PRI'yı mı kapsıyor)** — `F7-022` ve sentetik üreteç buna
   bağlı; yanlış varsayım üretilen bütün test verisini boşa çıkarır.
2. **E-11 (gerçek Profil C kaydı ve C++ struct tanımları)** — TOML şeması ancak gerçek bir
   dosyayla doğrulanabilir; `F7-080` kabulü bunsuz "gerçek veri doğrulandı" diyemez.
3. **D-39 (Tx klasöründeki veri tam olarak nedir)** — cevabı Tx analizinin **yorumunu**
   değiştirir: aynı sayı ya projektör sağlığını ya alıcı kanalını anlatır.

## 7. Güncelleme kuralı

- Cevap geldiğinde satır `KAPALI` yapılır; cevap, tarih ve kaynak yazılır.
- Varsayım gerçekle çelişirse: ilgili belgeler güncellenir, etkilenen işler `plan.md`'de yeniden
  `[ ]` yapılır ve `docs/notes/worklog.md`'ye gerekçe düşülür.
- Bu kütük `F0-017` (format milestone kabulü) ve her faz kabulünde gözden geçirilir.
