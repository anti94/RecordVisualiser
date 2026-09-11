# İndeksli akustik sorgu — F4-091 / F4-092

`build_profile_b_index` dosya ve kayıt/blok header'larını okuyarak konum, örnek
sayısı ve zaman offsetlerini toplar. Payload dizileri üretmez; indeks kaynak
eşlemesine referans tutmaz. Kayıt boyutları değişebilir, bilinmeyen bloklar
konumlarıyla korunur. Kayıt sınırını aşan blok ve kesik kayıt reddedilir;
son tam kayıttan sonraki kısa kuyruk `trailing_bytes` ile raporlanır.

Bir dosyayı art arda sorgulayan kod `AcousticQuery(buffer)` nesnesini bir kez
oluşturur ve `reader.query(channel_id, time_range)` çağırır. `buffer` bu oturum
boyunca değişmeyen salt okunur snapshot olmalıdır. Tek seferlik
`query_acoustic_channel` yardımcı işlevi her çağrıda kendi indeksini kurar.

Sorgu, kanalın sıralı blok başlangıçları ve kümülatif bitişleri üzerinde ikili
arama yapar. Yalnız örtüşen kayıtlardaki seçili örnekler float64/zaman dizisine
çevrilir. Başlangıç ve bitiş örnek indeksleri tam sayı aritmetiğiyle bulunur;
48 kHz gibi ns'ye tam bölünmeyen periyotlarda sınır kayması oluşmaz.
Sırasız ve örtüşen kayıtlar kayıp olmadan kararlı zaman sırasına getirilir.

FileHeader CRC'si açılışta, kayıt payload CRC'si yalnız sorgunun dokunduğu
kayıtlarda doğrulanır. CRC uyuşmazlığında örneklerin zamanları korunur; değerler
NaN, kalite `CRC_ERROR` olur. Kontrol sonuçları 4096 girdilik sınırlı önbellekte
tutulur. Bu katman ham int16 değerlerini float64'e çevirir; kanal kalibrasyonunu
uygulama sorumluluğu fiziksel kanal/repository katmanında kalır.

`last_records_read`, son sorgunun payload okuduğu benzersiz kayıt sayısıdır.
Testlerde dosya 8 kayıttan 512 kayda büyürken aynı sınır aşan 125 ms pencere
6000 örnek döndürmüş, iki kayda dokunmuş ve sorgu başına ayrılan tepe bellek
1 MB altında kalmıştır. İndeks kurma maliyeti bu sorgu ölçümünden ayrıdır.
`large_file_benchmark.py` indeksi bir kez kurar ve `index_seconds` alanında
maliyetini ayrıca raporlar.

Tam kayıt aralığı istendiğinde sonuç doğal olarak bütün örnekleri içerir.
Bu değişiklik tek başına tam kayıt görünümünün bellek sınırını kanıtlamaz;
F4-093 aynı benchmark'ı bu durumu da içerecek şekilde yeniden değerlendirir.
