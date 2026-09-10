# ADR-007 — Çizim için min/max özetleri

- Durum: Kabul edildi
- İlgili işler: F4-055–F4-058
- Tarih: 2026-09-10

Her çizim sorgusu en fazla `max_points` örnek döndürür. Kaynak sırasındaki
bitişik kovaların minimum ve maksimum değerleri, kendi orijinal zamanlarıyla
seçilir. Eşit minimumlarda ilk, eşit maksimumlarda son örnek seçilir; düz bir
sinyalin zaman kapsamı da korunur. Sonuç kaynak sırasına göre dizilir.

Sabit adımla örnek atlama dar impulsları kaybedebilir; ortalama almak tepe
genliğini küçültür. Min/max seçimi her kovadaki iki yönlü tepeleri korur.
FFT, PSD, STFT, istatistik ve DSP bu özeti girdi olarak kullanmaz.

Sonlu olmayan veri varsa kovaya üçüncü bir yer ayrılır ve ilk geçersiz örnek
korunur. Bütçe üçten küçükse bütün özellikleri aynı anda göstermek mümkün
değildir: önce geçersiz örnek, ikinci yer varsa en büyük mutlak sonlu değer
seçilir. Kalite bayrakları seçilen örnekten değişmeden alınır. Özet bütün
hata konumlarının veya olayların yerine geçmez.

Çok seviyeli özetlerde blok sınırları kaynak örnek indekslerine bağlıdır;
bir üst blok alt blokların uç değerlerinden oluşturulur. Viewport sınırını
kesen bloklar sorgu sırasında ham veriden tamamlanmalıdır. Seçilen seviye
nokta bütçesini aşarsa son çizim özeti tekrar sınırlandırılır.

Doğrulama: pozitif/negatif tek örneklik darbeler, sabit sinyal, düzensiz
zamanlar, NaN/kalite, küçük bütçeler ve referans kova min/max karşılaştırması.
