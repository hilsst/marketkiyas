from fastapi import APIRouter

from app.api.routes import alerts, auth, catalog, family, health, lists, products, savings, stores

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
api_router.include_router(products.router)
api_router.include_router(lists.router)
api_router.include_router(savings.router)
api_router.include_router(stores.router)
api_router.include_router(alerts.router)
api_router.include_router(family.router)
