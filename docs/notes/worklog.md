# İş günlüğü — süreler, atlanan işler ve notlar

> Bu dosya Bölüm 22 iş tablosunun yerine geçmez. Amaç, **her işin gerçekte ne kadar sürdüğünü** ve
> **yapılamayan veya eksik bilgiyle yapılan işleri** kaybetmeden kaydetmektir. Bir iş burada
> `ATLANDI` ise plan tablosunda `[ ]` olarak kalır ve engeli kalkınca tekrar ele alınır.
>
> Güncel madde listesi: `docs/notes/todo.md` (`python tools/sync_todo.py` ile üretilir).

## 1. Süreler

**Gerçek süre nasıl ölçülüyor:** bir işin commit'i ile bir önceki commit arasındaki zaman farkı.
Commit, o işin bitişidir; dolayısıyla fark, önceki iş bittikten sonra bu işe harcanan süredir.
Ölçüm otomatiktir, tahmin değildir.

Tablo `python tools/worklog_stats.py --update` ile üretilir; **elle düzenlenmez.**

<!-- SURELER:BASLANGIC -->

| İş ID | Hedef | Gerçek | Commit | Konu |
| --- | --- | --- | --- | --- |
| `F0-001` | 15 dk | — | `61e4fca` | git başlangıcını, ignore kurallarını ve VERSION kaynağını hazırla |
| `F0-002` | 15 dk | 1 dk 42 sn | `80c49ac` | üç kullanıcı rolü için ilk beş senaryoyu yaz |
| `F0-003` | 20 dk | 1 dk 44 sn | `985bceb` | örnek dosya ve format envanterini çıkar |
| `-` | — | 26 sn | `7be4fae` | gece koşusu için iş günlüğü ve atlama notlarını başlat |
| `F0-004` | 15 dk | 1 dk 10 sn | `4871335` | 32 byte örnek header sözleşmesini çıkar |
| `F0-005` | 20 dk | 56 sn | `713f6b7` | 64 byte örnek Data kayıt sözleşmesini çıkar |
| `F0-006` | 15 dk | 2 dk 3 sn | `141bdd2` | 125 ms periyot ve kayıt adı kurallarını belgeye bağla |
| `F0-007` | 20 dk | 1 dk 43 sn | `4e3aaa2` | mockup kanal gruplarını örnek veri sözlüğüne eşleştir |
| `F0-008` | 20 dk | 1 dk 38 sn | `e2b33ed` | CRC destekleyen formatın karar kaydını yaz |
| `F0-009` | 15 dk | 1 dk 41 sn | `c50bcb0` | küçük geçerli fixture için beklenen sonuçları yaz |
| `F0-010` | 15 dk | 1 dk 39 sn | `df8cf80` | bozuk fixture senaryolarının sonuçlarını yaz |
| `F0-011` | 20 dk | 3 dk 44 sn | `250bd0c` | UTC ve cihaz zamanı dönüşüm kararını yaz |
| `-` | — | 2 dk 27 sn | `b05a64d` | plan.md'den üretilen todo listesi ve süre kaydı ekle |
| `F0-012` | 20 dk | 2 dk 5 sn | `f144dea` | referans mockup'ın dokuz bölgesini yerleşime eşleştir |
| `F0-013` | 20 dk | 1 dk 45 sn | `35c00df` | mockup etkileşimleri ve görsel kabul listesini yaz |
| `F0-014` | 20 dk | 2 dk 27 sn | `71bbb85` | ölçüm bilgisayarı ve performans bütçesini kaydet |
| `F0-015` | 20 dk | 1 dk 27 sn | `5a833ce` | açık kararları ve dış bağımlılıkları kaydet |
| `F0-016` | 15 dk | 1 dk 28 sn | `86490c3` | ADR listesini iş ve sürüm hedefleriyle eşleştir |
| `F0-017` | 15 dk | 1 dk 26 sn | `35d7f68` | format milestone kabul tutanağını hazırla |
| `F1-001` | 20 dk | 6 dk 50 sn | `6e4a36f` | python paket iskeleti ve bağımlılık kilidini oluştur |
| `F1-002` | 15 dk | 1 dk 57 sn | `d7f0a90` | tek komutluk geliştirici kurulumunu yaz |
| `F1-003` | 15 dk | 1 dk 13 sn | `95a3fb3` | ruff kontrol yapılandırmasını ekle |
| `F1-004` | 15 dk | 2 dk 56 sn | `052a3df` | pyright tip kontrolünü ekle |
| `F1-005` | 15 dk | 4 dk 9 sn | `3b14a71` | pytest ve pytest-qt başlangıç düzenini kur |
| `F1-006` | 20 dk | 1 dk 17 sn | `89f8bec` | Windows kalite kontrol iş akışını ekle |
| `F1-007` | 20 dk | 1 dk 56 sn | `6860120` | uygulama girişini ve temiz kapanışı ekle |
| `F1-006` | 20 dk | 1 dk 17 sn | `dcfe128` | checkout satır sonlarını LF'e sabitle ( düzeltmesi) |
| `F1-008` | 20 dk | 4 dk 1 sn | `5a02e57` | merkezi exception yakalama yolunu ekle |
| `F1-009` | 20 dk | 2 dk 38 sn | `06c4c6b` | sürümlü temel ayarları yükle ve kaydet |
| `F1-010` | 20 dk | 4 dk 33 sn | `991b9c4` | dönen log ve session kimliği ekle |
| `-` | — | 1 dk 40 sn | `b3b3a74` | pyright/ruff sürümlerini sabitle ve default_factory tipini düzelt |
| `F1-011` | 15 dk | 1 dk 15 sn | `87b3c64` | ChannelMetadata modelini tanımla |
| `F1-012` | 15 dk | 1 dk 34 sn | `a01a899` | DataChunk ve kalite alanlarını tanımla |
| `-` | — | 2 dk 34 sn | `9d1a104` | iş sürelerini git geçmişinden otomatik üret |
| `-` | — | 1 dk 22 sn | `0d11b80` | numpy sürümünü sabitle, CI'a sürüm raporlama ekle |
| `F1-013` | 15 dk | 1 dk 30 sn | `074f936` | TimeRange ve RecordingMetadata modellerini ekle |
| `F1-014` | 15 dk | 1 dk 27 sn | `0e21f97` | Event ve BitResult modellerini ekle |
| `F1-015` | 15 dk | 1 dk 27 sn | `3afe5f3` | TransmissionInterval modelini ekle |
| `F1-016` | 20 dk | 3 dk 19 sn | `04534ec` | RecordingRepository protokolünü tanımla |
| `F1-017` | 15 dk | 1 dk 40 sn | `020f243` | LiveSource protokolünü tanımla |
| `F1-018` | 15 dk | 430 dk 17 sn | `36b9809` | deterministik sinüs üretecini ekle |
| `F1-019` | 20 dk | 1 dk 40 sn | `72145e4` | noise, chirp ve impulse örneklerini ekle |
| `F1-020` | 20 dk | 1 dk 55 sn | `48f95dc` | sahte kanal repository uygulamasını ekle |
| `F1-021` | 15 dk | 2 dk 18 sn | `a11d9f3` | sahte BIT, TX ve sistem olaylarını ekle |
| `F1-022` | 20 dk | 2 dk 38 sn | `59ce1b7` | mockup'ın üç sütunlu ana pencere düzenini oluştur |
| `F1-023` | 15 dk | 3 dk 30 sn | `5a20b3e` | menü ve toolbar eylem iskeletini ekle |
| `F1-024` | 15 dk | 7 dk 22 sn | `ea51cac` | Data Explorer dock'unu ekle |
| `F1-025` | 15 dk | 4 dk 43 sn | `b59e723` | Inspector'ı bağlamsal araç sekmesi olarak ekle |
| `F1-026` | 15 dk | 1 dk 59 sn | `d34620a` | alt Log/Messages alanı ve Events sekmesini ekle |
| `F1-013` | 15 dk | 34 sn | `e6832b4` | worklog'a ..F1-026 durumları ve bulunan sorunları ekle |
| `-` | — | 3 dk 25 sn | `720d5de` | pyright pythonVersion sabitini kaldır |
| `-` | — | 2 dk 34 sn | `b905773` | CI'nin 3.12 pyright hatasını açık sorun olarak kaydet |
| `-` | — | 344 dk 17 sn | `5f0d20b` | pyright bulgularını GitHub annotation'a çevir |
| `-` | — | 3 dk 9 sn | `702ec61` | pyright çıkış kodunu yutup annotation adımına ulaş |
| `-` | — | 3 dk 55 sn | `8c930f3` | PySide6 sürümünü sabitle, Qt None kontrollerini geri koy |
| `-` | — | 3 dk 53 sn | `814476a` | CI 3.12 pyright sorununu çözüldü olarak kapat |
| `F1-027` | 15 dk | 2 dk 54 sn | `5f679d9` | Playback/Time Control şeridini yerleştir |
| `F1-028` | 15 dk | 3 dk 21 sn | `18eddb8` | durum çubuğu alanlarını ekle |
| `F1-029` | 20 dk | 242 dk 21 sn | `6a735d1` | mockup koyu temasını ve mavi vurgularını uygula |
| `F1-030` | 20 dk | 2 dk 8 sn | `2bc3f14` | durum ikonları ve kanal paletini ekle |
| `F1-031` | 20 dk | 2 dk 45 sn | `50da59f` | tek kanallı PlotPanel iskeletini ekle |

