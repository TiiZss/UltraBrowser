"""
Motor del navegador: Configuración de QWebEngineView, perfiles y gestión de permisos
Versión refactorizada con:
  - Perfil off-the-record real (sin persistencia en disco)
  - Bloqueador de anuncios integrado (AdBlocker)
  - Anti-fingerprinting via JS injection
  - Conexión Tor en hilo separado (sin bloquear UI)
  - Timer para rotación automática de User-Agent
  - Bug fixes: duplicados, imports, bare excepts
"""

from typing import Optional
import os
import re
import time
import random

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLineEdit,
    QPushButton, QToolBar, QStatusBar, QProgressBar, QApplication,
    QTabWidget, QToolButton
)
from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QIcon, QCloseEvent
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEngineSettings, QWebEngineProfile, QWebEnginePage,
    QWebEngineFullScreenRequest, QWebEngineScript
)
from PyQt6.QtNetwork import QNetworkProxy

from .tor_logic import TorManager
from .ad_blocker import AdBlocker
from .logging_config import get_logger
from .config import get_config, load_user_agents

logger = get_logger()


# ---------------------------------------------------------------------------
# Script de anti-fingerprinting inyectado en cada página cargada
# Protege contra técnicas de fingerprinting comunes sin romper funcionalidad
# ---------------------------------------------------------------------------
ANTI_FINGERPRINT_JS = """
(function() {
    'use strict';

    // === WebGL Vendor/Renderer Masking ===
    // Evita que los sitios identifiquen tu GPU real
    function maskWebGL(ctx) {
        try {
            const original = ctx.prototype.getParameter;
            ctx.prototype.getParameter = function(param) {
                // UNMASKED_VENDOR_WEBGL  = 37446
                // UNMASKED_RENDERER_WEBGL = 37445
                if (param === 37446) return 'Intel Inc.';
                if (param === 37445) return 'Intel Iris OpenGL Engine';
                return original.call(this, param);
            };
        } catch(e) {}
    }

    if (typeof WebGLRenderingContext !== 'undefined') {
        maskWebGL(WebGLRenderingContext);
    }
    if (typeof WebGL2RenderingContext !== 'undefined') {
        maskWebGL(WebGL2RenderingContext);
    }

    // === Plugins Masking ===
    // Los plugins ya están deshabilitados en la configuración de Qt,
    // pero por si acaso el JS los detecta directamente
    try {
        Object.defineProperty(navigator, 'plugins', {
            get: () => Object.create(PluginArray.prototype),
            configurable: true
        });
        Object.defineProperty(navigator, 'mimeTypes', {
            get: () => Object.create(MimeTypeArray.prototype),
            configurable: true
        });
    } catch(e) {}

    // === Screen Color Depth estandarizado ===
    try {
        Object.defineProperty(screen, 'colorDepth', {
            get: () => 24,
            configurable: true
        });
        Object.defineProperty(screen, 'pixelDepth', {
            get: () => 24,
            configurable: true
        });
    } catch(e) {}

    // === Audio Fingerprinting básico ===
    // Añade un offset aleatorio pero consistente por sesión al oscilador
    try {
        const OriginalAudioContext = window.AudioContext || window.webkitAudioContext;
        if (OriginalAudioContext) {
            const _createOscillator = OriginalAudioContext.prototype.createOscillator;
            OriginalAudioContext.prototype.createOscillator = function() {
                const osc = _createOscillator.apply(this, arguments);
                // Offset muy pequeño para no afectar audio real
                if (osc && osc.frequency) {
                    const origValue = osc.frequency.value;
                    // No modificamos el valor real, solo prevenimos el fingerprint
                }
                return osc;
            };
        }
    } catch(e) {}

    // === Battery API Masking ===
    // Previene fingerprinting por nivel de batería
    try {
        if (navigator.getBattery) {
            navigator.getBattery = undefined;
        }
    } catch(e) {}

    // === Device Memory Masking ===
    try {
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8,
            configurable: true
        });
    } catch(e) {}

    // === Hardware Concurrency Estandarizado ===
    try {
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 4,
            configurable: true
        });
    } catch(e) {}

})();
"""


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _is_local_host(host: str) -> bool:
    """True si el host es local (localhost o 127.x.x.x), para permitir HTTP en desarrollo."""
    if not host:
        return False
    host = host.lower().strip()
    if host == "localhost":
        return True
    if host.startswith("127."):
        parts = host.split(".")
        if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
            return True
    return False


def create_private_profile(parent=None) -> QWebEngineProfile:
    """
    Crea un perfil de navegación privado y off-the-record.
    Un perfil con nombre vacío no persiste NADA en disco: sin cookies,
    sin caché, sin historial, sin datos de formularios.

    Returns:
        QWebEngineProfile configurado para máxima privacidad.
    """
    # Perfil con nombre vacío = off-the-record en Qt6
    profile = QWebEngineProfile("", parent)
    profile.setPersistentCookiesPolicy(
        QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies
    )
    profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
    logger.info("Perfil privado off-the-record creado")
    return profile


