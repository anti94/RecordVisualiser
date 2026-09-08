# İş günlüğü — süreler, atlanan işler ve notlar

> Bu dosya Bölüm 22 iş tablosunun yerine geçmez. Amaç, **her işin gerçekte ne kadar sürdüğünü** ve
> **yapılamayan veya eksik bilgiyle yapılan işleri** kaybetmeden kaydetmektir. Bir iş burada
> `ATLANDI` ise plan tablosunda `[ ]` olarak kalır ve engeli kalkınca tekrar ele alınır.
>
> Güncel madde listesi: `docs/notes/todo.md` (plan.md'den `python tools/sync_todo.py` ile üretilir).

Durum kodları: `TAMAM` · `ATLANDI` (engel var) · `KISMİ` (varsayımla yapıldı, doğrulama bekliyor)

**Gerçek süre nasıl ölçülüyor:** ardışık iki commit'in zaman damgası farkı. Bir işin commit'i, o işin
bitişidir; dolayısıyla fark, önceki iş bittikten sonra bu işe harcanan süredir. Ölçüm otomatiktir,
tahmin değildir.

## Koşu: 2026-09-08 gecesi (23:31 –)

| İş ID | Durum | Hedef | Gerçek | Commit | Not |
| --- | --- | --- | --- | --- | --- |
| `F0-001` | TAMAM | 15 dk | — | `61e4fca` | İlk commit; önceki referans olmadığı için ölçülemedi. `.gitattributes` da eklendi: golden `.bin` fixture'larının satır sonu dönüşümüyle bozulmaması için gerekliydi. |
| `F0-002` | TAMAM | 15 dk | 1 dk 42 sn | `80c49ac` | `docs/scenarios.md`, beş senaryo. |
| `F0-003` | TAMAM | 20 dk | 1 dk 44 sn | `985bceb` | `docs/format/inventory.md`. Depoda gerçek `.bin` yok; E-01..E-10 eksik girdiler işaretlendi. |
| — | TAMAM | — | 26 sn | `7be4fae` | Bu günlüğün başlatılması (plan işi değil). |
| `F0-004` | KISMİ | 15 dk | 1 dk 10 sn | `4871335` | Header sözleşmesi Bölüm 8.2 **taslağına** göre yazıldı; gerçek format dokümanı (E-02) gelince karşılaştırılmalı. |
| `F0-005` | KISMİ | 20 dk | 56 sn | `713f6b7` | Aynı gerekçe: 64 byte kayıt sözleşmesi taslak kaynaklı. |
| `F0-006` | TAMAM | 15 dk | 2 dk 3 sn | `141bdd2` | Profiller arası çelişki bulundu ve giderildi (ad sarması). Süreye, commit mesajı ile içerik uyuşmadığı için yapılan düzeltme (amend) dahildir. |
| `F0-007` | KISMİ | 20 dk | 1 dk 43 sn | `4e3aaa2` | Kanal eşlemesi **öneri**dir; gerçek kanal kataloğu (E-04) ve BIT test kataloğu (E-05) yok. |
| `F0-008` | KISMİ | 20 dk | 1 dk 38 sn | `e2b33ed` | CRC algoritması seçildi (ADR-011) ama donanım onayı yok (E-03). Cihaz farklı CRC kullanıyorsa ADR değişir. |
| `F0-009` | TAMAM | 15 dk | 1 dk 41 sn | `c50bcb0` | Beklenen baytlar üretilip doğrulandı; float32 round-trip kayıpsız. |
| `F0-010` | TAMAM | 15 dk | 1 dk 39 sn | `df8cf80` | Dört zorunlu senaryoya ek olarak K-05 ve K-06 tanımlandı. |
| `F0-011` | TAMAM | 20 dk | 3 dk 44 sn | `250bd0c` | ADR-003. Süre, iki kez başarısız olan kabuk komutunun yeniden yazılmasını içerir. |

**Ara toplam:** 11 iş · hedef 3 sa 10 dk · gerçek yaklaşık 18 dk (ilk iş hariç).

## Açık engeller

Ayrıntı ve hangi işleri engelledikleri: `docs/format/inventory.md` Bölüm 2.

- **E-01/E-02 — gerçek `.bin` kaydı ve resmî format dokümanı yok.** Faz 0'ın format işleri
  (`F0-004`, `F0-005`, `F0-007`, `F0-008`) yalnız Bölüm 8.2/8.3 **taslağına** göre yazılabildi ve
  `KISMİ` sayıldı. Sentetik doğrulama gerçek donanım kanıtı olarak sunulmaz.
- **E-03 — CRC tanımı yok.** ADR-011 bir öneri sunar; algoritma donanım ekibi onayı olmadan kesinleşmez.
- **E-04/E-05 — kanal ve BIT test katalogları yok.** `channel-map.md` slot atamaları önerilmiştir.
- **E-07 — cihaz zaman kaynağı bilinmiyor.** ADR-003 sarma/reset/drift davranışını tanımlar ama
  gerçek `tick_hz` ve drift değeri ölçülemedi.
- **E-10 — hedef ölçüm bilgisayarı bilinmiyor.** `F0-014` performans bütçesi yalnız hedef olarak yazılabilir.

## Ortam notları

- **Python sürümü:** bu makinede `python` → **3.9.13**. Plan Bölüm 2 ve `F1-001` Python **3.12**
  öngörüyor. Faz 1'e geçmeden önce 3.12+ kurulmalı; aksi halde paket iskeleti ve tip
  ipuçları hedef sürümde doğrulanamaz. `tools/sync_todo.py` 3.9 ile de çalışacak şekilde yazıldı.
- **Satır sonu:** Git `core.autocrlf` nedeniyle çalışma kopyasında CRLF uyarısı veriyor; depoda LF
  normalize ediliyor (`.gitattributes`). Beklenen davranıştır.

## Kullanıcıya sorulacaklar

- `.claude/settings.local.json` depoda izlenmiyor ve `.gitignore` içinde de yok. Yerel izin
  ayarlarının yanlışlıkla commit edilmemesi için ignore kuralına eklenmesi öneriliyor.
- `SONAR Veri Analiz Panosu Mockup’ı.7z` arşivi izlenmiyor; kaynak PNG depoda olduğu için
  gerekli görülmedi. Silinsin mi, kalsın mı?
- Python 3.12 kurulumu ne zaman yapılabilir? Faz 1 buna bağlı.