**61 commit · olculen toplam 1153 dk 44 sn · olculemeyen 1 (ilk commit)**

<!-- SURELER:BITIS -->

## 2. İşlerin durumu

Durum kodları: `TAMAM` · `ATLANDI` (engel var) · `KISMİ` (varsayımla yapıldı, doğrulama bekliyor)

| İş | Durum | Not |
| --- | --- | --- |
| `F0-001` | TAMAM | `.gitattributes` da eklendi: golden `.bin` fixture'larının satır sonu dönüşümüyle bozulmaması için gerekliydi. |
| `F0-002` | TAMAM | Beş senaryo. |
| `F0-003` | TAMAM | Depoda gerçek `.bin` yok; E-01..E-10 eksik girdiler işaretlendi. |
| `F0-004` | **KISMİ** | Header sözleşmesi Bölüm 8.2 **taslağına** göre yazıldı; gerçek format dokümanı (D-02) gelince karşılaştırılmalı. |
| `F0-005` | **KISMİ** | Aynı gerekçe: 64 byte kayıt sözleşmesi taslak kaynaklı. |
| `F0-006` | TAMAM | Profiller arası ad sarması çelişkisi bulundu ve giderildi. Süreye, commit mesajı ile içerik uyuşmadığı için yapılan düzeltme (amend) dahil. |
| `F0-007` | **KISMİ** | Kanal eşlemesi **öneri**dir; gerçek kanal kataloğu (D-06) ve BIT test kataloğu (D-07) yok. Mockup 8 BIT alt sistemi gösteriyor, öneri harita 3 grup — genişletilmeli. |
| `F0-008` | **KISMİ** | CRC algoritması seçildi (ADR-011) ama donanım onayı yok (D-05). |
| `F0-009` | TAMAM | Beklenen baytlar üretilip doğrulandı; float32 round-trip kayıpsız. |
| `F0-010` | TAMAM | Dört zorunlu senaryoya ek olarak K-05 ve K-06 tanımlandı. |
| `F0-011` | TAMAM | ADR-003. Süre, iki kez başarısız olan kabuk komutunun yeniden yazılmasını içerir. |
| `F0-012` | TAMAM | Mockup görseli okundu; planda olmayan kanallar ve 8 BIT alt sistemi tespit edildi. |
| `F0-013` | TAMAM | Etkileşim ve görsel kabul listesi; maddeler MVP/analiz/canlı aşamasına etiketli. |
| `F0-014` | **KISMİ** | Hedef ölçüm bilgisayarı bilinmiyor (D-15). GUI ölçümleri (P-04/P-05/P-08) iskelet olmadan yapılamadı. |
| `F0-015` | TAMAM | D-01..D-25 kütüğü. |
| `F0-016` | TAMAM | ADR-001..012 iş/sürüm eşlemesi. |
| `F0-017` | TAMAM | Faz 0 kabulü; gerçek veri eksikleri "doğrulanmadı" olarak ayrı bölümde. |
| `F1-001` | TAMAM | `requires-python` geçici olarak `>=3.9` (D-20). Paket kurulumu ve VERSION eşleşmesi doğrulandı. |
| `F1-002` | TAMAM | `-Recreate` ile sıfırdan koşuldu. |
| `F1-003` | TAMAM | Markdown dosyaları biçimlendirici kapsamı dışında tutuldu. |
| `F1-004` | TAMAM | Pyright **strict** modda 0 hata. Kilit dosyası ilk kez gerçekten kullanılabilir hâle geldi (`-Locked`). |
| `F1-005` | TAMAM | Katman kuralı artık testle korunuyor (`test_layering.py`). Kilit dev/gui olarak ikiye ayrıldı. |
| `F1-006` | TAMAM | CI ilk koşuda satır sonu farkı yüzünden düştü; `.gitattributes` `eol=lf` ile düzeltildi. |
| `F1-007` | TAMAM | Pencere yalnız **offscreen** doğrulandı; kullanıcının ekranında görünür pencere açılmadı. |
| `F1-008` | TAMAM | KeyboardInterrupt hata sayılmıyor. |
| `F1-009` | TAMAM | Bozuk ayar dosyası `.bozuk` uzantısıyla saklanıyor, atomik yazma. |
| `F1-010` | TAMAM | Ham sensör verisi filtreyle engelleniyor. Testlerin gerçek AppData'ya yazması da bu iş sırasında bulunup düzeltildi. |
| `F1-011` | TAMAM | Doğrulama kurucuda; geçersiz kanal oluşturulamıyor. |
| `F1-012` | TAMAM | Zaman/değer uzunluk tutarsızlığı kurucuda yakalanıyor. |
| `F1-013` | TAMAM | Ters aralık kurucuda reddediliyor. |
| `F1-014` | TAMAM | Tanınmayan BIT kodu UNKNOWN; PASS varsayılmıyor. |
| `F1-015` | TAMAM | Türetme, fixture beklentisiyle birebir aynı sonucu veriyor (250–750 ms). |
| `F1-016` | TAMAM | Sözleşmeyi karşılayan FakeRepository yazıldı; gerçek repository'ler aynı testlere tabi olacak. |
| `F1-017` | TAMAM | Modülün Qt yüklemediği ayrı süreçte doğrulanıyor. |
| `F1-018` | TAMAM | Nyquist üstü frekans reddediliyor; zaman ekseni tamsayı aritmetiğiyle. |
| `F1-019` | TAMAM | Seed sabit; chirp fazı frekansın integrali olarak hesaplanıyor. |
| `F1-020` | TAMAM | Sorgu sınırları yarı açık; aralık dışı sorgu boş parça döndürüyor. |
| `F1-021` | TAMAM | Olay zamanları sabit ve bilinir; rastgele olay üretilmiyor. |
| `F1-022` | TAMAM | Ölçülen sütunlar 1520 px pencerede tam 200 / 1008 / 300 px. |
| `F1-023` | **KISMİ** | Beş menü kuruldu ama **mockup dört menü gösteriyor** (Analysis yok). Karar bekliyor; `layout-map.md` §9'da kayıtlı. |
| `F1-024` | TAMAM | Ağaç hiyerarşik; arama derin ağaçta çalışıyor. |
| `F1-025` | TAMAM | Qt "tabified dock" yerine gerçek QTabWidget seçildi; gerekçe commit'te. |
| `F1-026` | TAMAM | Log ile Events ayrı; olaylar log'a yazılmıyor. |

