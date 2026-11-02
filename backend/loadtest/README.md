# Yük testi (Locust)

Faz 1 kapısı: **1.000 eşzamanlı kullanıcıda okuma uçlarının 95. yüzdeliği < 300 ms**, hata oranı ≤ %1.
Kapıya giren uçlar `locustfile.py` içindeki `READ_NAMES`; yazma uçları (kayıt, plan kurma) raporlanır, kapıya girmez.

```bash
pip install -r requirements-load.txt
python -m app.cli seed-demo && python -m loadtest.seed_catalog   # 84 tarifin hepsi planlanabilir olsun
uvicorn app.main:app --workers 4 &
locust -f loadtest/locustfile.py --headless -u 1000 -r 25 -t 3m --host http://localhost:8000
```

Kapı geçmezse çıkış kodu 1 olur ve hangi uç kaç ms olduğu yazılır. Eşikler `P95_LIMIT_MS`, `MAX_FAIL_RATIO`
ortam değişkenleriyle değişir. CI: `.github/workflows/load.yml` (elle, `target_url` ile gerçek sunucuya karşı da).

## Ölçümler (2 Kasım 2026, 4 çekirdekli geliştirme kutusu: sunucu 4 işçi + PostgreSQL + Locust aynı makinede)

| Kullanıcı | Sonuç |
|---|---|
| 50 | Okuma uçları p95 5–20 ms; **`GET /meal-plans/{id}` p95 440 ms** (kapı kalır) |
| 200 | CPU doymuş: okuma p95 2–4 sn, hata yok |
| 1.000 | CPU doymuş: p95 10–30 sn, %17 hata |

Bu kutuda 1.000 kullanıcı sonucu **sunucuyu değil makineyi ölçer** (yük üreticisi ve veritabanı aynı 4 çekirdeği
yer). Kapı ölçümü ayrı bir yük üreticisinden, canlıya yakın bir sunucuya karşı yapılmalı (Faz 2a VPS'i).

Bulgular:

1. **bcrypt olay döngüsünü tıkıyordu** (düzeltildi): `/auth/register` ve `/auth/login` şifreyi eşzamanlı
   hesaplıyordu; kayıt dalgasında diğer bütün istekler saniyelerce bekliyordu (50 kullanıcıda `/markets` p95 1,2 sn).
   Artık iş parçacığı havuzunda çalışıyor (`hash_password_async`).
2. **`GET /meal-plans/{id}` yavaş** (açık): plan her açılışta güncel fiyatlarla yeniden maliyetlendiriliyor;
   50 kullanıcıda bile 440 ms. Çözüm yemek planı kodunda (önbellek ya da maliyeti toplu sorgu), bu işin dışında.
3. Plan oluşturma ve listeye aktarma (`POST /meal-plans`, `/to-list`) 50 kullanıcıda p95 ~0,5 sn; kapı dışı ama
   haftalık ana akış olduğu için izlenmeli.
