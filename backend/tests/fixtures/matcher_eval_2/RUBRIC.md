# Etiketleme ölçütü (eşleştirici çalıştırılmadan ÖNCE yazıldı ve donduruldu)

`ok = true`  : Ürün, tarifte bu malzemenin yerine olduğu gibi (ek bir dönüşüm olmadan) alınabilir. Marka, ambalaj
               boyutu, yağ oranı gibi ayrıntılar önemsizdir (ör. "Pınar Süt 1 L" süt için ok).
`ok = false` : Başka bir ürün ya da malzemeyi yalnızca aroma/dolgu olarak taşıyan ürün (limonlu kek, domatesli cips,
               sebzeli hazır yemek), işlenmiş/hazır hali (konserve, salça, tursu, dondurulmuş hazır, dolma), temizlik/bakım
               ürünü, ya da malzemenin başka biçimi (un için irmik, toz şeker için pudra şeker/küp şeker).
`ok = null`  : Gerçekten belirsiz (ör. "laktozsuz süt" tarif için uygun mu belirsiz). Puanlamaya girmez.
Etiketler yalnızca ürün adına, malzemenin gündelik anlamına ve (gerekirse) ambalaj bilgisine bakılarak verildi;
eşleştirici çıktısı, `elenecek kelimeler` listesi ve OTHER_PRODUCT_WORDS etiketlerken bilinçli olarak dikkate alınmadı.
Elenecek kelimeler listesi yalnızca ölçülen sistemin parçasıdır.
