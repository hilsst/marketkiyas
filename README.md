# MarketKıyas

Türkiye'deki zincir marketlerin (BİM, A101, Şok, File) fiyatlarını karşılaştırıp alışveriş listesini en ucuz şekilde optimize eden uygulama.

## Yapı

- `backend/` FastAPI + PostgreSQL API (ayrıntılar: [backend/README.md](backend/README.md))
- `frontend/` Next.js 14 arayüzü; verileri API'den alır
- `docker-compose.yml` Postgres (pg_trgm) + API + fiyat toplayıcılar + arayüz

```bash
docker compose up --build                            # arayüz: http://localhost:3000, API: http://localhost:8000/docs
docker compose exec api python -m app.cli seed-demo  # isteğe bağlı: demodaki örnek ürünler ve listeler
```

`seed-demo` demodaki örnek kataloğu ve iki listeyi yükler; giriş: `demo@marketkiyas.app` / `demo1234`.
Bu fiyatlar gerçek değildir, yalnızca denemek içindir.

Arayüzü Docker olmadan çalıştırmak için:

```bash
cd frontend
cp .env.example .env.local   # NEXT_PUBLIC_API_URL
npm ci && npm run dev
```
