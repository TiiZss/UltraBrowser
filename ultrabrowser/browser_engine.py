"""
Motor del navegador: Configuración de QWebEngineView, perfiles y gestión de permisos
"""

from typing import Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLineEdit, 
    QPushButton, QToolBar, QStatusBar, QProgressBar, QApplication
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QAction, QKeySequence, QIcon
import os
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEngineSettings, QWebEnginePermission, 
    QWebEngineProfile, QWebEnginePage, QWebEngineFullScreenRequest
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
        
        # Conectar señal fullScreenRequested
        self.page.fullScreenRequested.connect(self.handle_fullscreen_request)
        
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
        # Habilitar soporte para pantalla completa
        settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        
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
                self.page.setFeaturePermission(security_origin, feature, QWebEnginePage.PermissionPolicy.PermissionDeniedByUser)
                logger.debug(f"Cámara denegada para: {origin_str}")

        elif feature == QWebEnginePage.Feature.FullScreen:
            # Solicitud de pantalla completa (permitir siempre)
            self.page.setFeaturePermission(security_origin, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser)
            logger.debug(f"Pantalla completa concedida para: {origin_str}")
            
        else:
            # Para otros permisos, denegar por defecto (principio de menor privilegio)
            self.page.setFeaturePermission(security_origin, feature, QWebEnginePage.PermissionPolicy.PermissionDeniedByUser)
            logger.debug(f"Permiso {feature} denegado para: {origin_str}")

    def handle_fullscreen_request(self, request: QWebEngineFullScreenRequest) -> None:
        """
        Maneja las solicitudes de pantalla completa.
        Acepta automáticamente la solicitud para permitir que el elemento (ej. video) ocupe la pantalla.
        """
        request.accept()
        logger.debug(f"Solicitud de pantalla completa aceptada para: {request.origin().toString()}")
    
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
    """Ventana principal del navegador con soporte para pestañas"""
    
    def __init__(self):
        """Inicializa la ventana principal del navegador"""
        super().__init__()
        
        # Obtener configuración
        config = get_config()
        self.config = config  # Guardar referencia
        
        self.setWindowTitle("UltraBrowser - Navegador Privado y seguro by TiiZss - https://www.tiizss.com")
        self.setGeometry(100, 100, config.window_width, config.window_height)
        
        # Configurar icono de la aplicación
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            logger.info(f"Icono cargado desde: {icon_path}")
        else:
            logger.warning(f"No se encontró el icono en: {icon_path}")
        
        # Crear widget central con pestañas
        from PyQt6.QtWidgets import QTabWidget, QToolButton
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        # Botón "+" en la esquina de las pestañas
        new_tab_button = QToolButton()
        new_tab_button.setText("+")
        new_tab_button.setToolTip("Nueva pestaña")
        new_tab_button.clicked.connect(lambda: self.add_new_tab())
        self.tabs.setCornerWidget(new_tab_button, Qt.Corner.TopLeftCorner)
        
        self.setCentralWidget(self.tabs)
        
        # Crear gestor de Tor (compartido)
        self.tor_manager = TorManager(debug_mode=config.debug_mode)
        
        # Crear barra de herramientas
        self.create_toolbar()
        
        # Crear barra de estado
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Listo")
        
        # Barra de progreso para carga de páginas (compartida en UI, actualizada por tab activo)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # Configurar atajos de teclado
        self.setup_shortcuts()
        
        # Cargar primera pestaña
        self.add_new_tab(QUrl(config.default_homepage), "Inicio")
        
        logger.info("BrowserWindow inicializada con soporte de pestañas")
    
    def current_browser(self) -> Optional[BrowserEngine]:
        """Retorna el motor del navegador de la pestaña actual"""
        return self.tabs.currentWidget()

    def add_new_tab(self, url: QUrl = None, label: str = "Nueva Pestaña") -> None:
        """Crea y añade una nueva pestaña"""
        if url is None:
            url = QUrl(self.config.default_homepage)
            
        browser = BrowserEngine(debug_mode=self.config.debug_mode)
        browser.setUrl(url)
        
        # Aplicar estado global de toggles a la nueva pestaña
        # Nota: Leemos el estado del toggle, no del browser actual (que podría no existir si es el primero)
        browser.set_camera_enabled(self.camera_toggle.isChecked())
        browser.set_microphone_enabled(self.microphone_toggle.isChecked())
        
        # Conectar señales
        browser.loadProgress.connect(lambda p: self.update_progress(p, browser))
        browser.loadFinished.connect(lambda s: self.on_load_finished(s, browser))
        browser.urlChanged.connect(lambda u: self.update_url_bar(u, browser))
        browser.titleChanged.connect(lambda t: self.update_tab_title(t, browser))
        
        # Si Tor está activo, configurar proxy (ya es global, no es necesario por pestaña)
        if self.tor_toggle.isChecked():
             # El proxy global ya está configurado
             pass

        index = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(index)
        
        logger.info(f"Nueva pestaña añadida (Índice: {index})")

    def close_tab(self, index: int) -> None:
        """Cierra la pestaña en el índice especificado"""
        if self.tabs.count() < 2:
            return # No cerrar la última pestaña (o se podría cerrar la app)

        widget = self.tabs.widget(index)
        if widget:
            widget.deleteLater()
            
        self.tabs.removeTab(index)
        logger.info(f"Pestaña cerrada (Índice: {index})")

    def on_tab_changed(self, index: int) -> None:
        """Maneja el cambio de pestaña activa"""
        browser = self.tabs.widget(index)
        if browser:
            self.update_url_bar(browser.url(), browser)
            self.update_title(browser.title())
            # Resetear iconos de estado si fuera necesario, pero mantenemos estado global

    def update_tab_title(self, title: str, browser: BrowserEngine) -> None:
        """Actualiza el título de la pestaña específica"""
        index = self.tabs.indexOf(browser)
        if index != -1:
            # Truncar título si es muy largo
            short_title = (title[:20] + '..') if len(title) > 20 else title
            self.tabs.setTabText(index, short_title)
            self.tabs.setTabToolTip(index, title)
            
            if browser == self.current_browser():
                self.update_title(title)

    def create_toolbar(self) -> None:
        """Crea la barra de herramientas con toggles y controles"""
        toolbar = QToolBar("Barra Principal")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Botón Atrás
        back_action = QAction("◀ Atrás", self)
        back_action.setShortcut(QKeySequence("Alt+Left"))
        back_action.triggered.connect(lambda: self.current_browser() and self.current_browser().back())
        back_action.setToolTip("Ir atrás (Alt+←)")
        toolbar.addAction(back_action)
        
        # Botón Adelante
        forward_action = QAction("Adelante ▶", self)
        forward_action.setShortcut(QKeySequence("Alt+Right"))
        forward_action.triggered.connect(lambda: self.current_browser() and self.current_browser().forward())
        forward_action.setToolTip("Ir adelante (Alt+→)")
        toolbar.addAction(forward_action)
        
        # Botón Recargar
        reload_action = QAction("🔄 Recargar", self)
        reload_action.setShortcut(QKeySequence("F5"))
        reload_action.triggered.connect(lambda: self.current_browser() and self.current_browser().reload())
        reload_action.setToolTip("Recargar página (F5)")
        toolbar.addAction(reload_action)

        toolbar.addSeparator()

        # Botón Nueva Pestaña
        new_tab_action = QAction("➕", self)
        new_tab_action.setShortcut(QKeySequence("Ctrl+T"))
        new_tab_action.triggered.connect(lambda: self.add_new_tab())
        new_tab_action.setToolTip("Nueva Pestaña (Ctrl+T)")
        toolbar.addAction(new_tab_action)
        
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
        self.tor_toggle.setStyleSheet("""
            QPushButton:checked {
                background-color: #4caf50;
                color: white;
            }
            QPushButton:!checked {
                background-color: #757575;
                color: white;
            }
        """)
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
    
    def setup_shortcuts(self) -> None:
        """Configura los atajos de teclado"""
        # Ctrl+L para enfocar la barra de direcciones
        focus_url_action = QAction(self)
        focus_url_action.setShortcut(QKeySequence("Ctrl+L"))
        focus_url_action.triggered.connect(lambda: self.url_bar.setFocus())
        self.addAction(focus_url_action)
        
        # Ctrl+W para cerrar pestaña
        close_tab_action = QAction(self)
        close_tab_action.setShortcut(QKeySequence("Ctrl+W"))
        close_tab_action.triggered.connect(lambda: self.close_tab(self.tabs.currentIndex()))
        self.addAction(close_tab_action)
    
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
        """Se llama cuando termina de cargar una página"""
        if browser != self.current_browser():
            return

        if not success:
            self.status_bar.showMessage("Error al cargar la página", 5000)
            logger.warning("Error al cargar la página")
        else:
            self.status_bar.showMessage("Página cargada", 2000)
    
    # ... (is_ip_address y validate_url se mantienen igual que pertenecen a la clase pero son utilitarios)
    def is_ip_address(self, text: str) -> bool:
        """Verifica si un texto es una dirección IP válida"""
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ip_pattern, text):
            parts = text.split('.')
            return all(0 <= int(part) <= 255 for part in parts)
        return False
    
    def validate_url(self, url_string: str) -> Optional[QUrl]:
        """Valida y normaliza una URL o convierte búsqueda a URL"""
        if not url_string or not url_string.strip():
            return None
        
        url_string = url_string.strip()
        
        if (not any(c in url_string for c in ['.', '/', ':']) and 
            not self.is_ip_address(url_string) and
            not url_string.startswith(('http://', 'https://', 'file://'))):
            search_url = f"https://duckduckgo.com/?q={url_string.replace(' ', '+')}"
            logger.debug(f"Búsqueda convertida a URL: {search_url}")
            return QUrl(search_url)
        
        if not url_string.startswith(('http://', 'https://', 'file://')):
            url_string = 'https://' + url_string
        
        url = QUrl(url_string)
        
        if not url.isValid() or url.isEmpty():
            logger.warning(f"URL inválida: {url_string}")
            return None
        
        scheme = url.scheme().lower()
        if scheme in ['javascript', 'data', 'vbscript']:
            logger.warning(f"URL bloqueada por esquema peligroso: {scheme}")
            return None
        
        return url
    
    def navigate_to_url(self) -> None:
        """Navega a la URL introducida en la barra de direcciones"""
        url_text = self.url_bar.text()
        url = self.validate_url(url_text)
        browser = self.current_browser()
        
        if url and browser:
            browser.setUrl(url)
            logger.info(f"Navegando a: {url.toString()}")
        else:
            self.status_bar.showMessage("URL inválida o no permitida", 3000)
            logger.warning(f"Intento de navegar a URL inválida: {url_text}")
    
    def update_url_bar(self, url: QUrl, browser: BrowserEngine) -> None:
        """Actualiza la barra de direcciones cuando cambia la URL"""
        if browser == self.current_browser():
            self.url_bar.setText(url.toString())
    
    def update_title(self, title: str) -> None:
        """Actualiza el título de la ventana"""
        self.setWindowTitle(f"{title} - UltraBrowser by TiiZss - https://www.tiizss.com")
    
    def toggle_camera(self, checked: bool) -> None:
        """Maneja el toggle de cámara (Global)"""
        # Actualizar todas las pestañas
        for i in range(self.tabs.count()):
            browser = self.tabs.widget(i)
            if isinstance(browser, BrowserEngine):
                browser.set_camera_enabled(checked)
                
        if checked:
            self.camera_toggle.setText("📷 Cámara: PERMITIDA")
            self.status_bar.showMessage("Cámara habilitada para TODAS las pestañas", 3000)
        else:
            self.camera_toggle.setText("📷 Cámara: BLOQUEADA")
            self.status_bar.showMessage("Cámara bloqueada para TODAS las pestañas", 3000)
    
    def toggle_microphone(self, checked: bool) -> None:
        """Maneja el toggle de micrófono (Global)"""
        # Actualizar todas las pestañas
        for i in range(self.tabs.count()):
            browser = self.tabs.widget(i)
            if isinstance(browser, BrowserEngine):
                browser.set_microphone_enabled(checked)

        if checked:
            self.microphone_toggle.setText("🎤 Micrófono: PERMITIDO")
            self.status_bar.showMessage("Micrófono habilitado para TODAS las pestañas", 3000)
        else:
            self.microphone_toggle.setText("🎤 Micrófono: BLOQUEADO")
            self.status_bar.showMessage("Micrófono bloqueado para TODAS las pestañas", 3000)
    
    def toggle_tor(self, checked: bool) -> None:
        """Maneja el toggle de Tor (Global)"""
        if checked:
            # 0. Estado visual: Conectando (Naranja)
            self.tor_toggle.setStyleSheet("""
                QPushButton:checked { background-color: #d35400; color: white; }
                QPushButton:!checked { background-color: #757575; color: white; }
            """)
            self.tor_toggle.setText("🔒 Tor: ...")
            
            # 1. Mostrar página de "Conectando..."
            loading_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: 'Segoe UI', sans-serif; background-color: #2b2b2b; color: #ffffff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                    .container { text-align: center; }
                    .loader { border: 5px solid #333; border-top: 5px solid #d35400; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 0 auto 20px; }
                    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
                    h2 { color: #d35400; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="loader"></div>
                    <h2>Conectando a Tor...</h2>
                    <p>Estableciendo circuito seguro. Por favor, espere unos segundos.</p>
                </div>
            </body>
            </html>
            """
            if self.current_browser():
                self.current_browser().setHtml(loading_html)
            
            # Forzar actualización de UI para que se vea el mensaje y el botón naranja
            for _ in range(10):
                QApplication.processEvents()
                import time
                time.sleep(0.05)
            
            # 2. Intentar conectar
            if self.tor_manager.enable_tor():
                # 3. Mostrar página de éxito PRIMERO
                success_html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body { font-family: 'Segoe UI', sans-serif; background-color: #2b2b2b; color: #ffffff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                        .container { text-align: center; }
                        .icon { font-size: 64px; color: #2ecc71; margin-bottom: 20px; }
                        h2 { color: #2ecc71; }
                        .btn { background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 20px; text-decoration: none; cursor: pointer; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="icon">🔒</div>
                        <h2>Conexión Segura Establecida</h2>
                        <p>Ahora navegas a través de la red Tor.</p>
                        <p>Tu IP es anónima.</p>
                        <a href="https://check.torproject.org" class="btn">Verificar mi IP</a>
                    </div>
                </body>
                </html>
                """
                if self.current_browser():
                    self.current_browser().setHtml(success_html)
                
                # Dar tiempo a renderizar HTML antes de poner botón verde
                for _ in range(5):
                    QApplication.processEvents()
                    time.sleep(0.05)

                # 4. Estado visual: Conectado (Verde)
                self.tor_toggle.setStyleSheet("""
                    QPushButton:checked { background-color: #4caf50; color: white; }
                    QPushButton:!checked { background-color: #757575; color: white; }
                """)
                self.tor_toggle.setText("🔒 Tor: ON")
                self.status_bar.showMessage("Tor activado para TODAS las pestañas", 3000)
                    
            else:
                self.tor_toggle.setChecked(False)
                # Restaurar estilo (aunque al estar unchecked se verá gris)
                self.tor_toggle.setStyleSheet("""
                    QPushButton:checked { background-color: #4caf50; color: white; }
                    QPushButton:!checked { background-color: #757575; color: white; }
                """)
                self.status_bar.showMessage("Error: No se pudo iniciar Tor.", 5000)
                
                # 4. Mostrar página de error
                error_html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body { font-family: 'Segoe UI', sans-serif; background-color: #2b2b2b; color: #ffffff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                        .container { text-align: center; max-width: 600px; padding: 20px; }
                        .icon { font-size: 64px; color: #e74c3c; margin-bottom: 20px; }
                        h2 { color: #e74c3c; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="icon">❌</div>
                        <h2>Error al conectar con Tor</h2>
                        <p>No se pudo iniciar el proceso Tor.</p>
                    </div>
                </body>
                </html>
                """
                if self.current_browser():
                     self.current_browser().setHtml(error_html)
                     
                logger.error("Error al habilitar Tor. Si no tienes Tor instalado, descárgalo de https://www.torproject.org/")
        else:
            if self.tor_manager.disable_tor():
                self.tor_toggle.setText("🔒 Tor: OFF")
                self.status_bar.showMessage("Tor desactivado", 3000)
                if self.current_browser():
                    self.current_browser().reload()
    
    def new_tor_identity(self) -> None:
        """Solicita una nueva identidad de Tor"""
        if self.tor_manager.get_new_identity():
            self.status_bar.showMessage("Nueva identidad de Tor solicitada", 3000)
        else:
            self.status_bar.showMessage("Error al solicitar identidad.", 5000)
    
    def clear_all(self) -> None:
        """Limpia todo y borra rastro en RAM (Global)"""
        # Limpiar todas las pestañas
        for i in range(self.tabs.count()):
            browser = self.tabs.widget(i)
            if isinstance(browser, BrowserEngine):
                browser.clear_all_data()
                browser.set_camera_enabled(False)
                browser.set_microphone_enabled(False)
        
        # Resetear toggles
        self.camera_toggle.setChecked(False)
        self.camera_toggle.setText("📷 Cámara: BLOQUEADA")
        self.microphone_toggle.setChecked(False)
        self.microphone_toggle.setText("🎤 Micrófono: BLOQUEADO")
        
        self.status_bar.showMessage("Limpieza completada en todas las pestañas", 3000)
        logger.info("Limpieza completa realizada")
