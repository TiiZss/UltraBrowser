"""
Bloqueador de anuncios y rastreadores para UltraBrowser
Usa QWebEngineUrlRequestInterceptor para interceptar y bloquear peticiones
sin romper la funcionalidad de las páginas.
"""

from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo
from .logging_config import get_logger

logger = get_logger()

# Dominios de redes publicitarias y rastreadores conocidos
# Esta lista bloquea el dominio y TODOS sus subdominios
AD_DOMAINS: frozenset = frozenset({
    # === Google Ads & Analytics ===
    "googleadservices.com",
    "googlesyndication.com",
    "doubleclick.net",
    "google-analytics.com",
    "googletagmanager.com",
    "googletagservices.com",
    "googleadapis.com",
    "googlevideo.com",          # Solo anuncios pre-roll (NO bloquear totalmente - ver nota)
    "adservice.google.com",
    "pagead2.googlesyndication.com",

    # === Facebook / Meta ===
    "connect.facebook.net",
    "an.facebook.com",
    "pixel.facebook.com",

    # === Amazon Ads ===
    "amazon-adsystem.com",
    "assoc-amazon.com",

    # === Microsoft / Bing Ads ===
    "bat.bing.com",
    "ads.microsoft.com",
    "c.microsoft.com",

    # === Redes publicitarias grandes ===
    "outbrain.com",
    "taboola.com",
    "criteo.com",
    "criteo.net",
    "rubiconproject.com",
    "pubmatic.com",
    "openx.net",
    "openx.org",
    "adnxs.com",
    "adnxs.net",
    "advertising.com",
    "adform.net",
    "adform.com",
    "adsrvr.org",
    "adroll.com",
    "adtechus.com",
    "atwola.com",
    "brightmountainmedia.com",
    "casalemedia.com",
    "contextweb.com",
    "conversantmedia.com",
    "emxdgt.com",
    "lijit.com",
    "lkqd.net",
    "loopme.com",
    "media.net",
    "moatads.com",
    "oath.com",
    "optimizely.com",
    "revcontent.com",
    "rhythmone.com",
    "sharethrough.com",
    "smartadserver.com",
    "sovrn.com",
    "spotxchange.com",
    "springserve.com",
    "synacor.com",
    "tribalfusion.com",
    "undertone.com",
    "unrulymedia.com",
    "vertamedia.com",
    "yieldmo.com",

    # === Rastreadores / Analytics ===
    "scorecardresearch.com",
    "quantserve.com",
    "hotjar.com",
    "mixpanel.com",
    "segment.io",
    "segment.com",
    "amplitude.com",
    "fullstory.com",
    "heap.io",
    "heapanalytics.com",
    "newrelic.com",
    "nr-data.net",
    "datadoghq.com",
    "mouseflow.com",
    "luckyorange.com",
    "crazyegg.com",
    "inspectlet.com",
    "intercom.io",
    "intercomcdn.com",

    # === Publicidad Twitter/X ===
    "ads.twitter.com",
    "analytics.twitter.com",
    "ads-twitter.com",
    "static.ads-twitter.com",

    # === Otros rastreadores ===
    "adsafeprotected.com",
    "doubleverify.com",
    "comscore.com",
    "omtrdc.net",              # Adobe Analytics
    "2mdn.net",
    "adfox.ru",
    "bidswitch.net",
    "bluekai.com",
    "demdex.net",              # Adobe Audience Manager
    "exelator.com",
    "idsync.rlcdn.com",
    "krxd.net",
    "liverail.com",
    "mxpnl.com",
    "nexac.com",
    "pixel.advertising.com",
    "rfihub.com",
    "rfihub.net",
    "rtax.criteo.com",
    "secure.adnxs.com",
    "servedby-buysellads.com",
    "sizmek.com",
    "spotx.tv",
    "stickyadstv.com",
    "teads.tv",
    "tremorhub.com",
    "turn.com",
    "tvpixel.com",
    "vindico.com",
    "xaxis.com",
    "yandex-team.ru",         # Solo tracker de Yandex, no el buscador
    "zemanta.com",
})

