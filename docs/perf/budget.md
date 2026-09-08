# Performans bütçesi ve ölçüm ortamı

> `F0-014` çıktısıdır. Plan Bölüm 11.1 hedeflerini, bu hedeflerin dayandığı **veri boyutlarını**,
> **ölçüm yöntemini** ve bugün ölçülebilen **başlangıç değerlerini** kaydeder.
>
> **Hedef ölçüm bilgisayarı bilinmiyor** (envanter E-10). Aşağıdaki ölçümler geliştirme
> makinesinde alınmıştır ve kabul kanıtı değildir; hedef donanım belli olduğunda tekrarlanır.

## 1. Ölçüm ortamları

| | Geliştirme makinesi (ölçüldü) | Hedef ölçüm bilgisayarı |
| --- | --- | --- |
| CPU | AMD Ryzen 7 4800H, 8 çekirdek / 16 iş parçacığı, 2,9 GHz | **BİLİNMİYOR** |
| RAM | 31,4 GB | **BİLİNMİYOR** |
| GPU | NVIDIA GeForce GTX 1660 Ti + AMD Radeon (tümleşik) | **BİLİNMİYOR** |
| Ekran | 1920 × 1080 | **BİLİNMİYOR** |
| Disk | NVMe SSD (KINGSTON SNV2S1000G, 932 GB; proje `D:` üzerinde) | **BİLİNMİYOR** |
| OS | Windows 11 Home 10.0.26200 | Windows 10/11 64-bit (plan Bölüm 2) |
| Python | **3.9.13** (plan 3.12 öngörüyor — bkz. worklog ortam notu) | 3.12 |
| NumPy | 1.26.4 | — |

Hedef makine bilgisi gelmeden `F0-014` **kapanmış sayılmaz**; bu tablo o zaman doldurulur ve
bütçe hedefleri gerekiyorsa revize edilir.

## 2. Veri boyutları

Kaynak: `docs/format/profile-a.md`, `docs/format/channel-map.md`, plan Bölüm 8.3.9.

| Senaryo | Kayıt boyutu | Saniyede | 1 dakika | 1 saat | 4 saat |
| --- | --- | --- | --- | --- | --- |
| **Profil A**, 8 kanal | 64 B | 512 B/s | 30 KB | **1,84 MB** | 7,4 MB |
| **Profil A**, 12 kanal | 80 B | 640 B/s | 38 KB | 2,30 MB | 9,2 MB |
| **Profil B**, 4 × 96 kHz + IMU + TX | 96 520 B | ~754 KiB/s | ~44 MiB | **~2,59 GiB** | ~10,4 GiB |

Kayıt sayısı her iki profilde aynıdır: 8/s · 480/dk · **28 800/saat**.

Bu iki ölçek **niteliksel olarak farklıdır**: Profil A tamamen belleğe sığar, Profil B sığmaz.
Bütçe hedefleri Profil B ölçeğine göre kurulur.

## 3. Hedefler (plan Bölüm 11.1)

| # | İşlem | Hedef | Ölçüm tanımı |
| --- | --- | --- | --- |
| P-01 | Uygulama açılışı | ≤ 3 s | Süreç başlangıcından ana pencerenin etkileşime hazır olmasına |
| P-02 | Küçük kayıt açılışı | ≤ 2 s | Profil A 1 saatlik dosya; dosya seçiminden kanal ağacının dolmasına |
| P-03 | Büyük kayıtta metadata görünmesi | ≤ 5 s | Profil B ~2,6 GiB dosya; seçimden dosya özeti + kanal ağacına |
| P-04 | Pan/zoom etkileşimi | algılanan ≥ 30 FPS | 60 s pencere, 4 kanal açık; kare süresi ≤ 33 ms |
| P-05 | Cursor geri bildirimi | ≤ 50 ms | Fare hareketinden değer etiketinin güncellenmesine |
| P-06 | Event'e gitme | ≤ 200 ms | BIT satırı tıklamasından grafiklerin hizalanmasına |
| P-07 | Viewport veri sorgusu | çoğunlukla ≤ 150 ms | Repository `query()` çağrısı; downsample dahil |
| P-08 | Play/pause tepkisi | ≤ 100 ms | Düğmeden ilk kare güncellemesine |
| P-09 | Bellek | dosya boyutuyla doğrusal büyümemeli | 2,6 GiB dosyada süreç RSS'i; 10,4 GiB dosyada **aynı mertebede** kalmalı |

## 4. Ölçülen başlangıç değerleri

Geliştirme makinesi, Python 3.9.13 + NumPy 1.26.4. Her ölçüm tek koşudur; kabul için
`F4` performans işlerinde 5 tekrarın medyanı kullanılacaktır.

