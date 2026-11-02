from fastapi import APIRouter

from app.api.routes import (
    aktuel,
    alerts,
    analytics,
    auth,
    catalog,
    deal_menu,
    family,
    health,
    lists,
    meals,
    products,
    savings,
    stores,
)

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
api_router.include_router(aktuel.router)
api_router.include_router(meals.router)
api_router.include_router(deal_menu.router)
api_router.include_router(analytics.router)
