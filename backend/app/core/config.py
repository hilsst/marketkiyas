from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MarketKıyas API"
    environment: str = "development"

    database_url: str = "postgresql+asyncpg://marketkiyas:marketkiyas@localhost:5432/marketkiyas"

    jwt_secret_key: str = "dev-only-secret-change-me-in-production-please"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 gün (mobil PWA için uzun oturum)

    # marketfiyati.org.tr (T.C. Ticaret Bakanlığı / TÜBİTAK fiyat platformu)
    marketfiyati_base_url: str = "https://api.marketfiyati.org.tr"
    marketfiyati_min_interval_seconds: float = 1.0  # istekler arası en az bekleme
    marketfiyati_max_retries: int = 4
    marketfiyati_timeout_seconds: float = 30.0
    default_search_distance_km: int = 5

    # Next.js frontend adresleri, virgülle ayrılmış
    cors_origins: str = "http://localhost:3000"

    @model_validator(mode="after")
    def _require_real_secret_in_prod(self) -> "Settings":
        if self.environment == "production" and self.jwt_secret_key.startswith("dev-only"):
            raise ValueError("Production ortamında JWT_SECRET_KEY ayarlanmalı")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