| Ölçüm | Sonuç | Not |
| --- | --- | --- |
| Disk sıralı yazma | ~525 MB/s | 256 MiB, `fsync` dahil |
| Disk sıralı okuma | ~2 090 MB/s | **Sayfa önbelleği sıcak** — soğuk okuma bundan düşüktür |
| Profil A ayrıştırma (`np.frombuffer` + boşluk taraması) | **39,3 M kayıt/s** | 115 200 kayıt 2,9 ms'de |
| Tek kanal min/max/mean, 115 200 nokta | 1,5 ms | |
| Profil B ölçekleme, 1 s veri (4 × 96 k `int16` → `float32`) | 0,86 ms | |
| 96 k nokta `rfft` | 2,0 ms | 10 koşunun ortalaması |

### 4.1 Bu sayılardan çıkan sonuçlar

**Profil A hiçbir bütçeyi zorlamaz.** 1 saatlik dosya 1,84 MB'tır; tamamı 39 M kayıt/s hızla
50 ms'in altında ayrıştırılır ve belleğe sığar. P-02 rahatlıkla karşılanır.

**Profil B'de dosyayı baştan sona taramak P-03'ü karşılayamaz.** 2,59 GiB'ı 500 MB/s soğuk okuma
hızıyla okumak **~5,3 s** sürer; 4 saatlik kayıtta **~21 s**. Yalnız kayıt başlıklarını okumak da
yardımcı olmaz, çünkü 48 baytlık başlıklar 2,6 GiB'a yayılmıştır ve pratikte tüm sayfalar okunur.

> **Sonuç: Profil B için dosya sonundaki `RecordIndex` isteğe bağlı değil, P-03'ün ön koşuludur.**
> 28 800 kayıt × 32 B = **~900 KiB** indeks; okunması milisaniyeler sürer. İndeks yoksa veya
> bozuksa açılış "tam tarama" moduna düşer ve bu durum kullanıcıya ilerleme çubuğuyla bildirilir —
> sessizce 20 saniye beklenmez.

**Viewport sorgusu (P-07) downsample olmadan sınırda kalır.** 60 s'lik pencerede tek kanal
5,76 M örnektir (11,5 MB `int16`). Ham okuma + min/max indirgeme ölçülen hızlarla ~75–100 ms
alır; dört kanalda bütçe aşılır. Downsample piramidi (Bölüm 11.2) P-07 için zorunludur.

**FFT bütçe içindedir.** 96 k noktalık `rfft` 2 ms'dir; 1 s'lik pencere için etkileşimli
kullanımda sorun çıkarmaz. Spektrogram maliyeti pencere sayısıyla çarpılır ve ayrı ölçülür.

## 5. Ölçüm yöntemi

| Kural | İçerik |
| --- | --- |
| Tekrar | Her ölçüm 5 kez; **medyan** raporlanır, en iyi değer değil |
| Soğuk/sıcak | Dosya açma ölçümleri **soğuk** yapılır; ölçüm öncesi sistem dosya önbelleği düşürülür veya makine yeniden başlatılır. Sıcak ölçüm ayrı satır olarak raporlanır |
| Ortam | Ölçüm sırasında başka ağır uygulama çalışmaz; güç profili "yüksek performans" |
| Zamanlama | `time.perf_counter()`; GUI ölçümlerinde kare süreleri Qt tarafında toplanır |
| Veri | Sentetik fixture'lar (`tools/make_synthetic_bin.py`) ve — geldiğinde — gerçek kayıt |
| Kayıt | Her ölçüm: tarih, commit karması, makine, dosya boyutu, sonuç. Sonuçlar `docs/perf/results/` altına yazılır |
| Regresyon | CI'da küçük smoke benchmark; %20'den fazla gerileme kalite kapısını düşürür (Bölüm 21) |
| Dürüstlük | Sentetik ölçüm gerçek donanım kanıtı olarak sunulmaz; hedef makinede tekrarlanmadan hedef "karşılandı" denmez |

## 6. Açık noktalar

- [ ] Hedef ölçüm bilgisayarının CPU/RAM/disk/ekran bilgisi (E-10).
- [ ] Soğuk disk okuma hızı — bu koşuda ölçülemedi (önbellek sıcaktı).
- [ ] Gerçek kayıt boyutu ve süresi (E-01); 2,6 GiB/saat varsayımı gerçek veriyle doğrulanmalı.
- [ ] Qt/PyQtGraph çizim maliyeti — GUI iskeleti kurulmadan (`F1-*`) ölçülemez; P-04, P-05, P-08
      şu an **ölçülmemiştir**.
- [ ] Bellek tavanı: hedef makinenin RAM'i bilinmeden P-09 için somut sınır yazılamaz.
