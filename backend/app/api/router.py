from fastapi import APIRouter

from app.api.routes import auth, catalog, health

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
# Sonraki adım: products, lists, optimize, savings router'ları
