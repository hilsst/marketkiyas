# MarketKıyas

Türkiye'deki zincir marketlerin (BİM, A101, Şok, File) fiyatlarını karşılaştırıp alışveriş listesini en ucuz şekilde optimize eden uygulama.

## Yapı

- `backend/` FastAPI + PostgreSQL API (ayrıntılar: [backend/README.md](backend/README.md))
- `frontend/` Next.js 14 arayüzü; verileri API'den alır
- `docker-compose.yml` Postgres (pg_trgm) + API + fiyat toplayıcılar + arayüz
- `1-KUR.bat`, `BASLAT.bat`, `DURDUR.bat` Windows'ta Docker'sız kurulum ve çalıştırma

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

### Windows'ta Docker'sız

Yönetici izni ve yeniden başlatma gerekmez. Python 3.12 (kullanıcıya), taşınabilir PostgreSQL 16 ve
veriler `%LOCALAPPDATA%\MarketKiyas` altına kurulur; Node.js kurulu olmalıdır.

- `1-KUR.bat` bir kez: veritabanı, API bağımlılıkları, şema, demo verisi, arayüz paketleri
- `BASLAT.bat` API + fiyat güncelleyici (6 saatte bir) + arayüz, tarayıcıda http://localhost:3000 açılır
- `DURDUR.bat` hepsini kapatır; loglar `%LOCALAPPDATA%\MarketKiyas\*.log`
