# Profil C klasör indeksi — açılış ölçümü

`F7-035` çıktısı. Ölçüm aracı: `tools/profile_c_index_benchmark.py`.
Ham sonuç: [`results/profile-c-index.json`](results/profile-c-index.json).

## Soru

10 dakikalık bir kayıt akım başına 600, toplam **1.200 dosya** taşır
(`docs/format/profile-c.md` §3.4). Bu klasörün indeksi kurulurken plan
Bölüm 11'deki **3 saniyelik ilk açılış bütçesi** aşılıyor mu?

## Ölçüm neden ikiye ayrıldı

Maliyetin iki bileşeni var ve ikisi farklı ölçekleniyor:

| Bileşen | Neye bağlı | Nasıl ölçüldü |
| --- | --- | --- |
| Dosya sayısı maliyeti | Dizin taraması, `stat`, ad ayrıştırma | 1.200 **küçük** dosya (2 KB) |
| Dosya başına okuma | Başlık ve frame başlıklarının çözülmesi | 40 **tam boyutlu** dosya (2 MiB) |

1.200 tam boyutlu dosya 2,35 GiB tutar. Her ölçümde onu diske yazmak,
indeksi değil **diski** ölçmek olurdu. Bu yüzden iki ölçüm birleştirilip
tavana çıkarım yapılıyor ve çıkarım olduğu burada yazılı.

## Sonuç

| Ölçüm | Dosya | Dosya boyutu | Tarama | Okuma |
| --- | --- | --- | --- | --- |
| Küçük | 1.200 | 1.984 B | 62 ms (0,052 ms/dosya) | 1.226 ms (1,022 ms/dosya) |
| Tam boyutlu | 40 | 2.100.544 B | 7 ms (0,185 ms/dosya) | 64 ms (1,609 ms/dosya) |

**Çıkarım: 1,99 s.** Bütçe 3,0 s. Sığıyor, payı %34.

## Ölçümün söylediği asıl şey

Tam boyutlu bir dosyayı okumak 1,61 ms, 2 KB'lik bir dosyayı okumak
1,02 ms sürüyor. Dosya bin kat büyüdüğünde maliyet yalnız **%57**
artıyor.

Yani darboğaz veri hacmi değil, **dosya başına sabit maliyet**: açma,
konumlanma, kapatma. 1.200 dosyanın kendisi 2,4 GiB'lik içerikten daha
pahalı.

Bunun bir sonucu var: dosyaları küçültmek (örneğin yarım saniyelik
dosyalar) açılışı **yavaşlatır**, hızlandırmaz. 1 saniyelik dilim seçimi
bu ölçümle desteklenir.

## Bu ölçümün sınırı

**Ölçüm önbellek sıcak.** Dosyalar ölçümden hemen önce yazıldığı için
işletim sistemi sayfa önbelleğinde duruyorlardı. Soğuk bir disk üzerinde
okuma maliyeti daha yüksek olur.

Bu, sonucu geçersiz kılmaz ama sınırını çizer: 1,99 s **en iyi durumdur**.
Gerçek bir kayıt arşivden ilk kez açıldığında bütçeye daha yakın
olacaktır. Soğuk ölçüm, gerçek Profil C kaydı geldiğinde (`E-11`)
yapılmalıdır.

İkinci sınır: ölçüm bu geliştirme makinesinde yapıldı. Hedef makinenin
disk ve dosya sistemi özellikleri bilinmiyor (`D-15`).

## İndeks ne kadar tasarruf ettiriyor

İndeks kurulduktan sonra ikinci açılış yalnız parmak izini doğrular:
1.200 dosyanın `stat` bilgisi okunur, içerikleri okunmaz. Bu, tablodaki
**tarama** satırıdır: 62 ms.

Yani indeks ilk açılışı 1,99 saniyeden 0,06 saniyeye indiriyor —
otuz katından fazla. İndeksin var olma gerekçesi budur.

## Yeniden koşturma

```powershell
.venv\Scripts\python.exe tools\profile_c_index_benchmark.py --out docs\perf\results\profile-c-index.json
```

Araç bütçe aşılırsa sıfırdan farklı çıkış kodu döner; CI'da kapı olarak
kullanılabilir.
