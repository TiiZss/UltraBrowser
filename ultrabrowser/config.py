"""
Sistema de configuración centralizado para UltraBrowser
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import json
from .exceptions import ConfigFileNotFoundError, ConfigFileInvalidError
from .logging_config import get_logger

logger = get_logger()


@dataclass
class TorConfig:
    """Configuración específica de Tor"""
    socks_port: int = 9050
    control_port: int = 9051
    host: str = "127.0.0.1"
    timeout: int = 10
    retry_attempts: int = 3
    tor_binary_path: Optional[str] = None


@dataclass
class BrowserConfig:
    """Configuración principal del navegador"""

    # Tor
    tor: TorConfig = field(default_factory=TorConfig)

    # Navegación
    default_homepage: str = "https://www.duckduckgo.com"
    force_https: bool = True
    block_insecure_content: bool = True

    # Privacidad
    enable_javascript: bool = True
    enable_plugins: bool = False
    enable_local_storage: bool = False
    webrtc_public_only: bool = True

    # Bloqueo de anuncios y rastreadores
    block_ads: bool = True

    # User-Agents
    user_agents_file: Path = field(default_factory=lambda: Path("config/user_agents.json"))
    rotate_user_agent: bool = True
    user_agent_rotation_interval: int = 30  # minutos

    # Debug
    debug_mode: bool = False
    # Nota de privacidad: log_file es None por defecto para no escribir datos
    # de navegación en disco. Activar solo para depuración.
    log_file: Optional[Path] = None
    diagnostics_dir: Optional[Path] = None
    chromium_log_file: Optional[Path] = None
    fault_log_file: Optional[Path] = None
    uncaught_exceptions_file: Optional[Path] = None
    open_diagnostics_on_failure: bool = True

    # UI
    window_width: int = 1200
    window_height: int = 800
    show_status_bar: bool = True

    @classmethod
    def from_file(cls, config_path: Path) -> 'BrowserConfig':
        """
        Carga configuración desde archivo JSON.

        Args:
            config_path: Ruta al archivo de configuración JSON

        Returns:
            Instancia de BrowserConfig con valores del archivo

        Raises:
            ConfigFileNotFoundError: Si el archivo no existe
            ConfigFileInvalidError: Si el JSON es inválido
        """
        if not config_path.exists():
            raise ConfigFileNotFoundError(
                f"Archivo de configuración no encontrado: {config_path}"
            )

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigFileInvalidError(f"JSON inválido en {config_path}: {e}") from e
        except OSError as e:
            raise ConfigFileInvalidError(f"Error al leer {config_path}: {e}") from e

        # Convertir rutas de string a Path
        path_fields = {
            'user_agents_file',
            'log_file',
            'diagnostics_dir',
            'chromium_log_file',
            'fault_log_file',
            'uncaught_exceptions_file',
        }
        for field_name in path_fields:
            if field_name in data and data[field_name]:
                data[field_name] = Path(data[field_name])

        # Manejar configuración anidada de Tor
        if 'tor' in data and isinstance(data['tor'], dict):
            # Filtrar claves desconocidas para robustez
            known_tor_keys = {f.name for f in TorConfig.__dataclass_fields__.values()}
            tor_data = {k: v for k, v in data['tor'].items() if k in known_tor_keys}
            data['tor'] = TorConfig(**tor_data)

        # Filtrar claves desconocidas del JSON para robustez
        known_keys = {f for f in cls.__dataclass_fields__}
        data = {k: v for k, v in data.items() if k in known_keys}

        return cls(**data)

    def to_file(self, config_path: Path) -> None:
        """
        Guarda la configuración en un archivo JSON.

        Args:
            config_path: Ruta donde guardar el archivo
        """
        data = self.to_dict()
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def to_dict(self) -> dict:
        """Convierte la configuración a diccionario serializable"""
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Path):
                data[key] = str(value)
            elif isinstance(value, TorConfig):
                data[key] = {
                    k: str(v) if isinstance(v, Path) else v
                    for k, v in value.__dict__.items()
                }
            elif value is None:
                data[key] = None
            else:
                data[key] = value
        return data


def load_user_agents(user_agents_file: Path) -> List[str]:
    """
    Carga la lista de User-Agents desde un archivo JSON.

    Args:
        user_agents_file: Ruta al archivo JSON con User-Agents

    Returns:
        Lista de User-Agents (valores por defecto si el archivo no existe)

    Raises:
        ConfigFileInvalidError: Si el JSON es inválido
    """
    _defaults = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    ]

    if not user_agents_file.exists():
        logger.warning(
            f"Archivo de User-Agents no encontrado: {user_agents_file}. "
            "Usando lista por defecto."
        )
        return _defaults

    try:
        with open(user_agents_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, dict) and 'user_agents' in data:
            agents = data['user_agents']
        elif isinstance(data, list):
            agents = data
        else:
            logger.warning(
                f"Formato inválido en {user_agents_file}. Usando lista por defecto."
            )
            return _defaults

        if not isinstance(agents, list) or not agents:
            logger.warning(
                f"Lista de User-Agents vacía en {user_agents_file}. Usando defaults."
            )
            return _defaults

        return [str(ua) for ua in agents if isinstance(ua, str) and ua.strip()]

    except json.JSONDecodeError as e:
        logger.error(f"JSON inválido en {user_agents_file}: {e}")
        raise ConfigFileInvalidError(f"JSON inválido en {user_agents_file}: {e}") from e
    except OSError as e:
        logger.error(f"Error al leer {user_agents_file}: {e}")
        raise ConfigFileInvalidError(f"Error al leer {user_agents_file}: {e}") from e


# Configuración global (inicializada en main.py)
_config: Optional[BrowserConfig] = None


def get_config() -> BrowserConfig:
    """Obtiene la configuración global. Si no está inicializada, devuelve una por defecto."""
    global _config
    if _config is None:
        _config = BrowserConfig()
    return _config


def set_config(config: BrowserConfig) -> None:
    """Establece la configuración global"""
    global _config
    _config = config
