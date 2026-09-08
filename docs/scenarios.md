# Kullanıcı senaryoları — ilk paket

> `F0-002` çıktısıdır. Kaynak roller Bölüm 4, veri sözleşmesi Bölüm 8.2/8.3, ekran referansı Bölüm 5.1'dir.
> Her senaryo bir **girdi** ve gözle doğrulanabilir bir **sonuç** tanımlar. Sonuç cümlesi kabul kontrolüdür;
> "iyi çalışır" gibi ölçülemeyen ifade kullanılmaz.

Ortak varsayımlar:

- Kayıt dosyası 125 ms periyotlu `Data00000`, `Data00001`, … zincirini taşır (Bölüm 8.2/8.3).
- Zaman gösterimi UTC, yerel saat ve kayıt başından geçen süre olarak ayrı ayrı sunulur (Bölüm 9).
- Bu paket kapsamındaki senaryolar **kayıtlı dosya** üzerinden çalışır; canlı akış Faz 5'tedir.

## S-01 — Operatör: BIT alarmından ilgili zaman aralığına gitme

| Alan | İçerik |
| --- | --- |
| Rol | Operatör (4.1) |
| Ön koşul | Kayıt açık; BIT paneli dolu; en az bir `FAIL` sonucu var. |
| Girdi | 30 dakikalık kayıt; `t = 00:12:30.125` anında `component = Amplifier`, `state = FAIL`, `code = 0x0412` BIT sonucu. |
| Adımlar | 1) BIT panelinde `FAIL` satırı seçilir. 2) `Go to time` eylemi çalıştırılır. |
| Gözlenebilir sonuç | Timeline imleci `00:12:30.125`'e taşınır; açık tüm grafikler aynı aralığa hizalanır; olayın ait olduğu kayıt `Data06001` olarak gösterilir; grafik üzerinde olay marker'ı seçili görünür. |
| Kabul kanıtı | Ekran görüntüsü + imlecin gösterdiği zamanın BIT satırındaki zamanla birebir eşleşmesi. |
| İlgili işler | `F3-047` sonrası BIT özeti; `F3-030` olaydan zamana gitme. |

## S-02 — Operatör: Transmisyon aralığını kanal davranışıyla birlikte inceleme

| Alan | İçerik |
| --- | --- |
| Rol | Operatör (4.1) |
| Ön koşul | Kayıtta en az bir tam `TRANSMIT` aralığı var. |
| Girdi | `tx_state` alanı `IDLE → TRANSMIT → IDLE` geçişi yapan kayıt; aralık `00:03:10.000`–`00:03:12.500`; aynı anda `Hydrophone 01` kanalı açık. |
| Adımlar | 1) Transmission paneli açılır. 2) İlgili aralık satırı seçilir. |
| Gözlenebilir sonuç | Grafik üzerinde aralık gölgeli bant olarak çizilir; başlangıç/bitiş 125 ms ızgarasına oturur; panelde `frequency`, `power` ve `mode` alanları dolu görünür; aralık dışındaki veri gölgelenmez. |
| Kabul kanıtı | Bant sınırlarının START/STOP kayıt zamanlarıyla ±125 ms içinde eşleşmesi (Bölüm 8.3.6). |
| İlgili işler | `F3-050` TX özeti; `F1-015` TransmissionInterval modeli. |

## S-03 — Test mühendisi: Kanal karşılaştırma ve spektral analiz

| Alan | İçerik |
| --- | --- |
| Rol | Test mühendisi (4.2) |
| Ön koşul | Kayıt açık; en az iki akustik kanal mevcut. |
| Girdi | 96 kHz örneklemeli `Hydrophone 01` ve `Hydrophone 02` kanalları; 2 saniyelik bir bölge; içinde bilinen 5 kHz'lik ton bulunur. |
| Adımlar | 1) İki kanal aynı grafiğe eklenir. 2) Bölge seçilir. 3) FFT ve spektrogram uygulanır. |
| Gözlenebilir sonuç | Zaman serisi iki eğriyi ayrı renkle çizer; FFT grafiğinde tepe 5 kHz ± bin genişliği içinde görünür; spektrogram aynı frekansta sürekli bir şerit gösterir; eksen birimleri ve pencere/örtüşme ayarları grafik başlığında okunur. |
| Kabul kanıtı | Bilinen tonlu sentetik fixture ile tepe frekansının sayısal doğrulaması. |
| İlgili işler | `F4-001`–`F4-020` spektral analiz; `F0-009` fixture beklentileri. |

## S-04 — Test mühendisi: Bölge ölçümü, açıklama ve dışa aktarma

| Alan | İçerik |
| --- | --- |
| Rol | Test mühendisi (4.2) |
| Ön koşul | S-03 sonundaki görünüm açık. |
| Girdi | Seçili ROI: `00:01:04.000`–`00:01:06.000`; kanal `Hydrophone 01`. |
| Adımlar | 1) ROI üzerinde istatistik kartı okunur. 2) Açıklama eklenir. 3) CSV ve PNG dışa aktarılır. |
| Gözlenebilir sonuç | İstatistik kartı min/maks/ortalama/RMS ve örnek sayısını gösterir; açıklama timeline'da etiketli görünür; CSV dosyası yalnız seçili aralığı ve birim başlığını içerir; PNG'de eksen, birim ve zaman aralığı okunabilir. |
| Kabul kanıtı | CSV ilk/son satırındaki zaman damgalarının ROI sınırlarıyla eşleşmesi; örnek sayısının `2 s × 96 kHz = 192000` olması. |
| İlgili işler | `F3-060` export; `F4-074` annotation modeli. |

## S-05 — Geliştirici: Bozuk kayıt tanılaması

| Alan | İçerik |
| --- | --- |
| Rol | Yazılım/donanım geliştiricisi (4.3) |
| Ön koşul | Tanılama görünümü etkin. |
| Girdi | Bilerek bozulmuş fixture: `Data00003` CRC hatalı, `Data00005` eksik (sıra boşluğu), son kayıt kesik. |
| Adımlar | 1) Dosya açılır. 2) Tanılama/log paneli incelenir. |
| Gözlenebilir sonuç | Uygulama dosyayı açmayı reddetmez; üç sorun ayrı satır olarak listelenir (`CRC hatası`, `sıra boşluğu`, `kesik kayıt`); her satır kayıt adını, `record_index` değerini ve dosya offsetini gösterir; grafik `Data00005` yerinde uydurma veri değil kesinti gösterir; sağlam kayıtlar normal çizilir. |
| Kabul kanıtı | `F0-010` bozuk fixture senaryolarının beklenen çıktısıyla birebir karşılaştırma. |
| İlgili işler | `F0-010` bozuk fixture; `F2-030` civarı decoder tanılama raporu. |

## Kapsam notu

Bu beş senaryo ilk kabul yüzeyidir; MVP "Definition of Done" (Bölüm 23) bunların tümünü gerçek veya sentetik kayıt üzerinde çalışır durumda ister. Yeni senaryolar aynı tablo biçimiyle eklenir ve bir iş kimliğine bağlanır.
