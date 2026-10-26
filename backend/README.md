# MarketKıyas Backend

FastAPI + PostgreSQL (pg_trgm) + SQLAlchemy 2 (async) + Alembic + JWT.

## Çalıştırma

```bash
docker compose up --build
# API:      http://localhost:8000
# Swagger:  http://localhost:8000/docs
```

API container açılırken `alembic upgrade head` çalıştırır; şema, `pg_trgm` extension'ı ve
4 market (BİM, A101, Şok, File) + temel kategoriler otomatik oluşur.

Docker'sız geliştirme:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
pytest   # marketkiyas_test veritabanını kullanır
```

## Şema

| Tablo | Amaç |
|---|---|
| `users` | Hesaplar (bcrypt şifre). localStorage'daki kullanıcı verisinin yerini alır. |
| `markets` | BİM, A101, Şok, File (slug, renk, logo). |
| `categories` | Ürün kategorileri (hiyerarşik, `parent_id`). Alışveriş Modu'nda sıralama için `sort_order`. |
| `products` | Bir marketteki tekil ürün. `(market_id, external_id)` tekil. `normalized_name` üzerinde **GIN trigram index**. Miktar normalize: `quantity` + `unit` (`ml` / `g` / `adet`, 1L → 1000 ml). |
| `price_history` | Fiyat değişimleri (sparkline grafikleri). `(product_id, recorded_at)` index. |
| `product_groups` | "Süt 1 L" gibi karşılaştırma grubu. Kullanıcı listeye **grubu** ekler. Trigram index. |
| `group_members` | Ürün ↔ grup. Bir ürün tek gruba girer; `match_score` (pg_trgm similarity), `is_manual`. |
| `shopping_lists` | `status` (active / shopping / completed), `applied_plan` (single_market / combination / opportunist). |
| `shopping_list_items` | `group_id`, `quantity`, `preferred_brand` (**NULL = Farketmez**, dolu = kilitli marka), plan sonrası `assigned_market_id` / `assigned_product_id` / `assigned_unit_price` (Alışveriş Modu'nda market bazlı gruplama), `is_checked` (gri + üstü çizili), `position` (sıra korunur). |
| `savings_records` | Tasarruf Kasası. "Alışverişi Bitir"de yazılır. `list_id` **ON DELETE SET NULL** + `list_name` snapshot: liste silinse de kasa kalır. Bir liste kasaya yalnızca bir kez eklenebilir (partial unique index). Haftalık/aylık(x4)/yıllık(x52) değerler `saved_amount`'tan hesaplanır. |

## Endpoint'ler (şimdilik)

- `GET  /api/health`
- `POST /api/auth/register` · `POST /api/auth/login` (JSON) · `GET /api/auth/me`
- `POST /api/auth/token` (Swagger "Authorize" için OAuth2 form)
- `GET  /api/markets` · `GET /api/categories`

## Sonraki adımlar

1. Endpoint'ler: `/api/products` (grup arama, pg_trgm), `/api/lists` CRUD, `/api/lists/{id}/optimize`
   (Tek Market / Kombinasyon / Fırsatçı), `/api/lists/{id}/apply`, `/api/lists/{id}/complete`, `/api/savings`.
2. Scraper'lar (Playwright + BS4, BİM için marketfiyati.org.tr) ve eşleştirme servisi.
3. Next.js'in `demo-data.ts` yerine API'ye bağlanması.
