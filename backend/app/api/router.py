from fastapi import APIRouter

from app.api.routes import auth, catalog, health, lists, products, savings

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(catalog.router)
api_router.include_router(products.router)
api_router.include_router(lists.router)
api_router.include_router(savings.router)