## 3. Bu koşuda bulunan ve düzeltilen sorunlar

Hiçbiri plan işi değildi; çalışırken ortaya çıktı.

| Sorun | Nerede bulundu | Çözüm |
| --- | --- | --- |
| İki profil arasında kayıt adı sarma çelişkisi | `F0-006` | Sarma kaldırıldı, tek kural `timing-and-naming.md` |
| Boşluklu dosyada `32 + n*64` offset formülü yanlış kayda gidiyor | `F0-006` analiz | Uyarı yazıldı; K-03 fixture'ı bunu yakalıyor |
| İndeks olmadan 2,6 GiB dosyada 5 s açılış hedefi tutmuyor | `F0-014` ölçüm | `RecordIndex` ön koşul ilan edildi |
| Mockup'ta planda olmayan kanallar ve 8 BIT alt sistemi | `F0-012` | `layout-map.md` §9'a kaydedildi, D-06/D-07'ye bağlandı |
| Bağımlılık kilidi hiçbir akış tarafından kullanılmıyordu | `F1-004` | `setup-dev.ps1 -Locked` eklendi |
| CI'da `ruff format` düşüyor, yerelde geçiyordu (satır sonu) | `F1-006` CI | `.gitattributes` `eol=lf` |
| CI'da `pyright` düşüyor, yerelde geçiyordu (sürüm kayması) | `F1-009` CI | ruff ve pyright sabit sürüme çekildi |
| Testler kullanıcının gerçek `%LOCALAPPDATA%` ve `%APPDATA%` yollarına yazıyordu | `F1-010` | Ortam değişkeni yönlendirmesi + conftest; oluşan klasör silindi |
| Bir GUI testinden sonra `caplog` testleri sessizce bozuluyordu | `F1-010` | conftest her testten sonra logger durumunu geri koyuyor |
| CI'da `pyright` 3.12 ayağında düşüyor, 3.9'da geçiyordu (numpy sürümü) | `F1-012` CI | numpy `>=1.26,<2.1`'e sabitlendi; CI'a sürüm raporlama adımı eklendi |
| Sarmalanmayan `QLabel` panelin asgari genişliğini şişiriyordu (sağ sütun 300 yerine 424 px) | `F1-022` | Yer tutucu etiketler word-wrap edildi |
| Menülere Python referansı tutulmayınca PySide nesneyi serbest bırakıyordu ("C++ object already deleted") | `F1-023` | Menüler pencerede saklanıyor |
| Kanal yolunda `/` hem ayraç hem ad parçasıydı; ağaçta `"Vehicle "` diye bozuk grup çıkıyordu | `F1-024` | Yol `Vehicle/Voltage` yapıldı, gösterim etiketi `GROUP_LABELS` ile eşlendi |
| Qt tabified dock'ta aynı anda tek dock görünür sayıldığı için "kartlar duruyor mu" doğrulanamıyordu | `F1-025` | Sağ sütunda gerçek `QTabWidget` kullanıldı |
| CI'da `pyright` yalnız 3.12 ayağında düşüyordu (PySide6 taslak farkı) | CI #26–#30 | PySide6 sabitlendi, `None` kontrolleri geri kondu; teşhis için pyright annotation adımı eklendi |

