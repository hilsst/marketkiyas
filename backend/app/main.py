import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings

log = logging.getLogger("marketkiyas")


async def _check_recipes() -> None:
    """Açılışta (ör. güncellemeyle yeni tarifler geldiğinde) malzemesi marketlerde olmayan tarifleri gizle.
    Sonraki kontroller fiyat senkronizasyonundan sonra worker'da yapılır."""
    from app.db.session import SessionLocal
    from app.services.meals import refresh_availability

    try:
        async with SessionLocal() as db:
            await refresh_availability(db)
    except Exception:
        log.exception("tarif bulunabilirlik kontrolü başarısız")


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(_check_recipes())
    yield
    task.cancel()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
