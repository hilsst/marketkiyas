# Eşleştirici bağımsız değerlendirme kümesi (BİM / A101 gerçek ürün adları)

**Amaç:** `app/services/ingredient_match.py` için, eşleştirici bu kümeye bakılarak ayarlanmadan alınmış dürüst bir
doğruluk ölçümü. Eski 202'lik küme (`../ingredient_match_set.json`, %97,5) eşleştirici ona bakılarak ayarlandığı
için bir "ayar kümesi"dir; bu küme onun yerine genelleme ölçümüdür.

## Veri
- Kaynak: marketfiyati.org.tr `/api/v2/search` ham yanıtları (Kemal'in PC'sinden, 2026-11-02, Ankara şubeleri, 60 sorgu
  × 2 sayfa × 25). Hiçbir ürün adı uydurulmadı; ham dosyalar repoda değil, `raw_manifest.json` her birinin SHA-256'sını tutar (izlenebilirlik), `products.json` ve `labels.json` testte SHA ile sabitlenir. BİM için 472, A101 için 562 (ürün, sorgu) çifti çıktı; bunlardan 639 benzersiz ürün aday oldu.
- `products.json`: aday ürünler (`id`, `title`, `stores`, `menu_category`, `main_category`, `quantity`).
- `labels.json`: 52 malzeme (arama ifadeleri/elenecek kelimeler `alembic/recipe_data/vocab.py`'den aynen). Malzeme başına
  mağaza başına 8 hash-örneklenmiş sonuç + 2 başka sorgudan "kolay negatif". 811 aday satırı: 312 uygun, 450 uygun değil,
  49 belirsiz (`ok: null`, puanlamaya girmez). `maydanoz` için BİM/A101 sonucu çıkmadı, atlandı.
- Etiket ölçütü: `RUBRIC.md`. Etiketler eşleştirici çıktısına bakılmadan, **çalıştırılmadan önce** verildi ve commit'lendi
  (`labels.json` SHA-256 `3201c130…`, `tests/test_matcher_eval.py` sabitler). Etiketleri tek kişi (Claude) verdi; Kemal'in
  ~%10 örnek kontrolü yapılmadı — bu bir sınırlama.
- Bölme: arama ifadesinin hash'ine göre `dev` 36 / `holdout` 16 malzeme. Holdout ayar sırasında hiç çalıştırılmadı;
  ayar yapılmadan, her mod için bir kez ölçüldü (ad modu, kategori modu ve `--split all` satırı; arada hiçbir değişiklik yok). Hata listelerine (`--errors`) holdout ölçümünden SONRA bakıldı. Dev üzerinde hatalara bakıldı.

## Sonuçlar (eşleştirici commit `e346399`, değişiklik yapılmadı)
Malzeme doğruluğu = eski testle aynı tanım (yanlış kabul yok ve uygun ürün varsa ≥1'i kabul edildi). %95 Wilson aralığı.

| Bölüm | Mağaza | Malzeme | Doğruluk | Kesinlik | Duyarlılık |
|---|---|---|---|---|---|
| dev | BİM | 36 | %83,3 (68–92) | %93,0 | %99,1 |
| dev | A101 | 36 | %86,1 (71–94) | %95,0 | %94,2 |
| dev | birleşik | 36 | %83,3 (68–92) | %93,7 | %96,3 |
| **holdout** | BİM | 16 | %87,5 (64–97) | %98,0 | %92,5 |
| **holdout** | A101 | 16 | %68,8 (44–86) | %93,0 | %81,6 |
| **holdout** | birleşik | 16 | **%75,0 (51–90)** | %95,5 | %87,6 |
| tümü | BİM | 52 | %84,6 (72–92) | %94,5 | %96,9 |
| tümü | A101 | 52 | %80,8 (68–89) | %94,5 | %90,6 |
| tümü | birleşik | 52 | **%80,8 (68–89)** | %94,2 | %93,6 |

Okuma: bağımsız doğruluk ~%81 (güven aralığı geniş: ±~10 puan), eski "ayar kümesi" %97,5'inden belirgin düşük,
eski kümenin ayarlanmamış kısmı için kaydedilen ~%85 (o testin açıklamasındaki not, burada yeniden doğrulanmadı) ile aynı düzeyde. Mağaza farkı (BİM %85 vs A101 %81) istatistiksel olarak ayırt edilemez.
Kategori modu (temizlik/kişisel bakım menü kategorisi + `grocery_like(category_known=True)`) bu kümede ad modundan
**farksız** çıktı: hataların hiçbiri temizlik ürünü değil. Not: kategori modu üretimdeki `meals._groups_for`'un yaklaşığıdır
(malzemenin kendi kategori listesi marketfiyati kategorilerine eşlenemediği için uygulanmadı). Not: bir mağazada hiç uygun ürünü olmayan malzemeler (ör. BİM dev'de 7, tüm holdout'ta `ispanak`) yalnızca yanlış kabulle başarısız olabilir; bu tanım eski testle aynıdır ama mağaza bazlı doğruluğu şişirir. Kapsam: aday havuzu API'nin
kendi arama sonuçlarıdır; arama dışında kalan ürünler için duyarlılık ölçülmedi.

## Ana hata kategorileri (52 malzeme; yanlış kabul = FA, uygun ürünü reddetme = FN)
| Kategori | Örnekler | Ürün | Kaynak |
|---|---|---|---|
| Hazır/işlenmiş/farklı ürün yanlış kabul | Pestolu Krema, Acılı Bonfile, Izgara Fileto, Wasa Gevrek Ekmek, Kinder/Haribo "Yumurta", Döner Kıyma | 9 FA | dev+holdout |
| Aroma/tür sıfatı engellenmiyor | Limonlu/Mango Maden Suyu, Cin Mısır (patlatmalık) | 6 FA | dev |
| Marka iddiası | "Becel Tereyağı Keyfi Margarin", "Sana Tereyağı Lezzeti Margarin" | 2 FA | holdout |
| Eş anlamlı eksik (elenecek kelime) | "Köz Patlıcan" (`kozlenmis` var, `köz` yok) | 1 FA | holdout |
| Aşırı geniş engel sözcüğü | `tabak` (ambalaj: "Mantar Tabak", "Bakpiliç Bonfile Tabak") | 3 FN | dev |
| Aşırı geniş engel sözcüğü | `konserve` ton balığı konservesini reddediyor (tüm konserve ton) | 3 FN | holdout |
| Arama ifadesi çok dar | "kuru sogan" -> "Soğan 1 Kg" ve "Mor Soğan 1 Kg" reddediliyor | 3 FN | holdout |

## Önerilen düzeltmeler (UYGULANMADI)
1. `OTHER_PRODUCT_WORDS`'ten `tabak` çıkar. Dev üzerinde denendi: A101 ürün-düzeyi duyarlılık %94,2→%96,7, malzeme
   doğruluğu %86,1→%88,9; eski 202'lik küme %97,5'te değişmedi. Kanıt: 3 ürün / 2 malzeme (zayıf-orta).
2. `konserve` engelini, arama ifadesi doğası gereği konserve olan malzemelerde ("ton baligi", `misir konservesi`) kaldır
   veya malzemeye göre izin ver. Kanıt holdout'tan (3 ürün, tek malzeme).
3. `sogan` için arama ifadesine `sogan` ekle (vocab verisi göç olduğu için yeni göç gerekir).
4. Ürün adında `margarin` varsa, arama ifadesi `margarin` içermiyorsa reddet.
5. Aroma sıfatları (`limonlu`, `mango`…) ve `cin` için engel: kanıt tek malzemede 3 ürün; şimdilik gözlem.

**Uyarı:** 2–4 numaralı öneriler holdout hatalarına (ölçümden sonra açılan `--errors` çıktısına) bakılarak çıkarıldı; yukarıdaki hata kategorisi tablosu da holdout vakalarını içerir. Bunlardan herhangi biri uygulanırsa holdout
artık bağımsız bir ölçüm olmaktan çıkar; yeni sayı için yeni aday havuzu (başka malzemeler/başka sorgular) gerekir.
Kümenin yalnızca 36+16 malzemesi var; tek bir malzemeye dayanan düzeltmelere güvenilmemeli.

## Çalıştırma
`python scripts/eval_matcher.py --split dev --errors` (holdout için yalnızca son ölçümde `--split holdout`);
`pytest tests/test_matcher_eval.py` bütünlük + gevşek gerileme tabanı (hedef yok).
Kaynak ham JSON'u yeniden üretmek için: `scripts/build_matcher_eval_candidates.py <raw_dir>` (ham dosyalar repoda değil).
