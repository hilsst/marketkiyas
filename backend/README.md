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
| `GET /api/stores/nearby?lat=&lon=&distance=5` | Çevredeki market şubeleri (marketfiyati.org.tr), `selected` bayrağıyla |
| `GET/PUT /api/me/stores` `{"store_ids": [..]}` | "Çevremdeki marketler" seçimi. Yeni şubelerin fiyatları arka planda çekilir |

### Optimizasyon kuralları

- **Kombinasyon:** Marka tercihlerine uyarak her kalem en ucuz marketten. Bu tutar "kendi tercihlerinle ödeyeceğin" referanstır.
- **Fırsatçı:** Marka tercihleri yok sayılır, her kalemin piyasadaki en ucuzu.
- **Tek Market:** Tercihlere uyarak market toplamları; sadece eksiksiz (missing=0) marketler arasından en ucuzu. Hiçbiri yoksa `warning: "Hiçbir market tüm ürünleri eksiksiz bulundurmuyor"` ve uygulama 409 döner.
- **Tasarruf:** Kombinasyon toplamı − Fırsatçı toplamı (tercih edilen markanın hiç bulunmadığı kalemler hariç). Aylık = x4, yıllık = x52.
- Plan uygulandıktan sonra kalem eklenir/silinir ya da miktar/marka değişirse plan sıfırlanır (alındı işaretleri korunur); liste yeniden uygulanmalıdır. Böylece kasaya eski hesap yazılmaz.

## Fiyat verisi: marketfiyati.org.tr

Tüm fiyatlar [marketfiyati.org.tr](https://www.marketfiyati.org.tr)'den gelir (`app/services/marketfiyati/`).
Kaynak JSON API sunduğu için tarayıcı otomasyonuna (Playwright) gerek yoktur.

- **İstemci:** istekler arası en az 1 sn, 429/5xx/ağ hatalarında üstel bekleme ile 4 tekrar (Retry-After'a uyar). Kendini `MarketKiyas/0.1` olarak tanıtır; tarayıcı taklidi yapmaz.
- **Aktarım:** zincir (`markets`, bilinmeyen zincirler otomatik eklenir) → şube (`stores`) → ürün (zincir başına bir satır) → şube fiyatı (`store_prices`) → ürünün en düşük fiyatı değiştiyse `price_history`.
- **Eşleştirme:** başlıktan marka atılır, miktar temel birime çevrilir ("Pınar Süt 1 L" → `sut 1000ml`). Aynı miktar/birimdeki gruplarla pg_trgm benzerliği ≥ 0.7 ise o gruba, değilse yeni gruba girer.
- **Kullanıcı şubeleri:** şube seçen kullanıcıya arama, optimizasyon ve plan yalnızca o şubelerin son 7 gündeki fiyatlarıyla çalışır; plan kalemlere şubeyi de atar. Şube seçmeyen kullanıcı zincirin en düşük fiyatını görür.

```bash
python -m app.cli nearby --lat 40.99 --lon 29.03             # çevredeki şubeleri kaydet
python -m app.cli sync --lat 40.99 --lon 29.03 --keywords süt ekmek
python -m app.cli sync-selected --every-hours 6              # docker-compose'daki worker bunu çalıştırır
```

## Fiyat verisi: market siteleri (yedek kaynak)

marketfiyati.org.tr'ye erişilemediğinde fiyatlar zincirlerin kendi sitelerinden toplanır (`app/services/scrapers/`).

- **Kurallar:** robots.txt'ye uyulur, sadece sitemap'teki ürün sayfaları gezilir, sayfalar arası en az 3 sn beklenir, istemci kendini `MarketKiyas/0.1` olarak tanıtır.
- **Şok:** fiyat HTML'de; BeautifulSoup ile okunur (2026-10-26 canlı sitede doğrulandı).
- **A101 (Kapıda):** düz HTTP isteklerine (sitemap dahil) 403 döner, bu yüzden robots.txt dışında her şey Playwright (başsız Chromium, yine `MarketKiyas` kimliğiyle) ile açılır. Fiyat JavaScript ile yüklenir. Sayfadaki JSON-LD fiyatı güncel değil (ör. 2 kg bütün piliç 32,90), kullanılmaz; fiyat görünen fiyat kutusundan okunur, kutu boşsa ürün atlanır. Site zaman zaman "Just a moment..." bot kontrolü gösterir; bu aşılmaya çalışılmaz, sayfa atlanır.
- **Okuma sırası:** önce schema.org JSON-LD (`Product.offers.price`, A101 hariç), yoksa `h1` başlık, "Marka" etiketi ve başlığa en yakın fiyat kutusu (sınıfında `price`/`fiyat` geçen öğeler; "benzer ürünler" kartlarına kayılmaz, indirimde düşük fiyat alınır).
- Site üst üste 5 sayfayı reddederse tarama durur.
- **BİM:** sitede ürün kataloğu yok (sadece haftalık Aktüel). **File:** sitede fiyat yok, online satış sadece mobil uygulamada.
- Zincir siteleri şube değil zincir geneli fiyat verir: fiyatlar zincirin konumsuz "online fiyat" şubesine yazılır, kullanıcı bunu da seçebilir.

```bash
python -m app.cli scrape --market sok --limit 100
python -m app.cli scrape --market a101 --limit 100   # requirements-scraper.txt (Playwright) gerekir
# Hazır kurulu bir Chromium kullanmak için: CHROMIUM_EXECUTABLE_PATH=/yol/chrome
```

docker-compose'daki `scraper` servisi (`Dockerfile.scraper`) 12 saatte bir iki zinciri tarar.

## Sonraki adımlar

1. Next.js'in `demo-data.ts` yerine API'ye bağlanması.
