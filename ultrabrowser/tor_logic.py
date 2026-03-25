"""
Gestión de conexión Tor: Configuración SOCKS5 y comunicación con el proceso Tor
"""

from typing import Optional
from PyQt6.QtNetwork import QNetworkProxy
from stem.control import Controller
from stem import Signal
import stem.process
import socket
import time
from pathlib import Path
import os
import platform
import sys

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

    def __init__(
        self,
        tor_config: Optional[TorConfig] = None,
        debug_mode: Optional[bool] = None
    ):
        """
        Inicializa el gestor de Tor.

        Args:
            tor_config: Configuración de Tor. Si es None, usa la configuración global.
            debug_mode: Modo debug. Si es None, usa la configuración global.
        """
        self.controller: Optional[Controller] = None
        self.tor_enabled = False
        self._tor_process = None

        # Obtener configuración
        config = get_config()
        self.tor_config = tor_config or config.tor
        self.debug_mode = debug_mode if debug_mode is not None else config.debug_mode

        # Configurar proxy SOCKS5 para Tor
        # Con SOCKS5, las consultas DNS también pasan por Tor (sin fugas de DNS)
        self.proxy = QNetworkProxy()
        self.proxy.setType(QNetworkProxy.ProxyType.Socks5Proxy)
        self.proxy.setHostName(self.tor_config.host)
        self.proxy.setPort(self.tor_config.socks_port)

        logger.debug(
            f"TorManager inicializado — Host: {self.tor_config.host}, "
            f"SOCKS5: {self.tor_config.socks_port}"
        )

    def is_tor_running(self) -> bool:
        """
        Verifica si el servicio Tor está activo mediante el puerto de control.

        Returns:
            True si Tor está ejecutándose, False en caso contrario.
        """
        try:
            controller = Controller.from_port(port=self.tor_config.control_port)
            controller.authenticate()
            controller.close()
            logger.debug("Tor está ejecutándose correctamente")
            return True
        except (ConnectionRefusedError, OSError) as e:
            logger.warning(f"Tor no disponible en puerto {self.tor_config.control_port}: {e}")
            if self.debug_mode:
                raise TorNotRunningError(f"Tor no está ejecutándose: {e}") from e
            return False
        except Exception as e:
            error_str = str(e).lower()
            if "authentication" in error_str or "password" in error_str:
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
        Retorna el objeto proxy configurado para Tor.

        Returns:
            QNetworkProxy configurado como SOCKS5 apuntando a Tor.
        """
        return self.proxy

    def verify_tor_connection(self) -> bool:
        """
        Verifica que Tor esté completamente funcional (control + proxy SOCKS5).

        Returns:
            True si ambos servicios responden correctamente.
        """
        if not self.is_tor_running():
            return False

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.tor_config.host, self.tor_config.socks_port))
            sock.close()
            if result == 0:
                logger.debug(
                    f"Proxy SOCKS5 verificado en "
                    f"{self.tor_config.host}:{self.tor_config.socks_port}"
                )
                return True
            else:
                logger.warning(
                    f"Proxy SOCKS5 no disponible en "
                    f"{self.tor_config.host}:{self.tor_config.socks_port}"
                )
                return False
        except Exception as e:
            logger.error(f"Error al verificar proxy SOCKS5: {e}")
            return False

    def enable_tor(self) -> bool:
        """
        Habilita el proxy Tor con verificación completa.
        Si Tor no está corriendo, intenta iniciarlo.

        Returns:
            True si Tor se habilitó correctamente, False en caso contrario.
        """
        try:
            if not self.is_tor_running():
                logger.info("Tor no está corriendo. Intentando iniciar proceso...")
                if not self.launch_tor():
                    logger.error("No se pudo iniciar el proceso Tor")
                    return False

            if not self.verify_tor_connection():
                logger.warning("Tor no disponible incluso después de intentar iniciarlo.")
                return False

            # Configurar proxy global para Qt (afecta a QWebEngine)
            QNetworkProxy.setApplicationProxy(self.proxy)
            self.tor_enabled = True
            logger.info(
                f"Tor habilitado — Proxy SOCKS5 en "
                f"{self.tor_config.host}:{self.tor_config.socks_port}"
            )
            return True
        except Exception as e:
            logger.error(f"Error al habilitar Tor: {e}")
            if self.debug_mode:
                raise TorProxyError(f"Error al configurar proxy: {e}") from e
            return False

    def launch_tor(self) -> bool:
        """
        Intenta iniciar el proceso de Tor (binario portátil o del sistema).

        Returns:
            True si se inició correctamente, False en caso contrario.
        """
        try:
            logger.info("Iniciando proceso Tor...")

            tor_cmd = "tor"  # Por defecto, usar el Tor del PATH del sistema

            # 1. Comprobar ruta configurada por el usuario
            if self.tor_config.tor_binary_path:
                path = Path(self.tor_config.tor_binary_path)
                if not path.is_absolute():
                    path = Path.cwd() / path
                if path.exists():
                    tor_cmd = str(path.absolute())
                    logger.info(f"Usando binario Tor configurado: {tor_cmd}")
                else:
                    logger.warning(
                        f"Binario configurado no encontrado: {path}. "
                        "Intentando autodetección."
                    )

            # 2. Autodetectar binario portátil incluido en el proyecto
            if tor_cmd == "tor":
                system = platform.system()
                base_path = Path.cwd() / "bin"
                bundled_map = {
                    "Windows": base_path / "windows" / "Tor" / "tor.exe",
                    "Linux":   base_path / "linux"   / "Tor" / "tor",
                    "Darwin":  base_path / "macos"   / "Tor" / "tor",
                }
                bundled_path = bundled_map.get(system)
                if bundled_path and bundled_path.exists():
                    # En Linux/macOS asegurarse de que el binario sea ejecutable
                    if system in ("Linux", "Darwin"):
                        bundled_path.chmod(bundled_path.stat().st_mode | 0o111)
                    tor_cmd = str(bundled_path.absolute())
                    logger.info(f"Usando binario Tor portátil ({system}): {tor_cmd}")

            # 3. Directorio de datos
            data_dir = Path.cwd() / "bin" / "tor_data"
            data_dir.mkdir(parents=True, exist_ok=True)

            tor_config = {
                "SocksPort": str(self.tor_config.socks_port),
                "ControlPort": str(self.tor_config.control_port),
                "DataDirectory": str(data_dir),
                # Sin cifrado de cookie de control (más sencillo para uso portátil)
                "CookieAuthentication": "0",
            }

            self._tor_process = stem.process.launch_tor_with_config(
                config=tor_config,
                init_msg_handler=lambda line: logger.debug(f"Tor: {line}"),
                take_ownership=False,
                completion_percent=100,
                tor_cmd=tor_cmd,
            )
            logger.info("Proceso Tor iniciado correctamente")
            return True

        except OSError as e:
            logger.error(f"Error al iniciar Tor: {e}")
            logger.error(
                "Asegúrate de que Tor esté instalado en el sistema o que el binario "
                "portátil esté en bin/<plataforma>/Tor/tor"
            )
            return False
        except Exception as e:
            logger.error(f"Error inesperado al iniciar Tor: {e}")
            return False

    def disable_tor(self) -> bool:
        """
        Deshabilita el proxy Tor, restaurando la conexión directa.

        Returns:
            True si se deshabilitó correctamente, False en caso contrario.
        """
        try:
            QNetworkProxy.setApplicationProxy(
                QNetworkProxy(QNetworkProxy.ProxyType.NoProxy)
            )
            self.tor_enabled = False
            logger.info("Tor deshabilitado — conexión directa restaurada")
            return True
        except Exception as e:
            logger.error(f"Error al deshabilitar Tor: {e}")
            if self.debug_mode:
                raise TorProxyError(f"Error al deshabilitar proxy: {e}") from e
            return False

    def get_new_identity(self) -> bool:
        """
        Solicita una nueva identidad de Tor (nuevo circuito).
        Cambia la IP visible para la sesión actual.

        Returns:
            True si se solicitó correctamente, False en caso contrario.
        """
        if not self.tor_enabled:
            logger.warning("No se puede cambiar identidad: Tor no está habilitado")
            return False

        try:
            with Controller.from_port(port=self.tor_config.control_port) as controller:
                controller.authenticate()
                controller.signal(Signal.NEWNYM)
            logger.info("Nueva identidad Tor solicitada — IP cambiada")
            return True
        except Exception as e:
            logger.error(f"Error al solicitar nueva identidad Tor: {e}")
            if self.debug_mode:
                raise TorConnectionError(f"Error al cambiar identidad: {e}") from e
            return False

    def get_exit_ip(self) -> Optional[str]:
        """
        Obtiene la IP de salida de Tor consultando check.torproject.org.
        Requiere que Tor esté activo y que socks5h:// esté disponible.

        Returns:
            Dirección IP de salida (string), o None si hay error.

        Note:
            Usa `requests` con proxy socks5h:// si está disponible.
            Si no, devuelve None en lugar de hacer una conexión directa.
        """
        if not self.tor_enabled:
            logger.warning("No se puede obtener IP de salida: Tor no está habilitado")
            return None

        try:
            import requests  # Opcional: no es dependencia hard del proyecto
            proxies = {
                "http":  f"socks5h://{self.tor_config.host}:{self.tor_config.socks_port}",
                "https": f"socks5h://{self.tor_config.host}:{self.tor_config.socks_port}",
            }
            response = requests.get(
                "https://check.torproject.org/api/ip",
                proxies=proxies,
                timeout=self.tor_config.timeout
            )
            data = response.json()
            ip = data.get("IP", None)
            if ip:
                logger.info(f"IP de salida Tor: {ip}")
            return ip
        except ImportError:
            logger.debug("requests no disponible — no se puede obtener IP de salida")
            return None
        except Exception as e:
            logger.error(f"Error al obtener IP de salida Tor: {e}")
            return None

    def __del__(self):
        """Limpieza al destruir el objeto: cierra el proceso Tor si fue iniciado aquí"""
        if self._tor_process is not None:
            try:
                self._tor_process.kill()
                logger.debug("Proceso Tor finalizado en destructor")
            except Exception:
                pass  # No se puede hacer nada si falla en el destructor
