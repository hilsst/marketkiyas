# Ucuzu telefon uygulaması (React Native + Expo)

Mağaza adı: **Ucuzu** (Kemal, 28 Ekim 2026; marka tescili kontrolü bekliyor). Depo ve sunucu hâlâ MarketKıyas adını taşır.

Sunucu: `backend/` (FastAPI). Uygulama sunucuya `EXPO_PUBLIC_API_URL` ile bağlanır; geliştirmede aynı Wi-Fi'deki
bilgisayarın web arayüzü vekili kullanılır (`BASLAT.bat` çalışırken `http://<bilgisayar-ip>:3000/api`).

```bash
cd mobile
npm install
npx expo start          # telefonda Expo Go ile QR kodu okutun
npx tsc --noEmit        # tip denetimi
npx expo lint
```

Yapı: `app/` ekranlar (Expo Router; `(tabs)/` alt menü, `login.tsx`), `lib/` API istemcisi ve oturum,
`components/ui.tsx` ortak bileşenler. Plan: Faz 1 adımları ve testler plan belgesinde.