## 3b. ÇÖZÜLDÜ: CI'nin Python 3.12 ayağında pyright hatası

**Durum: KAPALI.** CI üç işte de yeşil (koşu #31).

**Kök neden:** PySide6 tip taslakları sürüme göre değişiyor. Bir sürümde
`QTreeWidgetItem.child()` / `.parent()` `QTreeWidgetItem`, diğerinde
`QTreeWidgetItem | None` dönüyor. `F1-024`'te 3.9 ortamındaki taslağa uyup
`is not None` kontrollerini kaldırmıştım; aynı kod 3.12 ayağında
`reportOptionalMemberAccess` ve `reportArgumentType` hataları verdi. Kontroller
runtime açısından **doğruydu** — Qt üst düzey öğede `parent()` için gerçekten
null döndürüyor.

**Çözüm:** PySide6 `==6.10.3` olarak sabitlendi ve `None` kontrolleri geri kondu.
Taslak yanlış olduğunda doğru kontrolü hataya çeviren `reportUnnecessaryComparison`
stil kuralı kapatıldı; güvenlik kuralları açık bırakıldı.

**Teşhisi mümkün kılan adım:** CI job log'ları kimlik doğrulaması istiyor, ama
**annotations API'si istemiyor**. Bu yüzden `tools/pyright_annotations.py` eklendi:
pyright'ın JSON çıktısını `::error file=...,line=...` komutlarına çeviriyor.
İlk denemede annotation üretilmedi çünkü adım `bash -e` ile koşuyordu ve pyright
hata bulunca 1 döndürüp betiği durduruyordu; çıkış kodu yutulunca hata metni
okunabildi. Kalıcı fayda: pyright bulguları artık PR'larda satır satır görünüyor.

**Ders:** denetleyici davranışını değiştiren her bağımlılık (ruff, pyright, numpy,
PySide6) sabit sürümde tutulur; aralık bırakmak "bende geçti, CI'da kaldı"
farkını üretiyor.

## 4. Açık engeller

Ayrıntı: `docs/notes/open-decisions.md` (D-01..D-25) ve `docs/format/inventory.md` §2.

- **D-01/D-02 — gerçek `.bin` kaydı ve resmî format dokümanı yok.** Faz 0'ın format işleri
  taslağa göre yazıldı ve `KISMİ` sayıldı. Sentetik doğrulama gerçek donanım kanıtı sayılmaz.
- **D-05 — CRC tanımı yok.** ADR-011 öneri; donanım onayı bekliyor.
- **D-06/D-07 — kanal ve BIT test katalogları yok.**
- **D-09 — cihaz zaman kaynağı bilinmiyor.**
- **D-15 — hedef ölçüm bilgisayarı bilinmiyor.**
- **D-20 — Python 3.12 bu makinede kurulu değil** (yalnız 3.9.13 var). Kurulum sistem
  değişikliği olduğu için yapılmadı. **Kod 3.12'de doğrulanıyor:** CI matrisi hem 3.9 hem
  3.12 ile koşuyor ve geçiyor. Eksik olan yalnız yerel geliştirme ortamı.

## 5. Ortam notları

- **Python:** yerel `python` → 3.9.13. `requires-python` geçici olarak `>=3.9`; CI 3.12'yi de
  doğruluyor.
- **Sanal ortam:** `.venv` (3.9.13). PySide6 6.10.3 + Qt 6.10.3 kurulu; GUI testleri
  `QT_QPA_PLATFORM=offscreen` ile koşuyor.
- **Uzak depo:** `origin` → `https://github.com/anti94/RecordVisualiser`. Her iş commit'i ve
  sürüm etiketi push ediliyor.

## 6. Kullanıcıya sorulacaklar

- `.claude/settings.local.json` izlenmiyor ve `.gitignore` içinde de yok. Yerel izin ayarlarının
  yanlışlıkla commit edilmemesi için ignore kuralına eklenmesi öneriliyor.
- `SONAR Veri Analiz Panosu Mockup’ı.7z` arşivi izlenmiyor; kaynak PNG depoda olduğu için gerekli
  görülmedi. Silinsin mi, kalsın mı?
- Python 3.12 yerel kuruluma ne zaman eklenebilir? (D-20)
- Faz 1'in kalan işleri plan sırasıyla mı ilerlesin, yoksa parser/fixture (Faz 2) öne mi alınsın?
