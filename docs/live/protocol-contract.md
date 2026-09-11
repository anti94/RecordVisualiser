# Canlı veri kaynağı — tel (wire) protokol sözleşmesi

> Durum: **TASLAK**. Kaynak: `plan.md` Bölüm 13. Gerçek cihaz protokolü gelene kadar
> (envanter E-01) bu sözleşme referans alınır; resmî doküman geldiğinde karşılaştırılıp
> güncellenir.
>
> Bu belge `src/sonar_analyzer/io/live/protocol.py` (`F1-017`) ile aynı katmanda değil,
> **bir alt katmandadır**: `LiveSource`/`LivePacket` uygulamanın gördüğü domain
> sözleşmesidir (Python `Protocol`, GUI'den bağımsız); bu belge o sözleşmeyi
> **doldurmak için ağdan okunan baytların** biçimini tanımlar. UDP/TCP/Serial
> adaptörleri (`F5-005`–`F5-010`) bu belgeye göre bayt çözüp `LivePacket` üretir.
>
> **Kayıtlı dosya formatları değişmez.** Profil A (`docs/format/profile-a.md`) ve
> Profil B (`docs/format/profile-b.md`) bu işten etkilenmez; canlı akış ayrı bir
> tel formatıdır ve yalnız 125 ms kayıt ızgarasını ve kanonik zaman modelini
> (ADR-003) paylaşır.

## 1. Ortak kurallar (üç protokol için de geçerli)

| Kural | Değer |
| --- | --- |
| Byte sırası | little-endian (Profil A/B ile tutarlı) |
| Kayan nokta | IEEE 754 |
| Paket ızgarası | her `LivePacket` **bir** 125 ms penceresini taşır (`RECORD_PERIOD_NS = 125_000_000`), aynı Profil A/B kayıt ızgarası |
| Sıra numarası | `uint32`, pencere başına bir artar; `2**32`'de sarar (bkz. §4) |
| Zaman kaynağı | **cihaz sayacı** (`device_ticks`, `int64`); kanonik UTC ns'e dönüşüm bağlantı kurulumunda değişilen `TimeBase` ile ayrı yapılır (ADR-003 §2.3, `F5-013`) — tel formatı hiçbir zaman UTC'yi **varsaymaz** |
| Host alım zamanı | tel formatının parçası **değildir**; adaptör paketi aldığı anda kendi saatiyle damgalar (`LivePacket.received_ns`, `F1-017`) — yalnız bağlantı sağlığı/gecikme tanılaması içindir, kanal verisine karışmaz |

Zaman kaynağının tek yerde tanımlanıp üç protokol için de aynen geçerli olması
kasıtlıdır: hiçbir protokol kendi zaman yorumunu getirmez, hepsi aynı
`LiveWireHeader.device_ticks` alanını taşır.

## 2. Ortak paket başlığı — `LiveWireHeader` (28 bayt)

Üç protokolün de baytları bu başlıkla başlar; ayrışan yalnız başlığın **etrafındaki
çerçevedir** (§3). Tek bir `struct.Struct("<4sBBHIHHqI")` ile üçü de çözülür —
adaptörler arasında kod paylaşımı buradan gelir.

| Alan | Tip | Bayt | Açıklama |
| --- | --- | --- | --- |
| `magic` | `4s` | 4 | `b"SNLV"` (**S**o**n**ar **L**i**v**e) |
| `version` | `uint8` | 1 | `1` |
| `protocol_id` | `uint8` | 1 | `1`=UDP, `2`=TCP, `3`=Serial |
| `flags` | `uint16` | 2 | bit 0: `HAS_EVENTS` (payload'da `Event` var); geri kalan ayrılmış, `0` |
| `sequence_no` | `uint32` | 4 | bu 125 ms penceresinin sıra numarası |
| `fragment_index` | `uint16` | 2 | bu parçanın sırası (§3.1) |
| `fragment_count` | `uint16` | 2 | pencerenin toplam parça sayısı (§3.1) |
| `device_ticks` | `int64` | 8 | pencere başlangıcının cihaz sayacı değeri |
| `payload_length` | `uint32` | 4 | bu **parçanın** payload uzunluğu (bayt) |

Toplam: `4+1+1+2+4+2+2+8+4 = 28` bayt. Payload'ın kendisi bu işin (F5-001)
kapsamı dışıdır — kanal/olay kodlaması `F5-006`'nın konusudur; bu belge yalnız
zarfı (envelope) sabitler.

### 2.1 `magic`/`version` reddi

Beklenmeyen `magic` veya desteklenmeyen `version` gelen bir çerçeve **tanınmaz
kabul edilir**: sessizce atlanmaz, adaptör bunu bir tanılama olayı olarak
sayar ve söz konusu pencereyi (aşağıdaki protokole özgü kayıp politikasıyla)
kayıp sayar.

## 3. Paket sınırı, protokole özgü çerçeveleme ve kayıp politikası

### 3.1 UDP

- **Paket sınırı:** bir UDP datagramı, bir `LiveWireHeader` + payload çerçevesi
  taşır; datagram sınırı işletim sistemi tarafından korunur (ek uzunluk alanına
  gerek yok — `payload_length` yalnız tutarlılık denetimi içindir).
- **Parçalama zorunluluğu:** bir 125 ms penceresinin toplam payload'ı IP
  parçalanmasını (fragmentation) tetikleyecek kadar büyükse (bkz. alt madde),
  pencere `fragment_count > 1` ile **birden çok datagrama** bölünür;
  `fragment_index` `0..fragment_count-1` sırasını taşır. Tek datagrama sığan
  pencerelerde `fragment_index=0`, `fragment_count=1`.
  - Güvenli tek-datagram payload sınırı: `1500 (tipik Ethernet MTU) - 20 (IP) -
    8 (UDP) - 28 (LiveWireHeader) = 1444` bayt. Bunu aşan bir pencere birden
    çok datagrama bölünmelidir; bölme kuralı ve kanal içeriği `F5-006`'nın işi.
- **Zaman kaynağı:** §1 — `device_ticks` her parçada aynıdır (pencerenin
  başlangıcı), parça sırası zamanı değiştirmez.
- **Kayıp politikası:**
  - UDP teslimi garanti etmez ve sırayı korumaz. Bir `sequence_no` için
    beklenen `fragment_count` parçanın hepsi **500 ms** (pencere süresinin
    4 katı) içinde tamamlanmazsa, o pencere **tümüyle** kayıp sayılır — kısmi
    pencere asla teslim edilmez (ya tam pencere ya hiç).
  - Kayıp pencereler `LiveStats.dropped_packets`'ı artırır; `sequence_no`
    boşluğu (`F5-012`) aynı bilgiyi sıra numarasından da doğrular.
  - Zaten çözülmüş/zaman aşımına uğramış bir `sequence_no`'ya ait geç gelen
    parça sessizce atılır (yeniden açılmaz, geriye dönük düzeltme yapılmaz).
  - Yeniden gönderim (retransmission) **yoktur** — canlı görünüm eski veriyi
    beklemez; bu politika `F5-016`'nın drop/backpressure kuralıyla tutarlıdır.

### 3.2 TCP

- **Paket sınırı:** TCP bir bayt akışıdır, datagram sınırı yoktur. Çerçeve
  sınırı **uzunluk öneki** ile kurulur: adaptör önce sabit `28` baytı
  (`LiveWireHeader`) okur, `payload_length`i öğrenir, sonra tam o kadar bayt
  daha okur. Bir `recv()` çağrısının bir çerçeveye denk gelmesi **varsayılmaz**
  — çerçeve birden çok `recv()`'e bölünebilir veya birden çok çerçeve aynı
  `recv()`'de gelebilir; adaptör kendi bayt tamponunda biriktirir (`F5-008`).
- **Parçalama:** TCP'de IP parçalanması akış katmanına görünmez; bu yüzden
  `fragment_count` **her zaman `1`**'dir. Büyük pencereler tek çerçevede,
  yalnız `payload_length` büyüyerek taşınır.
- **Zaman kaynağı:** §1, değişmez.
- **Kayıp politikası:** TCP aktarım katmanında bayt kaybı **olmaz**
  (yeniden iletim TCP'nin işi); `sequence_no` boşluğu yalnız iki durumda
  oluşur ve ikisi de **kaynağın** kaybıdır, taşımanın değil:
  1. Cihaz, göndermeden önce kendi tamponunda bir pencereyi düşürmüştür.
  2. Bağlantı kesilip yeniden kurulmuştur (`ConnectionState.RECONNECTING`);
     kesinti süresindeki pencereler asla gönderilmemiştir.
  Her iki durumda da `sequence_no` boşluğu aynı `F5-012` mekanizmasıyla
  saptanır ve `dropped_packets`'a yansır — TCP "kayıpsız" değildir, yalnız
  kaybın kaynağı ağ değil, kaynağın kendisidir.

### 3.3 Serial

- **Paket sınırı:** serial de bir bayt akışıdır ve TCP'nin aksine kendi
  bütünlük denetimi yoktur (gürültü, taşma, yanlış baud ile bayt bozulabilir).
  Bu yüzden çerçeve **açık bir eşitleme deseniyle** başlar ve **CRC32
  kuyruğuyla** biter:

  ```text
  SYNC(2B, 0xAA 0x55) | LiveWireHeader(28B) | payload(N B) | crc32(4B, LE)
  ```

  `crc32`, `LiveWireHeader` + `payload` üzerinden hesaplanır (Profil B'nin
  `RECORD_TRAILER` deseniyle aynı fikir: bütünlük kaynağın kendisinde
  doğrulanır, taşımaya güvenilmez).
- **Parçalama:** TCP gibi akış tabanlıdır, `fragment_count` **her zaman `1`**.
- **Zaman kaynağı:** §1, değişmez.
- **Kayıp politikası:**
  - `crc32` uyuşmazsa çerçeve **tümüyle** atılır (payload'ın bir kısmı bile
    güvenilmez sayılmaz); alıcı sıradaki `SYNC` desenini arayarak yeniden
    eşitlenir (resync) — bozuk bir çerçeve sonraki çerçeveleri kilitlemez.
  - Son geçerli çerçeveden sonra **1000 ms** içinde yeni bir `SYNC` + geçerli
    CRC görülmezse bağlantı `ConnectionState.RECONNECTING`'e geçer (port
    kapatılıp yeniden açılır); bu değer düşük baud hızlarında (§13 hedef
    donanım bilinmiyor, E-10) 125 ms'lik pencere periyodunun katbekat üstünde
    tutulmuştur ki geçici jitter yanlışlıkla bağlantı hatası sayılmasın.
  - CRC hatası veya zaman aşımı `dropped_packets`'ı artırır; hangisinin
    olduğu tanılama logunda ayrı ayrı görünür (`crc_errors` / `timeout_count`
    — `F5-010`'un sayaç alanları).

## 4. Sıra numarası sarması

`sequence_no` `uint32`'dir ve `2**32` pencerede (125 ms × 2³² = 536.870.912 s
≈ 17 yıl — pratikte hiçbir oturumda gerçekleşmez, ama sözleşme olarak
tanımlı olmalı) sarar. Sarma kuralı ADR-003 §2.4'teki `device_ticks` sarma kontrolüyle
**aynı desenle** ele alınır: ardışık iki `sequence_no` arasında değer
azaldıysa ve makul bir sarma farkına (`delta = (seq + 2**32) - prev_seq`,
nominal periyodun birkaç katı içinde) uyuyorsa sarma kabul edilir; uymuyorsa
"sayaç geri gitti" olarak işaretlenir ve kayıp sayılmaz — bu, tekrar bağlanan
bir kaynağın sıfırdan başlayan sayacını **kayıp** yerine **yeni oturum**
olarak yorumlamayı sağlar (ayrım `F5-012`'nin işidir, burada yalnız kural
sabitlenir).

## 5. Bu sözleşmenin sınırları

- Kanal/örnek/olay payload kodlaması burada tanımlanmaz — `F5-006`
  (`UDP paketlerini decoder'a bağla`) ve eşdeğerleri bunu üstlenir.
- `device_ticks → kanonik UTC ns` dönüşümü ve `TimeBase` değişimi (bağlantı
  kurulumunda hangi alan/handshake ile taşınacağı) burada tanımlanmaz —
  `F5-013`'ün işidir. Bu belge yalnız tel formatının UTC'yi **varsaymadığını**
  sabitler.
- Ring buffer boyutu, kuyruk sınırı ve backpressure/drop politikasının genel
  (protokolden bağımsız) kuralı burada tanımlanmaz — `F5-012`–`F5-016` ve
  ADR-009'un işidir. Bu belge yalnız **tel düzeyinde** (bir pencere hangi
  koşulda kayıp sayılır) kararları verir; kuyruğun **sonra** o kaybı nasıl
  raporladığı ayrı bir katmandır.
- Gerçek cihazın protokolü (UDP mü TCP mi seri mi, gerçek `magic`/alan
  adları) bilinmiyor (envanter E-01). Bu sözleşme üç protokolü de aynı
  zarfla soyutlamak için tasarlanmış bir **taslaktır**; gerçek protokol
  geldiğinde karşılaştırılıp güncellenecektir (bu belgenin başındaki uyarı).
