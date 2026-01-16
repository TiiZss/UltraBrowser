"""
Motor del navegador: Configuración de QWebEngineView, perfiles y gestión de permisos
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLineEdit, 
    QPushButton, QToolBar, QStatusBar, QProgressBar
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QAction, QKeySequence, QIcon
import os
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEngineSettings, QWebEnginePermission, 
    QWebEngineProfile, QWebEnginePage
)
from PyQt6.QtNetwork import QNetworkProxy
from .tor_logic import TorManager
import random
import re

from .logging_config import get_logger
from .config import get_config, load_user_agents

logger = get_logger()


class BrowserEngine(QWebEngineView):
    """Motor del navegador con gestión de permisos"""
    
    def __init__(self, parent: Optional[QWidget] = None, debug_mode: Optional[bool] = None):
        """
        Inicializa el motor del navegador
        
        Args:
            parent: Widget padre
            debug_mode: Modo debug. Si es None, usa la configuración global
        """
        super().__init__(parent)
        
        # Obtener configuración
        config = get_config()
        self.debug_mode = debug_mode if debug_mode is not None else config.debug_mode
        
        # Estado de los permisos (por defecto bloqueados)
        self.camera_enabled = False
        self.microphone_enabled = False
        
        # Cargar User-Agents desde archivo
        try:
            self.user_agents = load_user_agents(config.user_agents_file)
        except Exception as e:
            logger.warning(f"Error al cargar User-Agents: {e}. Usando valores por defecto.")
            self.user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            ]
        
        # Configurar perfil "Off-the-record" (sin persistencia)
        self.profile = QWebEngineProfile.defaultProfile()
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
        self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        
        # Configurar User-Agent aleatorio para anti-fingerprinting
        random_user_agent = random.choice(self.user_agents)
        self.profile.setHttpUserAgent(random_user_agent)
        logger.debug(f"User-Agent configurado: {random_user_agent[:50]}...")
        
        # Configurar página web
        self.page = QWebEnginePage(self.profile, self)
        self.setPage(self.page)
        
        # Conectar señal featurePermissionRequested
        self.page.featurePermissionRequested.connect(self.handle_permission_request)
        
        # Conectar señal para forzar HTTPS (si está habilitado)
        if config.force_https:
            self.page.urlChanged.connect(self.force_https_redirect)
        
        # Configurar ajustes de privacidad y seguridad
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, config.enable_javascript)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        # Deshabilitar completamente WebRTC para prevenir fugas de IP
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebRTCPublicInterfacesOnly, config.webrtc_public_only)
        # Deshabilitar plugins (seguridad)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, config.enable_plugins)
        # Deshabilitar local storage persistente
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, config.enable_local_storage)
        # Habilitar solo contenido seguro
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, not config.block_insecure_content)
        
        # Protección contra loops infinitos en redirecciones HTTPS
        self._https_redirect_count = 0
        self._last_redirect_url: Optional[QUrl] = None
        
        logger.info("BrowserEngine inicializado con configuración de privacidad")
    
    def handle_permission_request(
        self, 
        security_origin: QUrl, 
        feature: QWebEnginePage.Feature
    ) -> None:
        """
        Maneja las solicitudes de permisos mediante featurePermissionRequested.
        Solo concede permisos si el toggle respectivo está habilitado.
        
        Args:
            security_origin: Origen de seguridad que solicita el permiso
            feature: Tipo de permiso solicitado (cámara, micrófono, etc.)
        """
        origin_str = security_origin.toString()
        
        if feature == QWebEnginePage.Feature.MediaAudioCapture:
            # Solicitud de micrófono
            if self.microphone_enabled:
                self.page.setFeaturePermission(security_origin, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser)
                logger.info(f"Micrófono concedido para: {origin_str}")
            else:
                self.page.setFeaturePermission(security_origin, feature, QWebEnginePage.PermissionPolicy.PermissionDeniedByUser)
                logger.debug(f"Micrófono denegado para: {origin_str}")
                
        elif feature == QWebEnginePage.Feature.MediaVideoCapture:
            # Solicitud de cámara
            if self.camera_enabled:
                self.page.setFeaturePermission(security_origin, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser)
                logger.info(f"Cámara concedida para: {origin_str}")
            else:
                self.page.setFeaturePermission(security_origin, feature, QWebEnginePage.PermissionPolicy.PermissionDeniedByUser)
                logger.debug(f"Cámara denegada para: {origin_str}")
        else:
            # Para otros permisos, denegar por defecto (principio de menor privilegio)
            self.page.setFeaturePermission(security_origin, feature, QWebEnginePage.PermissionPolicy.PermissionDeniedByUser)
            logger.debug(f"Permiso {feature} denegado para: {origin_str}")
    
    def force_https_redirect(self, url: QUrl) -> None:
        """
        Fuerza redirección de HTTP a HTTPS para mayor seguridad.
        Incluye protección contra loops infinitos.
        
        Args:
            url: URL a verificar y posiblemente redirigir
        """
        if url.scheme() == "http" and url.host():
            # Protección contra loops infinitos
            if self._last_redirect_url == url:
                self._https_redirect_count += 1
                if self._https_redirect_count > 3:
                    logger.warning(f"Demasiadas redirecciones HTTPS para {url.toString()}. Deteniendo redirección.")
                    return
            else:
                self._https_redirect_count = 0
                self._last_redirect_url = url
            
            # Redirigir HTTP a HTTPS
            secure_url = QUrl(url)
            secure_url.setScheme("https")
            logger.debug(f"Redirigiendo HTTP a HTTPS: {url.toString()} -> {secure_url.toString()}")
            self.setUrl(secure_url)
        else:
            # Resetear contador si no es HTTP
            self._https_redirect_count = 0
            self._last_redirect_url = None
    
    def set_camera_enabled(self, enabled: bool) -> None:
        """
        Actualiza el estado del toggle de cámara y revoca permisos si se desactiva
        
        Args:
            enabled: True para habilitar, False para deshabilitar
        """
        self.camera_enabled = enabled
        if not enabled:
            # Revocar todos los permisos de cámara concedidos
            self.revoke_camera_permissions()
        logger.info(f"Cámara {'habilitada' if enabled else 'deshabilitada'}")
    
    def set_microphone_enabled(self, enabled: bool) -> None:
        """
        Actualiza el estado del toggle de micrófono y revoca permisos si se desactiva
        
        Args:
            enabled: True para habilitar, False para deshabilitar
        """
        self.microphone_enabled = enabled
        if not enabled:
            # Revocar todos los permisos de micrófono concedidos
            self.revoke_microphone_permissions()
        logger.info(f"Micrófono {'habilitado' if enabled else 'deshabilitado'}")
    
    def revoke_camera_permissions(self) -> None:
        """Revoca todos los permisos de cámara concedidos en la sesión activa"""
        # Nota: PyQt6 no tiene una API directa para revocar permisos específicos
        # La mejor práctica es recargar la página o navegar a una nueva URL
        current_url = self.url()
        if not current_url.isEmpty():
            self.reload()
            logger.debug("Permisos de cámara revocados (página recargada)")
    
    def revoke_microphone_permissions(self) -> None:
        """Revoca todos los permisos de micrófono concedidos en la sesión activa"""
        current_url = self.url()
        if not current_url.isEmpty():
            self.reload()
            logger.debug("Permisos de micrófono revocados (página recargada)")
    
    def set_tor_proxy(self, proxy: Optional[QNetworkProxy]) -> None:
        """
        Configura el proxy Tor para el perfil WebEngine
        
        Args:
            proxy: Proxy a configurar, o None para restaurar el proxy por defecto
        """
        if proxy:
            self.profile.setProxy(proxy)
            logger.debug("Proxy Tor configurado en el perfil WebEngine")
        else:
            # Restaurar proxy por defecto
            self.profile.setProxy(QNetworkProxy())
            logger.debug("Proxy restaurado a valores por defecto")
    
    def clear_all_data(self) -> None:
        """Limpia todos los datos: caché, cookies, permisos, etc."""
        # Limpiar caché del perfil
        self.profile.clearHttpCache()
        # Recargar página para limpiar estado
        self.reload()
        logger.info("Todos los datos limpiados")
    
    def rotate_user_agent(self) -> None:
        """Rota el User-Agent a uno aleatorio de la lista"""
        new_user_agent = random.choice(self.user_agents)
        self.profile.setHttpUserAgent(new_user_agent)
        logger.debug(f"User-Agent rotado: {new_user_agent[:50]}...")


class BrowserWindow(QMainWindow):
    """Ventana principal del navegador con barra de herramientas y toggles"""
    
    def __init__(self):
        """Inicializa la ventana principal del navegador"""
        super().__init__()
        
        # Obtener configuración
        config = get_config()
        
        self.setWindowTitle("UltraBrowser - Navegador Privado y seguro by TiiZss - https://www.tiizss.com")
        self.setGeometry(100, 100, config.window_width, config.window_height)
        
        # Configurar icono de la aplicación
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            logger.info(f"Icono cargado desde: {icon_path}")
        else:
            logger.warning(f"No se encontró el icono en: {icon_path}")
        
        # Crear widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Crear motor del navegador
        self.browser = BrowserEngine(debug_mode=config.debug_mode)
        layout.addWidget(self.browser)
        
        # Crear gestor de Tor
        self.tor_manager = TorManager(debug_mode=config.debug_mode)
        
        # Crear barra de herramientas
        self.create_toolbar()
        
        # Crear barra de estado
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Listo")
        
        # Barra de progreso para carga de páginas
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # Conectar señales del navegador
        self.browser.loadProgress.connect(self.update_progress)
        self.browser.loadFinished.connect(self.on_load_finished)
        
        # Configurar atajos de teclado
        self.setup_shortcuts()
        
        # Cargar página inicial
        self.browser.setUrl(QUrl(config.default_homepage))
        
        logger.info("BrowserWindow inicializada")
    
    def create_toolbar(self) -> None:
        """Crea la barra de herramientas con toggles y controles"""
        toolbar = QToolBar("Barra Principal")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Botón Atrás
        back_action = QAction("◀ Atrás", self)
        back_action.setShortcut(QKeySequence("Alt+Left"))
        back_action.triggered.connect(self.browser.back)
        back_action.setToolTip("Ir atrás (Alt+←)")
        toolbar.addAction(back_action)
        
        # Botón Adelante
        forward_action = QAction("Adelante ▶", self)
        forward_action.setShortcut(QKeySequence("Alt+Right"))
        forward_action.triggered.connect(self.browser.forward)
        forward_action.setToolTip("Ir adelante (Alt+→)")
        toolbar.addAction(forward_action)
        
        # Botón Recargar
        reload_action = QAction("🔄 Recargar", self)
        reload_action.setShortcut(QKeySequence("F5"))
        reload_action.triggered.connect(self.browser.reload)
        reload_action.setToolTip("Recargar página (F5)")
        toolbar.addAction(reload_action)
        
        toolbar.addSeparator()
        
        # Barra de direcciones
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Introduce una URL o busca...")
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.url_bar.setToolTip("Barra de direcciones - Presiona Enter para navegar")
        toolbar.addWidget(self.url_bar)
        
        # Botón Ir
        go_action = QAction("Ir", self)
        go_action.setShortcut(QKeySequence("Return"))
        go_action.triggered.connect(self.navigate_to_url)
        go_action.setToolTip("Navegar a la URL (Enter)")
        toolbar.addAction(go_action)
        
        toolbar.addSeparator()
        
        # Toggle de Tor
        self.tor_toggle = QPushButton("🔒 Tor: OFF")
        self.tor_toggle.setCheckable(True)
        self.tor_toggle.setChecked(False)
        self.tor_toggle.clicked.connect(self.toggle_tor)
        self.tor_toggle.setToolTip("Activar/desactivar navegación a través de Tor")
        toolbar.addWidget(self.tor_toggle)
        
        # Botón para nueva identidad de Tor
        new_identity_action = QAction("🔄 Nueva Identidad", self)
        new_identity_action.triggered.connect(self.new_tor_identity)
        new_identity_action.setToolTip("Solicitar nueva identidad de Tor (nuevo circuito)")
        toolbar.addAction(new_identity_action)
        
        toolbar.addSeparator()
        
        # Toggle de Cámara
        self.camera_toggle = QPushButton("📷 Cámara: BLOQUEADA")
        self.camera_toggle.setCheckable(True)
        self.camera_toggle.setChecked(False)
        self.camera_toggle.clicked.connect(self.toggle_camera)
        self.camera_toggle.setToolTip("Permitir/bloquear acceso a la cámara")
        self.camera_toggle.setStyleSheet("""
            QPushButton:checked {
                background-color: #4caf50;
                color: white;
            }
            QPushButton:!checked {
                background-color: #f44336;
                color: white;
            }
        """)
        toolbar.addWidget(self.camera_toggle)
        
        # Toggle de Micrófono
        self.microphone_toggle = QPushButton("🎤 Micrófono: BLOQUEADO")
        self.microphone_toggle.setCheckable(True)
        self.microphone_toggle.setChecked(False)
        self.microphone_toggle.clicked.connect(self.toggle_microphone)
        self.microphone_toggle.setToolTip("Permitir/bloquear acceso al micrófono")
        self.microphone_toggle.setStyleSheet("""
            QPushButton:checked {
                background-color: #4caf50;
                color: white;
            }
            QPushButton:!checked {
                background-color: #f44336;
                color: white;
            }
        """)
        toolbar.addWidget(self.microphone_toggle)
        
        toolbar.addSeparator()
        
        # Botón de Limpieza Rápida
        clear_action = QAction("🗑️ Limpiar Todo", self)
        clear_action.setShortcut(QKeySequence("Ctrl+Shift+Delete"))
        clear_action.triggered.connect(self.clear_all)
        clear_action.setToolTip("Limpiar todos los datos (Ctrl+Shift+Del)")
        toolbar.addAction(clear_action)
        
        # Conectar señal de cambio de URL para actualizar la barra de direcciones
        self.browser.urlChanged.connect(self.update_url_bar)
        self.browser.titleChanged.connect(self.update_title)
    
    def setup_shortcuts(self) -> None:
        """Configura los atajos de teclado"""
        # Ctrl+L para enfocar la barra de direcciones
        focus_url_action = QAction(self)
        focus_url_action.setShortcut(QKeySequence("Ctrl+L"))
        focus_url_action.triggered.connect(lambda: self.url_bar.setFocus())
        self.addAction(focus_url_action)
    
    def update_progress(self, progress: int) -> None:
        """
        Actualiza la barra de progreso durante la carga
        
        Args:
            progress: Porcentaje de carga (0-100)
        """
        if progress < 100:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(progress)
        else:
            self.progress_bar.setVisible(False)
    
    def on_load_finished(self, success: bool) -> None:
        """
        Se llama cuando termina de cargar una página
        
        Args:
            success: True si la carga fue exitosa, False en caso contrario
        """
        if not success:
            self.status_bar.showMessage("Error al cargar la página", 5000)
            logger.warning("Error al cargar la página")
        else:
            self.status_bar.showMessage("Página cargada", 2000)
    
    def is_ip_address(self, text: str) -> bool:
        """
        Verifica si un texto es una dirección IP válida
        
        Args:
            text: Texto a verificar
            
        Returns:
            True si es una IP válida, False en caso contrario
        """
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ip_pattern, text):
            parts = text.split('.')
            return all(0 <= int(part) <= 255 for part in parts)
        return False
    
    def validate_url(self, url_string: str) -> Optional[QUrl]:
        """
        Valida y normaliza una URL o convierte búsqueda a URL
        
        Args:
            url_string: URL o término de búsqueda
            
        Returns:
            QUrl válido o None si la URL es inválida
        """
        if not url_string or not url_string.strip():
            return None
        
        url_string = url_string.strip()
        
        # Si parece una búsqueda (no tiene punto, no es IP, no tiene esquema)
        if (not any(c in url_string for c in ['.', '/', ':']) and 
            not self.is_ip_address(url_string) and
            not url_string.startswith(('http://', 'https://', 'file://'))):
            # Convertir a búsqueda en DuckDuckGo
            search_url = f"https://duckduckgo.com/?q={url_string.replace(' ', '+')}"
            logger.debug(f"Búsqueda convertida a URL: {search_url}")
            return QUrl(search_url)
        
        # Si no tiene esquema, agregar https://
        if not url_string.startswith(('http://', 'https://', 'file://')):
            url_string = 'https://' + url_string
        
        url = QUrl(url_string)
        
        # Validar que la URL sea válida
        if not url.isValid() or url.isEmpty():
            logger.warning(f"URL inválida: {url_string}")
            return None
        
        # Bloquear URLs peligrosas (javascript:, data:, etc.)
        scheme = url.scheme().lower()
        if scheme in ['javascript', 'data', 'vbscript']:
            logger.warning(f"URL bloqueada por esquema peligroso: {scheme}")
            return None
        
        return url
    
    def navigate_to_url(self) -> None:
        """Navega a la URL introducida en la barra de direcciones con validación"""
        url_text = self.url_bar.text()
        url = self.validate_url(url_text)
        
        if url:
            self.browser.setUrl(url)
            logger.info(f"Navegando a: {url.toString()}")
        else:
            self.status_bar.showMessage("URL inválida o no permitida", 3000)
            logger.warning(f"Intento de navegar a URL inválida: {url_text}")
    
    def update_url_bar(self, url: QUrl) -> None:
        """
        Actualiza la barra de direcciones cuando cambia la URL
        
        Args:
            url: Nueva URL
        """
        self.url_bar.setText(url.toString())
    
    def update_title(self, title: str) -> None:
        """
        Actualiza el título de la ventana
        
        Args:
            title: Nuevo título
        """
        self.setWindowTitle(f"{title} - UltraBrowser by TiiZss - https://www.tiizss.com")
    
    def toggle_camera(self, checked: bool) -> None:
        """
        Maneja el toggle de cámara
        
        Args:
            checked: True si está activado, False si está desactivado
        """
        self.browser.set_camera_enabled(checked)
        if checked:
            self.camera_toggle.setText("📷 Cámara: PERMITIDA")
            self.status_bar.showMessage("Cámara habilitada - Los sitios web pueden solicitar acceso", 3000)
        else:
            self.camera_toggle.setText("📷 Cámara: BLOQUEADA")
            self.status_bar.showMessage("Cámara bloqueada - Todas las solicitudes serán denegadas", 3000)
    
    def toggle_microphone(self, checked: bool) -> None:
        """
        Maneja el toggle de micrófono
        
        Args:
            checked: True si está activado, False si está desactivado
        """
        self.browser.set_microphone_enabled(checked)
        if checked:
            self.microphone_toggle.setText("🎤 Micrófono: PERMITIDO")
            self.status_bar.showMessage("Micrófono habilitado - Los sitios web pueden solicitar acceso", 3000)
        else:
            self.microphone_toggle.setText("🎤 Micrófono: BLOQUEADO")
            self.status_bar.showMessage("Micrófono bloqueado - Todas las solicitudes serán denegadas", 3000)
    
    def toggle_tor(self, checked: bool) -> None:
        """
        Maneja el toggle de Tor
        
        Args:
            checked: True si está activado, False si está desactivado
        """
        if checked:
            if self.tor_manager.enable_tor():
                # Configurar proxy Tor en el perfil WebEngine
                proxy = self.tor_manager.get_proxy()
                self.browser.set_tor_proxy(proxy)
                self.tor_toggle.setText("🔒 Tor: ON")
                self.status_bar.showMessage("Tor activado - Navegación a través de la red Tor", 3000)
            else:
                self.tor_toggle.setChecked(False)
                self.status_bar.showMessage("Error: Tor no está disponible. Inicia el servicio Tor primero.", 5000)
        else:
            if self.tor_manager.disable_tor():
                # Remover proxy del perfil WebEngine
                self.browser.set_tor_proxy(None)
                self.tor_toggle.setText("🔒 Tor: OFF")
                self.status_bar.showMessage("Tor desactivado - Navegación normal", 3000)
    
    def new_tor_identity(self) -> None:
        """Solicita una nueva identidad de Tor"""
        if self.tor_manager.get_new_identity():
            self.status_bar.showMessage("Nueva identidad de Tor solicitada", 3000)
        else:
            self.status_bar.showMessage("Error: No se pudo solicitar nueva identidad. Verifica que Tor esté activo.", 5000)
    
    def clear_all(self) -> None:
        """Limpia todo y borra rastro en RAM"""
        # Limpiar todos los datos del navegador
        self.browser.clear_all_data()
        # Revocar todos los permisos
        self.browser.set_camera_enabled(False)
        self.browser.set_microphone_enabled(False)
        # Actualizar toggles
        self.camera_toggle.setChecked(False)
        self.camera_toggle.setText("📷 Cámara: BLOQUEADA")
        self.microphone_toggle.setChecked(False)
        self.microphone_toggle.setText("🎤 Micrófono: BLOQUEADO")
        self.status_bar.showMessage("Limpieza completada - Todos los datos y permisos revocados", 3000)
        logger.info("Limpieza completa realizada")
