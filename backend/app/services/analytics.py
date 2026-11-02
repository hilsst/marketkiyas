"""Analitik ve huni ölçümü (Faz 1): plan -> liste -> alışveriş ve 4. hafta geri dönüş.

Olayların iki kaynağı var:
- Sunucu (güvenilir): huninin adımları, ilgili uç başarıyla dönünce ara katman (middleware) yazar.
  Böylece telefonda olay kaybolsa da (çevrimdışı, uygulama kapandı) huni sayıları doğru kalır.
- Uygulama: açılış, ekran görüntüleme gibi sunucunun göremediği olaylar; POST /api/events ile toplu gelir.

Kişi = cihaz kimliği (telefonun ürettiği rastgele UUID, X-Device-Id başlığı). Misafir de sayılır;
hesap açınca aynı cihazın olayları aynı kişiye yazılır. Cihaz kimliği yoksa (web) "u:<user_id>".
"""

import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models import AnalyticsEvent

log = logging.getLogger(__name__)

# Testler kendi oturum fabrikasını koyar
session_factory: async_sessionmaker[AsyncSession] = SessionLocal

DEVICE_HEADER = "x-device-id"
DEVICE_ID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")
EVENT_NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
MAX_PROPS_KEYS = 20
MAX_PROP_STR = 200

# Huni adımları, sırasıyla. Hepsi sunucu olayıdır.
FUNNEL_STEPS = ("plan_created", "plan_to_list", "shopping_started", "shopping_completed")

# (yöntem, yol, başarı kodu, olay adı). Yol içindeki sayılar olaya özellik olarak eklenir.
_SERVER_EVENTS: tuple[tuple[str, re.Pattern[str], int, str], ...] = (
    ("POST", re.compile(r"^/api/meal-plans/?$"), 201, "plan_created"),
    ("POST", re.compile(r"^/api/meal-plans/(?P<plan_id>\d+)/to-list$"), 200, "plan_to_list"),
    ("POST", re.compile(r"^/api/lists/(?P<list_id>\d+)/apply$"), 200, "shopping_started"),
    ("POST", re.compile(r"^/api/lists/(?P<list_id>\d+)/complete$"), 200, "shopping_completed"),
    ("POST", re.compile(r"^/api/auth/register$"), 201, "signed_up"),
    ("POST", re.compile(r"^/api/auth/google$"), 200, "google_login"),
)
SERVER_EVENT_NAMES = frozenset(e[3] for e in _SERVER_EVENTS)


def match_server_event(method: str, path: str) -> tuple[str, int, dict[str, int]] | None:
    """Bu istek bir huni adımı mı? (olay adı, beklenen durum kodu, yol özellikleri)"""
    for m, pattern, status, name in _SERVER_EVENTS:
        if m == method and (hit := pattern.match(path)):
            return name, status, {k: int(v) for k, v in hit.groupdict().items()}
    return None


def clean_device_id(value: str | None) -> str | None:
    return value if value and DEVICE_ID_RE.match(value) else None


