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

## Endpoint'ler

| Endpoint | Açıklama |
|---|---|
| `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` | JWT auth (`/api/auth/token` Swagger için) |
| `GET /api/markets`, `GET /api/categories`, `GET /api/health` | |
| `GET /api/products?q=süt&category_id=` | Ürün grubu araması (pg_trgm). Market bazında en ucuz fiyat + kilitlenebilir markalar |
| `GET /api/products/{group_id}` | Gruptaki ürünler ve son 30 fiyat noktası (sparkline) |
| `GET/POST /api/lists`, `GET/PATCH/DELETE /api/lists/{id}` | Liste CRUD. Silmek kasayı etkilemez |
| `POST /api/lists/{id}/items` | Kalem ekle (`preferred_brand: null` = Farketmez) |
| `PATCH /api/lists/{id}/items/{item_id}` | Marka kilitle/aç, miktar, `is_checked` (alındı), `position` |
| `DELETE /api/lists/{id}/items/{item_id}` | |
| `GET /api/lists/{id}/optimize` | Tek Market (eksik ürün uyarısıyla), Kombinasyon, Fırsatçı + haftalık/aylık/yıllık tasarruf |
| `POST /api/lists/{id}/apply` `{"plan_type": "opportunist"}` | Listeye Uygula: kalemlere market atanır, `shopping_groups` döner |
| `POST /api/lists/{id}/complete` | Alışverişi Bitir: Fırsatçı tasarrufu kasaya eklenir |
| `GET /api/savings` | Tasarruf Kasası (toplam + kayıtlar) |

### Optimizasyon kuralları

- **Kombinasyon:** Marka tercihlerine uyarak her kalem en ucuz marketten. Bu tutar "kendi tercihlerinle ödeyeceğin" referanstır.
- **Fırsatçı:** Marka tercihleri yok sayılır, her kalemin piyasadaki en ucuzu.
- **Tek Market:** Tercihlere uyarak market toplamları; sadece eksiksiz (missing=0) marketler arasından en ucuzu. Hiçbiri yoksa `warning: "Hiçbir market tüm ürünleri eksiksiz bulundurmuyor"` ve uygulama 409 döner.
- **Tasarruf:** Kombinasyon toplamı − Fırsatçı toplamı (tercih edilen markanın hiç bulunmadığı kalemler hariç). Aylık = x4, yıllık = x52.
- Plan uygulandıktan sonra kalem eklenir/silinir ya da miktar/marka değişirse plan sıfırlanır (alındı işaretleri korunur); liste yeniden uygulanmalıdır. Böylece kasaya eski hesap yazılmaz.

## Sonraki adımlar

1. Scraper'lar (Playwright + BS4, BİM için marketfiyati.org.tr) ve eşleştirme servisi.
2. Next.js'in `demo-data.ts` yerine API'ye bağlanması.
