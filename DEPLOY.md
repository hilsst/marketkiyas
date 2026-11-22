# Üretim kurulumu (VPS)

Gereken: Ubuntu 24.04 VPS, bir alan adı (A kaydı VPS IP'sine), 80 ve 443 portları açık.

## İlk kurulum
```bash
curl -fsSL https://get.docker.com | sh
git clone https://github.com/hilsst/marketkiyas && cd marketkiyas
cp deploy/.env.prod.example .env
# .env: DOMAIN, POSTGRES_PASSWORD (openssl rand -hex 24), JWT_SECRET_KEY (openssl rand -hex 32) doldur
nano .env
docker compose -f docker-compose.prod.yml up -d --build
curl https://$DOMAIN/api/health     # {"status":"ok","database":"ok"}
```
Şema (alembic) `migrate` servisiyle her açılışta güncellenir; api bitmesini bekler. Üretimde `seed-demo` ÇALIŞTIRMA (demo@marketkiyas.app / demo1234 hesabı açar).

## Güncelleme
```bash
git pull && docker compose -f docker-compose.prod.yml up -d --build
```
Yeni migrasyon varsa önce elle yedek al: `docker compose -f docker-compose.prod.yml exec backup pg_dump -Fc -f /backups/elle-$(date +%F).dump`

## Servisler
`api` (uvicorn, healthcheck /api/health), `worker` (6 saatte bir fiyat), `aktuel` (12 saatte bir BİM/Şok), `weekly-menus` (30 dk'da bir, push için `EXPO_PUSH_ENABLED=true`), `purge-guests` (günde bir), `backup` (günde bir pg_dump, 14 gün, `./backups`), `caddy` (HTTPS). Veritabanı portu dışarı açık değildir.

## Yedekten dönme
```bash
./deploy/restore.sh backups/marketkiyas-YYYYMMDD-HHMMSS.dump
```
Yedekler aynı diskte durur: VPS kaybolursa yedek de gider. `./backups` klasörünü haftalık başka yere kopyala (ör. `scp`/rclone).

## Günlükler ve durum
`docker compose -f docker-compose.prod.yml ps` ve `logs -f api`. Günlükler servis başına 10 MB x 5 dosya ile sınırlıdır. Analitik raporu: `docker compose -f docker-compose.prod.yml exec api python -m app.cli analytics`.

## Yük kapısı (1.000 kullanıcı, yanıt < 300 ms)
Yalnız VPS'te ve test verisi için: bkz. `backend/loadtest/README.md`. Gerçek hesaplar açar; canlı kullanıcıya açmadan önce çalıştır.

## Bilinen eksikler
Merkezi izleme/Sentry yok; web (Next.js) arayüzü bu yığına dahil değil (ürün mobil uygulama); scraper (Playwright) yok, A101 kapalı.


## Instagram'da fotoğraf yayını (isteğe bağlı)

Yönetici, onayladığı ve yükleyenin Instagram paylaşımına izin verdiği fotoğrafı uygulamadaki
Profil -> "Fotoğraf onayı" -> "Onaylı" sekmesinden elle yayınlar. Otomatik yayın yoktur.

1. Instagram hesabı **Business/Creator** olmalı; Meta geliştirici uygulaması açılıp içerik yayınlama izni
   (`instagram_content_publish`; Instagram Login yolunda `instagram_business_content_publish`) alınmalı (App Review gerekebilir).
2. Uzun ömürlü erişim anahtarı (yaklaşık 60 gün geçerli, süre dolmadan yenilenmeli) ve Instagram hesap kimliğini `.env.prod` içine yazın:
   `INSTAGRAM_ENABLED=true`, `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_USER_ID`, `PUBLIC_BASE_URL=https://alan-adiniz`.
   Instagram Login kullanılıyorsa `INSTAGRAM_GRAPH_HOST=https://graph.instagram.com`.
3. Görsel, Meta'nın sunucusundan `PUBLIC_BASE_URL/api/recipe-photos/<id>/image` adresinden çekilir; adres internetten
   açık olmalı (giriş, yönlendirme, bot koruması olmamalı).
4. Yeniden başlatın; yönetici ekranının üstünde "Instagram bağlı: @hesap" görünmelidir.

Not: Meta istek biçimleri bu geliştirme ortamında resmi dokümandan doğrulanamadı; ilk gerçek yayında kontrol edin.
Instagram'da yayınlanmış bir gönderi API ile silinemez; yükleyen silme isterse profilden elle kaldırın.
