# MarketKıyas

Türkiye'deki zincir marketlerin (BİM, A101, Şok, File) fiyatlarını karşılaştırıp alışveriş listesini en ucuz şekilde optimize eden uygulama.

## Yapı

- `backend/` FastAPI + PostgreSQL API (ayrıntılar: [backend/README.md](backend/README.md))
- `docker-compose.yml` Postgres (pg_trgm) + API

```bash
docker compose up --build   # http://localhost:8000/docs
```
