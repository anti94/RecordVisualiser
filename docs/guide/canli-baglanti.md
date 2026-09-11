# Canlı bağlantı ve kayıt kullanım örneği — `F6-026`

Bu belge üç taşıma protokolünü, bağlantı kesintisinde ne olduğunu ve
alınan kaydın nasıl yeniden açılacağını anlatır. Ekranlar dosya
modundakiyle **aynıdır**: canlı akış, dosya tarafıyla aynı sorgu
sözleşmesini karşılayan bir depo üzerinden beslenir, bu yüzden grafikler
ve analiz hücreleri veri kaynağına göre değişmez.

## 1. Üç protokol

| Protokol | Ne zaman | Taşımaya özgü davranış |
| --- | --- | --- |
| **UDP** | Cihaz yayın yapıyor, kayıp kabul edilebilir | Paket parçalara bölünür ve birleştirilir; bir parça 500 ms içinde gelmezse **paketin tamamı** düşer |
| **TCP** | Kayıpsız bağlantı isteniyor | Uzunluk önekli çerçeveleme; bağlantının düzgün kapanması (EOF) ile koparılması (RST) ayrı durumlardır |
| **Seri port** | Doğrudan kablo | `SYNC` (0xAA55) ile hizalanır; her çerçevede CRC32 doğrulanır, 1000 ms sessizlik zaman aşımıdır |

Üçü de aynı paket sözleşmesini üretir (`docs/live/protocol-contract.md`).
Tüketici taraf hangisinin bağlı olduğunu bilmez; bu yüzden protokol
değiştirmek arayüzü değiştirmez.

> **Seri port** isteğe bağlı `live` ekstrasını gerektirir:
> `pip install -e ".[gui,live]"`. Kurulu değilse bağlantı **açık bir hata**
> verir, sessizce başarısız olmaz.

### 1.1 Bağlanmak

**Tools → Connect Live Source** (`Ctrl+Shift+C`) ya da araç çubuğundaki
düğme. Bağlantı ayarları (adres, port, baud) **Settings**'te tutulur ve
oturumlar arasında saklanır.

Bağlandığınızda:

- durum çubuğundaki **bağlantı alanı** doluşur,
- sağ sütunda **Live** sekmesi belirir (varsayılan yerleşim değişmez),
- `Connect` pasifleşir, `Disconnect` etkinleşir.

Araç çubuğu ile durum çubuğu **tek bir kaynaktan** beslenir; ikisi farklı
şey söyleyemez.

### 1.2 Canlı sağlık sayaçları

**Live** sekmesi şunları gösterir ve hiçbirini kendi hesaplamaz:

| Alan | Ne demek |
| --- | --- |
| Alınan / Düşen paket | Kaynaktan gelen ve kaybolan paket sayısı |
| Kayıp oranı | Düşen / alınan |
| Atlanan (sıra boşluğu) | Sıra numarası atlayan pencereler ve kaç paket eksik |
| Tekrarlı · Sıra dışı | Aynı paketin iki kez gelmesi · geç gelen paket |
| Kuyruk · Kuyruk tepe | Anlık ve en yüksek kuyruk doluluğu, düşen paketle birlikte |
| Tampon | Halka tamponda tutulan örnek / kapasite |

**Kayıp görünürdür ve sessizce geçilmez.** "Kayıp yok" yazısına bakıp veri
kaybetmek, bu sayaçların var olma nedenidir.

### 1.3 Sona takip

Canlı akışta viewport son pencereyi izler. **Grafikte gezindiğiniz anda
takip kapanır** ve bir daha zorla sona taşınmazsınız; incelediğiniz yerden
koparılmazsınız. Takibi yeniden açmak için sona dönün.

Canlı akış başlarken playback saati durur: iki saatin aynı grafiği
eşzamanlı ilerletmesi, gördüğünüz zamanın hangi kaynaktan geldiğini
belirsizleştirirdi.

## 2. Bağlantı kesintisi

Kesinti üç biçimde olur ve üçü de **ayrı** durumlardır:

| Durum | Ne olur |
| --- | --- |
| Kullanıcı `Disconnect` dedi | Kayıt varsa kapatılır, neden "bağlantı kesildi" yazılır |
| Kaynak çöktü (soket hatası) | Okuma hatası loglanır, kayıt "kaynak hatası" ile kapanır |
| Geçici kopma | Yeniden bağlanma denenir: üstel, tavanlı gecikme ve **görünür** denemeler |

