"""
Excepciones personalizadas para UltraBrowser
Sistema de manejo de errores robusto y específico
"""


class UltraBrowserError(Exception):
    """Excepción base para todos los errores de UltraBrowser"""
    pass


class TorConnectionError(UltraBrowserError):
    """Error al conectar con Tor"""
    pass


class TorNotRunningError(TorConnectionError):
    """Tor no está ejecutándose"""
    pass


class TorProxyError(TorConnectionError):
    """Error con el proxy SOCKS5 de Tor"""
    pass


class TorAuthenticationError(TorConnectionError):
    """Error al autenticar con el controlador de Tor"""
    pass


class InvalidURLError(UltraBrowserError):
    """URL inválida o no permitida"""
    pass


class URLValidationError(InvalidURLError):
    """Error al validar una URL"""
    pass


class PermissionError(UltraBrowserError):
    """Error relacionado con permisos"""
    pass


class CameraPermissionError(PermissionError):
    """Error al acceder a la cámara"""
    pass


class MicrophonePermissionError(PermissionError):
    """Error al acceder al micrófono"""
    pass


class ConfigurationError(UltraBrowserError):
    """Error en la configuración"""
    pass


class ConfigFileNotFoundError(ConfigurationError):
    """Archivo de configuración no encontrado"""
    pass


class ConfigFileInvalidError(ConfigurationError):
    """Archivo de configuración inválido"""
    pass
