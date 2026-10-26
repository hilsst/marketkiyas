import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://marketkiyas:marketkiyas@localhost:5432/marketkiyas_test"
)

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.session import get_db
from app.main import app

engine = create_async_engine(settings.database_url, poolclass=NullPool)
TestSession = async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    cfg = Config("alembic.ini")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
async def clean_tables():
    yield
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE users, shopping_lists, shopping_list_items, savings_records, "
                "products, price_history, product_groups, group_members RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
async def db():
    async with TestSession() as session:
        yield session


@pytest.fixture
async def client():
    async def _get_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def auth_headers(client):
    r = await client.post(
        "/api/auth/register", json={"email": "kemal@example.com", "password": "gizli-sifre-123"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