# Subdominios específicos que son anuncios aunque su dominio principal sea legítimo
# Formato: "subdominio.dominio.tld"
AD_SUBDOMAINS: frozenset = frozenset({
    "ads.google.com",
    "ad.google.com",
    "adservice.google.com",
    "pagead2.googlesyndication.com",
    "tpc.googlesyndication.com",
    "pixel.twitter.com",
    "ads.yahoo.com",
    "udc.yahoo.com",
    "ads.linkedin.com",
    "px.ads.linkedin.com",
    "snap.licdn.com",
    "ads.reddit.com",
    "rp.reddit.com",
    "events.reddit.com",
    "ads.tiktok.com",
    "analytics.tiktok.com",
})

# Patrones en la ruta de la URL que indican anuncios
# Solo se aplican a recursos de terceros (no al frame principal)
AD_PATH_PATTERNS: tuple = (
    "/ads/",
    "/ad/",
    "/advertisement/",
    "/adserver/",
    "/adservice/",
    "/advert/",
    "/tracking/",
    "/tracker/",
    "/pixel.gif",
    "/pixel.png",
    "/pixel.js",
    "/beacon/",
    "/beacon.gif",
    "/counter.",
    "/impression.",
    "/imp.php",
    "/imp.js",
    "/analytics.js",
    "/ga.js",
    "/gtag/js",
)


class AdBlocker(QWebEngineUrlRequestInterceptor):
    """
    Bloqueador de anuncios y rastreadores.

    Intercepta peticiones HTTP antes de que se realicen y bloquea
    las que provienen de dominios publicitarios conocidos, preservando
    la funcionalidad de la página (scripts propios, imágenes, etc.).
    """

    def __init__(self, enabled: bool = True):
        super().__init__()
        self._enabled = enabled
        self._blocked_count = 0
        self._session_blocked_count = 0

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:
        """
        Intercepta y filtra peticiones de red.
        Solo bloquea recursos de terceros conocidos como anuncios.
        NUNCA bloquea el frame principal para no romper la navegación.
        """
        if not self._enabled:
            return

        # Nunca bloquear el frame principal (evita romper la página)
        if info.resourceType() == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMainFrame:
            return

        url = info.requestUrl()
        host = url.host().lower()

        # Eliminar "www." para la comparación
        bare_host = host[4:] if host.startswith("www.") else host

        # 1. Comprobar subdominios específicos conocidos como publicidad
        if host in AD_SUBDOMAINS or bare_host in AD_SUBDOMAINS:
            self._block(info, host)
            return

        # 2. Comprobar si el dominio o sus subdominios están en la lista negra
        # Ejemplo: "ads.example.com" -> comprueba "ads.example.com", "example.com"
        parts = bare_host.split(".")
        for i in range(len(parts) - 1):
            candidate = ".".join(parts[i:])
            if candidate in AD_DOMAINS:
                self._block(info, host)
                return

        # 3. Comprobar patrones de URL en recursos de terceros
        # Solo aplica si el origen de la petición y el destino son diferentes
        first_party = info.firstPartyUrl().host()
        if first_party and first_party != host:
            path = url.path().lower()
            query = url.query().lower()
            full_path = path + ("?" + query if query else "")
            for pattern in AD_PATH_PATTERNS:
                if pattern in full_path:
                    self._block(info, f"{host}{path[:60]}")
                    return

    def _block(self, info: QWebEngineUrlRequestInfo, identifier: str) -> None:
        """Bloquea la petición y registra el evento"""
        info.block(True)
        self._blocked_count += 1
        self._session_blocked_count += 1
        logger.debug(f"[AdBlock] Bloqueado: {identifier}")

    @property
    def blocked_count(self) -> int:
        """Total de peticiones bloqueadas en la sesión"""
        return self._blocked_count

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Activa o desactiva el bloqueador"""
        self._enabled = enabled
        logger.info(f"AdBlocker {'activado' if enabled else 'desactivado'}")

    def reset_count(self) -> None:
        """Resetea el contador de bloqueos"""
        self._session_blocked_count = 0
        logger.debug("Contador de AdBlocker reseteado")
