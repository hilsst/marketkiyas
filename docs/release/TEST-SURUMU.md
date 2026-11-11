# Ucuzu Android test sürümü (Google Play kapalı test)

## Kemal'in yapacakları (sırayla)
1. VPS al, alan adı bağla, `DEPLOY.md` ile sunucuyu kur. Telefon bu adrese bağlanacak; kurulmadan uygulama çalışmaz.
2. Expo hesabı aç (expo.dev), `cd mobile && npx eas-cli login && npx eas-cli init` (projectId app.json'a yazılır, commit et).
3. `mobile/eas.json` içindeki `API_ALAN_ADI` yerine gerçek alan adını yaz (örn. `api.ornek.com`).
4. Önce APK: `npx eas-cli build -p android --profile preview`. Telefona kur; misafir girişi, haftalık bildirim ve ana akışı dene.
5. Google Play Console hesabı aç (25 $, kimlik doğrulama).
6. AAB: `npx eas-cli build -p android --profile production`. Play Console > Kapalı test > yeni sürüm, AAB'yi yükle (ilk yükleme elle yapılır; imzalamayı "Play App Signing" kabul et).
7. Store sayfası ve Data Safety formunu `STORE-LISTING.md` metinleriyle doldur. Gizlilik politikası adresi gerekir (`GIZLILIK.md` yayınlanmalı).
8. 12 testçinin Gmail adresini testçi listesine ekle, 14 gün bekle.

## Claude'un yaptığı
- eas.json (development / preview APK / production AAB), versionCode, gereksiz izinler kapalı.
- Metinler: `GIZLILIK.md`, `STORE-LISTING.md`.

## Bilinen açıklar
- Reklam test modunda (`EXPO_PUBLIC_ADS=test`). Gerçek AppLovin MAX birimleri bağlanmadı.
- Hesap silme uygulamadan var (`DELETE /auth/me`); Play ayrıca web adresi ister, sayfa yok.
- Gerçek telefon doğrulaması (misafir, bildirim) yapılmadı.