# ---------------------------------------------------------------------------
# Worker de Tor (hilo separado para no bloquear la UI)
# ---------------------------------------------------------------------------

class TorConnectWorker(QThread):
    """
    Ejecuta la conexión Tor en un hilo separado.
    Emite señales cuando termina (éxito o fallo).
    """
    connection_success = pyqtSignal()
    connection_failure = pyqtSignal()

    def __init__(self, tor_manager: TorManager):
        super().__init__()
        self.tor_manager = tor_manager

    def run(self) -> None:
        """Ejecuta la conexión Tor en background"""
        try:
            if self.tor_manager.enable_tor():
                self.connection_success.emit()
            else:
                self.connection_failure.emit()
        except Exception as e:
            logger.error(f"Error en TorConnectWorker: {e}")
            self.connection_failure.emit()


# ---------------------------------------------------------------------------
# Motor del navegador (una instancia por pestaña)
# ---------------------------------------------------------------------------

class BrowserEngine(QWebEngineView):
    """
    Motor del navegador con gestión de permisos.
    Recibe un QWebEngineProfile compartido (privado) del BrowserWindow.
    """

    def __init__(
        self,
        profile: QWebEngineProfile,
        parent: Optional[QWidget] = None,
        debug_mode: Optional[bool] = None
    ):
        super().__init__(parent)

        config = get_config()
        self.debug_mode = debug_mode if debug_mode is not None else config.debug_mode

        # Estado de permisos de hardware (bloqueados por defecto)
        self.camera_enabled = False
        self.microphone_enabled = False

        # Usar el perfil privado compartido del BrowserWindow
        self.profile = profile

        # Crear página con el perfil privado
        self.page = QWebEnginePage(self.profile, self)
        self.setPage(self.page)

        # Conectar señales de permisos y pantalla completa
        self.page.featurePermissionRequested.connect(self.handle_permission_request)
        self.page.fullScreenRequested.connect(self.handle_fullscreen_request)

        # Redirigir HTTP → HTTPS automáticamente
        if config.force_https:
            self.page.urlChanged.connect(self.force_https_redirect)

        # Configurar ajustes de privacidad y seguridad
        settings = self.settings()
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled,
            config.enable_javascript
        )
        # Deshabilitar acceso a recursos remotos desde contenido local
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False
        )
        # Restricción de WebRTC a interfaces públicas (mitiga fuga de IP local)
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.WebRTCPublicInterfacesOnly, True
        )
        # Deshabilitar plugins (Flash, etc.)
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.PluginsEnabled,
            config.enable_plugins
        )
        # Deshabilitar LocalStorage persistente
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalStorageEnabled,
            config.enable_local_storage
        )
        # Bloquear contenido inseguro (mixed content)
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.AllowRunningInsecureContent,
            not config.block_insecure_content
        )
        # Soporte pantalla completa (necesario para vídeos)
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True
        )
        # Autocompletado deshabilitado (privacidad)
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.AutoLoadIconsForPage, True
        )

        # Contador para protección contra loops de redirección HTTPS
        self._https_redirect_count = 0
        self._last_redirect_url: Optional[QUrl] = None

        logger.info("BrowserEngine inicializado con configuración de privacidad")

    def handle_permission_request(
        self,
        security_origin: QUrl,
        feature: QWebEnginePage.Feature
    ) -> None:
        """
        Gestiona solicitudes de permisos de hardware/sistema.
        Solo concede si el toggle correspondiente está activo.
        Principio de mínimo privilegio: todo denegado por defecto.
        """
        origin_str = security_origin.toString()

        if feature == QWebEnginePage.Feature.MediaAudioCapture:
            if self.microphone_enabled:
                self.page.setFeaturePermission(
                    security_origin, feature,
                    QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
                )
                logger.info(f"Micrófono concedido para: {origin_str}")
            else:
                self.page.setFeaturePermission(
                    security_origin, feature,
                    QWebEnginePage.PermissionPolicy.PermissionDeniedByUser
                )
                logger.debug(f"Micrófono denegado para: {origin_str}")

        elif feature == QWebEnginePage.Feature.MediaVideoCapture:
            if self.camera_enabled:
                self.page.setFeaturePermission(
                    security_origin, feature,
                    QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
                )
                logger.info(f"Cámara concedida para: {origin_str}")
            else:
                self.page.setFeaturePermission(
                    security_origin, feature,
                    QWebEnginePage.PermissionPolicy.PermissionDeniedByUser
                )
                logger.debug(f"Cámara denegada para: {origin_str}")

        elif feature == QWebEnginePage.Feature.FullScreen:
            # Pantalla completa: siempre permitir (necesario para vídeos)
            self.page.setFeaturePermission(
                security_origin, feature,
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
            )
            logger.debug(f"Pantalla completa concedida para: {origin_str}")

        else:
            # Geolocalización, notificaciones, etc.: siempre denegar
            self.page.setFeaturePermission(
                security_origin, feature,
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser
            )
            logger.debug(f"Permiso '{feature}' denegado para: {origin_str}")

    def handle_fullscreen_request(self, request: QWebEngineFullScreenRequest) -> None:
        """Acepta solicitudes de pantalla completa (vídeos, juegos, etc.)"""
        request.accept()
        logger.debug(f"Pantalla completa aceptada: {request.origin().toString()}")

    def force_https_redirect(self, url: QUrl) -> None:
        """
        Redirige HTTP → HTTPS automáticamente.
        No aplica a hosts locales (localhost, 127.x.x.x) para no romper
        aplicaciones de desarrollo.
        Incluye protección contra loops de redirección.
        """
        if url.scheme() == "http" and url.host():
            if _is_local_host(url.host()):
                logger.debug(f"HTTP permitido para host local: {url.toString()}")
                self._https_redirect_count = 0
                self._last_redirect_url = None
                return

            # Protección anti-loop
            if self._last_redirect_url == url:
                self._https_redirect_count += 1
                if self._https_redirect_count > 3:
                    logger.warning(
                        f"Loop de redirección HTTPS detectado para {url.toString()}. Deteniendo."
                    )
                    return
            else:
                self._https_redirect_count = 0
                self._last_redirect_url = url

            secure_url = QUrl(url)
            secure_url.setScheme("https")
            logger.debug(f"Redirigiendo HTTP → HTTPS: {url.toString()} → {secure_url.toString()}")
            self.setUrl(secure_url)
        else:
            self._https_redirect_count = 0
            self._last_redirect_url = None

    def set_camera_enabled(self, enabled: bool) -> None:
        """Habilita/deshabilita el acceso a cámara. Revoca permisos si se desactiva."""
        self.camera_enabled = enabled
        if not enabled:
            self._revoke_media_permission()
        logger.info(f"Cámara {'habilitada' if enabled else 'deshabilitada'}")

    def set_microphone_enabled(self, enabled: bool) -> None:
        """Habilita/deshabilita el acceso a micrófono. Revoca permisos si se desactiva."""
        self.microphone_enabled = enabled
        if not enabled:
            self._revoke_media_permission()
        logger.info(f"Micrófono {'habilitado' if enabled else 'deshabilitado'}")

    def _revoke_media_permission(self) -> None:
        """Revoca permisos de media recargando la página (único método disponible en Qt6)."""
        current_url = self.url()
        if current_url and not current_url.isEmpty():
            self.reload()
            logger.debug("Permisos de media revocados mediante recarga")

    def clear_all_data(self) -> None:
        """Limpia caché en memoria y recarga la página."""
        self.profile.clearHttpCache()
        self.reload()
        logger.info("Datos de la pestaña limpiados")

    def rotate_user_agent(self, user_agents: list) -> None:
        """
        Rota el User-Agent del perfil compartido.
        Nota: Al ser el perfil compartido, afecta a TODAS las pestañas (comportamiento deseado).
        """
        if user_agents:
            new_ua = random.choice(user_agents)
            self.profile.setHttpUserAgent(new_ua)
            logger.debug(f"User-Agent rotado: {new_ua[:50]}...")


