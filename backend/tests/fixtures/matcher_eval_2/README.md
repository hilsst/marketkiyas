# Taze holdout (ikinci küme) ve uygulanan eşleştirici düzeltmeleri

İlk küme (`../matcher_eval/`) PR #38'de ölçüldü; orada holdout hatalarına bakılarak düzeltme önerileri çıkarıldığı için
o holdout artık bağımsız değildir. Bu küme, düzeltmelerden **sonra** bağımsız bir ölçüm için çekildi.

## Veri
- 60 YENİ sorgu (ilk kümede hiç kullanılmamış: biber salçası, kimyon, tahin, zeytin, ayran, yufka, noodle, elma, ...),
  Kemal'in PC'sinden, 2026-11-02, aynı salt okuma yöntemi (Ankara BİM/A101/Şok/Migros şubeleri, 2 sayfa × 25). Uydurma ad yok;
  `raw_manifest.json` ham dosyaların SHA-256'sını tutar.
- 52 malzeme (vocab.py'den aynen; BİM/A101 sonucu çıkmayan `zerdecal`, `parmesan`, `brokoli`, `karnabahar`, `soyasosu` atlandı),
  525 aday satırı: 164 uygun, 345 uygun değil, 16 belirsiz (`ok: null`). Etiketler `RUBRIC.md` ölçütüyle, eşleştirici çalıştırılmadan
  verilip commit'lendi (`labels.json` SHA-256 `9d40c772…`; testte sabit). Etiketleri tek kişi (Claude) verdi.
- Tüm kayıtlar `holdout`. `python scripts/eval_matcher.py --set 2 --split holdout`.

## Uygulanan düzeltmeler (`app/services/ingredient_match.py`, yalnızca `OTHER_PRODUCT_WORDS`)
README önerileri 1, 2 ve 4 (hepsi kümeler 1'e bakılarak, bu küme çekilmeden önce önerilmişti):
1. `tabak` kaldırıldı (ambalaj: "Mantar Tabak", "Tavuk Bonfile Tabak"). `tabagi` (gereç) listede kaldı.
2. `konserve` kaldırıldı (konserve ton balığı tamamen reddediliyordu). **README önerisinden daha geniş**: öneri, ifadeye göre izin vermekti;
   burada kelime tümden kalktı. `bezelye, domates, kapya, dolmabiber, patlican, mantar, ispanak, tazefasulye, bamya, nohut, kurufasulye,
   somon, hamsi` kendi `elenecek` listelerinde `konserve` taşıdığı için korunur. Artık konserve ürün kabul edebilecekler (kümelerimizde
   görülmedi, açık risk): `barbunya`, `havuc`, `pancar`, `sivribiber`, `kabak`, mercimekler, `zeytin`. Gerekirse bu malzemelerin `exclude`
   listesine `konserve` eklenmeli (vocab göçü gerekir).
3. `margarin` eklendi ("Becel Tereyağı Keyfi Margarin" tereyağı sayılmasın; arama ifadesinde `margarin` geçerse muaf).
Uygulanmayanlar: `sogan` arama ifadesi (vocab göçü + eski küme güncellemesi gerekir), aroma sıfatları ve `cin` (tek malzemede kanıt).

## Önce / sonra (malzeme doğruluğu; kesinlik; duyarlılık)
| Küme | Önce | Sonra |
|---|---|---|
| Eski 202'lik ayar kümesi | %97,5 | %97,5 |
| Küme 1 dev (36) birleşik | %83,3 · %93,7 · %96,3 | %83,3 · %93,8 · %97,7 (A101 doğruluk %86,1→%88,9) |
| Küme 1 holdout (16; **kirli**: düzeltmeler buna bakılarak seçildi) | %75,0 · %95,5 · %87,6 | %81,2 · %97,8 · %90,7 |
| **Taze küme 2 (52)** birleşik | **%88,5** (GA 77–95) · %95,9 · %86,6 | **%88,5** · %95,9 · %86,6 (değişmedi) |
| Taze küme 2 BİM / A101 | %94,2 / %88,5 | %94,2 / %88,5 (değişmedi) |

**Önemli:** Taze kümede "sonra" sayısı değişmedi, çünkü bu kümenin 345 ürün adından hiçbiri `konserve`, `margarin` ya da `tabak` içermiyor;
üç düzeltme saf kelime kontrolü. Bu, "düzeltmeler taze veride gerileme yapmadı" demektir, "taze veride iyileştirdi" demek değildir.
İyileşmeler (A101 dev, eski holdout) kirli/ayar verisindendir ve taze veriyle doğrulanmış değildir.
Taze küme ayrıca, düzeltmelerin kapsamadığı ve açık kalan hata sınıflarını gösterdi (bkz. aşağı); bunların hiçbiri düzeltilmedi.

## Taze kümede görülen, DÜZELTİLMEMİŞ hatalar (açık)
- A101'de `noodle`: 9 uygun ürün ("Indomie Special Paket Noodle 75 Gr", "Nissin Yakisoba … Noodle") hep reddediliyor (nedeni bu PR'da araştırılmadı).
- Aroma/varyant sıfatı: "Naneli Ayran", "Açai Ananas Yeşil Çay", "Mango & Lime Yeşil Çay", "Meyveli Yoğurt" (çilek), "Meyveli Taze Peynir" (muz), "Magnum Badem Dondurma".
- Birkaç ürünün çekim biçimi: "Nar Ekşisi Cam Sürahi", "Bahçıvan Rende Mozzarella", "Karabiber 75 Gr", "Bardak Ayran" reddediliyor.

**Dürüstlük notu:** Düzeltmeleri uygulamadan önce taze kümenin "önce" `--errors` çıktısına baktım. Düzeltmeler bu kümeden ÖNCE yazılmış README önerilerinden
seçildi; aroma sıfatı düzeltmesi, taze kümede benzer hatalar görünmesine rağmen uygulanmadı; taze kümede görülen hiçbir hata için kural yazılmadı.
Yine de bu hatalar artık görüldüğü için **bu küme sonraki ayar turları için bağımsız değildir**; bir sonraki tur için yeni bir üçüncü küme gerekir.
