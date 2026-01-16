"""
Gestión de conexión Tor: Configuración SOCKS5 y comunicación con el proceso Tor
"""

from typing import Optional
from PyQt6.QtNetwork import QNetworkProxy
from stem.control import Controller
from stem import Signal
import socket
import time

from .exceptions import (
    TorNotRunningError,
    TorProxyError,
    TorAuthenticationError,
    TorConnectionError
)
from .logging_config import get_logger
from .config import get_config, TorConfig

logger = get_logger()


class TorManager:
    """Gestiona la conexión y configuración de Tor"""
    
    def __init__(self, tor_config: Optional[TorConfig] = None, debug_mode: Optional[bool] = None):
        """
        Inicializa el gestor de Tor
        
        Args:
            tor_config: Configuración de Tor. Si es None, usa la configuración global
            debug_mode: Modo debug. Si es None, usa la configuración global
        """
        self.controller: Optional[Controller] = None
        self.tor_enabled = False
        
        # Obtener configuración
        config = get_config()
        self.tor_config = tor_config or config.tor
        self.debug_mode = debug_mode if debug_mode is not None else config.debug_mode
        
        # Configurar proxy SOCKS5 para Tor
        self.proxy = QNetworkProxy()
        self.proxy.setType(QNetworkProxy.ProxyType.Socks5Proxy)
        self.proxy.setHostName(self.tor_config.host)
        self.proxy.setPort(self.tor_config.socks_port)
        # Nota: Las consultas DNS también pasarán por Tor con SOCKS5
        
        logger.debug(f"TorManager inicializado - Host: {self.tor_config.host}, Port: {self.tor_config.socks_port}")
    
    def is_tor_running(self) -> bool:
        """
        Verifica si el servicio Tor está activo
        
        Returns:
            True si Tor está ejecutándose, False en caso contrario
            
        Raises:
            TorNotRunningError: Si Tor no está disponible
            TorAuthenticationError: Si hay error de autenticación
        """
        try:
            controller = Controller.from_port(port=self.tor_config.control_port)
            controller.authenticate()
            controller.close()
            logger.debug("Tor está ejecutándose correctamente")
            return True
        except (ConnectionRefusedError, OSError) as e:
            logger.warning(f"Tor no está disponible en el puerto {self.tor_config.control_port}: {e}")
            if self.debug_mode:
                raise TorNotRunningError(f"Tor no está ejecutándose: {e}") from e
            return False
        except Exception as e:
            # Intentar identificar si es error de autenticación
            error_str = str(e).lower()
            if 'authentication' in error_str or 'password' in error_str:
                logger.error(f"Error de autenticación con Tor: {e}")
                if self.debug_mode:
                    raise TorAuthenticationError(f"Error de autenticación: {e}") from e
            else:
                logger.error(f"Error inesperado al verificar Tor: {e}")
                if self.debug_mode:
                    raise TorConnectionError(f"Error inesperado: {e}") from e
            return False
    
    def get_proxy(self) -> QNetworkProxy:
        """
        Retorna el objeto proxy configurado para Tor
        
        Returns:
            Objeto QNetworkProxy configurado para SOCKS5
        """
        return self.proxy
    
    def verify_tor_connection(self) -> bool:
        """
        Verifica que Tor esté completamente funcional (control y proxy SOCKS5)
        
        Returns:
            True si Tor está completamente funcional, False en caso contrario
        """
        # 1. Verificar puerto de control
        if not self.is_tor_running():
            return False
        
        # 2. Verificar proxy SOCKS5
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.tor_config.host, self.tor_config.socks_port))
            sock.close()
            if result == 0:
                logger.debug(f"Proxy SOCKS5 verificado en {self.tor_config.host}:{self.tor_config.socks_port}")
                return True
            else:
                logger.warning(f"Proxy SOCKS5 no disponible en {self.tor_config.host}:{self.tor_config.socks_port}")
                return False
        except Exception as e:
            logger.error(f"Error al verificar proxy SOCKS5: {e}")
            return False
    
    def enable_tor(self) -> bool:
        """
        Habilita el proxy Tor con verificación completa
        
        Returns:
            True si Tor se habilitó correctamente, False en caso contrario
        """
        if not self.verify_tor_connection():
            logger.warning("Tor no está disponible. Por favor, inicia el servicio Tor.")
            return False
        
        try:
            # Configurar proxy global (para otras conexiones de Qt)
            QNetworkProxy.setApplicationProxy(self.proxy)
            self.tor_enabled = True
            logger.info(f"Tor habilitado - Proxy SOCKS5 configurado en {self.tor_config.host}:{self.tor_config.socks_port}")
            return True
        except Exception as e:
            logger.error(f"Error al habilitar Tor: {e}")
            if self.debug_mode:
                raise TorProxyError(f"Error al configurar proxy: {e}") from e
            return False
    
    def disable_tor(self) -> bool:
        """
        Deshabilita el proxy Tor
        
        Returns:
            True si se deshabilitó correctamente, False en caso contrario
        """
        try:
            # Restaurar proxy por defecto (sin proxy)
            QNetworkProxy.setApplicationProxy(QNetworkProxy(QNetworkProxy.ProxyType.NoProxy))
            self.tor_enabled = False
            logger.info("Tor deshabilitado")
            return True
        except Exception as e:
            logger.error(f"Error al deshabilitar Tor: {e}")
            if self.debug_mode:
                raise TorProxyError(f"Error al deshabilitar proxy: {e}") from e
            return False
    
    def get_new_identity(self) -> bool:
        """
        Solicita una nueva identidad de Tor (nuevo circuito)
        
        Returns:
            True si se solicitó correctamente, False en caso contrario
        """
        if not self.tor_enabled:
            logger.warning("No se puede solicitar nueva identidad: Tor no está habilitado")
            return False
        
        try:
            controller = Controller.from_port(port=self.tor_config.control_port)
            controller.authenticate()
            controller.signal(Signal.NEWNYM)
            controller.close()
            logger.info("Nueva identidad de Tor solicitada")
            return True
        except Exception as e:
            logger.error(f"Error al solicitar nueva identidad: {e}")
            if self.debug_mode:
                raise TorConnectionError(f"Error al solicitar nueva identidad: {e}") from e
            return False
    
    def get_current_ip(self) -> Optional[str]:
        """
        Obtiene la IP actual a través de Tor (requiere conexión activa)
        
        Returns:
            IP actual a través de Tor, o None si hay error
        """
        if not self.tor_enabled:
            logger.warning("No se puede obtener IP: Tor no está habilitado")
            return None
        
        try:
            # Crear socket a través del proxy Tor
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.tor_config.timeout)
            sock.connect((self.tor_config.host, self.tor_config.socks_port))
            
            # Enviar solicitud HTTP a través del proxy
            request = b"GET http://check.torproject.org/api/ip HTTP/1.1\r\nHost: check.torproject.org\r\n\r\n"
            sock.sendall(request)
            
            response = sock.recv(4096).decode()
            sock.close()
            
            # Extraer IP de la respuesta (simplificado)
            if "IP" in response:
                logger.debug("IP obtenida a través de Tor")
                return response
            logger.warning("No se pudo extraer IP de la respuesta")
            return None
        except socket.timeout:
            logger.error(f"Timeout al obtener IP (timeout: {self.tor_config.timeout}s)")
            return None
        except Exception as e:
            logger.error(f"Error al obtener IP: {e}")
            return None
