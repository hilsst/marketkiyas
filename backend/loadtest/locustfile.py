"""Yük testi (Faz 1 kapısı): 1.000 eşzamanlı kullanıcıda yanıt < 300 ms.

Çalıştırma (sunucu ve `python -m app.cli seed-demo` hazır olmalı):

    locust -f loadtest/locustfile.py --headless -u 1000 -r 50 -t 3m --host http://localhost:8000

Çıkış kodu: sunucu hatası oranı > %1 ya da bir okuma ucunun 95. yüzdeliği > P95_LIMIT_MS ise 1.
Yazma uçları (plan kurma, liste, kayıt) ayrı raporlanır ama kapıya girmez: plan üretmek hesaplı bir iştir.

Her sanal kullanıcı bir uygulama oturumu gibi davranır: kayıt olur (bcrypt, bilerek gerçek maliyetle),
ana sayfayı yükler, arar, tarif listeler, plan kurar, listeye aktarır, planı uygular, alışverişi bitirir.
"""
import os
import random
import uuid

from locust import HttpUser, between, events, task

P95_LIMIT_MS = float(os.getenv("P95_LIMIT_MS", "300"))
MAX_FAIL_RATIO = float(os.getenv("MAX_FAIL_RATIO", "0.01"))
SEARCHES = ["süt", "yumurta", "makarna", "zeytinyağı", "domates", "peynir", "ekmek", "pirinç"]
# Kapıya giren okuma uçları: ad -> yol şablonu (locust'ta `name=` ile gruplanır)
READ_NAMES = {
    "GET /markets", "GET /categories", "GET /products?q=", "GET /products/{id}", "GET /recipes",
    "GET /cuisines", "GET /meal-plans/{id}", "GET /lists", "GET /savings", "GET /lists/{id}/optimize",
}


class AppUser(HttpUser):
    wait_time = between(1, 4)

    def on_start(self) -> None:
        self.device = str(uuid.uuid4())
        self.h = {"X-Device-Id": self.device}
        self.group_ids: list[int] = []
        self.plan_id: int | None = None
        self.list_id: int | None = None
        email = f"yuk-{uuid.uuid4().hex[:12]}@example.com"
        with self.client.post(
            "/api/auth/register", name="POST /auth/register", headers=self.h,
            json={"email": email, "password": "yuk-testi-123"}, catch_response=True,
        ) as r:
            if r.status_code != 201:
                r.failure(f"kayıt {r.status_code}")
                return
            self.h["Authorization"] = f"Bearer {r.json()['access_token']}"
        self.client.get("/api/markets", name="GET /markets", headers=self.h)
        self.client.get("/api/categories", name="GET /categories", headers=self.h)
        self.client.post("/api/events", name="POST /events", headers=self.h, json={"events": [{"name": "app_open"}]})

    @task(6)
    def browse_and_search(self) -> None:
        q = random.choice(SEARCHES)
        r = self.client.get("/api/products", params={"q": q, "limit": 20}, name="GET /products?q=", headers=self.h)
        if r.ok and r.json():
            self.group_ids = [g["id"] for g in r.json()]
            if random.random() < 0.4:
                self.client.get(f"/api/products/{random.choice(self.group_ids)}", name="GET /products/{id}", headers=self.h)

    @task(4)
    def recipes(self) -> None:
        self.client.get("/api/cuisines", name="GET /cuisines", headers=self.h)
        self.client.get("/api/recipes", name="GET /recipes", headers=self.h)

    @task(3)
    def my_stuff(self) -> None:
        self.client.get("/api/lists", name="GET /lists", headers=self.h)
        self.client.get("/api/savings", name="GET /savings", headers=self.h)

    @task(2)
    def screen_events(self) -> None:
        events_ = [{"name": "screen_view", "props": {"screen": random.choice(["/", "/meals", "/deals", "/lists"])}}]
        self.client.post("/api/events", name="POST /events", headers=self.h, json={"events": events_})

    @task(1)
    def plan_to_shopping(self) -> None:
        """Ana akış: plan kur -> listeye aktar -> optimize -> uygula -> bitir."""
        r = self.client.post("/api/meal-plans", name="POST /meal-plans", headers=self.h, json={
            "period": "weekly", "servings": 2, "meal_slots": ["aksam"], "courses": ["ana"],
        })
        if not r.ok:
            return
        self.plan_id = r.json()["id"]
        self.client.get(f"/api/meal-plans/{self.plan_id}", name="GET /meal-plans/{id}", headers=self.h)
        r = self.client.post(f"/api/meal-plans/{self.plan_id}/to-list", name="POST /meal-plans/{id}/to-list", headers=self.h, json={})
        if not r.ok:
            return
        self.list_id = r.json()["list"]["id"]
        self.client.get(f"/api/lists/{self.list_id}/optimize", name="GET /lists/{id}/optimize", headers=self.h)
        a = self.client.post(f"/api/lists/{self.list_id}/apply", name="POST /lists/{id}/apply", headers=self.h,
                             json={"plan_type": "combination"})
        if a.ok:
            self.client.post(f"/api/lists/{self.list_id}/complete", name="POST /lists/{id}/complete", headers=self.h)


@events.quitting.add_listener
def _gate(environment, **_kw) -> None:
    stats = environment.stats
    problems = []
    total = stats.total
    if total.num_requests and total.num_failures / total.num_requests > MAX_FAIL_RATIO:
        problems.append(f"hata oranı %{100 * total.num_failures / total.num_requests:.2f} > %{100 * MAX_FAIL_RATIO:.0f}")
    for entry in stats.entries.values():
        if entry.name in READ_NAMES and entry.num_requests:
            p95 = entry.get_response_time_percentile(0.95)
            if p95 > P95_LIMIT_MS:
                problems.append(f"{entry.name}: p95 {p95:.0f} ms > {P95_LIMIT_MS:.0f} ms")
    if problems:
        print("YÜK TESTİ KAPISI BAŞARISIZ:\n  " + "\n  ".join(problems))
        environment.process_exit_code = 1
    else:
        print(f"YÜK TESTİ KAPISI GEÇTİ (okuma uçları p95 ≤ {P95_LIMIT_MS:.0f} ms, hata ≤ %{100 * MAX_FAIL_RATIO:.0f})")
