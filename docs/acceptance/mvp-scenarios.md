# MVP kullanıcı kabul senaryoları ve kanıt haritası

> `F3-078` çıktısı. Plan **Bölüm 17.5**'in kullanıcı kabul sorularını operatör ve
> mühendis akışları olarak koşan otomatik senaryoları, **Bölüm 23** "Definition
> of Done" maddelerine bağlar. Kanıt = adı verilen testin CI'da geçmesi.
>
> Makine-okur eşleme `tests/acceptance/test_mvp_scenarios.py` içindeki `SCENARIOS`
> tablosudur; `test_every_17_5_scenario_has_a_linked_evidence_test` bu iki
> belgenin tutarlı kaldığını korur.

## Roller (plan Bölüm 4)

- **Operatör** — sistem sağlığını görür, aktif alarmdan ilgili zaman aralığına
  gider, TX başlangıç/bitişleriyle kanal davranışını birlikte inceler.
- **Test mühendisi** — kaydı açar, kanal gruplarını karşılaştırır, bölge seçip
  ölçüm alır ve sonucu dışa aktarır.

## Senaryolar

| # | §17.5 sorusu | Rol | Bağlı §23 DoD maddeleri | Kanıt testi |
| --- | --- | --- | --- | --- |
| 1 | Operatör bir BIT FAIL'den ilgili sinyal anına en fazla iki etkileşimle gidebiliyor mu? | Operatör | BIT/event satırından grafikte aynı zamana gidiliyor | `test_operator_reaches_signal_moment_in_two_interactions` |
| 2 | Test mühendisi iki kanalı aynı eksende karşılaştırabiliyor mu? | Mühendis | Kanalları grafiğe ekleyip kaldırabiliyor; birden fazla grafik ortak X zaman ekseninde senkronize | `test_engineer_compares_two_channels_on_one_axis` |
| 3 | Seçili zaman aralığının istatistiği (v1.0.0) anlaşılır mı? | Mühendis | Cursor ve region ölçümleri doğru | `test_selected_range_statistics_are_labelled_and_scoped` |
| 4 | Kullanıcı X/Y zoom modunu yanlış yorumlamadan kullanabiliyor mu? | Her ikisi | X, Y ve XY zoom davranışları tutarlı | `test_zoom_modes_are_unambiguous` |
| 5 | Kaydedilen workspace yeniden açıldığında aynı düzen ve işlemler geliyor mu? | Her ikisi | Workspace kaydet/aç işlevi temel düzeni koruyor | `test_workspace_reopens_with_same_layout_and_operations` |

### Kapsam dışı (bu iş)

- §17.5'in **FFT/spektrogram** kabul sorusu `v2.0.0` kapsamındadır; MVP'de bu
  işlevler açıklamalı pasif durumda kalır (`docs/ui/*` ve `ViewTabBar`
  `ENABLED_TABS`). Bu senaryonun kabulü Faz 4'te (`F4-*` FFT işleri) kaydedilir.

## Nasıl çalıştırılır

```
python -m pytest tests/acceptance/test_mvp_scenarios.py -v
```

Beş senaryo testi + kanıt-haritası tutarlılık testi geçmelidir. Bir senaryo
başarısız olursa ilgili §23 DoD maddesi **kanıtsızdır** ve MVP kapatılamaz;
başarısızlık ayrı bir düzeltme işine dönüşür (plan Bölüm 22 kuralı).
