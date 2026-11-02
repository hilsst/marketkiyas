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
    # Misafirin şifresi yok: anahtar biterse verisine bir daha ulaşamaz, bu yüzden uzun
    guest_token_expire_minutes: int = 60 * 24 * 365
    # Sunucu bir vekilin (Next.js /api, yük dengeleyici) arkasındaysa istemci adresi X-Forwarded-For'dadır
    trust_forwarded_for: bool = False
    guest_per_ip_per_hour: int = 20  # aynı adresten saatte açılabilecek misafir oturumu

    # marketfiyati.org.tr (T.C. Ticaret Bakanlığı / TÜBİTAK fiyat platformu)
    marketfiyati_base_url: str = "https://api.marketfiyati.org.tr"
    marketfiyati_min_interval_seconds: float = 1.0  # istekler arası en az bekleme
    marketfiyati_max_retries: int = 4
    marketfiyati_timeout_seconds: float = 30.0
    marketfiyati_user_agent: str = "MarketKiyas/0.1 (+https://github.com/hilsst/marketkiyas)"
    default_search_distance_km: int = 5
    # Market siteleri: sayfa başına daha uzun bekleme (sunuculara yük bindirmemek için)
    scraper_min_interval_seconds: float = 3.0
    # Boşsa Playwright'ın kendi indirdiği Chromium kullanılır; hazır kurulu bir Chromium için yolunu verin
    chromium_executable_path: str | None = None

    # Next.js frontend adresleri, virgülle ayrılmış
    cors_origins: str = "http://localhost:3000"

    # E-posta (şifre sıfırlama kodu). smtp_host boşsa e-posta gönderilmez, kod sunucu günlüğüne yazılır (geliştirme)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    mail_from: str = "Ucuzu <no-reply@ucuzu.app>"

    # Google ile giriş: kabul edilen OAuth istemci kimlikleri (Android, iOS, web), virgülle ayrılmış
    google_client_ids: str = ""

    # Haftalık menü bildirimi push gönderimi (Expo). Kapalıyken bildirim yalnız uygulama içinde görünür.
    expo_push_enabled: bool = False
    expo_push_url: str = "https://exp.host/--/api/v2/push/send"

    # Analitik raporu (GET /api/analytics/report, X-Analytics-Token başlığı). Boşsa rapor ucu kapalı;
    # rapor her zaman `python -m app.cli analytics` ile de alınabilir
    analytics_token: str = ""

    @model_validator(mode="after")
    def _require_real_secret_in_prod(self) -> "Settings":
        if self.environment == "production" and self.jwt_secret_key.startswith("dev-only"):
            raise ValueError("Production ortamında JWT_SECRET_KEY ayarlanmalı")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def google_client_id_list(self) -> list[str]:
        return [c.strip() for c in self.google_client_ids.split(",") if c.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