Yeniden bağlanma sonsuza kadar denenmez; sınır aşılınca vazgeçilir ve
durum `FAILED` olur. Her deneme log'a yazılır.

### 2.1 Kesinti sırasında kayıt

Kayıt sürüyorsa kesintide **tam kayıtlar korunur**. Dosya güvenle
kapatılır: kuyrukta bekleyen bloklar diske iner, `fsync` yapılır ve kayıt
sınırına oturmayan yarım bayt kuyruğu kesilir.

Log'a iki şey yazılır:

- **kapanış nedeni** — kullanıcı durdurdu / bağlantı kesildi / kaynak
  hatası / disk hatası. Diskte bu dosyalar birbirinin aynıdır; neden
  yazılmazsa sonradan ayırt edilemez.
- **boşluklar** — hiç gelmeyen pencereler, aralık ve sayı olarak
  (`3..6 arası 4 pencere gelmedi`). Boşluk yoksa bu da açıkça yazılır;
  sessizlik "sorun yok" anlamına gelmemeli.

## 3. Kayıt almak

**Tools → Record** (`Ctrl+R`), klasör seçilir. **Stop** (`Ctrl+Shift+R`)
kaydı bitirir.

Kayıt sürerken durum çubuğunda ve sağdaki **Kayıt Durumu** kartında aynı
üç bilgi görünür: aktif dosya, geçen süre ve kayıt sayısı. İkisi tek bir
değerden türer.

**Geçen süre veriden türetilir, duvar saatinden değil.** Akış durursa süre
de durur; elinizde olmayan saniyelerin kaydedildiğini sanmazsınız.

### 3.1 Dosya değiştirme

Kayıt iki sınırda yeni dosyaya geçer:

- **boyut** — dosya sınırı aşacaksa (aşmadan önce),
- **isim** — sıra numarası `Data9999999`'a dayandığında
  (`docs/format/timing-and-naming.md`).

Yeni dosya **kendi içinde tutarlıdır**: ilk kaydı `Data00000` ve
`elapsed_us = 0`'dır; başlangıç zamanı o kaydın pencere başlangıcıdır.
Yani her dosya tek başına, öncekine bakmadan doğru okunur.

### 3.2 Disk dolarsa

Kayıt **hata durumuna geçer ve "başarılı kayıt" mesajı verilmez**.
Kurtulan kayıt sayısı ve dosya yolu bildirilir; dosya **silinmez** —
elde olan veri, olmayandan iyidir.

Kayda başlarken de boş alan denetlenir: yer yetmiyorsa kayıt hiç
başlamaz. Birkaç saniye sonra ölecek bir kayıt, kaydınız var sanmanıza
yol açardı.

## 4. Kaydı yeniden açmak

Alınan `.bin` dosyası **File → Open** ile açılır; ayrı bir mod yoktur.
Dosya Profil A sürüm 2'dir ve her kayıt CRC taşır.

Yeniden açtığınızda:

- örnekler kaynaktaki değerlerle **birebir** aynıdır,
- ardışık kayıtlar arasındaki fark tam **125 ms**'tir,
- BIT arızaları ve TX aralıkları kayıttaki pencerede görünür.

Bu, `F5-035`'te uçtan uca doğrulanmıştır: canlı akış kaydedilip üretim
okuyucusuyla yeniden açılmış ve örnekler, olaylar ve 125 ms sınırları
kaynakla karşılaştırılmıştır.

> Paket kaybı olan bir kayıtta **boşluk kalır**: eksik pencereler dosyada
> yoktur ve sıra numaraları atlar. Bu bir bozulma değildir; sıra
> numarası zamandan türetilir, bu yüzden kalan kayıtlar kendi doğru
> zamanlarında durur.

## 5. İlgili belgeler

- Ana ekran: `docs/guide/ana-ekran.md`
- Wire sözleşmesi: `docs/live/protocol-contract.md`
- Dayanıklılık raporu: `docs/live/endurance-report.md`
- Format: `docs/format/profile-a.md`, `docs/format/timing-and-naming.md`
