# SONAR Veri Analiz Panosu — `v3.0.0` (Canlı veri ve kayıt)

**Tarih:** 2026-09-11 · **Milestone:** `ms/06-live-recording` · **Kabul tutanağı:**
`docs/release/ms-06-live-recording.md`

`v3.0.0`, `v2.0.0`'da dosyadan okunan veriyle çalışan analiz panosunu **canlı
bir kaynağa** bağlar ve gelen veriyi Profil A `.bin` dosyalarına kaydeder.
Ekranlar değişmedi: canlı akış, dosya tarafıyla **aynı** sorgu sözleşmesini
karşılayan bir depo üzerinden beslendiği için grafikler, BIT özeti ve
analiz hücreleri veri kaynağına göre farklı davranmaz.

## Öne çıkanlar

- **Üç taşıma katmanı** — UDP (parça birleştirme, hepsi-ya-hiçbiri zaman
  aşımı), TCP (uzunluk önekli çerçeveleme, EOF ile RST ayrımı) ve seri port
  (`SYNC` yeniden hizalama, CRC32 kuyruğu). Üçü de aynı `LiveSource`
  sözleşmesini karşılar; tüketici hangisinin bağlı olduğunu bilmez.
- **Bağlantı durumu tek kaynaktan** — araç çubuğu ve durum çubuğu aynı
  `ConnectionState` değerinden türetilir, ayrışamazlar. Kesilme, yeniden
  bağlanma (üstel, tavanlı, görünür denemeler) ve hata ayrı durumlardır.
- **Sınırlı bellek** — canlı örnekler önceden ayrılmış sabit boyutlu halka
  tamponda, paketler sınırlı kuyrukta, olay/BIT/TX kayıtları sınırlı
  kuyruklarda tutulur. 2 saatlik koşuda bellek **%0,34** büyüdü.
- **Görünür kayıp** — düşen paket, kuyruk taşması ve disk yetişememesi ayrı
  ayrı sayılır ve canlı sağlık kartında görünür. Sessizce düşen bir paket,
  kullanıcının eksik veriyi tam sanması demek olurdu.
- **Kayıt** — `Record`/`Stop`, 125 ms ızgarasına oturan `DataNNNNN` kayıtları,
  disk yazımının canlı akıştan ayrılması (yavaş disk arayüzü kilitlemez),
  boyut ve isim sınırında yeni dosyaya geçiş.
- **Güvenli kapatma** — `Stop` sonrası bütün tam kayıtlar yeniden okunabilir:
  kuyrukta kalanlar diske iner, `fsync` yapılır ve kayıt sınırına oturmayan
  yarım bayt kuyruğu kesilir.
- **Dürüst hata durumu** — disk dolduğunda ya da yazma hatası olduğunda kayıt
  hata durumuna geçer ve **"başarılı kayıt" mesajı verilmez**; kurtulan
  kayıtların sayısı ve dosya yolu bildirilir, dosya silinmez.
- **Canlı BIT ve TX** — BIT durum geçişi, özet kartı besleyen **aynı** akıştan
  üretilen bir olayla işaretlenir; sağdaki özet ile grafikteki marker
  yapısal olarak aynı anı gösterir.
- **Sona takip** — viewport son pencereyi izler; kullanıcı gezindiğinde takip
  kapanır ve bir daha zorla sona taşınmaz.

## Kayıt ve dosya davranışı

- Kayıt dosyaları Profil A sürüm 2'dir: 36 baytlık başlık + 68 baytlık
  kayıtlar, kayıt başına CRC-32/ISO-HDLC (ADR-011).
- Dosya değiştirme iki sınırda olur: boyut (`max_bytes`) ve isim
  (`Data9999999`, `char[12]` alanının sınırı). Yeni dosya **kendi içinde
  tutarlıdır**: ilk kaydı `Data00000` ve `elapsed_us = 0`'dır, başlangıç
  zamanı o kaydın pencere başlangıcıdır. Dosya tek başına, önceki dosyaya
  bakmadan doğru okunur.
- Bağlantı kesilmesinde tam kayıtlar korunur; kapanış nedeni (kullanıcı
  durdurdu / bağlantı kesildi / kaynak hatası / disk hatası) ve akıştaki
  boşluklar aralık ve sayı olarak log'a yazılır.

## Doğrulama

| Kontrol | Sonuç |
| --- | --- |
| Üç adaptör | UDP 26, TCP 23, serial 58 test — **geçti** |
| Yeniden okuma (örnekler, olaylar, 125 ms sınırları) | 15 test — **geçti** |
| Dayanıklılık (bozucu, burst, kesinti) | 58 test — **geçti** |
| 2 saatlik koşu (bellek, kayıp, bütünlük) | üç ölçüt de **geçti** |
| Canlı modda mockup yerleşimi | 20 test — **geçti** |
| Tam test paketi | 4576 test, yeşil |

2 saatlik koşuda 57 600 pencere üretildi; 56 983 kayıt yazıldı ve
**hepsi geri okundu**, CRC'ler tuttu. Ayrıntı: `docs/live/endurance-report.md`.

## Bu sürümde düzeltilenler

Faz 5 doğrulama işleri üç gerçek kusuru ortaya çıkardı:

- Kayıt yazıcısı `bit_status`/`tx_status` alanlarını her zaman sıfır
  yazıyordu; canlı bir arıza kayıtta kayboluyordu (`F5-035`).
- Saf canlı modda merkez görselleştirme alanı "veri yok" ekranında
  kalıyordu (`F5-040`).
- Canlı pano her karede baştan kuruluyordu; iş oturum uzadıkça büyüyordu
  (`F5-038`).

## Bilinen sınırlar

Gerçek cihaz, gerçek seri port donanımı ve gerçek ağ koşullarıyla doğrulama
**yapılmadı**; bütün doğrulama `docs/live/protocol-contract.md` sözleşmesine
ve seed'li bir bozucuya karşıdır. 2 saatlik koşu simüle edilmiş zamandadır.
Tam liste: `docs/release/ms-06-live-recording.md` §8.

## Yükseltme

`v2.0.0` ile yazılmış workspace ve `.bin` dosyaları değişmeden açılır; dosya
formatı sürümü (Profil A v2) değişmedi. Seri port kullanımı isteğe bağlı
`live` ekstrasını gerektirir:

```powershell
.venv\Scripts\python.exe -m pip install -e ".[gui,dsp,live]"
```
