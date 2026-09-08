# Mimari karar kayıtları (ADR) — dizin ve zamanlama

> `F0-016` çıktısıdır. Plan Bölüm 28'deki ADR listesini **iş kimliği, hedef sürüm ve faz** ile eşler:
> her ADR ne hakkında, kim tetikliyor, hangi sürümde yazılmış olmalı.
>
> Kural: bir ADR, kararı **veren** işten sonra değil, kararı **uygulayan** ilk işten önce yazılır.
> Karar uygulandıktan sonra yazılan ADR, gerekçe değil savunma olur.

## Biçim

Her ADR şunları içerir: **bağlam · karar · değerlendirilen alternatifler · olumlu ve olumsuz
sonuçlar · karar tarihi · doğrulama**. Dosya adı: `ADR-<no>-<kısa-ad>.md`.

Durum: `YAZILDI` · `PLANLANDI` (tetikleyici iş henüz gelmedi) · `ERKEN` (karar gerekli ama
tetikleyici işten önce cevap bekliyor)

## Dizin

| ADR | Konu | Durum | Tetikleyici iş | Hedef sürüm | Faz | Belge |
| --- | --- | --- | --- | --- | --- | --- |
| ADR-001 | PySide6 seçimi (GUI çatısı) | PLANLANDI | `F1-001` | `0.18.0` | Faz 1 | — |
| ADR-002 | PyQtGraph ve plot abstraction sınırı | PLANLANDI | `F1-031` (spike sonuçları `F1-043`) | `0.48.0` | Faz 1 | — |
| ADR-003 | Kanonik timestamp birimi ve time-base modeli | **YAZILDI** | `F0-011` | `0.11.0` | Faz 0 | [`ADR-003-time-base.md`](ADR-003-time-base.md) |
| ADR-004 | Decoder versioning ve format detection | PLANLANDI | `F2-012` | `0.73.0` | Faz 2 | — |
| ADR-005 | Index/cache formatı | PLANLANDI | `F2-028` (atomik yazım `F2-031`) | `0.89.0` | Faz 2 | — |
| ADR-006 | Thread/process çalışma modeli | PLANLANDI | `F3-002` (DSP worker `F4-003`) | `0.104.0` | Faz 3 | — |
| ADR-007 | Downsampling algoritması | PLANLANDI | `F4-056` (çok seviyeli özet `F4-057`) | `1.56.0` | Faz 4 | — |
| ADR-008 | Workspace JSON şeması ve migration | PLANLANDI | `F3` workspace işleri | Faz 3 sonu | Faz 3 | — |
| ADR-009 | Live-source / backpressure politikası | PLANLANDI | `F5-016` | `2.16.0` | Faz 5 | — |
| ADR-010 | Native hızlandırmaya geçiş ölçütleri | PLANLANDI | `F4-067` | `1.67.0` | Faz 4 | — |
| ADR-011 | CRC destekleyen format sürümü | **YAZILDI** | `F0-008` | `0.8.0` | Faz 0 | [`ADR-011-crc.md`](ADR-011-crc.md) |
| ADR-012 | Paketleme aracı ve dağıtım biçimi | PLANLANDI | `F6-001` | `3.1.0` | Faz 6 | — |

## Her ADR'nin cevaplaması gereken soru

| ADR | Kararın özü | Hangi kanıta dayanmalı |
| --- | --- | --- |
| ADR-001 | GUI çatısı neden PySide6 (PyQt yerine)? | Lisans, Qt6 desteği, Windows paketleme, ekip deneyimi |
| ADR-002 | PyQtGraph nerede biter, kendi soyutlamamız nerede başlar? Matplotlib hangi işte kalır? | `F1-041`–`F1-043` spike'ının 1 M ve 10 M nokta ölçümleri |
| ADR-003 | Kanonik zaman birimi ve dönüşüm modeli | Çözünürlük/menzil analizi, `float64` ulp ölçümü — **yazıldı** |
| ADR-004 | Farklı format sürümleri nasıl algılanır, hangi decoder seçilir, bilinmeyen sürümde ne olur? | `magic` + `version` alanları; K-05 fixture davranışı |
| ADR-005 | İndeks dosyası nerede, hangi biçimde, nasıl geçersizleşir? | `docs/perf/budget.md` §4.1: indeks olmadan P-03 (5 s) karşılanamıyor |
| ADR-006 | Hangi iş thread'de, hangi iş ayrı süreçte; GIL nerede sorun? | `F1-043` darboğaz ölçümü; UI yanıt süresi hedefleri |
| ADR-007 | Hangi downsample algoritması; dar impuls nasıl korunur? | `F4-056` min/max envelope karşılaştırması; P-07 bütçesi |
| ADR-008 | Workspace dosyası hangi alanları taşır, sürüm değişince nasıl göç eder? | Şema sürümü ve geriye uyumluluk testleri |
| ADR-009 | Canlı veri yetişmezse ne düşer, kullanıcı bunu nasıl görür? | `F5-016` kuyruk sınırı, `F5-037` burst sonuçları |
| ADR-010 | Native modüle ne zaman geçilir? Eşik nedir? | `F4-067` profil sonuçları; ölçülmüş darboğaz olmadan geçilmez |
| ADR-011 | CRC algoritması, kapsamı, alan konumu ve sürümü | Referans vektörler — **yazıldı** |
| ADR-012 | PyInstaller mı Nuitka mı; imzalı mı imzasız mı? | `F6-001` spike kanıtı; D-16/D-17 cevapları |

## Erken cevap gerektirenler

Aşağıdaki ADR'ler tetikleyici işlerinden **önce** dış girdiye bağlıdır
(`docs/notes/open-decisions.md`):

| ADR | Bekleyen girdi | Neden erken gerekli |
| --- | --- | --- |
| ADR-004 | D-02, D-10 (format dokümanı, sürüm listesi) | Sürüm algılama kuralı, Faz 2'nin tüm decoder yapısını belirler |
| ADR-005 | D-03 (dosya boyutu) | İndeks boyutu ve saklama yeri buna bağlı |
| ADR-009 | D-12, D-13 (protokol, bant genişliği) | Kuyruk ve drop politikası protokolsüz tasarlanamaz |
| ADR-012 | D-16, D-17 (offline, code signing) | Sertifika tedarik süresi uzundur; Faz 6'da sorulursa geç kalınır |

## Not

Plan Bölüm 28 ADR-001–010'u sayar. Uygulama sırasında iki karar daha ADR'ye bağlandı:
**ADR-011** (CRC, `F0-008` çıktısı) ve **ADR-012** (paketleme, `F6-001` zaten ADR istiyordu ama
numarasızdı). Numaralar kalıcıdır; yeni ADR sıradaki numarayı alır ve bu tabloya eklenir.
