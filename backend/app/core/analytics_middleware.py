import logging

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.services import analytics

log = logging.getLogger(__name__)


class AnalyticsMiddleware:
    """Huni adımlarını (plan oluşturma, listeye aktarma, alışveriş) uç başarıyla dönünce kaydeder.
    Uçlara dokunmadan çalışır; kayıt hatası isteği asla bozmaz. Yanıt gönderildikten sonra yazar."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or (hit := analytics.match_server_event(scope["method"], scope["path"])) is None:
            await self.app(scope, receive, send)
            return

        status: list[int] = []

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status.append(message["status"])
            await send(message)

        await self.app(scope, receive, send_wrapper)

        name, expected, props = hit
        if not status or status[0] != expected:
            return
        headers = Headers(scope=scope)
        if headers.get("x-load-test"):
            return  # yük testi canlı huniyi bozmasın
        try:
            await analytics.record_server_event(
                name,
                device_id=analytics.clean_device_id(headers.get(analytics.DEVICE_HEADER)),
                user_id=analytics.user_id_from_authorization(headers.get("authorization")),
                props=props,
            )
        except Exception:
            log.exception("analitik olayı yazılamadı: %s", name)
