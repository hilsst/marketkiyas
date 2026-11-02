# Uçtan uca testler (Maestro)

Akışlar `maestro/` altında. Metin seçicilerle yazıldı; ekran metni değişirse akış da güncellenir.

| Akış | Ne sınar |
|---|---|
| `01-giris-cikis.yaml` | Misafir başlangıç -> var olan hesaba giriş -> çıkış (çıkışta yeni misafir açılır) |
| `02-plan-liste-alisveris.yaml` | Misafir olarak plan kur -> listeye aktar -> planı uygula -> alışverişi bitir (hesap açma istenir) -> tamamla |
| `03-misafir-baslangic.yaml` | İlk açılış giriş istemez, misafir kartı, kapat-aç sonrası misafir korunur |
| `04-misafir-yemek-plani.yaml` | Karşılamadan yemek planı, plan kurma, "Planını kaydet" ile misafirden hesaba geçiş |

Uygulama ilk açılışta kendi misafir hesabını açar (`lib/auth.tsx`). Sunucu geç kalırsa misafir arka planda
yeniden denenir (en kötü ~2 dk), bu yüzden akışlar `subflows/wait-guest.yaml` ile Profil'de "Misafir" kartını
bekler. `subflows/upgrade.yaml` misafiri benzersiz bir e-postayla hesaba çevirir. Var olan demo hesabına
girmek gerekirse `subflows/login.yaml` (misafirken "Hesap aç" ekranındaki "Giriş yap" sekmesi).

## Çalıştırma

```bash
# 1) Sunucu + demo veri (yemek planı için katalog gerekir)
docker compose up -d db backend
docker compose exec backend python -m app.cli seed-demo

# 2) Uygulama, Android emülatörde: APK için `eas build --profile preview --platform android`
#    ya da geliştirmede `npx expo run:android` (EXPO_PUBLIC_API_URL emülatörde http://10.0.2.2:8000/api)
adb install app-release.apk

# 3) Maestro (https://docs.maestro.dev)
maestro test mobile/e2e/maestro
```

CI: `.github/workflows/e2e.yml` aynısını Android emülatöründe çalıştırır (elle başlatılır, bkz. dosya başı).