def user_id_from_authorization(header: str | None) -> int | None:
    """Ara katman için: veritabanına gitmeden token'dan kullanıcı. Geçersizse None (uç zaten 401 döner)."""
    if not header or not header.lower().startswith("bearer "):
        return None
    try:
        return int(decode_access_token(header[7:].strip())["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


def clean_props(props: dict[str, Any] | None) -> dict[str, Any]:
    """Yalnız düz değerler (metin, sayı, evet/hayır), en çok 20 anahtar; metinler kısaltılır.
    Kişisel veri (e-posta, ad) gönderilmemeli; burada yalnız boyut sınırlanır."""
    out: dict[str, Any] = {}
    for k, v in (props or {}).items():
        if len(out) >= MAX_PROPS_KEYS:
            break
        if not isinstance(k, str) or not EVENT_NAME_RE.match(k):
            continue
        if isinstance(v, str):
            out[k] = v[:MAX_PROP_STR]
        elif v is None or isinstance(v, (bool, int, float)):
            out[k] = v
    return out


def clamp_time(at: datetime | None, now: datetime) -> datetime:
    """Telefon saati yanlış olabilir: gelecekten ya da 7 günden eski zamanlar yerine şimdiki zaman."""
    if at is None:
        return now
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    if at > now + timedelta(minutes=5) or at < now - timedelta(days=7):
        return now
    return at


async def record_server_event(
    name: str, *, device_id: str | None, user_id: int | None, props: dict[str, Any] | None = None
) -> None:
    if device_id is None and user_id is None:
        return
    async with session_factory() as db:
        if user_id is not None and await db.scalar(text("SELECT 1 FROM users WHERE id = :id"), {"id": user_id}) is None:
            user_id = None  # silinmiş hesap
        db.add(AnalyticsEvent(
            name=name, source="server", device_id=device_id, user_id=user_id,
            occurred_at=datetime.now(timezone.utc), props=clean_props(props),
        ))
        await db.commit()


async def record_client_events(
    db: AsyncSession, *, device_id: str | None, user_id: int | None,
    events: list[tuple[str, datetime | None, dict[str, Any] | None]],
) -> int:
    now = datetime.now(timezone.utc)
    rows = [
        AnalyticsEvent(name=name, source="app", device_id=device_id, user_id=user_id,
                       occurred_at=clamp_time(at, now), props=clean_props(props))
        for name, at, props in events
    ]
    db.add_all(rows)
    await db.commit()
    return len(rows)


async def erase_user_events(db: AsyncSession, user_id: int) -> None:
    """Hesap silinince (KVKK) kişinin olayları ve aynı cihazlardaki misafir olayları da silinir;
    cihaz kimliği başka bir olay üzerinden kişiye bağlanamaz kalır."""
    await db.execute(text(
        "DELETE FROM analytics_events WHERE user_id = :u OR device_id IN "
        "(SELECT device_id FROM analytics_events WHERE user_id = :u AND device_id IS NOT NULL)"
    ), {"u": user_id})


# ---------- Rapor ----------

def _actor(alias: str = "") -> str:
    return f"COALESCE({alias}device_id, 'u:' || {alias}user_id::text)"


_ACTOR = _actor()


@dataclass
class FunnelStep:
    name: str
    actors: int  # bu adımı (bir önceki adımdan sonra) yapan kişi
    rate_from_previous: float | None
    rate_from_first: float | None


@dataclass
class Report:
    since: datetime
    until: datetime
    active_actors: int  # pencerede herhangi bir olayı olan kişi
    event_counts: dict[str, int]
    funnel: list[FunnelStep]
    # 4. hafta geri dönüş: ilk görülmesinden sonraki 21.-28. günlerde tekrar gelen kişi oranı.
    # Yalnız 28 günü dolmuş kişiler sayılır.
    week4_eligible: int
    week4_returned: int
    week4_rate: float | None
    # Faz 2a kapısı (ilk 14 gün): en az 2 farklı haftada plan kuran ve planını listeye taşıyan oranı
    gate_eligible: int
    gate_two_week_planners: int
    gate_two_week_rate: float | None
    gate_plan_to_list: int
    gate_plan_to_list_rate: float | None
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _rate(a: int, b: int) -> float | None:
    return round(a / b, 4) if b else None


async def build_report(db: AsyncSession, since: datetime, until: datetime, now: datetime | None = None) -> Report:
    now = now or datetime.now(timezone.utc)
    window = {"since": since, "until": until}

    active = await db.scalar(text(
        f"SELECT count(DISTINCT {_ACTOR}) FROM analytics_events "
        "WHERE occurred_at >= :since AND occurred_at < :until AND (device_id IS NOT NULL OR user_id IS NOT NULL)"
    ), window) or 0

    counts = dict((await db.execute(text(
        "SELECT name, count(*) FROM analytics_events WHERE occurred_at >= :since AND occurred_at < :until "
        "GROUP BY name ORDER BY name"
    ), window)).all())

    # Sıralı huni: her kişi için her adım, bir önceki adımın zamanından SONRAki ilk gerçekleşmesiyle sayılır
    # (kişi huniden önce başka bir listeyle alışveriş yapmış olsa da düşmez).
    rows: dict[str, dict[str, list[datetime]]] = {}
    for actor, name, at in (await db.execute(text(
        f"SELECT {_ACTOR} AS actor, name, occurred_at FROM analytics_events "
        "WHERE occurred_at >= :since AND occurred_at < :until AND name = ANY(:steps) "
        "AND (device_id IS NOT NULL OR user_id IS NOT NULL) ORDER BY occurred_at"
    ), {**window, "steps": list(FUNNEL_STEPS)})).all():
        rows.setdefault(actor, {}).setdefault(name, []).append(at)

    funnel: list[FunnelStep] = []
    reached: dict[str, datetime | None] = {actor: None for actor in rows}  # None = adım sınırı yok (ilk adım)
    first_count: int | None = None
    prev_count: int | None = None
    for i, step in enumerate(FUNNEL_STEPS):
        nxt: dict[str, datetime | None] = {}
        for actor, after in reached.items():
            at = next((t for t in rows[actor].get(step, ()) if after is None or t >= after), None)
            if at is not None:
                nxt[actor] = at
        n = len(nxt)
        if first_count is None:
            first_count = n
        funnel.append(FunnelStep(step, n, _rate(n, prev_count) if i else None, _rate(n, first_count) if i else None))
        reached, prev_count = nxt, n

    # Kohortlar: ilk olayı, geri dönüş/kapı süresi kadar ÖNCEKİ pencerede olan kişiler. Böylece "son 28 gün"
    # raporunda 4. hafta oranı, 28-56 gün önce gelenlerin davranışını gösterir (pencere içindekiler henüz
    # 28 günü doldurmamıştır). Yalnız süresi dolmuş kişiler sayılır.
    def cohort_sql(days: int) -> str:
        return (
            f"WITH firsts AS (SELECT {_ACTOR} AS actor, min(occurred_at) AS first_at FROM analytics_events "
            "WHERE device_id IS NOT NULL OR user_id IS NOT NULL GROUP BY actor), "
            f"cohort AS (SELECT actor, first_at FROM firsts WHERE first_at >= CAST(:since AS timestamptz) - interval '{days} days' "
            f"AND first_at < CAST(:until AS timestamptz) - interval '{days} days') "
        )
    w4 = (await db.execute(text(
        cohort_sql(28) +
        "SELECT count(*) FILTER (WHERE c.first_at + interval '28 days' <= :now), "
        "count(*) FILTER (WHERE c.first_at + interval '28 days' <= :now AND EXISTS ("
        f"  SELECT 1 FROM analytics_events e WHERE {_actor('e.')} = c.actor "
        "   AND e.occurred_at >= c.first_at + interval '21 days' AND e.occurred_at < c.first_at + interval '28 days')) "
        "FROM cohort c"
    ), {**window, "now": now})).one()

    gate = (await db.execute(text(
        cohort_sql(14) +
        ", per AS (SELECT c.actor, "
        "  count(DISTINCT date_trunc('week', e.occurred_at)) FILTER (WHERE e.name = 'plan_created') AS plan_weeks, "
        "  bool_or(e.name = 'plan_to_list') AS moved "
        "  FROM cohort c LEFT JOIN analytics_events e "
        f"  ON {_actor('e.')} = c.actor "
        "  AND e.occurred_at < c.first_at + interval '14 days' "
        "  WHERE c.first_at + interval '14 days' <= :now GROUP BY c.actor) "
        "SELECT count(*), count(*) FILTER (WHERE plan_weeks >= 2), count(*) FILTER (WHERE moved) FROM per"
    ), {**window, "now": now})).one()

    notes = []
    if w4[0] == 0:
        notes.append("4. hafta oranı için ilk görülmesinin üzerinden 28 gün geçmiş kişi yok (kohort: dönemden 28 gün önce gelenler).")
    return Report(
        since=since, until=until, active_actors=active, event_counts=counts, funnel=funnel,
        week4_eligible=w4[0], week4_returned=w4[1], week4_rate=_rate(w4[1], w4[0]),
        gate_eligible=gate[0], gate_two_week_planners=gate[1], gate_two_week_rate=_rate(gate[1], gate[0]),
        gate_plan_to_list=gate[2], gate_plan_to_list_rate=_rate(gate[2], gate[0]), notes=notes,
    )


def format_report(r: Report) -> str:
    pct = lambda v: "-" if v is None else f"%{v * 100:.1f}"  # noqa: E731
    lines = [
        f"Dönem: {r.since:%Y-%m-%d} – {r.until:%Y-%m-%d}",
        f"Aktif kişi (cihaz): {r.active_actors}",
        "",
        "Huni (sıralı):",
    ]
    for s in r.funnel:
        lines.append(f"  {s.name:<20} {s.actors:>7}   önceki adımdan {pct(s.rate_from_previous):>7}   ilk adımdan {pct(s.rate_from_first):>7}")
    lines += [
        "",
        f"4. hafta geri dönüş: {r.week4_returned}/{r.week4_eligible} ({pct(r.week4_rate)})",
        f"Faz 2a kapısı (ilk 14 gün, {r.gate_eligible} kişi):",
        f"  2 farklı haftada plan kuran: {r.gate_two_week_planners} ({pct(r.gate_two_week_rate)}; hedef ≥ %50)",
        f"  planını listeye taşıyan:     {r.gate_plan_to_list} ({pct(r.gate_plan_to_list_rate)}; hedef ≥ %30)",
        "",
        "Olay sayıları:",
        *[f"  {k:<24} {v}" for k, v in r.event_counts.items()],
        *r.notes,
    ]
    return "\n".join(lines)
