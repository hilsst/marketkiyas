# Uçtan uca testler (Maestro)

Akışlar `maestro/` altında. Metin seçicilerle yazıldı; ekran metni değişirse akış da güncellenir.

| Akış | Ne sınar |
|---|---|
| `01-giris-cikis.yaml` | Yeni kurulum, karşılama ekranı, giriş, çıkış |
| `02-plan-liste-alisveris.yaml` | Plan kur → listeye aktar → planı uygula → alışverişi bitir (huni) |

**Henüz yazılmadı:** "misafir olarak plan → liste → alışveriş → kaydet" akışı (Faz Planı v2). Sunucu bugün plan
oluşturmak için hesap istiyor; misafir başlangıç ekranları gelince bu akış eklenir ve `subflows/login.yaml`
çıkarılır.

## Çalıştırma

```bash
# 1) Sunucu + demo veri (yemek planı için katalog gerekir)
docker compose up -d db backend
docker compose exec backend python -m app.cli seed-demo

# 2) Uygulama, Android emülatörde: APK için `eas build --profile preview --platform android`
#    ya da geliştirmede `npx expo run:android` (EXPO_PUBLIC_API_URL emülatörde http://10.0.2.2:8000/api)
adb install ucuzu.apk

# 3) Maestro (https://docs.maestro.dev)
maestro test mobile/e2e/maestro
```

CI: `.github/workflows/e2e.yml` aynısını Android emülatöründe çalıştırır (elle başlatılır, bkz. dosya başı).
