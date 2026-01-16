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
    
    # User-Agents
    user_agents_file: Path = field(default_factory=lambda: Path("config/user_agents.json"))
    rotate_user_agent: bool = True
    user_agent_rotation_interval: int = 30  # minutos
    
    # Debug
    debug_mode: bool = False
    log_file: Optional[Path] = field(default_factory=lambda: Path("logs/ultrabrowser.log"))
    
    # UI
    window_width: int = 1200
    window_height: int = 800
    show_status_bar: bool = True
    
    @classmethod
    def from_file(cls, config_path: Path) -> 'BrowserConfig':
        """
        Carga configuración desde archivo JSON
        
        Args:
            config_path: Ruta al archivo de configuración JSON
            
        Returns:
            Instancia de BrowserConfig con valores del archivo
            
        Raises:
            ConfigFileNotFoundError: Si el archivo no existe
            ConfigFileInvalidError: Si el JSON es inválido
        """
        if not config_path.exists():
            raise ConfigFileNotFoundError(f"Archivo de configuración no encontrado: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigFileInvalidError(f"JSON inválido en {config_path}: {e}") from e
        except Exception as e:
            raise ConfigFileInvalidError(f"Error al leer {config_path}: {e}") from e
        
        # Convertir rutas de string a Path
        if 'user_agents_file' in data:
            data['user_agents_file'] = Path(data['user_agents_file'])
        if 'log_file' in data and data['log_file']:
            data['log_file'] = Path(data['log_file'])
        
        # Manejar configuración anidada de Tor
        if 'tor' in data:
            data['tor'] = TorConfig(**data['tor'])
        
        return cls(**data)
    
    def to_file(self, config_path: Path) -> None:
        """
        Guarda la configuración en un archivo JSON
        
        Args:
            config_path: Ruta donde guardar el archivo
        """
        data = self.to_dict()
        
        # Crear directorio si no existe
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def to_dict(self) -> dict:
        """Convierte la configuración a diccionario"""
        data = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Path):
                data[key] = str(value)
            elif isinstance(value, TorConfig):
                data[key] = value.__dict__
            elif value is None:
                data[key] = None
            else:
                data[key] = value
        return data


def load_user_agents(user_agents_file: Path) -> List[str]:
    """
    Carga la lista de User-Agents desde un archivo JSON
    
    Args:
        user_agents_file: Ruta al archivo JSON con User-Agents
        
    Returns:
        Lista de User-Agents
        
    Raises:
        ConfigFileNotFoundError: Si el archivo no existe
        ConfigFileInvalidError: Si el JSON es inválido
    """
    if not user_agents_file.exists():
        logger.warning(f"Archivo de User-Agents no encontrado: {user_agents_file}. Usando valores por defecto.")
        # Retornar User-Agents por defecto
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
    
    try:
        with open(user_agents_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'user_agents' in data and isinstance(data['user_agents'], list):
            return data['user_agents']
        else:
            logger.warning(f"Formato inválido en {user_agents_file}. Usando valores por defecto.")
            return load_user_agents(Path("nonexistent"))  # Retornar defaults
    except json.JSONDecodeError as e:
        logger.error(f"Error al parsear JSON en {user_agents_file}: {e}")
        raise ConfigFileInvalidError(f"JSON inválido en {user_agents_file}: {e}") from e
    except Exception as e:
        logger.error(f"Error al leer {user_agents_file}: {e}")
        raise ConfigFileInvalidError(f"Error al leer {user_agents_file}: {e}") from e


# Configuración global (se inicializa en main.py)
_config: Optional[BrowserConfig] = None


def get_config() -> BrowserConfig:
    """Obtiene la configuración global"""
    global _config
    if _config is None:
        _config = BrowserConfig()
    return _config


def set_config(config: BrowserConfig) -> None:
    """Establece la configuración global"""
    global _config
    _config = config
