"""
Ejemplo de módulo de configuración centralizado
Este archivo muestra cómo implementar la mejora #3
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List
import json


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
    log_file: Path = field(default_factory=lambda: Path("logs/ultrabrowser.log"))
    
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
            FileNotFoundError: Si el archivo no existe
            json.JSONDecodeError: Si el JSON es inválido
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Archivo de configuración no encontrado: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convertir rutas de string a Path
        if 'user_agents_file' in data:
            data['user_agents_file'] = Path(data['user_agents_file'])
        if 'log_file' in data:
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
            else:
                data[key] = value
        return data


# Configuración por defecto
DEFAULT_CONFIG = BrowserConfig()