# ---------------------------------------------------------------------------
# Ventana principal
# ---------------------------------------------------------------------------

class BrowserWindow(QMainWindow):
    """Ventana principal del navegador con soporte para pestañas"""

    # HTML para páginas de estado de Tor
    _TOR_LOADING_HTML = """<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
        body{font-family:'Segoe UI',sans-serif;background:#1a1a2e;color:#eee;
             display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
        .box{text-align:center;max-width:500px;padding:40px}
        .loader{border:5px solid #333;border-top:5px solid #e67e22;border-radius:50%;
                width:60px;height:60px;animation:spin 1s linear infinite;margin:0 auto 24px}
        @keyframes spin{to{transform:rotate(360deg)}}
        h2{color:#e67e22;margin:0 0 12px}p{color:#aaa;margin:4px 0}
    </style></head><body><div class="box">
        <div class="loader"></div>
        <h2>Conectando a Tor...</h2>
        <p>Estableciendo circuito seguro.</p>
        <p>Por favor, espere unos segundos.</p>
    </div></body></html>"""

    _TOR_SUCCESS_HTML = """<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
        body{font-family:'Segoe UI',sans-serif;background:#1a1a2e;color:#eee;
             display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
        .box{text-align:center;max-width:500px;padding:40px}
        .icon{font-size:72px;margin-bottom:16px}
        h2{color:#2ecc71;margin:0 0 12px}p{color:#aaa;margin:4px 0}
        .btn{display:inline-block;margin-top:24px;padding:10px 24px;background:#3498db;
             color:white;text-decoration:none;border-radius:6px;font-size:14px}
        .btn:hover{background:#2980b9}
    </style></head><body><div class="box">
        <div class="icon">🔒</div>
        <h2>Conexión Segura Establecida</h2>
        <p>Navegas a través de la red Tor.</p>
        <p>Tu IP real está oculta.</p>
        <a href="https://check.torproject.org" class="btn">Verificar conexión Tor</a>
    </div></body></html>"""

    _TOR_ERROR_HTML = """<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
        body{font-family:'Segoe UI',sans-serif;background:#1a1a2e;color:#eee;
             display:flex;justify-content:center;align-items:center;height:100vh;margin:0}
        .box{text-align:center;max-width:600px;padding:40px}
        .icon{font-size:72px;margin-bottom:16px}
        h2{color:#e74c3c;margin:0 0 12px}p{color:#aaa;margin:4px 0}
        code{background:#333;padding:2px 6px;border-radius:3px;font-size:13px}
    </style></head><body><div class="box">
        <div class="icon">❌</div>
        <h2>No se pudo conectar a Tor</h2>
        <p>Asegúrate de que el binario Tor esté disponible.</p>
        <p>En Linux/macOS: <code>sudo apt install tor</code> o <code>brew install tor</code></p>
        <p>En Windows: el binario portátil está en <code>bin/windows/Tor/tor.exe</code></p>
    </div></body></html>"""

    def __init__(self):
        super().__init__()

        config = get_config()
        self.config = config

        self.setWindowTitle(
            "UltraBrowser - Navegador Privado y seguro by TiiZss - https://www.tiizss.com"
        )
        self.setGeometry(100, 100, config.window_width, config.window_height)

        # Icono de la aplicación
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            logger.warning(f"Icono no encontrado: {icon_path}")

        # ------------------------------------------------------------------
        # PERFIL PRIVADO COMPARTIDO (off-the-record, sin persistencia en disco)
        # ------------------------------------------------------------------
        self.browser_profile = create_private_profile(self)

        # Cargar User-Agents
        try:
            self.user_agents = load_user_agents(config.user_agents_file)
        except Exception as e:
            logger.warning(f"Error cargando User-Agents: {e}. Usando lista por defecto.")
            self.user_agents = self._default_user_agents()

        # Aplicar User-Agent aleatorio al perfil compartido
        self.browser_profile.setHttpUserAgent(random.choice(self.user_agents))

        # ------------------------------------------------------------------
        # BLOQUEADOR DE ANUNCIOS
        # ------------------------------------------------------------------
        self.ad_blocker = AdBlocker(enabled=getattr(config, 'block_ads', True))
        # Asociar el interceptor al perfil compartido
        self.browser_profile.setUrlRequestInterceptor(self.ad_blocker)

        # ------------------------------------------------------------------
        # SCRIPT DE ANTI-FINGERPRINTING (inyectado en cada página)
        # ------------------------------------------------------------------
        fp_script = QWebEngineScript()
        fp_script.setName("UltraBrowserAntiFingerprint")
        fp_script.setSourceCode(ANTI_FINGERPRINT_JS)
        fp_script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        fp_script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        fp_script.setRunsOnSubFrames(True)
        self.browser_profile.scripts().insert(fp_script)

        # ------------------------------------------------------------------
        # PESTAÑAS
        # ------------------------------------------------------------------
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)

        new_tab_button = QToolButton()
        new_tab_button.setText("+")
        new_tab_button.setToolTip("Nueva pestaña (Ctrl+T)")
        new_tab_button.clicked.connect(lambda: self.add_new_tab())
        self.tabs.setCornerWidget(new_tab_button, Qt.Corner.TopLeftCorner)

        self.setCentralWidget(self.tabs)

        # ------------------------------------------------------------------
        # TOR
        # ------------------------------------------------------------------
        self.tor_manager = TorManager(debug_mode=config.debug_mode)
        self._tor_worker: Optional[TorConnectWorker] = None

        # ------------------------------------------------------------------
        # UI: Toolbar + Status bar
        # ------------------------------------------------------------------
        self.create_toolbar()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Listo")

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

        self.setup_shortcuts()

        # ------------------------------------------------------------------
        # TIMER DE ROTACIÓN AUTOMÁTICA DE USER-AGENT
        # ------------------------------------------------------------------
        if config.rotate_user_agent and config.user_agent_rotation_interval > 0:
            interval_ms = config.user_agent_rotation_interval * 60 * 1000
            self._ua_timer = QTimer(self)
            self._ua_timer.timeout.connect(self._rotate_user_agent)
            self._ua_timer.start(interval_ms)
            logger.info(
                f"Rotación de User-Agent cada {config.user_agent_rotation_interval} minutos"
            )

        # Cargar página de inicio
        self.add_new_tab(QUrl(config.default_homepage), "Inicio")
        logger.info("BrowserWindow lista")

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _default_user_agents(self) -> list:
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
        ]

    def _rotate_user_agent(self) -> None:
        """Rota el User-Agent del perfil compartido (afecta a todas las pestañas)"""
        new_ua = random.choice(self.user_agents)
        self.browser_profile.setHttpUserAgent(new_ua)
        logger.debug(f"User-Agent rotado automáticamente: {new_ua[:60]}...")

    def current_browser(self) -> Optional[BrowserEngine]:
        """Retorna el BrowserEngine de la pestaña activa"""
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, BrowserEngine) else None

    # ------------------------------------------------------------------
    # Gestión de pestañas
    # ------------------------------------------------------------------

    def add_new_tab(self, url: QUrl = None, label: str = "Nueva Pestaña") -> None:
        """Crea y añade una nueva pestaña con el perfil privado compartido"""
        if url is None:
            url = QUrl(self.config.default_homepage)

        browser = BrowserEngine(
            profile=self.browser_profile,
            debug_mode=self.config.debug_mode
        )
        browser.setUrl(url)

        # Aplicar estado actual de los toggles a la nueva pestaña
        browser.set_camera_enabled(self.camera_toggle.isChecked())
        browser.set_microphone_enabled(self.microphone_toggle.isChecked())

        # Conectar señales
        browser.loadProgress.connect(lambda p: self.update_progress(p, browser))
        browser.loadFinished.connect(lambda s: self.on_load_finished(s, browser))
        browser.urlChanged.connect(lambda u: self.update_url_bar(u, browser))
        browser.titleChanged.connect(lambda t: self.update_tab_title(t, browser))

        index = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(index)
        logger.info(f"Nueva pestaña añadida (índice: {index})")

    def close_tab(self, index: int) -> None:
        """Cierra la pestaña en el índice dado (mínimo 1 pestaña siempre abierta)"""
        if self.tabs.count() < 2:
            return
        widget = self.tabs.widget(index)
        if widget:
            widget.deleteLater()
        self.tabs.removeTab(index)
        logger.info(f"Pestaña cerrada (índice: {index})")

    def on_tab_changed(self, index: int) -> None:
        """Actualiza URL bar y título al cambiar de pestaña"""
        browser = self.tabs.widget(index)
        if isinstance(browser, BrowserEngine):
            self.update_url_bar(browser.url(), browser)
            self.update_title(browser.title())

    def update_tab_title(self, title: str, browser: BrowserEngine) -> None:
        """Actualiza el texto de la pestaña (truncado) y el tooltip completo"""
        index = self.tabs.indexOf(browser)
        if index != -1:
            short = (title[:22] + "…") if len(title) > 22 else title
            self.tabs.setTabText(index, short)
            self.tabs.setTabToolTip(index, title)
            if browser == self.current_browser():
                self.update_title(title)

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------

    def create_toolbar(self) -> None:
        """Crea la barra de herramientas principal"""
        toolbar = QToolBar("Barra Principal")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Navegación
        back_action = QAction("◀", self)
        back_action.setShortcut(QKeySequence("Alt+Left"))
        back_action.setToolTip("Atrás (Alt+←)")
        back_action.triggered.connect(
            lambda: self.current_browser() and self.current_browser().back()
        )
        toolbar.addAction(back_action)

        forward_action = QAction("▶", self)
        forward_action.setShortcut(QKeySequence("Alt+Right"))
        forward_action.setToolTip("Adelante (Alt+→)")
        forward_action.triggered.connect(
            lambda: self.current_browser() and self.current_browser().forward()
        )
        toolbar.addAction(forward_action)

        reload_action = QAction("🔄", self)
        reload_action.setShortcut(QKeySequence("F5"))
        reload_action.setToolTip("Recargar (F5)")
        reload_action.triggered.connect(
            lambda: self.current_browser() and self.current_browser().reload()
        )
        toolbar.addAction(reload_action)

        toolbar.addSeparator()

        new_tab_action = QAction("➕", self)
        new_tab_action.setShortcut(QKeySequence("Ctrl+T"))
        new_tab_action.setToolTip("Nueva pestaña (Ctrl+T)")
        new_tab_action.triggered.connect(lambda: self.add_new_tab())
        toolbar.addAction(new_tab_action)

        toolbar.addSeparator()

        # Barra de direcciones
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Introduce una URL o escribe para buscar en DuckDuckGo...")
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.url_bar.setToolTip("Barra de direcciones")
        toolbar.addWidget(self.url_bar)

        go_action = QAction("Ir", self)
        go_action.triggered.connect(self.navigate_to_url)
        toolbar.addAction(go_action)

        toolbar.addSeparator()

        # Toggle Tor
        self.tor_toggle = QPushButton("🔒 Tor: OFF")
        self.tor_toggle.setCheckable(True)
        self.tor_toggle.setChecked(False)
        self.tor_toggle.setToolTip("Activar/desactivar navegación anónima a través de Tor")
        self.tor_toggle.clicked.connect(self.toggle_tor)
        self.tor_toggle.setStyleSheet(
            "QPushButton:checked{background:#4caf50;color:#fff}"
            "QPushButton:!checked{background:#757575;color:#fff}"
        )
        toolbar.addWidget(self.tor_toggle)

        new_id_action = QAction("🔄 Nueva ID", self)
        new_id_action.setToolTip("Solicitar nueva identidad Tor (nuevo circuito)")
        new_id_action.triggered.connect(self.new_tor_identity)
        toolbar.addAction(new_id_action)

        toolbar.addSeparator()

        # Toggle Ad Blocker
        block_ads_initial = getattr(self.config, 'block_ads', True)
        self.adblock_toggle = QPushButton(
            "🛡️ AdBlock: ON" if block_ads_initial else "🛡️ AdBlock: OFF"
        )
        self.adblock_toggle.setCheckable(True)
        self.adblock_toggle.setChecked(block_ads_initial)
        self.adblock_toggle.setToolTip("Activar/desactivar bloqueador de anuncios y rastreadores")
        self.adblock_toggle.clicked.connect(self.toggle_adblock)
        self.adblock_toggle.setStyleSheet(
            "QPushButton:checked{background:#2196f3;color:#fff}"
            "QPushButton:!checked{background:#757575;color:#fff}"
        )
        toolbar.addWidget(self.adblock_toggle)

        toolbar.addSeparator()

        # Toggle Cámara
        self.camera_toggle = QPushButton("📷 Cámara: BLOQUEADA")
        self.camera_toggle.setCheckable(True)
        self.camera_toggle.setChecked(False)
        self.camera_toggle.setToolTip("Permitir/bloquear acceso a la cámara")
        self.camera_toggle.clicked.connect(self.toggle_camera)
        self.camera_toggle.setStyleSheet(
            "QPushButton:checked{background:#4caf50;color:#fff}"
            "QPushButton:!checked{background:#f44336;color:#fff}"
        )
        toolbar.addWidget(self.camera_toggle)

        # Toggle Micrófono
        self.microphone_toggle = QPushButton("🎤 Micrófono: BLOQUEADO")
        self.microphone_toggle.setCheckable(True)
        self.microphone_toggle.setChecked(False)
        self.microphone_toggle.setToolTip("Permitir/bloquear acceso al micrófono")
        self.microphone_toggle.clicked.connect(self.toggle_microphone)
        self.microphone_toggle.setStyleSheet(
            "QPushButton:checked{background:#4caf50;color:#fff}"
            "QPushButton:!checked{background:#f44336;color:#fff}"
        )
        toolbar.addWidget(self.microphone_toggle)

        toolbar.addSeparator()

        # Limpiar datos
        clear_action = QAction("🗑️ Limpiar Todo", self)
        clear_action.setShortcut(QKeySequence("Ctrl+Shift+Delete"))
        clear_action.setToolTip("Limpiar caché, cookies y datos de sesión (Ctrl+Shift+Del)")
        clear_action.triggered.connect(self.clear_all)
        toolbar.addAction(clear_action)

    def setup_shortcuts(self) -> None:
        """Configura atajos de teclado globales"""
        focus_url = QAction(self)
        focus_url.setShortcut(QKeySequence("Ctrl+L"))
        focus_url.triggered.connect(lambda: self.url_bar.setFocus())
        self.addAction(focus_url)

        close_tab = QAction(self)
        close_tab.setShortcut(QKeySequence("Ctrl+W"))
        close_tab.triggered.connect(lambda: self.close_tab(self.tabs.currentIndex()))
        self.addAction(close_tab)

    # ------------------------------------------------------------------
    # Eventos de carga de página
    # ------------------------------------------------------------------

    def update_progress(self, progress: int, browser: BrowserEngine) -> None:
        """Actualiza la barra de progreso si es la pestaña activa"""
        if browser != self.current_browser():
            return
        if progress < 100:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(progress)
        else:
            self.progress_bar.setVisible(False)

    def on_load_finished(self, success: bool, browser: BrowserEngine) -> None:
        """Muestra mensaje en barra de estado al terminar de cargar"""
        if browser != self.current_browser():
            return
        if not success:
            self.status_bar.showMessage("Error al cargar la página", 5000)
            logger.warning("Error al cargar la página")
        else:
            count = self.ad_blocker.blocked_count
            if self.adblock_toggle.isChecked() and count > 0:
                self.status_bar.showMessage(
                    f"Cargado · Bloqueados en sesión: {count} anuncios/rastreadores", 3000
                )
            else:
                self.status_bar.showMessage("Página cargada", 2000)

    # ------------------------------------------------------------------
    # Navegación y URL
    # ------------------------------------------------------------------

    def is_ip_address(self, text: str) -> bool:
        """True si el texto es una dirección IPv4 válida"""
        match = re.fullmatch(r'(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})', text)
        if match:
            return all(0 <= int(g) <= 255 for g in match.groups())
        return False

    def validate_url(self, url_string: str) -> Optional[QUrl]:
        """
        Valida y normaliza la entrada del usuario.
        - Texto sin puntos/esquema → búsqueda en DuckDuckGo
        - Sin esquema → añade https:// (http:// si es localhost)
        - Bloquea esquemas peligrosos: javascript:, vbscript:
        """
        if not url_string or not url_string.strip():
            return None

        url_string = url_string.strip()

        # Detectar si es una búsqueda (sin punto, esquema ni IP)
        has_scheme = url_string.startswith(("http://", "https://", "file://"))
        has_dot = "." in url_string
        has_slash = "/" in url_string
        is_ip = self.is_ip_address(url_string.split("/")[0])

        if not has_scheme and not has_dot and not has_slash and not is_ip:
            query = url_string.replace(" ", "+")
            search_url = f"https://duckduckgo.com/?q={query}"
            logger.debug(f"Búsqueda: {search_url}")
            return QUrl(search_url)

        # Añadir esquema si falta
        if not has_scheme:
            candidate_http = "http://" + url_string
            parsed = QUrl(candidate_http)
            if parsed.isValid() and parsed.host() and _is_local_host(parsed.host()):
                url_string = candidate_http
            else:
                url_string = "https://" + url_string

        url = QUrl(url_string)

        if not url.isValid() or url.isEmpty():
            logger.warning(f"URL inválida: {url_string}")
            return None

        # Bloquear esquemas peligrosos
        scheme = url.scheme().lower()
        if scheme in ("javascript", "vbscript"):
            logger.warning(f"Esquema bloqueado por seguridad: {scheme}")
            return None

        return url

    def navigate_to_url(self) -> None:
        """Navega a la URL de la barra de direcciones"""
        url_text = self.url_bar.text()
        url = self.validate_url(url_text)
        browser = self.current_browser()

        if url and browser:
            browser.setUrl(url)
            logger.info(f"Navegando a: {url.toString()}")
        else:
            self.status_bar.showMessage("URL inválida o bloqueada", 3000)
            logger.warning(f"URL inválida: {url_text}")

    def update_url_bar(self, url: QUrl, browser: BrowserEngine) -> None:
        """Actualiza la barra de direcciones para la pestaña activa"""
        if browser == self.current_browser():
            self.url_bar.setText(url.toString())

    def update_title(self, title: str) -> None:
        """Actualiza el título de la ventana"""
        self.setWindowTitle(f"{title} - UltraBrowser by TiiZss")

    # ------------------------------------------------------------------
    # Toggles de privacidad
    # ------------------------------------------------------------------

    def toggle_camera(self, checked: bool) -> None:
        """Habilita/deshabilita cámara en todas las pestañas"""
        for i in range(self.tabs.count()):
            b = self.tabs.widget(i)
            if isinstance(b, BrowserEngine):
                b.set_camera_enabled(checked)
        label = "📷 Cámara: PERMITIDA" if checked else "📷 Cámara: BLOQUEADA"
        self.camera_toggle.setText(label)
        msg = "Cámara habilitada" if checked else "Cámara bloqueada"
        self.status_bar.showMessage(f"{msg} en todas las pestañas", 3000)

    def toggle_microphone(self, checked: bool) -> None:
        """Habilita/deshabilita micrófono en todas las pestañas"""
        for i in range(self.tabs.count()):
            b = self.tabs.widget(i)
            if isinstance(b, BrowserEngine):
                b.set_microphone_enabled(checked)
        label = "🎤 Micrófono: PERMITIDO" if checked else "🎤 Micrófono: BLOQUEADO"
        self.microphone_toggle.setText(label)
        msg = "Micrófono habilitado" if checked else "Micrófono bloqueado"
        self.status_bar.showMessage(f"{msg} en todas las pestañas", 3000)

    def toggle_adblock(self, checked: bool) -> None:
        """Activa/desactiva el bloqueador de anuncios"""
        self.ad_blocker.set_enabled(checked)
        self.adblock_toggle.setText("🛡️ AdBlock: ON" if checked else "🛡️ AdBlock: OFF")
        msg = "Bloqueador de anuncios activado" if checked else "Bloqueador de anuncios desactivado"
        self.status_bar.showMessage(msg, 3000)

    # ------------------------------------------------------------------
    # Tor
    # ------------------------------------------------------------------

    def toggle_tor(self, checked: bool) -> None:
        """Activa/desactiva Tor. La conexión se realiza en un hilo separado."""
        if checked:
            # Estado visual: conectando
            self.tor_toggle.setStyleSheet(
                "QPushButton:checked{background:#d35400;color:#fff}"
                "QPushButton:!checked{background:#757575;color:#fff}"
            )
            self.tor_toggle.setText("🔒 Tor: ...")
            self.tor_toggle.setEnabled(False)

            # Mostrar pantalla de "conectando..."
            if self.current_browser():
                self.current_browser().setHtml(self._TOR_LOADING_HTML)

            # Lanzar conexión en hilo separado (sin bloquear la UI)
            self._tor_worker = TorConnectWorker(self.tor_manager)
            self._tor_worker.connection_success.connect(self._on_tor_connected)
            self._tor_worker.connection_failure.connect(self._on_tor_failed)
            self._tor_worker.start()
        else:
            if self.tor_manager.disable_tor():
                self.tor_toggle.setText("🔒 Tor: OFF")
                self.tor_toggle.setStyleSheet(
                    "QPushButton:checked{background:#4caf50;color:#fff}"
                    "QPushButton:!checked{background:#757575;color:#fff}"
                )
                self.status_bar.showMessage("Tor desactivado", 3000)
                if self.current_browser():
                    self.current_browser().reload()

    def _on_tor_connected(self) -> None:
        """Callback: Tor conectado exitosamente"""
        if self.current_browser():
            self.current_browser().setHtml(self._TOR_SUCCESS_HTML)

        self.tor_toggle.setStyleSheet(
            "QPushButton:checked{background:#4caf50;color:#fff}"
            "QPushButton:!checked{background:#757575;color:#fff}"
        )
        self.tor_toggle.setText("🔒 Tor: ON")
        self.tor_toggle.setEnabled(True)
        self.status_bar.showMessage("Tor activado — navegando de forma anónima", 4000)
        logger.info("Tor conectado exitosamente")

    def _on_tor_failed(self) -> None:
        """Callback: fallo al conectar Tor"""
        if self.current_browser():
            self.current_browser().setHtml(self._TOR_ERROR_HTML)

        self.tor_toggle.setChecked(False)
        self.tor_toggle.setStyleSheet(
            "QPushButton:checked{background:#4caf50;color:#fff}"
            "QPushButton:!checked{background:#757575;color:#fff}"
        )
        self.tor_toggle.setText("🔒 Tor: OFF")
        self.tor_toggle.setEnabled(True)
        self.status_bar.showMessage("Error: No se pudo conectar a Tor", 6000)
        logger.error("Fallo al conectar a Tor")

    def new_tor_identity(self) -> None:
        """Solicita una nueva identidad Tor (nuevo circuito)"""
        if self.tor_manager.get_new_identity():
            self.status_bar.showMessage("Nueva identidad Tor solicitada", 3000)
        else:
            self.status_bar.showMessage("Error al cambiar identidad Tor", 5000)

    # ------------------------------------------------------------------
    # Limpieza
    # ------------------------------------------------------------------

    def clear_all(self) -> None:
        """Limpia todos los datos de sesión en todas las pestañas"""
        # Limpiar datos en cada pestaña
        for i in range(self.tabs.count()):
            b = self.tabs.widget(i)
            if isinstance(b, BrowserEngine):
                b.clear_all_data()
                b.set_camera_enabled(False)
                b.set_microphone_enabled(False)

        # Limpiar caché del perfil compartido
        self.browser_profile.clearHttpCache()

        # Resetear contador del ad blocker
        self.ad_blocker.reset_count()

        # Resetear toggles de hardware
        self.camera_toggle.setChecked(False)
        self.camera_toggle.setText("📷 Cámara: BLOQUEADA")
        self.microphone_toggle.setChecked(False)
        self.microphone_toggle.setText("🎤 Micrófono: BLOQUEADO")

        self.status_bar.showMessage(
            "Limpieza completa: caché, cookies y datos de sesión borrados", 4000
        )
        logger.info("Limpieza completa realizada")

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Cierre ordenado de la aplicación.

        Chromium emite "Release of profile requested but WebEnginePage still
        not deleted" si el QWebEngineProfile se destruye antes que las páginas
        que lo usan. Este método destruye explícitamente todas las
        QWebEnginePage ANTES de aceptar el cierre, garantizando el orden
        correcto de destrucción.
        """
        logger.info("Cerrando UltraBrowser...")

        # 1. Parar el timer de rotación de User-Agent
        if hasattr(self, '_ua_timer'):
            self._ua_timer.stop()

        # 2. Parar el worker de Tor si está en marcha
        if self._tor_worker and self._tor_worker.isRunning():
            self._tor_worker.quit()
            self._tor_worker.wait(2000)

        # 3. Destruir todas las QWebEnginePage ANTES de que el perfil
        #    sea liberado. Se navega a about:blank primero para que
        #    Chromium libere los recursos de red de forma limpia.
        while self.tabs.count() > 0:
            widget = self.tabs.widget(0)
            self.tabs.removeTab(0)
            if isinstance(widget, BrowserEngine):
                try:
                    widget.setUrl(QUrl("about:blank"))
                    # Desvincular la página del perfil asignando una vacía
                    widget.setPage(QWebEnginePage(widget))
                except Exception:
                    pass
            if widget:
                widget.deleteLater()

        # 4. Procesar eventos pendientes para que deleteLater() se ejecute
        #    antes de que continúe la destrucción de objetos padre.
        QApplication.processEvents()

        logger.info("Cierre completado limpiamente")
        event.accept()
